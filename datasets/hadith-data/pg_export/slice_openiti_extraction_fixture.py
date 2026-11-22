"""Cut the OpenITI extraction flow-test fixture: real reports copied from a canonical projection.

Usage: python slice_openiti_extraction_fixture.py --projection <dir> --catalog <catalog.json> --output <fixture.json>
       --hadith <id> [--hadith <id> ...] --retired-unified <old unified csv.gz> --retired <record_id> [...]
`hadiths` are the chosen projection rows typed from the live catalog (the new columns included). `retired` are real rows
of the previous load that the new projection no longer carries (an absorbed report), read from the old unified CSV.
Deterministic.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path

csv.field_size_limit(2**31 - 1)


def typed(value: str, data_type: str):
    if value == "":
        return None
    if data_type in ("integer", "bigint", "smallint"):
        return int(value)
    if data_type in ("real", "double precision", "numeric"):
        return float(value)
    if data_type == "boolean":
        return value == "true"
    if data_type in ("json", "jsonb"):
        return json.loads(value)
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--projection", required=True, type=Path)
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--hadith", action="append", required=True)
    parser.add_argument("--retired-unified", type=Path)
    parser.add_argument("--retired", action="append", default=[])
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    manifest = json.loads((args.projection / "canonical" / "manifest.json").read_text(encoding="utf-8"))
    types = {column["name"]: column["dataType"] for column in catalog["hadiths"]}
    chosen = set(args.hadith)
    hadiths = []
    with (args.projection / "canonical" / "hadiths.csv").open("rt", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["id"] in chosen:
                hadiths.append({name: typed(value, types[name]) for name, value in row.items()})
    missing = chosen - {row["id"] for row in hadiths}
    if missing:
        raise SystemExit(f"not in the projection: {sorted(missing)}")
    retired = []
    if args.retired:
        wanted = set(args.retired)
        with gzip.open(args.retired_unified, "rt", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                if row["record_id"] in wanted:
                    retired.append({
                        "id": f"hadith:{row['record_id']}", "record_id": row["record_id"],
                        "source_record_id": row["source_record_id"], "hadith_no": row["hadith_no"],
                        "page_ref": row["page_ref"], "text_ar": row["text_ar"],
                        "arabic_sha256": hashlib.sha256(row["text_ar"].encode("utf-8")).hexdigest(),
                        "provenance": row["provenance_source"],
                    })
        if len(retired) != len(wanted):
            raise SystemExit("a retired record is not in the old unified CSV")
    out = {
        "generated_from": {"projection_content_sha256": manifest["content_sha256"],
                           "projection_version": manifest["projection_version"]},
        "hadiths": sorted(hadiths, key=lambda row: row["id"]),
        "retired": sorted(retired, key=lambda row: row["id"]),
    }
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{len(hadiths)} reports, {len(retired)} retired -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
