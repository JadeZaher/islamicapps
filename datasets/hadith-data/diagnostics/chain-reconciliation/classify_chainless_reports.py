#!/usr/bin/env python3
"""Q3: why reports yield no extracted chain, by collection and cause (diagnostic only; never fabricates a chain).

A row is chainless when the canonical extractor returns no branch for the master `text_ar`. Each is assigned the
first matching cause below (README "No-chain classes"). Writes output/chainless_classification.json and
output/chainless_samples.jsonl. Usage: python -B classify_chainless_reports.py
"""

import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reconcile_common as rc  # noqa: E402

common = rc.common
OUTPUT = common.output_directory("chain-reconciliation/output")
COMMAND = "python -B datasets/hadith-data/diagnostics/chain-reconciliation/classify_chainless_reports.py"
SAMPLES_PER_CLASS = 8

_MARKS = re.compile(r"[ً-ٰٟـ]")
CROSS_REFERENCE = re.compile(r"^(?:\d+\s*[-ـ.]?\s*)?(?:و?بهذا الاسناد|و?بالاسناد|و?باسناده|و?بإسناده|و?بهذا الإسناد|"
                             r"و?عنه|مثله|و?بالإسناد|وعن|عنهم)")
TRANSMISSION = re.compile(r"(?<![ء-ي])(?:حدثنا|حدثني|أخبرنا|اخبرنا|أخبرني|اخبرني|أنبأنا|انبانا|سمعت|روى|روي|عن)"
                          r"(?![ء-ي])")
INFALLIBLE_OR_COMPANION_OPENING = re.compile(
    r"^(?:\d+\s*[-ـ.]?\s*)?(?:و?قال|و?سئل|و?سأل|و?روي|و?في رواية|و?كان|و?من كلام|و?من كتاب|و?من خطبة|و?قيل)")


ENGLISH_SAME_CHAIN = re.compile(r"same chain|his chain|their chain|his sources|same (?:isnad|narrators)", re.I)
ENGLISH_LINK = re.compile(r"\b(?:from|narrated|informed|reported)\b", re.I)


def strip_marks(text: str) -> str:
    return _MARKS.sub("", text or "")


def classify(row, source, k6_original, pc_chain, thaqalayn_sanad, openiti_sanad):
    text = strip_marks(row.get("text_ar") or "").strip()
    if not text:
        return "text_missing"
    if source in rc.PURE_CANON_SOURCES:
        if pc_chain:
            return "chain_in_separate_source_field_dropped_from_text_ar"
        return "source_dataset_ships_no_chain"
    if k6_original is not None and rc.parse_ids(k6_original.get("chain_indx")):
        return "source_index_present_extractor_miss"
    if thaqalayn_sanad:
        if CROSS_REFERENCE.match(text) or ENGLISH_SAME_CHAIN.search(thaqalayn_sanad):
            return "isnad_by_reference_to_previous_report"
        if len(ENGLISH_LINK.findall(thaqalayn_sanad)) >= 2:
            return "provider_english_sanad_has_chain_extractor_miss"
        if source == "Man Lā Yaḥḍuruh al-Faqīh":
            return "compiler_omitted_isnad_(Faqih_mashyakha_not_on_disk)"
        return "opens_with_attribution_no_isnad_(mursal_or_omitted)"
    if openiti_sanad:
        return "parser_sanad_present_extractor_miss"
    if len(text) < 40:
        return "text_fragment_or_truncated"
    if CROSS_REFERENCE.match(text):
        return "isnad_by_reference_to_previous_report"
    if source == "Nahj al-Balāgha":
        return "work_without_isnad_by_design"
    if INFALLIBLE_OR_COMPANION_OPENING.match(text):
        return "opens_with_attribution_no_isnad_(mursal_or_omitted)"
    if TRANSMISSION.search(text[:200]):
        return "transmission_wording_present_extractor_miss"
    return "no_transmission_wording_found"


def main() -> None:
    started = time.time()
    canon = rc.Canon()
    k6_rows, k6_sha = rc.read_k6_original()
    pure_canon = rc.read_pure_canon()
    thaqalayn = defaultdict(set)
    for _, hadith in rc.iter_thaqalayn():
        thaqalayn[(hadith.get("arabicText") or "").strip()].add((hadith.get("thaqalaynSanad") or "").strip())
    openiti = defaultdict(set)
    for path in rc.OPENITI_PARSED.values():
        for hadith in json.load(open(path, encoding="utf-8")).get("hadiths", []):
            openiti[(hadith.get("text_ar") or "").strip()].add(bool(hadith.get("sanad_detail")))

    by_source = defaultdict(Counter)
    totals = Counter()
    samples = defaultdict(list)
    rows_total = Counter()
    for row_number, row in common.iter_corpus_rows():
        tradition = common.clean(row.get("tradition"))
        source = common.clean(row.get("source"))
        rows_total[f"{tradition} | {source}"] += 1
        branches = canon.extract(row.get("text_ar"))
        if branches is None or branches:
            continue
        position = row_number - 2
        k6 = k6_rows[position] if (source in rc.K6_SOURCES and position < len(k6_rows)
                                   and k6_rows[position]["text_ar"] == row.get("text_ar")) else None
        text_key = (row.get("text_ar") or "").strip()
        chains = {(m.get("chain") or "").strip() for m in pure_canon.get(text_key, [])} - {""}
        sanads = thaqalayn.get(text_key, set()) - {""}
        label = classify(row, source, k6, len(chains) == 1, next(iter(sanads), ""), any(openiti.get(text_key, ())))
        by_source[f"{tradition} | {source}"][label] += 1
        totals[label] += 1
        if len(samples[label]) < SAMPLES_PER_CLASS and (row_number % 7 == 0 or len(samples[label]) < 2):
            samples[label].append({"class": label, "row": common.row_reference(row_number, row),
                                   "tradition": tradition, "text_ar_head": (row.get("text_ar") or "")[:220],
                                   "provider_sanad": next(iter(sanads), "")[:220],
                                   "pure_canon_chain": next(iter(chains), "")[:220]})

    recoverable = {
        "chain_in_separate_source_field_dropped_from_text_ar": "re-ETL: carry Pure Canon `chain` as the chain text",
        "source_index_present_extractor_miss": "extractor fix (K6 index shows a chain exists)",
        "provider_english_sanad_has_chain_extractor_miss": "extractor fix; provider English sanad is display evidence",
        "parser_sanad_present_extractor_miss": "extractor fix",
        "transmission_wording_present_extractor_miss": "extractor fix (sample first)",
        "isnad_by_reference_to_previous_report": "model as a reference to the previous report's chain (no new text)",
    }
    inputs = common.input_fingerprints(common.CORPUS_PATH, rc.PURE_CANON, rc.K6_ARCHIVE)
    inputs[f"{common.relative_path(rc.K6_ARCHIVE)}!{rc.K6_MEMBER}"] = k6_sha
    result = {
        "header": common.header_object("chain-reconciliation/chainless", COMMAND, inputs),
        "chainless_rows": sum(totals.values()),
        "by_class": dict(totals.most_common()),
        "by_source": {key: dict(counter.most_common()) for key, counter in sorted(by_source.items())},
        "rows_per_source": dict(sorted(rows_total.items())),
        "recovery_path_by_class": recoverable,
        "runtime_seconds": round(time.time() - started, 1),
    }
    common.write_json(OUTPUT, "chainless_classification.json", result)
    common.write_jsonl(OUTPUT, "chainless_samples.jsonl", [s for label in sorted(samples) for s in samples[label]])
    print(json.dumps({k: result[k] for k in ("chainless_rows", "by_class", "by_source")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
