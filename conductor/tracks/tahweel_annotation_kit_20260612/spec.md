# Specification: Taḥwīl-Aware Isnad Gold-Set Annotation Instruction Kit + SOP

**Track ID:** `tahweel_annotation_kit_20260612`
**Type:** Feature (documentation + tooling — annotation pipeline)
**Priority:** P1 (unblocks gold-set growth; non-blocking for either parent track but high leverage for both)
**Created:** 2026-06-12
**Depends on:** Nothing (parallel-safe with both extraction tracks)
**Blocks:** Nothing strictly (enables `tahweel_gold_expansion_*` follow-up tracks; the larger gold set tightens both parent tracks' acceptance gates)
**Parallel-safe with:** `uniform_isnad_extraction_20260609`, `tier2_llm_isnad_reconciliation_20260612`

---

## 1. Overview

Produce the **canonical documentation + tooling kit** that makes manual annotation of taḥwīl-marked hadith fixtures (`datasets/hadith-data/__tests__/fixtures/tahweel-gold.jsonl`) repeatable, teachable, and quality-checked. The current 5-fixture gold set was hand-annotated by Jade (project lead, an Islamic scholar) as a one-off effort. This track produces the kit that lets future annotators — Islamic studies students, fellow scholars, optionally LLM-assisted draft annotation under human verification — grow the gold set from 5 → 30 → 100+ fixtures without re-burning Jade's time per row.

The track ships **five deliverables** (one guide, four tools), all versioned in git as docs/code rather than as a stale wiki. The kit is itself the source of truth for "how do we annotate"; future expansion tracks reference it.

### 1.1 Audience split (load-bearing)

This spec.md targets **engineers** building the kit (numbered FRs, NFRs, lettered guardrails — same shape as the parent extractor track's spec).

The **deliverable guide it produces** (`docs/annotation/tahweel-annotation-guide.md`) targets a **different audience**: Islamic studies graduate students or fellow scholars with hadith knowledge but **no programming literacy**. NFR-1 enforces that audience-shift in the deliverable's prose.

### 1.2 What "annotation" means in this kit

For every JSONL row in `tahweel-gold.jsonl`, the annotator fills `expected_branches: list[list[str]]` — the ground-truth ordered list-of-lists of narrator **surface forms exactly as they appear in `text_ar`**. This is a **descriptive linguistic extraction**, not prescriptive ḥadīth science. Annotators are NOT making rijāl judgments about reliability; they are recording what the text literally says about chain structure. NFR-4 makes this scholarly framing explicit in the guide.

Resolver / normalisation (mapping `سفيان` → `سفيان بن عيينة` → `scholar_indx`) is **downstream**. The gold set is the input to the parent tracks' resolver evaluation, not the output of it.

## 2. Background

### 2.1 What exists today

| Artifact | Path | State |
|---|---|---|
| Gold fixtures | `datasets/hadith-data/__tests__/fixtures/tahweel-gold.jsonl` | 5 hand-annotated rows: Tirmidhi #1, Muslim #1/2/31/102 |
| Pull script (legacy) | `datasets/hadith-data/__tests__/fixtures/pull_tahweel_candidates.py` | Stratified by source + ح-count; no de-duplication; no cross-tradition coverage |
| Candidate sidecar | `datasets/hadith-data/__tests__/fixtures/tahweel-gold-candidates.jsonl` | Output of the legacy pull script; serves as raw input for annotation |
| Algorithm evaluation harness | `datasets/hadith-data/algo_evaluate.py` (from parent track Phase 0) | Consumes `tahweel-gold.jsonl`; the gold set drives the bake-off |
| Annotation guide | — | **Does not exist.** This track creates it. |
| Validator | — | **Does not exist.** This track creates it. |
| Calibration test | — | **Does not exist.** This track creates it. |
| IAA tooling | — | **Does not exist.** This track creates it. |

### 2.2 Why the kit matters for the parent tracks

- **`uniform_isnad_extraction_20260609`** picks the algorithm winner (candidate C / `lcs_suffix`) via the bake-off against the 5-fixture gold set. The research findings (`.omc/research/uniform-isnad/research-session/report.md`) flag **Jaccard p25 = 0.625** as a robustness concern: it's the lowest-scoring 25% of rows that determine the floor. More fixtures (especially the pathological 3+-branch cases and the surface-form-drift cases) tighten the p25 estimate and give the bake-off statistical legitimacy.

- **`tier2_llm_isnad_reconciliation_20260612`** calibrates its suspicion-detector thresholds against the gold set (Phase 0, T-0.1). The hand-authored `tahweel-gold-disagreements.jsonl` is a small adjunct; the broader the underlying gold set, the better the trigger-rate projections.

- **Both tracks' G-1/G-2/G-3 acceptance criteria** assume the gold set is correct. A gold set authored by a single annotator with no validation pass is one author bug from a wrong "correct" — the validator (D-3) catches the canonical mistakes, the IAA tooling (D-5) measures inter-annotator agreement once a second person joins.

### 2.3 The seven canonical case types

Drawn from the 5 existing fixtures + the parent track's corpus audit. The guide must cover all seven with worked Arabic examples + the actual JSON expected_branches + 2-3 lines of reasoning per case.

| # | Case type | Frequency in corpus | Worked example | Why it's hard |
|---|---|---|---|---|
| 1 | Single chain, no taḥwīl | ~98.2% of all rows (incl. all Musnad Ahmad, Al-Kāfī, Nahj al-Balāgha) | Any 1-branch row | Trivial; baseline |
| 2 | Classic 2-branch with convergence | Most Sunni K6 taḥwīl | Tirmidhi #1 | Branch A's tail comes from Branch B's post-convergence segment |
| 3 | 2-branch with co-transmitter at branch head | Common in Muslim | Muslim #2 (محمد بن المثنى AND ابن بشار together) | Two compiler-narrators at one branch's head |
| 4 | 2-branch parallel-but-no-convergence | A meaningful minority | Muslim #1 | Both branches share the SAME compiler-narrator but tail through entirely different downstream narrators — naive set intersection breaks |
| 5 | 2-branch with surface-form drift | Frequent | Muslim #31 (سفيان ↔ سفيان بن عيينة); Tirmidhi #1 (سماك ↔ سماك بن حرب) | Same person, different surface form across branches |
| 6 | 2-branch with pronoun/elided refs | Occasional | Muslim #102 (أبي meaning معاذ) | Annotator records the surface (`أبي`), NOT the resolved name |
| 7 | 3+-branch pathological | 49 rows in Ṣaḥīḥ Muslim alone per parent-track audit | TBD — find one in Phase 0 and annotate | Multiple convergences, may have nested ح |

## 3. Functional Requirements

### FR-1 — The annotation guide (Deliverable 1)

**FR-1.1** — Create `docs/annotation/tahweel-annotation-guide.md`. The guide is the **single source of truth** for how taḥwīl annotation is performed in this project. Future tracks needing a larger gold set link to this file.

**FR-1.2** — Required sections, in order:

1. **What we're annotating and why** — Plain-language framing per §1.2. Explicitly says: "This is a 'what does the text say' exercise, NOT a 'who is this person' exercise."
2. **The annotation contract** — Per-field documentation of the JSONL row schema. Fields the annotator MUST fill: `expected_branches`, `notes`, `annotator`, `annotated_at`, `difficulty`. Fields the annotator MUST NOT modify: `hadith_id`, `source`, `hadith_no`, `tahweel_count`, `text_ar`, `sanad`.
3. **The seven canonical case types** — Section §2.3's table expanded into per-case subsections. Each subsection contains: (a) one full Arabic example from `text_ar`, (b) the actual `expected_branches` JSON the annotator would write, (c) 2-3 lines of reasoning, (d) an ASCII diagram of the chain topology for cases 2-7.
4. **Decision tree for hard cases** — Per the brief, 5 named decision points:
   - "If you can't tell where the matn starts, look for the first `قال` / `قال رسول الله` / `قال أبو عبد الله` / `عن النبي` / `عن رسول الله` matn-attaching cue and stop the chain there."
   - "If two branches genuinely don't share narrators, that's Case 4 — keep them as separate parallel chains, do NOT force a shared suffix."
   - "If the same narrator appears with three different surface forms, record each surface form as the text says; the resolver downstream will unify them."
   - "If a pronoun like أبي or عنه has no clear referent in the text, record the pronoun as the surface form. Resolving it is the upstream resolver's job (see Muslim #102)."
   - "If the text has scholarly ambiguity (Ibn al-Salah's two readings of ح — تحويل vs الحديث), flag it as `difficulty: 5`, record your reasoning in `notes`, and **do NOT guess**. Genuinely-ambiguous rows are a documented out-of-band class per `.omc/research/uniform-isnad/research-session/stages/stage-3-formal-grammar.md`."
5. **Annotation quality checklist** — Pre-submission self-review, exactly the 7 bullets in the brief.
6. **Calibration set** — Pointer to D-4 (the redacted-gold calibration test). Documents the workflow: new annotator MUST score ≥0.85 average Jaccard on the 5-fixture calibration test before contributing real annotations.
7. **Inter-annotator agreement (IAA) metric** — Pointer to D-5. Documents that **Krippendorff's alpha** is the chosen metric (justification in §7 TC-2 below). Threshold: pairwise ≥ 0.80 for the row pair to be considered consensus-validated.
8. **HALAL / scope framing** (NFR-4) — Explicit statement: annotators are linguistic extractors, NOT muḥaddithīn. They are not issuing rijāl verdicts or making authenticity judgments. The work is descriptive.
9. **LLM-assisted draft annotation (optional)** — Documented workflow for using Claude Sonnet as a draft annotator (FR-6). Cost note (~$0.005/row). Explicit framing: LLM drafts are **starting points, not authoritative answers** — human always verifies.

**FR-1.3** — Worked examples are **shown, not described** (NFR-2). Every case-type subsection includes the full Arabic + the JSON + a topology diagram. The guide should be skim-readable: a new annotator should be able to flip to "Case 4: parallel-but-no-convergence" and find a complete worked example without reading the rest of the document.

### FR-2 — The next-candidate pull script (Deliverable 2)

**FR-2.1** — Create `datasets/hadith-data/__tests__/fixtures/pull_next_candidates.py`. Replaces `pull_tahweel_candidates.py` (which moves to `archive/`).

**FR-2.2** — Stratification dimensions the script enforces:
- **Source diversity** — At least one candidate per K6 Sunni source (Bukhari, Muslim, Tirmidhi, Abu Dawud, Ibn Majah, Nasai) plus at least one Imami (via `arabicText` field, Al-Kāfī or other Thaqalayn v2_books rows where ح appears) plus at least one Zaydi (Musnad Zayd) plus at least one Ibadi (Tartib al-Jami al-Sahih), IF such taḥwīl rows exist in that tradition. If a tradition has zero taḥwīl rows in the corpus, the script logs that fact in stderr and skips it cleanly. Cross-tradition coverage is **best-effort**, not blocking.
- **ح-count distribution** — Targets ~70% single-ح, ~25% 2-ح, ~5% 3+-ح. This matches the per-corpus distribution per the audit in `audit_tahweel_stats.py`.
- **Already-annotated dedup** — Reads `tahweel-gold.jsonl`, builds a set of `(source, hadith_no)` already annotated, excludes them from the candidate pool.
- **Optional `--difficulty-target N`** — Filters to rows whose ح-count / source / parser-difficulty heuristic suggests a target difficulty band. Cheap heuristic acceptable.

**FR-2.3** — Output: `datasets/hadith-data/__tests__/fixtures/staging-<YYYY-MM-DD>.jsonl`. Each row has the full schema (per FR-3.1) with `expected_branches: null`, `notes: ""`, `annotator: ""`, `annotated_at: ""`, `difficulty: null`. Annotator fills in their copy, validates (FR-3), and then promotes to `tahweel-gold.jsonl` via a `--promote` mode (FR-3.6) — staging never silently overwrites gold.

**FR-2.4** — CLI signature:
```
python pull_next_candidates.py --n 30 [--difficulty-target 3] [--seed N] [--exclude-traditions zaydi,ibadi]
```
Reproducible via `--seed`. Default seed is `42` for repeatability of the "first 30" batch.

### FR-3 — The annotation validator (Deliverable 3)

**FR-3.1** — Create `datasets/hadith-data/__tests__/fixtures/validate_annotation.py`. Lints any annotated JSONL file (`tahweel-gold.jsonl`, `staging-*.jsonl`, calibration submissions) for the canonical errors.

**FR-3.2** — Per-row checks the validator enforces:

| ID | Check | Failure mode |
|---|---|---|
| V-1 | `expected_branches` is non-null and a `list[list[str]]` | Hard fail |
| V-2 | Every narrator surface in `expected_branches` appears VERBATIM in `text_ar` after passing through `_norm` (the existing normalizer from `regen_unified_csvs.py`) | Hard fail; the canonical bug is "annotator imported the resolved name into the surface column" |
| V-3 | `len(expected_branches) == tahweel_count + 1` UNLESS `difficulty == 5` and `notes` contains an explanation | Hard fail with bypass |
| V-4 | Convergence consistency: if narrator surface X (after `_norm`) appears in branch[0] and branch[1], it appears at positions p0, p1 where p0 and p1 are both **after** the first divergence point. Order-preserving. | Warning if positions look swapped |
| V-5 | No matn-internal text in `expected_branches` — the validator finds the first matn anchor (`قال` / `أن` / `عن النبي` / `عن رسول الله` / `قال رسول الله` / `قال أبو عبد الله` etc. — full anchor list documented in `MATN_ANCHORS` from `algo_candidates/_common.py`) in `text_ar` and asserts no expected_branches surface appears after that position | Hard fail |
| V-6 | `difficulty` is an integer 1-5 | Hard fail |
| V-7 | `annotator` is a non-empty string | Hard fail |
| V-8 | `annotated_at` is a valid ISO-8601 timestamp parseable by `datetime.fromisoformat` | Hard fail |

**FR-3.3** — Output format: `datasets/hadith-data/__tests__/fixtures/validation-<YYYY-MM-DD>.md`. One section per row with PASS / FAIL / WARN per check, plus an aggregate summary at the top (pass rate, fail reasons histogram).

**FR-3.4** — CLI signature:
```
python validate_annotation.py [--input <path>] [--strict] [--out <path>]
```
- `--input` defaults to `tahweel-gold.jsonl`.
- `--strict` turns warnings (V-4 position swaps) into hard fails.
- Exit code 0 if all checks pass at the requested level, 1 otherwise.

**FR-3.5** — **Hard rule: no row enters `tahweel-gold.jsonl` without passing `validate_annotation.py`.** This rule is in the guide (FR-1.2 §2) and enforced by the staging-vs-gold split in FR-2 / FR-3.6.

**FR-3.6** — A `--promote --from <staging.jsonl> --to <gold.jsonl>` mode runs validation, refuses to promote any failing row, appends passing rows to gold (creating a backup `tahweel-gold.jsonl.bak-<ts>` per project memory rule `[[feedback_no_delete_backup]]`), and emits a promotion report.

### FR-4 — Calibration test (Deliverable 4)

**FR-4.1** — Create `docs/annotation/calibration-test.md` and `docs/annotation/calibration-test.jsonl`.

**FR-4.2** — `calibration-test.jsonl` contains the 5 existing fixtures with `expected_branches: null`, `notes: ""` (the gold reasoning is REDACTED). The annotator's job is to produce their own annotation. The gold answers live in a separate `docs/annotation/.calibration-gold.jsonl` (file name dotfile-prefixed; documented in the guide as "do not open before submitting").

**FR-4.3** — `score_calibration.py` script computes per-fixture **Jaccard similarity** between the annotator's `expected_branches` and the gold's `expected_branches`. Specifically:
- For each (annotator_branch_i, gold_branch_i) pair (matched by index), Jaccard = |intersection| / |union| over the surface-form sets after `_norm`.
- Per-row score = mean of per-branch Jaccards.
- Aggregate score = mean across all 5 fixtures.
- Output: a Markdown report at `docs/annotation/calibration-result-<annotator-id>-<date>.md`.

**FR-4.4** — **Admission threshold: aggregate ≥ 0.85.** Annotators below threshold are advised to re-read the guide and re-attempt. Annotators at/above are admitted to contribute real annotations. The threshold is documented in the guide (FR-1.2 §6).

**FR-4.5** — CLI signature:
```
python score_calibration.py --submission <annotator.jsonl> [--gold <path>] [--out <path>]
```
Default gold path is the dotfile.

### FR-5 — IAA tooling (Deliverable 5)

**FR-5.1** — Create `docs/annotation/iaa-tooling.md` and `datasets/hadith-data/__tests__/fixtures/compute_iaa.py`.

**FR-5.2** — `compute_iaa.py` reads ≥2 annotated JSONL files (one per annotator) and computes pairwise IAA over rows present in both files (matched by `hadith_id`). Outputs:
- Per-pair **Krippendorff's alpha** (rationale: TC-2; handles variable-length list-of-lists better than Cohen's kappa).
- Per-row disagreement detail: when annotators differ, what each said (rendered side-by-side).
- Aggregate pass rate at α ≥ 0.80 threshold.
- Output: `docs/annotation/iaa-report-<date>.md`.

**FR-5.3** — Treatment of list-of-lists for Krippendorff: each (hadith_id, branch_index, position) triple is the unit of analysis; the value is the surface form (after `_norm`). Missing units (one annotator's branch is shorter) count as disagreement. Detail in the iaa-tooling.md doc.

**FR-5.4** — CLI signature:
```
python compute_iaa.py --annotators <file1.jsonl> <file2.jsonl> [<file3.jsonl>...] [--out <path>] [--threshold 0.80]
```

### FR-6 — LLM-assisted draft annotation (optional)

**FR-6.1** — The guide (FR-1.2 §9) documents a workflow that uses Claude Sonnet 4.6 to produce a candidate `expected_branches` that a human verifier then accepts or corrects. This is **optional** and clearly marked as such; the guide must not present LLM drafts as authoritative.

**FR-6.2** — Workflow steps in the guide:
1. Pull candidates via `pull_next_candidates.py`.
2. Run an LLM-draft script (out of scope to ship in this track; reference the `tier2_llm/` prompts from the sibling track as the prompt baseline).
3. Human reviewer reads each LLM-drafted row, accepts / corrects / sets `difficulty`.
4. Validate via `validate_annotation.py`.
5. Promote to gold.

**FR-6.3** — Explicit warning in the guide: an unverified LLM draft is NOT a valid gold annotation. The `annotator` field for such rows MUST be the **human reviewer's** identifier, not "claude-sonnet-4.6" — the human is taking responsibility for the row.

**FR-6.4** — Cost note: ~$0.005/row at current Sonnet pricing. The track does NOT ship the LLM-draft script (deferred to a follow-up track if/when adopted), but the prompt baseline lives in `prompts/draft_annotation_v1.md` in the sibling tier-2 track and is reusable.

## 4. Non-Functional Requirements

**NFR-1 — Guide readable by non-engineers.** Target reader: Islamic studies grad student with hadith knowledge but no Python / regex / set-theory background. Forbidden jargon in the guide's prose: "Jaccard", "set intersection", "LCS", "Levenshtein", "regex", "kunya hash" (mention by name if needed but always plain-language adjacent). Required jargon (acceptable): "taḥwīl", "isnad", "sanad", "matn", "Companion", "Imam", "Prophet", "rijāl", "ح" — Islamic studies vocabulary stays. Test: the G-1 readability check is run by a human reader who is asked to score 2 of the 5 calibration cases correctly with no Python knowledge.

**NFR-2 — Worked examples are SHOWN, not described.** Every case-type section shows actual Arabic text + actual JSON + an ASCII chain diagram. No "imagine a hadith that…" prose. Diagrams are ASCII-art trees (Unicode box-drawing acceptable).

**NFR-3 — Versioned with the spec.** The guide, the calibration test, the validator, the IAA tool, and the pull script all live in git, get reviewed via PR, and ship together with this track's commit. No external wiki.

**NFR-4 — Scholarly framing.** The HALAL/scope section (FR-1.2 §8) makes clear that annotators are **descriptive linguistic extractors**, not muḥaddithīn. They are not issuing rijāl verdicts. This is a sensitivity issue given that some prospective annotators are Islamic studies students who may feel uncomfortable claiming authority over isnad analysis.

**NFR-5 — Tradition coverage in the kit.** The guide includes **at least 2 worked examples** from Imami sources (Al-Kāfī `arabicText` or other Thaqalayn v2_books that have taḥwīl) and **at least 1 from Zaydi or Ibadi** if any exist. Phase 0 audits the corpus for ح in non-Sunni sources; if none exist, the guide records that fact explicitly with a citation to the audit. The NFR is best-effort, NOT blocking — coverage of nonexistent cases is impossible.

**NFR-6 — Determinism.** Pull script is seedable; validator is deterministic; calibration scorer is deterministic; IAA computation is deterministic. Re-running any of them on the same input produces the same output bytes (modulo timestamps in human-readable headers).

**NFR-7 — Cross-platform.** Scripts run on macOS / Linux / Windows. The atomic-append concern noted in the sibling tier-2 track applies here too: any file write follows the project's already-established convention (`with open(..., 'w')` + rename, or Windows-safe lockfile).

**NFR-8 — All file writes follow `[[feedback_no_delete_backup]]`.** The `--promote` mode backs up `tahweel-gold.jsonl` before appending. The validator never modifies the input. Archive moves use `archive/` subdirectories, not `rm`.

## 5. Six Enforceable Guardrails

Each is an acceptance criterion with a test that ships in the track's commit.

**G-1 — Guide is readable by a non-engineer.** Recruit one human test reader with hadith knowledge but no programming background. Ask them to read the guide and then score 2 of the 5 calibration cases. Pass: both cases ≥ 0.85 Jaccard against gold. This is a human-loop guardrail, not a unit test — recorded in `verification.md` with the reader's first-name initial + date.

**G-2 — Calibration scorer detects the canonical errors.** Plant a deliberately-wrong annotation (e.g., swap Branch A and Branch B's narrator orders) in a test submission file. Run `score_calibration.py` against it. Assert the aggregate score is < 0.85 AND the per-row report flags the affected row as the lowest-scoring. Tested via `__tests__/test_calibration_planted_errors.py`.

**G-3 — Validator catches the canonical bugs.** Run `validate_annotation.py` against 5 hand-crafted bad annotations:
- (a) matn text included in `expected_branches` (V-5)
- (b) missing convergence narrator (V-4 warn)
- (c) wrong surface form not in `text_ar` (V-2)
- (d) `len(expected_branches) != tahweel_count + 1` without `difficulty=5` bypass (V-3)
- (e) missing `annotator` field (V-7)

Every one is flagged. Tested via `__tests__/test_validator_planted_errors.py`.

**G-4 — IAA tooling works on synthetic disagreement.** Feed `compute_iaa.py` two mock annotation files where ~30% of rows differ in measured ways. Assert α is in a plausible range (around 0.7; the test pins a deterministic seed and asserts the computed α within ±0.05 of the expected analytical value). Tested via `__tests__/test_iaa_synthetic.py`.

**G-5 — Pull script enforces diversity.** Run `pull_next_candidates.py --n 30 --seed 42`. Verify:
- No single source contributes > 50% of the pulled rows (where the source has enough rows).
- Single-ح rows ≈ 70% (±10%), 2-ح ≈ 25% (±10%), 3+-ح ≈ 5% (±5%).
- Zero overlap between the pulled rows and `tahweel-gold.jsonl`'s existing 5 rows.
- At least one non-Sunni-K6 row IF such rows exist in the corpus; otherwise the stderr log explains why none.

Tested via `__tests__/test_pull_stratification.py`.

**G-6 — End-to-end first batch (the dogfood test).** Pull 5 new candidates, hand-annotate them following the guide (Jade or a delegate), validate them with `validate_annotation.py`, promote to gold via `--promote`, re-run `algo_evaluate.py` from the parent track. Assertions:
- The 5 new rows pass the validator (all hard fails resolved).
- The bake-off Jaccard p25 either holds steady (≥ 0.625) or improves.
- The branch-count accuracy stays at 1.000 (no regression).
- A short G-6 report documents the bake-off delta and lives at `verification.md`.

This is the "kit actually works" test. Tested via Phase 6 manual run + numeric assertions in `verification.md`.

## 6. Out of Scope

- **Actually annotating 30+ new fixtures.** That's a separate effort (`tahweel_gold_expansion_*` future tracks) that USES this kit; building the kit is the deliverable, not running it to completion. Phase 6's 5-row dogfood is the proof of life, not the expansion.
- **Recruiting external annotators.** The kit prepares for that possibility (calibration test, IAA tooling) but doesn't execute recruitment.
- **Arabic translation of the guide.** Future i18n. The guide is English-first; Arabic loanwords (taḥwīl, isnad, etc.) are inline.
- **Multi-tradition coverage of every collection.** The kit shows the patterns; per-tradition expansion (Imami Bihar, Wasa'il; Zaydi Amali; etc.) happens per-tradition over time via future tracks.
- **Shipping the LLM-assisted draft script.** Documented as a workflow (FR-6); deferred as a runnable script to a follow-up track if/when the team decides to adopt it. The sibling tier-2 track's prompt baseline is the starting point.
- **Annotation-as-a-service tooling / web UI.** Annotators work in their text editor on JSONL files. A submission UI is future infrastructure.
- **Cross-validation against alternative gold sets** (e.g., a senior scholar's competing annotation). Single-gold per row is the kit's contract; the IAA tooling is the path to richer ground truth.

## 7. Technical Considerations / Decisions Made

**TC-1 — Why a guide AND four tools, not one or the other.** A guide without tools is a wiki post that stales. Tools without a guide produce inconsistent outputs because each annotator interprets "expected_branches" their own way. The combination — readable guide + machine-enforced contract — is the minimum viable kit.

**TC-2 — Krippendorff's α over Cohen's κ for IAA.** Cohen's κ is designed for categorical labels with a fixed value space. Our annotations are **variable-length list-of-lists of strings** — the value space per "unit" is open. Krippendorff's α handles missing units, variable-length sequences, and arbitrary distance metrics natively. Reference: Hayes & Krippendorff (2007), "Answering the Call for a Standard Reliability Measure for Coding Data." The per-unit distance for our data is "0 if surface forms match after `_norm`, 1 otherwise"; the unit is `(hadith_id, branch_index, position)`.

**TC-3 — Why staging-vs-gold split.** Annotation is error-prone (the seven canonical bugs in G-3 are common). If staging silently overwrote gold, one bad batch could corrupt the canonical fixtures. The `--promote` step is the human-supervised gate; the `--validate` pass catches the canonical errors before promotion.

**TC-4 — Why the calibration test exists at all.** Without it, every new annotator's first batch is essentially untested. The calibration test gives a numerical floor ("you scored 0.91 on the 5 known cases, you're admitted") that catches gross misunderstandings of the contract before they enter the gold set.

**TC-5 — Why difficulty=5 has a `len(expected_branches) != tahweel_count + 1` bypass.** The Phase 0 stage-3 research established Ibn al-Salah's two-readings ambiguity: ح could mean تحويل (taḥwīl, a chain switch) OR الحديث (an abbreviation of "the ḥadīth", which is NOT a chain switch). A row where the annotator cannot tell which reading applies is genuinely ambiguous in source — forcing them to pick a branch count is asking them to fabricate ground truth. The bypass lets them flag the row, record reasoning, and leave it as a documented ambiguous case. The validator still requires `notes` to be non-empty in this bypass mode.

**TC-6 — Why the guide forbids "Jaccard" in prose but documents the calibration threshold as 0.85 anyway.** Annotators don't need to understand Jaccard to follow the rule "your score must be ≥0.85." The scorer prints a plain-language gloss ("you matched 91% of the gold's narrators per branch on average — you're admitted!") so the number is interpretable without set theory.

**TC-7 — Pull script seed default = 42.** Reproducibility. The "first 30" batch and any re-derivation of it should produce the same row set. Future batches use higher seeds (43, 44, …) or no seed for randomized growth.

**TC-8 — Why we don't ship the LLM-draft script in this track.** Two reasons: (a) the tier-2 sibling track already authors a sign-off-required prompt for LLM extraction; reusing it via a sibling is cheaper than re-prompting; (b) shipping the LLM script requires API-key infra, cache governance, and a sign-off pass — all of which are appropriate for a dedicated track, not this kit-building track. The kit documents the workflow; future track ships the runtime.

## 8. Dependency Edges

- **Depends on:** Nothing. Parallel-safe with both extraction tracks.
- **Blocks:** Nothing strictly. BUT: the value of expanding the gold set BEFORE the parent track locks the bake-off winner is significant — the p25 robustness estimate tightens with more fixtures. If feasible, this track's Phase 6 (dogfood) could happen interleaved with the parent track's Phase 1 to surface algorithm edge cases earlier.
- **Enables:**
  - `tahweel_gold_expansion_*` follow-up tracks (per-tradition or per-batch growth).
  - Any community-driven annotation push (the calibration test + IAA tooling are the prerequisites for letting external contributors write to the gold set).
  - Tighter G-1/G-2/G-3 acceptance in both parent extraction tracks once the gold set grows.

## 9. Open Questions

**Q1 — Does the corpus contain any Zaydi or Ibadi taḥwīl rows?** The parent track's audit (`audit_tahweel_stats.py`) measured ح-occurrence per source for Sunni K6 and partly for Imami `arabicText`. We don't have a confirmed count for Musnad Zayd / Tartib al-Jami al-Sahih. Phase 0 task: run the audit script against those sources. If zero, NFR-5's "at least 1 from Zaydi or Ibadi" becomes "documented absence" rather than coverage.

**Q2 — Should the calibration threshold be 0.85 or higher for senior scholars?** A senior scholar joining the project may chafe at being asked to pass a calibration test designed for grad students. Document in the guide that the calibration is a one-time pass; a 0.95+ scorer can be presumed-ready without future re-tests. Phase 1 task: document this carve-out explicitly.

**Q3 — Should the guide be in `docs/annotation/` or `conductor/docs/`?** Convention in the repo is `docs/` for user-facing docs and `conductor/tracks/` for track artifacts. The guide is user-facing for annotators (not for engineers consuming the track artifact), so `docs/annotation/` is the right home. Decided: `docs/annotation/`. Documented here for the planner; no follow-up needed.

**Q4 — How does the kit handle annotator versioning when the contract changes?** If a future revision of the guide changes what `expected_branches` means (e.g., starts including the Prophet anchor when FR-4 of the parent track flips on), existing gold rows are now out of date. Decision: the gold JSONL gets a per-row `kit_version` field; the validator checks it and warns on mismatch. Not blocking for v1; Phase 7 closeout adds the field with default `"1.0.0"`.

**Q5 — Should `score_calibration.py` and `compute_iaa.py` share a common normalization library?** Yes — both call `_norm` from `regen_unified_csvs.py`. Phase 2 task validates that the import path is clean and doesn't drag in heavy CSV-builder dependencies.

## 10. Acceptance Gate Summary

| Gate | Criterion | Test |
|---|---|---|
| G-1 | Guide is readable by a non-engineer | Human-in-loop: 1 reader scores 2/5 calibration cases ≥ 0.85 |
| G-2 | Calibration scorer detects canonical errors | `__tests__/test_calibration_planted_errors.py` |
| G-3 | Validator catches the 5 canonical bugs | `__tests__/test_validator_planted_errors.py` |
| G-4 | IAA tooling works on synthetic disagreement | `__tests__/test_iaa_synthetic.py` (α ≈ 0.7 ± 0.05) |
| G-5 | Pull script enforces diversity | `__tests__/test_pull_stratification.py` |
| G-6 | End-to-end first batch (dogfood) | Phase 6 manual + `verification.md` numeric assertions |

Pass all six → ship.
