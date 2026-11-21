ALTER TYPE "public"."english_policy" ADD VALUE 'source_provided_and_machine_allowed';--> statement-breakpoint

-- public_translations (section 11.3, owner decision 2026-11-21): reviewed English always; source-provided English where
-- the work's policy allows it; machine English (state machine_unreviewed) only under the new policy. Each row keeps its
-- state, source, translator and model so the page labels and credits it. unknown_provenance is never public: it
-- cannot be credited. The policy is compared as text because the migrator applies every pending migration in one
-- transaction, and an enum value added in a transaction cannot be used as an enum literal before it commits.
CREATE OR REPLACE VIEW "public_translations" AS
SELECT t.*
FROM translations t
JOIN public_hadiths h ON h.id = t.hadith_id
JOIN collection_rights r ON r.collection_id = h.collection_id AND r.retired_at IS NULL
WHERE t.retired_at IS NULL
  AND t.quality_status = 'complete'
  AND t.arabic_sha256 = h.arabic_sha256
  AND (t.state IN ('human_verified', 'source_verified')
       OR (t.state = 'source_provided'
           AND r.english_policy::text IN ('source_provided_allowed', 'source_provided_and_machine_allowed'))
       OR (t.state = 'machine_unreviewed'
           AND r.english_policy::text = 'source_provided_and_machine_allowed'));
