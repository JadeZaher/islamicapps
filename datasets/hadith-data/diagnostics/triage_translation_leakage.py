#!/usr/bin/env python3
"""J7: classify every English cell the strict translation gate flags, by kind of Arabic-script leakage.

Recomputes regen.translation_issue over the preserved snapshot (the curation backlog is OS-locked).
Buckets for issue == arabic_leakage: honorific_glyph_or_mark_only, names_or_terms_only,
partial_untranslated, fully_arabic. Writes only under diagnostics/translation/. Offline, no model calls.

Usage: python -B diagnostics/triage_translation_leakage.py
"""

import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import diagnostic_common as common  # noqa: E402

JOB = "translation"
ARABIC_LETTER = re.compile(r"[ء-يٱ-ە]")
ARABIC_SCRIPT = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]")
LATIN_LETTER = re.compile(r"[A-Za-z]")
ARABIC_RUN = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]+(?:[\s،,.;:()\[\]\"'-]+[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]+)*")
NAMES_OR_TERMS_MAX_WORDS = 3
PARTIAL_MIN_RATIO = 0.10
FULLY_ARABIC_MIN_RATIO = 0.50


def classify_leakage(text_en: str) -> dict:
    """Bucket one English cell that contains Arabic-script characters (pure; tested)."""
    arabic_letters = len(ARABIC_LETTER.findall(text_en))
    latin_letters = len(LATIN_LETTER.findall(text_en))
    total = arabic_letters + latin_letters
    ratio = arabic_letters / total if total else 1.0
    runs = [run for run in ARABIC_RUN.findall(text_en)]
    longest = max((len(run.split()) for run in runs), default=0)
    if arabic_letters == 0:
        bucket = "honorific_glyph_or_mark_only"
    elif ratio >= FULLY_ARABIC_MIN_RATIO:
        bucket = "fully_arabic"
    elif longest > NAMES_OR_TERMS_MAX_WORDS or ratio >= PARTIAL_MIN_RATIO:
        bucket = "partial_untranslated"
    else:
        bucket = "names_or_terms_only"
    return {"bucket": bucket, "arabic_letter_ratio": round(ratio, 4), "arabic_letters": arabic_letters,
            "latin_letters": latin_letters, "arabic_runs": len(runs), "longest_arabic_run_words": longest,
            "first_arabic_span": (runs[0][:60] if runs else "")}


def main() -> None:
    started = time.time()
    regen = common.load_regen()
    issues = Counter()
    issue_by_tradition = defaultdict(Counter)
    bucket_by_tradition = defaultdict(Counter)
    bucket_by_source = defaultdict(Counter)
    buckets = Counter()
    other_issue_rows = []
    leakage_rows = []
    for row_number, row in common.iter_corpus_rows():
        tradition, source = common.clean(row["tradition"]), common.clean(row["source"])
        issue = regen.translation_issue(row.get("text_en") or "", row.get("text_ar") or "")
        issues[issue or "ok"] += 1
        issue_by_tradition[tradition][issue or "ok"] += 1
        if issue == "arabic_leakage":
            detail = classify_leakage(row.get("text_en") or "")
            buckets[detail["bucket"]] += 1
            bucket_by_tradition[tradition][detail["bucket"]] += 1
            bucket_by_source[f"{tradition} | {source}"][detail["bucket"]] += 1
            leakage_rows.append({**common.row_reference(row_number, row), "tradition": tradition,
                                 "issue": issue, **detail, "status": "triage_label_unreviewed"})
        elif issue:
            other_issue_rows.append({**common.row_reference(row_number, row), "tradition": tradition,
                                     "issue": issue, "text_en_chars": len(row.get("text_en") or ""),
                                     "text_ar_chars": len(row.get("text_ar") or "")})
    out = common.output_directory(JOB)
    leak_count = common.write_jsonl(out, "leakage_buckets.jsonl", leakage_rows)
    other_count = common.write_jsonl(out, "other_translation_issues.jsonl", other_issue_rows)
    common.write_json(out, "summary.json", {
        "header": common.header_object(
            JOB, "python -B datasets/hadith-data/diagnostics/triage_translation_leakage.py",
            common.input_fingerprints(common.CORPUS_PATH)),
        "scope_note": "Snapshot (legacy 26-column master) recomputation; the 29,915 classical recoveries have no English in the snapshot.",
        "translation_issue_counts": dict(sorted(issues.items(), key=lambda kv: -kv[1])),
        "issue_by_tradition": {t: dict(c) for t, c in sorted(issue_by_tradition.items())},
        "arabic_leakage_buckets": dict(sorted(buckets.items(), key=lambda kv: -kv[1])),
        "arabic_leakage_buckets_by_tradition": {t: dict(c) for t, c in sorted(bucket_by_tradition.items())},
        "arabic_leakage_buckets_by_collection": {k: dict(c) for k, c in sorted(bucket_by_source.items())},
        "bucket_definitions": {
            "honorific_glyph_or_mark_only": "Arabic-script code points but no Arabic letters (e.g. the salla-llahu ligature U+FDFA)",
            "names_or_terms_only": f"Arabic letter ratio < {PARTIAL_MIN_RATIO} and every Arabic run <= {NAMES_OR_TERMS_MAX_WORDS} words",
            "partial_untranslated": f"a run of > {NAMES_OR_TERMS_MAX_WORDS} Arabic words, or ratio >= {PARTIAL_MIN_RATIO}",
            "fully_arabic": f"Arabic letter ratio >= {FULLY_ARABIC_MIN_RATIO}",
        },
        "rows_written": {"leakage_buckets.jsonl": leak_count, "other_translation_issues.jsonl": other_count},
        "seconds": round(time.time() - started, 1),
    })
    print({"leakage": leak_count, "other": other_count, "buckets": dict(buckets), "seconds": round(time.time() - started, 1)})


if __name__ == "__main__":
    main()
