"""Cut the report-family flow-test fixture: real rows for a few reports, copied from a canonical projection.

Usage: python slice_correspondence_fixture.py --projection <dir> --catalog <catalog.json> --output <fixture.json>
       --hadith <id> [--hadith <id> ...]
Every pair between the chosen reports is kept (shown or not), with their chains, mentions, identity candidates, the
narrators those name, and the works they sit in. Values are typed from the live catalog. Deterministic.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

csv.field_size_limit(2**31 - 1)

TABLES = ("collections", "hadiths", "chains", "chain_mentions", "chain_mention_candidates", "narrators",
          "report_correspondence_candidates", "report_correspondence_cluster_members")


def typed(value: str, data_type: str):
    if value == "":
        return None
    if data_type in ("integer", "bigint", "smallint"):
        return int(value)
    if data_type in ("real", "double precision", "numeric"):
        return float(value)
    if data_type == "boolean":
        return value == "true"
    return value


def read(projection: Path, catalog: dict, table: str, keep) -> list[dict]:
    types = {column["name"]: column["dataType"] for column in catalog[table]}
    rows = []
    with (projection / "canonical" / f"{table}.csv").open("rt", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if keep(row):
                rows.append({name: typed(value, types[name]) for name, value in row.items()})
    return sorted(rows, key=lambda row: json.dumps(row, sort_keys=True, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--projection", required=True, type=Path)
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--hadith", action="append", required=True)
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    manifest = json.loads((args.projection / "canonical" / "manifest.json").read_text(encoding="utf-8"))
    chosen = set(args.hadith)

    out: dict[str, object] = {
        "generated_from": {"projection_content_sha256": manifest["content_sha256"],
                           "projection_version": manifest["projection_version"], "hadiths": sorted(chosen)},
    }
    out["hadiths"] = read(args.projection, catalog, "hadiths", lambda row: row["id"] in chosen)
    collections = {row["collection_id"] for row in out["hadiths"]}
    out["collections"] = read(args.projection, catalog, "collections", lambda row: row["id"] in collections)
    out["chains"] = read(args.projection, catalog, "chains", lambda row: row["hadith_id"] in chosen)
    out["chain_mentions"] = read(args.projection, catalog, "chain_mentions", lambda row: row["hadith_id"] in chosen)
    out["chain_mention_candidates"] = read(args.projection, catalog, "chain_mention_candidates",
                                           lambda row: row["hadith_id"] in chosen)
    narrators = {row["narrator_id"] for row in out["chain_mentions"] if row["narrator_id"]}
    narrators |= {row["narrator_id"] for row in out["chain_mention_candidates"]}
    out["narrators"] = read(args.projection, catalog, "narrators", lambda row: row["id"] in narrators)
    out["report_correspondence_candidates"] = read(
        args.projection, catalog, "report_correspondence_candidates",
        lambda row: row["hadith_id_a"] in chosen and row["hadith_id_b"] in chosen)
    out["report_correspondence_cluster_members"] = read(
        args.projection, catalog, "report_correspondence_cluster_members",
        lambda row: row["hadith_id"] in chosen and row["star_centre_hadith_id"] in chosen)
    missing = chosen - {row["id"] for row in out["hadiths"]}
    if missing:
        raise SystemExit(f"not in the projection: {sorted(missing)}")
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({table: len(out[table]) for table in TABLES}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
