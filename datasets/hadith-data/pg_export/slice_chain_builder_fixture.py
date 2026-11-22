"""Cut the chain builder flow-test fixture: real rows of a projection for named reports, closed over foreign keys.

Usage: python -I datasets/hadith-data/pg_export/slice_chain_builder_fixture.py <projection dir> <out.json> <hadith id>...
Read by src/db/queries/__tests__/chain-builder-flows.test.ts (pg_export/AGENTS.md §Chain builder).
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

csv.field_size_limit(2**31 - 1)

TABLES = ["traditions", "sources", "collections", "books", "chapters", "hadiths", "narrators", "narrator_source_profiles",
          "narrator_lexicon_profiles", "narrator_teachers", "chains", "chain_mentions", "chain_mention_candidates"]


def rows(directory: Path, table: str) -> list[dict]:
    with (directory / "canonical" / f"{table}.csv").open(encoding="utf-8", newline="") as handle:
        return [{key: (value if value != "" else None) for key, value in row.items()} for row in csv.DictReader(handle)]


def main(projection: Path, output: Path, chosen: list[str]) -> None:
    manifest = json.loads((projection / "canonical" / "manifest.json").read_text(encoding="utf-8"))
    chosen = sorted(set(chosen))
    hadiths = {row["id"]: row for row in rows(projection, "hadiths")}
    missing = [h for h in chosen if h not in hadiths]
    if missing:
        raise SystemExit(f"not in the projection: {missing}")
    picked_mentions = [m for m in rows(projection, "chain_mentions") if m["hadith_id"] in chosen]
    picked_candidates = [c for c in rows(projection, "chain_mention_candidates") if c["hadith_id"] in chosen]
    narrator_ids = ({c["narrator_id"] for c in picked_candidates} | {m["narrator_id"] for m in picked_mentions if m["narrator_id"]}
                    | {m["name_latin_narrator_id"] for m in picked_mentions if m["name_latin_narrator_id"]})
    collections = {hadiths[h]["collection_id"] for h in chosen}
    out: dict = {"generated_from": {"projection_content_sha256": manifest["content_sha256"],
                                    "projection_version": manifest["projection_version"]},
                 "reports": chosen}
    out["traditions"] = rows(projection, "traditions")
    out["collections"] = [row for row in rows(projection, "collections") if row["id"] in collections]
    out["sources"] = [row for row in rows(projection, "sources") if row["id"] in {c["source_id"] for c in out["collections"]}]
    out["hadiths"] = [hadiths[h] for h in chosen]
    out["books"] = [row for row in rows(projection, "books") if row["id"] in {hadiths[h]["book_id"] for h in chosen}]
    out["chapters"] = [row for row in rows(projection, "chapters") if row["id"] in {hadiths[h]["chapter_id"] for h in chosen}]
    out["narrators"] = [row for row in rows(projection, "narrators") if row["id"] in narrator_ids]
    out["narrator_source_profiles"] = [row for row in rows(projection, "narrator_source_profiles")
                                       if row["narrator_id"] in narrator_ids]
    out["narrator_lexicon_profiles"] = [row for row in rows(projection, "narrator_lexicon_profiles")
                                        if row["narrator_id"] in narrator_ids]
    out["narrator_teachers"] = [row for row in rows(projection, "narrator_teachers")
                                if row["student_id"] in narrator_ids and row["teacher_id"] in narrator_ids]
    out["chains"] = [row for row in rows(projection, "chains") if row["hadith_id"] in chosen]
    out["chain_mentions"] = picked_mentions
    out["chain_mention_candidates"] = picked_candidates
    output.write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({table: len(out[table]) for table in TABLES}, sort_keys=True))
    print(json.dumps(chosen, ensure_ascii=False))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3:])
