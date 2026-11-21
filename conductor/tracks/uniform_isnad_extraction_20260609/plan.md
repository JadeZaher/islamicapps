---
type: plan
---

# Plan: Uniform Taḥwīl-Aware Isnad Extraction

**Track:** `uniform_isnad_extraction_20260609`
**Spec:** `./spec.md`
**Created:** 2026-06-09
**Estimated wall time:** local implementation and verification only; production cutover is a separately approved operation after every local gate passes.

---

## Phase 0 — Audit + scaffolding (~1 hr)

The "see what we're dealing with" pass. Do this BEFORE writing any extractor code so the algorithm can be calibrated to actual corpus statistics, not assumptions.

- [x] **T-0.1** — Audit ح-occurrence statistics across `all_hadiths_unified.csv`. Count: rows with 0 ح, 1 ح (2 branches), 2 ح (3 branches), 3+ ح (4+ branches). Per source. Output: a small markdown table at `.omc/research/uniform-isnad/tahweel-stats.md`. (P0)
- [x] **T-0.2** — Audit `text_ar` patterns the extractor must handle: how often is ح inside a quoted matn (false positive risk)? Sample 100 rows manually if needed. (P0)
- [x] **T-0.3** — Audit convergence-narrator behavior: in the 1-ح subset, what fraction has exactly one shared narrator across the two branches? (Calibrates FR-1.1 step 3 heuristic.) (P1)
- [x] **T-0.4** — Confirm `arabicText` field on Thaqalayn v2_books is diacritized vs the `_norm` expectations. Sample 5 rows, run them through `_norm`, check that resolution succeeds. (P0 for FR-3.2)
- [x] **T-0.5** — Create the working directory + module scaffolds. Empty `datasets/hadith-data/extract_isnad_unified.py` with type stubs only, no implementation. (P0)

**Gate Φ-0:** stats are in `.omc/research/uniform-isnad/`, decisions about edge cases (T-0.2 false positives, T-0.3 ambiguous convergence) are recorded with chosen handling. Without these we'll build the wrong extractor.

## Phase 0.5 — Empirical algorithm bake-off (~4 hrs)

Phase 0's T-0.3 audit produced only 30% convergence-narrator overlap on a simple set-intersection algorithm — far below the > 95% the original spec assumed. We can't trust theoretical reasoning here; we need to evaluate candidates against a labeled set BEFORE writing production extractor code. Spec FR-0.5 codifies this; this phase executes it.

- [x] **T-0.5.1** — Build labeled gold set at `datasets/hadith-data/__tests__/fixtures/tahweel-gold.jsonl`. The current set has 32 manually read, locally identified records across Sunni, Imami, Ibadi, and Zaydi inputs; two long K6 rows declare exact chain-bearing excerpt scope. (P0)
- [x] **T-0.5.2** — Preserve the five historical candidates under `datasets/hadith-data/algo_candidates/` as comparison baselines and promote the suffix-alignment approach with documented fixes. (P0)
- [x] **T-0.5.3** — `datasets/hadith-data/algo_evaluate.py` now refuses fewer than 30 fixtures and reports branch-count accuracy, best-aligned branch Jaccard (median/p25/p75/mean), edit distance, and tradition breakdown to `.omc/research/uniform-isnad/algo-evaluation.md`. (P0)
- [ ] **T-0.5.4** — Run the harness. Inspect results. (P0, ~15 min)
- [ ] **T-0.5.5** — Pick the winner per FR-0.5.4. If no candidate clears the bar, spec a hybrid in `algo-evaluation.md` and re-run the harness on the hybrid. (P0, ~30 min worst case)
- [x] **T-0.5.6** — Amend `spec.md` FR-1.1 to point to the candidate-C-derived canonical implementation and its stricter 32-record release gate. (P0)

**Gate Φ-0.5:** algo-evaluation.md is checked in, the winning candidate beats the FR-0.5.4 thresholds, FR-1.1 is updated to name the winner. Phase 1 then implements ONLY the winning approach (no first-principles re-derivation).

**2026-07-20 status:** fixture/evaluator implementation is complete, but the
new 32-record evaluator has not yet been run. T-0.5.4/T-0.5.5 and Gate Φ-0.5
remain open until independent verification records the new metrics.

## Phase 1 — Extractor implementation (~6 hrs)

Pure Python. No DB writes, no CSV rebuild yet. Algorithm only.

- [x] **T-1.1** — Implement `extract_isnad_branches(text_ar) → list[list[str]]` as the canonical source-surface extractor. Parsing removes vocalization/tatweel but preserves lexical surfaces and relational pronouns. (P0)
- [x] **T-1.2** — Implement conservative lone-ح detection with a bounded post-marker transmission-verb check, including diacritized input. (P0)
- [x] **T-1.3** — Implement longest suffix-to-slice convergence alignment with loose lexical matching. A single weak pronoun/collective surface cannot establish convergence. (P0)
- [x] **T-1.4** — Keep each earlier branch's own convergence spelling and append only the unmatched last-branch tail; no-match branches remain independent and are counted. (P0)
- [x] **T-1.5** — Implement callback-based `resolve_branches_to_indxs` and deterministic `_UNIFIED_CHAIN_STATS` attempted/resolved telemetry. (P0)
- [x] **T-1.6** — Implement strict `_compute_chain_indx(text_ar, fallback=None, resolve_narrator=None) → str` with comma/pipe formatting and build_csv-compatible keyword arguments. (P0)
- [x] **T-1.7** — Replace the external-pytest test with a standard-library `unittest` suite covering the 32-record gold contract, quality floors, telemetry, resolver, and formatting behavior. (P0)
- [ ] **T-1.8** — Smoke test on Tirmidhi #1 via direct invocation. Confirm output matches G-1 through G-3 expectations BEFORE moving to integration. (P0 — quality gate)

**Gate Φ-1:** all unit tests pass, smoke test on Tirmidhi #1 produces 2 branches with correct convergence + shared post-convergence segment.

## Phase 2 — Integration into `regen_unified_csvs.py` (~3 hrs)

Wire the new extractor into the CSV builder, replacing the three divergent code paths.

- [x] **T-2.1** — K6 chain IDs are rebuilt from Arabic through `_compute_chain_indx`; the Sunni sidecar remains display `sanad`/`matn_ar` only. (P0)
- [x] **T-2.2** — Both OpenITI projections call the canonical Arabic resolver and use canonical `parsed id|hadith number|page ref` identity. (P0)
- [x] **T-2.3** — Classical rows use canonical branch extraction and atomic `_compute_chain_indx` resolution; legacy flat partial resolution is no longer published. (P0)
- [x] **T-2.4** — Thaqalayn `build_csv.py` reads `arabicText` and uses the unified extractor with staged fail-closed output. (P0)
- [x] **T-2.5** — The obsolete Thaqalayn extractor is preserved under `shia-hadith/archive/`. (P1)
- [x] **T-2.6** — All paths share canonical row/extractor telemetry; per-tradition chain coverage is emitted in the candidate manifest. (P1)
- [x] **T-2.7** — Static AST parsing is clean for the extractor, evaluator,
  regeneration/build paths, and both unittest modules. Dynamic smoke tests
  remain deferred to the single final verification sweep. (P0)

**Gate Φ-2:** Python typechecks, syntax-clean, unified stats print in expected format. Architect review pass (oh-my-claudecode:architect) before moving to Phase 3.

## Phase 3 — CSV format extension + TS loader update (~2 hrs)

Make the multi-branch `|`-delimiter flow through the TS reader.

- [ ] **T-3.1** — Update `parseIndices` in `src/scripts/lib/regen/io.ts` per FR-2.2. Change return type from `number[]` to `number[][]`. (P0)
- [ ] **T-3.2** — Update `UnifiedRow.chain_indx` type. (P0)
- [ ] **T-3.3** — Update `buildTier1Resolution` in `src/scripts/lib/regen/load-chain.ts` to iterate branches and emit one `NarratorResolutionResult` per branch with `chain_index = 0, 1, 2, …`. (P0)
- [ ] **T-3.4** — Update TS unit tests for `parseIndices` and `buildTier1Resolution`. (P0)
- [ ] **T-3.5** — `npx tsc --noEmit` clean over `src/scripts/lib/regen/`. (P0)

**Gate Φ-3:** TS compiles, tests green, single-branch CSV cells still parse to one-element outer list (backwards compat).

## Phase 4 — Resolver enrichment (FR-5, optional but recommended) (~3 hrs)

Close the kunya gap so Tirmidhi #1's `أبو عوانة` actually resolves to 20469.

- [ ] **T-4.1** — Audit kunya gap impact. Run resolver against every name in `sunni_isnad.jsonl`, count how many fail per source. (P1)
- [ ] **T-4.2** — Extend `build_narrator_index` to parse the rawi `name` field into segments and index each kunya / English / Arabic surface as an alias to the same scholar_indx — but ONLY when unique within the lexicon. (P0 for FR-5 scope)
- [ ] **T-4.3** — Skip the ambiguous-kunya disambiguator (use death_date_hijri proximity etc.) — file as follow-up track. Just the unique-kunya alias indexing for now. (P1)
- [ ] **T-4.4** — Add 5+ test cases to the Python tests: `أبو عوانة`, `أبو هريرة`, `ابن عمر`, `ابن عباس`, and one ambiguous kunya that should NOT resolve. (P0)

**Gate Φ-4:** Resolver hit rate on Tirmidhi #1's sanad goes from 2/3 to 3/3. Don't go beyond this scope; if the unique-only approach proves too narrow, the disambiguator becomes its own track.

## Phase 5 — UI multi-chain rendering (~2 hrs)

So users see the N branches, not a mush.

- [ ] **T-5.1** — Add `getFullChainGraphGrouped(hadithId)` in `src/app/actions/graph-actions.ts` returning `{ chains: Array<{ id, narrators: NarratorNode[] }>, edges: Edge[] }` keyed by `:Chain.id`. (P0)
- [ ] **T-5.2** — Update `src/app/hadith/[id]/components/IsnadChain.tsx` to render one chain row per `:Chain` node, with a separator "تَحويل (taḥwīl)" between them. (P0)
- [ ] **T-5.3** — Update `src/app/hadith/[id]/components/IsnadGraph.tsx` (the visual graph) to color/group nodes by `:Chain` membership. Shared narrators (e.g., Smāk in Tirmidhi #1) get a special "convergence" badge. (P1)
- [ ] **T-5.4** — Manual visual test on Tirmidhi #1 post-rebuild: confirm 2 distinct chains rendered, both ending at Ibn ʿUmar, convergence at Smāk visually marked. (P0)

**Gate Φ-5:** Visual confirmation on the live deployment that taḥwīl-aware chains render correctly for at least 5 hand-picked examples spanning Bukhari, Muslim, Tirmidhi, Al-Kāfī, Musnad Zayd.

## Phase 6 — Local dry run and separately approved cutover

This track is local-first and cost-safe. It does not authorize a long-running
Railway regeneration or repair. Remote mutation remains out of scope until the
local dataset, evaluator, loader, and UI gates all pass and the user separately
approves a production cutover plan for the correct Railway project.

### Phase 6a — Local evidence

- [ ] **T-6a.1** — Run the Python unittest suites and `algo_evaluate.py` once after all edits. Preserve the measured report. (P0)
- [ ] **T-6a.2** — Run a fully local staged CSV regeneration; require a bound ready manifest, zero partial chain IDs, and inspect `chain.by_tradition` coverage. (P0)
- [ ] **T-6a.3** — Load only into a disposable local Neo4j instance or execute a local no-write diff. Record counts, memory peak, elapsed time, and Tirmidhi #1 branch evidence. (P0)
- [ ] **T-6a.4** — Verify loader multi-branch tests, UI rendering, preservation of a synthetic human edge, and zero hadiths losing all prior chains. (P0)

**Gate Φ-6a:** local regeneration and dry-run evidence pass every prior gate.
The evaluator report must meet all overall and per-tradition thresholds. A
generator/manifest success alone is not uniform-isnad readiness.

### Phase 6b — Production cutover approval boundary

- [ ] **T-6b.1** — Confirm the intended Railway project/environment and current backup/restore procedure with the user. (P0)
- [ ] **T-6b.2** — Present local evidence, estimated remote time/cost, abort criteria, and rollback steps; obtain explicit approval for the bounded mutation. (P0)
- [ ] **T-6b.3** — Execute only the separately approved cutover, then run read-only post-cutover diagnostics and preserve the evidence. (P0)

**Gate Φ-6:** production data is unchanged until T-6b.1 and T-6b.2 are
explicitly satisfied. No unattended remote command is prescribed by this plan.

## Phase 7 — Closeout (~30 min)

- [ ] **T-7.1** — Update `conductor/tracks.md` with `[x]` and post-results summary.
- [ ] **T-7.2** — Write `verification.md` with concrete evidence per guardrail (Cypher results, screenshots).
- [ ] **T-7.3** — File follow-up tracks for the deferred ambiguous-kunya disambiguator and the chain-aware `:NARRATED_FROM` dedup.
- [ ] **T-7.4** — Update `MEMORY.md` index if any new project-level facts surfaced.

---

## Out-of-band risks + mitigations

**Risk-A — Convergence detection wrong on edge case.** The 3-branch Tirmidhi #3 could have non-trivial overlap. Mitigation: T-0.3 audit calibrates the heuristic before T-1.3 implementation. Worst case, the extractor falls back to "no stitch" and emits 3 truncated branches — same as today's bug but no worse.

**Risk-B — Regen wall-time grows.** Adding taḥwīl-handling means each row now parses Arabic text instead of joining a pre-resolved id list. Could double CSV-build time. Mitigation: T-1.7 includes a timing harness; if per-hadith parse exceeds 50ms (NFR-4) we cache the regex compilations and consider Cython.

**Risk-C — Multi-chain CSV breaks something in the ingest pipeline.** The `|` delimiter is new. Mitigation: T-3.4 unit tests + grep for any other consumer of `chain_indx` in the codebase before T-2.1.

**Risk-D — UI work isn't done before the user sees the multi-chain DB.** If we ship Phase 6 before Phase 5, the existing UI will render a single merged-and-deduped chain that looks correct-ish but doesn't show the taḥwīl structure. Mitigation: Phase 5 MUST land before Phase 6, or we ship a "coming soon" tradition badge until Phase 5 ships.

## Time and cost boundary

Local verification time is measured during Phase 6a rather than estimated from
old remote latency. Production duration and cost are intentionally unspecified
until the local evidence exists and the user approves a cutover for the correct
project. This plan never treats a multi-day remote job as an automatic next
step.
