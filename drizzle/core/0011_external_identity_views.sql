-- External identity, Latin names and the extended machine-reviewed tier (0010; src/db/AGENTS.md §External identity).
-- Expand only: public_chain_links gains four columns at the end; public_chain_mention_candidates keeps exactly the
-- pre-0010 bases, so a build that predates them reads only what it understands; public_chain_mention_candidates_v2
-- carries every basis. Enum values added in 0010 run in this same transaction, so bases are compared as text.
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
       CASE WHEN link.id IS NOT NULL THEN m.extraction_method END    AS standing_basis
FROM chain_mentions m
JOIN chains c ON c.id = m.chain_id AND c.retired_at IS NULL
JOIN public_hadiths h ON h.id = m.hadith_id
LEFT JOIN narrators link
       ON link.id = m.narrator_id
      AND link.retired_at IS NULL
      AND m.resolution IN ('source_index', 'human_verified', 'derived_relation_verified')
WHERE m.retired_at IS NULL;
--> statement-breakpoint
CREATE OR REPLACE VIEW "public_chain_mention_candidates" AS
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
WHERE c.basis::text IN ('name_exact', 'name_spelling_fold', 'name_kunya_only', 'source_index',
                        'source_index_confirmed_by_text')
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
-- tier_basis: a candidate that can carry the machine-reviewed tier by itself: a source claim confirmed by the text that
-- is not Riwayat's automatic linker and not a label-like record, an Imam's conventional kunya, or a reviewer decision.
-- "Two sources agree" is a pair of candidates, read from public_chain_links.standing_basis.
CREATE VIEW "public_chain_mention_candidates_v2" AS
SELECT l.id                                               AS mention_id,
       l.chain_id,
       l.hadith_id,
       c.narrator_id,
       c.basis,
       c.detail,
       c.source_ref,
       c.source_assertion_origin,
       (c.basis::text IN ('source_index_confirmed_by_text', 'source_hadith_kg_confirmed_by_text',
                          'source_riwayat_confirmed_by_text', 'imam_kunya_convention')
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
