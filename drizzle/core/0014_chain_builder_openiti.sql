ALTER TYPE "public"."mention_candidate_basis" ADD VALUE 'named_in_opening_isnad';--> statement-breakpoint
ALTER TABLE "chain_mentions" ADD COLUMN "inherited_from_mention_id" text;--> statement-breakpoint
-- Chain builder, OpenITI works (src/db/AGENTS.md §Chain builder). Expand only: one nullable column and one enum value
-- above; public_chain_links appends inherited_from_mention_id (CREATE OR REPLACE appends, dependents untouched);
-- public_chain_mention_candidates_v2 counts the new basis as a tier basis. The enum value is new in this transaction, so
-- bases are compared as text.
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
       m.inherited_from_mention_id
FROM chain_mentions m
JOIN chains c ON c.id = m.chain_id AND c.retired_at IS NULL
JOIN public_hadiths h ON h.id = m.hadith_id
LEFT JOIN narrators link
       ON link.id = m.narrator_id
      AND link.retired_at IS NULL
      AND m.resolution IN ('source_index', 'human_verified', 'derived_relation_verified')
WHERE m.retired_at IS NULL;
--> statement-breakpoint
CREATE OR REPLACE VIEW "public_chain_mention_candidates_v2" AS
SELECT l.id                                               AS mention_id,
       l.chain_id,
       l.hadith_id,
       c.narrator_id,
       c.basis,
       c.detail,
       c.source_ref,
       c.source_assertion_origin,
       (c.basis::text IN ('source_index_confirmed_by_text', 'source_hadith_kg_confirmed_by_text',
                          'source_riwayat_confirmed_by_text', 'imam_kunya_convention', 'named_in_opening_isnad')
        AND n.placeholder_reason IS NULL
        AND coalesce(c.source_assertion_origin, '') <> 'riwayat_automatic_linking'
        AND p.label_reason IS NULL)                       AS tier_basis
FROM public_chain_links l
JOIN chain_mention_candidates c ON c.mention_id = l.id AND c.retired_at IS NULL
JOIN narrators n ON n.id = c.narrator_id AND n.retired_at IS NULL
LEFT JOIN narrator_source_profiles p ON p.narrator_id = n.id AND p.retired_at IS NULL
UNION ALL
SELECT l.id,
       l.chain_id,
       l.hadith_id,
       d.target_narrator_id,
       'reviewer_decision'::mention_candidate_basis,
       d.decision_kind::text,
       NULL,
       NULL,
       true
FROM public_chain_links l
JOIN chain_mentions m ON m.id = l.id
JOIN narrator_surface_decisions d
  ON d.id = m.decision_id AND d.retired_at IS NULL AND d.target_narrator_id IS NOT NULL
JOIN narrators n ON n.id = d.target_narrator_id AND n.retired_at IS NULL;
