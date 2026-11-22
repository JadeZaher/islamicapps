#!/usr/bin/env python3
"""OpenITI report structure sidecar: Arabic chain span, chain inheritance, split confidence, source notes.

One row per report of the three parsed OpenITI works (al-Rabi, Musnad Zayd, Sahifat al-Rida), keyed by `record_id`
and bound to the SHA-256 of the unified CSV's exact `text_ar`. `text_ar` is never altered; every string here is a
verbatim span or note the parser verified against its source (datasets/parse_openiti.py `verification`).
See reconciled/README.md and src/db/AGENTS.md §OpenITI extraction fields.

Usage: python -B datasets/hadith-data/reconciled/build_openiti_extraction_sidecar.py [--input <unified csv.gz>]
"""

import argparse
import csv
import gzip
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sidecar_io as io_  # noqa: E402

common = io_.common
HADITH_DATA = io_.HADITH_DATA_DIR
DEFAULT_INPUT = HADITH_DATA / "development" / "incomplete-curation" / "all_hadiths_unified.incomplete.csv.gz"
PARSED = {
    "ibadi": HADITH_DATA / "ibadi-hadith" / "parsed_hadiths.json",
    "zaydi": HADITH_DATA / "zaydi-hadith" / "parsed_hadiths.json",
    "rida": HADITH_DATA / "rida-hadith" / "parsed_hadiths.json",
}
SOURCE_CODE = "OITI"
# The parser's commentary kinds mapped to who wrote the note (the page labels each kind and credits the source).
NOTE_KIND = {"rabi_comment": "compiler_comment", "gloss": "compiler_comment", "arranger_note": "arranger_note", "note": "note"}


def record_id_of(hadith: dict) -> tuple[str, str]:
    source_record_id = "|".join(str(hadith.get(key) or "").strip() for key in ("id", "hadith_no", "page_ref"))
    return f"openiti:{str(hadith['tradition']).strip().lower()}:{source_record_id}", source_record_id


def unified_openiti_texts(path: Path) -> dict[str, str]:
    csv.field_size_limit(1 << 30)
    texts: dict[str, str] = {}
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["record_id"].startswith("openiti:"):
                texts[row["record_id"]] = row["text_ar"]
    return texts


def source_notes(hadith: dict) -> list[dict]:
    commentary, kinds = hadith.get("commentary") or [], hadith.get("commentary_kinds") or []
    if isinstance(commentary, str) or len(commentary) != len(kinds):
        raise ValueError(f"{hadith['id']}: commentary and commentary_kinds disagree")
    notes = [{"kind": NOTE_KIND[kind], "text_ar": text} for text, kind in zip(commentary, kinds)]
    notes += [{"kind": "editor_footnote", "text_ar": text} for text in hadith.get("footnotes") or []]
    return notes


def build_rows(unified_texts: dict[str, str]) -> tuple[list[dict], Counter]:
    rows, counts = [], Counter()
    for tradition, path in PARSED.items():
        hadiths = json.loads(path.read_text(encoding="utf-8"))["hadiths"]
        record_ids = [record_id_of(h)[0] for h in hadiths]
        if len(set(record_ids)) != len(record_ids):
            raise ValueError(f"{tradition}: record ids are not unique")
        for position, hadith in enumerate(hadiths):
            record_id, source_record_id = record_id_of(hadith)
            text_ar = unified_texts.get(record_id)
            if text_ar is None:
                raise ValueError(f"{record_id}: not in the unified CSV; rebuild it first (regen_unified_csvs.py)")
            if text_ar != hadith["text_ar"]:
                raise ValueError(f"{record_id}: unified text_ar differs from the parsed text_ar")
            inherits = None
            if hadith.get("sanad_inherits_from"):
                # The previous report of the work with that id (rabi_0387 is printed twice).
                earlier = [i for i in range(position) if hadiths[i]["id"] == hadith["sanad_inherits_from"]]
                if not earlier:
                    raise ValueError(f"{record_id}: inherits from {hadith['sanad_inherits_from']}, which does not precede it")
                inherits = record_ids[earlier[-1]]
            notes = source_notes(hadith)
            counts[f"{tradition}:{hadith['split_confidence']}"] += 1
            counts[f"{tradition}:notes"] += len(notes)
            counts[f"{tradition}:inherits"] += inherits is not None
            rows.append({
                "record_id": record_id, "source_record_id": source_record_id,
                "text_ar_sha256": io_.sha256_text(text_ar),
                "sanad_ar": hadith.get("sanad_ar") or None,
                "sanad_inherits_from_record_id": inherits,
                "split_confidence": hadith["split_confidence"], "split_kind": hadith["split_kind"],
                "source_notes": notes, "source_code": SOURCE_CODE, "review_state": "unreviewed",
            })
    rows.sort(key=lambda row: row["record_id"])
    return rows, counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    args = parser.parse_args()
    rows, counts = build_rows(unified_openiti_texts(args.input.resolve()))
    output = io_.write_jsonl_gz("openiti_extraction.jsonl.gz", rows)
    io_.write_manifest("openiti_extraction.manifest.json", {
        "artifact": "openiti_extraction",
        "status": "sidecar_unreviewed_not_a_release_input",
        "meaning": "Arabic chain span, chain inheritance, split confidence and source notes of OpenITI reports, "
                   "bound to the exact Arabic of the unified CSV",
        "command": "python -B datasets/hadith-data/reconciled/build_openiti_extraction_sidecar.py",
        "inputs_sha256": common.input_fingerprints(args.input.resolve(), *PARSED.values()),
        "code_sha256": io_.code_fingerprints(Path(__file__).resolve(), io_.RECONCILED_DIR / "sidecar_io.py"),
        "outputs": [output],
        "counts": {"rows": len(rows), **dict(sorted(counts.items()))},
    })
    print(output)


if __name__ == "__main__":
    main()
