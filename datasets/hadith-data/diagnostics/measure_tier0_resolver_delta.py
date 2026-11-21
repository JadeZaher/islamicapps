#!/usr/bin/env python3
"""J2: dry run of the two NOT-adopted folding rules over the canonical (post-adoption) resolver.

Baseline is regen.resolve_narrator as it now stands (tier 0 exact, tier 1 adopted spelling folds, tier 2 guarded
kunya fold). The candidates measured are hamza_on_waw_and_ya_carriers and ta_marbuta_to_ha, alone and together,
looked up against the canonical tier-1 registry keys. A key with one identity is an `invariant_match`; several is
`ambiguous` and never resolves. Everything is a PROPOSED change and unreviewed. Writes only under
diagnostics/narrator-resolution/.

Usage: python -B datasets/hadith-data/diagnostics/measure_tier0_resolver_delta.py
"""

import itertools
import json
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import diagnostic_common as common  # noqa: E402
from name_invariant import (  # noqa: E402
    ADOPTED_RULE_NAMES, DIAGNOSTIC_ONLY_RULE_NAMES, compute_name_invariant, trace_name_invariant,
)

JOB = "narrator-resolution"
SAMPLE_SIZE = 100
SAMPLE_SEED = 20261121


def main() -> None:
    started = time.time()
    regen = common.load_regen()
    extractor = common.load_extractor()
    resolve, exact_index, _ = common.build_resolver(regen)
    adopted = frozenset(ADOPTED_RULE_NAMES)
    specs = [(f"only:{name}", adopted | (set(DIAGNOSTIC_ONLY_RULE_NAMES) - {name}))
             for name in DIAGNOSTIC_ONLY_RULE_NAMES]
    specs.append(("both_diagnostic_rules", adopted))
    specs = [(label, frozenset(disabled)) for label, disabled in specs]

    # Registry side: canonical tier-1 keys (formula-free, bare-name guard applied) mapped through the rule(s).
    registry_name = {}
    with open(common.REGISTRY_PATH, encoding="utf-8", errors="replace", newline="") as handle:
        import csv
        for row in csv.DictReader(handle):
            registry_name[(row.get("scholar_indx") or "").strip()] = (row.get("name") or "").strip()

    norms, norm_ids, rows = [], {}, []
    occurrences, tradition_counts, raw_example = Counter(), defaultdict(Counter), {}
    for _, row in common.iter_corpus_rows():
        tradition = common.clean(row["tradition"]) or "<missing>"
        try:
            branches = extractor.extract_isnad_branches(row.get("text_ar") or "")
        except extractor.IsnadExtractionLimitError:
            continue
        if not branches:
            continue
        ids = set()
        for branch in branches:
            for raw in branch:
                norm = regen.narrator_normalize(raw)
                number = norm_ids.get(norm)
                if number is None:
                    number = norm_ids[norm] = len(norms)
                    norms.append(norm)
                ids.add(number)
                if not resolve(norm):
                    occurrences[norm] += 1
                    tradition_counts[norm][tradition] += 1
                    raw_example.setdefault(norm, raw)
        rows.append((tradition, tuple(ids)))
    baseline_resolved = [1 if resolve(n) else 0 for n in norms]
    unresolved = [n for n in norms if not resolve(n)]

    match_of, ambiguous_of, collisions_of, index_of = {}, {}, {}, {}
    for label, disabled in specs:
        owners = defaultdict(set)
        sources = defaultdict(set)
        for folded_key, ids in exact_index.folded.items():
            key = compute_name_invariant(folded_key, disabled)
            owners[key] |= ids
            sources[key].add(folded_key)
        index_of[label] = owners
        collisions_of[label] = {k: (sorted(ids), sorted(sources[k])) for k, ids in owners.items()
                                if len(sources[k]) >= 2 and len(ids) >= 2}
        match_of[label], ambiguous_of[label] = {}, set()
        for norm in unresolved:
            if norm in exact_index.exact_ambiguous:
                continue
            key = compute_name_invariant(regen.narrator_fold_normalize(norm), disabled)
            found = owners.get(key)
            if found and len(found) == 1:
                match_of[label][norm] = next(iter(found))
            elif found:
                ambiguous_of[label].add(norm)

    all_bits = (1 << len(specs)) - 1
    masks = []
    for position, norm in enumerate(norms):
        bits = 0
        for bit, (label, _) in enumerate(specs):
            if baseline_resolved[position] or norm in match_of[label]:
                bits |= 1 << bit
        masks.append(bits)
    baseline_complete, complete = Counter(), {label: Counter() for label, _ in specs}
    for tradition, ids in rows:
        bits, base_ok = all_bits, True
        for number in ids:
            bits &= masks[number]
            base_ok = base_ok and bool(baseline_resolved[number])
        baseline_complete[tradition] += base_ok
        baseline_complete["all"] += base_ok
        for bit, (label, _) in enumerate(specs):
            if bits >> bit & 1:
                complete[label][tradition] += 1
                complete[label]["all"] += 1

    results = {}
    for label, _ in specs:
        by_tradition = Counter()
        for n in match_of[label]:
            by_tradition.update(tradition_counts[n])
        top = sorted(match_of[label], key=lambda n: -occurrences[n])[:10]
        results[label] = {
            "surfaces_newly_matched": len(match_of[label]),
            "ambiguous_surfaces": len(ambiguous_of[label]),
            "unresolved_occurrences_gained": sum(occurrences[n] for n in match_of[label]),
            "occurrences_gained_by_tradition": dict(by_tradition),
            "rows_fully_resolvable": complete[label]["all"],
            "rows_newly_complete_vs_new_baseline": complete[label]["all"] - baseline_complete["all"],
            "rows_fully_resolvable_by_tradition": {t: complete[label][t] for t in ("Sunni", "Imami", "Ibadi", "Zaydi")},
            "registry_merge_collision_keys": len(collisions_of[label]),
            "top_matches": [{"surface_normalized": n, "registry_scholar_indx": match_of[label][n],
                             "registry_name_raw": registry_name[match_of[label][n]], "occurrences": occurrences[n]}
                            for n in top],
        }
    full_label, full_disabled = specs[-1]
    matches = []
    for norm, indx in sorted(match_of[full_label].items(), key=lambda kv: (-occurrences[kv[0]], kv[0])):
        folded = regen.narrator_fold_normalize(norm)
        key, trace = trace_name_invariant(folded, full_disabled)
        matches.append({
            "surface_as_written": raw_example[norm], "surface_normalized": norm, "invariant_key": key,
            "scholar_indx_candidate": indx, "registry_name_raw": registry_name[indx],
            "rules_fired_on_surface": [t[0] for t in trace], "occurrences": occurrences[norm],
            "by_tradition": dict(tradition_counts[norm]), "status": "invariant_match_unreviewed"})
    sample = random.Random(SAMPLE_SEED).sample(matches, min(SAMPLE_SIZE, len(matches)))
    sample.sort(key=lambda m: -m["occurrences"])
    collision_rows = [{"invariant_key": k, "scholar_indx": ids, "registry_names": [registry_name[i] for i in ids],
                       "distinct_tier1_keys": keys, "status": "collision_unreviewed"}
                      for k, (ids, keys) in collisions_of[full_label].items()]
    pairs = sum(len(list(itertools.combinations(c["scholar_indx"], 2))) for c in collision_rows)

    out = common.output_directory(JOB)
    match_count = common.write_jsonl(out, "name_invariant_matches.jsonl", matches)
    sample_count = common.write_jsonl(out, "name_invariant_spotcheck_sample.jsonl", sample)
    common.write_jsonl(out, "name_invariant_registry_collisions.jsonl", collision_rows)
    common.write_json(out, "name_invariant_delta.json", {
        "header": common.header_object(
            JOB, "python -B datasets/hadith-data/diagnostics/measure_tier0_resolver_delta.py",
            common.input_fingerprints(common.CORPUS_PATH, common.REGISTRY_PATH)),
        "policy_note": ("The adopted rules are in the canonical resolver. This measures only the two rules that were not "
                        "adopted, over the canonical baseline. Proposed and unreviewed."),
        "rules_measured": list(DIAGNOSTIC_ONLY_RULE_NAMES),
        "baseline_canonical": {"rows_fully_resolvable": baseline_complete["all"], "by_tradition": {
            t: baseline_complete[t] for t in ("Sunni", "Imami", "Ibadi", "Zaydi")},
            "distinct_unresolved_surfaces": len(unresolved), "unresolved_occurrences": sum(occurrences.values())},
        "losses": {"note": "invariant lookup only runs on surfaces the canonical resolver left unresolved",
                   "baseline_resolved_surfaces_changed": 0},
        "variants": results,
        "matches_at_both_rules": match_count, "colliding_identity_pairs_at_both_rules": pairs,
        "seconds": round(time.time() - started, 1),
    })
    print(json.dumps({"matches": match_count, "sample": sample_count, "collision_pairs": pairs,
                      "baseline_rows": baseline_complete["all"], "seconds": round(time.time() - started, 1)}))


if __name__ == "__main__":
    main()
