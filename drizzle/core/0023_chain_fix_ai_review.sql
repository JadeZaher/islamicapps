-- 0023 (2026-11-22, src/db/AGENTS.md §Chain fixes, AI review tier): additive. Reader tools v3_3/v3_4; the AI reviewer's review rows (reviewer
-- vocabulary, outcome, run, packet; a human row still decides alone); decision states awaiting_human and set_aside_by_ai and the AI marks;
-- a correction fix (two reviews) may be accepted without a blind reader; the witness-match table (empty); two views appended.
CREATE TABLE "chain_fix_witness_matches" (
	"id" text PRIMARY KEY NOT NULL,
	"fix_id" text NOT NULL,
	"hadith_id" text NOT NULL,
	"witness" text NOT NULL,
	"locator" text NOT NULL,
	"method" text NOT NULL,
	"matched" boolean NOT NULL,
	"reader_text_sha256" text NOT NULL,
	"note" text NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"created_by" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_by" text NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_by" text,
	CONSTRAINT "chain_fix_witness_matches_text_check" CHECK (btrim("chain_fix_witness_matches"."witness") <> '' and btrim("chain_fix_witness_matches"."locator") <> '' and btrim("chain_fix_witness_matches"."method") <> '' and btrim("chain_fix_witness_matches"."note") <> ''),
	CONSTRAINT "chain_fix_witness_matches_hash_check" CHECK ("chain_fix_witness_matches"."reader_text_sha256" ~ '^[0-9a-f]{64}$')
);
--> statement-breakpoint
ALTER TABLE "chain_fix_decisions" DROP CONSTRAINT "chain_fix_decisions_state_check";--> statement-breakpoint
ALTER TABLE "chain_fix_decisions" DROP CONSTRAINT "chain_fix_decisions_agreement_check";--> statement-breakpoint
ALTER TABLE "chain_fix_reviews" DROP CONSTRAINT "chain_fix_reviews_decision_check";--> statement-breakpoint
ALTER TABLE "chain_fix_submissions" DROP CONSTRAINT "chain_fix_submissions_tool_version_check";--> statement-breakpoint
ALTER TABLE "chain_fix_reviews" ALTER COLUMN "decision" DROP NOT NULL;--> statement-breakpoint
ALTER TABLE "chain_fix_decisions" ADD COLUMN "ai_review" jsonb;--> statement-breakpoint
ALTER TABLE "chain_fix_decisions" ADD COLUMN "ai_disputed" jsonb;--> statement-breakpoint
ALTER TABLE "chain_fix_decisions" ADD COLUMN "ai_corrected" jsonb;--> statement-breakpoint
ALTER TABLE "chain_fix_reviews" ADD COLUMN "review_decision" text;--> statement-breakpoint
ALTER TABLE "chain_fix_reviews" ADD COLUMN "outcome" text;--> statement-breakpoint
ALTER TABLE "chain_fix_reviews" ADD COLUMN "codes_at_review" text[];--> statement-breakpoint
ALTER TABLE "chain_fix_reviews" ADD COLUMN "status_at_review" text;--> statement-breakpoint
ALTER TABLE "chain_fix_reviews" ADD COLUMN "specialist_version" text;--> statement-breakpoint
ALTER TABLE "chain_fix_reviews" ADD COLUMN "run_id" text;--> statement-breakpoint
ALTER TABLE "chain_fix_reviews" ADD COLUMN "pass" integer;--> statement-breakpoint
ALTER TABLE "chain_fix_reviews" ADD COLUMN "packet_path" text;--> statement-breakpoint
ALTER TABLE "chain_fix_reviews" ADD COLUMN "packet_sha256" text;--> statement-breakpoint
ALTER TABLE "chain_fix_reviews" ADD COLUMN "packet_item_id" text;--> statement-breakpoint
ALTER TABLE "chain_fix_reviews" ADD COLUMN "started_at" timestamp with time zone;--> statement-breakpoint
ALTER TABLE "chain_fix_reviews" ADD COLUMN "finished_at" timestamp with time zone;--> statement-breakpoint
ALTER TABLE "chain_fix_reviews" ADD COLUMN "uncertainty" text;--> statement-breakpoint
ALTER TABLE "chain_fix_reviews" ADD COLUMN "question" text;--> statement-breakpoint
ALTER TABLE "chain_fix_reviews" ADD COLUMN "reasons" jsonb;--> statement-breakpoint
ALTER TABLE "chain_fix_reviews" ADD COLUMN "variant_verdicts" jsonb;--> statement-breakpoint
ALTER TABLE "chain_fix_reviews" ADD COLUMN "corrected_reading" jsonb;--> statement-breakpoint
ALTER TABLE "chain_fix_reviews" ADD COLUMN "second_run_id" text;--> statement-breakpoint
ALTER TABLE "chain_fix_reviews" ADD COLUMN "second_run_agrees" boolean;--> statement-breakpoint
ALTER TABLE "chain_fix_submissions" ADD COLUMN "corrects_fix_id" text;--> statement-breakpoint
ALTER TABLE "chain_fix_witness_matches" ADD CONSTRAINT "chain_fix_witness_matches_fix_id_fk" FOREIGN KEY ("fix_id") REFERENCES "public"."chain_fixes"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chain_fix_witness_matches" ADD CONSTRAINT "chain_fix_witness_matches_hadith_id_fk" FOREIGN KEY ("hadith_id") REFERENCES "public"."hadiths"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
CREATE INDEX "chain_fix_witness_matches_fix_id_idx" ON "chain_fix_witness_matches" USING btree ("fix_id");--> statement-breakpoint
ALTER TABLE "chain_fix_submissions" ADD CONSTRAINT "chain_fix_submissions_corrects_fix_id_fk" FOREIGN KEY ("corrects_fix_id") REFERENCES "public"."chain_fixes"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chain_fix_decisions" ADD CONSTRAINT "chain_fix_decisions_ai_marks_check" CHECK (("chain_fix_decisions"."ai_review" is null or jsonb_typeof("chain_fix_decisions"."ai_review") = 'object') and ("chain_fix_decisions"."ai_disputed" is null or "chain_fix_decisions"."state" = 'accepted')
        and ("chain_fix_decisions"."ai_corrected" is null or "chain_fix_decisions"."state" in ('accepted', 'confirmed', 'rejected', 'superseded')));--> statement-breakpoint
ALTER TABLE "chain_fix_decisions" ADD CONSTRAINT "chain_fix_decisions_state_check" CHECK ("chain_fix_decisions"."state" in ('submitted', 'disputed', 'outvoted', 'held', 'accepted', 'confirmed', 'rejected', 'superseded', 'stale', 'awaiting_human', 'set_aside_by_ai'));--> statement-breakpoint
ALTER TABLE "chain_fix_decisions" ADD CONSTRAINT "chain_fix_decisions_agreement_check" CHECK ("chain_fix_decisions"."state" <> 'accepted' or "chain_fix_decisions"."effect" = 'annotate' or ("chain_fix_decisions"."runs" >= 2 and "chain_fix_decisions"."text_only_runs" >= 1 and "chain_fix_decisions"."runs" >= 2 * "chain_fix_decisions"."dissenting_runs")
        or ("chain_fix_decisions"."ai_corrected" is not null and "chain_fix_decisions"."runs" >= 2));--> statement-breakpoint
ALTER TABLE "chain_fix_reviews" ADD CONSTRAINT "chain_fix_reviews_ai_tier_check" CHECK (("chain_fix_reviews"."reviewer_kind" = 'human' and "chain_fix_reviews"."decision" is not null and "chain_fix_reviews"."review_decision" is null)
        or ("chain_fix_reviews"."reviewer_kind" = 'ai' and "chain_fix_reviews"."review_decision" is null and "chain_fix_reviews"."decision" is not null)
        or ("chain_fix_reviews"."reviewer_kind" = 'ai' and "chain_fix_reviews"."decision" is null and "chain_fix_reviews"."review_decision" in ('confirm_reading', 'confirm_with_correction', 'prefer_reader_a', 'prefer_reader_b', 'no_chain', 'keep_stored', 'refer_to_human')
            and "chain_fix_reviews"."outcome" is not null and btrim(coalesce("chain_fix_reviews"."run_id", '')) <> '' and "chain_fix_reviews"."pass" >= 1 and "chain_fix_reviews"."packet_sha256" ~ '^[0-9a-f]{64}$'
            and "chain_fix_reviews"."status_at_review" in ('held', 'pending', 'applied') and "chain_fix_reviews"."codes_at_review" is not null));--> statement-breakpoint
ALTER TABLE "chain_fix_reviews" ADD CONSTRAINT "chain_fix_reviews_decision_check" CHECK (("chain_fix_reviews"."decision" is null or "chain_fix_reviews"."decision" in ('confirmed', 'rejected', 'superseded'))
        and coalesce("chain_fix_reviews"."decision" = 'superseded', false) = ("chain_fix_reviews"."superseded_by_fix_id" is not null));--> statement-breakpoint
ALTER TABLE "chain_fix_submissions" ADD CONSTRAINT "chain_fix_submissions_tool_version_check" CHECK ("chain_fix_submissions"."tool_version" is null or "chain_fix_submissions"."tool_version" in ('v3', 'v3_1', 'v3_2', 'v3_3', 'v3_4'));--> statement-breakpoint
-- public_chain_fix_labels (0019 body) with four columns appended (CREATE OR REPLACE appends only): the AI reviewer's marks on the live
-- decision and the newest live witness match bound to the fix's reader text. "Agent verified" needs both an AI review and a match row.
CREATE OR REPLACE VIEW "public_chain_fix_labels" AS
SELECT c.id                                   AS chain_id,
       c.hadith_id,
       f.id                                   AS fix_id,
       d.state,
       d.effect,
       c.structure_status,
       d.models,
       d.runs,
       d.decided_at,
       (d.state = 'accepted')                 AS awaiting_final_review,
       coalesce((SELECT jsonb_agg(jsonb_build_object('reviewer', r.reviewer, 'reviewed_at', r.reviewed_at, 'note', r.note, 'citation', r.citation)
                                  ORDER BY r.reviewed_at)
                 FROM (SELECT DISTINCT ON (x.reviewer) x.* FROM chain_fix_reviews x
                       WHERE x.fix_id = f.id AND x.reviewer_kind = 'human'
                       ORDER BY x.reviewer, x.reviewed_at DESC, x.id DESC) r
                 WHERE r.decision = 'confirmed'), '[]'::jsonb) AS human_confirmations,
       d.ai_review,
       d.ai_disputed,
       d.ai_corrected,
       (SELECT jsonb_build_object('witness', w.witness, 'locator', w.locator, 'method', w.method, 'matched_at', w.created_at)
        FROM chain_fix_witness_matches w
        WHERE w.fix_id = f.id AND w.retired_at IS NULL AND w.matched AND w.reader_text_sha256 = f.reader_text_sha256
        ORDER BY w.created_at DESC, w.id DESC LIMIT 1) AS witness_match
FROM chains c
JOIN chain_fixes f ON f.id = c.chain_fix_id
JOIN chain_fix_decisions d ON d.fix_id = f.id AND d.retired_at IS NULL AND d.effect IS NOT NULL
JOIN public_hadiths h ON h.id = c.hadith_id
WHERE c.retired_at IS NULL
  AND f.arabic_sha256 = h.arabic_sha256;
--> statement-breakpoint
-- public_chain_fix_dispositions (0021 body) with the AI reviewer's mark appended.
CREATE OR REPLACE VIEW "public_chain_fix_dispositions" AS
SELECT f.hadith_id,
       f.id                       AS fix_id,
       f.disposition,
       d.state,
       d.models,
       d.runs,
       d.decided_at,
       (d.state = 'accepted')     AS awaiting_final_review,
       d.ai_review
FROM chain_fixes f
JOIN chain_fix_decisions d ON d.fix_id = f.id AND d.retired_at IS NULL AND d.effect IS NOT NULL
JOIN public_hadiths h ON h.id = f.hadith_id AND h.arabic_sha256 = f.arabic_sha256
WHERE f.disposition IS NOT NULL
  AND 'applied' = (SELECT a.action FROM chain_fix_applications a WHERE a.fix_id = f.id ORDER BY a.id DESC LIMIT 1)
  AND NOT EXISTS (SELECT 1 FROM chains c WHERE c.hadith_id = f.hadith_id AND c.retired_at IS NULL);
