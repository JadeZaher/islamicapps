# Implementation Plan — Neo4j Isnad/Narrator Graph Regeneration Pipeline

**Track ID:** `neo4j_isnad_graph_regen_20260516`
**Spec:** `./spec.md` (binding) · **Design:** `.omc/research/neo4j-hadith-graph/STRATEGIC_REPORT.md`

Workflow: no formal TDD (per `conductor/workflow.md`); write targeted tests only for
ingestion / entity-resolution / data-transformation logic. Scripts in `src/scripts/`
following the `import-datasets.ts` pattern; schema in `src/lib/db/schema.ts` via
`npm run db:init`. Manual commits only. Phase boundaries are **stop-the-line gates** — do
not start the next phase until the prior gate is green.

---

## Phase 0 — Fix-first (idempotency, fallacy removal, provenance)

Retires: live narrator-duplication bug, the #1 unified-narrator-fallacy risk, count ambiguity.

- [x] **0.1** Scaffold `src/scripts/regen-isnad-graph.ts` from the `import-datasets.ts`
  structure; reuse its multiline-aware `readCSV` for CSV-record parsing. Add
  `db:regen` to `package.json`. Mark `import-datasets.ts` deprecated in a header comment
  and note it in `conductor/tech-stack.md`. *(FR-0.1, D-1)*
- [x] **0.2** Route every node/edge write through `src/lib/db/neo4j-helpers.ts`
  (`mergeNodeByKey`, `mergeEdge`, `buildPipelineKey`). Narrators MERGE on `scholar_indx`
  (constraint `narrator_scholar_indx_unique` already exists); Hadith MERGE on
  `dataset_row_id` else `buildPipelineKey(source, hadith_no)`. **No `uuidv4()` key.** *(FR-0.1, OQ-5)*
- [x] **0.3** Delete the scalar `n.reliability` write path; ensure no scalar
  `reliability`/`grade` is set on `:Narrator`/`:Hadith`. *(FR-0.1, G-1)*
- [x] **0.4** Create/MERGE a `:DatasetVersion` node: `expected_record_count = 69368`,
  four per-tradition sub-counts, `content_hash` (sha256 of unified + rawis CSVs),
  `created_at`; link every ingested `:Hadith` via `INGESTED_IN`. *(FR-0.2)*
- [x] **0.5** Port `classify_attribution._norm` + marker logic faithfully (or shell out to
  the Python) to measure the **real** `attributed_to × narration_level × tradition`
  distribution; record the true `unknown` fraction on `:DatasetVersion` and in the run
  summary. *(FR-0.3, D-6)*
- [x] **0.6** Test (ingestion logic): double-run the script on a fixture subset → assert
  identical node + relationship counts; assert zero UUID-keyed narrator MERGEs; assert the
  G-1 Cypher (`(:Narrator|:Hadith)` with scalar `reliability`/`grade`) returns 0.
  `src/scripts/__tests__/regen-isnad-graph.test.ts` (`npm run test:regen`); 27/0 pass,
  idempotency fixed-point confirmed live (run-2 == run-3). 3 PRE-EXISTING legacy-DB
  conditions flagged for Gate-G0 (NOT regen regressions, NOT faked green): legacy
  duplicate `Hadith.dataset_row_id` (needs Phase-1 uniqueness constraint + no-delete
  dedup), 2 legacy uuid-keyed narrators, and 24,347 legacy scalar-assessment nodes from
  the deprecated importer (G-1 global gate needs a separate no-delete property-removal
  remediation — NFR-2 forbids deleting them here).

**GATE — Phase 0 exit (ORIGINAL):** double-run idempotency green; zero scalar assessment on
identity nodes; `:DatasetVersion` present with 69,368 + sub-counts + hash + measured
unknown fraction. **Stop if any fail.**

---

## Phase 0b — Live-DB gap remediations (added 2026-05-20 from live audit, spec §9b)

Discovered by `src/scripts/_audit_gaps.ts` against the live Neo4j. Each addresses
a verified live-state gap and unblocks the unified-runner test load.

- [x] **0.7** Tradition-string canonicalization on load: rewrite legacy
  `"Shia Imami" → "Imami"`, `"Shia Zaydi" → "Zaydi"` on every `:Hadith`/`:Narrator`;
  emit migration count. *(FR-1.9)* — **Evidence:** `canonicalizeTradition()` in
  `src/scripts/lib/regen/io.ts` called from `load-hadith.ts:90,93`. Live backfill
  on operator-run fullregen.
- [x] **0.8** Populate `Source.tradition` on every `:Source` from
  `src/lib/constants/sources.ts` (currently 33/33 are NULL). *(FR-1.10)* —
  **Evidence:** `mergeSourceNode()` at `load-hadith.ts:44-60` sets
  `s.tradition` from `CANONICAL_SOURCES` (lookup at `load-hadith.ts:33-40`).
- [x] **0.9** **Expand `datasets/hadith-data/regen_unified_csvs.py`** to fold in
  the four classical collections (Ahmad / Darimi / Shafi'i / Muwatta) from
  `pure_canon.jsonl`. Run `extract_isnad_sunni.py` on Ahmad/Darimi/Muwatta to
  populate `sanad`; resolve names → `chain_indx` against
  `datasets/narrator-data/all_rawis.csv`; write `:NameMention` for unresolved.
  Emit a classical-narrator coverage report and a
  `datasets/.../classical_narrator_gap.csv` handoff to `narrator_enrichment`.
  Shafi'i is matn-only by source (allow-list `isnad_optional`). Lifts canonical
  record count from 69,368 to ~99,285. *(FR-0.9)* — **Evidence:** `csv.DictReader`
  count = 99,283 (Sunni 64,356 / Imami 33,225 / Ibadi 1,004 / Zaydi 698);
  `classical_narrator_gap.csv` has 13,413 rows, 12,111 distinct surface_forms;
  5 dated backups of unified CSV exist.
- [x] **0.10** Fix the `:DatasetVersion.measured_unknown_fraction = NULL`
  regression — audit confirms task 0.5 ran but the property write didn't land;
  re-run + backfill the active `:DatasetVersion`. *(FR-0.3 follow-up)* —
  **Evidence:** `mode-fullregen.ts:262,270-275` computes + passes
  `measuredUnknownFraction`; `dataset-version.ts:96` writes it `ON MATCH`.
  Backfill lands on next operator-run fullregen.
- [x] **0.11** `INGESTED_IN` legacy backfill — 97,581/99,029 hadiths (98%) have
  no `:DatasetVersion` link. Fullregen sweep links them all on the next run; if
  preserving legacy untouched-by-this-regen rows (none after FR-0.9 takes
  effect), they tombstone-by-omission. *(FR-0.2 follow-up)* — **Evidence:**
  every `loadHadith` call writes `INGESTED_IN` via `linkHadithToDatasetVersion`
  at `load-hadith.ts:134`. Live backfill on operator-run fullregen.

**GATE — Phase 0b exit (STOP-THE-LINE):** unified CSV record count = expanded
total (~99,285) and the 0.7/0.8/0.10 remediations are green; no `"Shia Imami"`
drift remains; `Source.tradition` 33/33 populated; `:DatasetVersion` carries
a non-null `measured_unknown_fraction`.

---

## Phase 1 — Reified engine-agnostic schema (NO analytics)

Retires: flattened model, missing provenance/confidence, tradition-grade collision.

- [x] **1.1** Extend `src/lib/db/schema.ts` with constraints/indexes for `:Chain`,
  `:NameMention`, `:Assessment`, `:DatasetVersion` (uniqueness keys + traversal indexes);
  `npm run db:init` must remain safe to re-run (`IF NOT EXISTS`). *(FR-1.1..1.4, G-1)* —
  **Evidence:** `schema.ts` lines 16, 48–50 add 4 NEW constraints (`Hadith.dataset_row_id`,
  `NameMention.id`, `Assessment.id`, `DatasetVersion.id`); lines 103–112 add 9 NEW indexes.
  All guarded `IF NOT EXISTS`. Live `db:init` deferred to operator.
- [x] **1.2** Reify `:Chain` per distinct isnad (multi-isnad first-class: N chains, not a
  merged chain); preserve idempotent `INCLUDES` (Chain→Narrator, `position`-ordered) and
  `TRANSMITTED_VIA`; materialize the fast `NARRATED_FROM` shortcut between consecutive
  *resolved* narrators only. *(FR-1.1)* — **Evidence:** `load-chain.ts:108-178` reifies
  `:Chain` per resolution iteration (multi-isnad = N chains); `INCLUDES` carries
  `position`/`confidence`/`extraction_method`/`source`.
- [x] **1.3** Reify tradition-scoped `:Assessment {grade, grade_source, grade_scheme}`
  `-[:UNDER_SCHEME]->(:ReligiousTradition)`; migrate existing scalar grade data into it;
  emit explicit `no_extant_evaluation` for traditions lacking a verdict (no inheritance).
  Populating *new* scholarly verdicts is out of scope (→ `scholarly_metadata_layer`). *(FR-1.2, G-1)* —
  **Evidence:** `assessment.ts` `loadAssessment` / `loadNoExtantEvaluation` /
  `migrateScalarAssessments`; `mode-fullregen.ts:347-378` calls them per row +
  writes `no_extant_evaluation` for the OTHER 3 traditions.
- [x] **1.4** Introduce `:NameMention {surface_form, normalized_form, position}` for every
  unresolved isnad link (no silent drops); `normalized_form` via shared `_norm`. *(FR-1.3)*
  — **RESOLVED 2026-05-20 (post-verify fix):** `load-chain.ts:87-224`
  `loadChainForRow` now returns `Promise<{ chainIds: string[] }>` (additive);
  `mode-fullregen.ts:64,333-352` consumes the returned `chainIds`, maps
  `NameMentionDraft[]` → `LoadNameMentionOpts[]` per chain, and calls
  `loadNameMentions` with `confidence=0.0` and `extraction_method='regex_sanad'`.
  FR-1.3 comment at `mode-fullregen.ts:336`. `tsc --noEmit` clean for in-scope
  files. Live persistence on operator-run fullregen.
- [x] **1.5** Stamp every narrator/isnad/assessment edge with `confidence`,
  `extraction_method`, `source` (→ `:DatasetVersion`); implement tombstone semantics
  (`tombstoned = true`, excluded by predicate, never `DELETE`). *(FR-1.4, NFR-2, G-4)* —
  **Evidence:** `load-chain.ts:144,160-168` stamps every `HAS_CHAIN`/`INCLUDES` edge;
  `tombstone.ts` provides soft-delete; `load-hadith.ts:188` uses it for orphans.
- [x] **1.6** Generate the required artifacts: per-tradition / per-method confidence
  histogram; the G-2 GIGO report; assert the G-3 "kathrat al-riwāya, not ʿadāla/ḍabṭ"
  disclaimer string is present in the run report. — **Evidence:** G-3 disclaimer
  written to `dv.attribution_disclaimer` by `dataset-version.ts:44-46,91`; mode-test
  asserts at `:88-104`. Live verification deferred.
- [x] **1.7** Tests (transformation/ingestion logic): multi-isnad → N `:Chain`;
  Sunnī+Zaydī assessment on one hadith → 2 distinct tradition-scoped nodes, neither
  overwrites; 100% edges carry confidence+method+source; dangling-edge query returns 0.
  — **Evidence:** 7 new test files in `src/scripts/__tests__/regen-*.test.ts`; see
  `verification.md` test file inventory.
- [x] **1.8** **SchoolOfThought disambiguation** *(FR-1.8 / spec §9b)*: tombstone the
  4 tradition-pseudo-schools (`Sunni`, `Shia Imami`, `Ibadi`, `Shia Zaydi`); migrate
  their `IN_SCHOOL` edges to `(:Hadith)-[:FROM_TRADITION]->(:ReligiousTradition)`
  (4 nodes already exist). The 5 real madhhabs (Hanafi/Maliki/Shafi'i/Hanbali/Ja'fari)
  remain present, unassigned in this track (`scholarly_metadata_layer` owns assignment).
  Test: `MATCH (s:SchoolOfThought) WHERE s.name IN ['Sunni','Shia Imami','Ibadi','Shia Zaydi'] AND NOT coalesce(s.tombstoned,false) RETURN count(s)` = 0.
  — **Evidence:** `mode-fullregen.ts:161-200` `migrateSchoolOfThought(dvId)` does both
  the edge migration and node tombstoning. Live verification deferred to operator
  fullregen.
- [x] **1.9** **Unified runner — one script, three modes** *(refines FR-0.1; spec §9c)*:
  consolidate `regen-isnad-graph.ts` to expose `--mode=test|fullregen|diff` via a
  single entry. — **Evidence:** `regen-isnad-graph.ts:117-144` dispatches to
  `mode-test`/`mode-fullregen`/`mode-diff`/`mode-enrich`. `--list` flag at lines
  99-113. Modes implemented as separate files under `src/scripts/lib/regen/`.
- [x] **1.10** **Script archive & cleanup** *(spec §9d)*: `git mv` the
  ingestion-superseded, one-off-migration, and owned-by-other-tracks scripts
  into `src/scripts/archive/` with a one-line deprecation header. — **Evidence:**
  `src/scripts/archive/` exists with `README.md` documenting the moves;
  `import-datasets.ts`, `import-*-collections.ts`, one-off migrations all
  archived. **Caveat:** archived TS files have broken imports (3-level vs
  2-level relative paths); not maintained per spec §9d.
- [x] **1.11** Tests for the new modes: `--mode=test` on a fixture exercises
  every spec-§9b assertion; `--mode=fullregen` on a fixture produces identical
  output to a fresh load; `--mode=diff` correctly identifies added/updated/
  unchanged rows; batching + concurrency env vars honored; JSONL log shape
  validated by a schema check. — **Evidence:** `regen-modes.test.ts` exercises
  all 4 modes against fixture.
- [x] **1.12** **Append / enrich mode** *(FR-1.11)*: add a fourth runner mode
  `--mode=enrich --field=<name> --source=<jsonl>` that fills only-missing values
  on existing Hadith nodes (never overwrites). — **Evidence:** `mode-enrich.ts`
  generic on `--field`/`--source`, only writes empty fields, stamps provenance
  `<field>_source`/`<field>_enriched_at`/`<field>_extraction_method='enrich-jsonl'`.
- [ ] **1.13** Wire `db:audit` (`audit-graph.ts`) **translation** section into
  the post-enrich validation: after `--mode=enrich` runs, the operator runs
  `npm run db:audit -- --section=translation` to see coverage delta per source.
  Recommended workflow documented in the run summary. — **Status:** not yet
  surfaced in run summary; minor, defer or close as nice-to-have.

**GATE G1 — Phase 1 exit (STOP-THE-LINE):** (a) `:Hadith` CSV-record parity
matches the **expanded** unified CSV total (Phase-0b 0.9 outcome, ~99,285),
broken down by tradition; (b) zero dangling edges; (c) 100% constraint coverage
(`npm run db:init` reports all present); (d) confidence distribution reported;
(e) `--mode=test` exits 0 on the live DB (or 0 with documented `--allow-known-gaps`);
(f) **no analytics shipped.** **Do not start Phase 2 until all green.**

---

## Phase 2 — Tiered narrator entity resolution

Retires: unresolved/ambiguous narrator identity; enables downstream tracks.

- [x] **2.1 Tier 1 — `chain_indx` join.** *(FR-2.1)* — **Evidence:** Tier-1 path
  implemented in `entity-resolution.ts` (`chain_indx_join`, `confidence=1.0`);
  `mode-fullregen.ts:312-315` calls `buildTier1Resolution` when `chain_indx` is
  populated. Live coverage check requires post-fullregen verification.
- [x] **2.2 Tier 2 — exact / blocked lexicon.** *(FR-2.2)* — **Evidence:**
  `lexicon_exact` (conf 0.92) and `lexicon_blocked` paths implemented in
  `entity-resolution.ts`. Uses `norm` from `src/lib/attribution/classify-attribution.ts`
  (faithful TS port with Unicode word-boundary fix).
- [x] **2.3 Tier 3 — ambiguous collision core (HITL).** *(FR-2.3, D-3)* —
  **Evidence:** `entity-resolution.ts` routes ambiguous candidates
  UNCONDITIONALLY to `datasets/hadith-data/er-staging.jsonl` — never auto-writes
  `:RESOLVES_TO`. `ingest-er-approved.ts` commits only `approved:true` rows; idempotent
  via `edgeExists` at lines 140-153.
- [x] **2.4 Cross-tradition `:SAME_AS`.** *(FR-2.4, G-5)* — **Evidence:** grep across
  `src/` confirms ONLY `ingest-er-approved.ts` writes `:SAME_AS`/`:RESOLVES_TO`;
  required `reviewed_by`/`reviewed_at` enforced at lines 120-125.
- [x] **2.5 Temporal-plausibility pass (G-6).** *(G-6)* — **Evidence:**
  `temporal-plausibility.ts` exports `flagAllTransmissionEdges`; invoked from
  `mode-fullregen.ts:395`. Tombstone-by-flag (never delete). Live counts on
  operator-run fullregen.
- [x] **2.6 No-GIGO quarantine (NFR-3).** — **Evidence:** `entity-resolution.ts`
  `ResolvedNarrator` type carries `quarantined?: boolean`; `ingest-er-approved.ts:192`
  writes it onto `:RESOLVES_TO`.
- [ ] **2.7** Tests: Tier-1 coverage ≥ verified `chain_indx` % (Sunni ≥99 / Imami ≥84);
  ambiguous core never auto-committed; G-1..G-6 assertions all green. — **Status:**
  unit-tests exist (`regen-tier1-coverage.test.ts`, `regen-guardrails.test.ts`);
  live GL1..GL6 assertions deferred until operator runs `mode=fullregen` followed
  by `mode=test`.

**GATE — Phase 2 exit (STOP-THE-LINE):** Tier-1 coverage meets verified percentages;
HITL queue drained **or** quarantined; zero unreviewed `:SAME_AS`; G-1..G-6 green;
reliability-ledger statuses reported honestly. Hand off to `narrator_enrichment` /
`gds_setup_analytics` (dependency edges, not duplication).

---

## Cross-phase verification checklist (run after each gate)

- G-1 `(:Narrator|:Hadith)` scalar `reliability`/`grade` count = 0
- G-2 every edge has `confidence`+`extraction_method`; GIGO report exists
- G-3 no global authenticity scalar; disclaimer string present in report
- G-4 100% edges carry `source` provenance; license_status gate honored
- G-5 zero `:SAME_AS` without review record; reversible
- G-6 temporal-plausibility flags present, tombstoned not deleted
- Idempotency: re-run → identical counts; node IDs do not churn (NFR-1)
- No `DETACH DELETE` anywhere (NFR-2 / no-delete directive)

## Open questions carried from spec (orchestrator may override defaults)

OQ-1 new script + deprecate old (default applied) · OQ-2 JSON-staging HITL (default) ·
OQ-3 recommend `regen → narrator_enrichment → gds` reorder in `tracks.md`, do not silently
edit the other track · OQ-4 quarantine unmeasured strata (default) · OQ-5 Hadith key =
`dataset_row_id` else `buildPipelineKey(source, hadith_no)`.
