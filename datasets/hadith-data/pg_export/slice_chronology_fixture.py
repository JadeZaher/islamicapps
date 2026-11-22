"""Cut the chain chronology flow-test fixture: real rows of a projection, closed over foreign keys.

Usage: python -I datasets/hadith-data/pg_export/slice_chronology_fixture.py <projection dir> <out.json>
Reports: Sunan Abi Da'ud k6:28147 (a later ʿUmar read as the Companion: identity withheld), k6:28195 (a flattened tahwil:
al-Awzaʿi twice in one chain) and the first report by id whose chain keeps a standing pair the student was born at most
IRSAL_YEARS after the teacher died (impossible as hearing, both identities stand). Read by
src/db/queries/__tests__/chronology-flows.test.ts.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from chain_chronology import Lifespan, transmission_chronology  # noqa: E402

csv.field_size_limit(2**31 - 1)

NAMED = ["hadith:k6:28147", "hadith:k6:28195"]
TABLES = ["traditions", "sources", "collections", "books", "chapters", "hadiths", "narrators", "narrator_lexicon_profiles",
          "narrator_teachers", "chains", "chain_mentions", "chain_mention_candidates"]


def rows(directory: Path, table: str) -> list[dict]:
    with (directory / "canonical" / f"{table}.csv").open(encoding="utf-8", newline="") as handle:
        return [{key: (value if value != "" else None) for key, value in row.items()} for row in csv.DictReader(handle)]


def year(value: str | None) -> int | None:
    return int(value) if value and int(value) != 0 else None


def main(projection: Path, output: Path) -> None:
    manifest = json.loads((projection / "canonical" / "manifest.json").read_text(encoding="utf-8"))
    mentions = rows(projection, "chain_mentions")
    profiles = {row["narrator_id"]: row for row in rows(projection, "narrator_lexicon_profiles")}
    life = {key: Lifespan(year(row["birth_year_hijri"]), year(row["death_year_hijri"])) for key, row in profiles.items()}
    by_chain: dict[str, dict[int, dict]] = defaultdict(dict)
    for mention in mentions:
        by_chain[mention["chain_id"]][int(mention["position"])] = mention
    irsal = set()
    for chain in by_chain.values():
        for position, student in chain.items():
            teacher = chain.get(position + 1)
            if not teacher or not student["narrator_id"] or not teacher["narrator_id"]:
                continue
            pair = (life.get(student["narrator_id"]), life.get(teacher["narrator_id"]))
            if pair[0] and pair[1] and transmission_chronology(*pair) == "student_born_after_teacher_died":
                irsal.add(student["hadith_id"])
    chosen = sorted(set(NAMED) | {min(hadith for hadith in irsal if hadith.startswith("hadith:k6:"))})

    hadiths = {row["id"]: row for row in rows(projection, "hadiths")}
    picked_mentions = [m for m in mentions if m["hadith_id"] in chosen]
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
    out["narrator_lexicon_profiles"] = [profiles[n] for n in sorted(narrator_ids) if n in profiles]
    out["narrator_teachers"] = [row for row in rows(projection, "narrator_teachers")
                                if row["student_id"] in narrator_ids and row["teacher_id"] in narrator_ids]
    out["chains"] = [row for row in rows(projection, "chains") if row["hadith_id"] in chosen]
    out["chain_mentions"] = picked_mentions
    out["chain_mention_candidates"] = picked_candidates
    output.write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({table: len(out[table]) for table in TABLES}, sort_keys=True))
    print(json.dumps(chosen, ensure_ascii=False))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
