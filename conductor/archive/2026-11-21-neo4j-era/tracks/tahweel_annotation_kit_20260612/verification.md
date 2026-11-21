# Verification — taḥwīl annotation kit + SOP

**Track:** `tahweel_annotation_kit_20260612`
**Closed:** 2026-06-24
**Gate Φ-7 status:** PASSED (G-2/3/4/5 PASS; G-1/G-6-human deferred per Risk-D/E)

---

## Phase 0 — audit + scaffolding (was Φ-0, 2026-06-13)

### T-0.1 — Existing fixture case-type coverage

| Fixture | Source | Cases covered |
|---|---|---|
| `30001` (Tirmidhi #1) | Jami' al-Tirmidhi | **2** (classic 2-branch convergence at سماك) + **5** (surface drift: سماك vs سماك بن حرب) |
| `muslim-1` | Sahih Muslim | **4** (parallel-but-no-convergence) |
| `muslim-2` | Sahih Muslim | **2** + **3** (convergence at شعبة + co-transmitter at branch head) |
| `muslim-31` | Sahih Muslim | **2** + **5** (convergence at مسعر + surface drift سفيان/سفيان بن عيينة) |
| `muslim-102` | Sahih Muslim | **2** + **5** + **6** (convergence + drift + pronoun reference أبي) |

**Gaps identified at Phase 0:** case 1 (single chain, addressed via illustrative Bukhari example in guide §3.1) and case 7 (3+-branch, addressed via Ṣaḥīḥ Muslim #1565 in guide §3.7).

### T-0.2 — Non-Sunni taḥwīl audit (decisive finding)

| Tradition | Rows | ح-marked rows |
|---|---:|---:|
| Imami (16 sources) | 33,225 | **0** |
| Zaydi (Musnad al-Imam Zayd) | 698 | **0** |
| Ibadi (al-Rabīʿ ibn Ḥabīb) | 1,004 | **0** |
| Rida (Saḥīfat al-Imam Ali al-Rida) | 35 | **0** |
| **TOTAL non-Sunni** | **34,962** | **0** |

**NFR-5 resolves to "document the absence" rather than "include 2 Imami examples."** Encoded in guide §3.8.

### T-0.3 — Case-type 7 example

**Picked:** Ṣaḥīḥ Muslim hadith_no=1565 (`tahweel_count: 3`, 4 branches converging at الأعمش, includes the idiom `كلهم عن X، بهذا الإسناد مثله`). Encoded as guide §3.7 with draft 5-branch decomposition (case 3 × case 7 composition).

### T-0.4 — Scaffold directories + archive

Created at Phase 0: `docs/annotation/` (5 files) + `datasets/hadith-data/__tests__/fixtures/` (4 scripts + `archive/pull_tahweel_candidates.py` moved from parent).

---

## Phase 1 — annotation guide

**File:** `docs/annotation/tahweel-annotation-guide.md` — 6,658 words, 9 sections (§1–§9).

| Check | Result |
|---|---|
| All 9 spec FR-1.2 sections present | ✅ §1–§9 confirmed via heading grep |
| NFR-1 forbidden-jargon grep | ✅ Zero hits for `jaccard\|set intersection\|LCS\|longest common (sub)?seq\|Levenshtein\|edit distance\|regex\|kunya hash` |
| §3 worked-example JSON matches fixtures verbatim | ✅ All 5 fixtures (30001, muslim-1/2/31/102) round-tripped through `json.loads` and compared structurally |
| §3.1 case-1 illustrative Bukhari example present | ✅ Labelled "illustrative — not from fixture set yet" |
| §3.7 case-7 draft annotation for Muslim #1565 present | ✅ 5-branch decomposition documented |
| §3.8 non-Sunni absence section present | ✅ Cites Phase 0 audit |
| User decisions encoded | ✅ All 5 fixtures used; soft scope framing in §8 ("structural extraction task, distinct from classical isnad evaluation"); both α and κ documented in §7 |

---

## Phase 2 — calibration test

**Files:** `docs/annotation/calibration-test.jsonl`, `docs/annotation/.calibration-gold.jsonl`, `docs/annotation/calibration-test.md` (~450 words), `datasets/hadith-data/__tests__/fixtures/score_calibration.py`.

| Check | Result |
|---|---|
| `calibration-test.jsonl` has 5 redacted rows | ✅ All `expected_branches: null` |
| `.calibration-gold.jsonl` byte-identical to gold | ✅ 5,516 bytes |
| **Self-test: scorer on gold-as-submission** | ✅ Aggregate **1.000**, exit 0, "you matched 100.0% of the gold narrators per branch on average" |
| **G-2 planted-error tests** | ✅ **5/5 PASS** |
| User-facing output uses plain language gloss | ✅ Per TC-6 |

---

## Phase 3 — validator

**Files:** `datasets/hadith-data/__tests__/fixtures/validate_annotation.py`, `__tests__/__tests__/test_validator_planted_errors.py`.

Validator implements **V-1 through V-9** (V-9 added at Phase 7 closeout for `kit_version` per spec Q4).

| Check | Result |
|---|---|
| Validator on backfilled gold | ✅ **5 PASS, 0 WARN, 0 FAIL** at default level |
| **G-3 planted-error tests** | ✅ **13/13 PASS** (10 acceptance + 3 sanity) |
| Promote mode atomic refusal on partial failure | ✅ `test_promote_atomic_refuses_partial_failure` |
| Promote mode backup-before-append | ✅ `test_promote_success_creates_backup_and_appends` |
| V-9 semver enforcement | ✅ FAIL on non-semver, WARN on missing (legacy-friendly) |

### Real findings surfaced during Phase 3

1. **V-2 false positive on Arabic punctuation.** `muslim-2` (`"وابن، بشار"`) and `muslim-102` (`"أبو خيثمة، زهير بن حرب"`) have an Arabic comma mid-name that broke naive substring search. Fixed by adding a `_norm_v2()` helper that strips Arabic + Latin punctuation before the substring check. **Annotation is canonical; the check was incomplete.**

2. **Gold metadata gap.** The 5 fixtures predated V-6/V-7/V-8 schema. Backfilled in Phase 7 with `annotator: "JZ"`, `annotated_at: "2026-06-11T00:00:00+00:00"`, per-row difficulty (3 for cases 2/3, 4 for parallel-no-convergence + pronoun-reference), and `kit_version: "1.0.0"`. Backup at `tahweel-gold.jsonl.bak-20260616-prephase7`.

---

## Phase 4 — IAA tooling

**Files:** `datasets/hadith-data/__tests__/fixtures/compute_iaa.py`, `docs/annotation/iaa-tooling.md` (1,469 words, 6 sections), `__tests__/__tests__/test_iaa_synthetic.py`.

| Check | Result |
|---|---|
| **Self-test: gold as both annotators** | ✅ **α = 1.0000, κ = 1.0000**, 5 shared hadith_ids, 54 triples, 0 disagreements |
| **G-4 synthetic tests** | ✅ **6/6 PASS** |
| Inline Krippendorff implementation (no PyPI dep) | ✅ ~40 lines, textbook formula (per Risk-C mitigation) |
| Both metrics documented in iaa-tooling.md | ✅ §3 (metrics) + §5 (interpretation) |

---

## Phase 5 — pull script

**Files:** `datasets/hadith-data/__tests__/fixtures/pull_next_candidates.py`, `__tests__/__tests__/test_pull_stratification.py`. Legacy `pull_tahweel_candidates.py` archived under `archive/`.

| Check | Result |
|---|---|
| Real-CSV smoke test (`--n 5 --seed 42`) | ✅ 5 rows across 5 distinct K6 sources (Abu Dawud, Ibn Majah, Tirmidhi, Bukhari, Muslim), no gold overlap |
| Cross-tradition skip log | ✅ stderr emitted 4 WARN lines (imami, zaydi, ibadi, rida) — consistent with Phase 0 audit |
| **G-5 stratification tests** | ✅ **12/12 PASS** |
| Dedup against `tahweel-gold.jsonl` | ✅ `test_dedup_against_gold`, `test_zero_overlap_with_gold` |
| Distribution targets (70/25/5) within tolerance | ✅ `test_distribution_close_to_70_25_5` |
| Seed reproducibility (default 42) | ✅ `test_seed_42_reproducible` |
| `--difficulty-target` heuristic | ✅ `test_difficulty_target_5_picks_3plus` |
| `--exclude-traditions` filter | ✅ `test_exclude_traditions` |

---

## Phase 6 — dogfood

Pull script run: `python pull_next_candidates.py --n 5 --seed 43 --csv all_hadiths_unified.csv --out staging-2026-06-16.jsonl`

| hadith_id | source | hadith_no | ح-count | Why it's a good test |
|---|---|---|---:|---|
| 22456 | Sunan Abi Da'ud | 2455 | 1 | `جميعا عن` idiom — co-transmitter convergence variant |
| 51217 | Sunan Ibn Majah | 1221 | 1 | `قالا حدثنا` — co-transmitters at branch head (case 3) |
| 44413 | Sunan an-Nasa'i | 4397 | 1 | `أنبأنا` (anbāʾanā) variant of transmission verb |
| 4550 | Sahih Bukhari | 4756 | 1 | First Bukhari ح-row pulled by the kit — historically under-represented |
| 11922 | Sahih Muslim | 1943 | 1 | `ابن المثنى، وابن بشار` — natural case 3 (co-transmitter at branch head) |

Cross-tradition skip log: 4 WARN lines (imami, zaydi, ibadi, rida) — consistent with Phase 0 audit.

### G-6: human-annotation pass DEFERRED per Risk-D

`staging-2026-06-16.jsonl` is generated, validates structurally, and is ready for Jade's hand-annotation following the guide. Per Risk-D in the plan ("Jade unavailable for Phase 6 annotation"), the kit ships with the machine-side dogfood complete and the human dogfood as a documented follow-up.

Runbook entry for the follow-up:
- Annotator: JZ (or delegate; delegate must clear calibration first).
- Input: `staging-2026-06-16.jsonl`.
- Steps: fill `expected_branches`/`notes`/`annotator`/`annotated_at`/`difficulty` per guide; run `validate_annotation.py --input staging-2026-06-16.jsonl --strict`; if 5/5 PASS, promote via `--promote --from staging-2026-06-16.jsonl --to ../tahweel-gold.jsonl`; re-run `algo_evaluate.py` from the parent track; record bake-off Δ.
- Expected gain: gold growth 5 → 10, p25 either holds (≥ 0.625) or improves.

### G-1: non-engineer reader pass DEFERRED per Risk-E

No non-engineer test reader was recruited within this session. Deferred to a follow-up gate (consistent with Risk-E's authorization). The guide is structurally ready and skim-readable per NFR-2.

---

## Phase 7 — closeout

| Action | Result |
|---|---|
| Gold backfilled: `annotator`, `annotated_at`, `difficulty`, `kit_version: "1.0.0"` | ✅ All 5 rows. Backup: `tahweel-gold.jsonl.bak-20260616-prephase7` |
| Validator V-9 (`kit_version`) check added | ✅ FAIL on non-semver, WARN on missing |
| Test fixture (Test 1) updated to assert post-backfill state | ✅ `test_existing_gold_content_checks_pass` now asserts V-1..V-9 PASS |
| **Full test sweep across all 4 G-N test files** | ✅ **36/36 PASS** (0.68s) |
| Final validator self-test on backfilled gold | ✅ **5 PASS, 0 WARN, 0 FAIL** |
| Final scorer self-test (gold as submission) | ✅ Aggregate **1.000** |
| Final IAA self-test (gold as both annotators) | ✅ **α = 1.0000, κ = 1.0000** |

---

## Acceptance gate summary

| Gate | Status | Evidence |
|---|---|---|
| **G-1** — Guide readable by non-engineer | ⏳ **DEFERRED** per Risk-E (no reader available this session) |
| **G-2** — Calibration scorer detects canonical errors | ✅ **PASSED** — 5/5 planted-error tests pass |
| **G-3** — Validator catches the canonical bugs | ✅ **PASSED** — 13/13 planted-error tests pass |
| **G-4** — IAA tooling works on synthetic disagreement | ✅ **PASSED** — 6/6 synthetic tests pass; self-test α=κ=1.0 |
| **G-5** — Pull script enforces diversity | ✅ **PASSED** — 12/12 tests pass; smoke produced 5 K6 sources, 0 gold overlap |
| **G-6** — End-to-end first batch (dogfood) | ⏳ **MACHINE-SIDE PASSED; HUMAN-SIDE DEFERRED** per Risk-D |

**Net:** 4 of 6 gates fully passed; 2 deferred with explicit Risk-D/E authorization. **The kit is shippable.**

---

## Follow-up tracks to file

1. **`tahweel_gold_expansion_2026q3`** — Execute the deferred G-6 human pass against `staging-2026-06-16.jsonl`. Grow gold 5 → 10 → 30+.
2. **`tahweel_kit_g1_readability_check`** — Recruit one non-engineer hadith-literate reader. Run G-1.
3. **`tahweel_llm_draft_runtime`** — Ship the FR-6 LLM-draft script that guide §9 documents but doesn't include. Reuse sibling tier-2 track's prompt baseline.
4. **`tahweel_gold_expansion_imami`** — If/when Imami `arabicText` ح-bearing rows enter the corpus, extend the kit's tradition coverage.

---

## Files shipped

```
docs/annotation/
    tahweel-annotation-guide.md             ✅ 6,658 words, 9 sections
    calibration-test.md                     ✅ ~450 words, instructions
    calibration-test.jsonl                  ✅ 5 redacted rows
    .calibration-gold.jsonl                 ✅ 5,516 bytes (= gold)
    iaa-tooling.md                          ✅ 1,469 words, 6 sections

datasets/hadith-data/__tests__/fixtures/
    pull_next_candidates.py                 ✅ FR-2 (Phase 5)
    validate_annotation.py                  ✅ FR-3 + V-9 (Phase 3+7)
    score_calibration.py                    ✅ FR-4 (Phase 2)
    compute_iaa.py                          ✅ FR-5 (Phase 4)
    tahweel-gold.jsonl                      ✅ 5 rows + kit_version + metadata
    tahweel-gold.jsonl.bak-20260616-prephase7  ✅ pre-backfill backup
    staging-2026-06-16.jsonl                ✅ Phase 6 dogfood candidates
    validation-2026-06-16.md                ✅ Phase 6 validator report
    archive/
        pull_tahweel_candidates.py          ✅ legacy script archived
    __tests__/
        test_pull_stratification.py         ✅ G-5  (12 tests)
        test_validator_planted_errors.py    ✅ G-3  (13 tests)
        test_calibration_planted_errors.py  ✅ G-2  (5 tests)
        test_iaa_synthetic.py               ✅ G-4  (6 tests)
```

**Total tests: 36 PASS / 0 FAIL** (0.68s wall).
