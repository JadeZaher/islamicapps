#!/usr/bin/env python3
"""Q1: agreement between id-bearing chain indices and the text-extracted chain, per report (diagnostic only).

Indices under test:
  k6_source_index        original K6 `chain_indx` inside archive/datasets.7z (the source's own claim)
  legacy_master_index    `chain_indx` in the committed master (older local resolver; feeds today's live links)
Writes output/agreement_matrix.json, output/agreement_reports.jsonl.gz, output/corroborated_observations.jsonl.gz,
output/resolver_conflicts.jsonl. Usage: python -B measure_source_index_agreement.py
"""

import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reconcile_common as rc  # noqa: E402

common = rc.common
OUTPUT = common.output_directory("chain-reconciliation/output")
COMMAND = "python -B datasets/hadith-data/diagnostics/chain-reconciliation/measure_source_index_agreement.py"


def classify(canon, ids, branches):
    """Return (class, per-position tiers or None, aligned pairs with branch coordinates)."""
    if not ids:
        return "no_source_index", None, []
    if branches is None:
        return "extraction_limit", None, []
    if not branches:
        return "no_text_chain", None, []
    if len(branches) == 1:
        branch = branches[0]
        if len(branch) == len(ids):
            tiers = [rc.corroboration_tier(canon, branch[k], ids[k], ids[k - 1] if k else None)
                     for k in range(len(ids))]
            pairs = [(k, 0, k, tier) for k, tier in enumerate(tiers) if tier in rc.CORROBORATED]
            label = "full_agreement" if len(pairs) == len(ids) else "same_length_name_mismatch"
            return label, tiers, pairs
        pairs = [(i, 0, j, tier) for i, j, tier in rc.align(canon, ids, branch)]
        label = "length_differs_source_longer" if len(ids) > len(branch) else "length_differs_text_longer"
        return label, None, pairs
    # Taḥwīl / co-transmitter rows: best single branch, or all branches concatenated in reading order.
    best = []
    for b_index, branch in enumerate(branches):
        pairs = [(i, b_index, j, tier) for i, j, tier in rc.align(canon, ids, branch)]
        if len(pairs) > len(best):
            best = pairs
    flat, coordinates = [], []
    for b_index, branch in enumerate(branches):
        for j, surface in enumerate(branch):
            flat.append(surface)
            coordinates.append((b_index, j))
    if len(flat) <= 120:
        pairs = [(i,) + coordinates[j] + (tier,) for i, j, tier in rc.align(canon, ids, flat)]
        if len(pairs) > len(best):
            best = pairs
    label = "multi_branch_all_source_ids_aligned" if len(best) == len(ids) else "multi_branch_partial"
    return label, None, best


def main() -> None:
    started = time.time()
    canon = rc.Canon()
    k6_rows, k6_sha = rc.read_k6_original()
    inputs = common.input_fingerprints(common.CORPUS_PATH, common.REGISTRY_PATH, rc.K6_ARCHIVE)
    inputs[f"{common.relative_path(rc.K6_ARCHIVE)}!{rc.K6_MEMBER}"] = k6_sha
    inputs[common.relative_path(common.HADITH_DATA_DIR / "regen_unified_csvs.py")] = common.sha256_file(
        common.HADITH_DATA_DIR / "regen_unified_csvs.py")

    matrix = {name: {"by_class": Counter(), "by_source": defaultdict(Counter), "by_tradition": defaultdict(Counter),
                     "source_ids": 0, "source_ids_aligned_corroborated": 0,
                     "position_tiers_same_length_rows": Counter(), "aligned_pair_tiers": Counter(),
                     "resolver_conflicts_same_length_rows": Counter(), "resolver_conflict_pairs": Counter(),
                     "uncorroborated_positions_with_registry_edge_to_neighbour": Counter(),
                     "source_ids_missing_from_registry": Counter()}
              for name in ("k6_source_index", "legacy_master_index")}
    join = Counter()
    legacy_vs_k6 = Counter()
    observations_rows, report_rows, conflicts = [], [], []

    def record(index_name, tradition, source, row_number, row, ids, branches):
        label, tiers, pairs = classify(canon, ids, branches)
        stats = matrix[index_name]
        stats["by_class"][label] += 1
        stats["by_source"][f"{tradition} | {source}"][label] += 1
        stats["by_tradition"][tradition][label] += 1
        stats["source_ids"] += len(ids)
        stats["source_ids_aligned_corroborated"] += len(pairs)
        if tiers:
            stats["position_tiers_same_length_rows"].update(tiers)
        for *_, tier in pairs:
            stats["aligned_pair_tiers"][tier] += 1
        reference = common.row_reference(row_number, row)
        report_rows.append({"index": index_name, "row": reference, "tradition": tradition, "class": label,
                            "source_ids": ids, "branches": branches or [],
                            "position_tiers": tiers, "aligned": [list(p) for p in pairs]})
        for source_id in ids:
            if source_id not in canon.registry:
                stats["source_ids_missing_from_registry"][source_id] += 1
        if tiers:
            branch = branches[0]
            for k, tier in enumerate(tiers):
                if rc.resolver_conflict(canon, branch[k], ids[k]):
                    resolved = canon.resolve(branch[k])
                    stats["resolver_conflicts_same_length_rows"][f"{tier}"] += 1
                    stats["resolver_conflict_pairs"][f"{canon.fold(branch[k])} | source {ids[k]} | resolver {resolved}"] += 1
                    if index_name == "k6_source_index" and len(conflicts) < 3000:
                        conflicts.append({"row": reference, "position": k, "surface": branch[k],
                                          "source_id": ids[k], "resolver_id": resolved, "name_tier": tier})
                if tier not in rc.CORROBORATED:
                    entry = canon.registry.get(ids[k], {})
                    neighbours = {ids[k - 1]} if k else set()
                    neighbours |= {ids[k + 1]} if k + 1 < len(ids) else set()
                    linked = bool(neighbours & (entry.get("teachers", set()) | entry.get("students", set())))
                    stats["uncorroborated_positions_with_registry_edge_to_neighbour"][str(linked)] += 1
        if index_name != "k6_source_index" or not branches:
            return
        basis = rc.BASIS_CORROBORATED if label == "full_agreement" else rc.BASIS_ALIGNED
        for i, b_index, j, tier in pairs:
            branch = branches[b_index]
            observations_rows.append({
                "surface": branch[j], "key": canon.fold(branch[j]),
                "teacher": canon.fold(branch[j + 1]) if j + 1 < len(branch) else "<END>",
                "student": canon.fold(branch[j - 1]) if j > 0 else "<START>",
                "source_id": ids[i], "tier": tier, "basis": basis, "report_class": label,
                "strict_resolver_id": canon.resolve(branch[j]), "row": reference["line"],
                "source": reference["source"]})

    for row_number, row in common.iter_corpus_rows():
        tradition = common.clean(row.get("tradition"))
        source = common.clean(row.get("source"))
        position = row_number - 2
        branches = None
        legacy_ids = rc.parse_ids(row.get("chain_indx"))
        need_text = legacy_ids or (source in rc.K6_SOURCES and position < len(k6_rows))
        if need_text:
            branches = canon.extract(row.get("text_ar"))
        if source in rc.K6_SOURCES and position < len(k6_rows):
            original = k6_rows[position]
            if (original["text_ar"] == row.get("text_ar")
                    and original["source"].strip() == source):
                join["k6_rows_joined_by_position_and_exact_arabic"] += 1
                k6_ids = rc.parse_ids(original["chain_indx"])
                record("k6_source_index", tradition, source, row_number, row, k6_ids, branches)
                if legacy_ids:
                    shared = len(set(legacy_ids) & set(k6_ids))
                    legacy_vs_k6["legacy_rows"] += 1
                    legacy_vs_k6["legacy_ids"] += len(legacy_ids)
                    legacy_vs_k6["legacy_ids_also_in_k6_row"] += shared
                    if set(legacy_ids) <= set(k6_ids):
                        legacy_vs_k6["legacy_row_subset_of_k6_row"] += 1
                    if legacy_ids == k6_ids:
                        legacy_vs_k6["legacy_row_equal_k6_row"] += 1
            else:
                join["k6_rows_join_rejected"] += 1
        if legacy_ids:
            record("legacy_master_index", tradition, source, row_number, row, legacy_ids, branches)

    for stats in matrix.values():
        for name in ("resolver_conflict_pairs", "source_ids_missing_from_registry"):
            counter = stats[name]
            stats[name] = {"distinct": len(counter), "occurrences": sum(counter.values()),
                           "top": dict(counter.most_common(150))}

    def plain(value):
        if isinstance(value, dict):
            return {key: plain(item) for key, item in sorted(value.items())}
        return value

    summary = {}
    for name, stats in matrix.items():
        by_class = stats["by_class"]
        corroborated_ids = stats["source_ids_aligned_corroborated"]
        summary[name] = {
            "reports_with_index": sum(count for label, count in by_class.items() if label != "no_source_index"),
            "full_agreement_reports": by_class["full_agreement"],
            "multi_branch_all_source_ids_aligned": by_class["multi_branch_all_source_ids_aligned"],
            "source_ids": stats["source_ids"],
            "source_ids_corroborated_by_aligned_text": corroborated_ids,
            "percent_source_ids_corroborated": round(100 * corroborated_ids / max(stats["source_ids"], 1), 1),
        }
    full_name_only = sum(
        1 for row in report_rows if row["index"] == "k6_source_index" and row["class"] == "full_agreement"
        and all(tier in rc.CORROBORATED_FULL for tier in row["position_tiers"]))
    summary["k6_source_index"]["full_agreement_reports_every_position_full_name_or_relational"] = full_name_only

    result = {
        "header": common.header_object("chain-reconciliation/agreement", COMMAND, inputs),
        "normalizer_features_present": canon.normalizer_features,
        "join": dict(join),
        "summary": summary,
        "legacy_master_index_vs_k6_source_index_on_k6_rows": dict(legacy_vs_k6),
        "matrix": {name: {key: plain(value) for key, value in stats.items()} for name, stats in matrix.items()},
        "runtime_seconds": round(time.time() - started, 1),
    }
    common.write_json(OUTPUT, "agreement_matrix.json", result)
    common.write_jsonl(OUTPUT, "agreement_reports.jsonl.gz", report_rows, gzipped=True)
    common.write_jsonl(OUTPUT, "corroborated_observations.jsonl.gz", observations_rows, gzipped=True)
    common.write_jsonl(OUTPUT, "resolver_conflicts.jsonl", conflicts)
    print(json_dump(summary))
    print("join", dict(join), "legacy_vs_k6", dict(legacy_vs_k6), f"{result['runtime_seconds']}s")


def json_dump(value) -> str:
    import json
    return json.dumps(value, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
