"""
Phase 0.5 algorithm bake-off evaluator.

Runs each candidate (A-E) against the annotated rows of
tahweel-gold.jsonl. Reports:
  - branch-count accuracy (% fixtures where len(actual) == len(expected))
  - per-branch narrator-set Jaccard (median + p25/p75)
  - per-branch edit distance (Levenshtein on ordered list)
  - per-fixture detailed breakdown when a candidate fails

Writes Markdown report to .omc/research/uniform-isnad/algo-evaluation.md
"""
from __future__ import annotations
import json
import os
import statistics
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.normpath(os.path.join(BASE, '..')))

from algo_candidates import CANDIDATES  # noqa: E402
from algo_candidates._common import name_normalize  # noqa: E402

GOLD = os.path.join(BASE, '__tests__', 'fixtures', 'tahweel-gold.jsonl')
OUT_MD = os.path.normpath(os.path.join(
    BASE, '..', '..', '.omc', 'research', 'uniform-isnad', 'algo-evaluation.md',
))


def jaccard(a: list[str], b: list[str]) -> float:
    sa = set(name_normalize(x) for x in a)
    sb = set(name_normalize(x) for x in b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def edit_distance(a: list[str], b: list[str]) -> int:
    """Levenshtein on the position-ordered list, with loose name-equality."""
    from algo_candidates.candidate_B_name_span import _matches
    n, m = len(a), len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if _matches(a[i - 1], b[j - 1]) else 1
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)
    return dp[n][m]


def evaluate_candidate(cand_name, cand_fn, fixtures: list[dict]) -> dict:
    branch_count_hits = 0
    jaccard_scores: list[float] = []
    edit_distances: list[int] = []
    expected_total_branches = 0
    actual_total_branches = 0
    per_fixture: list[dict] = []
    errors = 0

    for f in fixtures:
        expected = f['expected_branches']
        expected_total_branches += len(expected)
        try:
            actual = cand_fn(f['text_ar'])
        except Exception as e:
            errors += 1
            per_fixture.append({
                'fixture': f['hadith_id'],
                'error': str(e),
            })
            continue
        actual_total_branches += len(actual)
        if len(actual) == len(expected):
            branch_count_hits += 1

        # Per-branch Jaccard + edit-distance:
        # align by INDEX (i.e., compare expected[i] to actual[i])
        n_pairs = min(len(expected), len(actual))
        per_fix_branches = []
        for i in range(n_pairs):
            j = jaccard(actual[i], expected[i])
            ed = edit_distance(actual[i], expected[i])
            jaccard_scores.append(j)
            edit_distances.append(ed)
            per_fix_branches.append({
                'expected_len': len(expected[i]),
                'actual_len': len(actual[i]),
                'jaccard': round(j, 3),
                'edit_distance': ed,
                'expected': expected[i],
                'actual': actual[i],
            })
        # Unmatched branches: count expected ones missed as 0-jaccard,
        # plus excess actual ones as 0-jaccard penalties
        for _ in range(abs(len(expected) - len(actual))):
            jaccard_scores.append(0.0)
            edit_distances.append(0)  # don't penalize edit distance for missing branch
        per_fixture.append({
            'fixture': f['hadith_id'],
            'expected_branches': len(expected),
            'actual_branches': len(actual),
            'count_match': len(actual) == len(expected),
            'branches': per_fix_branches,
        })

    return {
        'candidate': cand_name,
        'errors': errors,
        'branch_count_accuracy': round(branch_count_hits / max(len(fixtures), 1), 3),
        'jaccard_median': round(statistics.median(jaccard_scores), 3) if jaccard_scores else 0.0,
        'jaccard_p25': round(statistics.quantiles(jaccard_scores, n=4)[0], 3) if len(jaccard_scores) >= 4 else 0.0,
        'jaccard_p75': round(statistics.quantiles(jaccard_scores, n=4)[2], 3) if len(jaccard_scores) >= 4 else 0.0,
        'jaccard_mean': round(statistics.mean(jaccard_scores), 3) if jaccard_scores else 0.0,
        'edit_distance_median': statistics.median(edit_distances) if edit_distances else 0,
        'expected_branches_total': expected_total_branches,
        'actual_branches_total': actual_total_branches,
        'per_fixture': per_fixture,
    }


def main() -> int:
    if not os.path.exists(GOLD):
        print(f'ERROR: {GOLD} not found', file=sys.stderr)
        return 1
    with open(GOLD, 'r', encoding='utf-8') as f:
        fixtures = [json.loads(l) for l in f if l.strip()]
    annotated = [f for f in fixtures if f.get('expected_branches')]
    print(f'Loaded {len(fixtures)} fixtures, {len(annotated)} annotated')
    print()

    results: list[dict] = []
    for cand_name, cand_fn in CANDIDATES.items():
        r = evaluate_candidate(cand_name, cand_fn, annotated)
        results.append(r)
        print(f"{cand_name:25s}  branch-acc={r['branch_count_accuracy']:.3f}  "
              f"jacc med={r['jaccard_median']:.3f} (p25={r['jaccard_p25']:.2f}/p75={r['jaccard_p75']:.2f})  "
              f"edit-med={r['edit_distance_median']}  errs={r['errors']}")

    # Markdown report
    os.makedirs(os.path.dirname(OUT_MD), exist_ok=True)
    lines = [
        '# Algorithm bake-off — Phase 0.5 evaluation',
        '',
        f'Generated by: `datasets/hadith-data/algo_evaluate.py`',
        f'Fixtures: `datasets/hadith-data/__tests__/fixtures/tahweel-gold.jsonl` ({len(annotated)} annotated rows)',
        '',
        '## Summary',
        '',
        '| Candidate | branch-count acc | Jaccard median | Jaccard p25 | Jaccard p75 | Jaccard mean | edit median | errors |',
        '|---|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for r in results:
        lines.append(
            f"| `{r['candidate']}` | {r['branch_count_accuracy']:.3f} | "
            f"{r['jaccard_median']:.3f} | {r['jaccard_p25']:.3f} | "
            f"{r['jaccard_p75']:.3f} | {r['jaccard_mean']:.3f} | "
            f"{r['edit_distance_median']} | {r['errors']} |"
        )
    lines.extend([
        '',
        '## Pass criteria (FR-0.5.4)',
        '',
        '- branch-count accuracy ≥ 0.85',
        '- Jaccard median ≥ 0.80',
        '',
        '## Per-fixture detail',
        '',
    ])
    for r in results:
        lines.append(f'### {r["candidate"]}')
        lines.append('')
        for pf in r['per_fixture']:
            lines.append(f'**`{pf["fixture"]}`** — expected_branches={pf.get("expected_branches", "?")}  actual_branches={pf.get("actual_branches", "?")}  count_match={pf.get("count_match", "?")}')
            for i, b in enumerate(pf.get('branches', [])):
                lines.append(f'  - branch {i}: jaccard={b["jaccard"]} edit={b["edit_distance"]}')
                lines.append(f'    - expected ({b["expected_len"]}): {b["expected"]}')
                lines.append(f'    - actual   ({b["actual_len"]}): {b["actual"]}')
            if pf.get('error'):
                lines.append(f'  - ERROR: {pf["error"]}')
            lines.append('')
    with open(OUT_MD, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print()
    print(f'Wrote {OUT_MD}')

    return 0


if __name__ == '__main__':
    sys.exit(main())
