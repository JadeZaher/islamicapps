#!/usr/bin/env python3
"""J2: dry run of a name-invariant lookup against the corpus (changes no resolver).

Lookup order is unchanged exact-normalized match first, invariant key second, so no currently resolved surface can
change. A key that maps to exactly one registry identity is an `invariant_match`; a key shared by several is
`ambiguous` and never resolves. Each folding rule is measured alone and cumulatively. Everything is a PROPOSED
policy change and unreviewed; no identity is asserted. Writes only under diagnostics/narrator-resolution/.

Usage: python -B datasets/hadith-data/diagnostics/measure_tier0_resolver_delta.py
"""

import csv
import itertools
import json
import random
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import diagnostic_common as common  # noqa: E402
from narrator_surface_logic import categorize_surface  # noqa: E402
from name_invariant import INVARIANT_RULES, RULE_NAMES, compute_name_invariant, trace_name_invariant  # noqa: E402

JOB = "narrator-resolution"
SPECIFIC_CATEGORIES = {"ism_nasab", "other_multi_token"}   # guard: not kunya-only, bare ism or bare nasab
SAMPLE_SIZE = 100
SAMPLE_SEED = 20261121
LATIN = re.compile(r"[A-Za-z]")


def variant_specs() -> list[tuple[str, frozenset, bool]]:
    """(label, disabled rules, specificity guard): one rule alone, cumulative prefixes, guarded cumulative."""
    specs = []
    for rule in RULE_NAMES:
        specs.append((f"only:{rule}", frozenset(set(RULE_NAMES) - {rule}), False))
    for count in range(1, len(RULE_NAMES) + 1):
        specs.append((f"cumulative_{count}:{RULE_NAMES[count - 1]}", frozenset(RULE_NAMES[count:]), False))
    for count in range(1, len(RULE_NAMES) + 1):
        specs.append((f"guarded_cumulative_{count}:{RULE_NAMES[count - 1]}", frozenset(RULE_NAMES[count:]), True))
    return specs


def main() -> None:
    started = time.time()
    regen = common.load_regen()
    extractor = common.load_extractor()
    exact_index, _ = regen.build_narrator_index(str(common.REGISTRY_PATH))
    base = regen.narrator_normalize

    registry = []   # (indx, raw name, arabic name, base-normalized arabic name)
    with open(common.REGISTRY_PATH, encoding="utf-8", errors="replace", newline="") as handle:
        for row in csv.DictReader(handle):
            indx, name = (row.get("scholar_indx") or "").strip(), (row.get("name") or "").strip()
            arabic = regen._extract_arabic_name(name) if indx and name else ""
            if arabic:
                registry.append((indx, name, arabic, base(arabic)))
    registry_name = {r[0]: r[1] for r in registry}

    # Pass 1: corpus rows as tuples of distinct norms; counts and first raw example for unresolved norms.
    norm_ids: dict[str, int] = {}
    norms: list[str] = []
    rows = []
    occurrences, tradition_counts, raw_example = Counter(), defaultdict(Counter), {}
    latin_surface_norms = set()
    resolved_key_has_latin = 0
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
                norm = base(raw)
                if LATIN.search(norm):
                    latin_surface_norms.add(norm)
                number = norm_ids.get(norm)
                if number is None:
                    number = norm_ids[norm] = len(norms)
                    norms.append(norm)
                ids.add(number)
                if exact_index.get(norm):
                    resolved_key_has_latin += bool(LATIN.search(norm))
                else:
                    occurrences[norm] += 1
                    tradition_counts[norm][tradition] += 1
                    raw_example.setdefault(norm, raw)
        rows.append((tradition, tuple(ids)))
    unresolved = [n for n in norms if not exact_index.get(n)]
    baseline_resolved_mask = [1 if exact_index.get(n) else 0 for n in norms]

    specs = variant_specs()
    index_by_variant, collisions_by_variant = {}, {}
    for label, disabled, _ in specs:
        owners = defaultdict(set)
        base_names = defaultdict(set)
        for indx, _, _, arabic_norm in registry:
            key = compute_name_invariant(arabic_norm, disabled)
            if key:
                owners[key].add(indx)
                base_names[key].add(" ".join(arabic_norm.split()))
        index_by_variant[label] = owners
        # merge collisions: distinct identities AND distinct baseline names share one key (created by the rules)
        collisions_by_variant[label] = {k: (sorted(ids), sorted(base_names[k])) for k, ids in owners.items()
                                        if len(ids) >= 2 and len(base_names[k]) >= 2}

    match_of: dict[str, dict] = {label: {} for label, _, _g in specs}      # norm -> indx for invariant_match
    ambiguous_of: dict[str, set] = {label: set() for label, _, _g in specs}
    for label, disabled, guarded in specs:
        owners = index_by_variant[label]
        for norm in unresolved:
            if guarded and categorize_surface(norm) not in SPECIFIC_CATEGORIES:
                continue
            key = compute_name_invariant(norm, disabled)
            found = owners.get(key) if key else None
            if found and len(found) == 1:
                match_of[label][norm] = next(iter(found))
            elif found:
                ambiguous_of[label].add(norm)

    results = {}
    baseline_complete = Counter()
    complete = {label: Counter() for label, _, _g in specs}
    masks = []
    for position, norm in enumerate(norms):
        bits = 0
        for bit, (label, _, _g) in enumerate(specs):
            if baseline_resolved_mask[position] or norm in match_of[label]:
                bits |= 1 << bit
        masks.append(bits)
    all_bits = (1 << len(specs)) - 1
    for tradition, ids in rows:
        row_bits = all_bits
        base_ok = True
        for number in ids:
            row_bits &= masks[number]
            base_ok = base_ok and bool(baseline_resolved_mask[number])
        if base_ok:
            baseline_complete[tradition] += 1
            baseline_complete["all"] += 1
        for bit, (label, _, _g) in enumerate(specs):
            if row_bits >> bit & 1:
                complete[label][tradition] += 1
                complete[label]["all"] += 1
    losses = 0
    for label, _, _g in specs:
        losses += max(0, baseline_complete["all"] - complete[label]["all"])
    # Occurrence-level loss check: every baseline-resolved norm keeps its exact id by construction; verify mask.
    surface_losses = sum(1 for position in range(len(norms))
                         if baseline_resolved_mask[position] and not (masks[position] == all_bits))

    for label, _, _g in specs:
        gained = sum(occurrences[n] for n in match_of[label])
        by_tradition = Counter()
        for n in match_of[label]:
            by_tradition.update(tradition_counts[n])
        top = sorted(match_of[label], key=lambda n: -occurrences[n])[:10]
        collisions = collisions_by_variant[label]
        results[label] = {
            "surfaces_newly_matched": len(match_of[label]),
            "ambiguous_surfaces": len(ambiguous_of[label]),
            "unresolved_occurrences_gained": gained,
            "occurrences_gained_by_tradition": dict(by_tradition),
            "rows_fully_resolvable": complete[label]["all"],
            "rows_newly_complete_vs_baseline": complete[label]["all"] - baseline_complete["all"],
            "rows_fully_resolvable_by_tradition": {t: complete[label][t] for t in ("Sunni", "Imami", "Ibadi", "Zaydi")},
            "registry_merge_collision_keys": len(collisions),
            "top_matches": [{"surface_normalized": n, "registry_scholar_indx": match_of[label][n],
                             "registry_name_raw": registry_name[match_of[label][n]], "occurrences": occurrences[n]}
                            for n in top],
        }

    full_label = f"cumulative_{len(RULE_NAMES)}:{RULE_NAMES[-1]}"
    full_disabled = frozenset()
    pair_rule: dict[tuple, str] = {}
    seen_pairs: set = set()
    for count in range(1, len(RULE_NAMES) + 1):
        label = f"cumulative_{count}:{RULE_NAMES[count - 1]}"
        current = set()
        for ids, _ in collisions_by_variant[label].values():
            current |= set(itertools.combinations(ids, 2))
        for pair in current - seen_pairs:
            pair_rule[pair] = RULE_NAMES[count - 1]
        seen_pairs |= current
    collision_rows = []
    for key, (ids, base_names) in collisions_by_variant[full_label].items():
        rules = sorted({pair_rule[pair] for pair in itertools.combinations(ids, 2) if pair in pair_rule})
        collision_rows.append({"invariant_key": key, "introduced_by_rules": rules, "scholar_indx": ids,
                               "registry_names": [registry_name[i] for i in ids],
                               "distinct_baseline_names": base_names, "status": "collision_unreviewed"})
    matches = []
    for norm, indx in sorted(match_of[full_label].items(), key=lambda kv: (-occurrences[kv[0]], kv[0])):
        key, trace = trace_name_invariant(norm, full_disabled)
        registry_row = next(r for r in registry if r[0] == indx)
        registry_trace = trace_name_invariant(registry_row[3], full_disabled)[1]
        matches.append({
            "surface_as_written": raw_example[norm], "surface_normalized": norm, "invariant_key": key,
            "scholar_indx_candidate": indx, "registry_name_raw": registry_row[1],
            "registry_arabic_name": registry_row[2],
            "rules_fired_on_surface": [t[0] for t in trace],
            "rules_fired_on_registry_name": [t[0] for t in registry_trace],
            "occurrences": occurrences[norm], "by_tradition": dict(tradition_counts[norm]),
            "status": "invariant_match_unreviewed"})
    sample = random.Random(SAMPLE_SEED).sample(matches, min(SAMPLE_SIZE, len(matches)))
    sample.sort(key=lambda m: -m["occurrences"])
    rule_sample_counts = Counter(r for m in matches for r in set(m["rules_fired_on_surface"] + m["rules_fired_on_registry_name"]))

    category_tally = defaultdict(lambda: [0, 0])
    for m in matches:
        tally = category_tally[categorize_surface(m["surface_normalized"])]
        tally[0] += 1
        tally[1] += m["occurrences"]
    honorific_surface_side = sum(1 for m in matches if "honorific_formula_strip" in m["rules_fired_on_surface"])
    honorific_registry_only = sum(1 for m in matches if "honorific_formula_strip" in m["rules_fired_on_registry_name"]
                                  and "honorific_formula_strip" not in m["rules_fired_on_surface"])
    registry_with_honorific = sum(1 for r in registry if "رضي الله عن" in r[3] or "عليه السلام" in r[3])
    out = common.output_directory(JOB)
    match_count = common.write_jsonl(out, "name_invariant_matches.jsonl", matches)
    sample_count = common.write_jsonl(out, "name_invariant_spotcheck_sample.jsonl", sample)
    collision_count = common.write_jsonl(out, "name_invariant_registry_collisions.jsonl", collision_rows)
    exact_latin_keys = sum(1 for k in exact_index if LATIN.search(k))
    delta = {
        "header": common.header_object(
            JOB, "python -B datasets/hadith-data/diagnostics/measure_tier0_resolver_delta.py",
            common.input_fingerprints(common.CORPUS_PATH, common.REGISTRY_PATH)),
        "policy_note": ("Proposed change to exact-normalization policy; unreviewed. Lookup order: unchanged exact match, "
                        "then invariant key; a key with several identities is ambiguous and never resolves."),
        "base_normalization_reused": "regen_unified_csvs.narrator_normalize (unmodified)",
        "rules_in_order": list(RULE_NAMES),
        "baseline": {"rows_fully_resolvable": baseline_complete["all"], "by_tradition": {
            t: baseline_complete[t] for t in ("Sunni", "Imami", "Ibadi", "Zaydi")},
            "distinct_unresolved_surfaces": len(unresolved), "unresolved_occurrences": sum(occurrences.values())},
        "losses": {"baseline_complete_rows_lost_in_any_variant": losses,
                   "baseline_resolved_surfaces_not_resolved_in_every_variant": surface_losses},
        "per_rule_alone": {label.split(":", 1)[1]: results[label] for label, _, _g in specs if label.startswith("only:")},
        "cumulative": {label: results[label] for label, _, _g in specs if label.startswith("cumulative_")},
        "cumulative_with_specificity_guard": {
            label: results[label] for label, _, _g in specs if label.startswith("guarded_")},
        "specificity_guard": "match only surfaces categorized ism_nasab or other_multi_token (drops kunya-only, bare ism, bare nasab)",
        "matches_by_surface_category": {c: {"surfaces": n, "occurrences": o} for c, (n, o) in category_tally.items()},
        "honorific_rule_side": {"matches_where_it_fired_on_surface": honorific_surface_side,
                                "matches_where_it_fired_only_on_registry_name": honorific_registry_only,
                                "registry_arabic_names_containing_honorific_phrase": registry_with_honorific,
                                "registry_arabic_names_total": len(registry)},
        "registry_collisions_total_at_full_invariant": len([c for c in collision_rows]),
        "colliding_identity_pairs_by_introducing_rule": dict(Counter(pair_rule.values())),
        "matches_at_full_invariant": match_count,
        "matches_by_rule_that_fired_either_side": dict(rule_sample_counts.most_common()),
        "latin_check": {
            "corpus_surfaces_are_arabic_only_source": True,
            "distinct_surface_norms_containing_latin_letters": len(latin_surface_norms),
            "baseline_resolved_occurrences_whose_exact_key_contains_latin": resolved_key_has_latin,
            "registry_exact_keys_containing_latin": exact_latin_keys,
            "conclusion": "Matching is Arabic-surface against registry; mixed Latin+Arabic full-name keys exist but no resolved surface uses one, so no Latin invariant was built.",
        },
        "seconds": round(time.time() - started, 1),
    }
    common.write_json(out, "name_invariant_delta.json", delta)
    print(json.dumps({"matches": match_count, "sample": sample_count, "collisions": collision_count,
                      "losses": losses, "surface_losses": surface_losses, "seconds": delta["seconds"]}))


if __name__ == "__main__":
    main()
