"""Edition identifications: the Sunni audit's high-confidence rows that name a person with a printed-edition citation.

Usage: python -I datasets/hadith-data/pg_export/build_edition_identifications.py
Reads chain-audit/sunni/corrections.jsonl; writes edition_identifications.json (pg_export/AGENTS.md §Edition identifications).
Only rows with `proposed_narrator_id`, confidence `high` and a cited quote; medium rows stay candidates in the audit only.
"""

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "chain-audit" / "sunni" / "corrections.jsonl"
OUTPUT = HERE / "edition_identifications.json"


def surface_of(row: dict) -> str:
    values = row["evidence"]["values"]
    if "culprit_position" in values:
        side = "student" if values["culprit_position"] == values["student_position"] else "teacher"
        return values[f"{side}_surface"]
    return values["surface"]


def main() -> None:
    raw = SOURCE.read_bytes()
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    out = []
    for row in rows:
        if not row.get("proposed_narrator_id") or row["confidence"] != "high" or not row.get("identity_evidence"):
            continue
        evidence = row["identity_evidence"][0]
        _, record, branch, position = row["mention_id"].rsplit(":", 3)
        locator = f"{evidence['book']}, vol. {evidence['vol']}, p. {evidence['page']}"
        out.append({
            "hadith_id": row["hadith_id"], "bundle_branch": int(branch), "bundle_position": int(position),
            "surface": surface_of(row), "narrator_id": row["proposed_narrator_id"], "replaces": row.get("culprit_narrator_id"),
            "detail": f"{locator}: «{evidence['quote'][:200]}»", "locator": locator, "url": evidence.get("search_url"),
            "integrator_note": row.get("integrator_note"),
        })
    out.sort(key=lambda item: (item["hadith_id"], item["bundle_branch"], item["bundle_position"]))
    OUTPUT.write_text(json.dumps({
        "meaning": "Identifications the Sunni chain audit made from a printed edition's own note, high confidence only. Basis "
                   "edition_identification: machine-reviewed with a cited source, never verified by a reviewer.",
        "source": "datasets/hadith-data/chain-audit/sunni/corrections.jsonl",
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "identifications": out,
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(len(out))


if __name__ == "__main__":
    main()
