#!/usr/bin/env python3
"""Before/after diff of the strict resolver around the placeholder and nested-name fix (diagnostic only).

Before = regen_unified_csvs.py at git revision --before-rev (default 7e6be3d, the last commit before the fix),
loaded from git in memory; after = the working-tree module. Surfaces come from the master text_ar plus the
Pure Canon `chain` field. Also measures (does not adopt) a tradition guard. Writes output/resolver-fix/.
Usage: python -B measure_resolver_fix_diff.py [--before-rev REV]
"""

import argparse
import csv
import gzip
import json
import subprocess
import sys
import types
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reconcile_common as rc  # noqa: E402

common = rc.common
OUTPUT = common.output_directory("chain-reconciliation/output/resolver-fix")
REGEN_PATH = common.HADITH_DATA_DIR / "regen_unified_csvs.py"
REGEN_GIT_PATH = "datasets/hadith-data/regen_unified_csvs.py"


def load_regen_at(rev: str):
    source = subprocess.run(["git", "show", f"{rev}:{REGEN_GIT_PATH}"], cwd=common.PROJECT_DIR,
                            capture_output=True, check=True, timeout=60).stdout.decode("utf-8")
    module = types.ModuleType("regen_before")
    module.__file__ = str(REGEN_PATH)
    exec(compile(source, str(REGEN_PATH), "exec"), module.__dict__)  # noqa: S102 - our own committed module
    return module, rc.sha256_bytes(source.encode("utf-8"))


def generation(grade: str) -> str:
    """Lexicon generation marker -> coarse class used by the tradition-guard measurement."""
    if grade.startswith(("Comp.", "Rasool", "Prophet")):
        return "companion_or_prophet_household"
    if grade.startswith("Follower"):
        return "follower"
    return "later_narrator"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before-rev", default="7e6be3d")
    args = parser.parse_args()
    before, before_sha = load_regen_at(args.before_rev)
    after = common.load_regen()
    extractor = common.load_extractor()
    b_exact, b_blocked = before.build_narrator_index(str(common.REGISTRY_PATH))
    a_exact, a_blocked = after.build_narrator_index(str(common.REGISTRY_PATH))
    registry = {r["scholar_indx"].strip(): r for r in csv.DictReader(open(common.REGISTRY_PATH, encoding="utf-8"))}
    pure_canon = rc.read_pure_canon()

    surfaces = Counter()           # raw surface -> occurrences
    by_tradition = defaultdict(Counter)
    row_surfaces = []              # (tradition, view, surfaces) for atomic row counts
    for _, row in common.iter_corpus_rows():
        tradition = common.clean(row.get("tradition"))
        source = common.clean(row.get("source"))
        texts = [("master_text_ar", row.get("text_ar") or "")]
        if source in rc.PURE_CANON_SOURCES:
            chains = {(m.get("chain") or "").strip() for m in pure_canon.get((row.get("text_ar") or "").strip(), [])}
            texts.append(("pure_canon_chain_field", next(iter(chains)) if len(chains) == 1 else ""))
        for view, text in texts:
            try:
                branches = extractor.extract_isnad_branches(text) if text else []
            except extractor.IsnadExtractionLimitError:
                branches = []
            flat = [s for branch in branches for s in branch]
            row_surfaces.append((tradition, view, flat))
            if view == "master_text_ar" and source in rc.PURE_CANON_SOURCES:
                continue  # Pure Canon matn text is not a chain; its `chain` field is counted instead
            for surface in flat:
                surfaces[surface] += 1
                by_tradition[surface][tradition] += 1

    def name_of(indx):
        return (registry.get(indx or "", {}).get("name") or "")[:90]

    resolved_before, resolved_after = {}, {}

    def resolve_before(surface):
        if surface not in resolved_before:
            hit = before.resolve_narrator(surface, b_exact, b_blocked)
            resolved_before[surface] = str(hit) if hit else None
        return resolved_before[surface]

    def resolve_after(surface):
        if surface not in resolved_after:
            hit = after.resolve_narrator(surface, a_exact, a_blocked)
            resolved_after[surface] = str(hit) if hit else None
        return resolved_after[surface]

    for surface in surfaces:
        resolve_before(surface)
        resolve_after(surface)

    changes, totals = [], Counter()
    for surface, count in surfaces.items():
        old, new = resolved_before[surface], resolved_after[surface]
        if old == new:
            continue
        if old and not new:
            label = "lost"
            name_field = registry.get(old, {}).get("name") or ""
            norm = after.narrator_normalize(surface)
            if old in a_exact.placeholders:
                reason = a_exact.placeholders[old]
            elif before._extract_arabic_name_raw(name_field) != after._extract_arabic_name_raw(name_field):
                reason = "nested_name_fix_removed_truncated_key"
            elif norm in a_exact.exact_ambiguous:
                reason = "key_now_ambiguous_with_corrected_or_placeholder_entry"
            else:
                reason = "other"
        elif new and not old:
            label, reason = "gained", "nested_name_now_extracted_whole"
        else:
            label, reason = "changed_id", "nested_name_now_extracted_whole"
        totals[f"{label}:{reason}:surfaces"] += 1
        totals[f"{label}:{reason}:occurrences"] += count
        changes.append({"class": label, "reason": reason, "surface": surface, "key": after.narrator_normalize(surface),
                        "occurrences": count, "by_tradition": dict(by_tradition[surface]),
                        "before_id": old, "before_name": name_of(old), "after_id": new, "after_name": name_of(new)})
    changes.sort(key=lambda c: (c["class"], -c["occurrences"], c["surface"]))

    atomic = defaultdict(Counter)
    for tradition, view, flat in row_surfaces:
        if not flat:
            continue
        atomic[f"{view} | {tradition}"]["rows_with_chain"] += 1
        atomic[f"{view} | {tradition}"]["complete_before"] += all(resolve_before(s) for s in flat)
        atomic[f"{view} | {tradition}"]["complete_after"] += all(resolve_after(s) for s in flat)

    # K6 regression: every equal-length position from the agreement job, before vs after.
    regression = Counter()
    with gzip.open(OUTPUT.parent / "agreement_reports.jsonl.gz", "rt", encoding="utf-8") as handle:
        for line in handle:
            report = json.loads(line)
            if report["index"] != "k6_source_index" or not report["position_tiers"]:
                continue
            for surface, source_id in zip(report["branches"][0], report["source_ids"]):
                for label, resolved in (("before", resolve_before(surface)), ("after", resolve_after(surface))):
                    if resolved:
                        regression[f"{label}_{'agrees' if resolved == source_id else 'conflicts'}_with_k6"] += 1

    # Tradition guard (measured, not adopted): post-fix resolutions on non-Sunni rows into the shared lexicon.
    guard = defaultdict(Counter)
    guard_examples = defaultdict(Counter)
    for surface, count in surfaces.items():
        target = resolved_after[surface]
        if not target:
            continue
        for tradition, n in by_tradition[surface].items():
            if tradition == "Sunni":
                continue
            klass = generation(registry.get(target, {}).get("grade") or "")
            guard[tradition][klass] += n
            guard_examples[f"{tradition} | {klass}"][(surface, target, name_of(target),
                                                      (registry.get(target, {}).get("grade") or "")[:30])] += n

    placeholder_rows = [{"scholar_indx": indx, "reason": reason, "name": registry[indx]["name"],
                         "grade": registry[indx]["grade"]} for indx, reason in
                        sorted(a_exact.placeholders.items(), key=lambda item: int(item[0]))]
    handle, _ = common.open_output(OUTPUT, "excluded_placeholder_entries.csv")
    with handle:
        writer = csv.DictWriter(handle, fieldnames=["scholar_indx", "reason", "name", "grade"])
        writer.writeheader()
        writer.writerows(placeholder_rows)
    common.write_jsonl(OUTPUT, "resolution_diff.jsonl", changes)
    result = {
        "header": common.header_object(
            "chain-reconciliation/resolver-fix",
            "python -B datasets/hadith-data/diagnostics/chain-reconciliation/measure_resolver_fix_diff.py",
            {**common.input_fingerprints(common.CORPUS_PATH, common.REGISTRY_PATH, REGEN_PATH, rc.PURE_CANON),
             f"{REGEN_GIT_PATH}@{args.before_rev}": before_sha}),
        "placeholders_by_reason": dict(Counter(a_exact.placeholders.values())),
        "distinct_surfaces": len(surfaces), "occurrences": sum(surfaces.values()),
        "diff_totals": dict(sorted(totals.items())),
        "atomic_rows": {k: dict(v) for k, v in sorted(atomic.items())},
        "k6_equal_length_positions": dict(regression),
        "tradition_guard_measured_not_adopted": {t: dict(c) for t, c in guard.items()},
        "tradition_guard_examples": {k: [{"surface": s, "id": i, "name": n, "grade": g, "occurrences": c}
                                         for (s, i, n, g), c in v.most_common(8)]
                                     for k, v in sorted(guard_examples.items())},
    }
    common.write_json(OUTPUT, "resolver_fix_summary.json", result)
    print(json.dumps({k: result[k] for k in ("placeholders_by_reason", "diff_totals", "atomic_rows",
                                             "k6_equal_length_positions", "tradition_guard_measured_not_adopted")},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
