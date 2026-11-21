#!/usr/bin/env python3
"""J7b: risk-stratified review queue over EXISTING accepted machine-translation candidates.

Reads the three candidate JSONLs read-only; joins `k6:<id>` to the preserved snapshot `id` and verifies the
candidate's arabic_sha256 against the snapshot Arabic. No English body is copied (hash and length only), no
override is written, nothing is accepted. Writes only under diagnostics/translation/.

Usage: python -B diagnostics/build_translation_review_queue.py
(run triage_translation_leakage.py first for the honorific-glyph cross-check)
"""

import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import diagnostic_common as common  # noqa: E402

JOB = "translation"
CANDIDATE_DIR = common.HADITH_DATA_DIR / "machine_translation_candidates"
CANDIDATE_FILES = (
    "local_lmstudio_candidates.jsonl",
    "openrouter_gemini_2_5_flash_v7_full_resilient3_2026-07-22.jsonl",
    "openrouter_gemini_2_5_flash_v8_suffix_2026-07-22.jsonl",
)
INHERITANCE_MARKERS = ("نورث", "ميراث", "يورث", "ورثه", "فرائض", "توارث")
LEGAL_MARKERS = ("حلال", "حرام", "يحل", "يحرم", "طلاق", "نكاح", "زكاه", "ربا", "القصاص", "ديه", "حدود")
LONG_ARABIC_CHARS = 4000
ACCEPTANCE_SAMPLE_MODULUS = 10      # every 10th (by hash) of the unmarked stratum is sampled first
STRATUM_ORDER = {"doctrinal_or_legal_marker": 0, "long_report": 1, "imami_terminology": 2,
                 "sampled_general": 3, "general_remainder": 4}


def classify_stratum(arabic_norm: str, arabic_chars: int, tradition: str, record_id: str) -> tuple[str, list]:
    """Risk stratum from Arabic content (pure; tested). Markers are triage hints, not judgements."""
    hits = [m for m in INHERITANCE_MARKERS + LEGAL_MARKERS if m in arabic_norm]
    if hits:
        return "doctrinal_or_legal_marker", hits
    if arabic_chars > LONG_ARABIC_CHARS:
        return "long_report", []
    if tradition == "Imami":
        return "imami_terminology", []
    bucket = int(hashlib.sha256(record_id.encode()).hexdigest(), 16) % ACCEPTANCE_SAMPLE_MODULUS
    return ("sampled_general" if bucket == 0 else "general_remainder"), []


def main() -> None:
    started = time.time()
    from classify_attribution import _norm  # noqa: PLC0415 - same normalizer as the pipeline
    snapshot = {}
    for _, row in common.iter_corpus_rows():
        if common.clean(row["tradition"]) == "Sunni":
            snapshot[common.clean(row["id"])] = (common.clean(row["tradition"]), common.clean(row["source"]),
                                                 row.get("text_ar") or "")
    glyph_ids = set()
    leak_path = common.DIAGNOSTICS_DIR / JOB / "leakage_buckets.jsonl"
    if leak_path.exists():
        for line in leak_path.read_text(encoding="utf-8").splitlines():
            entry = json.loads(line)
            if entry["bucket"] == "honorific_glyph_or_mark_only":
                glyph_ids.add(entry["id"])

    status_counts = Counter()
    per_record: dict[str, dict] = {}
    sha_mismatch = unmatched = 0
    for name in CANDIDATE_FILES:
        with open(CANDIDATE_DIR / name, encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                candidate = json.loads(line)
                status_counts[(name, candidate.get("input_issue"), candidate.get("validation_status"))] += 1
                if candidate.get("validation_status") != "accepted_machine_unreviewed":
                    continue
                record_id = candidate["record_id"]
                tradition, source, arabic = snapshot.get(record_id.split(":", 1)[-1], (None, None, None))
                if arabic is None or not record_id.startswith("k6:"):
                    unmatched += 1
                    continue
                digests = {hashlib.sha256(arabic.strip().encode()).hexdigest(),
                           hashlib.sha256(arabic.encode()).hexdigest()}
                if candidate["arabic_sha256"] not in digests:
                    sha_mismatch += 1
                    continue
                entry = per_record.setdefault(record_id, {
                    "record_id": record_id, "snapshot_id": record_id.split(":", 1)[-1], "tradition": tradition,
                    "source": source, "arabic_sha256": candidate["arabic_sha256"], "arabic_chars": len(arabic),
                    "_arabic": arabic, "candidates": []})
                text = candidate.get("text_en") or ""
                entry["candidates"].append({
                    "artifact": f"datasets/hadith-data/machine_translation_candidates/{name}", "line": line_number,
                    "prompt_version": candidate.get("prompt_version"), "input_issue": candidate.get("input_issue"),
                    "translation_model": candidate.get("translation_model"),
                    "candidate_text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                    "candidate_text_chars": len(text)})

    queue = []
    for entry in per_record.values():
        stratum, markers = classify_stratum(_norm(entry.pop("_arabic")).replace("ة", "ه"), entry["arabic_chars"],
                                            entry["tradition"], entry["record_id"])
        entry.update({
            "risk_stratum": stratum, "marker_hits": markers,
            "multiple_candidates": len(entry["candidates"]) > 1,
            "snapshot_english_leakage_was_only_honorific_glyph": entry["snapshot_id"] in glyph_ids,
            "candidate_status": "candidate_only_machine_unreviewed", "review_state": "unreviewed", "decision": None})
        queue.append(entry)
    queue.sort(key=lambda e: (STRATUM_ORDER[e["risk_stratum"]], -e["arabic_chars"], e["record_id"]))

    out = common.output_directory(JOB)
    count = common.write_jsonl(out, "review_queue.jsonl", queue)
    by_stratum = Counter(e["risk_stratum"] for e in queue)
    glyph_only = [e for e in queue if e["snapshot_english_leakage_was_only_honorific_glyph"]]
    common.write_json(out, "review_queue_summary.json", {
        "header": common.header_object(
            JOB, "python -B datasets/hadith-data/diagnostics/build_translation_review_queue.py",
            common.input_fingerprints(common.CORPUS_PATH, *[CANDIDATE_DIR / n for n in CANDIDATE_FILES])),
        "queue_records": count,
        "accepted_candidate_events_total": sum(len(e["candidates"]) for e in queue),
        "records_with_more_than_one_candidate": sum(1 for e in queue if e["multiple_candidates"]),
        "records_by_risk_stratum": dict(sorted(by_stratum.items(), key=lambda kv: STRATUM_ORDER[kv[0]])),
        "records_by_tradition": dict(Counter(e["tradition"] for e in queue)),
        "records_by_source": dict(Counter(e["source"] for e in queue).most_common()),
        "arabic_sha256_join_mismatches": sha_mismatch, "candidate_rows_without_snapshot_row": unmatched,
        "candidate_event_counts_by_file_issue_status": [
            {"file": k[0], "input_issue": k[1], "validation_status": k[2], "events": v}
            for k, v in sorted(status_counts.items(), key=lambda kv: str(kv[0]))],
        "queue_records_whose_snapshot_english_leakage_was_only_an_honorific_glyph": len(glyph_only),
        "acceptance_sampling": f"unmarked records are sampled when sha256(record_id) % {ACCEPTANCE_SAMPLE_MODULUS} == 0",
        "marker_lists_are_triage_hints_only": {"inheritance": INHERITANCE_MARKERS, "legal": LEGAL_MARKERS},
        "seconds": round(time.time() - started, 1),
    })
    print({"queue": count, "strata": dict(by_stratum), "glyph_only_queue_records": len(glyph_only),
           "sha_mismatch": sha_mismatch, "unmatched": unmatched, "seconds": round(time.time() - started, 1)})


if __name__ == "__main__":
    main()
