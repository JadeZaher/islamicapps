"""SHA-256 of prompt.md (exact bytes, LF endings, as reviews/ai/tools/specialist-lib.ts hashes a specialist prompt).

  python hash_prompt.py            # print the hash and the front-matter version
  python hash_prompt.py --check    # fail unless README.md records this hash
"""

import argparse
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = (ROOT / "prompt.md").read_bytes()
    if b"\r" in data:
        print("prompt.md has CR characters: the hash would depend on the checkout's line endings", file=sys.stderr)
        return 2
    digest = hashlib.sha256(data).hexdigest()
    version = re.search(rb"^version:\s*(\S+)", data, re.MULTILINE).group(1).decode()
    print(f"{digest}  version {version}")
    if args.check and f"`{digest}`" not in (ROOT / "README.md").read_text(encoding="utf-8"):
        print("README.md does not record this hash", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
