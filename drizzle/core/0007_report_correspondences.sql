CREATE TYPE "public"."report_correspondence_basis" AS ENUM('textual_overlap');--> statement-breakpoint
CREATE TYPE "public"."report_correspondence_class" AS ENUM('same_wording', 'same_report_variant_wording', 'partial_overlap');--> statement-breakpoint
CREATE TYPE "public"."report_correspondence_decision" AS ENUM('confirmed', 'rejected', 'uncertain');--> statement-breakpoint
CREATE TYPE "public"."report_correspondence_reviewed_relation" AS ENUM('same_wording', 'same_report_variant_wording', 'partial_overlap', 'same_ruling_different_attribution', 'shared_formula_only', 'shared_quran_quotation');--> statement-breakpoint
CREATE TYPE "public"."report_correspondence_scope" AS ENUM('same_work', 'cross_work_same_tradition', 'cross_tradition');--> statement-breakpoint
CREATE TABLE "report_correspondence_candidates" (
	"id" text PRIMARY KEY NOT NULL,
	"hadith_id_a" text NOT NULL,
	"hadith_id_b" text NOT NULL,
	"arabic_sha256_a" text NOT NULL,
	"arabic_sha256_b" text NOT NULL,
	"relation_class" "report_correspondence_class" NOT NULL,
	"jaccard" real NOT NULL,
	"containment" real NOT NULL,
	"global_containment" real NOT NULL,
	"length_ratio" real NOT NULL,
	"shared_shingles" integer NOT NULL,
	"shingles_a" integer NOT NULL,
	"shingles_b" integer NOT NULL,
	"words_a" integer NOT NULL,
	"words_b" integer NOT NULL,
	"score_band" text NOT NULL,
	"scope" "report_correspondence_scope" NOT NULL,
	"matn_split_a" text NOT NULL,
	"matn_split_b" text NOT NULL,
	"cluster_id" text NOT NULL,
	"basis" "report_correspondence_basis" NOT NULL,
	"method_version" text NOT NULL,
	"first_seen_dataset_version_id" text NOT NULL,
	"changed_in_dataset_version_id" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_in_dataset_version_id" text,
	CONSTRAINT "report_correspondence_candidates_pair_method_key" UNIQUE("hadith_id_a","hadith_id_b","method_version"),
	CONSTRAINT "report_correspondence_candidates_pair_order_check" CHECK ("report_correspondence_candidates"."hadith_id_a" collate "C" < "report_correspondence_candidates"."hadith_id_b" collate "C"),
	CONSTRAINT "report_correspondence_candidates_scores_check" CHECK ("report_correspondence_candidates"."jaccard" between 0 and 1 and "report_correspondence_candidates"."containment" between 0 and 1 and "report_correspondence_candidates"."global_containment" between 0 and 1)
);
--> statement-breakpoint
CREATE TABLE "report_correspondence_cluster_members" (
	"method_version" text NOT NULL,
	"hadith_id" text NOT NULL,
	"cluster_id" text NOT NULL,
	"star_centre_hadith_id" text NOT NULL,
	"is_star_centre" boolean NOT NULL,
	"first_seen_dataset_version_id" text NOT NULL,
	"changed_in_dataset_version_id" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_in_dataset_version_id" text,
	CONSTRAINT "report_correspondence_cluster_members_pkey" PRIMARY KEY("method_version","hadith_id"),
	CONSTRAINT "report_correspondence_cluster_members_centre_check" CHECK ("report_correspondence_cluster_members"."is_star_centre" = ("report_correspondence_cluster_members"."hadith_id" = "report_correspondence_cluster_members"."star_centre_hadith_id"))
);
--> statement-breakpoint
CREATE TABLE "report_correspondence_decisions" (
	"id" text PRIMARY KEY DEFAULT gen_random_uuid()::text NOT NULL,
	"hadith_id_a" text NOT NULL,
	"hadith_id_b" text NOT NULL,
	"bound_arabic_sha256_a" text NOT NULL,
	"bound_arabic_sha256_b" text NOT NULL,
	"decision" "report_correspondence_decision" NOT NULL,
	"reviewed_relation" "report_correspondence_reviewed_relation",
	"note" text,
	"citation_id" text,
	"decided_by" text NOT NULL,
	"decided_at" timestamp with time zone DEFAULT now() NOT NULL,
	"supersedes_decision_id" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"created_by" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_by" text NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_by" text,
	CONSTRAINT "report_correspondence_decisions_pair_order_check" CHECK ("report_correspondence_decisions"."hadith_id_a" collate "C" < "report_correspondence_decisions"."hadith_id_b" collate "C"),
	CONSTRAINT "report_correspondence_decisions_confirmed_relation_check" CHECK ("report_correspondence_decisions"."decision" <> 'confirmed' or "report_correspondence_decisions"."reviewed_relation" is null
          or "report_correspondence_decisions"."reviewed_relation" in ('same_wording', 'same_report_variant_wording', 'partial_overlap')),
	CONSTRAINT "report_correspondence_decisions_retired_check" CHECK (num_nonnulls("report_correspondence_decisions"."retired_at", "report_correspondence_decisions"."retired_by") in (0, 2))
);
--> statement-breakpoint
ALTER TABLE "report_correspondence_candidates" ADD CONSTRAINT "report_correspondence_candidates_hadith_id_a_fk" FOREIGN KEY ("hadith_id_a") REFERENCES "public"."hadiths"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "report_correspondence_candidates" ADD CONSTRAINT "report_correspondence_candidates_hadith_id_b_fk" FOREIGN KEY ("hadith_id_b") REFERENCES "public"."hadiths"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "report_correspondence_candidates" ADD CONSTRAINT "report_corr_candidates_first_seen_dataset_version_id_fk" FOREIGN KEY ("first_seen_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "report_correspondence_candidates" ADD CONSTRAINT "report_corr_candidates_changed_in_dataset_version_id_fk" FOREIGN KEY ("changed_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "report_correspondence_candidates" ADD CONSTRAINT "report_corr_candidates_retired_in_dataset_version_id_fk" FOREIGN KEY ("retired_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "report_correspondence_cluster_members" ADD CONSTRAINT "report_correspondence_cluster_members_hadith_id_fk" FOREIGN KEY ("hadith_id") REFERENCES "public"."hadiths"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "report_correspondence_cluster_members" ADD CONSTRAINT "report_correspondence_cluster_members_star_centre_hadith_id_fk" FOREIGN KEY ("star_centre_hadith_id") REFERENCES "public"."hadiths"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "report_correspondence_cluster_members" ADD CONSTRAINT "report_corr_cluster_members_first_seen_dataset_version_id_fk" FOREIGN KEY ("first_seen_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "report_correspondence_cluster_members" ADD CONSTRAINT "report_corr_cluster_members_changed_in_dataset_version_id_fk" FOREIGN KEY ("changed_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "report_correspondence_cluster_members" ADD CONSTRAINT "report_corr_cluster_members_retired_in_dataset_version_id_fk" FOREIGN KEY ("retired_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "report_correspondence_decisions" ADD CONSTRAINT "report_correspondence_decisions_hadith_id_a_fk" FOREIGN KEY ("hadith_id_a") REFERENCES "public"."hadiths"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "report_correspondence_decisions" ADD CONSTRAINT "report_correspondence_decisions_hadith_id_b_fk" FOREIGN KEY ("hadith_id_b") REFERENCES "public"."hadiths"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "report_correspondence_decisions" ADD CONSTRAINT "report_correspondence_decisions_citation_id_fk" FOREIGN KEY ("citation_id") REFERENCES "public"."citations"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "report_correspondence_decisions" ADD CONSTRAINT "report_correspondence_decisions_supersedes_decision_id_fk" FOREIGN KEY ("supersedes_decision_id") REFERENCES "public"."report_correspondence_decisions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
CREATE INDEX "report_correspondence_candidates_hadith_id_b_idx" ON "report_correspondence_candidates" USING btree ("hadith_id_b");--> statement-breakpoint
CREATE INDEX "report_correspondence_candidates_cluster_id_idx" ON "report_correspondence_candidates" USING btree ("cluster_id");--> statement-breakpoint
CREATE INDEX "report_correspondence_cluster_members_hadith_id_idx" ON "report_correspondence_cluster_members" USING btree ("hadith_id");--> statement-breakpoint
CREATE INDEX "report_correspondence_cluster_members_cluster_id_idx" ON "report_correspondence_cluster_members" USING btree ("cluster_id");--> statement-breakpoint
CREATE UNIQUE INDEX "report_correspondence_decisions_live_pair_key" ON "report_correspondence_decisions" USING btree ("hadith_id_a","hadith_id_b") WHERE "report_correspondence_decisions"."retired_at" is null;--> statement-breakpoint
CREATE INDEX "report_correspondence_decisions_hadith_id_b_idx" ON "report_correspondence_decisions" USING btree ("hadith_id_b");--> statement-breakpoint

-- Hand-written below (see src/db/AGENTS.md "Report correspondences").
-- report_correspondence_shown_pairs: the one display rule, over live reports in either publication state, one row per
-- unordered pair. Shown when a live reviewer decision confirmed it (whatever its score, even with no live candidate),
-- or when a live candidate meets the threshold the job's precision reading recommends (same wording; variant wording
-- at Jaccard >= 0.4; partial overlap at containment >= 0.7) and no reviewer rejected it. A decision or a candidate
-- counts only while both reports still carry the Arabic it was bound to: a changed text re-queues the pair, a decision
-- is never silently reapplied. Written without CTEs so a filter on one report reaches the indexes (a CTE used twice is
-- materialized whole).
CREATE VIEW "report_correspondence_shown_pairs" AS
SELECT c.hadith_id_a, c.hadith_id_b, c.id AS candidate_id, c.relation_class, c.jaccard, c.containment, c.scope,
       d.id AS decision_id, d.decision, d.reviewed_relation
FROM report_correspondence_candidates c
JOIN hadiths ha ON ha.id = c.hadith_id_a AND ha.retired_at IS NULL AND ha.arabic_sha256 = c.arabic_sha256_a
JOIN hadiths hb ON hb.id = c.hadith_id_b AND hb.retired_at IS NULL AND hb.arabic_sha256 = c.arabic_sha256_b
LEFT JOIN report_correspondence_decisions d
       ON d.hadith_id_a = c.hadith_id_a AND d.hadith_id_b = c.hadith_id_b AND d.retired_at IS NULL
      AND d.bound_arabic_sha256_a = ha.arabic_sha256 AND d.bound_arabic_sha256_b = hb.arabic_sha256
WHERE c.retired_at IS NULL
  AND (d.decision = 'confirmed'
       OR (d.decision IS DISTINCT FROM 'rejected'
           AND (c.relation_class = 'same_wording'
                OR (c.relation_class = 'same_report_variant_wording' AND c.jaccard >= 0.4)
                OR (c.relation_class = 'partial_overlap' AND c.containment >= 0.7))))
UNION ALL
SELECT d.hadith_id_a, d.hadith_id_b, NULL, NULL, NULL, NULL, NULL, d.id, d.decision, d.reviewed_relation
FROM report_correspondence_decisions d
JOIN hadiths ha ON ha.id = d.hadith_id_a AND ha.retired_at IS NULL AND ha.arabic_sha256 = d.bound_arabic_sha256_a
JOIN hadiths hb ON hb.id = d.hadith_id_b AND hb.retired_at IS NULL AND hb.arabic_sha256 = d.bound_arabic_sha256_b
WHERE d.retired_at IS NULL
  AND d.decision = 'confirmed'
  AND NOT EXISTS (
        SELECT 1 FROM report_correspondence_candidates c
        WHERE c.hadith_id_a = d.hadith_id_a AND c.hadith_id_b = d.hadith_id_b AND c.retired_at IS NULL
          AND c.arabic_sha256_a = ha.arabic_sha256 AND c.arabic_sha256_b = hb.arabic_sha256);
--> statement-breakpoint

-- report_correspondence_display: the shown pairs, one row per direction, so a report's family is one indexed lookup.
CREATE VIEW "report_correspondence_display" AS
SELECT s.hadith_id_a AS hadith_id, s.hadith_id_b AS corresponding_hadith_id, s.candidate_id, s.relation_class,
       s.jaccard, s.containment, s.scope, s.decision_id, s.decision, s.reviewed_relation,
       (s.decision IS NOT DISTINCT FROM 'confirmed') AS confirmed
FROM report_correspondence_shown_pairs s
UNION ALL
SELECT s.hadith_id_b, s.hadith_id_a, s.candidate_id, s.relation_class,
       s.jaccard, s.containment, s.scope, s.decision_id, s.decision, s.reviewed_relation,
       (s.decision IS NOT DISTINCT FROM 'confirmed')
FROM report_correspondence_shown_pairs s;
--> statement-breakpoint

-- public_report_correspondences: the display rule where both reports are public (section 11.3 gate).
CREATE VIEW "public_report_correspondences" AS
SELECT x.*
FROM report_correspondence_display x
JOIN public_hadiths h ON h.id = x.hadith_id
JOIN public_hadiths o ON o.id = x.corresponding_hadith_id;
