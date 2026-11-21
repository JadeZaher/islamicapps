#!/usr/bin/env python3
"""J5: stratified samples of suspicious unresolved surfaces for extractor-regression gold-set expansion.

Needs J1 output. Picks surfaces deterministically (sha256 order) per stratum, attaches the raw Arabic span
with context from the source row, and counts heuristic noise hints over the whole census. It does not touch
__tests__/fixtures. Writes only under diagnostics/extractor-noise/.

Usage: python -B diagnostics/sample_extractor_noise.py
"""

import gzip
import hashlib
import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import diagnostic_common as common  # noqa: E402

JOB = "extractor-noise"
QUOTAS = {"relational_or_fragment": 40, "other_multi_token_singleton": 100,
          "collective_or_anonymous_singleton": 30, "single_ism_or_laqab_singleton": 30}
VERB_HINT = re.compile(r"(?<![ء-ي])(?:حدثنا|حدثني|اخبرنا|اخبرني|انبانا|سمعت|قال|قالت|يقول|روى|عن)(?![ء-ي])")
LONG_TOKENS = 8
CONTEXT_CHARS = 70


def noise_hints(norm: str) -> list[str]:
    """Cheap heuristics that suggest a mis-segmented span (hints only, not labels)."""
    hints = []
    tokens = norm.split()
    if VERB_HINT.search(norm):
        hints.append("contains_transmission_or_speech_word")
    if len(tokens) >= LONG_TOKENS:
        hints.append(f"token_count_ge_{LONG_TOKENS}")
    if re.search(r"[0-9A-Za-z]", norm):
        hints.append("contains_digit_or_latin")
    if len(norm) <= 2:
        hints.append("one_or_two_characters")
    return hints


def stratum_of(entry: dict) -> str | None:
    category, singleton = entry["category"], entry["occurrences"] == 1
    if category == "relational_or_fragment":
        return category
    if singleton and category in ("other_multi_token", "collective_or_anonymous", "single_ism_or_laqab"):
        return f"{category}_singleton"
    return None


def main() -> None:
    started = time.time()
    census_path = common.DIAGNOSTICS_DIR / "narrator-resolution" / "surface_census.jsonl.gz"
    if not census_path.exists():
        raise SystemExit("run build_narrator_surface_census.py (J1) first")
    pools = defaultdict(list)
    hint_surfaces, hint_occurrences = Counter(), Counter()
    total_surfaces = Counter()
    with gzip.open(census_path, "rt", encoding="utf-8") as handle:
        for line in handle:
            entry = json.loads(line)
            hints = noise_hints(entry["surface_normalized"])
            total_surfaces[entry["category"]] += 1
            for hint in hints:
                hint_surfaces[(entry["category"], hint)] += 1
                hint_occurrences[(entry["category"], hint)] += entry["occurrences"]
            stratum = stratum_of(entry)
            if stratum:
                pools[stratum].append(entry)
    chosen = []
    for stratum, quota in QUOTAS.items():
        ordered = sorted(pools[stratum], key=lambda e: hashlib.sha256(e["surface_normalized"].encode()).hexdigest())
        if stratum == "relational_or_fragment":     # every distinct fragment first, then by frequency
            ordered = sorted(pools[stratum], key=lambda e: -e["occurrences"])
        chosen += [(stratum, e) for e in ordered[:quota]]
    wanted = {e["example_rows"][0]["line"]: (stratum, e) for stratum, e in chosen if e["example_rows"]}
    samples = []
    for row_number, row in common.iter_corpus_rows():
        if row_number not in wanted:
            continue
        stratum, entry = wanted[row_number]
        text = row.get("text_ar") or ""
        raw = entry["raw_examples"][0] if entry["raw_examples"] else ""
        at = text.find(raw) if raw else -1
        samples.append({
            "stratum": stratum, **entry["example_rows"][0], "tradition": common.clean(row["tradition"]),
            "surface_normalized": entry["surface_normalized"], "raw_surface": raw,
            "occurrences_in_corpus": entry["occurrences"], "noise_hints": noise_hints(entry["surface_normalized"]),
            "raw_span_found_in_text_ar": at >= 0,
            "context_ar": text[max(0, at - CONTEXT_CHARS): at + len(raw) + CONTEXT_CHARS] if at >= 0 else text[:2 * CONTEXT_CHARS],
            "status": "unreviewed_noise_candidate"})
    samples.sort(key=lambda s: (s["stratum"], -s["occurrences_in_corpus"], s["surface_normalized"]))
    out = common.output_directory(JOB)
    count = common.write_jsonl(out, "samples.jsonl", samples)
    common.write_json(out, "summary.json", {
        "header": common.header_object(
            JOB, "python -B datasets/hadith-data/diagnostics/sample_extractor_noise.py",
            common.input_fingerprints(census_path)),
        "samples": count, "quotas": QUOTAS,
        "samples_by_stratum": dict(Counter(s["stratum"] for s in samples)),
        "samples_whose_raw_span_was_found_in_text_ar": sum(1 for s in samples if s["raw_span_found_in_text_ar"]),
        "census_surfaces_by_category": dict(total_surfaces),
        "noise_hint_surfaces_by_category_and_hint": {f"{c} | {h}": n for (c, h), n in sorted(hint_surfaces.items())},
        "noise_hint_occurrences_by_category_and_hint": {f"{c} | {h}": n for (c, h), n in sorted(hint_occurrences.items())},
        "seconds": round(time.time() - started, 1),
    })
    print({"samples": count, "seconds": round(time.time() - started, 1)})


if __name__ == "__main__":
    main()
