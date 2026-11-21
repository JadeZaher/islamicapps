---
type: research
date: 2026-11-21
intent: Choose the low-memory store to replace Neo4j on Railway (Postgres vs SQLite/libSQL vs Turso vs Neon/Supabase), with sourced pricing, pgvector sizing, Postgres tuning and Drizzle wiring.
status: findings
---

# 05 - Railway database choice (low memory first)

Raw captures live in `.omc/research/pg-refactor/raw/` (cited below as `raw/<file>:<line>`).
Every claim has a URL; "unverified" means no primary source was found; "derived" means
arithmetic from cited inputs.

## Verdict (TL;DR)

**Railway Postgres template (image `ghcr.io/railwayapp-templates/postgres-ssl:18`), always-on,
tuned with `ALTER SYSTEM`, private networking, pgvector already in the image.
Embeddings: `halfvec`, no ANN index at launch; if 1024-dim, add a binary-quantized
`bit(1024)` column for exact Hamming pre-filter + halfvec re-rank.**
Expected Railway bill on Hobby: **about $5-8/month total** (app + DB), versus roughly $18/month
of RAM alone for Neo4j at 1.78 GB.

Flip conditions are listed in section 8.

---

## 1. Railway pricing (source: https://docs.railway.com/pricing/plans, `raw/pricing_plans.md`)

| Item | Price | Source line |
| --- | --- | --- |
| RAM | $10 / GB / month ($0.000231 / GB / min) | `raw/pricing_plans.md:59` |
| CPU | $20 / vCPU / month ($0.000463 / vCPU / min) | `:60` |
| Network egress | $0.05 / GB | `:61` |
| Volume storage | $0.15 / GB / month | `:62` |
| Free plan | $0/mo, $1 usage/mo, services sleep, 0.5 GB RAM/service, 0.5 GB volume, 1 project / 3 services | `:24`, `:39`; `raw/pricing_free-plan.md:9-15` (https://docs.railway.com/pricing/free-plan) |
| Hobby | $5/mo, includes $5 usage (pay only the delta above $5) | `:25`, `:86-95` |
| Pro | $20/mo, includes $20 usage | `:26`, `:97` |
| Hobby per-service limits | 48 GB RAM, 48 vCPU, 5 GB volume default (resizable) | `:41`; `raw/volumes_reference.md:16-18` |
| Backups | incremental, copy-on-write, billed at volume rate on exclusive bytes; daily/weekly/monthly schedules | `raw/volumes_backups.md:13,50-52` (https://docs.railway.com/volumes/backups) |
| Private network traffic | not egress; use private `DATABASE_URL`, public URL traffic counts as egress | `raw/pricing_understanding-your-bill.md:124` (https://docs.railway.com/pricing/understanding-your-bill) |

Billing gotcha (community, not docs): Railway bills container memory including Linux page cache;
one thread found 94% of billed memory was page cache, another saw 0.9 GB -> 6 GB after a PITR backup.
Sources: https://station.railway.com/questions/railway-postgres-pitr-backup-leaves-6-gb-e762df27 ,
https://station.railway.com/questions/postgres-high-ram-usage-e99b4be4 (search summary; only the second was fetched).
Implication: do **not** enable PITR (pgBackRest WAL archiving) on a cost-sensitive instance; use scheduled volume backups.

## 2. How Railway Postgres is deployed

- Template `postgres` = single service, image `ghcr.io/railwayapp-templates/postgres-ssl:18`, volume at
  `/var/lib/postgresql/data`, `PGDATA=/var/lib/postgresql/data/pgdata`, `DATABASE_URL` uses
  `RAILWAY_PRIVATE_DOMAIN:5432`, `RAILWAY_DEPLOYMENT_DRAINING_SECONDS=60`
  (Railway MCP `describe-template postgres`, https://railway.com/deploy/postgres).
- It is a plain container: official Docker Hub `postgres` image + self-signed SSL init script
  (cert renewed by redeploy every 820 days) + tini PID 1 + wrapper
  (https://docs.railway.com/databases/postgresql `raw/databases_postgresql.md:22`;
  https://github.com/railwayapp-templates/postgres-ssl `raw/postgres-ssl_Dockerfile.18.txt`, `raw/postgres-ssl_README.md.txt`).
  The wrapper refuses to start if the volume is not at `/var/lib/postgresql/data` (`raw/postgres-ssl_wrapper.sh.txt:8-16`).
- **pgvector IS in the official image now**: Dockerfile installs `postgresql-18-pgvector=0.8.*` and `pgaudit`
  (`raw/postgres-ssl_Dockerfile.18.txt`, the `apt-get install ... "postgresql-18-pgvector=${PGVECTOR_PKG_VERSION}"` line;
  README "Extensions" `raw/postgres-ssl_README.md.txt:76-83`: "Both are a `CREATE EXTENSION` away").
  CONFLICT: the docs page still says "we do not plan to add extensions to the PostgreSQL templates"
  and points at the community pgvector template (`raw/databases_postgresql.md:71-77`). The image source is
  authoritative; verify with `SELECT * FROM pg_available_extensions WHERE name='vector'` after provisioning.
  No separate pgvector template needed. (Community template `3jJFCA` = `pgvector/pgvector:pg18`, unverified maintainer, TCP proxy on by default - avoid.)
- Image preloads `pg_stat_statements,pgaudit` via `shared_preload_libraries` on every boot (`raw/postgres-ssl_README.md.txt:85-90`).
- Backups: native volume backups; HA (Patroni), PITR and PgBouncer are opt-in (`raw/databases_postgresql.md:5-7`).
- SHM size default 64 MB, override `RAILWAY_SHM_SIZE_BYTES` (`raw/databases_postgresql.md:80-92`).
- Changing image/start command/variables "makes the database yours to manage" (`raw/databases_postgresql.md:100`).
- Dev/prod mismatch: local dev is PG16 on 5433 without pgvector; Railway template is PG18 with pgvector 0.8.x.
  Either pin the Railway service to a `:16.x` tag or run PG18+pgvector locally (e.g. `pgvector/pgvector:pg18` container) for vector work.
- **Idle memory footprint**: no official number (unverified). Community: a near-idle Railway Postgres measured
  ~50 MB with no clients, ~33 MB after `max_connections=10`, 333 MB after one large index scan (page cache);
  default `shared_buffers` reported as 16384 x 8kB = 128 MB
  (https://station.railway.com/questions/postgres-high-ram-usage-e99b4be4, posts 2026-09-06..09).
  Another summary cites a ~300 MB floor on an idle DB (search-result summary, unverified).
  Working estimate for this app tuned as in section 5: **80-200 MB billed**, dominated by page cache of the hot working set.

## 3. Serverless (App Sleep) for a DB over private networking

Source: https://docs.railway.com/deployments/serverless (`raw/deployments_serverless.md`).
- Sleep is driven by **outbound** inactivity: inactive after 5 min, in practice sleeps 5-10 min after last outbound packet (`:21`).
- Kept awake by open DB connections / poolers and private-network traffic in either direction (`:25-31`).
- Woken by traffic from internet or **from another service over the private network** (`:38`). So yes, a DB can sleep and be woken by the app over private networking; Free-plan doc says "Databases sleep the same way, wake on the next connection, and keep their data" (`raw/pricing_free-plan.md:20`).
- Wake latency: **not documented (unverified)**. Docs only say "small delay", first request "may return a 502", and sleeping de-prioritizes the workload, possibly requiring a rebuild (`:44-49`).
- Reliability: community report (2026-04-08, no staff reply) that with serverless app + serverless Postgres, Postgres stayed asleep on 30-40% of cold starts; fix was manual redeploy (https://station.railway.com/questions/postgres-stays-asleep-when-backend-wakes-b1d473f6). Second report of a serverless DB not waking: https://station.railway.com/questions/urgent-database-serverless-not-waking-621ef75e (title only, unverified detail).
- Conclusion: the current HTTP 500-on-wake problem is exactly this class. **Do not enable serverless on the DB.** A tuned always-on Postgres costs ~$1-2/mo of RAM, less than the reliability cost. Also note the app's pool (idle connections) would keep the DB awake anyway unless `idle_timeout` drains it.

## 4. Volumes (relevant to SQLite-on-volume)

Source: https://docs.railway.com/volumes/reference (`raw/volumes_reference.md`).
- **One volume per service** (`:70`); **replicas cannot be used with volumes** (`:71`).
- Redeploy of a service with a volume has **a small amount of downtime even with a healthcheck**, because two deployments cannot mount it at once (`:72-74`).
- Size default: Free/Trial 0.5 GB, Hobby 5 GB, Pro 50 GB; live grow, no shrink (`:14-19`, `:75`).
- Per-project volume caps: Free 1, Hobby 10, Pro 20 (`:22-31`).
- I/O: 3,000 read IOPS / 3,000 write IOPS on all sizes (`:43-46`).
- Billed on used bytes, ~2-3% filesystem metadata overhead (`:49-51`).
- Non-root images may hit permission issues; `RAILWAY_RUN_UID=0` (`:79`). The repo Dockerfile runs as `nextjs` user (`Dockerfile:46`), so this would bite SQLite-on-volume.
- **Pre-deploy commands do not mount volumes** and run in a separate container (https://docs.railway.com/deployments/pre-deploy-command `raw/railway_pre-deploy-command.md:24`). So SQLite migrations must run in the start command; Postgres migrations can run as a pre-deploy command (`:8`: a failed command blocks the deploy, no retry).
- Getting the bulk-loaded DB file onto the volume: `railway volume browse/files`, sftp/scp via `railway ssh` (`:78`).

## 5. Postgres low-memory tuning

Defaults (https://www.postgresql.org/docs/current/runtime-config-resource.html, `raw/pg_runtime-config-resource.html`;
https://www.postgresql.org/docs/current/runtime-config-connection.html):
`shared_buffers` 128 MB, `work_mem` 4 MB, `maintenance_work_mem` 64 MB, `max_connections` 100.
Docs: "On systems with less than 1GB of RAM, a smaller percentage of RAM is appropriate".

Recommended for this workload (read-mostly, ~5 pooled connections; values are engineering judgement, not benchmarked):

```sql
ALTER SYSTEM SET shared_buffers = '64MB';          -- restart required
ALTER SYSTEM SET max_connections = 20;             -- restart required
ALTER SYSTEM SET work_mem = '4MB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';    -- SET LOCAL higher only for one-off index builds
ALTER SYSTEM SET effective_cache_size = '256MB';   -- planner hint only, allocates nothing
ALTER SYSTEM SET max_parallel_workers_per_gather = 1;  -- parallel workers use /dev/shm (64MB SHM default)
ALTER SYSTEM SET autovacuum_max_workers = 2;       -- restart required
ALTER SYSTEM SET jit = off;                        -- small OLTP queries; avoids LLVM memory
ALTER SYSTEM SET huge_pages = off;
```

How to apply on Railway's image: `ALTER SYSTEM` writes `postgresql.auto.conf` on the volume and survives
redeploys; the image explicitly does not touch `postgresql.auto.conf` and keeps its own settings in
`$PGDATA/conf.d/` (`raw/postgres-ssl_README.md.txt:285-291`). Caveat: an operator `ALTER SYSTEM SET shared_preload_libraries`
replaces the list; the wrapper re-adds `pg_stat_statements,pgaudit` on boot (`:85-90`).
Alternative: custom start command `postgres -p 5432 -c listen_addresses=* -c shared_buffers=64MB ...`
(Dockerfile `CMD` is `["postgres","-p","5432","-c","listen_addresses=*"]`), but changing the start command
makes the DB "yours to manage" (`raw/databases_postgresql.md:100`) - prefer `ALTER SYSTEM` + restart.
Run it as a checked-in SQL file (e.g. `db/ops/railway-tuning.sql`) so it is reproducible.
Per-backend RSS ~5-10 MB each (unverified estimate) -> 5 app connections + autovacuum + bg workers ~= 60-100 MB on top of shared_buffers.

## 6. pgvector sizing for 99,283 embeddings

Per-value size from pgvector README (https://github.com/pgvector/pgvector, `raw/pgvector_README.md`):
`vector` = 4*d + 8 bytes (`:966`), `halfvec` = 2*d + 8 bytes (`:1004`), `bit` = d/8 + 8 bytes (`:1042`).
Limits for indexing: `vector` up to 2,000 dims, `halfvec` up to 4,000 (`:252-253`).

| Type | bytes/value | raw x 99,283 (derived) | on-disk heap, STORAGE PLAIN (derived: rows per 8 KB page) |
| --- | --- | --- | --- |
| vector(1024) | 4,104 | 407 MB | 1 row/page -> ~813 MB (or TOASTed ~430 MB with default storage) |
| halfvec(1024) | 2,056 | 204 MB | 3 rows/page -> ~271 MB |
| vector(384) | 1,544 | 153 MB | 5 rows/page -> ~163 MB |
| halfvec(384) | 776 | 77 MB | 10 rows/page -> ~81 MB |
| bit(1024) (binary quantized) | 136 | 13.5 MB | ~45 rows/page -> ~18 MB |

Page math assumes ~28 B tuple header+id and 8,168 usable bytes per page (derived, not measured).
halfvec(1024) at 2,056 B sits just over the ~2 KB TOAST threshold, so declare `STORAGE PLAIN`
(README recommends PLAIN for best performance, `:686-691`).

Index behaviour (README):
- Default is **exact** search, perfect recall (`:197`).
- HNSW: better speed/recall, slower build, **more memory**; build is much faster when the graph fits in `maintenance_work_mem`, otherwise warns and continues slower (`:208`, `:291-305`). HNSW index size ~= vector data + neighbour lists, i.e. roughly the heap size or a bit more (unverified estimate: halfvec(1024) HNSW ~250-350 MB). To be fast it must stay in cache -> breaks a 256 MB budget at 1024 dims.
- IVFFlat: faster build, **less memory**, worse speed/recall; `lists = rows/1000` (~100 here), `probes ~ sqrt(lists)` (`:336-342`).
- Filtering with ANN indexes is post-filter; use iterative scans (pgvector >= 0.8.0) (`:450-495`) - matters for "search within tradition X".
- Binary quantization + re-rank is documented (`:577-607`): exact Hamming scan over `bit(d)` then re-order top-N by full-precision distance.

Is exact (no index) search fast enough at 99k? (estimate, NOT benchmarked; pgvector is not installed on local PG16 so it could not be measured here):
- halfvec(384), ~81 MB scanned: expect ~50-200 ms warm on 1 vCPU. Acceptable; **skip the index**.
- halfvec(1024), ~271 MB scanned: ~0.3-1 s warm; cold reads hit volume (3,000 IOPS) and could be multi-second. Not acceptable as-is without either an index (RAM) or the bit pre-filter.
- bit(1024) Hamming scan ~18 MB + re-rank top 100 halfvec rows: ~10-50 ms, ~20 MB hot set. **Recommended path if the model is 1024-dim (e.g. BGE-M3)**: store `halfvec(1024) STORAGE PLAIN` + generated/maintained `bit(1024)` column, no ANN index.
- Benchmark task before shipping semantic search: load 99k random halfvecs into a pgvector PG18 container capped at 256 MB and time `ORDER BY embedding <=> $1 LIMIT 20` cold and warm.

## 7. Drizzle ORM wiring (Next.js 16 standalone)

- Versions on npm today: `drizzle-orm` latest **0.45.4**, `rc` 1.0.0-rc.6; `drizzle-kit` latest **0.31.11**, `rc` 1.0.0-rc.6; `postgres` (postgres.js) 4.1.1; `pg` 8.23.1 (`npm view ... dist-tags`, 2026-11-21). The online docs (https://orm.drizzle.team/llms-full.txt, `raw/drizzle_llms-full.txt`) now describe v1 (e.g. `drizzle-kit@rc`, folder-per-migration layout at `:6775-6790`). Pin the stable 0.45.x/0.31.x pair or deliberately adopt 1.0 rc; do not mix.
- Repo today: no drizzle/postgres deps; `neo4j-driver ^6.0.1`, `next 16.0.10` (`package.json:33-34`); `output: 'standalone'` (`next.config.ts:4`); Dockerfile runner copies only `.next/standalone` + static and runs `node server.js` as `nextjs` user (`Dockerfile:27-57`).
- Drivers (docs `raw/drizzle_llms-full.txt:63520-63570`): both `drizzle-orm/node-postgres` (Pool) and `drizzle-orm/postgres-js` supported, either `drizzle(process.env.DATABASE_URL)` or pass a client. `prepare: false` only needed behind a transaction-mode pooler (`:63598-63604`) - not needed with direct private connection.
- Recommended `src/db/client.ts`: module-level singleton cached on `globalThis` (prevents pool multiplication under dev HMR), `postgres(url, { max: 5, idle_timeout: 20, connect_timeout: 10 })` (or `new Pool({ max: 5, idleTimeoutMillis: 20000 })`), `ssl` off on private network (`*.railway.internal`), on when using `DATABASE_PUBLIC_URL`. Import only from server code (`import 'server-only'`). Pool max 5 vs `max_connections=20` leaves headroom for migrations/psql/loader.
- pgvector in Drizzle: `vector` + `l2Distance`/`cosineDistance`/`innerProduct` + HNSW index helpers since 0.31.0 (https://github.com/drizzle-team/drizzle-orm/blob/main/changelogs/drizzle-orm/0.31.0.md, `raw/drizzle_changelog_0.31.0.md:45-64`). **`halfvec` column exists in 0.45.4** (verified: https://unpkg.com/drizzle-orm@0.45.4/pg-core/columns/vector_extension/halfvec.d.ts) and `bit`, `sparsevec`; distance fns in `drizzle-orm/sql/functions/vector` include `cosineDistance`, `hammingDistance`, `jaccardDistance`. Drizzle does not create the extension: run `CREATE EXTENSION IF NOT EXISTS vector` in a custom migration. `STORAGE PLAIN` is not a Drizzle column option (unverified) -> add via custom SQL migration.
- Migrations at deploy: `drizzle-kit generate` locally, commit `drizzle/`. At deploy use a **Railway pre-deploy command** running a tiny script with `migrate()` from `drizzle-orm/postgres-js/migrator` (or `node-postgres/migrator`). Pre-deploy runs in the app image, on the private network, with app env vars, and a failure blocks the deploy (`raw/railway_pre-deploy-command.md:3-8`). Risk: Next standalone output traces only imported files, so the runner image will not contain `drizzle/` or the migrator entry unless the Dockerfile `COPY`s them (or the script is bundled with esbuild). Do not ship `drizzle-kit` in the runtime image.
- SQLite in Drizzle: `drizzle-orm/libsql`, `better-sqlite3`, `bun-sqlite`, and node:sqlite (1.0 beta tag `node-sqlite`) are supported (`raw/drizzle_llms-full.txt:23988-24112`). The schema would need a separate `sqlite-core` definition: Drizzle schemas are dialect-specific, so "only query modules change" in `docs/architecture/data-architecture.md:37-38` understates a move - table definitions change too.

## 8. Options compared (Hobby plan, monthly, derived from section 1 rates)

Assumptions: Next app ~200 MB avg ($2.0), light CPU (~0.02 vCPU avg = $0.40), DB data ~1.5-2 GB incl. indexes + vectors, egress < 5 GB. Hobby bill = max($5, usage).

| Option | Memory (est.) | Usage $/mo (est.) | Bill $/mo | Pros | Cons |
| --- | --- | --- | --- | --- | --- |
| **A. Railway Postgres template, tuned, always-on** | app 200 MB + PG 100-200 MB | app 2.4 + PG (1.0-2.0 RAM + 0.4 CPU + 0.3 vol + ~0.2 backups) ~= 4.3-5.3 | **$5-6** (headroom to ~$8) | pgvector in image; private net; backups; pre-deploy migrations; matches doc proposal; multi-writer curation; `COPY` loader works over TCP | DB ~1-2 $/mo more than SQLite; prod PG18 vs local PG16 |
| B. SQLite (better-sqlite3 / libSQL file) on volume in app service | app 250-350 MB (page cache incl.) | ~3.0-3.8 | **$5** (inside included usage) | lowest memory, zero network hops, one service | no replicas; downtime each redeploy (volume); migrations must run in start command (no volume in pre-deploy); non-root user volume perms; loader must ship a file via ssh/sftp; single writer; sqlite-vec is "pre-v1, expect breaking changes" (https://github.com/asg017/sqlite-vec `raw/sqlite-vec_README.md:11`), libSQL native vectors only via libSQL driver; dialect-specific Drizzle schema |
| C. Turso (hosted libSQL) + app on Railway | app 200 MB | Railway ~2.4 + Turso Free $0 (5 GB, 500M rows read, 10M rows written/mo) or Developer $4.99 | **$5** (or ~$10) | no DB container at all; native vectors `F32/F16/F8_BLOB`, DiskANN index `libsql_vector_idx` (https://docs.turso.tech/features/ai-and-embeddings `raw/turso_ai-embeddings.md:15-17,43-46,151`) | every query crosses public internet (Railway egress $0.05/GB + latency x many fixed-depth joins per page); rows-read metering: one brute-force vector query over 99k rows = 99k rows read -> ~5k searches/mo exhausts Free; pricing source https://turso.tech/pricing `raw/turso_pricing.html.txt:40-70` |
| D. Neon (external) + app on Railway | app 200 MB | Railway ~2.4 + Neon Launch ~$15 (Neon's own "intermittent" example: 140 CU-h, 1 GB) | **~$20** | scale-to-zero, branching, pgvector | Free tier caps 1 GB storage/project (`raw/neon_pricing.html.txt:26`) - likely too small with vectors; $0.106/CU-h, $0.35/GB-mo (`:23,26`); cold start latency on scale-to-zero (unverified ms); public-internet hop + Railway egress (https://neon.com/pricing) |
| D'. Supabase (external) | - | Pro $25 incl. $10 compute credit (Micro 1 GB) | **~$30** | managed, pgvector | Free: 500 MB DB, pauses after 1 week inactivity (`raw/supabase_pricing.html.txt:55-62`); Pro $25 (`:142-155`) (https://supabase.com/pricing) |
| Status quo: Neo4j on Railway | 1,780 MB avg | RAM alone ~$17.8 + CPU | ~$20+ | - | sleeps -> 500s; no graph features used |

### Recommendation

Option A. It removes ~1.6 GB of RAM, costs about the Hobby floor, keeps writes multi-user safe,
lets `drizzle migrate` run in a pre-deploy command, and pgvector needs no custom image.
Run it always-on (no serverless), private `DATABASE_URL`, scheduled daily volume backups, no PITR.

### Conditions that flip it

- -> **B (SQLite on volume)** if: curation stays single-writer/admin-only, a few seconds of downtime per deploy is acceptable, no replicas are ever needed, and the memory budget must fall below ~250 MB total. Saves ~$1-2/mo only.
- -> **C (Turso)** if: the app is moved off Railway's container model (edge/serverless hosting) or the owner wants zero DB ops; only if per-page query count is reduced (batching) because each query is a WAN round-trip.
- -> **D (Neon)** if: DB branching per PR / preview environments become a priority, or traffic is so bursty that scale-to-zero beats ~$1-2/mo always-on RAM (it does not at this scale).
- -> **Bigger Railway Postgres + HNSW** if: semantic search must use 1024-dim vectors with filtered ANN at low latency and the bit pre-filter recall is insufficient; budget ~+300-400 MB RAM (~$3-4/mo).

## Open items (unverified, need measurement)

1. Idle RSS + page cache of the tuned PG18 Railway service with the real dataset (measure via Railway metrics after first load).
2. Exact-search latency for halfvec(384/1024) and bit(1024)+re-rank at 99k rows in a 256 MB container.
3. Wake latency of a serverless Railway DB (not documented; recommendation avoids depending on it).
4. Whether `pg_available_extensions` on a freshly provisioned template service lists `vector` (image source says yes; docs page says no).
5. Real on-disk size of the relational data (needed to finalize volume cost; estimate 1-2 GB).
