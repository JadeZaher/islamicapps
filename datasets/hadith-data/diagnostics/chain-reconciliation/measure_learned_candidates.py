#!/usr/bin/env python3
"""Q2: identities learned from source-index positions the text corroborates, applied as CANDIDATES (diagnostic only).

Needs output/corroborated_observations.jsonl.gz and output/agreement_reports.jsonl.gz from
measure_source_index_agreement.py. Writes output/learned_candidates.json (metrics + cumulative strategy table),
output/learned_candidate_keys.jsonl.gz (one row per surface/context key), output/source_index_attested_links.jsonl.gz
(per-position K6 links with basis). Usage: python -B measure_learned_candidates.py
"""

import gzip
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reconcile_common as rc  # noqa: E402

common = rc.common
OUTPUT = common.output_directory("chain-reconciliation/output")
COMMAND = "python -B datasets/hadith-data/diagnostics/chain-reconciliation/measure_learned_candidates.py"
STRATEGIES = ("S0_strict_resolver", "S1_plus_k6_source_index_corroborated", "S2_plus_learned_unique_in_context",
              "S3_plus_learned_unique_for_surface")


def read_jsonl_gz(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            yield json.loads(line)


class LearnedIndex:
    """(surface key[, teacher|student]) -> Counter(source_id), with optional leave-one-out subtraction."""

    def __init__(self, observations):
        self.by_key = defaultdict(Counter)
        self.by_teacher = defaultdict(Counter)
        self.by_student = defaultdict(Counter)
        for obs in observations:
            self.by_key[obs["key"]][obs["source_id"]] += 1
            self.by_teacher[(obs["key"], obs["teacher"])][obs["source_id"]] += 1
            self.by_student[(obs["key"], obs["student"])][obs["source_id"]] += 1

    @staticmethod
    def _unique(counter: Counter, minus=None):
        live = {sid: n - (1 if sid == minus else 0) for sid, n in counter.items()}
        live = {sid: n for sid, n in live.items() if n > 0}
        return next(iter(live)) if len(live) == 1 else None

    def candidate(self, key, teacher, student, minus=None):
        """Most specific unique candidate: (id, rule) or (None, 'ambiguous'/'unseen')."""
        for rule, counter in (("unique_in_teacher_context", self.by_teacher.get((key, teacher))),
                              ("unique_in_student_context", self.by_student.get((key, student)))):
            if counter:
                hit = self._unique(counter, minus)
                if hit:
                    return hit, rule
        counter = self.by_key.get(key)
        if not counter or not any(n - (1 if sid == minus else 0) > 0 for sid, n in counter.items()):
            return None, "unseen"
        hit = self._unique(counter, minus)
        return (hit, "unique_for_surface") if hit else (None, "ambiguous")


def main() -> None:
    started = time.time()
    canon = rc.Canon()
    observations = [obs for obs in read_jsonl_gz(OUTPUT / "corroborated_observations.jsonl.gz")]
    strict_obs = [obs for obs in observations if obs["basis"] == rc.BASIS_CORROBORATED]
    learned = LearnedIndex(observations)

    # Leave-one-out agreement with the source's own claim (evidence of rule behaviour, not of identity).
    loo = defaultdict(Counter)
    for obs in observations:
        hit, rule = learned.candidate(obs["key"], obs["teacher"], obs["student"], minus=obs["source_id"])
        loo[rule]["predictions"] += 1
        if hit is not None:
            loo[rule]["agrees_with_source_id" if hit == obs["source_id"] else "disagrees_with_source_id"] += 1

    # Per-report attested K6 links: (line, branch, position) -> (id, basis).
    attested = {}
    attested_rows = []
    for report in read_jsonl_gz(OUTPUT / "agreement_reports.jsonl.gz"):
        if report["index"] != "k6_source_index" or not report["aligned"]:
            continue
        basis = rc.BASIS_CORROBORATED if report["class"] == "full_agreement" else rc.BASIS_ALIGNED
        line = report["row"]["line"]
        for i, b_index, j, tier in report["aligned"]:
            attested[(line, b_index, j)] = report["source_ids"][i]
            attested_rows.append({"row": report["row"], "branch": b_index, "position": j,
                                  "surface": report["branches"][b_index][j], "source_id": report["source_ids"][i],
                                  "name_tier": tier, "report_class": report["class"], "basis": basis,
                                  "review_state": "unreviewed"})

    pure_canon = rc.read_pure_canon()
    views = {}
    for view in ("master_text_ar", "pure_canon_chain_field"):
        views[view] = {"occ": defaultdict(Counter), "rows": defaultdict(Counter),
                       "cross_tradition_name_matches": defaultdict(Counter)}
    unresolved_keys_norm, unresolved_keys_fold = Counter(), Counter()
    unresolved_keys_with_obs = Counter()
    candidate_rule_occ = defaultdict(Counter)

    def group_of(tradition, source):
        if tradition != "Sunni":
            return tradition
        return "Sunni K6" if source in rc.K6_SOURCES else f"Sunni PC {source}"

    def score_branches(view, group, tradition, row_number, branches, baseline, attested_ok):
        tables = views[view]
        tables["rows"][group]["rows"] += 1
        if not branches:
            return
        tables["rows"][group]["rows_with_extracted_chain"] += 1
        worst = 0
        for b_index, branch in enumerate(branches):
            for j, surface in enumerate(branch):
                stage = None
                tables["occ"][group]["occurrences"] += 1
                if canon.resolve(surface):
                    stage = 0
                else:
                    key = canon.fold(surface)
                    if baseline:
                        unresolved_keys_norm[canon.regen.narrator_normalize(surface)] += 1
                        unresolved_keys_fold[key] += 1
                        if key in learned.by_key:
                            unresolved_keys_with_obs[key] += 1
                    if attested_ok and (row_number, b_index, j) in attested:
                        stage = 1
                    else:
                        teacher = canon.fold(branch[j + 1]) if j + 1 < len(branch) else "<END>"
                        student = canon.fold(branch[j - 1]) if j > 0 else "<START>"
                        hit, rule = learned.candidate(key, teacher, student)
                        if baseline:
                            candidate_rule_occ[group][rule] += 1
                        if hit and tradition == "Sunni":
                            stage = 2 if rule != "unique_for_surface" else 3
                        elif hit:
                            # A Sunni-lexicon id on an Imami/Ibadi/Zaydi surface is a name match, not evidence.
                            tables["cross_tradition_name_matches"][group][rule] += 1
                if stage is None:
                    worst = 99
                    tables["occ"][group]["not_covered"] += 1
                else:
                    tables["occ"][group][STRATEGIES[stage]] += 1
                    worst = max(worst, stage)
        for level, name in enumerate(STRATEGIES):
            if worst <= level:
                tables["rows"][group][name] += 1

    for row_number, row in common.iter_corpus_rows():
        tradition = common.clean(row.get("tradition")) or "<missing>"
        source = common.clean(row.get("source"))
        group = group_of(tradition, source)
        branches = canon.extract(row.get("text_ar"))
        score_branches("master_text_ar", group, tradition, row_number, branches, baseline=True, attested_ok=True)
        if source in rc.PURE_CANON_SOURCES:
            matches = pure_canon.get((row.get("text_ar") or "").strip(), [])
            chains = {(m.get("chain") or "").strip() for m in matches}
            chain = next(iter(chains)) if len(chains) == 1 else ""
            branches = canon.extract(chain) if chain else []
        score_branches("pure_canon_chain_field", group, tradition, row_number, branches, baseline=False,
                       attested_ok=source not in rc.PURE_CANON_SOURCES)

    def cumulative(table):
        out = {}
        for tradition, counts in sorted(table.items()):
            running, entry = 0, {"occurrences": counts["occurrences"]}
            for name in STRATEGIES:
                running += counts[name]
                entry[name] = running
            entry["not_covered"] = counts["not_covered"]
            out[tradition] = entry
        total = Counter()
        for entry in out.values():
            total.update(entry)
        out["ALL"] = dict(total)
        return out

    def rows_table(table):
        total = Counter()
        for counts in table.values():
            total.update(counts)
        ordered = {}
        for group, counts in sorted(table.items()):
            ordered[group] = {name: counts[name] for name in ("rows", "rows_with_extracted_chain") + STRATEGIES}
        ordered["ALL"] = {name: total[name] for name in ("rows", "rows_with_extracted_chain") + STRATEGIES}
        return ordered

    consistency = Counter()
    for key, counter in learned.by_key.items():
        consistency[min(len(counter), 5)] += 1
    unresolved_with_obs_consistency = Counter()
    for key in unresolved_keys_with_obs:
        unresolved_with_obs_consistency[min(len(learned.by_key[key]), 5)] += 1
    separable = Counter()
    # Homonym separation by teacher context, over keys with several source ids.
    teacher_contexts = defaultdict(list)
    for (key, teacher), counter in learned.by_teacher.items():
        teacher_contexts[key].append(counter)
    for key, counter in learned.by_key.items():
        if len(counter) < 2:
            continue
        separable["multi_id_keys"] += 1
        separable["multi_id_observations"] += sum(counter.values())
        separable["observations_in_unique_teacher_contexts"] += sum(
            sum(ctx.values()) for ctx in teacher_contexts[key] if len(ctx) == 1)

    result = {
        "header": common.header_object(
            "chain-reconciliation/learned-candidates", COMMAND,
            common.input_fingerprints(common.CORPUS_PATH, common.REGISTRY_PATH,
                                      OUTPUT / "corroborated_observations.jsonl.gz")),
        "normalizer_features_present": canon.normalizer_features,
        "observations": {"all": len(observations), "from_full_agreement_reports": len(strict_obs),
                         "distinct_surface_keys": len(learned.by_key),
                         "surface_keys_by_number_of_source_ids(5=5+)": dict(sorted(consistency.items())),
                         "homonym_separation_by_teacher_context": dict(separable)},
        "leave_one_out_rule_agreement_with_source_id": {rule: dict(c) for rule, c in loo.items()},
        "unresolved": {
            "occurrences": sum(unresolved_keys_fold.values()),
            "distinct_by_narrator_normalize": len(unresolved_keys_norm),
            "distinct_by_canonical_fold": len(unresolved_keys_fold),
            "distinct_fold_keys_with_at_least_one_observation": len(unresolved_keys_with_obs),
            "occurrences_of_keys_with_observation": sum(unresolved_keys_with_obs.values()),
            "keys_with_observation_by_number_of_source_ids(5=5+)": dict(sorted(unresolved_with_obs_consistency.items())),
        },
        "candidate_rule_on_unresolved_non_attested_occurrences": {t: dict(c) for t, c in sorted(candidate_rule_occ.items())},
        "views": {view: {"occurrences_covered_cumulative": cumulative(tables["occ"]),
                         "rows_complete_cumulative_atomic": rows_table(tables["rows"]),
                         "cross_tradition_name_matches_not_counted": {
                             g: dict(c) for g, c in sorted(tables["cross_tradition_name_matches"].items())}}
                  for view, tables in views.items()},
        "basis_labels": {"S0_strict_resolver": rc.BASIS_STRICT,
                         "S1_plus_k6_source_index_corroborated": f"{rc.BASIS_CORROBORATED} | {rc.BASIS_ALIGNED}",
                         "S2_plus_learned_unique_in_context": rc.BASIS_LEARNED + " (teacher/student context)",
                         "S3_plus_learned_unique_for_surface": rc.BASIS_LEARNED + " (surface only)"},
        "runtime_seconds": round(time.time() - started, 1),
    }
    common.write_json(OUTPUT, "learned_candidates.json", result)

    def key_rows():
        for (key, teacher), counter in sorted(learned.by_teacher.items()):
            yield {"key": key, "context_axis": "teacher", "context": teacher,
                   "source_ids": dict(counter.most_common()), "unique": len(counter) == 1,
                   "surface_total_ids": dict(learned.by_key[key].most_common(10)),
                   "basis": rc.BASIS_LEARNED, "status": "candidate_only", "review_state": "unreviewed"}
    common.write_jsonl(OUTPUT, "learned_candidate_keys.jsonl.gz", key_rows(), gzipped=True)
    common.write_jsonl(OUTPUT, "source_index_attested_links.jsonl.gz", attested_rows, gzipped=True)
    print(json.dumps({k: result[k] for k in ("unresolved", "views")}, ensure_ascii=False, indent=1))
    print(f"{result['runtime_seconds']}s")


if __name__ == "__main__":
    main()
