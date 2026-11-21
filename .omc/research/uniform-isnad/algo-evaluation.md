# Uniform isnad extraction evaluation

Fixtures: `datasets\hadith-data\__tests__\fixtures\all-tradition-isnad-gold-v1.jsonl` (32 provenance-backed records)

The canonical release gate requires overall branch-count accuracy >= 0.90, median branch Jaccard >= 0.90, median ordered edit similarity >= 0.90, and for every tradition branch-count accuracy and mean ordered similarity >= 0.80. Legacy candidates are comparison baselines only.

| Extractor | branch-count accuracy | Jaccard median | ordered median | p25 | p75 | mean | edit median | errors |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `canonical_uniform` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.0 | 0 |
| `legacy_A_simple_set` | 0.688 | 0.690 | 0.690 | 0.000 | 1.000 | 0.556 | 1.5 | 0 |
| `legacy_B_name_span` | 0.688 | 0.714 | 0.732 | 0.000 | 1.000 | 0.565 | 1.0 | 0 |
| `legacy_C_lcs_suffix` | 0.688 | 0.690 | 0.732 | 0.000 | 1.000 | 0.561 | 1.0 | 0 |
| `legacy_D_position_anchored` | 0.688 | 0.667 | 0.690 | 0.000 | 1.000 | 0.549 | 1.5 | 0 |
| `legacy_E_no_stitch` | 0.688 | 0.690 | 0.750 | 0.000 | 1.000 | 0.573 | 1.0 | 0 |

## Canonical tradition breakdown

- Ibadi: branch-count accuracy `1.000`, mean branch Jaccard `1.000`, mean ordered similarity `1.000`
- Imami: branch-count accuracy `1.000`, mean branch Jaccard `1.000`, mean ordered similarity `1.000`
- Sunni: branch-count accuracy `1.000`, mean branch Jaccard `1.000`, mean ordered similarity `1.000`
- Zaydi: branch-count accuracy `1.000`, mean branch Jaccard `1.000`, mean ordered similarity `1.000`

## Canonical cases below 0.80

None.
