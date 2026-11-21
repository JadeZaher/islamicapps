#!/usr/bin/env python3
"""J2: dry run of the Tier-0 exact-match rules T0-b/c/d against the corpus (changes no resolver).

T0-b registry-declared alias segments, T0-c kunya-head case fold (ابي/ابا to ابو), T0-d trailing
honorific strip. Reports surfaces newly matched, new ambiguity collisions, occurrences gained and
rows newly complete (atomic). Every match is a RULE MATCH awaiting review, never an identity.

Usage: python -B diagnostics/measure_tier0_resolver_delta.py
"""

import csv
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import diagnostic_common as common  # noqa: E402
from narrator_surface_logic import (  # noqa: E402
    fold_kunya_head, registry_alias_segments, strip_trailing_honorific,
)

JOB = "narrator-resolution"
VARIANTS = ("baseline", "t0b_alias_segments", "t0c_kunya_fold", "t0d_honorific_strip",
            "t0b_t0c", "t0b_t0c_t0d")


def main() -> None:
    started = time.time()
    regen = common.load_regen()
    extractor = common.load_extractor()
    exact_index, blocked_index = regen.build_narrator_index(str(common.REGISTRY_PATH))

    # Variant index = baseline entries + segment entries, uniqueness rule unchanged.
    owners: dict[str, set] = defaultdict(set)
    segment_origin: dict[str, list] = defaultdict(list)   # norm -> [(indx, segment_raw, name_raw)]
    registry_name: dict[str, str] = {}
    with open(common.REGISTRY_PATH, encoding="utf-8", errors="replace", newline="") as handle:
        for registry_row in csv.DictReader(handle):
            indx = (registry_row.get("scholar_indx") or "").strip()
            name = (registry_row.get("name") or "").strip()
            if not indx or not name:
                continue
            registry_name[indx] = name
            owners[regen.narrator_normalize(name)].add(indx)
            arabic = regen._extract_arabic_name(name)
            if arabic:
                owners[regen.narrator_normalize(arabic)].add(indx)
                for segment in registry_alias_segments(name):
                    seg_norm = strip_trailing_honorific(regen.narrator_normalize(segment))
                    if seg_norm:
                        owners[seg_norm].add(indx)
                        segment_origin[seg_norm].append((indx, segment, name))
    segment_index = {norm: next(iter(ids)) for norm, ids in owners.items() if len(ids) == 1}

    segment_collisions = []
    existing_made_ambiguous = []
    for norm, origins in segment_origin.items():
        ids = owners[norm]
        if len(ids) >= 2:
            entry = {"segment_normalized": norm, "scholar_indx_all": sorted(ids),
                     "was_unique_exact_before": norm in exact_index}
            (existing_made_ambiguous if norm in exact_index else segment_collisions).append(entry)

    cache: dict[str, dict] = {}

    def lookups(norm: str) -> dict:
        hit = cache.get(norm)
        if hit is not None:
            return hit
        folded = fold_kunya_head(norm)
        stripped = strip_trailing_honorific(norm)
        result = {"baseline": (exact_index.get(norm), "exact")}
        result["t0b_alias_segments"] = (
            (segment_index.get(norm), "t0b") if segment_index.get(norm) else (None, ""))
        result["t0c_kunya_fold"] = (
            (exact_index.get(norm), "exact") if exact_index.get(norm)
            else (exact_index.get(folded), "t0c") if folded != norm and exact_index.get(folded) else (None, ""))
        result["t0d_honorific_strip"] = (
            (exact_index.get(norm), "exact") if exact_index.get(norm)
            else (exact_index.get(stripped), "t0d") if stripped != norm and exact_index.get(stripped) else (None, ""))
        # Combined variants try the exact surface first, then each rule in order, on the segment index.
        for label, rules in (("t0b_t0c", ("c",)), ("t0b_t0c_t0d", ("c", "d", "cd"))):
            found = (segment_index.get(norm), "t0b") if segment_index.get(norm) else (None, "")
            if not found[0] and "c" in rules and folded != norm and segment_index.get(folded):
                found = (segment_index[folded], "t0c")
            if not found[0] and "d" in rules and stripped != norm and segment_index.get(stripped):
                found = (segment_index[stripped], "t0d")
            if not found[0] and "cd" in rules:
                both = fold_kunya_head(stripped)
                if both != norm and segment_index.get(both):
                    found = (segment_index[both], "t0c+t0d")
            result[label] = found
        # No baseline fallback: a surface that becomes ambiguous under segments is a real loss.
        result["_resolved"] = {label: bool(result[label][0]) for label in VARIANTS}
        cache[norm] = result
        return result

    occurrence_by_norm: Counter = Counter()
    tradition_by_norm: dict[str, Counter] = defaultdict(Counter)
    metrics = Counter()
    rows_complete = {label: Counter() for label in VARIANTS}
    gained_occurrences = {label: 0 for label in VARIANTS}
    lost_occurrences = {label: 0 for label in VARIANTS}
    gained_single_token = {label: 0 for label in VARIANTS}

    for _, row in common.iter_corpus_rows():
        tradition = common.clean(row.get("tradition")) or "<missing>"
        try:
            branches = extractor.extract_isnad_branches(row.get("text_ar") or "")
        except extractor.IsnadExtractionLimitError:
            continue
        if not branches:
            continue
        metrics["rows_with_extracted_chain"] += 1
        complete = {label: True for label in VARIANTS}
        for branch in branches:
            for raw in branch:
                norm = regen.narrator_normalize(raw)
                found = lookups(norm)
                baseline_hit = bool(found["baseline"][0])
                if not baseline_hit:
                    occurrence_by_norm[norm] += 1
                    tradition_by_norm[norm][tradition] += 1
                for label in VARIANTS:
                    hit = found["_resolved"][label]
                    if not hit:
                        complete[label] = False
                    if hit and not baseline_hit:
                        gained_occurrences[label] += 1
                        if " " not in norm:
                            gained_single_token[label] += 1
                    if baseline_hit and not hit:
                        lost_occurrences[label] += 1
        for label in VARIANTS:
            if complete[label]:
                rows_complete[label][tradition] += 1
                rows_complete[label]["all"] += 1

    matches = []
    for norm, count in occurrence_by_norm.items():
        found = cache[norm]
        rules = {}
        for label in VARIANTS[1:]:
            indx, rule = found[label]
            if indx:
                rules[label] = (indx, rule)
        if not rules:
            continue
        for label, (indx, rule) in rules.items():
            matches.append({
                "surface_normalized": norm,
                "variant": label,
                "rule": rule,
                "scholar_indx_candidate": indx,
                "registry_name_raw": registry_name.get(indx, ""),
                "registry_segment_origin": [o[1] for o in segment_origin.get(norm, []) if o[0] == indx][:3],
                "occurrences_in_unresolved": count,
                "by_tradition": dict(tradition_by_norm[norm]),
                "status": "rule_match_unreviewed",
            })
    matches.sort(key=lambda m: (-m["occurrences_in_unresolved"], m["surface_normalized"], m["variant"]))

    surfaces_newly = {label: len({m["surface_normalized"] for m in matches if m["variant"] == label})
                      for label in VARIANTS[1:]}
    baseline_rows = rows_complete["baseline"]["all"]
    delta = {
        "header": common.header_object(
            JOB, "python -B datasets/hadith-data/diagnostics/measure_tier0_resolver_delta.py",
            common.input_fingerprints(common.CORPUS_PATH, common.REGISTRY_PATH)),
        "policy_note": ("Diagnostic dry run. No resolver or registry is changed. Every matched row is a "
                        "rule match awaiting review; T0-b/c/d need an amendment to AGENTS.md before use."),
        "rows_with_extracted_chain": metrics["rows_with_extracted_chain"],
        "registry_alias_segments": {
            "distinct_segment_surfaces": len(segment_origin),
            "segments_unique_to_one_scholar": sum(1 for n in segment_origin if len(owners[n]) == 1),
            "segments_colliding_among_segments_or_new_names": len(segment_collisions),
            "segments_that_make_an_existing_unique_exact_surface_ambiguous": len(existing_made_ambiguous),
        },
        "per_variant": {
            label: {
                "surfaces_newly_matched": surfaces_newly.get(label, 0),
                "occurrences_gained": gained_occurrences[label],
                "occurrences_gained_single_token_surfaces": gained_single_token[label],
                "occurrences_lost_to_new_ambiguity": lost_occurrences[label],
                "rows_fully_resolvable": rows_complete[label]["all"],
                "rows_newly_complete_vs_baseline": rows_complete[label]["all"] - baseline_rows,
                "rows_fully_resolvable_by_tradition": {
                    t: rows_complete[label][t] for t in ("Sunni", "Imami", "Ibadi", "Zaydi")},
            }
            for label in VARIANTS
        },
        "top_newly_matched_surfaces": [
            {k: m[k] for k in ("surface_normalized", "variant", "scholar_indx_candidate",
                               "registry_name_raw", "occurrences_in_unresolved")}
            for m in matches[:25]
        ],
        "seconds": round(time.time() - started, 1),
    }
    out = common.output_directory(JOB)
    common.write_json(out, "tier0_delta.json", delta)
    count = common.write_jsonl(out, "tier0_matches.jsonl", matches)
    common.write_jsonl(out, "tier0_ambiguity_collisions.jsonl",
                       [{"kind": "segment_vs_segment_or_new", **e} for e in segment_collisions]
                       + [{"kind": "makes_existing_unique_exact_ambiguous", **e} for e in existing_made_ambiguous])
    print({"matches": count, "segment_collisions": len(segment_collisions),
           "existing_made_ambiguous": len(existing_made_ambiguous), "seconds": delta["seconds"]})


if __name__ == "__main__":
    main()
