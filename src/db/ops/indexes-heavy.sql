-- Heavy index builds (section 2.6, 7.1). NOT a migration: CREATE INDEX CONCURRENTLY cannot run inside the
-- drizzle migrator's single transaction. Run by an operator in a load window, after the first bundle load,
-- as the schema owner, outside any transaction block (psql -f, autocommit on). Record the built size in
-- data-architecture.md section 2.8. src/db/verify.ts accepts these indexes as optional.
-- Session-only; 128MB is a chosen value sized for the 250-450 MB memory budget (section 1.4), not a doc figure.
SET maintenance_work_mem = '128MB';

-- Arabic text search: trigram GIN over the project-normalized Arabic (section 7.2).
CREATE INDEX CONCURRENTLY IF NOT EXISTS "hadiths_text_ar_normalized_trgm_idx"
  ON "hadiths" USING gin ("text_ar_normalized" gin_trgm_ops);

RESET maintenance_work_mem;

-- Size check:
-- SELECT pg_size_pretty(pg_relation_size('hadiths_text_ar_normalized_trgm_idx'));
