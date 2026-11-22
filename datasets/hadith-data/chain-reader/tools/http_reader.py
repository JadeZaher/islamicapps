"""STUB: run the reader through an HTTP chat API. No request is implemented; see ../README.md §Running (b).

  python http_reader.py --packet pilot/packets/packet-01.jsonl --out-dir outputs/<run> --dry-run

What a request may contain: the contents of prompt.md as the system message and, as the user message, one packet row
(`{"id": ..., "text": ...}`: an opaque id and the public Arabic text). Nothing else: no project name, no path, no label,
no stored chain. The key is read at runtime from the environment variable below and is never printed, logged or written.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEY_VARIABLE = "CHAIN_READER_API_KEY"


def read_key() -> str:
    key = os.environ.get(KEY_VARIABLE, "")
    if not key:
        raise SystemExit(f"set {KEY_VARIABLE} in the environment (never in a file or an argument)")
    return key


def build_request(prompt: str, row: dict) -> dict:
    """The whole payload content for one report. A packet row must be exactly id and text."""
    if set(row) != {"id", "text"}:
        raise ValueError(f"packet row must hold only id and text, got {sorted(row)}")
    return {"system": prompt, "user": json.dumps({"id": row["id"], "text": row["text"]}, ensure_ascii=False)}


def send(request: dict, key: str) -> str:
    """Fill in once a provider is chosen: POST `request` (mapped to that provider's message format) with `key` in its
    authorisation header, temperature 0, and return the reply text verbatim. Not implemented on purpose."""
    raise NotImplementedError("no provider chosen; see README.md §Running (b)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--packet", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--dry-run", action="store_true", help="check the payloads and print their sizes; needs no key")
    args = parser.parse_args()
    prompt = (ROOT / "prompt.md").read_text(encoding="utf-8")
    rows = [json.loads(line) for line in Path(args.packet).read_text(encoding="utf-8").splitlines() if line.strip()]
    requests = [build_request(prompt, row) for row in rows]
    if args.dry_run:
        print(f"{len(requests)} requests; system {len(prompt)} chars; user {min(len(r['user']) for r in requests)}-{max(len(r['user']) for r in requests)} chars")
        return 0
    key = read_key()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for row, request in zip(rows, requests):
        (out_dir / f"{row['id']}.json").write_text(send(request, key), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
