ALTER TABLE "chain_fix_submissions" ADD COLUMN "tool_version" text;--> statement-breakpoint
ALTER TABLE "chain_fix_submissions" ADD COLUMN "inherited_from" jsonb;--> statement-breakpoint
ALTER TABLE "chain_fixes" ADD COLUMN "disposition" text;--> statement-breakpoint
ALTER TABLE "chain_fix_submissions" ADD CONSTRAINT "chain_fix_submissions_tool_version_check" CHECK ("chain_fix_submissions"."tool_version" is null or "chain_fix_submissions"."tool_version" in ('v3', 'v3_1'));--> statement-breakpoint
ALTER TABLE "chain_fix_submissions" ADD CONSTRAINT "chain_fix_submissions_inherited_from_check" CHECK ("chain_fix_submissions"."inherited_from" is null or jsonb_typeof("chain_fix_submissions"."inherited_from") = 'array');--> statement-breakpoint
ALTER TABLE "chain_fixes" ADD CONSTRAINT "chain_fixes_disposition_check" CHECK ("chain_fixes"."disposition" is null or ("chain_fixes"."disposition" = 'no_chain_by_reading' and jsonb_array_length("chain_fixes"."planned" -> 'chains') = 0));--> statement-breakpoint
-- 0021 (first model-read fixes, 2026-11-22; src/db/AGENTS.md §Chain fixes). Additive. A report whose applied fix found no isnad in
-- the text: its chains are retired by the apply, and the page reads this view to say so instead of showing nothing. Only while the
-- fix's latest application is `applied`, its live decision has an effect, it reads the current Arabic and no live chain remains.
CREATE VIEW "public_chain_fix_dispositions" AS
SELECT f.hadith_id,
       f.id                       AS fix_id,
       f.disposition,
       d.state,
       d.models,
       d.runs,
       d.decided_at,
       (d.state = 'accepted')     AS awaiting_final_review
FROM chain_fixes f
JOIN chain_fix_decisions d ON d.fix_id = f.id AND d.retired_at IS NULL AND d.effect IS NOT NULL
JOIN public_hadiths h ON h.id = f.hadith_id AND h.arabic_sha256 = f.arabic_sha256
WHERE f.disposition IS NOT NULL
  AND 'applied' = (SELECT a.action FROM chain_fix_applications a WHERE a.fix_id = f.id ORDER BY a.id DESC LIMIT 1)
  AND NOT EXISTS (SELECT 1 FROM chains c WHERE c.hadith_id = f.hadith_id AND c.retired_at IS NULL);
--> statement-breakpoint
-- What a mention of a model-read chain is beyond a name written in the chain, from the fix's own plan: `imam_in_text` (the source
-- named in the report text, read as the last link) and `inherited` (repeats the earlier report's written mention). The page labels them.
CREATE VIEW "public_chain_fix_mention_kinds" AS
SELECT pm ->> 'id'          AS mention_id,
       c.id                 AS chain_id,
       c.hadith_id,
       pm ->> 'reader_kind' AS reader_kind
FROM chains c
JOIN chain_fixes f ON f.id = c.chain_fix_id
JOIN public_hadiths h ON h.id = c.hadith_id AND h.arabic_sha256 = f.arabic_sha256
CROSS JOIN LATERAL jsonb_array_elements(f.planned -> 'chains') pc
CROSS JOIN LATERAL jsonb_array_elements(pc -> 'mentions') pm
WHERE c.retired_at IS NULL
  AND pc ->> 'id' = c.id
  AND pm ->> 'reader_kind' IN ('imam_in_text', 'inherited');
