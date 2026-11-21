# Ultrapilot Passoff — Neo4j Isnad/Narrator Graph Regen

**Track:** `neo4j_isnad_graph_regen_20260516`
**Authoritative spec:** [`spec.md`](./spec.md) (binding) · **Plan:** [`plan.md`](./plan.md)
**Design source:** [`.omc/research/neo4j-hadith-graph/STRATEGIC_REPORT.md`](../../../.omc/research/neo4j-hadith-graph/STRATEGIC_REPORT.md)

> **Purpose.** Partition the remaining Phase-0b / 1 / 2 work into non-overlapping
> file-owned workstreams so ultrapilot can run them in parallel without merge
> conflicts. Each workstream is a self-contained agent prompt with explicit
> file ownership, entry/exit criteria, and the shared invariants every agent
> must honor.

---

## How to launch

```
/ultrapilot @conductor/tracks/neo4j_isnad_graph_regen_20260516/ultrapilot-passoff.md
```

Or paste the line below into Claude as a prompt:

> Implement the Neo4j isnad/narrator graph regen track in parallel using the
> passoff in `conductor/tracks/neo4j_isnad_graph_regen_20260516/ultrapilot-passoff.md`.
> Each agent strictly owns the files listed in its workstream — no
> cross-writes. Stop at each gate (Phase 0b exit, Gate G1, Phase 2 exit) and
> hand the verification step to the verifier agent before proceeding.

---

## Pre-flight (every agent reads first)

1. **Spec** — `conductor/tracks/neo4j_isnad_graph_regen_20260516/spec.md` (sections 0–8 binding; §9b/c/d encode the live-DB gaps and the unified-runner contract).
2. **Plan** — `conductor/tracks/neo4j_isnad_graph_regen_20260516/plan.md` (your task IDs live here; Phase 0a is already `[x]` complete — do not redo).
3. **Strategic report** — `.omc/research/neo4j-hadith-graph/STRATEGIC_REPORT.md` (sections 0, 2, 5, 6).
4. **Existing reference** — `src/scripts/regen-isnad-graph.ts`, `src/scripts/__tests__/regen-isnad-graph.test.ts`, `src/lib/db/{neo4j,neo4j-helpers,schema}.ts`, `datasets/classify_attribution.py`, `datasets/extract_isnad_sunni.py`, `datasets/hadith-data/regen_unified_csvs.py`.
5. **Your own workstream section below** (§ A–F).

---

## Global invariants (NON-NEGOTIABLE for every agent)

These are spec §5 G-1..G-6 + repo memory rules, restated tactically:

1. **Identity ≠ Assessment.** Never write `reliability`, `grade`, or any scalar verdict on a `:Narrator` or `:Hadith` node. Verdicts go on tradition-scoped `:Assessment` nodes.
2. **No deletes.** Use `tombstoned = true` + `superseded_by = <DatasetVersion.id>` instead of `DETACH DELETE`. This is the standing `feedback_no_delete_backup.md` rule.
3. **Stable business keys.** MERGE Narrators on `RAWI:scholar_indx`, MERGE Hadiths on `dataset_row_id` else `buildPipelineKey(source, hadith_no)`. **Never** on `uuidv4()`.
4. **Parameterized Cypher only.** No string interpolation of user/CSV data into queries.
5. **Canonical record count is the CSV-record count** (`csv.DictReader` semantics), NEVER `wc -l` (Arabic text has embedded newlines — `wc -l` over-counts by ~14%). After Phase-0b 0.9 lands, the expected total is ~99,285 (Sunni 34,441 K6 + Imami 33,225 + Ibadi 1,004 + Zaydi 698 + ~29,917 classical). Pin via `:DatasetVersion.expected_record_count`.
6. **Tradition canonicalization.** Use `"Imami"` / `"Zaydi"` everywhere — NEVER `"Shia Imami"` / `"Shia Zaydi"` (legacy DB drift; task 0.7 rewrites them).
7. **Idempotency.** Every loader must satisfy: a second run on the same `:DatasetVersion` produces identical counts.
8. **No analytics in this track.** GDS centrality, Louvain, link prediction → `gds_setup_analytics_20260425` (out of scope, dependency edge only).
9. **Honest failure.** If a presence check can't pass, exit non-zero with a clear message. Do NOT mark a task `[x]` you faked green.
10. **Tests where logic warrants.** Per `conductor/workflow.md`: no formal TDD; add targeted tests for ingestion / ER / data-transformation logic only. Skip UI / trivial CRUD tests.

---

## File-ownership matrix (the partition that prevents conflicts)

| Workstream | Owned files (write) | Reads only |
|---|---|---|
| **A — Data prep (Python)** | `datasets/hadith-data/regen_unified_csvs.py`, `datasets/extract_isnad_sunni.py`, `datasets/classify_attribution.py`, NEW `datasets/hadith-data/classical_narrator_gap.csv` (output) | `datasets/.../pure_canon.jsonl`, `datasets/narrator-data/all_rawis.csv` |
| **B — Schema** | `src/lib/db/schema.ts` | `src/lib/db/neo4j-helpers.ts` (interfaces) |
| **C — Core loader modules (NEW)** | NEW `src/scripts/lib/regen/{io,dataset-version,load-hadith,load-chain,assessment,name-mention,tombstone,temporal-plausibility}.ts` | spec, schema.ts, neo4j-helpers.ts |
| **D — Entity resolution (NEW)** | NEW `src/scripts/lib/regen/entity-resolution.ts`, NEW `src/scripts/ingest-er-approved.ts`, NEW `datasets/hadith-data/er-staging.jsonl` (output) | all_rawis.csv, sunni_isnad.jsonl |
| **E — Mode dispatcher + enrich** | `src/scripts/regen-isnad-graph.ts` (CLI + mode dispatch only), NEW `src/scripts/lib/regen/{mode-test,mode-fullregen,mode-diff,mode-enrich}.ts` | workstream C modules' exports |
| **F — Tests** | `src/scripts/__tests__/regen-*.test.ts` (all matching the existing test file's pattern) | every workstream's code |
| **G — Verifier** (run last) | none — read-only verification | every workstream's output |

**Rule:** if you need to write to a file outside your owned column, surface it on the integration-interfaces section below and wait for the verifier handoff. Do NOT cross-write.

---

## Integration interfaces (so modules compose without coordination)

```ts
// src/scripts/lib/regen/io.ts   (workstream C)
export function readUnifiedCsv(path: string): AsyncIterable<UnifiedRow>;
export function readAllRawis(path: string): Promise<Map<number, RawiRecord>>;

// src/scripts/lib/regen/dataset-version.ts   (workstream C)
export async function mergeDatasetVersion(opts: {
    expectedRecordCount: number;
    perTraditionCounts: Record<string, number>;
    contentHash: string;
    measuredUnknownFraction?: number;
}): Promise<{ id: string }>;

// src/scripts/lib/regen/load-hadith.ts   (workstream C)
export async function loadHadith(row: UnifiedRow, ctx: LoadContext): Promise<void>;
// ctx carries: dataset-version id, batch handle, logger, mode (test|fullregen|diff|enrich)

// src/scripts/lib/regen/entity-resolution.ts   (workstream D)
export type ErTier = 'chain_indx_join' | 'lexicon_exact' | 'lexicon_blocked' | 'rerank' | 'regex_sanad';
export async function resolveNarrators(
    row: UnifiedRow,
    rawis: Map<number, RawiRecord>,
): Promise<{ resolved: ResolvedNarrator[]; mentions: NameMentionDraft[]; method: ErTier; }>;

// src/scripts/regen-isnad-graph.ts   (workstream E)
// CLI only. Dispatches to a mode handler based on --mode=test|fullregen|diff|enrich.
// All real work lives in the mode-* modules.
```

These signatures are the contract. Workstreams C and D may add private helpers freely; the public exports above are the only stable surface.

---

## Workstreams

### A — Data prep (Python)

**Owns:** `datasets/hadith-data/regen_unified_csvs.py`, `datasets/extract_isnad_sunni.py` (extension), `datasets/classify_attribution.py` (read-only reuse), new output `datasets/hadith-data/classical_narrator_gap.csv`.
**Plan tasks:** **0.9** (the prerequisite).
**Spec refs:** **FR-0.9**, §9b.

**Tasks:**
1. Extend `regen_unified_csvs.py` to ingest the four classical collections from `pure_canon.jsonl` (Musnad Ahmad 23,529 / Sunan al-Darimi 2,478 / Musnad al-Shafi'i 2,054 / Muwatta' Malik 1,856), tagging `tradition='Sunni'` and using canonical source names from `src/lib/constants/sources.ts`.
2. Run `extract_isnad_sunni.py` over Ahmad / Darimi / Muwatta Arabic text (Shafi'i is matn-only by source — do NOT attempt isnad extraction on it). Populate the `sanad` column.
3. Resolve sanad names → `chain_indx` by lookup against `datasets/narrator-data/all_rawis.csv`: exact match first, then blocked match using `classify_attribution._norm`. Reuse the Phase-2 Tier-1/2 logic spec § FR-2.1/FR-2.2 (or expose your resolver so workstream D can share it — preferred).
4. Write unresolved-name set to `datasets/hadith-data/classical_narrator_gap.csv` (columns: `surface_form, normalized_form, source, hadith_no, first_seen_at, count`). This is the handoff to `narrator_enrichment_20260425`.
5. Update the per-tradition record counts in the unified CSV builder to emit the new total (~99,285).

**Exit criteria:**
- `all_hadiths_unified.csv` record count = ~99,285 (csv.DictReader); sub-counts match.
- Sunni `chain_indx` populated on Ahmad/Darimi/Muwatta rows where extraction succeeded (target: same baseline `extract_isnad_sunni.py` achieves on K6, ≈ 55%).
- Shafi'i rows have no `chain_indx` and no `sanad` (per FR-0.9 allow-list).
- `classical_narrator_gap.csv` exists with unresolved set + counts.
- Coverage report printed to stdout at end of run.

**Do NOT touch:** any `.ts` file, any Neo4j-side code.

---

### B — Schema

**Owns:** `src/lib/db/schema.ts`.
**Plan tasks:** **1.1**, partial **1.8** (the schema-side of SchoolOfThought disambiguation).
**Spec refs:** **FR-1.1..1.4**, **FR-1.8**, G-1.

**Tasks:**
1. Add (or verify present, with `IF NOT EXISTS`) uniqueness constraints + traversal indexes for: `:Chain {id}`, `:NameMention {id}`, `:Assessment {id}`, `:DatasetVersion {id}`, `:ReligiousTradition {name}`.
2. Verify the existing `narrator_scholar_indx_unique` constraint is correct and ergonomic.
3. Add a uniqueness constraint on `:Hadith.dataset_row_id` (audit flagged legacy duplicates — they'll be tombstoned by workstream C, but the constraint blocks new ones).
4. `npm run db:init` MUST remain re-runnable (every constraint guarded by `IF NOT EXISTS`).

**Exit criteria:**
- `npm run db:init` succeeds on the live DB.
- `SHOW CONSTRAINTS` includes every label this track touches.
- The pre-existing constraint count (23) increases only by NEW constraints; no constraint is `DROP`ped.

**Do NOT touch:** `regen-isnad-graph.ts`, any loader.

---

### C — Core loader modules (NEW)

**Owns:** `src/scripts/lib/regen/{io,dataset-version,load-hadith,load-chain,assessment,name-mention,tombstone,temporal-plausibility}.ts` (every file in this directory is NEW).
**Plan tasks:** **1.2, 1.3, 1.4, 1.5, 1.6**, partial **2.5** (temporal-plausibility), partial **0.10/0.11** (DatasetVersion provenance + INGESTED_IN backfill).
**Spec refs:** **FR-1.1..1.4, FR-1.10**, **G-4, G-6**, NFR-2.

**Tasks per module:**
- `io.ts` — multiline-aware CSV reader (reuse the pattern from `import-datasets.ts` archived version if helpful), JSONL streaming reader, JSONL logger writing to `logs/regen-<mode>-<dvId>.jsonl`.
- `dataset-version.ts` — `mergeDatasetVersion`; computes per-tradition sub-counts + content-hash; links every loaded `:Hadith` via `INGESTED_IN`; writes `measured_unknown_fraction`.
- `load-hadith.ts` — Hadith MERGE on stable business key; `Source.tradition` set from `src/lib/constants/sources.ts`; canonicalize tradition strings (`"Shia Imami"` → `"Imami"`, etc.); apply tombstone semantics on supersession.
- `load-chain.ts` — reify `:Chain` per distinct isnad; multi-isnad is N chains; `INCLUDES` carries `position`; materialize `NARRATED_FROM` shortcut only between resolved narrators.
- `assessment.ts` — tradition-scoped `:Assessment {grade, grade_source, grade_scheme}` `-[:UNDER_SCHEME]->(:ReligiousTradition)`; explicit `no_extant_evaluation` when a tradition has no verdict; **migrate existing scalar grades into assessments** (then null the scalars).
- `name-mention.ts` — `:NameMention {surface_form, normalized_form, position}` for every unresolved narrator link; `normalized_form` via shared Arabic `_norm`.
- `tombstone.ts` — utility for "soft delete": `SET n.tombstoned = true, n.superseded_by = $dvId`; an `excludeTombstoned()` predicate helper for projections.
- `temporal-plausibility.ts` — using `all_rawis.death_date_hijri`, flag transmission edges where teacher death precedes student floruit. Sets `temporal_plausibility = 'impossible'` or `'unknown'`. Tombstone, never delete.

**Every edge written by these modules MUST carry:** `confidence` (0–1), `extraction_method` (`chain_indx_join` | `lexicon_exact` | `lexicon_blocked` | `rerank` | `regex_sanad`), and `source` provenance pointing to the active `:DatasetVersion`.

**Exit criteria:**
- All eight files exist, exported per the interface signatures above.
- Each is a pure module (no side effects on import; no top-level Cypher).
- Mode-handler agents (workstream E) can import them without any further refactor.

**Do NOT touch:** `regen-isnad-graph.ts` (workstream E owns it), `schema.ts` (workstream B), `entity-resolution.ts` (workstream D).

---

### D — Entity resolution (NEW)

**Owns:** `src/scripts/lib/regen/entity-resolution.ts` (NEW), `src/scripts/ingest-er-approved.ts` (NEW), `datasets/hadith-data/er-staging.jsonl` (NEW, output).
**Plan tasks:** **2.1, 2.2, 2.3, 2.4**, partial **2.6** (no-GIGO quarantine).
**Spec refs:** **FR-2.1..2.4**, **G-5**, NFR-3.

**Tasks:**
1. **Tier 1** — `chain_indx` join. For Sunni rows with numeric ID array, emit `:NARRATED_FROM` edges keyed on `RAWI:scholar_indx` with `extraction_method='chain_indx_join'`, `confidence=1.0`. Verified: Sunni 99% of K6 + the new classical rows (where workstream A populated chain_indx).
2. **Tier 2** — exact / blocked lexicon. For rows missing chain_indx (Imami 16% gap, Ibadi 100%, Zaydi 100%, Sunni 1%): reuse `classify_attribution._norm`; exact match → `lexicon_exact` (conf ≥ 0.9); blocked normalized-key match → `lexicon_blocked` with justified confidence.
3. **Tier 3** — ambiguous collision core (Abū Jaʿfar = al-Kulaynī/al-Bāqir/al-Jawād, Abū ʿAbd Allāh = al-Ṣādiq/others, etc.). Graph-prior retrieve → rerank using `all_rawis` nasab/tabaqa/death-date features. **Do NOT auto-write**: emit ranked candidates + features to `datasets/hadith-data/er-staging.jsonl`.
4. **`src/scripts/ingest-er-approved.ts`** — idempotent script that reads a human-approved subset of the staging JSONL (filter on `approved: true`), writes `:RESOLVES_TO` edges with `extraction_method='rerank'`, `reviewed_by`, `reviewed_at`. Pattern mirrors the existing `ingest-approved-parallels.ts`. Add `db:ingest-er` to `package.json`.
5. **Cross-tradition `:SAME_AS`** is handled the same way: candidate → staging → human approval → ingest. Test asserts zero `:SAME_AS` without `reviewed_by`.
6. **No-GIGO quarantine** (NFR-3): resolutions for unmeasured strata (Imami-gap, transliterated, cross-tradition) get `quarantined = true`; queries filter them out by default; `db:audit` can include them with a flag.

**Exit criteria:**
- `resolveNarrators(row, rawis)` returns `{resolved, mentions, method}` per the integration contract above.
- Tier-1 coverage on the live data is ≥ the verified `chain_indx` percentages (Sunni K6 ≥ 99%; Sunni classical ≥ 55%; Imami ≥ 83% AFTER chain_indx text→IDs is solved, else 0%; Ibadi/Zaydi 0% by design — they go to Tier 2).
- Ambiguous core writes to staging only, never auto-commits.
- The HITL queue is documented (a one-page note inline in the staging JSONL header).

**Do NOT touch:** any other `lib/regen/*.ts` (workstream C), `regen-isnad-graph.ts` (workstream E), `schema.ts` (workstream B).

---

### E — Mode dispatcher + enrich mode

**Owns:** `src/scripts/regen-isnad-graph.ts` (CLI + dispatch only; all real work delegated to `lib/regen/`), NEW `src/scripts/lib/regen/{mode-test,mode-fullregen,mode-diff,mode-enrich}.ts`.
**Plan tasks:** **0.7, 0.8, 1.9, 1.12**, partial **1.10** (the package.json edits already landed).
**Spec refs:** **FR-1.9..1.11**, §9c.

**Tasks:**
1. Rewrite `regen-isnad-graph.ts` as a thin CLI: parse `--mode=test|fullregen|diff|enrich`, `--field`, `--source`, `--allow-known-gaps`, `--batch-size`, `--concurrency`. Delegate immediately to the matching `mode-*` module.
2. **`mode-fullregen.ts`** — tombstone old `:DatasetVersion`'s graph (NEVER `DETACH DELETE`), then load from `all_hadiths_unified.csv` + `all_rawis.csv`. Calls workstream C modules + workstream D's `resolveNarrators`. Honors `BATCH_SIZE` / `CONCURRENCY` env (defaults 500 / 4).
3. **`mode-test.ts`** — read-only. Runs every spec §9b assertion + every G-1..G-6 guardrail. Per-tradition coverage report. Exit non-zero on any fail unless `--allow-known-gaps` matches the documented allow-list (Shafi'i `isnad_optional`, classical-translation-coverage warn).
4. **`mode-diff.ts`** — compare each CSV row to existing DB on biz key; only `MERGE` if missing OR if a tracked field changed. Emit added/updated/unchanged/tombstoned summary.
5. **`mode-enrich.ts`** (FR-1.11) — generic, field-agnostic: takes `--field=<name> --source=<jsonl>`. Only writes where the target field is empty/missing. Stamps `<field>_source`, `<field>_enriched_at`, `<field>_extraction_method='enrich-jsonl'`. Idempotent. Per-row log entries: `added` / `skipped_already_filled` / `missing_in_db` / `missing_in_source` / `error`.
6. **Phase-0b 0.7 + 0.8** as part of `mode-fullregen` (the canonicalization + Source.tradition population happen on load — they're not separate scripts).

**Exit criteria:**
- `npm run db:regen -- --list` (add this) prints the four modes with descriptions.
- `npm run db:regen -- --mode=test` exits 0 (or 0 with documented `--allow-known-gaps`) on the post-fullregen DB.
- A second `npm run db:regen -- --mode=fullregen` immediately after a successful first run reports zero new writes (idempotent).
- `npm run db:regen -- --mode=enrich --field=text_english --source=<test file>` is idempotent and never overwrites populated values.

**Do NOT touch:** `lib/regen/{io,dataset-version,load-*,assessment,name-mention,tombstone,temporal-plausibility,entity-resolution}.ts` — those are workstream C/D. Import them; do not modify them.

---

### F — Tests

**Owns:** `src/scripts/__tests__/regen-*.test.ts` (extend the existing test file's pattern).
**Plan tasks:** **1.7, 1.11, 2.7**.
**Spec refs:** spec §5 (six guardrails, each a test) + §12 (acceptance gates).

**Tasks:**
1. Mode tests on a small fixture (~50 rows from each tradition):
   - `--mode=test` exercises every spec-§9b assertion.
   - `--mode=fullregen` on the fixture produces identical output to a fresh load.
   - `--mode=diff` correctly identifies added / updated / unchanged.
   - `--mode=enrich` is idempotent + never overwrites + stamps provenance.
2. Guardrail tests (each MUST have a matching test):
   - G-1: scalar reliability/grade on Narrator|Hadith → 0.
   - G-2: GIGO report exists; every edge has confidence + extraction_method.
   - G-3: disclaimer string present in run summary; no global authenticity scalar.
   - G-4: 100% edges have `source` provenance.
   - G-5: zero `:SAME_AS` without `reviewed_by`.
   - G-6: temporal-plausibility flags present, tombstoned not deleted.
3. Schema tests: every new constraint in workstream B is asserted present.
4. Tier-1 coverage test: ≥ the verified `chain_indx` percentages.
5. Multi-isnad test: a hadith with two distinct chains gets two `:Chain` nodes, not a merged one.
6. Tradition canonicalization test: after fullregen, zero `:Hadith` or `:Narrator` has `tradition` matching `"Shia Imami"` or `"Shia Zaydi"`.

**Exit criteria:**
- `npm run test:regen` exits 0.
- All six guardrail tests are present and pass on the live (post-fullregen) DB.

**Do NOT touch:** production code outside `__tests__/`. Surface bugs you find back to the owning workstream.

---

### G — Verifier (runs LAST, on a separate fan-in)

**Owns:** nothing (read-only).
**Plan tasks:** verifies every gate.
**Spec refs:** §12 acceptance gate summary.

**Tasks:**
1. After workstream A: confirm unified CSV record count matches expected and the classical-narrator gap file exists.
2. After workstream B: confirm `npm run db:init` succeeds and all expected constraints present.
3. After workstream C + D + E: confirm `npm run db:regen -- --mode=test` exits 0; `npm run db:audit` shows no critical regressions; `npm run test:regen` exits 0; double-run idempotency holds.
4. Confirm spec §12 gates: Phase 0 exit (re-affirm — already `[x]`), **Phase 0b exit**, **Gate G1**, **Phase 2 exit**.
5. Emit a single verification report to `conductor/tracks/neo4j_isnad_graph_regen_20260516/verification.md` with the per-gate pass/fail status and the cypher/test evidence for each.

**Do NOT touch:** any code. If something fails, file it back to the owning workstream.

---

## Stop-the-line gates (passoff orchestration)

The agents may run A and B concurrently from the start. C, D, E MUST wait until B's schema lands (their MERGEs depend on the constraints). E MUST wait until C and D land (it imports them). F can develop tests against the interfaces in parallel with C/D/E. G runs last.

```
[A: data prep]  ──┐
                  ├─→  C: core modules   ──┐
[B: schema]    ──┤                          ├─→  E: mode dispatcher  ──┐
                  │   D: entity resolution ──┘                          ├─→ G: verifier
                  └─→  F: tests (in parallel with C/D/E) ───────────────┘
```

At each arrow, the producer workstream marks its tasks `[x]` in `plan.md` with a one-line evidence note (test that passes / Cypher count / file path).

---

## Done criteria (whole track)

- Spec §12 gate **Phase 0b exit** is green.
- Spec §12 gate **Gate G1** is green.
- Spec §12 gate **Phase 2 exit** is green.
- `verification.md` exists with all gates `[x]`.
- `tracks.md` entry for this track has the box checked `[x]` (manual — operator does this, per workflow.md).
- Manual commit suggested:
  ```
  git add conductor/tracks/neo4j_isnad_graph_regen_20260516/ src/scripts/ src/lib/db/schema.ts datasets/hadith-data/regen_unified_csvs.py package.json
  git commit -m "feat(graph): Neo4j isnad/narrator graph regen pipeline (track neo4j_isnad_graph_regen_20260516)"
  ```
