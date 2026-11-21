# Plan: Tier-2 LLM Second-Opinion Pass for Taḥwīl-Aware Isnad Extraction

**Track:** `tier2_llm_isnad_reconciliation_20260612`
**Spec:** `./spec.md`
**Created:** 2026-06-12
**Estimated wall time:** ~14 hrs of focused work + ~5 min for the live K6 multi-branch pass + ~30 min for the diagnose-script verification
**Research basis:** `.omc/research/uniform-isnad/research-session/report.md` (5-stage scientist mission, 2026-06-12)

---

## Phase 0 — Audit + scaffolding (~2 hrs)

The "see what we're dealing with" pass. Calibrates the suspicion detector thresholds against real Tier-1 output before any production code is written.

- [ ] **T-0.1** — Run the existing Tier-1 extractor (`extract_isnad_branches` from `uniform_isnad_extraction_20260609` Phase 1) over every row in `datasets/hadith-data/__tests__/fixtures/tahweel-gold.jsonl` and record per-fixture: which of the 5 FR-1.2 trigger codes fire, whether Tier-1 output matches gold, and the resolver-rate per branch. Output: `.omc/research/uniform-isnad/tier2-trigger-calibration.md`. (P0, ~30 min)
- [ ] **T-0.2** — Confirm the existing er-staging schema (`src/scripts/ingest-er-approved.ts`, `datasets/hadith-data/er-staging.jsonl`) supports FR-3.4's NameMention fields. If `branch_index` or `prompt_version` is missing, document the additive schema extension. (Spec Q2) (P0, ~30 min)
- [ ] **T-0.3** — Sample 50 K6 multi-branch hadiths from the unified CSV, run Tier-1 against them, count expected Tier-2 trigger rate. Project to 1,768-row corpus and 99k-row corpus; record in the calibration file. Validates the ~5% trigger estimate from the research report. (P1, ~30 min)
- [ ] **T-0.4** — Confirm the exact Claude Sonnet 4.6 model ID via `anthropic` SDK / Anthropic console. Update the spec's Q1 placeholder. (P0, ~10 min)
- [ ] **T-0.5** — Hand-author `datasets/hadith-data/__tests__/fixtures/tahweel-gold-disagreements.jsonl` covering each of the 6 FR-4.2 disagreement types. Each entry: `{type, tier1_branches, tier2_branches, expected_event_code, expected_final_branches}`. ~6 hand-written fixtures. (P0, ~45 min)
- [ ] **T-0.6** — Create the module scaffold under `datasets/hadith-data/tier2_llm/` with empty files: `__init__.py`, `client.py`, `suspicion.py`, `hallucination_guard.py`, `reconcile.py`, `cost_tracker.py`, `prompts/`, `__tests__/`, `__tests__/_mocks.py`, `.cache/.gitkeep`. Add `.cache/*.jsonl` to `.gitignore`. (P0, ~15 min)

**Gate Φ-0:** Calibration markdown is checked in, gold-disagreements fixture exists, module scaffolds present. Suspicion thresholds in spec FR-1.2 either confirmed or revised based on T-0.1 data.

## Phase 1 — Suspicion detector + cost tracker (~2 hrs)

Pure Python, no network. The two stateless modules that everything else depends on.

- [ ] **T-1.1** — Implement `is_suspicious(tier1_branches, tier1_resolved, text_ar)` per FR-1.1 / FR-1.2. Import the ح-counting regex from the parent track's `audit_tahweel_stats.py` rather than redefining. (P0, ~60 lines)
- [ ] **T-1.2** — Implement `cost_tracker.add_cost(input_tokens, output_tokens) → float` and `check_ceiling() → bool` per FR-6.1. Read ceiling from `TIER2_COST_CEILING_USD` env var with $50 default. Pricing constants: `_PRICE_IN_PER_MTOK = 3.0`, `_PRICE_OUT_PER_MTOK = 15.0`. (P0, ~40 lines)
- [ ] **T-1.3** — Write `__tests__/test_tier2_suspicion.py` per FR-7.1: ≥ 10 tests covering all 5 trigger codes + non-triggering controls + edge cases (empty `text_ar`, quoted-ح-in-matn). (P0, ~150 lines)
- [ ] **T-1.4** — Write `__tests__/test_tier2_cost_tracker.py`: cost accumulation, ceiling check transitions, env-var override, per-run reset. ≥ 6 tests. (P0, ~80 lines)

**Gate Φ-1:** All Phase 1 unit tests pass. Suspicion detector runs without network. Cost tracker boundaries are precise.

## Phase 2 — Prompt authoring + LLM client wrapper (~3 hrs)

Network-touching code. Mock-first development; real Anthropic calls only at the end of the phase for one smoke test.

- [ ] **T-2.1** — Author `prompts/extract_branches_v1.md` per FR-2.3. Three few-shot examples (2-branch, 3-branch, no-taḥwīl) drawn from `tahweel-gold.jsonl`. Markdown structure: system context (classical isnad grammar primer), task description (extract branches), tool-use spec (the JSON schema from FR-2.2), 3 examples with input + expected tool call. ~200 lines markdown. (P0)
- [ ] **T-2.2** — **NFR-5 sign-off: Jade reviews + signs the prompt file.** Add the `<!-- signed-off-by: Jade Zaher, 2026-06-XX -->` comment line. Track does NOT proceed past this task without sign-off. (P0 BLOCKING)
- [ ] **T-2.3** — Define the `LLMClient` Protocol in `client.py`: single method `call(text_ar, sanad_hint, hadith_meta) → LLMResponse` where `LLMResponse` is a typed dataclass `{branches: list[list[str]] | None, input_tokens: int, output_tokens: int, raw_response: dict, error: str | None}`. (P0, ~40 lines)
- [ ] **T-2.4** — Implement `MockLLMClient` in `__tests__/_mocks.py` per NFR-2: keyed by `sha256(text_ar + sanad_hint_json)`, returns canned responses from a fixture file `__tests__/fixtures/mock_llm_responses.jsonl`. Implements the `LLMClient` Protocol. (P0, ~80 lines)
- [ ] **T-2.5** — Implement `AnthropicClient` per FR-2.1 / FR-2.2. Uses `anthropic.Anthropic()` SDK; calls `messages.create(model=..., tools=[extract_branches_tool], tool_choice={"type": "tool", "name": "extract_branches"})`. Extracts `tool_use.input.branches`. Returns the `LLMResponse` dataclass with token counts from `response.usage`. (P0, ~120 lines)
- [ ] **T-2.6** — Implement `call_llm_for_branches(text_ar, sanad_hint, hadith_meta)` per FR-2.1: 3-attempt retry per FR-2.4, returns sentinel on exhaustion. Inject the `LLMClient` via constructor or module-level singleton so tests can swap in the mock. (P0, ~80 lines)
- [ ] **T-2.7** — Implement the response cache per NFR-1: JSONL at `.cache/<model_id>__<prompt_version>.jsonl`, keyed by `sha256(text_ar + json.dumps(sanad_hint, sort_keys=True))`. On hit, skip the call AND skip cost tracking. On miss, append after the call. Atomic-append on POSIX, file-lock fallback on Windows (NFR-8). (P0, ~80 lines)
- [ ] **T-2.8** — Write `__tests__/test_tier2_client.py`: mock-driven tests covering successful call, schema-validation retry path, retry-exhaustion sentinel, cache hit, cache miss. ≥ 8 tests, all use `MockLLMClient`. (P0, ~150 lines)
- [ ] **T-2.9** — Single live smoke test against real Anthropic API: one row from `tahweel-gold.jsonl`, with $1 manual cost ceiling. Manually verify the response shape and that cost-tracker accounting is correct. Tagged `@pytest.mark.network` and skipped in CI. (P0, ~30 min wall time)

**Gate Φ-2:** Prompt signed off. Mock-tested client passes all tests. One real Anthropic call verifies the live integration end-to-end. Cache writes + reads correctly across process boundaries.

## Phase 3 — Hallucination guard + reconciler (~2.5 hrs)

Stateless logic, mock-driven testing. No new network paths.

- [ ] **T-3.1** — Implement `guard_branches(llm_branches, exact_index, blocked_index) → (guarded_branches, stats)` per FR-3.1. Reuse the existing `resolve_narrator` from `regen_unified_csvs.py` — import, do not duplicate. Track per-branch resolution rate; apply FR-3.3's 50% threshold. (P0, ~100 lines)
- [ ] **T-3.2** — Implement NameMention emission per FR-3.4: `{type: "tier2_name_mention", hadith_id, dvId, surface_form, branch_index, position, llm_confidence, prompt_version, model_id, ts}`. Writer function appends to a per-row `name_mentions: list[dict]` accumulator that the caller flushes to the er-staging file at end of run. (P0, ~50 lines)
- [ ] **T-3.3** — Implement `reconcile_tier1_tier2(tier1_resolved, tier2_guarded, text_ar, row_meta) → (final_branches, audit_events)` per FR-4.1 / FR-4.2. Each of the 6 disagreement codes is a distinct branch in the function. Use the gold-disagreements fixture as the test bedrock. (P0, ~150 lines)
- [ ] **T-3.4** — Write `__tests__/test_tier2_hallucination_guard.py` per FR-7.2: ≥ 6 tests, including the planted-phantom test for G-2 and the 49%-vs-51% FR-3.3 boundary. (P0, ~120 lines)
- [ ] **T-3.5** — Write `__tests__/test_tier2_reconcile.py` per FR-7.3: ≥ 8 tests, one per disagreement type from `tahweel-gold-disagreements.jsonl` plus the passthrough no-disagreement case. (P0, ~150 lines)

**Gate Φ-3:** All Phase 3 tests pass. Guard correctly tombstones phantoms. Reconciler emits the correct event code for every fixture in the disagreements file. Zero silent overwrites verified.

## Phase 4 — Integration into `regen_unified_csvs.py` (~2 hrs)

Wire the Tier-2 wrapper into the existing CSV builder. This is the "make it run end-to-end" phase.

- [ ] **T-4.1** — Implement `_compute_chain_indx_with_tier2(text_ar, fallback_sanad_list, exact_index, blocked_index, stats, row_meta) → str` per FR-5.1. The 6-step algorithm exactly as specified. (P0, ~120 lines)
- [ ] **T-4.2** — Replace all three call sites in `regen_unified_csvs.py` per FR-5.2: `_enrich()` Sunni branch, `openiti_to_clean_row` / `openiti_to_shia_row`, `load_classical_sunni_rows`. Pass `row_meta = {"hadith_id": ..., "dvId": ..., "source": ...}`. (P0)
- [ ] **T-4.3** — Add the `name_mention_indx` sidecar column to the unified CSV header (FR-5.3, spec Q4 → end of header). Wire the per-row accumulator from T-3.2 to write a `;`-separated list of `NM::<hash>:surface_form` entries into the column. Empty string when no mentions. (P0)
- [ ] **T-4.4** — Implement the `DISABLE_TIER2` env-var passthrough per NFR-4: at module load, if `os.getenv("DISABLE_TIER2") == "1"`, alias `_compute_chain_indx_with_tier2 = _compute_chain_indx` (no suspicion check, no LLM call, no audit log). (P0, ~10 lines)
- [ ] **T-4.5** — Implement `--dry-run-tier2` flag per NFR-3: passed to `regen_unified_csvs.py`, sets a module flag that makes `call_llm_for_branches` return Tier-1 unchanged. (P0)
- [ ] **T-4.6** — Wire the audit log writer: open `logs/tier2-<dvId>.jsonl` at start of pass, append per FR-4.4, close at end. Buffer flush every 100 rows so a killed pass doesn't lose data. (P0, ~40 lines)
- [ ] **T-4.7** — Wire the cost-ceiling incident file writer per FR-6.2: when `check_ceiling()` returns True, write `logs/tier2-cost-ceiling-<dvId>-<ts>.json` once, then switch the rest of the pass to Tier-1 fallback. (P0, ~30 lines)
- [ ] **T-4.8** — Syntax + smoke check: `python -c "import ast; ast.parse(open('regen_unified_csvs.py').read())"` and `python -c "from datasets.hadith_data.tier2_llm import client, suspicion, hallucination_guard, reconcile, cost_tracker"` (or equivalent path). (P0)

**Gate Φ-4:** Syntax clean. `DISABLE_TIER2=1` round-trip produces a bit-identical CSV to the parent track's output (verified informally — full G-4 test in Phase 5). `--dry-run-tier2` produces audit log entries with `action: "tier1_passthrough"` for every row.

## Phase 5 — End-to-end fixture + guardrail tests (~1.5 hrs)

The G-1 through G-7 test suite. All seven guardrails ship as automated tests.

- [ ] **T-5.1** — Write `__tests__/test_tier2_e2e.py` per FR-7.4: runs `_compute_chain_indx_with_tier2` against each gold fixture with `MockLLMClient`, asserts final branches match gold OR fall back to Tier-1 cleanly. Covers G-1. (P0, ~120 lines)
- [ ] **T-5.2** — Write `__tests__/test_tier2_g2_hallucination.py`: plants `"خليفة بن قرفقس"` (a non-existent narrator) in the mock LLM response, asserts the guard tombstones it as `NM::<hash>`, asserts zero phantom scholar_indxs in final `chain_indx`. (P0, ~60 lines)
- [ ] **T-5.3** — Write `__tests__/test_tier2_g3_cost_ceiling.py`: 50-row test CSV, ceiling at $0.05, asserts ~10 rows processed with Tier-2 and the incident file is written with correct counts. (P0, ~80 lines)
- [ ] **T-5.4** — Write `__tests__/test_tier2_g4_disable.py`: runs the CSV builder twice (once with `DISABLE_TIER2=1`, once with the parent track's `_compute_chain_indx` directly), asserts byte-identical output after sorting by `dataset_row_id`. (P0, ~80 lines)
- [ ] **T-5.5** — G-5 is covered by T-3.5 (reconciler tests), but add an integration smoke that runs the gold-disagreements fixtures through the full `_compute_chain_indx_with_tier2` and asserts every event code appears in `logs/tier2-<test-dvId>.jsonl`. (P0, ~60 lines)
- [ ] **T-5.6** — Write `__tests__/test_tier2_g7_idempotency.py`: runs the pass twice in succession with the cache directory persisted, asserts run 2's cost counter is 0.0 and the audit log entries are byte-identical (after timestamp normalization). (P0, ~80 lines)
- [ ] **T-5.7** — `pytest datasets/hadith-data/tier2_llm/__tests__/ -v` runs clean. All G-1 through G-5, G-7 tests pass. G-6 deferred to Phase 6 (needs live data). (P0)

**Gate Φ-5:** 6 of 7 guardrails pass in CI. G-6 (coverage uplift) is the only one requiring a live run.

## Phase 6 — Dry-run validation pass over K6 multi-branch (~1 hr)

Sanity check before committing real LLM spend. Dry-run pulls the rows, exercises every code path, but doesn't call the LLM.

- [ ] **T-6.1** — Backup `all_hadiths_unified.csv` to `.bak-tier2-<ts>` (the `[[feedback_no_delete_backup]]` rule). (P0)
- [ ] **T-6.2** — Filter the unified CSV down to the 1,768 K6 multi-branch hadiths (`text_ar` contains ح + source ∈ {Bukhari, Muslim, Tirmidhi, Abu Dawud, Ibn Majah, Nasai}). Write to `all_hadiths_k6_multibranch.csv` for the focused run. (P0)
- [ ] **T-6.3** — Run `python regen_unified_csvs.py --dry-run-tier2 --input all_hadiths_k6_multibranch.csv --output /tmp/k6_dryrun.csv`. Inspect: how many rows triggered the suspicion detector, what reason codes fired, was the projected real-pass cost within the $50 ceiling? (P0, ~10 min)
- [ ] **T-6.4** — If T-6.3 projects > $30 spend OR > 30% trigger rate, STOP and revisit suspicion thresholds (FR-1.4 is monotonic — only loosen if cost projection is way under, tighten if way over). (P0 — abort criterion)
- [ ] **T-6.5** — Verify the audit log structure on the dry-run output. Random-sample 10 rows, eyeball the `events[]` list, confirm reasonable. (P1)

**Gate Φ-6:** Projected cost ≤ $30. Trigger rate within [2%, 20%] window. Audit log structure verified. Ready for live run.

## Phase 7 — Live Tier-2 pass over K6 multi-branch (~1 hr active + 5 min wall time)

The real LLM spend. Monitored.

- [ ] **T-7.1** — Confirm `ANTHROPIC_API_KEY` is set, model ID pinned, prompt signed off (NFR-5). Verify cache directory is clean (for a clean cost-attribution baseline) or warm (if previous dry-run hit the same cache key — note this and skip if expected). (P0)
- [ ] **T-7.2** — Run live: `TIER2_COST_CEILING_USD=50 python regen_unified_csvs.py --input all_hadiths_k6_multibranch.csv --output all_hadiths_k6_multibranch_tier2.csv`. Stream stdout to a log file. ETA ~5 min wall time. Monitor in a second terminal: `tail -f logs/tier2-<dvId>.jsonl | jq '.cost_usd' | awk '{s+=$1} END {print s}'`. (P0)
- [ ] **T-7.3** — On completion: total cost should be ≤ $25 (per the spec's realistic estimate). If higher, document why in `logs/tier2-cost-analysis-<dvId>.md`. (P0)
- [ ] **T-7.4** — Inspect 20 random Tier-2-processed rows from the audit log. For each, look at `tier1_branches` vs `final_branches` and confirm the reconciliation looks sensible to a human eye. Flag any obvious hallucinations or weird overwrites. (P0, ~30 min)
- [ ] **T-7.5** — Stream the NameMention entries into `er-staging.jsonl` per FR-3.4. Verify the existing `ingest-er-approved.ts` flow can consume them (run it in `--dry-run` mode if available). (P0)

**Gate Φ-7:** Live pass completes within cost ceiling. Audit log is sane. NameMention sidecar feeds er-staging cleanly. Ready for coverage measurement.

## Phase 8 — Coverage measurement + G-6 acceptance (~1 hr)

The "did it actually help?" check. This is G-6.

- [ ] **T-8.1** — Run `tsx src/scripts/diagnose-chain-data.ts` against the new `all_hadiths_k6_multibranch_tier2.csv` AND against the parent-track baseline (Tier-1-only) `all_hadiths_k6_multibranch.csv`. Capture both reports. (P0)
- [ ] **T-8.2** — Compute the delta: per-source `avg narrators per chain`, `avg chains per hadith`, `with_chain` rate. Assert the K6 multi-branch avg narrators per chain moves into [4.8, 6.8] from the [4.5, 6.5] baseline. Write `verification.md` with the comparison table. (P0)
- [ ] **T-8.3** — Re-evaluate the 5 gold fixtures + the new disagreement fixtures against the Tier-2 output via `algo_evaluate.py` from the parent track. Assert Jaccard p25 moves from 0.625 toward 0.75. (P0)
- [ ] **T-8.4** — If T-8.2 or T-8.3 fails: file a follow-up to tune the suspicion detector / prompt, do NOT lower the bar. Document the failure mode in `.omc/research/uniform-isnad/tier2-coverage-analysis.md`. (P0 if failure)
- [ ] **T-8.5** — G-6 PASS criterion documented. Architect verification subagent (`oh-my-claudecode:architect`) reviews the verification.md against the spec. (P0)

**Gate Φ-8:** G-6 passes. All seven guardrails are now green. Track ready to close.

## Phase 9 — Closeout (~30 min)

- [ ] **T-9.1** — Update `conductor/tracks.md` with `[x]` and a post-results summary (cost, coverage delta, residual count escalated to HITL).
- [ ] **T-9.2** — Update `verification.md` with concrete evidence for each of G-1 through G-7 (test names, diagnose-script numbers, sample audit log entries).
- [ ] **T-9.3** — File follow-up tracks:
  - `tahweel_gold_expansion_<date>` — grow the gold set beyond 5 fixtures.
  - `tier2_multi_vendor_<date>` — GPT-4 / Gemini as Tier-2 alternatives (if cost/accuracy shifts).
  - `tier2_full_corpus_<date>` — apply Tier-2 across all 99k rows after the K6 multi-branch run validates the floor uplift.
- [ ] **T-9.4** — Unblock `uniform_isnad_extraction_20260609` Phase 6b re-run on K6 multi-branch by updating that track's blocking note in `conductor/tracks.md`.
- [ ] **T-9.5** — Update `MEMORY.md` index if any new project-level facts surfaced (e.g., final model ID, observed trigger rate, observed cost, NameMention schema changes).

---

## Out-of-band risks + mitigations

**Risk-A — Anthropic API rate limits during the live pass.** ~88 calls in 5 min ≈ 17 calls/min, well under the 1000/min default tier. Mitigation: if rate-limited, the SDK retries with backoff automatically; pass continues. Document in the audit log.

**Risk-B — Prompt drift.** If a future Anthropic model upgrade subtly changes outputs, the cache key (which includes `model_id`) invalidates and the pass re-runs everything. Mitigation: cache-key versioning is already in NFR-1. Document the upgrade in `verification.md` if it happens.

**Risk-C — Cost ceiling hit mid-K6-multi-branch.** Means projected $25 spend was off by 2x. Mitigation: `cost_ceiling_hit` incident file documents the boundary; the pass cleanly falls back to Tier-1 for the remaining rows. Track can still close with partial coverage gain documented. Re-running after ceiling raise is one env-var change away.

**Risk-D — Gold-disagreements fixture is wrong.** Hand-authored fixtures are subject to author bias. Mitigation: Jade (NFR-5 sign-off) reviews the disagreements file in Phase 0 before reconciler implementation in Phase 3. If post-Phase-3 testing reveals a fixture is wrong, fix the fixture, do NOT lower the assertion.

**Risk-E — NameMention sidecar column breaks an unknown CSV consumer.** Mitigation: T-0.2 audits er-staging schema compatibility; the column is appended at the END of the header (Q4 in spec); existing readers ignore unknown columns by index-based reads. If something breaks, the parent track's `parseIndices` is the only blast-radius concern and it does not touch the new column.

**Risk-F — Live Anthropic responses are different shape than mock fixtures assumed.** Mitigation: T-2.9 (one real call in Phase 2) catches this before Phase 3 reconciler depends on the shape.

## Total estimated wall time

| Phase | Active hrs | Unattended hrs |
|---|---|---|
| 0 — Audit + scaffolding | 2 | — |
| 1 — Suspicion + cost tracker | 2 | — |
| 2 — Prompt + LLM client | 3 | — |
| 3 — Guard + reconciler | 2.5 | — |
| 4 — Pipeline integration | 2 | — |
| 5 — Guardrail tests | 1.5 | — |
| 6 — Dry-run validation | 1 | — |
| 7 — Live K6 pass | 1 | ~0.1 (5 min) |
| 8 — Coverage measurement | 1 | — |
| 9 — Closeout | 0.5 | — |
| **Total** | **16.5 hr** | **~5 min** |

Net ~2 focused days. The bulk of the cost is human review of the prompt (NFR-5 Jade sign-off) and the disagreement fixtures (T-0.5) — not code. Live LLM spend is bounded at $50, expected $15–25, and runs in 5 minutes against the K6 multi-branch subset.

The downstream win: K6 multi-branch coverage moves from the Tier-1 floor (p25 Jaccard 0.625, avg narrators per chain 4.5–6.5) toward the hybrid ceiling (p25 0.75, avg 4.8–6.8). The residual ambiguous cases — ~5–15% per the research's structural-impossibility finding — flow cleanly into the existing er-staging HITL queue rather than being silently mis-extracted.
