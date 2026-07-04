#!/usr/bin/env python3
"""
audit_kunya_gap.py
==================
Quantify the resolver hit-rate gap on the unified corpus (Phase 4 / FR-5 audit
tool for the uniform_isnad_extraction_20260609 conductor track).

Reads all_hadiths_unified.csv, runs extract_isnad_branches + resolve_narrator
on every text_ar, and counts:
  - Total surface forms attempted
  - Resolved count + percentage
  - Top 50 unresolved surface forms by frequency (with sample hadith_id)
  - Per-source resolver hit rate

Run BEFORE applying Phase 4 enrichment to capture the baseline, then again
AFTER to measure the delta.

Usage::

    # Baseline (before Phase 4 kunya enrichment):
    PYTHONPATH=datasets/hadith-data:datasets \\
        python datasets/hadith-data/audit_kunya_gap.py \\
        --out .omc/research/uniform-isnad/kunya-gap-audit-pre-phase4.md

    # After enrichment:
    PYTHONPATH=datasets/hadith-data:datasets \\
        python datasets/hadith-data/audit_kunya_gap.py \\
        --out .omc/research/uniform-isnad/kunya-gap-audit-post-phase4.md

    # Quick smoke test on first 500 rows:
    python datasets/hadith-data/audit_kunya_gap.py --limit 500 --out /tmp/audit-smoke.md

Options:
    --out PATH      Output markdown file path (default: stdout)
    --limit N       Process only the first N rows (for smoke testing)
    --rawis PATH    Override path to all_rawis.csv
    --unified PATH  Override path to all_hadiths_unified.csv
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from collections import Counter, defaultdict

# Allow running from repo root with PYTHONPATH=datasets/hadith-data:datasets
_HERE = os.path.dirname(os.path.abspath(__file__))
_DATASETS = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)
sys.path.insert(0, _DATASETS)

# Increase field size limit for large CSV cells
csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))


def _get_defaults():
    rawis_path = os.path.join(_DATASETS, 'narrator-data', 'all_rawis.csv')
    unified_path = os.path.join(_HERE, 'all_hadiths_unified.csv')
    return rawis_path, unified_path


def main():
    rawis_default, unified_default = _get_defaults()

    parser = argparse.ArgumentParser(
        description="Audit kunya resolver hit-rate gap (Phase 4 FR-5 tool).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--out', default=None, help='Output markdown file path (default: stdout)')
    parser.add_argument('--limit', type=int, default=None, help='Process only first N rows')
    parser.add_argument('--rawis', default=rawis_default, help='Path to all_rawis.csv')
    parser.add_argument('--unified', default=unified_default, help='Path to all_hadiths_unified.csv')
    args = parser.parse_args()

    # Import resolver components
    try:
        from regen_unified_csvs import build_narrator_index, resolve_narrator
    except ImportError as e:
        print(f"ERROR: Cannot import resolver: {e}", file=sys.stderr)
        print("Run with: PYTHONPATH=datasets/hadith-data:datasets python ...", file=sys.stderr)
        sys.exit(1)

    try:
        from extract_isnad_unified import extract_isnad_branches
    except ImportError as e:
        print(f"ERROR: Cannot import extractor: {e}", file=sys.stderr)
        sys.exit(1)

    # Check input files
    for path, label in [(args.rawis, 'all_rawis.csv'), (args.unified, 'all_hadiths_unified.csv')]:
        if not os.path.exists(path):
            print(f"ERROR: {label} not found at: {path}", file=sys.stderr)
            sys.exit(1)

    print(f"[audit] Loading narrator index from: {args.rawis}", file=sys.stderr)
    exact_index, blocked_index = build_narrator_index(args.rawis)
    print(f"[audit] Narrator index: {len(exact_index)} unique entries", file=sys.stderr)

    # Counters
    total_surfaces = 0
    resolved_surfaces = 0
    unresolved_counter = Counter()    # surface -> count
    unresolved_samples = {}           # surface -> first hadith_id seen
    source_stats = defaultdict(lambda: {'attempted': 0, 'resolved': 0})

    print(f"[audit] Scanning: {args.unified}", file=sys.stderr)
    row_count = 0

    with open(args.unified, encoding='utf-8', errors='replace', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if args.limit and row_count >= args.limit:
                break
            row_count += 1
            if row_count % 10_000 == 0:
                pct = resolved_surfaces / total_surfaces * 100 if total_surfaces else 0
                print(
                    f"[audit] {row_count:,} rows | surfaces: {total_surfaces:,} | "
                    f"resolved: {resolved_surfaces:,} ({pct:.1f}%)",
                    file=sys.stderr,
                )

            text_ar = row.get('text_ar', '') or ''
            hadith_id = row.get('hadith_id', '') or row.get('id', '') or str(row_count)
            source = row.get('source', '') or row.get('tradition', '') or 'unknown'

            if not text_ar.strip():
                continue

            # Extract isnad surfaces
            try:
                branches = extract_isnad_branches(text_ar)
            except Exception:
                continue

            for branch in (branches or []):
                for narrator in (branch or []):
                    surface = narrator.strip() if isinstance(narrator, str) else ''
                    if not surface:
                        continue
                    total_surfaces += 1
                    source_stats[source]['attempted'] += 1

                    result = resolve_narrator(surface, exact_index, blocked_index)
                    if result is not None:
                        resolved_surfaces += 1
                        source_stats[source]['resolved'] += 1
                    else:
                        unresolved_counter[surface] += 1
                        if surface not in unresolved_samples:
                            unresolved_samples[surface] = hadith_id

    # Compute final stats
    hit_rate = resolved_surfaces / total_surfaces * 100 if total_surfaces else 0
    top_unresolved = unresolved_counter.most_common(50)

    # Format output
    lines = []
    lines.append("# Kunya Gap Audit — Phase 4 FR-5")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Rows processed | {row_count:,} |")
    lines.append(f"| Total surface forms attempted | {total_surfaces:,} |")
    lines.append(f"| Resolved | {resolved_surfaces:,} |")
    lines.append(f"| Unresolved | {total_surfaces - resolved_surfaces:,} |")
    lines.append(f"| Hit rate | **{hit_rate:.2f}%** |")
    lines.append(f"| Narrator index size | {len(exact_index):,} |")
    lines.append("")

    lines.append("## Per-Source Hit Rate")
    lines.append("")
    lines.append("| Source | Attempted | Resolved | Hit Rate |")
    lines.append("|--------|-----------|----------|----------|")
    for src, stats in sorted(source_stats.items(), key=lambda x: -x[1]['attempted']):
        att = stats['attempted']
        res = stats['resolved']
        pct = res / att * 100 if att else 0
        lines.append(f"| {src} | {att:,} | {res:,} | {pct:.1f}% |")
    lines.append("")

    lines.append("## Top 50 Unresolved Surface Forms")
    lines.append("")
    lines.append("| Rank | Surface Form | Count | Sample Hadith ID |")
    lines.append("|------|-------------|-------|-----------------|")
    for rank, (surface, count) in enumerate(top_unresolved, 1):
        sample = unresolved_samples.get(surface, '')
        lines.append(f"| {rank} | {surface} | {count:,} | {sample} |")
    lines.append("")

    output = "\n".join(lines)

    if args.out:
        out_dir = os.path.dirname(args.out)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"[audit] Report written to: {args.out}", file=sys.stderr)
    else:
        sys.stdout.buffer.write(output.encode('utf-8'))
        sys.stdout.buffer.write(b"\n")


if __name__ == '__main__':
    main()
