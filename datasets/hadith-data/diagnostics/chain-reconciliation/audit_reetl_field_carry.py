#!/usr/bin/env python3
"""Q4: which chain-related source fields survive into the committed master, per source (diagnostic only).

Compares each original source file with the master row it became (joins as in the other jobs: K6 by file position
plus exact Arabic; Pure Canon, Thaqalayn and OpenITI by exact stripped Arabic with a unique match).
Writes output/reetl_field_carry.json. Usage: python -B audit_reetl_field_carry.py
"""

import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reconcile_common as rc  # noqa: E402

common = rc.common
OUTPUT = common.output_directory("chain-reconciliation/output")
COMMAND = "python -B datasets/hadith-data/diagnostics/chain-reconciliation/audit_reetl_field_carry.py"


def main() -> None:
    started = time.time()
    k6_rows, k6_sha = rc.read_k6_original()
    pure_canon = rc.read_pure_canon()
    thaqalayn = defaultdict(list)
    for file_id, hadith in rc.iter_thaqalayn():
        thaqalayn[(hadith.get("arabicText") or "").strip()].append(hadith)
    openiti = defaultdict(list)
    for tradition, path in rc.OPENITI_PARSED.items():
        for hadith in json.load(open(path, encoding="utf-8")).get("hadiths", []):
            openiti[(hadith.get("text_ar") or "").strip()].append(hadith)

    carry = defaultdict(Counter)
    for row_number, row in common.iter_corpus_rows():
        source = common.clean(row.get("source"))
        tradition = common.clean(row.get("tradition"))
        text = (row.get("text_ar") or "").strip()
        master_ids = rc.parse_ids(row.get("chain_indx"))
        if source in rc.K6_SOURCES:
            stats = carry["K6 (sunnah.com/K6 CSV)"]
            original = k6_rows[row_number - 2] if row_number - 2 < len(k6_rows) else None
            stats["rows"] += 1
            if original is None or original["text_ar"] != row.get("text_ar"):
                stats["join_failed"] += 1
                continue
            source_ids = rc.parse_ids(original["chain_indx"])
            stats["source_chain_indx_present"] += bool(source_ids)
            stats["source_chain_indx_ids"] += len(source_ids)
            stats["master_chain_indx_equal_source"] += bool(source_ids) and master_ids == source_ids
            stats["master_chain_indx_present_but_different"] += bool(master_ids) and master_ids != source_ids
            stats["master_chain_indx_empty_while_source_present"] += bool(source_ids) and not master_ids
            stats["master_ids_kept_from_source"] += len(set(master_ids) & set(source_ids))
        elif source in rc.PURE_CANON_SOURCES:
            stats = carry[f"Pure Canon {source}"]
            stats["rows"] += 1
            matches = pure_canon.get(text, [])
            chains = {(m.get("chain") or "").strip() for m in matches}
            if len(chains) != 1:
                stats["join_ambiguous_or_failed"] += 1
                continue
            chain = next(iter(chains))
            stats["source_chain_field_present"] += bool(chain)
            stats["master_text_ar_contains_source_chain"] += bool(chain) and chain in text
            stats["master_sanad_column_nonempty"] += bool(common.clean(row.get("sanad")))
            stats["source_shelf_no_present"] += bool(str(matches[0].get("shelf_no") or "").strip())
        elif tradition == "Imami" and thaqalayn.get(text):
            stats = carry["Thaqalayn V2"]
            stats["rows"] += 1
            hadith = thaqalayn[text][0]
            stats["join_unique"] += len(thaqalayn[text]) == 1
            sanad = (hadith.get("thaqalaynSanad") or "").strip()
            stats["provider_english_sanad_present"] += bool(sanad)
            stats["master_sanad_equals_provider_english_sanad"] += bool(sanad) and common.clean(row.get("sanad")) == sanad
            stats["provider_matn_present"] += bool((hadith.get("thaqalaynMatn") or "").strip())
            stats["master_matn_en_nonempty"] += bool(common.clean(row.get("matn_en")))
            stats["provider_gradingsFull_present"] += bool(hadith.get("gradingsFull"))
            stats["master_gradings_full_nonempty"] += bool(common.clean(row.get("gradings_full")))
            stats["master_chain_indx_present"] += bool(master_ids)
        elif openiti.get(text):
            stats = carry[f"OpenITI {tradition}"]
            stats["rows"] += 1
            hadith = openiti[text][0]
            stats["parser_sanad_detail_present"] += bool(hadith.get("sanad_detail"))
            stats["parser_sanad_detail_tabaqah_present"] += any(d.get("tabaqah") for d in hadith.get("sanad_detail") or [])
            stats["master_sanad_nonempty"] += bool(common.clean(row.get("sanad")))
            stats["parser_page_ref_present"] += bool(str(hadith.get("page_ref") or "").strip())
            stats["master_page_ref_nonempty"] += bool(common.clean(row.get("page_ref")))
        else:
            carry[f"unjoined {tradition} | {source}"]["rows"] += 1

    inputs = common.input_fingerprints(common.CORPUS_PATH, rc.PURE_CANON, rc.K6_ARCHIVE)
    inputs[f"{common.relative_path(rc.K6_ARCHIVE)}!{rc.K6_MEMBER}"] = k6_sha
    result = {"header": common.header_object("chain-reconciliation/reetl-field-carry", COMMAND, inputs),
              "carry": {key: dict(value) for key, value in sorted(carry.items())},
              "runtime_seconds": round(time.time() - started, 1)}
    common.write_json(OUTPUT, "reetl_field_carry.json", result)
    print(json.dumps(result["carry"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
