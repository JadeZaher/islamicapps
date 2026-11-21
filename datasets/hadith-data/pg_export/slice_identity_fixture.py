"""Cut the external-identity flow-test fixture: real rows of a loaded projection, closed over foreign keys.

Usage: python -I datasets/hadith-data/pg_export/slice_identity_fixture.py <projection dir> <out.json>
Reports chosen by rule (first by id that qualifies), so a rebuild of the same projection gives the same file:
Sunan Abi Da'ud k6:19122 with its two Ma'ani al-Akhbar tellings (the owner's example), an al-Kafi report whose chain
has an Imam kunya and a Riwayat identity standing, a Sunni report where two sources agree, a report with a Riwayat
automatic link confirmed by the text, a Sunni report with a bare أبي عبد الله, a report naming a label-like Riwayat
record, and the first Ibadi and Zaydi reports. Read by src/db/queries/__tests__/identity-flows.test.ts.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

csv.field_size_limit(2**31 - 1)

OWNER_EXAMPLE = ["hadith:k6:19122", "hadith:thaqalayn:06c871a7dec1feb72290ba14", "hadith:thaqalayn:77fead5f962be2476f87fea5"]
TABLES = ["traditions", "sources", "collections", "books", "chapters", "hadiths", "translations", "narrators",
          "narrator_source_profiles", "narrator_external_ids", "narrator_link_candidates", "chains", "chain_mentions",
          "chain_mention_candidates", "report_correspondence_candidates", "report_correspondence_cluster_members"]


def rows(directory: Path, table: str) -> list[dict]:
    with (directory / "canonical" / f"{table}.csv").open(encoding="utf-8", newline="") as handle:
        return [{key: (value if value != "" else None) for key, value in row.items()} for row in csv.DictReader(handle)]


def main(projection: Path, output: Path) -> None:
    manifest = json.loads((projection / "canonical" / "manifest.json").read_text(encoding="utf-8"))
    mentions = rows(projection, "chain_mentions")
    candidates = rows(projection, "chain_mention_candidates")
    hadiths = {row["id"]: row for row in rows(projection, "hadiths")}
    translations = rows(projection, "translations")
    profiles = {row["narrator_id"]: row for row in rows(projection, "narrator_source_profiles")}
    english = {row["hadith_id"] for row in translations if row["quality_status"] == "complete"}
    methods: dict[str, set[str]] = defaultdict(set)
    for mention in mentions:
        if mention["extraction_method"] and mention["narrator_id"]:
            methods[mention["hadith_id"]].add(mention["extraction_method"])
    by_hadith: dict[str, list[dict]] = defaultdict(list)
    for candidate in candidates:
        by_hadith[candidate["hadith_id"]].append(candidate)

    def first(predicate) -> str:
        for hadith_id in sorted(hadiths):
            if predicate(hadith_id):
                return hadith_id
        raise SystemExit("no report qualifies")

    chosen = list(OWNER_EXAMPLE)
    chosen.append(first(lambda h: h.startswith("hadith:thaqalayn:") and hadiths[h]["collection_id"].endswith("al-kafi")
                        and {"imam_kunya_convention", "source_riwayat_confirmed_by_text"} <= methods[h] and h in english))
    chosen.append(first(lambda h: h.startswith("hadith:k6:") and "two_sources_agree" in methods[h] and h in english))
    chosen.append(first(lambda h: any(c["source_assertion_origin"] == "riwayat_automatic_linking"
                                      and c["basis"] == "source_riwayat_confirmed_by_text" for c in by_hadith[h])))
    sunni_kunya = {m["hadith_id"] for m in mentions if m["surface_ar"] == "أبي عبد الله" and m["hadith_id"].startswith("hadith:k6:")}
    chosen.append(first(lambda h: h in sunni_kunya))
    labels = {narrator for narrator, profile in profiles.items() if profile["label_reason"] == "name_held_by_several_ids"}
    chosen.append(first(lambda h: any(c["narrator_id"] in labels for c in by_hadith[h])))
    chosen.append(first(lambda h: hadiths[h]["tradition_id"] == "tradition:ibadi" and by_hadith[h]))
    chosen.append(first(lambda h: hadiths[h]["tradition_id"] == "tradition:zaydi"))
    chosen = sorted(set(chosen))

    out: dict = {"generated_from": {"projection_content_sha256": manifest["content_sha256"],
                                    "projection_version": manifest["projection_version"]},
                 "reports": chosen}
    picked_mentions = [m for m in mentions if m["hadith_id"] in chosen]
    picked_candidates = [c for c in candidates if c["hadith_id"] in chosen]
    narrator_ids = ({c["narrator_id"] for c in picked_candidates} | {m["narrator_id"] for m in picked_mentions if m["narrator_id"]}
                    | {m["name_latin_narrator_id"] for m in picked_mentions if m["name_latin_narrator_id"]})
    links = [row for row in rows(projection, "narrator_link_candidates") if row["external_narrator_id"] in narrator_ids]
    narrator_ids |= {row["rawi_narrator_id"] for row in links}
    collections = {hadiths[h]["collection_id"] for h in chosen}
    pairs = [row for row in rows(projection, "report_correspondence_candidates")
             if row["hadith_id_a"] in chosen and row["hadith_id_b"] in chosen]
    paired = {row["hadith_id_a"] for row in pairs} | {row["hadith_id_b"] for row in pairs}
    out["traditions"] = rows(projection, "traditions")
    out["collections"] = [row for row in rows(projection, "collections") if row["id"] in collections]
    out["sources"] = [row for row in rows(projection, "sources") if row["id"] in {c["source_id"] for c in out["collections"]}]
    out["hadiths"] = [hadiths[h] for h in chosen]
    out["books"] = [row for row in rows(projection, "books") if row["id"] in {hadiths[h]["book_id"] for h in chosen}]
    out["chapters"] = [row for row in rows(projection, "chapters") if row["id"] in {hadiths[h]["chapter_id"] for h in chosen}]
    out["translations"] = [row for row in translations if row["hadith_id"] in chosen]
    out["narrators"] = [row for row in rows(projection, "narrators") if row["id"] in narrator_ids]
    out["narrator_source_profiles"] = [profile for narrator, profile in sorted(profiles.items()) if narrator in narrator_ids]
    out["narrator_external_ids"] = [row for row in rows(projection, "narrator_external_ids") if row["narrator_id"] in narrator_ids]
    out["narrator_link_candidates"] = links
    out["chains"] = [row for row in rows(projection, "chains") if row["hadith_id"] in chosen]
    out["chain_mentions"] = picked_mentions
    out["chain_mention_candidates"] = picked_candidates
    out["report_correspondence_candidates"] = pairs
    out["report_correspondence_cluster_members"] = [row for row in rows(projection, "report_correspondence_cluster_members")
                                                    if row["hadith_id"] in paired and row["star_centre_hadith_id"] in chosen]
    output.write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({table: len(out[table]) for table in TABLES}, sort_keys=True))
    print(json.dumps(chosen, ensure_ascii=False))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
