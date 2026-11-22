ALTER TABLE "chains" ADD COLUMN "structure_status" text;--> statement-breakpoint
ALTER TABLE "chains" ADD COLUMN "structure_reasons" text[];--> statement-breakpoint
ALTER TABLE "chains" ADD CONSTRAINT "chains_structure_status_check" CHECK ("chains"."structure_status" is null or ("chains"."structure_status" = 'checked_by_rule' and "chains"."structure_reasons" is null) or ("chains"."structure_status" = 'uncertain' and cardinality("chains"."structure_reasons") > 0));
--> statement-breakpoint
-- Chain structure gate (src/db/AGENTS.md §Chain structure gate). Expand only: chains.structure_status and structure_reasons
-- above; public_chain_links appends chain_structure_status and chain_structure_reasons (CREATE OR REPLACE appends);
-- narrator_transmissions is recreated with the 0015 body plus one guard: an uncertain chain never forms a pair.
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
       CASE WHEN link.id IS NOT NULL THEN m.confidence END           AS confidence,
       m.name_latin,
       m.name_latin_basis,
       m.name_latin_narrator_id,
       CASE WHEN link.id IS NOT NULL THEN m.extraction_method END    AS standing_basis,
       m.identity_withheld_reason,
       m.inherited_from_mention_id,
       c.suspension                                                  AS chain_suspension,
       c.missing_link_after                                          AS chain_missing_link_after,
       c.structure_status                                            AS chain_structure_status,
       c.structure_reasons                                           AS chain_structure_reasons
FROM chain_mentions m
JOIN chains c ON c.id = m.chain_id AND c.retired_at IS NULL
JOIN public_hadiths h ON h.id = m.hadith_id
LEFT JOIN narrators link
       ON link.id = m.narrator_id
      AND link.retired_at IS NULL
      AND m.resolution IN ('source_index', 'human_verified', 'derived_relation_verified')
WHERE m.retired_at IS NULL;
--> statement-breakpoint
DROP MATERIALIZED VIEW "narrator_transmissions";
--> statement-breakpoint
CREATE MATERIALIZED VIEW "narrator_transmissions" AS
WITH standing AS (
  SELECT m.chain_id, m.hadith_id, m.position, m.narrator_id, m.confidence, m.extraction_method, m.resolution_basis
  FROM chain_mentions m
  JOIN chains c ON c.id = m.chain_id AND c.retired_at IS NULL
    -- 0017: only a chain whose structure a tested rule stands behind forms pairs (NULL: a row loaded before the gate)
    AND c.structure_status IS DISTINCT FROM 'uncertain'
  WHERE m.retired_at IS NULL
    AND m.narrator_id IS NOT NULL
    AND m.resolution IN ('source_index', 'human_verified', 'derived_relation_verified')
    -- 0015: an unnamed transmitter or a back-reference is a label, never one side of a pair
    AND m.link_kind NOT IN ('anonymous', 'not_a_narrator')
),
seams AS (
  SELECT chain_id, min(position) AS first_pos, max(position) AS last_pos
  FROM standing
  GROUP BY chain_id, narrator_id
  HAVING count(*) > 1
),
pairs AS (
  SELECT a.narrator_id AS student_id, b.narrator_id AS teacher_id,
         a.hadith_id, a.position AS student_pos, b.position AS teacher_pos,
         least(a.confidence, b.confidence) AS confidence,
         a.extraction_method
  FROM standing a
  JOIN standing b ON b.chain_id = a.chain_id AND b.position = a.position + 1
  -- 0015: never across an unnamed transmitter (adjacency already implies it; kept explicit for any later read)
  WHERE ((a.resolution_basis = 'source_index' AND b.resolution_basis = 'source_index')
      OR (a.resolution_basis = 'human_decision' AND b.resolution_basis = 'human_decision'))
    AND NOT EXISTS (SELECT 1 FROM seams s
                    WHERE s.chain_id = a.chain_id AND s.first_pos <= a.position AND s.last_pos >= b.position)
),
grouped AS (
  SELECT p.student_id, p.teacher_id,
         count(DISTINCT p.hadith_id)::int                                 AS hadith_count,
         -- one occurrence per report position pair, not per tahwil or co-transmitter branch
         count(DISTINCT (p.hadith_id, p.student_pos, p.teacher_pos))::int AS occurrence_count,
         max(p.confidence)                                                AS confidence,
         array_agg(DISTINCT coalesce(p.extraction_method, 'unspecified')) AS extraction_methods
  FROM pairs p
  GROUP BY p.student_id, p.teacher_id
)
SELECT g.student_id, g.teacher_id, g.hadith_count, g.occurrence_count, g.confidence, g.extraction_methods,
       CASE
         WHEN r.rule IS NOT NULL AND r.attested                            THEN 'disputed'
         WHEN r.rule IS NOT NULL                                           THEN 'impossible'
         WHEN sl.disputed OR tl.disputed                                   THEN 'disputed'
         WHEN nullif(sl.birth_max, 0) <= nullif(tl.death_min, 0)           THEN 'plausible'
         ELSE 'unknown'
       END                                                                 AS temporal_plausibility,
       CASE
         WHEN r.rule IS NOT NULL AND r.attested
           THEN 'the lexicon lists this teacher, but its years say ' || r.rule
         WHEN r.rule IS NOT NULL THEN r.rule || ', on the most permissive bounds'
         WHEN sl.disputed OR tl.disputed THEN 'verified lifespan claims conflict'
       END                                                                 AS temporal_reason
FROM grouped g
LEFT JOIN narrator_lifespans sl ON sl.narrator_id = g.student_id
LEFT JOIN narrator_lifespans tl ON tl.narrator_id = g.teacher_id
CROSS JOIN LATERAL (
  SELECT CASE
           WHEN nullif(sl.birth_min, 0) > nullif(tl.death_max, 0)      THEN 'student born after teacher died'
           WHEN nullif(tl.birth_min, 0) > nullif(sl.death_max, 0)      THEN 'teacher born after student died'
           WHEN nullif(tl.death_min, 0) > nullif(sl.death_max, 0) + 60 THEN 'teacher died more than 60 years after student'
         END AS rule,
         EXISTS (SELECT 1 FROM narrator_teachers t
                 WHERE t.student_id = g.student_id AND t.teacher_id = g.teacher_id AND t.retired_at IS NULL) AS attested
) r;
--> statement-breakpoint
CREATE UNIQUE INDEX "narrator_transmissions_pair_key" ON "narrator_transmissions" ("student_id", "teacher_id");
--> statement-breakpoint
CREATE INDEX "narrator_transmissions_teacher_id_idx" ON "narrator_transmissions" ("teacher_id");
