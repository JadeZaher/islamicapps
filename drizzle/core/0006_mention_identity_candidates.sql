CREATE TYPE "public"."mention_candidate_basis" AS ENUM('name_exact', 'name_spelling_fold', 'name_kunya_only', 'source_index', 'source_index_confirmed_by_text', 'reviewer_decision');--> statement-breakpoint
CREATE TYPE "public"."narrator_placeholder_reason" AS ENUM('unidentified_shaykh_marker', 'no_arabic_name', 'bare_single_token_name', 'kunya_only_name');--> statement-breakpoint
CREATE TABLE "chain_mention_candidates" (
	"id" text PRIMARY KEY NOT NULL,
	"mention_id" text NOT NULL,
	"hadith_id" text NOT NULL,
	"narrator_id" text NOT NULL,
	"basis" "mention_candidate_basis" NOT NULL,
	"detail" text,
	"source_position" integer,
	"first_seen_dataset_version_id" text NOT NULL,
	"changed_in_dataset_version_id" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_in_dataset_version_id" text,
	CONSTRAINT "chain_mention_candidates_mention_narrator_basis_key" UNIQUE("mention_id","narrator_id","basis"),
	CONSTRAINT "chain_mention_candidates_pipeline_basis_check" CHECK ("chain_mention_candidates"."basis" <> 'reviewer_decision'),
	CONSTRAINT "chain_mention_candidates_source_position_check" CHECK (("chain_mention_candidates"."basis" in ('source_index', 'source_index_confirmed_by_text')) = ("chain_mention_candidates"."source_position" is not null))
);
--> statement-breakpoint
ALTER TABLE "narrators" ADD COLUMN "placeholder_reason" "narrator_placeholder_reason";--> statement-breakpoint
ALTER TABLE "chain_mention_candidates" ADD CONSTRAINT "chain_mention_candidates_mention_id_fk" FOREIGN KEY ("mention_id") REFERENCES "public"."chain_mentions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chain_mention_candidates" ADD CONSTRAINT "chain_mention_candidates_hadith_id_fk" FOREIGN KEY ("hadith_id") REFERENCES "public"."hadiths"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chain_mention_candidates" ADD CONSTRAINT "chain_mention_candidates_narrator_id_fk" FOREIGN KEY ("narrator_id") REFERENCES "public"."narrators"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chain_mention_candidates" ADD CONSTRAINT "chain_mention_candidates_first_seen_dataset_version_id_fk" FOREIGN KEY ("first_seen_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chain_mention_candidates" ADD CONSTRAINT "chain_mention_candidates_changed_in_dataset_version_id_fk" FOREIGN KEY ("changed_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chain_mention_candidates" ADD CONSTRAINT "chain_mention_candidates_retired_in_dataset_version_id_fk" FOREIGN KEY ("retired_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
CREATE INDEX "chain_mention_candidates_hadith_id_idx" ON "chain_mention_candidates" USING btree ("hadith_id");--> statement-breakpoint
CREATE INDEX "chain_mention_candidates_narrator_id_idx" ON "chain_mention_candidates" USING btree ("narrator_id");
--> statement-breakpoint

-- Hand-written below (owner decisions 2026-11-21; see src/db/AGENTS.md "Identity candidates").
-- Verified link now: resolution in (source_index, human_verified, derived_relation_verified) AND a live narrator_id.
-- exact_registry is no longer verified: a name match is a candidate in chain_mention_candidates. The loader writes
-- narrator_id only for an uncontested source_index_confirmed_by_text candidate; decisions write the rest.
-- Same predicate in public_chain_links and twice in refresh_publication_facets.

CREATE OR REPLACE VIEW "public_chain_links" AS
SELECT m.id,
       m.chain_id,
       m.hadith_id,
       c.branch,
       m.position,
       m.surface_ar,
       m.link_kind,
       m.resolution,
       (link.id IS NOT NULL)                                         AS is_link,
       link.id                                                       AS narrator_id,
       CASE WHEN link.id IS NOT NULL THEN m.confidence END           AS confidence
FROM chain_mentions m
JOIN chains c ON c.id = m.chain_id AND c.retired_at IS NULL
JOIN public_hadiths h ON h.id = m.hadith_id
LEFT JOIN narrators link
       ON link.id = m.narrator_id
      AND link.retired_at IS NULL
      AND m.resolution IN ('source_index', 'human_verified', 'derived_relation_verified')
WHERE m.retired_at IS NULL;
--> statement-breakpoint

-- public_chain_mention_candidates: every identity candidate of a public mention, with its basis, so a reader sees
-- all matches and where each comes from. Reviewer decisions appear as basis reviewer_decision (read from the
-- curation table, never stored in the pipeline table). verified_basis marks the bases that may set a verified link.
CREATE VIEW "public_chain_mention_candidates" AS
SELECT l.id                                               AS mention_id,
       l.chain_id,
       l.hadith_id,
       c.narrator_id,
       c.basis,
       c.detail,
       (c.basis = 'source_index_confirmed_by_text')       AS verified_basis
FROM public_chain_links l
JOIN chain_mention_candidates c ON c.mention_id = l.id AND c.retired_at IS NULL
JOIN narrators n ON n.id = c.narrator_id AND n.retired_at IS NULL
UNION ALL
SELECT l.id,
       l.chain_id,
       l.hadith_id,
       d.target_narrator_id,
       'reviewer_decision'::mention_candidate_basis,
       d.decision_kind::text,
       true
FROM public_chain_links l
JOIN chain_mentions m ON m.id = l.id
JOIN narrator_surface_decisions d
  ON d.id = m.decision_id AND d.retired_at IS NULL AND d.target_narrator_id IS NOT NULL
JOIN narrators n ON n.id = d.target_narrator_id AND n.retired_at IS NULL;
--> statement-breakpoint

CREATE OR REPLACE FUNCTION "refresh_publication_facets"(hadith_ids text[])
RETURNS integer
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
DECLARE
  changed_chains integer;
  changed_hadiths integer;
BEGIN
  -- Verified link: same predicate as public_chain_links (0006).
  WITH chain_counts AS (
    SELECT c.id,
           count(n.id)::integer AS verified
    FROM chains c
    LEFT JOIN chain_mentions m
           ON m.chain_id = c.id AND m.retired_at IS NULL
    LEFT JOIN narrators n
           ON n.id = m.narrator_id
          AND n.retired_at IS NULL
          AND m.resolution IN ('source_index', 'human_verified', 'derived_relation_verified')
    WHERE c.hadith_id = ANY (hadith_ids)
    GROUP BY c.id
  )
  UPDATE chains c
     SET verified_link_count = cc.verified
    FROM chain_counts cc
   WHERE c.id = cc.id
     AND c.verified_link_count IS DISTINCT FROM cc.verified;
  GET DIAGNOSTICS changed_chains = ROW_COUNT;

  WITH mention_counts AS (
    SELECT c.hadith_id,
           count(m.id)::integer AS mentions,
           count(n.id)::integer AS verified
    FROM chains c
    LEFT JOIN chain_mentions m
           ON m.chain_id = c.id AND m.retired_at IS NULL
    LEFT JOIN narrators n
           ON n.id = m.narrator_id
          AND n.retired_at IS NULL
          AND m.resolution IN ('source_index', 'human_verified', 'derived_relation_verified')
    WHERE c.hadith_id = ANY (hadith_ids)
      AND c.retired_at IS NULL
    GROUP BY c.hadith_id
  ),
  facets AS (
    SELECT h.id,
           CASE
             WHEN coalesce(h.text_ar, '') !~ '[^[:space:]]' THEN 'missing'
             WHEN nullif(trim(h.arabic_sha256), '') IS NOT NULL
              AND nullif(trim(h.source_record_id), '') IS NOT NULL
              AND (nullif(trim(h.url), '') IS NOT NULL OR nullif(trim(h.page_ref), '') IS NOT NULL)
               THEN 'present_locator_bound'
             ELSE 'present'
           END::source_text_status AS source_text_status,
           CASE
             WHEN mc.hadith_id IS NULL THEN
               CASE WHEN EXISTS (
                      SELECT 1 FROM chain_absence_dispositions d
                      WHERE d.retired_at IS NULL
                        AND (d.hadith_id = h.id OR d.collection_id = h.collection_id))
                    THEN 'absent_in_source' ELSE 'extraction_failed' END
             WHEN mc.mentions > 0 AND mc.verified = mc.mentions THEN 'complete'
             WHEN mc.verified = 0 THEN 'unresolved'
             ELSE 'partial'
           END::chain_status AS chain_status,
           CASE
             WHEN EXISTS (
                    SELECT 1 FROM hadith_assessments a
                    WHERE a.hadith_id = h.id AND a.retired_at IS NULL
                      AND a.kind IN ('cited_ruling', 'compiler_statement'))
               THEN 'cited_assessments'
             WHEN EXISTS (
                    SELECT 1 FROM hadith_assessments a
                    WHERE a.hadith_id = h.id AND a.retired_at IS NULL
                      AND a.kind = 'compiler_criterion')
               THEN 'compiler_criterion'
             ELSE 'none_recorded'
           END::grading_status AS grading_status
    FROM hadiths h
    LEFT JOIN mention_counts mc ON mc.hadith_id = h.id
    WHERE h.id = ANY (hadith_ids)
  )
  UPDATE hadiths h
     SET source_text_status = f.source_text_status,
         chain_status = f.chain_status,
         grading_status = f.grading_status
    FROM facets f
   WHERE h.id = f.id
     AND (h.source_text_status, h.chain_status, h.grading_status)
         IS DISTINCT FROM (f.source_text_status, f.chain_status, f.grading_status);
  GET DIAGNOSTICS changed_hadiths = ROW_COUNT;

  RETURN changed_chains + changed_hadiths;
END;
$$;
--> statement-breakpoint
REVOKE ALL ON FUNCTION "refresh_publication_facets"(text[]) FROM PUBLIC;
--> statement-breakpoint

-- narrator_transmissions: verified-only, from confirmed source-index links or human decisions. A pair counts only
-- when both neighbours are verified on the same footing: both source_index (narrator_id is written only for an
-- uncontested source_index_confirmed_by_text candidate, whose report-level agreement class already checked the
-- branch shape against the Arabic) or both human_decision. A name match never creates a pair.
DROP MATERIALIZED VIEW "narrator_transmissions";
--> statement-breakpoint
CREATE MATERIALIZED VIEW "narrator_transmissions" AS
WITH pairs AS (
  SELECT a.narrator_id AS student_id, b.narrator_id AS teacher_id,
         a.hadith_id, a.position AS student_pos, b.position AS teacher_pos,
         least(a.confidence, b.confidence) AS confidence,
         a.extraction_method
  FROM chain_mentions a
  JOIN chain_mentions b ON b.chain_id = a.chain_id AND b.position = a.position + 1
  JOIN chains c ON c.id = a.chain_id
  WHERE a.retired_at IS NULL AND b.retired_at IS NULL AND c.retired_at IS NULL
    AND a.narrator_id IS NOT NULL AND b.narrator_id IS NOT NULL
    AND a.resolution IN ('source_index', 'human_verified', 'derived_relation_verified')
    AND b.resolution IN ('source_index', 'human_verified', 'derived_relation_verified')
    AND ((a.resolution_basis = 'source_index' AND b.resolution_basis = 'source_index')
      OR (a.resolution_basis = 'human_decision' AND b.resolution_basis = 'human_decision'))
)
SELECT p.student_id, p.teacher_id,
       count(DISTINCT p.hadith_id)::int                                    AS hadith_count,
       -- one occurrence per report position pair, not per tahwil or co-transmitter branch
       count(DISTINCT (p.hadith_id, p.student_pos, p.teacher_pos))::int    AS occurrence_count,
       max(p.confidence)                                                   AS confidence,
       array_agg(DISTINCT coalesce(p.extraction_method, 'unspecified'))    AS extraction_methods,
       -- guardrail G-6, same rule as temporal-plausibility.ts, on ranges
       CASE
         WHEN sl.birth_min > tl.death_max                                  THEN 'impossible'
         WHEN sl.disputed OR tl.disputed                                   THEN 'disputed'
         WHEN sl.birth_max IS NOT NULL AND tl.death_min IS NOT NULL
          AND sl.birth_max <= tl.death_min                                 THEN 'plausible'
         ELSE 'unknown'
       END                                                                 AS temporal_plausibility,
       CASE
         WHEN sl.birth_min > tl.death_max THEN 'student born after teacher died, on the most permissive bounds'
         WHEN sl.disputed OR tl.disputed  THEN 'verified lifespan claims conflict'
         ELSE NULL
       END                                                                 AS temporal_reason
FROM pairs p
LEFT JOIN narrator_lifespans sl ON sl.narrator_id = p.student_id
LEFT JOIN narrator_lifespans tl ON tl.narrator_id = p.teacher_id
GROUP BY p.student_id, p.teacher_id,
         sl.birth_min, sl.birth_max, sl.disputed, tl.death_min, tl.death_max, tl.disputed;
--> statement-breakpoint
CREATE UNIQUE INDEX "narrator_transmissions_pair_key" ON "narrator_transmissions" ("student_id", "teacher_id");
--> statement-breakpoint
CREATE INDEX "narrator_transmissions_teacher_id_idx" ON "narrator_transmissions" ("teacher_id");