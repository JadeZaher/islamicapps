-- Derived-column functions (sections 4.1, 11.2). apply_decision(unit_id) is deferred to the step that
-- ships decision replay (see src/db/AGENTS.md "Deferred"). Lock keys match src/db/advisory-locks.ts.

-- refresh_publication_facets: recompute chains.verified_link_count and the three hadith facets for
-- the given hadiths. Every update is guarded with IS DISTINCT FROM so unchanged rows are not rewritten.
-- Returns the number of chain and hadith rows changed.
CREATE OR REPLACE FUNCTION "refresh_publication_facets"(hadith_ids text[])
RETURNS integer
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
DECLARE
  changed_chains integer;
  changed_hadiths integer;
BEGIN
  -- Verified link: same predicate as public_chain_links in 0003_views.sql.
  WITH chain_counts AS (
    SELECT c.id,
           count(n.id)::integer AS verified
    FROM chains c
    LEFT JOIN chain_mentions m
           ON m.chain_id = c.id AND m.retired_at IS NULL
    LEFT JOIN narrators n
           ON n.id = m.narrator_id
          AND n.retired_at IS NULL
          AND m.resolution IN ('exact_registry', 'human_verified', 'derived_relation_verified')
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
          AND m.resolution IN ('exact_registry', 'human_verified', 'derived_relation_verified')
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

-- refresh_network: refresh narrator_transmissions concurrently, one refresh at a time. Skipped (returns
-- false) while another session holds the data-write lock (a load or a migration) or another refresh runs.
-- SECURITY DEFINER so the app role can refresh a view it does not own (section 4.1).
CREATE OR REPLACE FUNCTION "refresh_network"()
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
  IF NOT pg_try_advisory_xact_lock_shared(4741100001) THEN
    RETURN false;
  END IF;
  IF NOT pg_try_advisory_xact_lock(4741100002) THEN
    RETURN false;
  END IF;
  PERFORM set_config('work_mem', '32MB', true);
  REFRESH MATERIALIZED VIEW CONCURRENTLY narrator_transmissions;
  UPDATE dataset_versions SET network_refreshed_at = now() WHERE is_current;
  RETURN true;
END;
$$;
--> statement-breakpoint
REVOKE ALL ON FUNCTION "refresh_network"() FROM PUBLIC;
--> statement-breakpoint
REVOKE ALL ON FUNCTION "refresh_publication_facets"(text[]) FROM PUBLIC;
