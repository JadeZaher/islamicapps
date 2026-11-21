-- Extensions the core schema needs before any table or index (section 2.7). Idempotent.
-- pg_trgm: trigram GIN indexes for Arabic, title, category and name search (section 7.1).
-- unaccent: the loader computes narrators.name_en_folded = lower(unaccent(name_en)) (section 7.3).
-- pgvector ("vector") is NOT created here: it belongs to the step 11 migration with hadith_embeddings.
CREATE EXTENSION IF NOT EXISTS pg_trgm;
--> statement-breakpoint
CREATE EXTENSION IF NOT EXISTS unaccent;
