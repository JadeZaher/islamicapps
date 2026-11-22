ALTER TABLE "hadiths" ADD COLUMN "sanad_ar" text;--> statement-breakpoint
ALTER TABLE "hadiths" ADD COLUMN "sanad_inherits_from" text;--> statement-breakpoint
ALTER TABLE "hadiths" ADD COLUMN "split_confidence" text;--> statement-breakpoint
ALTER TABLE "hadiths" ADD COLUMN "source_notes" jsonb;--> statement-breakpoint
ALTER TABLE "hadiths" ADD CONSTRAINT "hadiths_split_confidence_check" CHECK ("hadiths"."split_confidence" in ('high', 'low'));--> statement-breakpoint
ALTER TABLE "hadiths" ADD CONSTRAINT "hadiths_source_notes_check" CHECK ("hadiths"."source_notes" is null or jsonb_typeof("hadiths"."source_notes") = 'array');
--> statement-breakpoint
-- Report structure for OpenITI reports (src/db/AGENTS.md §OpenITI extraction fields). Expand only: four nullable columns
-- at the end of hadiths. public_hadiths is `select h.*`, so its column list froze at creation; CREATE OR REPLACE appends
-- the new columns after the existing ones and leaves every dependent view untouched.
CREATE OR REPLACE VIEW "public_hadiths" AS
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
