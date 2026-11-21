# 09 - Scripts / Neo4j-coupled files: fate after Postgres cutover
Date: 2026-11-21. Intent: classify every script + Neo4j-coupled file (DELETE NOW / DELETE AT CUTOVER / PORT / KEEP), evidence, stale docs, Dockerfile/Railway findings, deploy config recommendation. Read-only; Railway metadata read via MCP (no Neo4j connection).

Policy note: memory `feedback_no_delete_backup` + `src/scripts/archive/README.md` ("archive, never delete") -> treat "DELETE" as `git mv` into `src/scripts/archive/` (excluded from tsc + eslint) unless owner says hard delete. Code is git-tracked so hard delete is recoverable via checkpoint af2f90b.

## 0. Key structural facts
- Live Neo4j app coupling is only 4 non-script files: `src/app/actions/graph-actions.ts`, `src/app/actions/comparative-actions.ts`, `src/app/api/comparative/research/route.ts`, `src/lib/comparative/neo4j-commit.ts`, plus `src/lib/pagination.ts:5,27` (imports `neo4j.int` for SKIP/LIMIT). All import `@/lib/db/neo4j` (runQuery/runWrite/runTransaction). `src/lib/db/neo4j.ts:52-56` reads NEO4J_URL/USERNAME/PASSWORD.
- NO script is imported by the Next app. Scripts only matter to operators. tsconfig `include: **/*.ts` with excludes only `src/scripts/archive`, `src/scripts/__tests__`, `datasets` => EVERY `src/scripts/*.ts` and `src/scripts/lib/**` is type-checked by `next build`. Neo4j-coupled scripts can break the Docker build (candidate cause of "Failed to build an image"; unconfirmed, diagnosis returned null).
- `package.json` script `db:ingest-parallels` -> `src/scripts/ingest-approved-parallels.ts` DOES NOT EXIST (dangling). `test:regen` runs only `regen-isnad-graph.test.ts`. package.json has no drizzle, no pg, no prisma; has `neo4j-driver ^6.0.1`, `openai ^6.32.0`, `tsx` devDep. No test runner (tests are tsx-executed scripts).
- conductor/tech-stack.md says Prisma ^7.1.0 "available" - not in package.json (git log: "more docker updates remove prisma"). Stale.
- Python already owns the canonical build: `datasets/hadith-data/neo4j_export/{contract.py,export_bundle.py,validate_bundle.py}` (bulk-import bundle CSVs incl. tradition, grade_tradition, birth/death_date_hijri at contract.py:46-48, `tradition_id()` contract.py:431). Bundle CSVs are a near-ready source for Postgres COPY; the TS regen loader is NOT needed to load Postgres.

## 1. src/lib/db/* and src/lib/import/*
| File | Lines | Class | Evidence / note |
|---|---|---|---|
| src/lib/db/neo4j.ts | 145 | DELETE AT CUTOVER | driver singleton; callers = 4 app files + all scripts. Replace by `src/db/client.ts` (Drizzle). |
| src/lib/db/neo4j-helpers.ts | 200 | DELETE AT CUTOVER | `mergeNodeByKey`, `mergeEdge`, `buildPipelineKey`; callers: regen load-*.ts, batch-loaders, mode-diff, seed-taxonomy. Port the idea only: stable business key -> unique index / ON CONFLICT target. |
| src/lib/db/schema.ts | 242 | DELETE AT CUTOVER (PORT intent) | Cypher constraints via `initializeSchema` (callers mode-diff/enrich/fullregen). Replaced by drizzle schema + migrations. Port the rule `canRetireHadithDatasetRowIdConstraint` (schema.ts:10): record_id must be unique+non-null -> UNIQUE NOT NULL from day one, plus a pre-load duplicate check. |
| src/lib/db/seed.ts | 80 | DELETE AT CUTOVER | only caller `init-db.ts`. |
| src/lib/db/AGENTS.md | 32 | PORT (rewrite) | "Graph evidence contract": BiographicalAssertion / TemporalAssertion / Citation-Edition-Work model, "no narrator-by-event overlap edges, compute interval overlap at read time", publish gate (publication_ready + verification_status in {human_verified, source_verified} + citation_source + locator or url). Design invariants - move to `src/db/AGENTS.md` as tables (range/min-max year columns + btree/GiST). Do not lose. |
| src/lib/import/canon-normalize.ts | 63 | DELETE NOW | zero importers (grep finds only itself); header points at an archived Python path. Real Arabic norm is `src/lib/attribution/classify-attribution.ts`. |
| src/lib/pagination.ts | - | PORT | replace `neo4j.int` skip/limit with plain numbers / Drizzle offset (or keyset). |
| src/lib/comparative/neo4j-commit.ts | - | PORT | write parallels via Drizzle; rename `commit-parallels.ts`. |
| src/lib/comparative/{pipeline,faith-prompts,you-research-client}.ts | - | KEEP | no DB coupling (pipeline used by find-parallels). |
| src/lib/attribution/classify-attribution.ts | - | KEEP | pure; Python twin `datasets/classify_attribution.py`; parity test exists; used by entity-resolution + 2 tests. |

## 2. src/scripts/*.ts (top level, 25 files)
None is imported by the app; "in pkg" = referenced by package.json.
| Script | Lines | In pkg | Class | Reason / port target |
|---|---|---|---|---|
| bench-neo4j-batch.ts | 153 | no | DELETE NOW | Neo4j timeout probe; one-off. |
| bench-neo4j-latency.ts | 62 | no | DELETE NOW | probe; header names nonexistent `probe-neo4j-perf.ts`. |
| check-traditions.ts | 51 | no | DELETE NOW | distinct h.tradition probe; subsumed by audit. |
| diagnose-chain-data.ts | 178 | no | DELETE NOW | raw neo4j-driver one-off on a single UUID. |
| diagnose-db.ts | 135 | no | DELETE NOW | counts probe, subsumed by audit-graph. |
| verify-db.ts | 46 | no | DELETE NOW | raw driver, v1 seed verification. |
| verify-migration.ts | 54 | no | DELETE NOW | v1->v2 migration check, finished. |
| verify-tirmidhi-fix.ts | 14 | no | DELETE NOW | one-off fix verification. |
| report-chain-stats.ts | 24 | no | DELETE NOW | 24-line probe. |
| init-db.ts | 29 | db:init | DELETE AT CUTOVER | comment admits schema skipped due to syntax errors; replaced by drizzle-kit migrate. |
| drain-db.ts | 49 | db:drain | DELETE AT CUTOVER | Neo4j 716 MiB tx-cap batch delete; Postgres = TRUNCATE / fresh DB. Needed until cutover for blue/green reload. |
| regen-isnad-graph.ts | 199 | db:regen, test:regen | DELETE AT CUTOVER | thin dispatcher for mode-* (fullregen/diff/enrich/test). Replace with `src/db/load/` loader. |
| audit-graph.ts | 295 | db:audit | PORT | sectioned read-only audit CLI; rewrite as SQL `db:audit` (counts, tradition distribution, orphan chains). |
| data-readiness-audit.ts | 447 | no | PORT (partial) | GDS + embedding readiness audit; keep embedding half (text length/empties) for the vector table; GDS half dies (no GDS in new design). |
| backup-db.ts | 170 | no | DELETE AT CUTOVER | Bolt JSONL dump to .omc/backups. Run ONCE before cutover as the safety backup, then retire (Postgres uses pg_dump). |
| build-credits.ts | 253 | build:credits | KEEP | no DB; generates datasets/CREDITS.md. |
| find-parallels.ts | 139 | db:find-parallels | PORT | one `runQuery` reads Hadith, then you.com via `lib/comparative/pipeline`; swap to Drizzle query. |
| ingest-er-approved.ts | 269 | db:ingest-er | PORT (low priority) | HITL ER ingestion from `er-staging.jsonl`; port to ON CONFLICT upserts or defer (Deferred). |
| extract-sanad-from-text.ts | 243 | no | DELETE NOW (confirm) | extracts sanad from text_ar markers; superseded by Python `extract_isnad_unified.py` (track uniform_isnad_extraction_20260609). Confirm with track before removal. |
| link-sanad-chains.ts | 438 | db:link-sanads | DELETE AT CUTOVER | builds legacy MatnVariation/Chain model from parse_sanad.py output - v1 schema; v2 chains come from regen/Python. |
| remediate-legacy-scalar-assessment.ts | 310 | db:remediate-legacy-assessment | DELETE AT CUTOVER | Gate-G0 fixer for scalar grade props; a fresh relational load has no legacy scalars. |
| seed-historical-data.ts | 1034 | db:seed-history | PORT (data) | curated HistoricalEvent definitions (unverified_seed; publish gate per db/AGENTS.md). Extract event array into `src/db/seed/historical-events.ts`/JSON; keep rule "refresh only while unverified_seed AND unpublished". |
| seed-narrator-bios-phase0.ts | 664 | no | PORT (data) | hand-written bios for 20 supernode narrators with provenance protection; irreplaceable curated data - never drop. |
| seed-taxonomy.ts | 237 | no | PORT (data) | two-axis taxonomy (ReligiousTradition etc.) via mergeNodeByKey/mergeEdge -> reference tables seeded by migration/seed. |
| verify-regen-acceptance.ts | 275 | no | PORT | acceptance queries become post-load verification SQL (`db:verify`); reuse thresholds. |
Also: remove dangling `db:ingest-parallels` from package.json NOW.

## 3. src/scripts/lib/**, ops, types, archive, __tests__
lib/env.ts (31) - KEEP (dotenv loader, DB-agnostic); add DATABASE_URL.

lib/regen/* (17 files, ~7.2k lines). All import `lib/db/neo4j` except io.ts, entity-resolution.ts (pure), name-mention.ts partially.
| File | Lines | Class | Note |
|---|---|---|---|
| mode-fullregen.ts | 1858 | DELETE AT CUTOVER (PORT gate) | the curated-release preflight (before first DB connection: unique record_id, translation_status=complete, provenance, schema-v2 manifest + hash binding; see lib/regen/AGENTS.md) is the real value. Port as loader preflight OR confirm Python curation gates (curation_manifest.json full_load_gates) already enforce content QA and only re-verify manifest hash. Lease / blue-green machinery dies. |
| io.ts | 528 | PORT (shared) | no DB. CSV multiline parser, `readUnifiedCsv`, `readAllRawis`, `canonicalizeTradition` (io.ts:173), `parseChainIndices` (:319), `sha256File`. Move to `src/db/load/io.ts`. COPY from neo4j_export bundle may make the parser unnecessary - loader design decision. |
| batch-loaders.ts / batch-loaders-fresh.ts | 685/15 | DELETE AT CUTOVER | UNWIND-batch Cypher; replaced by Drizzle `insert().values(chunk).onConflictDoNothing()` or COPY. |
| load-hadith.ts / load-chain.ts / load-narrators.ts | 233/277/198 | DELETE AT CUTOVER | per-node MERGE loaders (already superseded by batch-loaders). |
| mode-diff.ts / mode-enrich.ts | 293/246 | DELETE AT CUTOVER | incremental modes; Postgres upsert by record_id covers it. |
| mode-test.ts | 395 | DELETE AT CUTOVER (PORT checks) | guardrail suite -> post-load SQL checks. |
| assessment.ts | 457 | PORT pure parts | pure: `schemeForTradition` (:79 Sunni->sunni_7tier, Imami->imami_4tier, Zaydi->zaydi_3tier, Ibadi->ibadi_2tier), `parseGradingsFull` (:340). DB writes + `migrateScalarAssessments` die. 88% of ~399k assessments are `no_extant_evaluation` placeholders: do NOT load them; absent row = no evaluation. |
| entity-resolution.ts | 592 | PORT pure parts | `ErTier` (:72: chain_indx_join, lexicon_exact, lexicon_blocked, rerank, regex_sanad) -> `extraction_method` enum on chain/link rows. Re-declares `UnifiedRow`/`RawiRecord` duplicating io.ts:59,117 (dedupe). |
| temporal-plausibility.ts | 271 | PORT pure fn | `assessTemporalPlausibility` (:63-111) pure. DB funcs die; replace with one set-based SQL UPDATE or read-time compute. |
| name-mention.ts | 174 | PORT (norm only) | `norm()` (:69) duplicates classify-attribution; DB write dies. |
| supernode-detect.ts | 273 | DELETE AT CUTOVER | existed for Neo4j supernode MERGE contention. |
| tombstone.ts | 92 | DELETE AT CUTOVER | Neo4j soft-delete; Postgres: dataset_version FK / deleted_at if needed. |
| dataset-version.ts | 591 | PORT concept, simplify | single `dataset_version` table (id, csv_sha256, manifest_sha256, release_class, loaded_at, active) + rule "non_release can never be active" (`inferDatasetVersionReleaseClass` :69, lifecycle asserts :89-170). FullregenLease (:176-) replaced by `pg_advisory_lock`. |
| AGENTS.md | - | PORT (rewrite) | keep curated release-gate paragraphs; drop Neo4j/lease/bolt:// parts. |

ops/ (post-regen-supervisor.sh 18, -v2.sh 24, README.md 26): DELETE AT CUTOVER; v2 DELETE NOW (README says kept only for 2026-05-22 timeline). Poll a `db:regen` PID then run `--mode=test`.
types/parallel-candidate.ts (93): KEEP (no DB type).
archive/: 24 files + README - one-off v1 import/migration scripts (import-*, migrate-*, enrich-narrators-*, apply-schema, peek-*, probe-*, tag-ibadi, normalize-grades...), all Neo4j; excluded from tsc and eslint; nothing imports them. KEEP (archive policy); zero runtime value.

__tests__/ (9 `.test.ts` regen-* plus neo4j-test-env.ts 80, fixtures/, AGENTS.md 5 lines), tsx-run, excluded from tsc:
- regen-arabic-norm-parity.test.ts (417): imports only classify-attribution -> KEEP (DB-free; guards JS \b vs Python \b). Move next to `src/lib/attribution/`.
- regen-tradition-canonicalization.test.ts (348): live-Neo4j section DELETE AT CUTOVER; pure canonicalize table cases PORT.
- regen-full-load-hardening.test.ts (753): the "DB-free contract test" for the release gate (lib/regen/AGENTS.md "Focused verification") -> PORT with gate logic; best test in set.
- regen-modes (371), regen-isnad-graph (729), regen-guardrails (652), regen-schema (275), regen-multi-isnad (287), regen-chain-indx-multi-branch (341), regen-tier1-coverage (332): Neo4j-flavoured; DELETE AT CUTOVER but mine first for pure cases (temporal plausibility table, `parseChainIndices` multi-branch, tier1 coverage thresholds) and re-express as: load CSV fixture into a throwaway PG db, assert rows (flow-tests policy).
- neo4j-test-env.ts DELETE AT CUTOVER; AGENTS.md rewrite (`TEST_DATABASE_URL`; keep the disposable-DB marker guard idea).
- `test:regen` DELETE AT CUTOVER; add `test` script running kept pure tests.

## 4. Config files
| File | Finding | Class |
|---|---|---|
| package.json | NOW: remove `db:ingest-parallels`. CUTOVER remove: db:init, db:drain, db:regen, db:audit(repoint), db:remediate-legacy-assessment, test:regen, db:link-sanads, dep `neo4j-driver`; repoint db:seed-history, db:ingest-er, db:find-parallels. Add: `drizzle-orm`, `pg` (or `postgres`), dev `drizzle-kit`, scripts db:generate/db:migrate/db:load/db:audit/db:verify/test. Check `openai` use (embeddings). | PORT |
| Dockerfile | section 6 | PORT (fix) |
| .dockerignore | excludes .git, .env*, .next, node_modules, datasets, .omc, .mpg, logs, coverage, pytest/pycache, tsbuildinfo. OK; must NOT exclude `drizzle/`. Add conductor/, docs/, .agent/, the .docx, src/scripts/archive. | KEEP + tweak |
| .railwayignore | content identical to .dockerignore; only used by `railway up`. | KEEP (optional delete) |
| eslint.config.mjs | globalIgnores include `src/scripts/archive/**` and `datasets/hadith-data/archive/**`; fine. Add `drizzle/**`. | KEEP |
| tsconfig.json | excludes node_modules, datasets, src/scripts/archive, src/scripts/__tests__. ADD `src/scripts` (or use tsconfig.scripts.json) so `next build` stops typechecking operator scripts. `tsconfig.tsbuildinfo` at repo root is an artifact (check .gitignore). | PORT |
| next.config.ts | `output: 'standalone'` - Dockerfile depends on it. Add `serverExternalPackages: ['pg']` if node-postgres. | KEEP |
| conductor/tech-stack.md | stale: L16 Graph DB Neo4j, L17 Prisma, L20 node types, L43-48 command table (`db:import`/import-datasets.ts which is archived; db:ingest-parallels dangling), L56-57 schema/connection files, L63-66 NEO4J env. | PORT (rewrite) |
| conductor/workflow.md | stale: L29 "no any unless Neo4j driver", L30 parameterized Cypher, L55-58 "Neo4j Schema Changes / db:init". Rewrite: SQL only in `src/db/queries` via Drizzle; migrations checked in via drizzle-kit. | PORT (rewrite) |

## 5. Pure logic worth preserving + Python duplication
| Logic | TS location | Python twin? | Action |
|---|---|---|---|
| Temporal plausibility (impossible if student born after teacher died or teacher born after student died; plausible only if all 4 bounds present; else unknown; never delete edges) | temporal-plausibility.ts:63-111 | NO (only birth/death columns in contract.py:46-48) | Preserve - unique logic. Pure fn + one SQL UPDATE on the narrator-link table; table-driven test (4 cases + nulls). |
| Tradition canonicalization (`TRADITION_MAP`, fail-closed on unknown, no silent Sunni default) | io.ts:~150-180 | YES: `tradition_id()` contract.py:431, `add_tradition_column.py`, `regen_unified_csvs.py` | Keep ONE copy; enforce with a pg enum ('Sunni','Imami','Zaydi','Ibadi'). Source->single-tradition rule (mode-fullregen.ts:~209 `CANONICAL_SOURCE_TRADITIONS`) becomes source.tradition FK. |
| Grade scheme per tradition | assessment.ts:79 | partial (`grade_tradition` column) | lookup table/enum. |
| Gradings parse | assessment.ts:340 | unknown | keep pure. |
| ER tier enum | entity-resolution.ts:72 | extraction lives in Python (`extract_isnad_unified.py`, `classify_attribution.py`) | keep enum as provenance column. |
| Arabic `norm` | classify-attribution.ts (+ duplicate name-mention.ts:69) | YES `datasets/classify_attribution.py` + parity test | KEEP TS; drop duplicate. Postgres unaccent/pg_trgm will not strip harakat reliably -> store a `text_normalized` column computed with this norm at load time. |
| chain_indx multi-branch parse | io.ts:288-340 | Python emits chain_indx | keep pure + tests. |
| Curation release gate | mode-fullregen.ts preflight | partly Python (curation_manifest.json gates) | port minimal: manifest hash binding + zero blockers; do not duplicate content QA done in Python. |
| Supernode, tombstone, lease | - | - | do not port. |

## 6. Dockerfile / Railway findings
Facts (Railway MCP): project hadith-ontology (43973172-fd19-4c41-8097-369cf805cbe6), services taawun, islamicapps (35e54e3c-6f77-4bde-9811-1d388dee6787), neo4j-hadith-graph-alltraditions (9cc54126-...). islamicapps config: `build.builder=RAILPACK`, no dockerfilePath/start/healthcheck/preDeploy; domain islamicapps-production.up.railway.app -> port 8080; source JadeZaher/islamicapps branch main; region us-west2. Deploys: 2026-08-18 FAILED at BUILD_IMAGE ("Failed to build an image", no commit meta => CLI upload, diagnosis null; id 623d9113-5b8a-46ad-9890-e7102b67bec9); 2026-07-22 02:11 SUCCESS (the only live deploy; canRollback true); 07-22 02:07 FAILED; older GitHub deploys REMOVED (last built commit 176ae40, 2026-06-03). Service variables: NEO4J_URL/USERNAME/PASSWORD, YOU_API_KEY, plus strays HEAP_INITIAL_SIZE, HEAP_MAX_SIZE, PAGECACHE_SIZE, NEO4J_PLUGINS, NODE_CSV_URLS, RELATION_CSV_URLS (Neo4j-server/import vars on the app service - remove at cutover; inspect the *_CSV_URLS for embedded secrets).
Problems:
1. Builder mismatch: explicit RAILPACK means the Dockerfile is not what deploys. If the Dockerfile is used, `ENV PORT 3000` + `EXPOSE 3000` conflict with the domain pinned to 8080 -> 502. Fix: drop `ENV PORT 3000` (Railway injects PORT; Next standalone honours it), clear or re-point the domain target port (auto-detect), keep `HOSTNAME 0.0.0.0`.
2. Likely build-failure causes (no logs obtained; ranked): (a) `next build` typechecks all `src/scripts/**` (tsconfig include) incl. 1858-line mode-fullregen; (b) a page prerendering from Neo4j at build with no NEO4J_* in build env (Railway passes variables to Docker builds only via declared `ARG`); (c) tsbuildinfo/stale files; (d) legacy `ENV key value` syntax only warns. Get real logs: `railway logs --build` for the deployment id above (or MCP get-logs).
3. Dockerfile gaps: no `NEXT_TELEMETRY_DISABLED`, no HEALTHCHECK, runner image has no tsx/drizzle-kit (devDeps) so a migrate step must be built in; node:22-alpine + standalone copy layout is otherwise correct.
4. .railwayignore duplicates .dockerignore.
Recommended deploy config (config-as-code `railway.json`, verify field names against Railway docs via search-docs before committing):
```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "build": { "builder": "DOCKERFILE", "dockerfilePath": "Dockerfile" },
  "deploy": {
    "preDeployCommand": ["node", "scripts/migrate.mjs"],
    "healthcheckPath": "/api/health",
    "healthcheckTimeout": 60,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 5
  }
}
```
- Migrate-on-deploy: `preDeployCommand` runs in the built image on the private network before the new deploy goes live; non-zero exit blocks the release. drizzle-kit is a devDep and absent from the standalone runner, so use the programmatic migrator (`drizzle-orm/node-postgres/migrator`, `migrate(db, { migrationsFolder: 'drizzle' })`) in a small `scripts/migrate.mjs`, esbuild-bundled in the builder stage to one file (standalone tracing will not include its deps), and `COPY --from=builder /app/drizzle ./drizzle` into the runner. Connect with `DATABASE_URL=${{Postgres.DATABASE_URL}}` (reference variable, private domain).
- Add `/api/health` doing `SELECT 1` so the healthcheck gates traffic and wake-failures stop being silent.
- Postgres service: plain Railway Postgres lacks pgvector; use the Railway pgvector template/image. Keep it small: low shared_buffers, pool max ~5, `halfvec` in a separate embeddings table. Local PG16 (5433) lacks pgvector: put `CREATE EXTENSION vector` + the embeddings table in a SEPARATE migration so local dev can skip it.
- Prerender: mark DB-reading routes `export const dynamic = 'force-dynamic'` so the build needs no DB (preferred over ARG DATABASE_URL).
- At cutover: remove NEO4J_*, HEAP_*, PAGECACHE_SIZE, NEO4J_PLUGINS, *_CSV_URLS from the app; add DATABASE_URL; delete the Neo4j service + volume ONLY after final backup-db.ts JSONL + verification and explicit owner approval (memory: never delete data).

## 7. Stale documentation
- conductor/tech-stack.md, conductor/workflow.md (lines above); conductor/product-guidelines.md and conductor/code_styleguides/typescript.md (Neo4j mentions); tracks: neo4j_isnad_graph_regen_20260516 (mark SUPERSEDED, do not edit), gds_setup_analytics_20260425 (GDS obsolete), vector_embedding_pipeline_20260425 (retarget to pgvector).
- CONTRIBUTING.md:57 ("Neo4j for the graph"); README.md (check); .agent/rules/app-goal.md (L8, L13-16, L103: Neo4j Community on Railway, neo4j-driver).
- src/lib/db/AGENTS.md, src/scripts/lib/regen/AGENTS.md, src/scripts/__tests__/AGENTS.md, src/scripts/ops/README.md.
- datasets/hadith-data/neo4j_export/{AGENTS.md,README.md}: still valid as the export bundle (feed for Postgres); reword as a source format. Also datasets/hadith-data/{README.md,DATA_QUALITY_REPORT.md}, datasets/RESEARCH_REPORT.md, datasets/strategies/{README.md,uniform-tahweel-aware-isnad-extraction.md}.
- docs/architecture/data-architecture.md: status proposed -> accepted; its lines ~235-258 list Neo4j removal items (consistent).
- Drift: tech-stack lists Prisma and `db:import` that do not exist.

## 8. Ordered action list
DELETE NOW (pre-cutover, no live dependence; prefer git mv to archive): bench-neo4j-batch, bench-neo4j-latency, check-traditions, diagnose-chain-data, diagnose-db, verify-db, verify-migration, verify-tirmidhi-fix, report-chain-stats, src/lib/import/canon-normalize.ts, ops/post-regen-supervisor-v2.sh, package.json `db:ingest-parallels`; extract-sanad-from-text.ts after confirming track. Then ONE tsc/lint sweep.
DELETE AT CUTOVER: db/neo4j.ts, neo4j-helpers.ts, schema.ts, seed.ts, init-db, drain-db, regen-isnad-graph, link-sanad-chains, remediate-legacy-scalar-assessment, backup-db (after final backup), lib/regen/{mode-*, batch-loaders*, load-*, supernode-detect, tombstone, dataset-version DB parts}, ops/*, Neo4j tests + neo4j-test-env, neo4j-driver dep.
PORT: audit-graph, data-readiness-audit (embedding half), find-parallels, ingest-er-approved, seed-historical-data, seed-narrator-bios-phase0, seed-taxonomy, verify-regen-acceptance, temporal-plausibility (pure), assessment pure fns, entity-resolution pure parts, io.ts, release-gate preflight + its test, neo4j-commit.ts, pagination.ts, db/AGENTS.md invariants, graph-actions.ts, comparative-actions.ts, comparative research route.
KEEP: lib/env.ts, build-credits.ts, types/parallel-candidate.ts, classify-attribution.ts + parity test, comparative pipeline/faith-prompts/you client, archive/, eslint config, next.config standalone, Python pipeline + neo4j_export bundle exporter.
