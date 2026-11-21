#!/usr/bin/env python3
"""Back up datasets/ to an S3-compatible bucket (Railway Storage Bucket). See docs/backups/README.md.

Subcommands: plan | upload | verify. Credentials come from environment variables only:
  BACKUP_S3_ENDPOINT, BACKUP_S3_BUCKET, BACKUP_S3_ACCESS_KEY_ID, BACKUP_S3_SECRET_ACCESS_KEY
Never deletes or modifies local files; never deletes remote objects.
"""
import argparse, concurrent.futures as cf, hashlib, json, os, random, sys, threading, time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DATASETS = REPO / "datasets"
# Path prefixes (relative to datasets/) excluded wholesale: regenerable or being written by another process.
EXCLUDED_PREFIXES = ("hadith-data/development/", "sources/external/")
EXCLUDED_DIR_NAMES = {"__pycache__"}
EXCLUDED_SUFFIXES = (".pyc", ".lock", ".sqlite3", ".sqlite3-wal", ".sqlite3-shm", ".sqlite3-journal")
CONCURRENCY = 4
MULTIPART_THRESHOLD = 64 * 1024 * 1024
CHUNK = 32 * 1024 * 1024


def collect():
    """Return (included[(rel, size)], excluded{reason: [(rel, size)]}, unreadable[rel])."""
    included, excluded, unreadable = [], {}, []

    def skip(reason, rel, size):
        excluded.setdefault(reason, []).append((rel, size))

    for root, dirs, files in os.walk(DATASETS):
        rel_root = Path(root).relative_to(DATASETS).as_posix()
        rel_root = "" if rel_root == "." else rel_root + "/"
        keep = []
        for d in dirs:
            rel_dir = rel_root + d + "/"
            if d in EXCLUDED_DIR_NAMES:
                skip("__pycache__", rel_dir, dir_size(Path(root) / d))
            elif rel_dir in EXCLUDED_PREFIXES:
                skip("regenerable/in-flight: " + rel_dir, rel_dir, dir_size(Path(root) / d))
            else:
                keep.append(d)
        dirs[:] = keep
        for f in files:
            rel = rel_root + f
            path = Path(root) / f
            try:
                size = path.stat().st_size
            except OSError:
                unreadable.append(rel)
                continue
            if f.endswith(EXCLUDED_SUFFIXES):
                suffix = next(s for s in EXCLUDED_SUFFIXES if f.endswith(s))
                skip("regenerable: *" + suffix, rel, size)
                continue
            try:
                with open(path, "rb") as fh:
                    fh.read(1)
            except OSError:
                unreadable.append(rel)
                continue
            included.append((rel, size))
    return sorted(included), excluded, sorted(unreadable)


def dir_size(path):
    total = 0
    for r, _, fs in os.walk(path):
        for f in fs:
            try:
                total += os.path.getsize(os.path.join(r, f))
            except OSError:
                pass
    return total


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while chunk := fh.read(8 * 1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def fmt(n):
    return f"{n/1e9:.3f} GB" if n >= 1e8 else f"{n/1e6:.1f} MB"


def client():
    import boto3
    from botocore.config import Config
    names = ("BACKUP_S3_ENDPOINT", "BACKUP_S3_BUCKET", "BACKUP_S3_ACCESS_KEY_ID", "BACKUP_S3_SECRET_ACCESS_KEY")
    env = {k: os.environ.get(k) for k in names}
    missing = [k for k, v in env.items() if not v]
    if missing:
        sys.exit("missing environment variables: " + ", ".join(missing))
    cfg = Config(signature_version="s3v4", s3={"addressing_style": "virtual"},
                 retries={"max_attempts": 8, "mode": "standard"},
                 request_checksum_calculation="when_required", response_checksum_validation="when_required",
                 max_pool_connections=16, read_timeout=120)
    s3 = boto3.client("s3", endpoint_url=env["BACKUP_S3_ENDPOINT"], region_name="auto", config=cfg,
                      aws_access_key_id=env["BACKUP_S3_ACCESS_KEY_ID"],
                      aws_secret_access_key=env["BACKUP_S3_SECRET_ACCESS_KEY"])
    return s3, env["BACKUP_S3_BUCKET"]


def write_manifest(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")


def build_manifest(included):
    """Hash every included file; rows are {path, bytes, sha256}."""
    rows = []
    for i, (rel, size) in enumerate(included, 1):
        rows.append({"path": rel, "bytes": size, "sha256": sha256_file(DATASETS / rel)})
        if size > 50e6 or i % 200 == 0:
            print(f"  hashed {i}/{len(included)} {rel} ({fmt(size)})", flush=True)
    return rows


def cmd_plan(args):
    included, excluded, unreadable = collect()
    print(f"INCLUDE: {len(included)} files, {fmt(sum(s for _, s in included))}")
    for reason, items in sorted(excluded.items()):
        print(f"EXCLUDE [{reason}]: {len(items)} entries, {fmt(sum(s for _, s in items))}")
    for rel in unreadable:
        print(f"UNREADABLE (not backed up): {rel}")


def cmd_upload(args):
    s3, bucket = client()
    from boto3.s3.transfer import TransferConfig
    from botocore.exceptions import ClientError
    included, _, unreadable = collect()
    manifest_path = Path(args.manifest)
    if manifest_path.exists() and not args.rehash:
        rows = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines()]
        print(f"reusing manifest {manifest_path} ({len(rows)} files); pass --rehash to recompute", flush=True)
    else:
        print(f"hashing {len(included)} files ...", flush=True)
        rows = build_manifest(included)
        write_manifest(manifest_path, rows)
    total = sum(r["bytes"] for r in rows)
    print(f"manifest: {len(rows)} files, {fmt(total)}", flush=True)
    tcfg = TransferConfig(multipart_threshold=MULTIPART_THRESHOLD, multipart_chunksize=CHUNK, use_threads=False)
    lock = threading.Lock()
    state = {"done": 0, "bytes": 0, "skipped": 0, "failed": []}
    start = time.time()

    def one(r):
        key = f"{args.prefix}/{r['path']}"
        path = DATASETS / r["path"]
        for attempt in range(1, 6):
            try:
                try:
                    head = s3.head_object(Bucket=bucket, Key=key)
                    if head["ContentLength"] == r["bytes"] and head.get("Metadata", {}).get("sha256") == r["sha256"]:
                        return "skipped"
                except ClientError as e:
                    if e.response["Error"]["Code"] not in ("404", "NoSuchKey", "NotFound"):
                        raise
                if path.stat().st_size != r["bytes"]:
                    return "failed: changed-locally-since-manifest"
                s3.upload_file(str(path), bucket, key, ExtraArgs={"Metadata": {"sha256": r["sha256"]}}, Config=tcfg)
                return "uploaded"
            except Exception as e:  # noqa: BLE001
                if attempt == 5:
                    return f"failed: {type(e).__name__}"
                time.sleep(2 ** attempt)

    # Smallest first so most files land early; the large ones last.
    with cf.ThreadPoolExecutor(CONCURRENCY) as ex:
        futs = {ex.submit(one, r): r for r in sorted(rows, key=lambda r: r["bytes"])}
        for fut in cf.as_completed(futs):
            r, res = futs[fut], fut.result()
            with lock:
                state["done"] += 1
                state["bytes"] += r["bytes"]
                if res == "skipped":
                    state["skipped"] += 1
                if res.startswith("failed"):
                    state["failed"].append((r["path"], res))
                if r["bytes"] > 50e6 or state["done"] % 100 == 0 or res.startswith("failed"):
                    print(f"[{state['done']}/{len(rows)}] {fmt(state['bytes'])}/{fmt(total)} {res} {r['path']} "
                          f"({time.time()-start:.0f}s)", flush=True)
    print(f"done: {state['done']} files, {state['skipped']} already present, {len(state['failed'])} problems")
    for p in state["failed"]:
        print("PROBLEM:", p)
    for u in unreadable:
        print("NOT BACKED UP (unreadable):", u)
    sys.exit(1 if state["failed"] else 0)


def cmd_verify(args):
    s3, bucket = client()
    rows = [json.loads(line) for line in Path(args.manifest).read_text(encoding="utf-8").splitlines()]
    remote = {}
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=args.prefix + "/"):
        for o in page.get("Contents", []):
            remote[o["Key"][len(args.prefix) + 1:]] = o["Size"]
    local = {r["path"]: r["bytes"] for r in rows}
    print(f"remote: {len(remote)} objects, {sum(remote.values())} bytes")
    print(f"local manifest: {len(local)} files, {sum(local.values())} bytes")
    missing = [p for p in local if p not in remote]
    mismatched = [p for p in local if p in remote and remote[p] != local[p]]
    extra = [p for p in remote if p not in local]
    print(f"missing={len(missing)} size_mismatch={len(mismatched)} extra={len(extra)}")
    by_size = sorted(rows, key=lambda r: -r["bytes"])
    sample = by_size[:5] + random.Random(0).sample(by_size[5:], min(args.sample - 5, len(by_size) - 5))
    bad = 0
    for r in sample:
        h = hashlib.sha256()
        body = s3.get_object(Bucket=bucket, Key=f"{args.prefix}/{r['path']}")["Body"]
        for chunk in body.iter_chunks(8 * 1024 * 1024):
            h.update(chunk)
        ok = h.hexdigest() == r["sha256"]
        bad += not ok
        print(("OK  " if ok else "BAD ") + f"{r['sha256'][:12]} {fmt(r['bytes'])} {r['path']}", flush=True)
    print(f"sha256 sample: {len(sample)-bad}/{len(sample)} match")
    sys.exit(1 if (missing or mismatched or bad) else 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("plan", cmd_plan), ("upload", cmd_upload), ("verify", cmd_verify)):
        p = sub.add_parser(name)
        p.set_defaults(fn=fn)
        if name != "plan":
            p.add_argument("--prefix", default="2026-11-21", help="dated key prefix")
            p.add_argument("--manifest", default=str(REPO / "docs/backups/dataset-backup-2026-11-21.manifest.jsonl"))
        if name == "upload":
            p.add_argument("--rehash", action="store_true")
        if name == "verify":
            p.add_argument("--sample", type=int, default=25)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
