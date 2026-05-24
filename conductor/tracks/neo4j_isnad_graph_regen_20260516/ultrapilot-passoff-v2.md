# Ultrapilot Passoff — Perfect Regeneration (v2)

**Track:** `neo4j_isnad_graph_regen_20260516` (continuation; clean-slate restart)
**Supersedes:** `ultrapilot-passoff.md` (v1 — partial run, 19 issues surfaced in post-mortem)
**Authoritative spec:** [`spec.md`](./spec.md) (binding)
**Plan:** [`plan.md`](./plan.md)
**Prior verification:** [`verification.md`](./verification.md)

> **Goal.** Single clean-slate run that produces the complete isnad/narrator/grade
> graph from the already-validated `all_hadiths_unified.csv` (99,283 rows) and
> `all_rawis.csv` (24,326 narrators), with all 19 v1 post-mortem issues
> resolved. No partial states, no in-place fixes mid-run, no hangs.

---

## How to launch

```
/ultrapilot @conductor/tracks/neo4j_isnad_graph_regen_20260516/ultrapilot-passoff-v2.md
```

Or paste this into Claude:

> Execute the Neo4j perfect-regen pass per `ultrapilot-passoff-v2.md`. Run the
> pre-flight checks first; **stop and report** if any pre-flight item fails.
> Drain the live DB, then run the v2 fullregen. Verify with `mode=test` post-run.

---

## Why v2 exists (1-paragraph post-mortem of v1)

The v1 run (2026-05-20/21) successfully exercised the full pipeline scaffold but
produced a graph with only `:Hadith`, `:Chain`, and `:Assessment` (all
`no_extant_evaluation`) nodes — **zero `:Narrator`, zero `:INCLUDES`, zero
`:NARRATED_FROM`, zero `:FROM_TRADITION`**. Root causes: (1) `io.ts` mapped wrong
CSV column names, so `dataset_row_id`, `text_en`, `grade_value`,
`grade_tradition`, `gradings_full` and ~10 other fields were silently dropped;
(2) the pipeline loaded 24,326 rawis into a Map for in-memory ER but never
persisted them as `:Narrator` nodes — `load-chain.ts:159` does `MATCH (n:Narrator
...)` not `MERGE`, so every `INCLUDES` edge silently no-ops; (3) `if (row.grade)`
read a column that didn't exist, so 100% of rows fell through to
`no_extant_evaluation × 4 traditions`; (4) `gradings_full` (15% of rows, the
rich multi-scholar verdict field) was never read; (5) no `FROM_TRADITION` edge
created on new hadiths. Plus operational issues: connection silently hung after
~3,371 rows (no per-tx timeout), `.env` was UTF-16 LE so `dotenv` couldn't read
it, and `init-db.ts` skips schema initialization entirely (legacy comment).

V2 fixes all 19 issues with three disjoint-file edits (already partially on disk
as of 2026-05-21: H1 ✓, H2 ✓, H3 was mid-edit when stopped and must be
completed). See § "v2 changeset checklist" below for the exact state on disk and
what remains.

---

## Pre-flight (operator runs BEFORE invoking ultrapilot)

Every item is a hard gate. Stop and fix if any fails.

### P1 — `.env` is UTF-8

Windows default is UTF-16 LE; `dotenv` silently ignores it.

```powershell
# Check
file .env  # should say "ASCII text" or "UTF-8 Unicode text", NOT "Little-endian UTF-16"
# OR
(Get-Content .env -TotalCount 1).Substring(0, [Math]::Min(20, (Get-Content .env -TotalCount 1).Length))
# Re-encode if needed
$c = Get-Content .env; $c | Out-File .env -Encoding utf8
```

### P2 — `.env` has all required keys

```
NEO4J_URL=...
NEO4J_USERNAME=...
NEO4J_PASSWORD=...
```

### P3 — Source CSVs present and correctly sized

```bash
python -c "
import csv; csv.field_size_limit(50_000_000)
with open('datasets/hadith-data/all_hadiths_unified.csv', encoding='utf-8') as f:
    n = sum(1 for _ in csv.DictReader(f))
print('hadiths:', n)  # MUST be 99,283 ± 50
with open('datasets/narrator-data/all_rawis.csv', encoding='utf-8') as f:
    n = sum(1 for _ in csv.DictReader(f))
print('rawis:', n)  # MUST be 24,326 ± 10
"
```

### P4 — Required `package.json` scripts present

```
"db:init":      "tsx src/scripts/init-db.ts"
"db:drain":     "tsx src/scripts/drain-db.ts"
"db:regen":     "tsx src/scripts/regen-isnad-graph.ts"
"db:ingest-er": "tsx src/scripts/ingest-er-approved.ts"
"test:regen":   "tsx src/scripts/__tests__/regen-isnad-graph.test.ts"
```

If `db:drain` or `db:regen` are missing (they were reverted at one point in v1
session): re-add them. The scripts they reference already exist.

### P5 — `src/lib/db/neo4j.ts` has 30s per-tx timeout

The v1 run hung silently after row 3,371 because a Bolt connection silently
dropped and no timeout fired. Confirm `runWrite` passes `{ timeout: 30_000 }` to
`session.executeWrite`. If missing, add:

```ts
const WRITE_TX_TIMEOUT_MS = 30_000;

export async function runWrite<T = any>(query: string, params = {}): Promise<T[]> {
    const driver = getDriver();
    const session = driver.session();
    try {
        const result = await session.executeWrite(
            (tx) => tx.run(query, params),
            { timeout: WRITE_TX_TIMEOUT_MS },
        );
        return result.records.map(...);
    } finally { await session.close(); }
}
```

### P6 — `tsc --noEmit` clean on regen files

```bash
npx tsc --noEmit 2>&1 | grep -E "src/scripts/(lib/regen|regen-isnad-graph|ingest-er)" | grep -v "archive"
```

Should be empty. Pre-existing errors in `src/scripts/archive/*` are out of scope.

### P7 — `tsx` and `dotenv` resolve

```bash
npx tsx --version  # should print a version, not "command not found"
node -e "require('dotenv')"  # should not throw
```

---

## v2 changeset checklist (state on disk as of 2026-05-21)

### ✓ Already complete (do NOT re-edit)

- [x] **H1**: `src/scripts/lib/regen/io.ts` — rewrote `UnifiedRow` to match
      actual CSV columns. Added: `dataset_row_id` (from CSV `id`), `hadith_id`,
      `volume`, `category`, `text_en` (was `text_english`), `matn_ar`, `matn_en`,
      `sanad_confidence`, `school`, `chain_type`, `attributed_to`,
      `narration_level`, `grade_value` (was `grade`), `grade_tradition`,
      `gradings_full`, `url`, `page_ref`. Removed: `title`, `primary_topic`,
      `text_english`, `grade`. `parseIndices` now handles both `"1,2,3"` and
      `"[1,2,3]"` shapes. All string fields `.trim()`'d.
- [x] **H1**: `src/scripts/lib/regen/load-hadith.ts` — expanded `mutableProps`
      to write every new UnifiedRow field on the `:Hadith` node. Unknown-source
      warning dedup via module-level `Set<string>`.
- [x] **H2**: NEW `src/scripts/lib/regen/load-narrators.ts` — exports
      `bulkLoadNarrators(rawis: Map<number, RawiRecord>, dvId: string): Promise<{ created; matched; errors }>`.
      Batches of 200. Properties: scholar_indx (MERGE key), id, name,
      name_english, name_arabic, bio, death_date_hijri, death_date_gregorian,
      geographic_region, tabaqah, source (=dvId), `_raw_grade` (G-1
      breadcrumb — NOT a verdict scalar). Never writes `grade` or `reliability`
      on the Narrator (G-1).
- [x] **H2**: `src/scripts/lib/regen/assessment.ts` — added `parseGradingsFull`,
      `loadGradingsFull`, `GradingEntry`. Pipe-separated parser with
      depth-tracking right-to-left paren scan for nested `(1/25)` citations.

### ⚠️ Mid-edit when stopped (MUST COMPLETE before running)

H3 was killed mid-edit. The file `src/scripts/lib/regen/mode-fullregen.ts` was
partially modified (header doc updated, imports added for `bulkLoadNarrators`
and `loadGradingsFull`, FR-1.8 migration block in place, NARRATED_FROM
direction comment added) — but the body work was incomplete. Verify and complete
the items below:

- [ ] **H3-A**: After `readAllRawis()`, before the streaming loop, call
  ```ts
  console.log('[fullregen] Bulk-merging :Narrator nodes from rawis...');
  const narratorResult = await bulkLoadNarrators(rawis, dvId);
  console.log(`[fullregen] Narrators: created=${narratorResult.created} matched=${narratorResult.matched} errors=${narratorResult.errors}`);
  ```
- [ ] **H3-B**: After `await loadHadith(row, ctx)` in the row loop, write the
  `Hadith -[:FROM_TRADITION]-> :ReligiousTradition` edge:
  ```ts
  await runWrite(
      `MATCH (h:Hadith { ${keyProp}: $hadithKey })
       MERGE (rt:ReligiousTradition { name: $tradition })
         ON CREATE SET rt.id = randomUUID(), rt.created_at = datetime()
       MERGE (h)-[r:FROM_TRADITION]->(rt)
         ON CREATE SET r.source = $dvId, r.confidence = 1.0,
                       r.extraction_method = 'unified_csv'`,
      { hadithKey: keyVal, tradition: rowTradition, dvId: ctx.dvId },
  );
  ```
- [ ] **H3-C**: Replace the legacy `if (row.grade) { ... } else { ... }` block
  with the gradings-aware dispatch:
  ```ts
  const traditionsWithAssessment = new Set<Tradition>();

  // (a) gradings_full fan-out
  if (row.gradings_full && row.gradings_full.trim()) {
      const { written } = await loadGradingsFull({
          targetLabel: 'Hadith',
          targetKeyProp: keyProp,
          targetKeyValue: keyVal,
          sourceTradition: rowTradition,
          gradingsFull: row.gradings_full,
      });
      assessmentLoaded += written;
      traditionsWithAssessment.add(rowTradition);
  }

  // (b) scalar grade_value (only if its tradition not already covered)
  const primaryTradition = row.grade_tradition
      ? canonicalizeTradition(row.grade_tradition)
      : rowTradition;
  if (row.grade_value?.trim() && !traditionsWithAssessment.has(primaryTradition)) {
      await loadAssessment({
          targetLabel: 'Hadith', targetKeyProp: keyProp, targetKeyValue: keyVal,
          tradition: primaryTradition, grade: row.grade_value,
          gradeSource: row.grade_source || 'hadith_csv',
          gradeScheme: schemeForTradition(primaryTradition),
      });
      assessmentLoaded++;
      traditionsWithAssessment.add(primaryTradition);
  }

  // (c) no_extant_evaluation for uncovered traditions
  for (const trad of ALL_TRADITIONS) {
      if (!traditionsWithAssessment.has(trad)) {
          await loadNoExtantEvaluation('Hadith', keyProp, keyVal, trad);
          noExtantLoaded++;
      }
  }
  ```
- [ ] **H3-D**: Pre-scan must compute `measuredUnknownFraction` and pass it to
  `mergeDatasetVersion({ ..., measuredUnknownFraction })`. Definition: rows
  where `grade_value` AND `grade_tradition` AND `gradings_full` are all empty.
- [ ] **H3-E**: At end of run, print the G-3 disclaimer:
  ```
  [fullregen] ⚠️  DISCLAIMER (spec §5 G-3): Per-narrator and per-hadith
  reliability scores in this dataset reflect "kathrat al-riwāya" (frequency of
  transmission) — NOT classical ʿadāla/ḍabṭ (justice/precision) verdicts. They
  are NOT authoritative authenticity rulings.
  ```
- [ ] **H3-F**: Print per-source counts at end:
  ```
  [fullregen] Per-source counts:
    Sahih Bukhari: 7370
    Sahih Muslim: 7596
    ...
  ```
- [ ] **H3-G**: Print GIGO report at end (relationship counts + confidence
  stats per edge type — query against the live DB after the load):
  ```cypher
  MATCH ()-[r]->() WHERE r.confidence IS NOT NULL
  RETURN type(r) AS rel_type, count(r) AS count,
         min(r.confidence) AS min_conf, max(r.confidence) AS max_conf,
         avg(r.confidence) AS avg_conf
  ```
- [ ] **H3-H**: At startup (during/after pre-scan), warn for any CSV source name
  NOT in `CANONICAL_SOURCES.*.canonical`:
  ```
  [fullregen] ⚠️  Unregistered source(s) in unified CSV (will default to Sunni): ...
  ```

### ⚠️ Verification-only (read-only, file in deliverable)

- [ ] **V1**: Multi-isnad check — confirm the unified CSV pre-splits multi-isnad
  rows. Run:
  ```bash
  python -c "
  import csv; csv.field_size_limit(50_000_000)
  seen = {}
  with open('datasets/hadith-data/all_hadiths_unified.csv', encoding='utf-8') as f:
      for r in csv.DictReader(f):
          k = (r['source'].strip(), r['hadith_no'].strip())
          seen[k] = seen.get(k, 0) + 1
  multi = {k:v for k,v in seen.items() if v > 1}
  print('multi-isnad pre-split count:', len(multi))
  "
  ```
  Expected: > 0 → multi-isnad IS pre-split, current 1-chain-per-row in
  `buildTier1Resolution` is correct. = 0 → multi-isnad is encoded in a single
  row and Tier-1 needs to split; file as a follow-up.

- [ ] **V2**: Quarantine flag — confirm `src/scripts/lib/regen/entity-resolution.ts`
  sets `quarantined=true` on edges from Ibadi/Zaydi/Imami-gap rows (NFR-3).
  Read-only check; do not fix here.

---

## Clean-slate execution sequence

Run in this order. Each step is atomic; the next assumes the previous succeeded.

1. **Drain the live DB**
   ```
   npm run db:drain
   ```
   Batches of 1,000 (chosen to fit Neo4j's default 716 MiB tx memory limit).
   On 306k nodes, ~5 min. If 1 node remains at end ("FAIL — 1 nodes still
   present"), it's a system meta-node — drain a second time or ignore (the
   fullregen's MERGE-based loaders will work over it).

2. **Verify empty**
   ```bash
   npx tsx peek-db.ts  # (or any small script that runs `MATCH (n) RETURN count(n)`)
   ```
   Should report 0 nodes. (Schema constraints persist across drain — that's
   expected and good.)

3. **Run fullregen**
   ```
   ts=$(date -u +%Y%m%dT%H%M%SZ)
   npm run db:regen -- --mode=fullregen > logs/regen-fullregen-stdout-${ts}.log 2>&1 &
   ```
   `mode-fullregen` calls `initializeSchema()` internally — no separate
   `db:init` needed. Expect ~10-15 hours on the full 99,283 rows over Railway
   Bolt. (v1 was running at ~200 rows/min; v2 has more writes per row — Narrator
   bulk-merge upfront + FROM_TRADITION + grade fan-out for ~30k rows — but
   should land in the same ballpark.)

4. **Monitor**
   Tail the log via `tail -F logs/regen-fullregen-stdout-${ts}.log` or arm a
   Monitor filter on `[fullregen] (Progress|Done|complete|errors=|⚠️|Error)`.
   Progress logs every 200 rows.

5. **Post-run verification**
   ```
   npm run db:regen -- --mode=test
   ```
   This is the read-only assertion run. Expect exit 0 (or exit 0 with
   `--allow-known-gaps shafi_i_isnad_optional,nahj_balagha_non_isnad`).

---

## Acceptance criteria

### Node counts (Cypher `MATCH (n:Label) RETURN count(n)`)

| Label | Expected | Tolerance |
|---|---|---|
| `:Hadith` | 99,283 | ±50 |
| `:Narrator` | 24,326 | ±10 |
| `:Chain` | ≥ 99,283 | + multi-isnad if pre-split |
| `:Assessment` | ≥ 44,817 | (29,915 scalar + ~14,902 gradings_full × ≥1 each) + no_extant |
| `:NameMention` | > 5,000 | most from Ibadi/Zaydi sanad + Imami gap |
| `:DatasetVersion` | 1 active | + N tombstoned from prior runs |
| `:ReligiousTradition` | 4 | Sunni, Imami, Zaydi, Ibadi |
| `:Source` | 32 | matches distinct sources in unified CSV |

### Relationship counts

| Type | Expected | Notes |
|---|---|---|
| `HAS_CHAIN` | ≥ 99,283 | one per hadith chain |
| `INCLUDES` (Chain→Narrator) | hundreds of thousands | only resolved narrators |
| `INCLUDES_MENTION` (Chain→NameMention) | thousands | only unresolved |
| `NARRATED_FROM` | tens of thousands | shortcut edges between consecutive resolved narrators |
| `FROM_TRADITION` | 99,283 | one per hadith |
| `INGESTED_IN` | 99,283 | provenance |
| `FROM_SOURCE` | 99,283 | hadith → source |
| `HAS_ASSESSMENT` | ≥ assessment count | |
| `UNDER_SCHEME` | ≥ assessment count | |

### Guardrails (Cypher one-liners; each MUST return 0 — or as noted)

```cypher
-- G-1: no scalar grade/reliability on identity nodes
MATCH (n) WHERE (n:Narrator OR n:Hadith) AND
  (n.reliability IS NOT NULL OR n.grade IS NOT NULL) RETURN count(n);
-- Expected: 0

-- G-2: every NARRATED_FROM has confidence + extraction_method
MATCH ()-[r:NARRATED_FROM]->() WHERE r.confidence IS NULL OR r.extraction_method IS NULL RETURN count(r);
-- Expected: 0

-- G-3: disclaimer string emitted (check stdout log for the disclaimer line)
-- Expected: 1 line matching "DISCLAIMER (spec §5 G-3)"

-- G-4: every edge has source provenance
MATCH ()-[r:INCLUDES|NARRATED_FROM|INCLUDES_MENTION|HAS_CHAIN|FROM_TRADITION]->()
WHERE r.source IS NULL RETURN type(r), count(r);
-- Expected: empty

-- G-5: zero :SAME_AS without reviewed_by
MATCH ()-[r:SAME_AS]->() WHERE r.reviewed_by IS NULL RETURN count(r);
-- Expected: 0

-- G-6: temporal_plausibility flagged where applicable
MATCH ()-[r:NARRATED_FROM]->() WHERE r.temporal_plausibility IS NULL RETURN count(r);
-- Expected: 0 (every NARRATED_FROM should be flagged 'impossible' | 'unknown' | 'plausible')
```

### Tradition canonicalization (must be 0)

```cypher
MATCH (n) WHERE (n:Hadith OR n:Narrator) AND n.tradition IN ['Shia Imami', 'Shia Zaydi']
RETURN count(n);
```

### Per-tradition row counts (matches CSV)

```cypher
MATCH (h:Hadith) RETURN h.tradition AS t, count(h) AS n ORDER BY n DESC;
-- Expected: Sunni 64356, Imami 33225, Ibadi 1004, Zaydi 698
```

### DatasetVersion provenance

```cypher
MATCH (dv:DatasetVersion {active: true})
RETURN dv.id, dv.expected_record_count, dv.measured_unknown_fraction,
       dv.content_hash, dv.created_at;
-- expected_record_count = 99283, measured_unknown_fraction ≈ 0.70 (70% of rows have no grade)
```

---

## Failure modes observed in v1 (avoid these — pre-flight covers them)

| Failure | Symptom | Root cause | v2 fix |
|---|---|---|---|
| `dotenv` silently ignores `.env` | "Missing required environment variables" despite valid `.env` | Windows UTF-16 LE encoding | Pre-flight P1 |
| Drain transaction OOM | `dbms.memory.transaction.total.max threshold reached` | 10k-row DETACH DELETE | `drain-db.ts` uses 1k batches |
| Drain LIMIT type error | `Invalid input. '10000.0' is not a valid value. Must be a non-negative integer.` | JS number serialized as float over Bolt | `drain-db.ts` uses literal integer in Cypher, not parameter |
| Silent hang at row N | Process alive at low CPU, log frozen for hours | Bolt connection silently dropped, no per-tx timeout | Pre-flight P5 — `runWrite` adds 30s timeout |
| 0 `:Narrator` nodes | `INCLUDES` MATCH no-ops silently | rawis loaded into Map but never persisted | H2 `load-narrators.ts` + H3-A wiring |
| All `no_extant_evaluation` | `assessments=0` in progress | `if (row.grade)` reads non-existent column | H3-C grade fan-out |
| `dataset_row_id` NULL on every node | new schema constraint does nothing | `mapUnifiedRow` looks for wrong column | H1 io.ts rewrite |
| `init-db.ts` skips schema | "⏭️ Skipping schema constraints" | legacy comment + early return | `mode-fullregen` calls `initializeSchema()` directly (line 214); don't use `db:init` |

---

## Out of scope (handed off to other tracks)

| Need | Track |
|---|---|
| K6 al-Albani grades (34k rows with 0% grading) | [data_acquisition_20260521](../data_acquisition_20260521/) — to be created |
| Sunni-classical English translation (29,915 rows) | [translate_classical_collections_20260418](../translate_classical_collections_20260418/) |
| Narrator biographical enrichment (16k missing Arabic names) | [narrator_enrichment_20260425](../narrator_enrichment_20260425/) |
| Grade canonical normalization | [grade_normalization_20260425](../grade_normalization_20260425/) |
| Vector embeddings | [vector_embedding_pipeline_20260425](../vector_embedding_pipeline_20260425/) |
| GDS analytics (Louvain, link prediction) | [gds_setup_analytics_20260425](../gds_setup_analytics_20260425/) |
| New collection acquisition (Bayhaqi, Bihar, Wasa'il, Tahdhib, Istibsar, Ibn Hibban, Tabarani) | [data_acquisition_20260521](../data_acquisition_20260521/) — to be created |

---

## Done criteria (whole pass)

- [ ] Pre-flight P1–P7 all green.
- [ ] `db:drain` completes (≤1 system node remaining is OK).
- [ ] `npm run db:regen -- --mode=fullregen` exits 0.
- [ ] All node-count / relationship-count / guardrail assertions above pass.
- [ ] `npm run db:regen -- --mode=test` exits 0 (or 0 with documented `--allow-known-gaps`).
- [ ] `verification.md` updated with the post-v2 pass.
- [ ] Manual commit:
  ```
  git add conductor/tracks/neo4j_isnad_graph_regen_20260516/ src/scripts/ src/lib/db/ package.json
  git commit -m "feat(graph): perfect-regen v2 (track neo4j_isnad_graph_regen_20260516)"
  ```
