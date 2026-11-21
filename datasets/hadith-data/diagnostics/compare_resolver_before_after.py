#!/usr/bin/env python3
"""Before/after proof for the adopted narrator lookup (read-only).

Loads the resolver as committed at a base revision (`git show`, executed in memory, nothing written) and the
working-tree resolver, resolves every distinct corpus surface with both, and reports gains, losses and id changes.
Writes only under diagnostics/narrator-resolution/.

Usage: python -B datasets/hadith-data/diagnostics/compare_resolver_before_after.py [--base-rev af2f90b]
"""

import argparse
import json
import subprocess
import sys
import time
import types
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import diagnostic_common as common  # noqa: E402

JOB = "narrator-resolution"


def load_base_resolver(rev: str):
    """Execute regen_unified_csvs.py as of `rev` in memory (git show is read-only)."""
    relative = (common.HADITH_DATA_DIR / "regen_unified_csvs.py").relative_to(common.PROJECT_DIR).as_posix()
    source = subprocess.run(["git", "show", f"{rev}:{relative}"], cwd=common.PROJECT_DIR, capture_output=True,
                            check=True).stdout.decode("utf-8")
    module = types.ModuleType("regen_unified_csvs_base")
    module.__file__ = str(common.HADITH_DATA_DIR / "regen_unified_csvs.py")
    exec(compile(source, module.__file__, "exec"), module.__dict__)  # noqa: S102 - repo's own committed code
    return module


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rev", default="af2f90b")
    args = parser.parse_args()
    started = time.time()
    before, after = load_base_resolver(args.base_rev), common.load_regen()
    extractor = common.load_extractor()
    old_exact, old_blocked = before.build_narrator_index(str(common.REGISTRY_PATH))
    new_exact, new_blocked = after.build_narrator_index(str(common.REGISTRY_PATH))

    cache: dict[str, tuple] = {}

    def resolve_both(raw: str):
        hit = cache.get(raw)
        if hit is None:
            hit = cache[raw] = (before.resolve_narrator(raw, old_exact, old_blocked),
                                after.resolve_narrator(raw, new_exact, new_blocked))
        return hit

    def tier_of(raw: str) -> str:
        norm = after.narrator_normalize(raw)
        if new_exact.get(norm):
            return "tier0_exact"
        key = after.narrator_fold_normalize(raw)
        if new_exact.folded.get(key):
            return "tier1_spelling_folds"
        return "tier2_guarded_kunya_fold"

    occ = Counter()
    gained_by_tier = Counter()
    gained_by_tradition = defaultdict(Counter)
    lost = changed = 0
    loss_examples = []
    surfaces_old, surfaces_new = set(), set()
    rows_complete = {"before": Counter(), "after": Counter()}
    surface_formula = set()
    for _, row in common.iter_corpus_rows():
        tradition = common.clean(row["tradition"]) or "<missing>"
        try:
            branches = extractor.extract_isnad_branches(row.get("text_ar") or "")
        except extractor.IsnadExtractionLimitError:
            continue
        if not branches:
            continue
        ok_before = ok_after = True
        for branch in branches:
            for raw in branch:
                old, new = resolve_both(raw)
                occ["surface_occurrences"] += 1
                if old:
                    occ["resolved_before"] += 1
                    surfaces_old.add(raw)
                if new:
                    occ["resolved_after"] += 1
                    surfaces_new.add(raw)
                if old and not new:
                    lost += 1
                    loss_examples.append({"surface": raw, "before": old, "after": new})
                elif old and new and old != new:
                    changed += 1
                    loss_examples.append({"surface": raw, "before": old, "after": new})
                if new and not old:
                    tier = tier_of(raw)
                    gained_by_tier[tier] += 1
                    gained_by_tradition[tradition][tier] += 1
                if not old:
                    ok_before = False
                if not new:
                    ok_after = False
                if after._BLESSING_FORMULA.search(after.narrator_fold_normalize(raw)):
                    surface_formula.add(raw)
        rows_complete["before"][tradition] += ok_before
        rows_complete["after"][tradition] += ok_after
        rows_complete["before"]["all"] += ok_before
        rows_complete["after"]["all"] += ok_after

    # Ambiguity and registry-formula statistics.
    def formula_names(module, strip):
        count = 0
        with open(common.REGISTRY_PATH, encoding="utf-8", errors="replace", newline="") as handle:
            import csv
            for row in csv.DictReader(handle):
                name = (row.get("name") or "").strip()
                arabic = module._extract_arabic_name(name, strip_formulas=strip) if strip is not None else \
                    module._extract_arabic_name(name)
                key = after.narrator_fold_normalize(arabic)
                count += bool(after._BLESSING_FORMULA.search(key))
        return count

    registry_before = 0
    registry_after = formula_names(after, True)
    with open(common.REGISTRY_PATH, encoding="utf-8", errors="replace", newline="") as handle:
        import csv
        for row in csv.DictReader(handle):
            name = (row.get("name") or "").strip()
            arabic = before._extract_arabic_name(name)
            registry_before += bool(after._BLESSING_FORMULA.search(after.narrator_fold_normalize(arabic)))
    legacy_ambiguous_but_tier1_unique = sum(
        1 for key in new_exact.exact_ambiguous if len(new_exact.folded.get(key, ())) == 1)
    tier1_ambiguous = sum(1 for ids in new_exact.folded.values() if len(ids) >= 2)
    # Surfaces resolved at tier 0 whose folded key would be ambiguous in tier 1 (legacy resolution retained).
    retained_legacy = sum(1 for key in new_exact
                          if len(new_exact.folded.get(after.narrator_fold_normalize(key), ())) >= 2)

    report = {
        "header": common.header_object(
            JOB, "python -B datasets/hadith-data/diagnostics/compare_resolver_before_after.py",
            common.input_fingerprints(common.CORPUS_PATH, common.REGISTRY_PATH)),
        "base_revision": args.base_rev,
        "occurrences": dict(occ),
        "occurrences_gained_by_tier": dict(gained_by_tier),
        "occurrences_gained_by_tradition_and_tier": {t: dict(c) for t, c in gained_by_tradition.items()},
        "losses": {"previously_resolved_now_unresolved": lost, "previously_resolved_now_different_id": changed,
                   "examples": loss_examples[:20]},
        "distinct_resolved_surfaces": {"before": len(surfaces_old), "after": len(surfaces_new),
                                       "lost": len(surfaces_old - surfaces_new)},
        "rows_fully_resolvable": {k: dict(v) for k, v in rows_complete.items()},
        "registry_index": {
            "tier0_entries_before": len(old_exact), "tier0_entries_after": len(new_exact),
            "tier0_ambiguous_keys": len(new_exact.exact_ambiguous),
            "tier1_keys": len(new_exact.folded), "tier1_ambiguous_keys": tier1_ambiguous,
            "tier0_resolutions_retained_although_tier1_key_is_ambiguous": retained_legacy,
            "bare_single_token_names_withheld_after_formula_strip": len(new_exact.withheld_bare_names),
            "registry_arabic_names_carrying_a_blessing_formula": {"before": registry_before, "after": registry_after},
        },
        "distinct_surfaces_still_carrying_a_blessing_formula": len(surface_formula),
        "seconds": round(time.time() - started, 1),
    }
    common.write_json(common.output_directory(JOB), "resolver_adoption_diff.json", report)
    print(json.dumps({k: report[k] for k in ("occurrences", "occurrences_gained_by_tier", "losses",
                                             "rows_fully_resolvable", "seconds")}, ensure_ascii=False))
    print(json.dumps(report["registry_index"], ensure_ascii=False), report["distinct_surfaces_still_carrying_a_blessing_formula"])


if __name__ == "__main__":
    main()
