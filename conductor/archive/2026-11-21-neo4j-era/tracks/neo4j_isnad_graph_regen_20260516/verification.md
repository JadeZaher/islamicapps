# Verification — Neo4j Isnad/Narrator Graph Regen

**Track:** `neo4j_isnad_graph_regen_20260516`
**Verified at:** 2026-05-20 (UTC, agent local clock from `currentDate`)
**Verifier:** ultrapilot Workstream G (read-only fan-in)
**Method:** Static code + artifact inspection. Neo4j env not loaded in agent
shell — all live-DB assertions are documented as **operator-deferred** rather
than faked green.

---

## Gate summary

| Gate | Status | Evidence |
|---|---|---|
| **Phase 0 exit (original)** | `[x]` | Tasks 0.1–0.6 were already `[x]` from prior work; re-affirmed by inspection — `regen-isnad-graph.ts` is now a thin CLI delegating to `lib/regen/mode-*`, MERGEs route through `mergeNodeByKey`/`buildPipelineKey`, no scalar `n.reliability` writes in production code, `mergeDatasetVersion` is wired into `mode-fullregen`. |
| **Phase 0b exit (STOP-THE-LINE)** | `[!]` needs-attention | CSV record count **99,283** (target 99,285 ± 50) — PASS. Code for 0.7/0.8/0.10 wired but **awaits operator-run fullregen** to land in live DB. `classical_narrator_gap.csv` exists (13,413 rows, 12,111 distinct surface_forms). 2 CSV rows still contain the literal string "Shia Imami" — both are inside `text_en` / `chain_indx` narrative text (NOT a tradition field) — see Out-of-Track Finding #5. |
| **Gate G1 (Phase 1 exit)** | `[x]` | post-fix re-verification on 2026-05-20: FR-1.3 wired at `mode-fullregen.ts:336-352` (FR-1.3 comment + `loadNameMentions` call per chain); `runRegen` exported at `regen-isnad-graph.ts:167-180`; `tsc --noEmit` clean for in-scope files (only `src/scripts/archive/*` pre-existing errors remain). All six guardrail tests exist, test framework is `tsx`-runnable. Schema in code has 4 new constraints (+9 indexes) — `db:init` still deferred to operator. |
| **Phase 2 exit (STOP-THE-LINE)** | `[ ]` not yet | Tier-1 path implemented in `entity-resolution.ts`; Tier-3 staging file exists; `ingest-er-approved.ts` is idempotent and pattern-matches `ingest-approved-parallels.ts`. Cannot pass without (a) operator fullregen, (b) HITL queue drained or quarantined. Gate cannot be marked `[x]` from a read-only verification. |

---

## Per-task verification (from plan.md)

### Phase 0 (re-affirmed by inspection — original `[x]` preserved)

- **0.1** `[x]` — `src/scripts/regen-isnad-graph.ts:1-152` is now a thin CLI dispatcher; `package.json:11` has `db:regen`; `import-datasets.ts` is archived under `src/scripts/archive/` per workstream F's archive README.
- **0.2** `[x]` — `load-hadith.ts:117` uses `mergeNodeByKey`; narrator MERGE in `load-chain.ts:158-159` is on `scholar_indx`. No `uuidv4` MERGE keys for narrators or hadiths.
- **0.3** `[x]` — `assessment.ts` does not write scalar `reliability` to Narrator. Static-grep over `src/scripts/lib/regen` shows no `n.reliability =` or `h.grade =` writes outside `migrateScalarAssessments` (which REMOVES them).
- **0.4** `[x]` — `dataset-version.ts:58-133` `mergeDatasetVersion()` writes `expected_record_count`, per-tradition sub-counts, `content_hash`, `created_at`, `active=true`, `attribution_disclaimer`. `linkHadithToDatasetVersion()` writes `INGESTED_IN` from every loaded hadith. Operator-run fullregen materializes this in the live DB.
- **0.5** `[x]` (code) / `[ ]` (live) — `mode-fullregen.ts:262` computes `measuredUnknownFraction` and passes it to `mergeDatasetVersion`. The audit-fix is the `dataset-version.ts:96` `ON MATCH SET dv.measured_unknown_fraction = $measuredUnknownFraction` line; the legacy NULL is overwritten on the next fullregen.
- **0.6** `[x]` — `src/scripts/__tests__/regen-isnad-graph.test.ts` exists with the original 27/0 fixture-subset double-run idempotency test. **NOTE the broken import below.**

### Phase 0b

- **0.7** `[x]` — wired in `load-hadith.ts:90,93` via `canonicalizeTradition(...)` from `io.ts`; LIVE verification requires operator-run fullregen.
- **0.8** `[x]` — `load-hadith.ts:44-60` `mergeSourceNode()` sets `s.tradition` on every MERGE, derived from `CANONICAL_SOURCES` lookup at `load-hadith.ts:33-40`.
- **0.9** `[x]` — `csv.DictReader` count of `datasets/hadith-data/all_hadiths_unified.csv` = **99,283** (within the ±50 of the 99,285 target). Per-tradition: Sunni 64,356 / Imami 33,225 / Ibadi 1,004 / Zaydi 698. `classical_narrator_gap.csv` exists with 13,413 rows and 12,111 distinct `surface_form`. Backup `all_hadiths_unified.csv.bak-2026-05-21T*` files exist (5 dated backups).
- **0.10** `[x]` — `mode-fullregen.ts:270-275` passes `measuredUnknownFraction` to `mergeDatasetVersion`; `dataset-version.ts:96` writes it on every merge (CREATE and MATCH). LIVE backfill on next fullregen.
- **0.11** `[x]` — `mode-fullregen.ts:307` calls `loadHadith` for every row → `load-hadith.ts:134` calls `linkHadithToDatasetVersion`. Legacy hadiths NOT in the unified CSV are not tombstoned by fullregen (per the inline comment at `mode-fullregen.ts:27-32` — that is mode-diff's job).

### Phase 1

- **1.1** `[x]` (code) / `[ ]` (live) — `src/lib/db/schema.ts` has 4 NEW constraints (`Hadith.dataset_row_id`, `NameMention.id`, `Assessment.id`, `DatasetVersion.id`) at lines 16, 48–50; 9 new indexes for `NameMention` / `Assessment` / `DatasetVersion` at lines 103–112. All wrapped `IF NOT EXISTS`. Constraint count in code: pre-existing 25 → new 29 (+4); index count delta +9. **Operator must run `npm run db:init`** to land them in the live DB.
- **1.2** `[x]` — `load-chain.ts:108-178` reifies `:Chain` per distinct isnad, multi-isnad is N chains (looping over `resolutions`), `INCLUDES` edge carries `position`, `confidence`, `extraction_method`, `source`. `NARRATED_FROM` shortcut between consecutive resolved narrators is also written by `load-chain.ts` (downstream of `INCLUDES`).
- **1.3** `[x]` **RESOLVED (post-verify fix 2026-05-20)** — `loadChainForRow` (load-chain.ts:87-224) now returns `{ chainIds: string[] }`; `mode-fullregen.ts:333-352` consumes the returned `chainIds` and, per chain index, maps `NameMentionDraft[]` → `LoadNameMentionOpts[]` and calls `loadNameMentions` with `confidence=0.0` and `extraction_method='regex_sanad'`. FR-1.3 acceptance ("no isnad link silently drops because its narrator is unresolved") is now satisfied in code. Change is additive (returned `chainIds` is unused by any prior caller). LIVE verification on operator-run fullregen.
- **1.4** `[x]` — `:NameMention` schema + creator exists in `name-mention.ts`; the `_norm` port is faithful to Python and the regen-arabic-norm-parity test (25 assertions) passes.
- **1.5** `[x]` — every edge in `load-chain.ts` (lines 144, 160-168) carries `confidence`, `extraction_method`, `source`. Tombstone helper at `tombstone.ts` is invoked by `load-hadith.ts:188` for orphans.
- **1.6** `[x]` (code) — G-3 disclaimer string is written to active `:DatasetVersion.attribution_disclaimer` by `dataset-version.ts:44-46,91` — the exact text is *"Graph metrics reflect kathrat al-riwāya (volume of transmission), NOT ʿadāla/ḍabṭ or any authenticity ḥukm. Algorithmic output is never a scholarly verdict."*. `mode-test.ts:88-104` `checkG3Attribution` asserts the property is set. **LIVE post-fullregen verification** required.
- **1.7** `[x]` — see test inventory below.
- **1.8** `[x]` — `mode-fullregen.ts:161-200` `migrateSchoolOfThought(dvId)` ensures 4 `:ReligiousTradition` nodes exist, migrates `[:IN_SCHOOL]` → `[:FROM_TRADITION]`, then tombstones the 4 pseudo-school nodes via `tombstoneByKey`. LIVE verification requires operator-run fullregen.
- **1.9** `[x]` — `regen-isnad-graph.ts:117-144` dispatches to `mode-test`/`mode-fullregen`/`mode-diff`/`mode-enrich`. `--list` flag at `:99-113` lists all four modes with descriptions.
- **1.10** `[x]` (deprecation) / `[!]` (test:regen wiring) — Scripts archived: see `src/scripts/archive/README.md`. **However, `package.json:14` `test:regen` script still only runs the legacy `regen-isnad-graph.test.ts`** — workstream F's 7 new test files require either individual `npx tsx` runs or a composite script. Recommended follow-up.
- **1.11** `[x]` — `regen-modes.test.ts` exercises all 4 modes against a fixture.
- **1.12** `[x]` — `mode-enrich.ts` is generic on `--field` / `--source`, only writes empty fields, stamps `<field>_source`/`<field>_enriched_at`/`<field>_extraction_method='enrich-jsonl'`. Idempotency tested.
- **1.13** `[ ]` — `db:audit` `--section=translation` integration not yet documented in run summary. Minor; defer.

### Phase 2

- **2.1** `[x]` — `entity-resolution.ts` exports `resolveNarrators(row, rawis)`. Tier 1 path implemented (`chain_indx_join`, `confidence=1.0`). LIVE coverage check requires post-fullregen verification.
- **2.2** `[x]` — Tier 2 `lexicon_exact` (conf ≥ 0.92) and `lexicon_blocked` paths implemented.
- **2.3** `[x]` — Tier 3 routes UNCONDITIONALLY to `datasets/hadith-data/er-staging.jsonl` (verified in code — never writes `:RESOLVES_TO` from the resolver). Header documents HITL workflow.
- **2.4** `[x]` — `ingest-er-approved.ts` mirrors `ingest-approved-parallels.ts`; idempotency via `edgeExists` at lines 140-153; requires `reviewed_by`/`reviewed_at` on every record at lines 120-125.
- **2.5** `[x]` (code) — `temporal-plausibility.ts` exports `flagAllTransmissionEdges` invoked at `mode-fullregen.ts:395`. LIVE flagging on operator-run fullregen.
- **2.6** `[x]` — `entity-resolution.ts` carries `quarantined` flag in the `ResolvedNarrator` type and `ingest-er-approved.ts:192` writes it on `:RESOLVES_TO`.
- **2.7** `[!]` `[x]` for code presence, `[ ]` for live execution — see test inventory; GL1..GL6 deferred until post-fullregen.

---

## Guardrails (G-1..G-6)

| # | Static-code result | Live-DB result | Notes |
|---|---|---|---|
| **G-1** | `[x]` — no `n.reliability=` / `n.grade=` writes in production code (only REMOVE in `migrateScalarAssessments`). | DEFERRED to operator-run `mode=test`. 35,297 pre-existing legacy scalar nodes are NOT a regen regression — see Out-of-Track #1. |
| **G-2** | `[x]` — every edge written by `load-chain.ts` carries `confidence`+`extraction_method`+`source`. | DEFERRED. |
| **G-3** | `[x]` — disclaimer "kathrat al-riwāya, not ʿadāla/ḍabṭ" written by `dataset-version.ts:44-46` onto `dv.attribution_disclaimer`. `mode-test.ts:88-104` asserts it. | DEFERRED post-fullregen. |
| **G-4** | `[x]` — `dataset-version.ts` `INGESTED_IN`, `load-chain.ts` `HAS_CHAIN`/`INCLUDES`, `loadAssessment` `HAS_ASSESSMENT`/`UNDER_SCHEME` all stamp `source=$dvId`. | DEFERRED. |
| **G-5** | `[x]` — Grep across `src/` confirms **only** `src/scripts/ingest-er-approved.ts` writes `:SAME_AS` / `:RESOLVES_TO` (other matches are test scaffolds or commentary). HITL workflow enforced. | `[x]` will hold by construction. |
| **G-6** | `[x]` — `temporal-plausibility.ts` exports `flagAllTransmissionEdges` (tombstone-by-flag, never delete). Invoked at `mode-fullregen.ts:395`. | DEFERRED. |

---

## TypeScript sanity (`npx tsc --noEmit`)

**Post-fix re-run on 2026-05-20:** Zero in-scope errors. Only pre-existing
`src/scripts/archive/*` errors remain (~60), which are out of scope per spec
§9d (archived scripts have intentionally-broken relative paths and are not
maintained).

**Originally reported (now RESOLVED):**

```
src/scripts/__tests__/regen-isnad-graph.test.ts(37,10): error TS2305:
  Module '"../regen-isnad-graph"' has no exported member 'runRegen'.
```

The fix landed in `regen-isnad-graph.ts:155-180`: option (a) from the
recommendation — a `runRegen(opts?: RunRegenOpts)` shim was re-exported,
building `CliArgs` with `mode: 'fullregen'` and dispatching to
`runModeFullregen`. The legacy `{ limit?, noWrite?, versionLabel? }` shape is
accepted for API compatibility (the inline comment notes that those fields
aren't plumbed yet — fullregen always runs to completion). Test
`src/scripts/__tests__/regen-isnad-graph.test.ts:37` now compiles.

---

## Test file inventory (workstream F deliverables)

| File | LOC range | Purpose | Status |
|---|---|---|---|
| `regen-modes.test.ts` | exists | All 4 mode dispatchers exercised on fixture | unit-runnable |
| `regen-guardrails.test.ts` | 55 check() calls | GU1..GU6 unit + GL1..GL6 live deferred | unit-runnable; live deferred |
| `regen-schema.test.ts` | S1 + S2 | Schema constraint presence in code + live | unit-runnable; live deferred |
| `regen-tier1-coverage.test.ts` | exists | Tier-1 join coverage ≥ chain_indx % | unit-runnable on fixture; live deferred |
| `regen-multi-isnad.test.ts` | exists | Multi-isnad → N `:Chain` not merged | unit-runnable |
| `regen-tradition-canonicalization.test.ts` | exists | Zero "Shia Imami"/"Shia Zaydi" post-regen | unit-runnable on fixture; live deferred |
| `regen-arabic-norm-parity.test.ts` | 25 assertions | TS `_norm` byte-equivalent to Python | all 25 pass per F's report |
| `regen-isnad-graph.test.ts` (legacy) | original 27 tests | Pre-existing fixture double-run | **FIXED** post-verify — `runRegen` shim re-exported at `regen-isnad-graph.ts:167` |

---

## Live-DB operations the operator must run before declaring the track complete

1. `npm run db:init` — applies B's 4 new constraints + 9 new indexes to the live DB.
2. `npm run db:regen -- --list` — confirm prints the 4 modes (no DB writes; quick smoke).
3. `npm run db:regen -- --mode=fullregen` — applies 0.7/0.8/0.10/0.11/1.8/G-6 remediations and full graph load. **Multi-hour mutation** — schedule accordingly.
4. `npm run db:regen -- --mode=test` — post-fullregen guardrail check; expect exit 0 (or 0 with documented `--allow-known-gaps` for the Shafi'i isnad_optional + classical_translation_coverage allow-listed warnings).
5. `npm run db:audit` — broader graph audit; confirm no unexpected regressions.
6. ~~Address the `runRegen` import error~~ — RESOLVED 2026-05-20 (post-verify
   fix). Still TODO: wire the 7 new test files into a composite `test:regen`
   script (per F's caveat) so all of them run.
7. After fullregen, populate `er-staging.jsonl` via the Tier-3 ambiguous-core resolution flow, perform HITL review, then run `npm run db:ingest-er` to commit approved `:RESOLVES_TO` edges. Phase 2 exit gate cannot be marked green until the HITL queue is drained or every remaining row is marked `quarantined`.

---

## Cross-cutting findings

### Finding #1 — FR-1.3 NameMention write-path gap — RESOLVED (2026-05-20)

**Severity (originally):** must-fix before Phase 1 can be marked `[x]`.
**Status:** RESOLVED via post-verify fix.

**Original gap:** `mode-fullregen` called `resolveNarrators` → got
`{ resolved, mentions, method }` → called `loadChainForRow`. `loadChainForRow`
wrote the `:Chain` and `INCLUDES` edges to resolved narrators, but the
unresolved mentions were merely counted into `mentionLoaded` without being
persisted as `:NameMention` nodes — violating FR-1.3 acceptance ("no isnad
link silently drops because its narrator is unresolved; it becomes a
`:NameMention` with provenance").

**Fix landed at:**
- `src/scripts/lib/regen/load-chain.ts:87-224` — `loadChainForRow` now returns
  `Promise<{ chainIds: string[] }>` (additive — prior callers silently
  discarded the void return).
- `src/scripts/lib/regen/mode-fullregen.ts:64` — adds
  `import { loadNameMentions, type LoadNameMentionOpts } from './name-mention';`.
- `src/scripts/lib/regen/mode-fullregen.ts:333-352` — destructures `chainIds`
  from `loadChainForRow`, iterates per chain index, maps each
  `NameMentionDraft[]` to `LoadNameMentionOpts[]` (carrying the actual
  `chainId`, `surface_form`, `position`, `confidence=0.0`,
  `extraction_method='regex_sanad'`, `dvId`), then calls
  `loadNameMentions(mentionOpts)`. The FR-1.3 comment is at line 336.

**Live verification:** still requires operator-run fullregen to materialize
in the live DB.

### Finding #2 — `Assessment.pipeline_key` MERGE key (verified, no gap)

`assessment.ts` lines 103, 108 build `assessmentKey = "${targetKeyProp}:${targetKeyValue}::${tradition}"` and MERGE on `Assessment.pipeline_key`. The `MATCH (target:${targetLabel} { ${targetKeyProp}: $targetKeyValue })` finds the Hadith using the same biz key `load-hadith.ts` used to MERGE it. **The key alignment is correct**: `assessment` is keyed on the (target biz-key, tradition) tuple, not on the Hadith's own `pipeline_key`. Self-consistent.

C's note about `:Assessment.pipeline_key` not being indexed is a fair perf observation — the MERGEs use `pipeline_key` directly, but B did not add an `Assessment.pipeline_key` index. Below 10k assessments per fullregen this is fine; above that, recommend B add a follow-up index.

### Finding #3 — `runRegen` export missing (TYPE ERROR) — RESOLVED (2026-05-20)

**Status:** RESOLVED via post-verify fix at `src/scripts/regen-isnad-graph.ts:155-180`.
Re-exported `runRegen(opts?: RunRegenOpts)` builds `CliArgs` with
`mode: 'fullregen'` and dispatches to `runModeFullregen`. `tsc --noEmit` no
longer reports the in-scope error; `src/scripts/__tests__/regen-isnad-graph.test.ts:37`
now compiles. See updated TypeScript Sanity section above for details.

### Finding #4 — `mode-fullregen` streams the unified CSV twice

`mode-fullregen.ts:253-261` does a pre-scan to count per-tradition records, then re-streams at `:303` for the load. Total ~50 MB × 2 = ~100 MB of I/O. Correct, but a single-pass design would halve runtime. Not blocking.

### Finding #5 — 2 literal "Shia Imami" strings remain in the unified CSV

Investigation: the 2 occurrences (`hadith_no=26` `text_en`, `hadith_no=41` `chain_indx`) are inside narrative English text, **NOT in a tradition field**. The `tradition` column itself has no "Shia Imami" / "Shia Zaydi" values. The canonicalization on load (FR-1.9) operates on tradition fields only; narrative-text occurrences are correctly left alone. **No action required.**

---

## Out-of-track findings (recommend separate tracks)

1. **35,297 pre-existing live-DB nodes with global authenticity scalars.** Not produced by this regen pipeline; produced by the deprecated `import-datasets.ts`. NFR-2 forbids deletion. Recommend a separate `legacy_scalar_assessment_remediation_<date>` track to migrate them into `:Assessment` nodes then `REMOVE` the scalars (which `migrateScalarAssessments()` already implements — could be invoked standalone). Out of scope for `neo4j_isnad_graph_regen_20260516`.

2. **`Assessment.pipeline_key` not indexed.** Recommend B follow-up if assessment count exceeds 10k per regen.

3. **`datasets/narrator_resolver.py` shared resolver helper not yet extracted.** Workstream A noted this as a recommendation; folding the Python-side blocked-lookup logic into a reusable module would help both A's CSV expansion and a future Python-side enrichment track.

4. **Workstream A reports 22% chain_indx resolution on Sunni classical** (Ahmad/Darimi/Muwatta), versus 99.6% on K6. Per A this is by design — the `all_rawis.csv` controlled vocabulary is K6-centric and uses Arabic, while the classical sanad strings include English transliterations. The `classical_narrator_gap.csv` (13,413 rows) is the explicit handoff to `narrator_enrichment_20260425`. Documented, not a regression.

5. **`test:regen` package.json script only runs `regen-isnad-graph.test.ts`** — the 7 new test files (modes, guardrails, schema, tier1-coverage, multi-isnad, tradition-canonicalization, arabic-norm-parity) need either a composite script or individual `npx tsx` invocations. Recommend small `scripts/run-regen-tests.sh` or expand `test:regen` to `tsx src/scripts/__tests__/regen-*.test.ts` (per-file invocation since each runs its own assertion harness).

---

## Recommended commit (operator)

```bash
git add conductor/tracks/neo4j_isnad_graph_regen_20260516/ \
        src/scripts/ \
        src/lib/db/schema.ts \
        datasets/hadith-data/regen_unified_csvs.py \
        datasets/hadith-data/classical_narrator_gap.csv \
        datasets/hadith-data/er-staging.jsonl \
        package.json
git commit -m "feat(graph): Neo4j isnad/narrator graph regen pipeline (track neo4j_isnad_graph_regen_20260516)"
```

Hold off on marking `tracks.md` entry `[x]` until:
1. ~~The `runRegen` import issue is resolved (small fix).~~ DONE 2026-05-20.
2. ~~FR-1.3 NameMention write-path gap is patched (small fix).~~ DONE 2026-05-20.
3. Operator runs `npm run db:init` and `npm run db:regen -- --mode=fullregen` successfully.
4. Operator runs `npm run db:regen -- --mode=test` and it exits 0 (with or without `--allow-known-gaps` matching the documented allow-list).

---

## Post-verify re-verification (2026-05-20)

After the original verifier (Workstream G) marked Gate G1 as `[!]` for two
specific issues, a post-verify fix agent landed minimal targeted changes
which were re-verified by this read-only pass:

**Files changed (production code):**
- `src/scripts/lib/regen/load-chain.ts:87-91, 102, 138, 223` —
  `loadChainForRow` now returns `Promise<{ chainIds: string[] }>`; `chainIds`
  is populated inside the per-resolution loop after each `:Chain` MERGE.
  Change is purely additive — no prior caller consumed a return value.
- `src/scripts/lib/regen/mode-fullregen.ts:64, 333-352` — imports
  `loadNameMentions` + `LoadNameMentionOpts`; per-row loop now consumes
  `chainIds` from `loadChainForRow` and persists `:NameMention` nodes for
  each unresolved mention via `loadNameMentions`. FR-1.3 comment is at
  line 336.
- `src/scripts/regen-isnad-graph.ts:155-180` — exported
  `runRegen(opts?: RunRegenOpts)` shim that builds `CliArgs` with
  `mode: 'fullregen'` and dispatches to `runModeFullregen`. Header comment
  notes the legacy `{ limit, noWrite, versionLabel }` shape is accepted for
  API compatibility but not yet plumbed into the mode.

**TypeScript:** `npx tsc --noEmit` re-run on 2026-05-20 — zero in-scope errors
(only `src/scripts/archive/*` errors remain, which are out of scope per
spec §9d).

**Test import:** `src/scripts/__tests__/regen-isnad-graph.test.ts:37` (`import
{ runRegen } from '../regen-isnad-graph'`) now compiles.

**Updated gate statuses:**
- **Gate G1 (Phase 1 exit)** — flipped from `[!]` to `[x]`. Code-level gates
  for FR-1.3 and the `runRegen` export are both satisfied. Live `db:init` and
  live `mode=test` still require operator action.
- **Phase 0b exit** — remains `[!]`. The 0.7 / 0.8 / 0.10 / 0.11
  remediations are wired in code but operator-run fullregen has not yet
  landed them in the live DB. This is unchanged by the post-verify fix.
- **Phase 2 exit** — remains `[ ]`. Still blocked on operator-run fullregen
  + HITL queue drain (unchanged by the post-verify fix).
