# Plan: Taḥwīl-Aware Isnad Gold-Set Annotation Instruction Kit + SOP

**Track:** `tahweel_annotation_kit_20260612`
**Spec:** `./spec.md`
**Created:** 2026-06-12
**Estimated wall time:** ~19.5 hrs of focused work (writing-heavy; ~6 hrs is the guide draft alone) + ~3 hrs of Jade annotation time during Phase 6 dogfood
**Research basis:** `.omc/research/uniform-isnad/research-session/report.md`, `.omc/research/uniform-isnad/research-session/stages/stage-3-formal-grammar.md` (Ibn al-Salah ambiguity)

---

## Phase 0 — Audit + scaffolding (~1 hr)

Inventory the existing 5 fixtures, the existing pull script, and the bake-off harness. Identify which case-types from §2.3 are already covered by the gold fixtures and which need newly-found examples (specifically the 3+-branch pathological case from FR-1.2 §3 / case type 7).

- [ ] **T-0.1** — Re-read `datasets/hadith-data/__tests__/fixtures/tahweel-gold.jsonl` (existing 5 rows). For each row, tag which of the 7 canonical case types it exemplifies. Output: a short table in `verification.md` mapping `hadith_id → case_type(s)`. (P0, ~10 min)
- [ ] **T-0.2** — Run `audit_tahweel_stats.py` against the unified CSV restricted to Imami (`arabicText` path), Zaydi (Musnad Zayd), and Ibadi (Tartib al-Jami al-Sahih) sources. Count ح-occurrences per source. Output: `.omc/research/uniform-isnad/non-sunni-tahweel-audit.md`. This answers spec Q1 and determines whether NFR-5 is "include examples" or "document absence". (P0, ~20 min)
- [ ] **T-0.3** — Grep the unified CSV for 3+-ح rows in Ṣaḥīḥ Muslim. Pick ONE as the canonical case-type-7 example for the guide. Record `(hadith_id, source, hadith_no, text_ar)` in a scratch file. (P0, ~15 min)
- [ ] **T-0.4** — Scaffold the directory layout:
  ```
  docs/annotation/
      tahweel-annotation-guide.md            # FR-1, empty header
      calibration-test.md                    # FR-4, empty header
      calibration-test.jsonl                 # FR-4, empty
      .calibration-gold.jsonl                # FR-4, empty (dotfile)
      iaa-tooling.md                         # FR-5, empty header
  datasets/hadith-data/__tests__/fixtures/
      pull_next_candidates.py                # FR-2, empty
      validate_annotation.py                 # FR-3, empty
      score_calibration.py                   # FR-4, empty
      compute_iaa.py                         # FR-5, empty
      archive/
          pull_tahweel_candidates.py         # moved from parent dir (FR-2.1)
      __tests__/
          test_pull_stratification.py        # G-5
          test_validator_planted_errors.py   # G-3
          test_calibration_planted_errors.py # G-2
          test_iaa_synthetic.py              # G-4
  ```
  Move (not delete, per `[[feedback_no_delete_backup]]`) `pull_tahweel_candidates.py` to `archive/`. (P0, ~10 min)
- [ ] **T-0.5** — Verification checkpoint. Confirm scratch files are populated for T-0.1 / T-0.2 / T-0.3, scaffolds exist, archive move is clean. [checkpoint marker] (P0, ~5 min)

**Gate Φ-0:** Audit data captured. Case-type-7 example chosen. Non-Sunni taḥwīl counts known. Directory scaffolds in place. Spec Q1 has a concrete answer.

## Phase 1 — Write the annotation guide draft (Deliverable 1, ~6 hrs)

The biggest deliverable in the track. Most of this is prose; the tooling phases (2-5) lean on the guide as their reference.

- [ ] **T-1.1** — Write §1 (What we're annotating and why) of `docs/annotation/tahweel-annotation-guide.md`. Plain-language framing per spec §1.2. ~500 words. (P0, ~30 min)
- [ ] **T-1.2** — Write §2 (The annotation contract). Per-field documentation of the JSONL schema. Explicit "do not modify" vs "you fill in" split. ~400 words + a schema table. (P0, ~30 min)
- [ ] **T-1.3** — Write §3 (The seven canonical case types). One subsection per type. Each subsection: Arabic example from a real fixture, the JSON expected_branches, 2-3 lines of reasoning, ASCII chain diagram. Use Tirmidhi #1 (case 2), Muslim #1 (case 4), Muslim #2 (case 3), Muslim #31 (case 5), Muslim #102 (case 6) — already-annotated. Find a 1-branch row from the unified CSV for case 1. Use the T-0.3 hadith for case 7. (P0, ~2.5 hrs — the longest sub-task)
- [ ] **T-1.4** — Write §4 (Decision tree for hard cases). The 5 named decision points from spec FR-1.2 §4 verbatim, each with a worked example illustrating the rule. (P0, ~45 min)
- [ ] **T-1.5** — Write §5 (Annotation quality checklist). The 7 bullets from the brief. Each bullet is one sentence + one example of what failure looks like. (P0, ~20 min)
- [ ] **T-1.6** — Write §6 (Calibration set workflow), §7 (IAA metric — Krippendorff justification per TC-2), §8 (HALAL / scope framing per NFR-4), §9 (LLM-assisted draft annotation workflow per FR-6). Pointers to the tooling phases. (P0, ~45 min)
- [ ] **T-1.7** — Self-review the guide against NFR-1 (no forbidden jargon: "Jaccard", "set intersection", "LCS", "Levenshtein", "regex"). Run a search for those terms; replace with plain-language equivalents. (P0, ~15 min)
- [ ] **T-1.8** — Verification checkpoint. Read the guide end-to-end. Confirm every required section from FR-1.2 §1-9 is present and that worked examples are SHOWN, not described (NFR-2). [checkpoint marker] (P0, ~15 min)

**Gate Φ-1:** Guide v1 draft is complete, lint-free on the forbidden-jargon check, and contains worked examples + diagrams for all 7 case types. Ready for the G-1 human-loop test (deferred to Phase 6 — needs a non-engineer reader).

## Phase 2 — Build the calibration test (Deliverable 4, ~2 hrs)

The first tooling phase. Redact the existing 5 gold rows into a calibration JSONL; build the scorer.

- [ ] **T-2.1** — Generate `docs/annotation/calibration-test.jsonl` from `tahweel-gold.jsonl`: copy each row, set `expected_branches = null`, `notes = ""`, `annotator = ""`, `annotated_at = ""`, `difficulty = null`. Preserve `hadith_id`, `source`, `hadith_no`, `tahweel_count`, `text_ar`, `sanad`. (P0, ~15 min)
- [ ] **T-2.2** — Generate `docs/annotation/.calibration-gold.jsonl` from `tahweel-gold.jsonl` (the full file; serves as the hidden answer key). Document in the guide §6 that this dotfile must not be opened before the annotator submits. (P0, ~5 min)
- [ ] **T-2.3** — Write `docs/annotation/calibration-test.md` — the human-facing instructions for the calibration test: "Open the JSONL, fill in `expected_branches` for each of the 5 rows following the guide, save as `<your-name>-calibration.jsonl`, then run `score_calibration.py --submission <your-file>.jsonl`." (P0, ~20 min)
- [ ] **T-2.4** — Implement `score_calibration.py` per FR-4.3 / FR-4.5: per-fixture Jaccard between submission's `expected_branches` and gold's, aggregate as mean. Output a Markdown report at `docs/annotation/calibration-result-<annotator-id>-<date>.md`. Import `_norm` from `regen_unified_csvs.py` (spec Q5). (P0, ~45 min)
- [ ] **T-2.5** — Write `__tests__/test_calibration_planted_errors.py` per G-2: build a planted-error submission (e.g., swap Branch A and Branch B narrator orders on Tirmidhi #1); assert the aggregate score < 0.85 and the affected row is flagged as lowest-scoring. ≥ 3 planted-error tests. (P0, ~30 min)
- [ ] **T-2.6** — Verification checkpoint. Run `score_calibration.py` against the gold itself (perfect submission); assert aggregate = 1.0. Run against the planted-error file; assert < 0.85. [checkpoint marker] (P0, ~10 min)

**Gate Φ-2:** Calibration test infrastructure works end-to-end. G-2 test passes. Self-test (gold submitted as own answer) produces 1.0.

## Phase 3 — Build the annotation validator (Deliverable 3, ~3 hrs)

The single linter that gates entry to `tahweel-gold.jsonl`.

- [ ] **T-3.1** — Implement V-1 through V-8 checks per FR-3.2 in `validate_annotation.py`. Each check is a function `check_v<N>(row) → (status, message)` where status is `"PASS" | "WARN" | "FAIL"`. (P0, ~90 min)
  - V-1: `expected_branches` non-null + correct type
  - V-2: every surface in `text_ar` after `_norm` (the canonical bug)
  - V-3: `len(expected_branches) == tahweel_count + 1` (with `difficulty=5` bypass)
  - V-4: convergence consistency (WARN by default, FAIL under `--strict`)
  - V-5: no matn-internal text (uses `MATN_ANCHORS` from `algo_candidates/_common.py`)
  - V-6: `difficulty ∈ [1, 5]`
  - V-7: `annotator` non-empty
  - V-8: `annotated_at` parseable ISO-8601
- [ ] **T-3.2** — Implement the Markdown report writer per FR-3.3. One section per row; aggregate summary at top (pass rate, fail reason histogram). Output path defaults to `datasets/hadith-data/__tests__/fixtures/validation-<YYYY-MM-DD>.md`. (P0, ~30 min)
- [ ] **T-3.3** — Implement the `--promote --from <staging.jsonl> --to <gold.jsonl>` mode per FR-3.6. Runs validation; refuses to promote failing rows; backs up `tahweel-gold.jsonl.bak-<ts>` before appending. (P0, ~30 min)
- [ ] **T-3.4** — Implement CLI per FR-3.4: `--input`, `--strict`, `--out`, exit codes. (P0, ~15 min)
- [ ] **T-3.5** — Write `__tests__/test_validator_planted_errors.py` per G-3: 5 planted-error fixtures covering V-2, V-3, V-4, V-5, V-7. Each one asserts the correct check ID is flagged. ≥ 7 tests total (5 planted + 2 sanity controls). (P0, ~45 min)
- [ ] **T-3.6** — Verification checkpoint. Run `validate_annotation.py --input tahweel-gold.jsonl`. Assert all 5 existing rows pass all checks. (If a check flags an existing row as bad, either fix the row OR fix the check — the existing 5 are the ground truth.) [checkpoint marker] (P0, ~10 min)

**Gate Φ-3:** Validator passes on the existing gold fixtures. G-3 tests pass. Promotion flow works end-to-end with backup.

## Phase 4 — Build the IAA tooling (Deliverable 5, ~2 hrs)

Krippendorff's α computation over (hadith_id, branch_index, position) triples.

- [ ] **T-4.1** — Implement `compute_iaa.py` per FR-5.2 / FR-5.4. Reads ≥2 JSONL annotation files. For each `hadith_id` present in ≥2 files, expand to triples `(hadith_id, branch_index, position) → surface_form`. Compute Krippendorff α with binary distance (`0` if normalized surfaces match, `1` otherwise). (P0, ~60 min)
  - Use the `krippendorff` PyPI package OR implement the textbook formula inline (≤30 lines). Document the choice in the script header.
- [ ] **T-4.2** — Implement the disagreement-detail renderer per FR-5.2 bullet 2: when annotators differ on a triple, render side-by-side as a Markdown table row with both surface forms + the `hadith_id` link. (P0, ~30 min)
- [ ] **T-4.3** — Implement the aggregate pass-rate calculation per FR-5.2 bullet 3. Output path: `docs/annotation/iaa-report-<date>.md`. (P0, ~15 min)
- [ ] **T-4.4** — Write `docs/annotation/iaa-tooling.md` — human-facing doc explaining when to run IAA (after 2+ annotators have overlapping rows), how to interpret α, the threshold (0.80), the unit-of-analysis (triple), the distance metric. Per FR-5.3. ~600 words. (P0, ~30 min)
- [ ] **T-4.5** — Write `__tests__/test_iaa_synthetic.py` per G-4: generate two synthetic annotation files with deterministic seed where ~30% of triples disagree. Assert computed α is in [0.65, 0.75] (analytically tractable for the deterministic seed). ≥ 4 tests covering perfect agreement, perfect disagreement, mid disagreement, missing-units edge case. (P0, ~30 min)
- [ ] **T-4.6** — Verification checkpoint. Run `compute_iaa.py` on two copies of `tahweel-gold.jsonl` (same file given as both annotators); assert α = 1.0. [checkpoint marker] (P0, ~5 min)

**Gate Φ-4:** IAA tooling passes G-4 synthetic test. Self-test (same file as both annotators) produces α = 1.0. Disagreement detail rendering is readable.

## Phase 5 — Build the next-candidate pull script (Deliverable 2, ~2 hrs)

Extension of the existing legacy pull script. Adds dedup, cross-tradition coverage, `--difficulty-target`.

- [ ] **T-5.1** — Port the source-stratification + ح-count-stratification logic from `archive/pull_tahweel_candidates.py` into `pull_next_candidates.py`. Refactor into helper functions; preserve the existing 60/30/10 → 70/25/5 distribution target (the spec's FR-2.2 target is tighter than the legacy 60/30/10). (P0, ~30 min)
- [ ] **T-5.2** — Add dedup logic per FR-2.2: read `tahweel-gold.jsonl`, build a set of `(source, hadith_no)` already annotated, exclude from the candidate pool. (P0, ~15 min)
- [ ] **T-5.3** — Add cross-tradition coverage per FR-2.2: query the unified CSV for `arabicText`-bearing rows (Imami) and Musnad Zayd / Tartib al-Jami rows (Zaydi / Ibadi). If T-0.2 found zero taḥwīl rows in a tradition, log to stderr and skip (best-effort, not blocking). (P0, ~30 min)
- [ ] **T-5.4** — Add `--difficulty-target N` flag per FR-2.2 bullet 4. Heuristic: difficulty 1-2 = single-ح; 3-4 = 2-ح; 5 = 3+-ح. Document the heuristic in the script header. (P0, ~20 min)
- [ ] **T-5.5** — Add CLI per FR-2.4: `--n`, `--difficulty-target`, `--seed` (default 42 per TC-7), `--exclude-traditions`. Output to `staging-<YYYY-MM-DD>.jsonl` per FR-2.3 with the full schema (expected_branches/notes/annotator/annotated_at/difficulty fields present but unfilled). (P0, ~30 min)
- [ ] **T-5.6** — Write `__tests__/test_pull_stratification.py` per G-5: run `pull_next_candidates.py --n 30 --seed 42` against a mock CSV, assert:
  - No single source > 50% of rows (where source has enough rows).
  - ح-count distribution within tolerance.
  - Zero overlap with the existing 5 gold fixtures.
  - At least one non-Sunni-K6 row IF T-0.2 found any.
  ≥ 5 tests. (P0, ~45 min)
- [ ] **T-5.7** — Verification checkpoint. Run `pull_next_candidates.py --n 5 --seed 42` against the real unified CSV. Inspect the output — 5 rows with the expected schema, none overlapping the existing gold. [checkpoint marker] (P0, ~10 min)

**Gate Φ-5:** Pull script generates a staging JSONL with the expected stratification + dedup. G-5 tests pass. Output is reproducible with seed=42.

## Phase 6 — Dogfood: end-to-end first batch (~3 hrs)

The G-6 test. The kit-actually-works pass. This is **the** acceptance test for the track.

- [ ] **T-6.1** — Run `pull_next_candidates.py --n 5 --seed 43` (seed 43 to differ from G-5's seed=42 test set). Outputs `staging-2026-06-XX.jsonl` with 5 unannotated candidates. (P0, ~5 min)
- [ ] **T-6.2** — Jade (or delegate) hand-annotates the 5 candidates following `tahweel-annotation-guide.md`. Fills `expected_branches`, `notes`, `annotator: "JZ"`, `annotated_at`, `difficulty`. Records any guide-readability friction or ambiguity in a scratch file `phase-6-annotation-notes.md`. (P0, ~2 hrs — Jade's annotation time)
- [ ] **T-6.3** — Run `validate_annotation.py --input staging-2026-06-XX.jsonl --strict`. Expectation: all 5 rows pass. If any fail, fix the annotation OR the validator (whichever is bug). (P0, ~15 min)
- [ ] **T-6.4** — Promote: `validate_annotation.py --promote --from staging-2026-06-XX.jsonl --to ../tahweel-gold.jsonl`. Backup is auto-created. `tahweel-gold.jsonl` now has 10 rows. (P0, ~5 min)
- [ ] **T-6.5** — Re-run the parent track's `algo_evaluate.py` (candidate C / `lcs_suffix`) against the expanded gold. Capture: branch-count accuracy, Jaccard median, Jaccard p25, Jaccard mean. Compare to the 5-row baseline (median=0.845, p25=0.625, mean=0.776 per parent spec FR-1.1). Assertions per G-6: branch-count accuracy holds at 1.000; p25 either holds (≥ 0.625) or improves. (P0, ~15 min)
- [ ] **T-6.6** — **G-1 readability check (the human-loop gate).** Recruit one human test reader with hadith knowledge but no programming background. Hand them `tahweel-annotation-guide.md` + `calibration-test.jsonl` (subset of 2 rows for time). Score their submissions via `score_calibration.py`. Pass: both rows ≥ 0.85 Jaccard. Record reader's first-name initial + date in `verification.md`. If the reader hits friction, document the friction and EITHER patch the guide OR document the gap as a known limitation. (P0, ~30 min — depends on reader availability; may push to Phase 7 if reader unavailable)
- [ ] **T-6.7** — Verification checkpoint. `verification.md` documents:
  - The 5 new rows that landed in gold (with `hadith_id`s and case-type labels).
  - The bake-off delta (numbers).
  - The G-1 reader's score (or "deferred to follow-up" if unavailable).
  - Any annotation friction recorded in T-6.2's notes.
  [checkpoint marker] (P0, ~15 min)

**Gate Φ-6:** Gold set grew from 5 → 10 with zero validator failures. Bake-off Jaccard p25 holds or improves. G-1 reader passed (or documented as deferred). The kit demonstrably works.

## Phase 7 — Closeout (~30 min)

- [ ] **T-7.1** — Add the per-row `kit_version: "1.0.0"` field to all rows in `tahweel-gold.jsonl` per spec Q4. Update the validator to check the field. (P0, ~10 min)
- [ ] **T-7.2** — Update `conductor/tracks.md` with `[x]` and a 3-line post-results summary (gold set grew 5 → 10, all 6 guardrails passed, reader passed G-1 readability). (P0, ~5 min)
- [ ] **T-7.3** — Write `verification.md` with concrete evidence for each of G-1 through G-6 (test names, scorer outputs, reader's initial + date, bake-off comparison table). (P0, ~10 min)
- [ ] **T-7.4** — File follow-up tracks:
  - `tahweel_gold_expansion_2026q3` — grow gold from 10 → 30 using this kit.
  - `tahweel_llm_draft_runtime_<date>` — ship the FR-6 LLM-draft script (deferred per TC-8).
  - `tahweel_gold_expansion_imami_<date>` — Imami `arabicText`-source expansion (if T-0.2 found qualifying rows).
  (P0, ~5 min)

**Gate Φ-7:** Track closed. Follow-ups filed. `verification.md` shipped.

---

## Out-of-band risks + mitigations

**Risk-A — The 3+-branch case-type-7 example doesn't exist in Phase 0.** The brief says 49 such rows exist in Ṣaḥīḥ Muslim per parent-track audit. If T-0.3 can't find one quickly, fall back to a 2-branch with nested ح ("ح وحدثنا … ح وحدثنا" pattern) for the example. Mitigation: confirm in T-0.3 before Phase 1.

**Risk-B — Non-Sunni traditions have zero taḥwīl rows.** If T-0.2 confirms zero, NFR-5's "at least 1 from Zaydi or Ibadi" flips to "documented absence". The guide section becomes "Why this guide is Sunni-K6-centric" + a citation to the audit. Mitigation: documented in spec Q1; not blocking.

**Risk-C — Krippendorff's α library dependency.** The `krippendorff` PyPI package is reliable but adds a dependency. Alternative: implement the textbook formula inline (≤30 lines). T-4.1 makes the choice; favor inline if dependency creep is a concern.

**Risk-D — Jade unavailable for Phase 6 annotation.** The 2-hour annotation window depends on Jade's time. Mitigation: delegate is acceptable (any of the prior calibration-passing annotators). If no delegate, defer Phase 6 to a follow-up runbook; ship the track with G-6 marked as "deferred" and the kit otherwise complete. Document in `tracks.md`.

**Risk-E — Non-engineer reader for G-1 unavailable.** Same shape as Risk-D. Acceptable to defer G-1 to a follow-up gate; ship the track with the readability gate as "deferred, to be tested when reader available." Document explicitly.

**Risk-F — V-2 false positives on diacritics or honorifics.** A surface like `سفيان` in the gold but the text says `سفيانَ` (with diacritic) — `_norm` should strip diacritics, but if it doesn't, V-2 hard-fails a legitimate annotation. Mitigation: T-3.6 verification step catches this against the known-good 5 rows; if it fails, the bug is in `_norm` or the check, not the annotation, and gets fixed accordingly.

**Risk-G — Calibration scorer is too strict at 0.85.** If the existing 5 fixtures themselves don't form a self-consistent ground truth (e.g., Jade's annotation philosophy drifted between row 1 and row 5), a perfectly-following annotator could still score < 0.85. Mitigation: T-0.1 reviews internal consistency of the 5 rows. If inconsistencies surface, EITHER (a) fix the gold rows to be consistent, OR (b) lower the threshold to 0.80 and document. Decide before Phase 2.

## Total estimated wall time

| Phase | Active hrs |
|---|---|
| 0 — Audit + scaffolding | 1 |
| 1 — Annotation guide draft | 6 |
| 2 — Calibration test | 2 |
| 3 — Validator | 3 |
| 4 — IAA tooling | 2 |
| 5 — Pull script | 2 |
| 6 — Dogfood (incl. ~2hr Jade annotation + 0.5hr reader) | 3 |
| 7 — Closeout | 0.5 |
| **Total** | **19.5 hr** |

Net ~2.5 focused days. The guide draft (Phase 1) is the dominant cost; the four tools are each a half-day or less. The dogfood phase (Phase 6) is the load-bearing acceptance test — it proves the kit works by actually using it to grow the gold set 5 → 10 with zero validator failures and no bake-off regression.

The downstream win: the gold set becomes a growable artifact rather than a heroic one-off. Both parent extraction tracks (uniform + tier-2) tighten their acceptance gates as the gold grows; future contributors have a calibration-gated path in.
