-- public_translations (owner decision 2026-11-22): machine English is shown only with a recorded model and recorded provenance
-- (journal, prompt, provider, time), on top of 0009's hash, quality and policy gates. A machine row without them is held back.
-- Additive: same columns, same body, one more condition on the machine branch.
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
           AND r.english_policy::text = 'source_provided_and_machine_allowed'
           AND t.model IS NOT NULL
           AND t.provenance_source IS NOT NULL));
