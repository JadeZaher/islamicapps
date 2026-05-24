# SYSTEMS Persona — Pipeline Architecture End-to-End

**Research question:** A reproducible ETL pipeline that regenerates a 69,368-row
multi-tradition hadith CSV/JSON dataset into Neo4j as an isnad/narrator graph,
idempotently and with provenance.

**Lens:** Pipeline architecture, ingestion, idempotency, stable IDs, provenance,
sync-on-regen, validation harness.

---

## 0. Current State (codebase ground truth)

The repo already has a working but **ad-hoc** Neo4j layer. Concretely:

| Artifact | Path | Role |
|---|---|---|
| Master CSV (single source of truth) | `datasets/hadith-data/all_hadiths_unified.csv` (+`.gz`) | 23-col superset; **`id` reassigned every rebuild** |
| Derived views | `all_hadiths_clean.csv` (37,043 rows), `all_hadiths_shia.csv(.gz)` | column projections |
| Regen script | `datasets/hadith-data/regen_unified_csvs.py` | Sunni + Imami + Ibadi + Zaydi + Rida → master |
| Isnad sidecars | `datasets/hadith-data/sunni_isnad.jsonl`; `*-hadith/parsed_hadiths.json` `sanad`/`sanad_detail` | structured chains |
| Narrator authority list | `datasets/narrator-data/all_rawis.csv` (24,326 rows: `scholar_indx`, teachers/students) | controlled vocab |
| Provenance | `datasets/hadith-data/{zaydi,ibadi,rida}-hadith/PROVENANCE.json` | per-collection manifest (good prior art) |
| Neo4j driver | `src/lib/db/neo4j.ts` (`runWrite` = `executeWrite`, retry-safe) | |
| Idempotent helpers | `src/lib/db/neo4j-helpers.ts` (`mergeNodeByKey`, `mergeEdge`, `buildPipelineKey`) | **already encodes the right conventions** |
| Schema | `src/lib/db/schema.ts` (`Narrator.id`, `Narrator.scholar_indx`, `Hadith.id`, `Hadith.dataset_row_id` UNIQUE/idx) | |
| Chain linker | `src/scripts/link-sanad-chains.ts` | fuzzy name → Narrator, batched UNWIND + `MERGE` |
| Importers | `src/scripts/import-*.ts` (classical, shia, zaydi, musnad, pure-canon) | UNWIND + `MERGE (h:Hadith {id})` |

**Key structural problem already noted in the code itself**
(`regen_unified_csvs.py:77-84`): the master `id` is *reassigned every rebuild*,
so it **cannot** be the graph join key. The script invents a stable surrogate
`_sunni_key = "{source}|{hadith_no}"`. This is the central design tension this
research must resolve and generalize to **all** traditions and to narrators.

The existing `neo4j-helpers.ts` docstring already states the target conventions
(every node has a `:id` UUID constraint **and** a business-key MERGE anchor;
`ON CREATE SET` immutables + `created_at`; `ON MATCH SET` mutables +
`updated_at`; `_merge_sentinel` for created-flag). The recommendation below
**builds on this**, it does not replace it.

---

## 1. Neo4j Bulk Ingestion Options — Which, When, Throughput

| Method | Throughput @ ~70k hadith + ~25k narrators + edges | Idempotent? | Online? | Verdict for this project |
|---|---|---|---|---|
| `neo4j-admin database import full` | Fastest by far (parallel, bypasses tx log; billions/hr class) | **No** — empty DB only, blind `CREATE`, dedupe only via `--id-type` + `nodes` skip | No (DB stopped) | **Use for cold rebuild** (`graph.db` from scratch). At 70k it finishes in seconds. |
| `neo4j-admin database import incremental --stage=all` (Neo4j 2025.x) | Near-bulk speed | Adds/updates props, labels, nodes/rels into an **existing** DB; needs `--force`, DB stopped | No (`--stage=all` needs stop) | Optional for additive deltas; **awkward here** because regen reshuffles ids — only viable once IDs are stabilized (Section 3). |
| `LOAD CSV ... CALL (row) { MERGE ... } IN [n CONCURRENT] TRANSACTIONS OF k ROWS ON ERROR RETRY ... THEN CONTINUE` | Good (k=200–1000, 2–4 concurrent); 70k rows in minutes | **Yes** with `MERGE` on stable key | **Yes** (Aura/Railway-friendly) | **Recommended steady-state loader.** Self-contained Cypher, retry built in. |
| `apoc.periodic.iterate` | Comparable to CALL-in-tx | Yes with `MERGE` | Yes | Legacy. Neo4j now recommends replacing with `CALL {} IN CONCURRENT TRANSACTIONS` ([Neo4j blog](https://neo4j.com/blog/developer/concurrent-writes-cypher-subqueries/)). Only if stuck on old APOC. |
| Driver-side UNWIND + `MERGE` (current `import-*.ts`) | Good; this is what the repo does today | Yes | Yes | Keep as the **programmatic path** when transforms are too complex for pure Cypher (Arabic normalization, fuzzy narrator match). |
| Spark / Arrow connector | Massive scale only | Yes (via MERGE write mode) | Yes | **Overkill** at 70k. Skip. |

**Concrete recommendation: two loaders, one schema.**

1. **Cold path (CI / disaster recovery):** export normalized node/edge CSVs →
   `neo4j-admin database import full`. Sub-minute, deterministic, perfect for
   reproducible from-scratch rebuilds.
2. **Warm path (steady state, the source regenerates often):** `LOAD CSV` +
   `CALL (row){ MERGE } IN CONCURRENT TRANSACTIONS ... ON ERROR RETRY` for
   pure-data nodes, and the existing batched-UNWIND TS importers for rows
   needing Arabic normalization / fuzzy resolution.

Sources: [Neo4j Import Operations Manual](https://neo4j.com/docs/operations-manual/current/import/),
[CALL subqueries in transactions](https://neo4j.com/docs/cypher-manual/current/subqueries/subqueries-in-transactions/),
[Concurrent Writes to Cypher Subqueries](https://neo4j.com/blog/developer/concurrent-writes-cypher-subqueries/),
[apoc.periodic.iterate](https://neo4j.com/docs/apoc/current/overview/apoc.periodic/apoc.periodic.iterate/),
[Neo4j v5 LTS evolution](https://neo4j.com/blog/developer/neo4j-v5-lts-evolution/).

### 1a. neo4j-admin incremental — exact command

```bash
# DB must be STOPPED; --force required on an existing database
bin/neo4j-admin database import incremental --stage=all --force \
  --nodes=Hadith=import/hadith_header.csv,import/hadith.csv \
  --nodes=Narrator=import/narrator_header.csv,import/narrator.csv \
  --relationships=NARRATES=import/narrates_header.csv,import/narrates.csv \
  neo4j
```
For semi-online: `--stage=prepare` (stopped) → `--stage=build` (can run) →
`--stage=merge` (stopped). Source:
[Importing data tutorial](https://neo4j.com/docs/operations-manual/current/tutorial/neo4j-admin-import/).

---

## 2. Idempotent Upsert Patterns

Rule (already in `neo4j-helpers.ts`, generalize it): **every node MERGEs on a
stable business key, never on the regenerated `id`.** `MERGE` is the idempotent
primitive; `ON CREATE` sets immutables + `id` + `created_at`, `ON MATCH` sets
mutables + `updated_at`. ([MERGE manual](https://neo4j.com/docs/cypher-manual/current/clauses/merge/)).

### 2a. Constraints (run once, before any load)

```cypher
CREATE CONSTRAINT hadith_bizkey  IF NOT EXISTS FOR (h:Hadith)   REQUIRE h.biz_key  IS UNIQUE;
CREATE CONSTRAINT hadith_id      IF NOT EXISTS FOR (h:Hadith)   REQUIRE h.id       IS UNIQUE;
CREATE CONSTRAINT narrator_nkey  IF NOT EXISTS FOR (n:Narrator) REQUIRE n.narrator_key IS UNIQUE;
CREATE CONSTRAINT narrator_id    IF NOT EXISTS FOR (n:Narrator) REQUIRE n.id       IS UNIQUE;
CREATE CONSTRAINT source_name    IF NOT EXISTS FOR (s:Source)   REQUIRE s.name     IS UNIQUE;
```
Uniqueness constraints also create the backing index that makes `MERGE`
O(1) — without them MERGE does a full label scan and locks broadly.
**Gotcha:** never put two uniqueness constraints on the same MERGE pattern
(`MERGE (n {a,b})` fails if one matches and the other doesn't) — MERGE on a
*single* composite key string instead. ([Constraints manual](https://neo4j.com/docs/cypher-manual/current/constraints/)).

### 2b. Idempotent hadith upsert (steady-state loader)

```cypher
LOAD CSV WITH HEADERS FROM 'file:///all_hadiths_unified.csv' AS row
CALL (row) {
  MERGE (h:Hadith {biz_key: row.source + '|' + row.hadith_no})
  ON CREATE SET h.id = randomUUID(), h.created_at = datetime(),
                h.source = row.source, h.tradition = row.tradition
  ON MATCH  SET h.updated_at = datetime()
  SET h.text_ar = row.text_ar, h.text_en = row.text_en,
      h.sanad = row.sanad, h.sanad_confidence = toInteger(row.sanad_confidence),
      h.attributed_to = row.attributed_to,
      h.dataset_row_id = toInteger(row.id),      // regen-volatile, info only
      h.content_hash = row.content_hash          // for change detection (S.6)
} IN 4 CONCURRENT TRANSACTIONS OF 500 ROWS
  ON ERROR RETRY FOR 5 SECONDS THEN CONTINUE
  REPORT STATUS AS s;
```

### 2c. Idempotent isnad edge (carries no mutable props → MERGE only)

```cypher
UNWIND $rows AS r
MATCH (h:Hadith {biz_key: r.hadith_key})
MERGE (n:Narrator {narrator_key: r.narrator_key})
  ON CREATE SET n.id = randomUUID(), n.created_at = datetime(),
                n.name_arabic = r.name_ar, n.name_english = r.name_en,
                n.scholar_indx = r.scholar_indx
MERGE (h)-[rel:HAS_NARRATOR {position: r.pos}]->(n)   // position in key → ordered, dedup-safe
  ON CREATE SET rel.transmission_verb = r.verb;
```
For consecutive-narrator `HEARD_FROM`/`NARRATED_TO` edges, MERGE on the
ordered pair `(student_key, teacher_key)` (current `link-sanad-chains.ts`
already does this) — re-runs are no-ops.

**Critical idempotency gotcha:** MERGE on a relationship that includes a
property the loader recomputes (`position`) is only stable if the property is
**deterministically derived** from the data, not from row order in a reshuffled
CSV. Derive `position` from the parsed chain index, not the CSV line number.

---

## 3. Stable Narrator / Hadith IDs from Messy Extracted Names

The dataset regenerates often and `id` is reassigned each time — so **no
sequential surrogate may be a graph key**. Three candidate strategies:

| Strategy | Survives regen? | Survives name fix? | Use for |
|---|---|---|---|
| Raw hash of extracted name (`sha1(normalized_name)`) | Yes | **No** — any OCR/spelling fix changes the key, orphaning edges | ❌ avoid as primary |
| Sequential surrogate | No (reassigned) | n/a | ❌ never a key |
| **UUID5 over a controlled-vocab anchor** | **Yes** | **Yes** if anchor stable | ✅ recommended |

**Recommended: layered resolution → controlled-vocab key.**

1. **Anchor on `scholar_indx`** when the name resolves into
   `datasets/narrator-data/all_rawis.csv` (24,326 curated narrators with
   teachers/students). This is a **stable controlled-vocabulary key** that
   already survives dataset regen — it is editorial, not extracted.
   `narrator_key = "RAWI:" + scholar_indx`.
2. **Fallback for unresolved extracted names:** deterministic
   `narrator_key = "EXT:" + uuid5(NAMESPACE, normalized_arabic_name)`.
   UUID5 is deterministic: same input → same UUID across every regen
   ([UUID5 idempotency](https://shimul.dev/en/blog/uuid5_idempotency/)).
3. **Alias table to survive name corrections:** keep
   `datasets/narrator-data/narrator_aliases.csv` mapping
   `raw_extracted_name → narrator_key`. When an OCR fix changes a name, add
   an alias row instead of letting the hash drift — the graph key stays put
   (the entity-resolution "older cluster retains the ID" pattern,
   [Entity Resolution](https://faingezicht.com/articles/2024/09/03/entity-resolution/),
   [dbt surrogate keys](https://docs.getdbt.com/blog/managing-surrogate-keys)).
4. **Hadith key:** `biz_key = "{source}|{hadith_no}"` (generalize the existing
   `_sunni_key` to every tradition; for OpenITI use
   `"{source}|{kitab_no}.{bab_no}.{hadith_no}"` to guarantee uniqueness).

Net effect: re-running regen never duplicates a narrator/hadith, and a curated
name correction does **not** orphan the isnad subgraph.

---

## 4. Provenance & Schema Versioning

The repo already has the right instinct (`PROVENANCE.json` per collection).
Formalize and extend:

1. **Per-dataset sidecar manifest** (extend existing `PROVENANCE.json`):
   add `schema_version`, `git_commit`, `row_count`, `content_sha256` of the
   CSV, `generated_at`, upstream `source_uri`, and the `regen_unified_csvs.py`
   args used. Write one alongside `all_hadiths_unified.csv`.
2. **In-graph provenance node:** one `(:DatasetVersion {version, sha256,
   git_commit, generated_at, row_count})`; every Hadith
   `MERGE (h)-[:LOADED_FROM]->(dv)`. A single Cypher query then answers
   "which graph state corresponds to which CSV build" — essential because the
   source regenerates often.
3. **Schema version constant** in `src/lib/db/schema.ts`; bump on any
   label/constraint change; record in `DatasetVersion.schema_version` and the
   sidecar so a graph can be matched to the loader that built it.
4. **DVC for the data artifacts.** Track `all_hadiths_unified.csv` and the
   `*-hadith/parsed_hadiths.json` inputs with DVC; model
   extract→resolve→load as `dvc.yaml` stages. `dvc.lock` records md5 of
   deps/params; `dvc repro` re-runs only stages whose inputs changed and
   reuses the **run cache** otherwise — this is the reproducibility backbone
   ([DVC pipelines](https://doc.dvc.org/user-guide/pipelines),
   [dvc repro](https://doc.dvc.org/command-reference/repro),
   [dvc.yaml](https://doc.dvc.org/user-guide/project-structure/dvcyaml-files)).

```yaml
# dvc.yaml
stages:
  extract:
    cmd: python datasets/parse_openiti.py && python datasets/extract_isnad.py --all
    deps: [datasets/hadith-data/zaydi-hadith, datasets/parse_openiti.py, datasets/extract_isnad.py]
    outs: [datasets/hadith-data/zaydi-hadith/parsed_hadiths.json]
  regen:
    cmd: python datasets/hadith-data/regen_unified_csvs.py
    deps:
      - datasets/hadith-data/regen_unified_csvs.py
      - datasets/hadith-data/zaydi-hadith/parsed_hadiths.json
      - datasets/hadith-data/sunni_isnad.jsonl
    outs: [datasets/hadith-data/all_hadiths_unified.csv]
  normalize_for_graph:
    cmd: python datasets/build_graph_csvs.py   # → nodes/*.csv, edges/*.csv + manifest
    deps: [datasets/hadith-data/all_hadiths_unified.csv, datasets/narrator-data/all_rawis.csv]
    outs: [datasets/graph/]
  validate:
    cmd: python datasets/validate_graph_csvs.py datasets/graph/
    deps: [datasets/graph/]
  load:
    cmd: tsx src/scripts/load-graph.ts --dir datasets/graph
    deps: [datasets/graph/]
```

5. **Orchestration (Prefect vs Dagster).** For this size and the
   "CSV regenerates often, only reload what changed" requirement, **Dagster's
   software-defined assets** are the better fit: declare
   `unified_csv → graph_node_csvs → neo4j_graph` as assets; Dagster skips
   re-materializing downstream assets when upstream is unchanged and supports
   partition backfills ([Dagster vs Prefect](https://dagster.io/vs/dagster-vs-prefect),
   [ZenML showdown](https://www.zenml.io/blog/orchestration-showdown-dagster-vs-prefect-vs-airflow)).
   **However**, given DVC already gives content-hash caching and the repo is
   Python+TS scripts, the **pragmatic recommendation is DVC as the engine +
   a thin Prefect flow** only if scheduling/observability is later needed
   (Prefect's task-first model wraps the existing scripts with zero
   restructuring). Don't adopt Dagster's asset-everything model unless the
   pipeline graph grows substantially.

---

## 5. Keeping the Graph in Sync When the Upstream CSV Rebuilds

Because `regen_unified_csvs.py` reshuffles `id` and the source regenerates
often, a naive reload would orphan/duplicate. Sync strategy:

1. **Content hash per hadith** added in the regen step:
   `content_hash = sha256(text_ar + sanad + tradition)` written as a CSV
   column. The loader skips MERGE-set when `h.content_hash` is unchanged
   (cheap idempotent no-op; only changed rows touch the graph).
2. **Diff-driven delta:** compare new `all_hadiths_unified.csv` against the
   last loaded `DatasetVersion` (or the previous DVC-tracked CSV) on
   `biz_key`. Produce three sets: **added** (MERGE create), **changed**
   (`content_hash` differs → MERGE update + re-link isnad), **removed**
   (`biz_key` absent from new build).
3. **Tombstone, never hard-delete** removed hadiths
   (`SET h.retired_at = datetime()`), per the project memory directive
   *"Never delete data files; only purge from DB when explicitly asked."*
   Removal of an upstream row should not silently destroy graph history.
4. **Re-link isnad only for changed rows**: `DETACH` old
   `HAS_NARRATOR`/chain edges for those `biz_key`s, then re-run the chain
   linker on just that subset. Narrator nodes persist (stable
   `narrator_key`), so only edges churn.
5. **Stale-narrator GC** (optional, gated): a Narrator with zero inbound
   isnad edges and no `scholar_indx` after a full reload is a candidate for
   review — report it, don't auto-delete.

---

## 6. Test / Validation Harness (gate before promotion)

Run on the generated `datasets/graph/` CSVs **before** any load, and again on
the loaded graph, fail the DVC `validate` stage on any breach:

**Pre-load (on CSVs):**
- Row count == manifest `row_count` (expected ≈ 69,368; clean view 37,043).
- Every `biz_key` non-empty and unique (no `"|"` / empty `hadith_no`).
- Every isnad edge references a `narrator_key` present in the node CSV
  (no dangling edges) and a `hadith biz_key` present.
- `scholar_indx` references exist in `all_rawis.csv`.
- UTF-8 / no BOM / CSV field-size sanity (the regen script already raises
  `csv.field_size_limit`).

**Post-load (Cypher assertions):**
```cypher
// 1. No duplicate business keys (constraint should prevent; assert anyway)
MATCH (h:Hadith) WITH h.biz_key AS k, count(*) AS c WHERE c > 1 RETURN k, c;
// 2. No dangling isnad: every HAS_NARRATOR endpoint exists (relationship integrity)
MATCH (h:Hadith)-[r:HAS_NARRATOR]->(n:Narrator)
WHERE n.narrator_key IS NULL RETURN count(r);
// 3. Hadith count matches manifest
MATCH (h:Hadith) RETURN count(h) AS loaded;   // == DatasetVersion.row_count
// 4. Orphan narrators with no scholar_indx and no edges (report)
MATCH (n:Narrator) WHERE n.scholar_indx IS NULL AND NOT (n)<-[:HAS_NARRATOR]-()
RETURN count(n) AS orphan_narrators;
// 5. Constraint presence
SHOW CONSTRAINTS YIELD name WHERE name IN
  ['hadith_bizkey','narrator_nkey'] RETURN collect(name);
```
Promote (point the app at the DB / swap the Aura instance) only when all
post-load assertions pass and counts match the sidecar manifest. Wire these
into a `verify-graph.ts` (the repo already has `src/scripts/verify-db.ts` and
`data-readiness-audit.ts` to extend).

---

## 7. Recommended Staged DAG (end-to-end)

```
                ┌── upstream sources (OpenITI mARkdown, Thaqalayn JSON, Sunni CSV) ──┐
                v                                                                    │
[extract]  parse_openiti.py + extract_isnad.py  ── parsed_hadiths.json (+PROVENANCE) │
                v                                                                    │
[regen]    regen_unified_csvs.py  ── all_hadiths_unified.csv  + content_hash col     │
                v                                            + sidecar manifest      │
[resolve]  build_graph_csvs.py                                                       │
              • narrator_key = RAWI:scholar_indx | EXT:uuid5(norm_name)              │
              • alias table merge (narrator_aliases.csv)                             │
              • emit nodes/{hadith,narrator,source}.csv, edges/{has_narrator,        │
                heard_from,from_source}.csv  (admin-import header format)            │
                v                                                                    │
[diff]     compare biz_key + content_hash vs last DatasetVersion ──► added/changed/  │
                v                                                       removed sets │
[validate] validate_graph_csvs.py  (counts, uniqueness, dangling, FK)  ── GATE ──────┘
                v                              (fail → stop, no DB writes)
[load]     cold:  neo4j-admin database import full        (CI / from-scratch)
           warm:  LOAD CSV + CALL IN CONCURRENT TRANSACTIONS / batched-UNWIND TS
                  (MERGE on biz_key / narrator_key; tombstone removed)
                v
[verify]   verify-graph.ts  (post-load Cypher assertions vs manifest)  ── GATE
                v
[promote]  write (:DatasetVersion) node + LOADED_FROM edges; point app at DB
```

All stages are DVC `dvc.yaml` stages → `dvc repro` runs only what changed,
`dvc.lock` + the in-graph `DatasetVersion` give end-to-end provenance, and
every load is idempotent because keys are stable and writes are `MERGE`.

### Minimal concrete to-do for this repo
1. Add `content_hash` + generalize `biz_key` (all traditions) in
   `regen_unified_csvs.py`.
2. New `datasets/build_graph_csvs.py` — emit admin-import-format node/edge CSVs
   + `narrator_key` resolution + alias table + JSON sidecar manifest.
3. New `datasets/validate_graph_csvs.py` + extend `src/scripts/verify-db.ts`.
4. Refactor `import-*.ts` to share one `load-graph.ts` that MERGEs on
   `biz_key`/`narrator_key` (helpers in `neo4j-helpers.ts` already do this).
5. `dvc.yaml` (above) + bump `SCHEMA_VERSION` constant.

---

## Sources
- [Neo4j Import — Operations Manual](https://neo4j.com/docs/operations-manual/current/import/)
- [Importing data — neo4j-admin tutorial](https://neo4j.com/docs/operations-manual/current/tutorial/neo4j-admin-import/)
- [CALL subqueries in transactions — Cypher Manual](https://neo4j.com/docs/cypher-manual/current/subqueries/subqueries-in-transactions/)
- [Introducing Concurrent Writes to Cypher Subqueries — Neo4j blog](https://neo4j.com/blog/developer/concurrent-writes-cypher-subqueries/)
- [apoc.periodic.iterate — APOC docs](https://neo4j.com/docs/apoc/current/overview/apoc.periodic/apoc.periodic.iterate/)
- [MERGE — Cypher Manual](https://neo4j.com/docs/cypher-manual/current/clauses/merge/)
- [Constraints — Cypher Manual](https://neo4j.com/docs/cypher-manual/current/constraints/)
- [Neo4j v5 LTS and continued evolution](https://neo4j.com/blog/developer/neo4j-v5-lts-evolution/)
- [Achieving Idempotency for Entity ID using UUID5](https://shimul.dev/en/blog/uuid5_idempotency/)
- [Roughly Everything About Entity Resolution](https://faingezicht.com/articles/2024/09/03/entity-resolution/)
- [Surrogate Keys in dbt: Integers or hashes? — dbt blog](https://docs.getdbt.com/blog/managing-surrogate-keys)
- [DVC Pipelines](https://doc.dvc.org/user-guide/pipelines) · [dvc repro](https://doc.dvc.org/command-reference/repro) · [dvc.yaml](https://doc.dvc.org/user-guide/project-structure/dvcyaml-files)
- [Dagster vs Prefect](https://dagster.io/vs/dagster-vs-prefect) · [Orchestration Showdown — ZenML](https://www.zenml.io/blog/orchestration-showdown-dagster-vs-prefect-vs-airflow)
