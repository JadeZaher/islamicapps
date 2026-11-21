-- Hand-written views (sections 5.5, 5.9, 11.3). drizzle-kit only knows them as `.existing()` declarations.
-- "Verified link" everywhere below: resolution in (exact_registry, human_verified,
-- derived_relation_verified) AND a live narrator_id. source_index joins the list only if the owner
-- approves it (section 14 question 1). Keep this predicate identical in 0004_functions.sql.

-- narrator_lifespans: Hijri lifespan ranges, one row per live narrator with at least one bound.
-- Pre-assertions shape (section 5.5): biographical_assertions has not shipped, so claim_count is 0,
-- disputed is false, and each point year is both bounds. Death prefers a published bio whose
-- citation is live and reviewed (section 5.8), else the lexicon; birth comes only from the lexicon.
-- basis is the weakest source any bound came from. Redefined by the migration that creates
-- biographical_assertions.
CREATE VIEW "narrator_lifespans" AS
WITH curated_death AS (
  SELECT b.narrator_id, b.death_year_hijri
  FROM narrator_bios b
  JOIN citations c ON c.id = b.citation_id
  WHERE b.retired_at IS NULL
    AND b.status = 'published'
    AND b.death_year_hijri IS NOT NULL
    AND c.retired_at IS NULL
    AND c.review_state IN ('human_verified', 'source_verified')
),
bounds AS (
  SELECT n.id AS narrator_id,
         p.birth_year_hijri AS lexicon_birth,
         cd.death_year_hijri AS curated_death,
         CASE WHEN cd.death_year_hijri IS NULL THEN p.death_year_hijri END AS lexicon_death
  FROM narrators n
  LEFT JOIN narrator_lexicon_profiles p ON p.narrator_id = n.id AND p.retired_at IS NULL
  LEFT JOIN curated_death cd ON cd.narrator_id = n.id
  WHERE n.retired_at IS NULL
)
SELECT narrator_id,
       lexicon_birth                               AS birth_min,
       lexicon_birth                               AS birth_max,
       coalesce(curated_death, lexicon_death)      AS death_min,
       coalesce(curated_death, lexicon_death)      AS death_max,
       0                                           AS claim_count,
       false                                       AS disputed,
       CASE
         WHEN lexicon_birth IS NOT NULL OR lexicon_death IS NOT NULL THEN 'lexicon_unverified'
         ELSE 'curated'
       END                                         AS basis
FROM bounds
WHERE lexicon_birth IS NOT NULL OR curated_death IS NOT NULL OR lexicon_death IS NOT NULL;
--> statement-breakpoint

-- narrator_transmissions: verbatim from section 5.5. Only consecutive verified links; a pair counts
-- only inside an atomically resolved chain or when both links are human decisions (question 11).
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
    AND a.resolution IN ('exact_registry', 'human_verified', 'derived_relation_verified')
    AND b.resolution IN ('exact_registry', 'human_verified', 'derived_relation_verified')
    AND ((c.resolved AND a.resolution_basis = 'report_atomic' AND b.resolution_basis = 'report_atomic')
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
--> statement-breakpoint

-- published_historical_events (section 5.9): the check-constraint gate, enforced again on read,
-- plus a live, reviewed citation when citation_id is set.
CREATE VIEW "published_historical_events" AS
SELECT e.*,
       e.start_year_hijri                              AS event_start,
       coalesce(e.end_year_hijri, e.start_year_hijri)  AS event_end
FROM historical_events e
WHERE e.retired_at IS NULL
  AND e.start_year_hijri IS NOT NULL
  AND e.publication_ready
  AND e.verification_status IN ('human_verified', 'source_verified')
  AND nullif(trim(e.citation_source), '') IS NOT NULL
  AND (nullif(trim(e.citation_locator), '') IS NOT NULL OR nullif(trim(e.citation_url), '') IS NOT NULL)
  AND (e.citation_id IS NULL OR EXISTS (
        SELECT 1 FROM citations c
        WHERE c.id = e.citation_id
          AND c.retired_at IS NULL
          AND c.review_state IN ('human_verified', 'source_verified')));
--> statement-breakpoint

-- public_hadiths (section 11.3): live, not excluded, has Arabic, in a live rights-cleared work, and
-- the current dataset version is publicly servable (release-class, or a recorded owner override).
CREATE VIEW "public_hadiths" AS
SELECT h.*
FROM hadiths h
JOIN collections col ON col.id = h.collection_id AND col.retired_at IS NULL
JOIN collection_rights r ON r.collection_id = h.collection_id AND r.retired_at IS NULL
WHERE h.retired_at IS NULL
  AND NOT h.quality_excluded
  AND h.source_text_status <> 'missing'
  AND r.rights_status = 'cleared'
  AND EXISTS (
        SELECT 1 FROM dataset_versions v
        WHERE v.is_current
          AND v.load_status = 'complete'
          AND (v.release_class = 'release' OR v.public_override_by IS NOT NULL));
--> statement-breakpoint

-- public_translations (section 11.3): reviewed English on a public hadith, bound to its exact Arabic.
-- source_provided only where the work's english_policy allows it. Never translation_candidates.
CREATE VIEW "public_translations" AS
SELECT t.*
FROM translations t
JOIN public_hadiths h ON h.id = t.hadith_id
JOIN collection_rights r ON r.collection_id = h.collection_id
WHERE t.retired_at IS NULL
  AND t.quality_status = 'complete'
  AND t.arabic_sha256 = h.arabic_sha256
  AND (t.state IN ('human_verified', 'source_verified')
       OR (t.state = 'source_provided' AND r.english_policy = 'source_provided_allowed'));
--> statement-breakpoint

-- public_chain_links (section 11.3, contract 9.4): every live mention of a public hadith, so the
-- isnad always reads as written; narrator_id and confidence only on verified links.
CREATE VIEW "public_chain_links" AS
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
      AND m.resolution IN ('exact_registry', 'human_verified', 'derived_relation_verified')
WHERE m.retired_at IS NULL;
