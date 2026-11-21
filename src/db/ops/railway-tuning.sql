-- Low-memory server settings (data-architecture.md section 2.4). Applied by an operator with
-- `npx tsx src/db/ops/apply-tuning.ts --database production --confirm-production` (ALTER SYSTEM cannot run in a
-- transaction, so this is never a migration). Server-wide: the development and production databases share this server.
-- Settings marked "restart" take effect only when the Postgres service is restarted; the rest on pg_reload_conf().
-- Never set shared_preload_libraries here: the image's wrapper owns that list. See src/db/AGENTS.md §Server tuning.
alter system set shared_buffers = '64MB';                 -- restart
-- 40, not the design's 20: the development database lives on this server (decision 22), so its test suites,
-- fixture pools and loader share the budget with the production app (2 x 5 during a deploy) and the migrator.
alter system set max_connections = 40;                    -- restart
alter system set work_mem = '4MB';
alter system set maintenance_work_mem = '64MB';
alter system set autovacuum_work_mem = '32MB';
alter system set effective_cache_size = '256MB';
alter system set max_parallel_workers_per_gather = 1;
alter system set autovacuum_max_workers = 2;              -- restart before PostgreSQL 18; reload on 18 (bounded by autovacuum_worker_slots)
alter system set max_wal_size = '512MB';
alter system set jit = off;
alter system set huge_pages = off;                        -- restart
