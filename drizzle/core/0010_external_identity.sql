CREATE TYPE "public"."name_latin_basis" AS ENUM('provider_english', 'identity_name', 'transliteration_vocalized', 'transliteration_table');--> statement-breakpoint
ALTER TYPE "public"."mention_candidate_basis" ADD VALUE 'source_hadith_kg';--> statement-breakpoint
ALTER TYPE "public"."mention_candidate_basis" ADD VALUE 'source_hadith_kg_confirmed_by_text';--> statement-breakpoint
ALTER TYPE "public"."mention_candidate_basis" ADD VALUE 'source_riwayat';--> statement-breakpoint
ALTER TYPE "public"."mention_candidate_basis" ADD VALUE 'source_riwayat_confirmed_by_text';--> statement-breakpoint
ALTER TYPE "public"."mention_candidate_basis" ADD VALUE 'imam_kunya_convention';--> statement-breakpoint
ALTER TYPE "public"."mention_candidate_basis" ADD VALUE 'imam_kunya_candidate';--> statement-breakpoint
ALTER TYPE "public"."narrator_authority" ADD VALUE 'hadith_kg';--> statement-breakpoint
ALTER TYPE "public"."narrator_authority" ADD VALUE 'riwayat';--> statement-breakpoint
ALTER TYPE "public"."narrator_authority" ADD VALUE 'imam_register';--> statement-breakpoint
ALTER TYPE "public"."narrator_placeholder_reason" ADD VALUE 'relational_name';--> statement-breakpoint
ALTER TYPE "public"."narrator_placeholder_reason" ADD VALUE 'collective_or_anonymous_name';--> statement-breakpoint
ALTER TYPE "public"."narrator_placeholder_reason" ADD VALUE 'hadith_kg_stub_narrator';--> statement-breakpoint
CREATE TABLE "narrator_external_ids" (
	"id" text PRIMARY KEY NOT NULL,
	"narrator_id" text NOT NULL,
	"namespace" text NOT NULL,
	"external_id" text NOT NULL,
	"asserted_by" text NOT NULL,
	"first_seen_dataset_version_id" text NOT NULL,
	"changed_in_dataset_version_id" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_in_dataset_version_id" text
);
--> statement-breakpoint
CREATE TABLE "narrator_link_candidates" (
	"id" text PRIMARY KEY NOT NULL,
	"external_narrator_id" text NOT NULL,
	"rawi_narrator_id" text NOT NULL,
	"basis" text NOT NULL,
	"evidence" jsonb NOT NULL,
	"review_state" text NOT NULL,
	"first_seen_dataset_version_id" text NOT NULL,
	"changed_in_dataset_version_id" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_in_dataset_version_id" text,
	CONSTRAINT "narrator_link_candidates_review_state_check" CHECK ("narrator_link_candidates"."review_state" = 'unreviewed')
);
--> statement-breakpoint
CREATE TABLE "narrator_source_profiles" (
	"narrator_id" text PRIMARY KEY NOT NULL,
	"source" text NOT NULL,
	"assertions" jsonb NOT NULL,
	"licence" text NOT NULL,
	"label_reason" text,
	"asserted_by" text NOT NULL,
	"review_state" text DEFAULT 'source_unverified' NOT NULL,
	"first_seen_dataset_version_id" text NOT NULL,
	"changed_in_dataset_version_id" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_in_dataset_version_id" text,
	CONSTRAINT "narrator_source_profiles_source_check" CHECK ("narrator_source_profiles"."source" in ('hadith_kg', 'riwayat', 'imam_register')),
	CONSTRAINT "narrator_source_profiles_review_state_check" CHECK ("narrator_source_profiles"."review_state" = 'source_unverified')
);
--> statement-breakpoint
ALTER TABLE "chain_mention_candidates" DROP CONSTRAINT "chain_mention_candidates_source_position_check";--> statement-breakpoint
ALTER TABLE "narrators" ADD COLUMN "name_latin" text;--> statement-breakpoint
ALTER TABLE "narrators" ADD COLUMN "name_latin_basis" "name_latin_basis";--> statement-breakpoint
ALTER TABLE "chain_mention_candidates" ADD COLUMN "source_ref" text;--> statement-breakpoint
ALTER TABLE "chain_mention_candidates" ADD COLUMN "source_assertion_origin" text;--> statement-breakpoint
ALTER TABLE "chain_mentions" ADD COLUMN "name_latin" text;--> statement-breakpoint
ALTER TABLE "chain_mentions" ADD COLUMN "name_latin_basis" "name_latin_basis";--> statement-breakpoint
ALTER TABLE "chain_mentions" ADD COLUMN "name_latin_narrator_id" text;--> statement-breakpoint
ALTER TABLE "narrator_external_ids" ADD CONSTRAINT "narrator_external_ids_narrator_id_fk" FOREIGN KEY ("narrator_id") REFERENCES "public"."narrators"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_external_ids" ADD CONSTRAINT "narrator_external_ids_first_seen_dataset_version_id_fk" FOREIGN KEY ("first_seen_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_external_ids" ADD CONSTRAINT "narrator_external_ids_changed_in_dataset_version_id_fk" FOREIGN KEY ("changed_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_external_ids" ADD CONSTRAINT "narrator_external_ids_retired_in_dataset_version_id_fk" FOREIGN KEY ("retired_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_link_candidates" ADD CONSTRAINT "narrator_link_candidates_external_narrator_id_fk" FOREIGN KEY ("external_narrator_id") REFERENCES "public"."narrators"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_link_candidates" ADD CONSTRAINT "narrator_link_candidates_rawi_narrator_id_fk" FOREIGN KEY ("rawi_narrator_id") REFERENCES "public"."narrators"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_link_candidates" ADD CONSTRAINT "narrator_link_candidates_first_seen_dataset_version_id_fk" FOREIGN KEY ("first_seen_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_link_candidates" ADD CONSTRAINT "narrator_link_candidates_changed_in_dataset_version_id_fk" FOREIGN KEY ("changed_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_link_candidates" ADD CONSTRAINT "narrator_link_candidates_retired_in_dataset_version_id_fk" FOREIGN KEY ("retired_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_source_profiles" ADD CONSTRAINT "narrator_source_profiles_narrator_id_fk" FOREIGN KEY ("narrator_id") REFERENCES "public"."narrators"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_source_profiles" ADD CONSTRAINT "narrator_source_profiles_first_seen_dataset_version_id_fk" FOREIGN KEY ("first_seen_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_source_profiles" ADD CONSTRAINT "narrator_source_profiles_changed_in_dataset_version_id_fk" FOREIGN KEY ("changed_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_source_profiles" ADD CONSTRAINT "narrator_source_profiles_retired_in_dataset_version_id_fk" FOREIGN KEY ("retired_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
CREATE INDEX "narrator_external_ids_narrator_id_idx" ON "narrator_external_ids" USING btree ("narrator_id");--> statement-breakpoint
CREATE INDEX "narrator_link_candidates_external_narrator_id_idx" ON "narrator_link_candidates" USING btree ("external_narrator_id");--> statement-breakpoint
CREATE INDEX "narrator_link_candidates_rawi_narrator_id_idx" ON "narrator_link_candidates" USING btree ("rawi_narrator_id");--> statement-breakpoint
ALTER TABLE "chain_mentions" ADD CONSTRAINT "chain_mentions_name_latin_narrator_id_fk" FOREIGN KEY ("name_latin_narrator_id") REFERENCES "public"."narrators"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrators" ADD CONSTRAINT "narrators_name_latin_check" CHECK (("narrators"."name_latin" is null) = ("narrators"."name_latin_basis" is null));--> statement-breakpoint
ALTER TABLE "chain_mention_candidates" ADD CONSTRAINT "chain_mention_candidates_source_ref_check" CHECK (("chain_mention_candidates"."basis"::text in ('source_hadith_kg', 'source_hadith_kg_confirmed_by_text', 'source_riwayat',
        'source_riwayat_confirmed_by_text')) = ("chain_mention_candidates"."source_ref" is not null and "chain_mention_candidates"."source_assertion_origin" is not null));--> statement-breakpoint
ALTER TABLE "chain_mention_candidates" ADD CONSTRAINT "chain_mention_candidates_source_position_check" CHECK (("chain_mention_candidates"."basis"::text in ('source_index', 'source_index_confirmed_by_text', 'source_hadith_kg',
        'source_hadith_kg_confirmed_by_text', 'source_riwayat', 'source_riwayat_confirmed_by_text'))
        = ("chain_mention_candidates"."source_position" is not null));--> statement-breakpoint
ALTER TABLE "chain_mentions" ADD CONSTRAINT "chain_mentions_name_latin_check" CHECK (("chain_mentions"."name_latin" is null) = ("chain_mentions"."name_latin_basis" is null)
        and (("chain_mentions"."name_latin_basis"::text = 'identity_name') is true) = ("chain_mentions"."name_latin_narrator_id" is not null));