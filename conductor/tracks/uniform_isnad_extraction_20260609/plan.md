# Plan: Uniform Taḥwīl-Aware Isnad Extraction

**Track:** `uniform_isnad_extraction_20260609`
**Spec:** `./spec.md`
**Created:** 2026-06-09
**Estimated wall time:** ~1.5 days of focused work + ~18 hours of unattended fullregen against Railway Neo4j

---

## Phase 0 — Audit + scaffolding (~1 hr)

The "see what we're dealing with" pass. Do this BEFORE writing any extractor code so the algorithm can be calibrated to actual corpus statistics, not assumptions.

- [ ] **T-0.1** — Audit ح-occurrence statistics across `all_hadiths_unified.csv`. Count: rows with 0 ح, 1 ح (2 branches), 2 ح (3 branches), 3+ ح (4+ branches). Per source. Output: a small markdown table at `.omc/research/uniform-isnad/tahweel-stats.md`. (P0)
- [ ] **T-0.2** — Audit `text_ar` patterns the extractor must handle: how often is ح inside a quoted matn (false positive risk)? Sample 100 rows manually if needed. (P0)
- [ ] **T-0.3** — Audit convergence-narrator behavior: in the 1-ح subset, what fraction has exactly one shared narrator across the two branches? (Calibrates FR-1.1 step 3 heuristic.) (P1)
- [ ] **T-0.4** — Confirm `arabicText` field on Thaqalayn v2_books is diacritized vs the `_norm` expectations. Sample 5 rows, run them through `_norm`, check that resolution succeeds. (P0 for FR-3.2)
- [ ] **T-0.5** — Create the working directory + module scaffolds. Empty `datasets/hadith-data/extract_isnad_unified.py` with type stubs only, no implementation. (P0)

**Gate Φ-0:** stats are in `.omc/research/uniform-isnad/`, decisions about edge cases (T-0.2 false positives, T-0.3 ambiguous convergence) are recorded with chosen handling. Without these we'll build the wrong extractor.

## Phase 0.5 — Empirical algorithm bake-off (~4 hrs)

Phase 0's T-0.3 audit produced only 30% convergence-narrator overlap on a simple set-intersection algorithm — far below the > 95% the original spec assumed. We can't trust theoretical reasoning here; we need to evaluate candidates against a labeled set BEFORE writing production extractor code. Spec FR-0.5 codifies this; this phase executes it.

- [ ] **T-0.5.1** — Build labeled gold set at `datasets/hadith-data/__tests__/fixtures/tahweel-gold.jsonl`. ≥30 hand-annotated taḥwīl hadiths from the K6 corpus, covering: 2-branch (most common), 3-branch, 4+-branch pathological case, at least one row with truly independent (no-shared-narrator) branches, span Bukhari/Muslim/Tirmidhi/Abu Dawud/Ibn Majah/Nasai. Annotation is manual — read each text_ar, write expected_branches. (P0, ~2 hrs)
- [ ] **T-0.5.2** — Implement candidates A/B/C/D/E in `datasets/hadith-data/algo_candidates/`. Each is a single .py file exporting `extract_branches(text_ar) → list[list[str]]`. Skeletons can share helpers via a tiny `_common.py`. (P0, ~1 hr)
- [ ] **T-0.5.3** — Build `datasets/hadith-data/algo_evaluate.py` per FR-0.5.3: for each (candidate, fixture), compute branch-count accuracy, per-branch Jaccard (median + p25/p75), edit distance, resolver-rate proxy. Write the Markdown report to `.omc/research/uniform-isnad/algo-evaluation.md`. (P0, ~45 min)
- [ ] **T-0.5.4** — Run the harness. Inspect results. (P0, ~15 min)
- [ ] **T-0.5.5** — Pick the winner per FR-0.5.4. If no candidate clears the bar, spec a hybrid in `algo-evaluation.md` and re-run the harness on the hybrid. (P0, ~30 min worst case)
- [ ] **T-0.5.6** — Amend `spec.md` FR-1.1 to point to the winning candidate. (P0)

**Gate Φ-0.5:** algo-evaluation.md is checked in, the winning candidate beats the FR-0.5.4 thresholds, FR-1.1 is updated to name the winner. Phase 1 then implements ONLY the winning approach (no first-principles re-derivation).

## Phase 1 — Extractor implementation (~6 hrs)

Pure Python. No DB writes, no CSV rebuild yet. Algorithm only.

- [ ] **T-1.1** — Implement `extract_isnad_branches(text_ar) → list[list[str]]` per FR-1.1. Reuse `_CHAIN_VERB_SPLIT`, `_AAN_SPLIT`, `_CLASSICAL_HONORIFIC`, `_CLASSICAL_PUNCT` from `regen_unified_csvs.py` (import, do not duplicate). (P0, ~150 lines)
- [ ] **T-1.2** — Implement the ح-splitter precisely. Match: `(?:^|[،\s])ح\s+و?(?:حدثنا|حدثني|أخبرنا|أنبأنا|ثنا|نا)`. Do NOT match lone ح inside quoted matn. (P0)
- [ ] **T-1.3** — Implement convergence detection. Two-branch case: find `set(branch_1) & set(branch_2)`. Three-branch: pairwise convergence detection, then stitch shared trailing suffix. Use `_norm`-keyed matching for robustness. (P0)
- [ ] **T-1.4** — Implement post-convergence segment stitching. From the LAST branch (post-matn), find the convergence narrator, take everything AFTER it, append to every preceding branch's pre-convergence prefix. (P0)
- [ ] **T-1.5** — Implement `resolve_branches_to_indxs` per FR-1.2. Reuse existing `resolve_narrator`. Track per-branch attempted/resolved in module stats dict `_UNIFIED_CHAIN_STATS`. (P0, ~30 lines)
- [ ] **T-1.6** — Implement `_compute_chain_indx(text_ar, fallback, …) → str` per FR-3.1. This is the single function that replaces all three divergent paths. Returns CSV cell string with `|`-separated branches. (P0, ~40 lines)
- [ ] **T-1.7** — Write Python `pytest` test file at `datasets/hadith-data/__tests__/test_extract_isnad_unified.py` covering FR-1.3 cases (a)–(g). All 12+ tests must pass. (P0)
- [ ] **T-1.8** — Smoke test on Tirmidhi #1 via direct invocation. Confirm output matches G-1 through G-3 expectations BEFORE moving to integration. (P0 — quality gate)

**Gate Φ-1:** all unit tests pass, smoke test on Tirmidhi #1 produces 2 branches with correct convergence + shared post-convergence segment.

## Phase 2 — Integration into `regen_unified_csvs.py` (~3 hrs)

Wire the new extractor into the CSV builder, replacing the three divergent code paths.

- [ ] **T-2.1** — Replace W1's Fix A `_enrich()` Sunni branch chain_indx rebuild with `_compute_chain_indx`. Keep the `sanad` display-string assignment from sidecar unchanged. (P0)
- [ ] **T-2.2** — Replace W3's Fix C `_openiti_chain_indx` calls in `openiti_to_clean_row` / `openiti_to_shia_row` with `_compute_chain_indx`. Delete `_openiti_chain_indx` once unreferenced. (P0)
- [ ] **T-2.3** — Replace the inline `extract_classical_isnad` + flat `','.join(resolved_indxs)` in `load_classical_sunni_rows` with `_compute_chain_indx`. (P0)
- [ ] **T-2.4** — Update FR-3.2: modify `datasets/hadith-data/shia-hadith/build_csv.py` to read `arabicText` from v2_books JSON and use the unified extractor. (P0)
- [ ] **T-2.5** — Archive (do not delete — see `[[feedback_no_delete_backup]]`) the obsolete `datasets/hadith-data/shia-hadith/extract_thaqalayn_sanad.py` to `archive/` subdir. (P1)
- [ ] **T-2.6** — Remove module-level `_K6_CHAIN_INDX_STATS` and `_OPENITI_CHAIN_INDX_STATS`, replace with single `_UNIFIED_CHAIN_STATS`. Update the summary print at end of `main()`. (P1)
- [ ] **T-2.7** — Syntax + smoke check: `python -c "import ast; ast.parse(open('regen_unified_csvs.py').read())"`. (P0)

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

## Phase 6 — Differential repair against live Neo4j (~3–5 days unattended + verify)

NOT a fullregen. See spec §1.1 and FR-6 — this phase implements the new `--mode=repair` and runs it against the live DB. The fullregen path is explicitly forbidden in this track.

### Phase 6a — Build `mode-repair.ts` (~6 hrs active)

- [ ] **T-6a.1** — Create `src/scripts/lib/regen/mode-repair.ts` per FR-6.1. Mirrors `mode-fullregen.ts` structure but replaces the streaming flush-buffer loop with the per-hadith diff + surgical repair pass. (P0, ~400 lines)
- [ ] **T-6a.2** — Implement the diff function: `computeChainDiff(liveState, newBranches) → DiffActions`. Pure function, no DB writes. (P0)
- [ ] **T-6a.3** — Implement surgical-repair Cypher queries — each scoped via `MATCH (h:Hadith {dataset_row_id: $id})-[:HAS_CHAIN]->(:Chain) …`. Forbidden-pattern guard: a `grep` script in `__tests__/` that asserts mode-repair.ts contains zero global `MATCH ()-[r:INCLUDES]->()` patterns. CI-style. (P0)
- [ ] **T-6a.4** — Implement soft-tombstone for `:Chain` removal per FR-6.1 step 5. `chain.active = false`, `chain.tombstoned_at`, `chain.tombstoned_by = $dvId`. (P0)
- [ ] **T-6a.5** — Implement `--dry-run` per FR-6.5. Per-row JSON to `logs/regen-repair-<dvId>-dryrun.jsonl`, zero Neo4j writes. (P0)
- [ ] **T-6a.6** — Implement `--resume-from-row` and checkpoint emission per FR-6.4. (P0)
- [ ] **T-6a.7** — Implement pre-snapshot backup per FR-6.3. Streamed JSONL writer; do not buffer all 99k rows in RAM. (P0)
- [ ] **T-6a.8** — Register the new mode in `src/scripts/regen-isnad-graph.ts` CLI dispatcher. (P0)
- [ ] **T-6a.9** — Unit tests for the diff function — 8+ cases covering identical, narrator_added, narrator_removed, position_changed, chain_added, chain_removed, mixed, empty-on-both-sides. (P0)
- [ ] **T-6a.10** — Inject-human-edge fixture test per G-7. (P0)

**Gate Φ-6a:** all tests green, dry-run on Tirmidhi #1 against the current live Neo4j produces a diff that adds Abū ʿAwāna + Muṣʿab + Ibn ʿUmar to Branch A and creates Branch B with the full Hannād→…→Ibn ʿUmar chain. No writes performed. Diff JSON saved as evidence.

### Phase 6b — Run repair (~3–5 days unattended)

- [ ] **T-6b.1** — Backup `all_hadiths_unified.csv` to `.bak-uniform-isnad-<ts>`. (P0)
- [ ] **T-6b.2** — Rebuild unified CSV via `python regen_unified_csvs.py` with the new uniform extractor. Verify per-tradition stats. (P0)
- [ ] **T-6b.3** — Run `npm run db:regen -- --mode=repair --dry-run` end-to-end on full 99,283 rows. Inspect the dry-run JSONL; count expected change types per source. Sanity-check that **most** Imami/Zaydi rows show diffs (resolver improvements + sanad_detail), most non-taḥwīl K6 rows show only minor narrator-position diffs, and Nahj al-Balāgha shows `unchanged` (no isnad genre). (P0)
- [ ] **T-6b.4** — If T-6b.3 reveals unexpected mass-deletion patterns (e.g., a parser bug that makes every row's diff look like "remove everything"), STOP and fix before going live. (P0 — abort criterion)
- [ ] **T-6b.5** — Detached run: `nohup npx tsx src/scripts/regen-isnad-graph.ts --mode=repair > logs/repair-<ts>.log 2>&1 &`. Use the 120s `WRITE_TX_TIMEOUT_MS` from 2026-06-08. ETA 3–5 days at the measured Railway rate. (P0)
- [ ] **T-6b.6** — Daily check-in on progress + errors. Resume from checkpoint if killed. (P1)
- [ ] **T-6b.7** — On completion, run `npx tsx src/scripts/diagnose-chain-data.ts` and verify all FR-6.6 thresholds. (P0)
- [ ] **T-6b.8** — Run `probe-tirmidhi.ts` (updated for multi-chain) as G-1/G-2/G-3 evidence. (P0)
- [ ] **T-6b.9** — Inject-human-edge end-to-end test on a non-production hadith ID; assert the edge survives a repair pass per G-7. (P0)
- [ ] **T-6b.10** — Architect verification subagent over the repaired state, including pre/post snapshot comparison from FR-6.3. (P0)

**Gate Φ-6:** Seven guardrails pass. Tirmidhi #1 displays 2 chains correctly to user. Zero hadiths lost all `:HAS_CHAIN` edges during repair. Track closes.

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

## Total estimated wall time

| Phase | Active hrs | Unattended hrs |
|---|---|---|
| 0 | 1 | — |
| 0.5 | 4 | — |
| 1 | 6 | — |
| 2 | 3 | — |
| 3 | 2 | — |
| 4 | 3 | — |
| 5 | 2 | — |
| 6a | 6 | — |
| 6b | 0.5 | 72–120 |
| 7 | 0.5 | — |
| **Total** | **23 hr** | **72–120 hr** |

Net ~3 days of focused implementation + 3–5 days for the mode-repair pass. The repair wall time is intentionally longer than fullregen would be — that's the cost of non-destructive surgical updates over 99k rows × ~3 round-trips per row at Railway's 72ms-per-edge rate. The user-explicit constraint is correctness over speed, and the gain is that any hand-curated or HITL-augmented edges (`r.source NOT STARTS WITH 'dv-'`) are preserved through the entire pass.
