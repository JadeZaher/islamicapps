#!/usr/bin/env python3
"""Back up the production Postgres to the private Railway bucket. See docs/backups/README.md.

Subcommands:
  run        preflight -> pg_dump (custom, compressed) -> SHA-256 -> upload -> verify listing + re-hash
  verify     list a prefix and re-hash the dump against its recorded SHA-256
  retention  list dated db/ prefixes and flag those beyond --keep (reports only, never deletes)
  put        upload extra files (relative to datasets/ or --root) under a prefix with per-file SHA-256 (input backups)

Environment only (no secrets on the command line or on disk):
  BACKUP_DATABASE_URL                                 database to dump (e.g. the value of DATABASE_URL_PRODUCTION)
  BACKUP_S3_ENDPOINT, BACKUP_S3_BUCKET, BACKUP_S3_ACCESS_KEY_ID, BACKUP_S3_SECRET_ACCESS_KEY
  BACKUP_PG_DUMP   optional: path to a pg_dump/psql directory-less binary prefix whose major version >= the server's
  BACKUP_PG_IMAGE  optional: container image providing pg_dump/psql (default docker.io/library/postgres:18), run with podman
Never deletes local or remote data except the local dump when --delete-local is passed after a verified upload.
"""
import argparse, datetime as dt, hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path, PureWindowsPath

REPO = Path(__file__).resolve().parents[3]
DATASETS = REPO / "datasets"
IMAGE = os.environ.get("BACKUP_PG_IMAGE", "docker.io/library/postgres:18")
MULTIPART = 64 * 1024 * 1024


def tool(name, args, workdir=None, capture=False):
    """Run pg_dump/psql locally (BACKUP_PG_DUMP=<bin dir>) or in a podman container; the URL is read from the environment."""
    bin_dir = os.environ.get("BACKUP_PG_DUMP")
    if bin_dir:
        cmd = [str(Path(bin_dir) / name), os.environ["BACKUP_DATABASE_URL"]] + args
    else:
        cmd = ["podman", "run", "--rm", "-e", "BACKUP_DATABASE_URL"]
        if workdir:
            cmd += ["-v", f"{PureWindowsPath(workdir) if os.name == 'nt' else workdir}:/out"]
        cmd += [IMAGE, "sh", "-c", f'{name} "$BACKUP_DATABASE_URL" "$@"', "sh"] + args
    return subprocess.run(cmd, check=True, text=True, capture_output=capture)


def database_url_present():
    if not os.environ.get("BACKUP_DATABASE_URL"):
        sys.exit("missing environment variable: BACKUP_DATABASE_URL")


def psql_scalar(sql):
    return tool("psql", ["-Atc", sql], capture=True).stdout.strip()


def client():
    import boto3
    from botocore.config import Config
    names = ("BACKUP_S3_ENDPOINT", "BACKUP_S3_BUCKET", "BACKUP_S3_ACCESS_KEY_ID", "BACKUP_S3_SECRET_ACCESS_KEY")
    env = {k: os.environ.get(k) for k in names}
    missing = [k for k, v in env.items() if not v]
    if missing:
        sys.exit("missing environment variables: " + ", ".join(missing))
    cfg = Config(signature_version="s3v4", s3={"addressing_style": "virtual"}, retries={"max_attempts": 8, "mode": "standard"},
                 request_checksum_calculation="when_required", response_checksum_validation="when_required", read_timeout=120)
    s3 = boto3.client("s3", endpoint_url=env["BACKUP_S3_ENDPOINT"], region_name="auto", config=cfg,
                      aws_access_key_id=env["BACKUP_S3_ACCESS_KEY_ID"], aws_secret_access_key=env["BACKUP_S3_SECRET_ACCESS_KEY"])
    return s3, env["BACKUP_S3_BUCKET"]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while chunk := fh.read(8 * 1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def upload(s3, bucket, path, key, sha):
    from boto3.s3.transfer import TransferConfig
    s3.upload_file(str(path), bucket, key, ExtraArgs={"Metadata": {"sha256": sha}},
                   Config=TransferConfig(multipart_threshold=MULTIPART, multipart_chunksize=32 * 1024 * 1024, use_threads=False))


def remote_sha(s3, bucket, key):
    h = hashlib.sha256()
    for chunk in s3.get_object(Bucket=bucket, Key=key)["Body"].iter_chunks(8 * 1024 * 1024):
        h.update(chunk)
    return h.hexdigest()


def listing(s3, bucket, prefix):
    found = {}
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix + "/"):
        for o in page.get("Contents", []):
            found[o["Key"]] = o["Size"]
    return found


def cmd_run(args):
    database_url_present()
    s3, bucket = client()
    stamp = args.date or dt.date.today().isoformat()
    prefix = f"db/{stamp}"
    workdir = Path(args.workdir).resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    name = f"railway-{stamp}.dump"
    dump_path = workdir / name

    versions = psql_scalar("select string_agg(id || ' ' || load_status, ';') from dataset_versions")
    server = psql_scalar("show server_version")
    print(f"server {server}; dataset versions: {versions}", flush=True)
    loading = "loading" in versions
    if loading:
        print("WARNING: a dataset version is loading; the dump is a consistent snapshot but may hold a partial load", flush=True)

    started = time.time()
    target = str(dump_path) if os.environ.get("BACKUP_PG_DUMP") else "/out/" + name
    tool("pg_dump", ["--format=custom", "--compress=6", "--no-owner", "--no-acl", "--file=" + target], workdir=str(workdir))
    dump_seconds = time.time() - started
    size = dump_path.stat().st_size
    started = time.time()
    sha = sha256_file(dump_path)
    print(f"dump {size} bytes in {dump_seconds:.0f}s; sha256 {sha}", flush=True)

    meta = {"database": "railway", "server_version": server, "dataset_versions": versions, "load_in_progress": loading,
            "dump_file": name, "bytes": size, "sha256": sha, "dump_seconds": round(dump_seconds), "format": "custom, gzip level 6",
            "taken_at": dt.datetime.now(dt.timezone.utc).isoformat()}
    meta_path, sum_path = workdir / f"{name}.meta.json", workdir / f"{name}.sha256"
    meta_path.write_text(json.dumps(meta, indent=1), encoding="utf-8")
    sum_path.write_text(f"{sha}  {name}\n", encoding="utf-8")
    started = time.time()
    for path in (dump_path, sum_path, meta_path):
        upload(s3, bucket, path, f"{prefix}/{path.name}", sha if path == dump_path else sha256_file(path))
    print(f"uploaded in {time.time()-started:.0f}s", flush=True)
    verify(s3, bucket, prefix, name, sha, size)
    if args.delete_local:
        shutil.rmtree(workdir) if not any(p.name not in {name, name + ".sha256", name + ".meta.json"} for p in workdir.iterdir()) else dump_path.unlink()
        print("local dump removed after verified upload")
    print("retention: nothing is deleted automatically; run `retention --keep N` to list prefixes you may remove by hand")


def verify(s3, bucket, prefix, name, sha, size):
    found = listing(s3, bucket, prefix)
    for suffix in ("", ".sha256", ".meta.json"):
        if f"{prefix}/{name}{suffix}" not in found:
            sys.exit(f"MISSING {prefix}/{name}{suffix}")
    if found[f"{prefix}/{name}"] != size:
        sys.exit("SIZE MISMATCH on the dump")
    if remote_sha(s3, bucket, f"{prefix}/{name}") != sha:
        sys.exit("SHA-256 MISMATCH on the dump")
    print(f"verified {prefix}: {len(found)} objects, dump {size} bytes, sha256 matches", flush=True)


def cmd_verify(args):
    s3, bucket = client()
    found = listing(s3, bucket, args.prefix)
    dumps = [k for k in found if k.endswith(".dump")]
    if not dumps:
        sys.exit("no .dump under " + args.prefix)
    key = dumps[0]
    expected = s3.get_object(Bucket=bucket, Key=key + ".sha256")["Body"].read().decode().split()[0]
    verify(s3, bucket, args.prefix, Path(key).name, expected, found[key])


def cmd_retention(args):
    s3, bucket = client()
    prefixes = sorted({"/".join(k.split("/")[:2]) for k in listing(s3, bucket, "db").keys()})
    for i, p in enumerate(reversed(prefixes)):
        print(("KEEP   " if i < args.keep else "REVIEW ") + p)
    print("report only: nothing is deleted. Policy: keep the newest N plus the first of each month; remove others by hand.")


def cmd_put(args):
    s3, bucket = client()
    root = Path(args.root).resolve() if args.root else DATASETS
    rows = []
    for rel in args.paths:
        base = root / rel
        files = [p for p in base.rglob("*") if p.is_file()] if base.is_dir() else [base]
        for p in sorted(files):
            rows.append((p, p.relative_to(root).as_posix()))
    manifest = []
    for p, relative in rows:
        sha, size = sha256_file(p), p.stat().st_size
        key = f"{args.prefix}/{relative}"
        try:
            head = s3.head_object(Bucket=bucket, Key=key)
            if head["ContentLength"] == size and head.get("Metadata", {}).get("sha256") == sha:
                manifest.append({"path": relative, "bytes": size, "sha256": sha})
                continue
        except Exception:  # noqa: BLE001 - absent object
            pass
        upload(s3, bucket, p, key, sha)
        manifest.append({"path": relative, "bytes": size, "sha256": sha})
        print(f"uploaded {relative} ({size} bytes)", flush=True)
    Path(args.manifest).write_text("".join(json.dumps(r, separators=(",", ":")) + "\n" for r in manifest), encoding="utf-8")
    found = listing(s3, bucket, args.prefix)
    missing = [m["path"] for m in manifest if f"{args.prefix}/{m['path']}" not in found]
    print(f"{len(manifest)} files, {sum(m['bytes'] for m in manifest)} bytes, remote {len(found)} objects, missing {len(missing)}")
    sys.exit(1 if missing else 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run")
    p.add_argument("--date")
    p.add_argument("--workdir", default=str(REPO / ".omc/backups/postgres"))
    p.add_argument("--delete-local", action="store_true")
    p.set_defaults(fn=cmd_run)
    p = sub.add_parser("verify")
    p.add_argument("--prefix", required=True)
    p.set_defaults(fn=cmd_verify)
    p = sub.add_parser("retention")
    p.add_argument("--keep", type=int, default=8)
    p.set_defaults(fn=cmd_retention)
    p = sub.add_parser("put")
    p.add_argument("--prefix", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--root", help="directory the paths are relative to (default: datasets/)")
    p.add_argument("paths", nargs="+", help="paths relative to --root (default datasets/)")
    p.set_defaults(fn=cmd_put)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
