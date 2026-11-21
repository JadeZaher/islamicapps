CREATE TYPE "public"."assessment_kind" AS ENUM('cited_ruling', 'compiler_criterion', 'compiler_statement', 'collection_label');--> statement-breakpoint
CREATE TYPE "public"."calendar" AS ENUM('hijri', 'gregorian');--> statement-breakpoint
CREATE TYPE "public"."chain_status" AS ENUM('complete', 'partial', 'unresolved', 'absent_in_source', 'extraction_failed');--> statement-breakpoint
CREATE TYPE "public"."confidence_level" AS ENUM('HIGH', 'MEDIUM', 'LOW');--> statement-breakpoint
CREATE TYPE "public"."curation_status" AS ENUM('proposed', 'verified', 'published');--> statement-breakpoint
CREATE TYPE "public"."decision_scope" AS ENUM('teacher_context', 'teacher_and_student_context', 'mention');--> statement-breakpoint
CREATE TYPE "public"."english_policy" AS ENUM('reviewed_only', 'source_provided_allowed');--> statement-breakpoint
CREATE TYPE "public"."event_category" AS ENUM('PROPHETIC_ERA', 'RASHIDUN', 'UMAYYAD', 'ABBASID', 'SCHOLARLY', 'MILITARY', 'POLITICAL', 'SOCIAL', 'RELIGIOUS', 'SCIENTIFIC', 'CULTURAL', 'ECONOMIC');--> statement-breakpoint
CREATE TYPE "public"."event_verification" AS ENUM('unverified', 'unverified_seed', 'human_verified', 'source_verified');--> statement-breakpoint
CREATE TYPE "public"."evidence_review_state" AS ENUM('candidate_only', 'lexicon_unverified', 'source_provided', 'source_verified', 'human_verified');--> statement-breakpoint
CREATE TYPE "public"."grade_canonical" AS ENUM('sahih', 'hasan', 'muwaththaq', 'da_if', 'majhul', 'mursal', 'mawdu', 'mu_tabar', 'mukhtalaf', 'ungraded');--> statement-breakpoint
CREATE TYPE "public"."grade_scheme" AS ENUM('sunni_7tier', 'imami_4tier', 'zaydi_3tier', 'ibadi_2tier', 'unspecified');--> statement-breakpoint
CREATE TYPE "public"."grading_status" AS ENUM('cited_assessments', 'compiler_criterion', 'none_recorded');--> statement-breakpoint
CREATE TYPE "public"."hadith_tradition" AS ENUM('Sunni', 'Imami', 'Zaydi', 'Ibadi');--> statement-breakpoint
CREATE TYPE "public"."isra_iliyyat_status" AS ENUM('MUWAFIQ', 'MUKHALIF', 'MASKUT_ANHU', 'NONE');--> statement-breakpoint
CREATE TYPE "public"."link_kind" AS ENUM('unclassified', 'person', 'derived_relation', 'collective', 'anonymous', 'not_a_narrator');--> statement-breakpoint
CREATE TYPE "public"."load_status" AS ENUM('loading', 'complete', 'failed');--> statement-breakpoint
CREATE TYPE "public"."location_relation" AS ENUM('born', 'died', 'resided');--> statement-breakpoint
CREATE TYPE "public"."mention_resolution" AS ENUM('unresolved', 'exact_registry', 'source_index', 'human_verified', 'derived_relation_verified', 'undecidable');--> statement-breakpoint
CREATE TYPE "public"."motif_category" AS ENUM('ESCHATOLOGY', 'CREATION', 'PROPHETIC_STORIES', 'LEGAL', 'WISDOM', 'PERSIAN_INFLUENCE', 'COSMOLOGY');--> statement-breakpoint
CREATE TYPE "public"."narration_level" AS ENUM('marfu', 'imam', 'mawquf', 'maqtu', 'unknown');--> statement-breakpoint
CREATE TYPE "public"."narrator_assessment_kind" AS ENUM('critic_ruling', 'consensus_summary');--> statement-breakpoint
CREATE TYPE "public"."narrator_authority" AS ENUM('rawi', 'imami_rijal');--> statement-breakpoint
CREATE TYPE "public"."narrator_verdict" AS ENUM('thiqa', 'thiqa_thabt', 'saduq', 'la_basa_bihi', 'majhul', 'daif', 'matruk', 'kadhab', 'mukhtalaf_fihi', 'not_applicable');--> statement-breakpoint
CREATE TYPE "public"."parallel_type" AS ENUM('CONDEMNATION', 'CULTURAL_BLEED', 'SHARED_SOURCE', 'DIRECT_BORROWING', 'APOLOGETIC', 'DISPUTED');--> statement-breakpoint
CREATE TYPE "public"."record_origin" AS ENUM('manual', 'seed', 'ai_research', 'neo4j_migration');--> statement-breakpoint
CREATE TYPE "public"."release_class" AS ENUM('release', 'non_release');--> statement-breakpoint
CREATE TYPE "public"."research_outcome" AS ENUM('parallel_found', 'no_parallel', 'error');--> statement-breakpoint
CREATE TYPE "public"."resolution_basis" AS ENUM('report_atomic', 'mention_exact', 'source_index', 'human_decision');--> statement-breakpoint
CREATE TYPE "public"."rights_status" AS ENUM('cleared', 'pending', 'restricted');--> statement-breakpoint
CREATE TYPE "public"."school_category" AS ENUM('SUNNI_THEOLOGICAL', 'SHIA_THEOLOGICAL', 'IBADI_THEOLOGICAL', 'SUNNI_MADHHAB', 'SHIA_MADHHAB');--> statement-breakpoint
CREATE TYPE "public"."source_text_status" AS ENUM('present_locator_bound', 'present', 'missing');--> statement-breakpoint
CREATE TYPE "public"."surface_decision_kind" AS ENUM('same_as', 'derived_relation', 'collective', 'anonymous', 'not_a_narrator', 'undecidable');--> statement-breakpoint
CREATE TYPE "public"."tabaqah_class" AS ENUM('PROPHET', 'SAHABA', 'TABIUN', 'ATBA_TABIUN', 'ATBA_ATBA', 'LATER_SCHOLAR');--> statement-breakpoint
CREATE TYPE "public"."translation_state" AS ENUM('human_verified', 'source_verified', 'source_provided', 'machine_unreviewed', 'unknown_provenance');--> statement-breakpoint
CREATE TABLE "curation_audit" (
	"id" bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY (sequence name "curation_audit_id_seq" INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 START WITH 1 CACHE 1),
	"occurred_at" timestamp with time zone DEFAULT now() NOT NULL,
	"actor" text NOT NULL,
	"action" text NOT NULL,
	"entity_type" text NOT NULL,
	"entity_id" text NOT NULL,
	"before" jsonb,
	"after" jsonb,
	"request_id" text
);
--> statement-breakpoint
CREATE TABLE "dataset_versions" (
	"id" text PRIMARY KEY NOT NULL,
	"source_bundle_sha256" text NOT NULL,
	"input_dataset_sha256" text NOT NULL,
	"rawis_sha256" text NOT NULL,
	"legacy_master_sha256" text NOT NULL,
	"curation_manifest_sha256" text,
	"extractor_version" text NOT NULL,
	"extractor_sha256" text NOT NULL,
	"bundle_version" text NOT NULL,
	"bundle_schema_version" integer NOT NULL,
	"source_release_state" text NOT NULL,
	"release_class" "release_class" NOT NULL,
	"non_release_reason" text,
	"public_override_by" text,
	"public_override_reason" text,
	"public_override_at" timestamp with time zone,
	"load_purpose" text NOT NULL,
	"load_status" "load_status" NOT NULL,
	"is_current" boolean DEFAULT false NOT NULL,
	"version_label" text,
	"expected_record_count" integer,
	"counts" jsonb DEFAULT '{}'::jsonb NOT NULL,
	"attribution_disclaimer" text NOT NULL,
	"loaded_by" text NOT NULL,
	"started_at" timestamp with time zone DEFAULT now() NOT NULL,
	"completed_at" timestamp with time zone,
	"network_refreshed_at" timestamp with time zone,
	"git_head" text,
	CONSTRAINT "dataset_versions_curation_manifest_check" CHECK ("dataset_versions"."source_release_state" <> 'development_nonrelease' or "dataset_versions"."curation_manifest_sha256" is not null),
	CONSTRAINT "dataset_versions_public_override_complete_check" CHECK (num_nonnulls("dataset_versions"."public_override_by", "dataset_versions"."public_override_reason", "dataset_versions"."public_override_at") in (0, 3)),
	CONSTRAINT "dataset_versions_public_override_non_release_check" CHECK ("dataset_versions"."public_override_by" is null or "dataset_versions"."release_class" = 'non_release')
);
--> statement-breakpoint
CREATE TABLE "books" (
	"id" text PRIMARY KEY NOT NULL,
	"collection_id" text NOT NULL,
	"number" text,
	"name" text,
	"volume" text,
	"provider_file_id" text,
	"provider_book_id" text,
	"first_seen_dataset_version_id" text NOT NULL,
	"changed_in_dataset_version_id" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_in_dataset_version_id" text
);
--> statement-breakpoint
CREATE TABLE "chapters" (
	"id" text PRIMARY KEY NOT NULL,
	"collection_id" text NOT NULL,
	"book_id" text,
	"number" text,
	"category_number" text,
	"name" text,
	"name_folded" text,
	"provider_chapter_locator" text,
	"first_seen_dataset_version_id" text NOT NULL,
	"changed_in_dataset_version_id" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_in_dataset_version_id" text
);
--> statement-breakpoint
CREATE TABLE "collection_rights" (
	"collection_id" text PRIMARY KEY NOT NULL,
	"rights_status" "rights_status" DEFAULT 'pending' NOT NULL,
	"english_policy" "english_policy" DEFAULT 'reviewed_only' NOT NULL,
	"rights_note" text,
	"citation" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"created_by" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_by" text NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_by" text
);
--> statement-breakpoint
CREATE TABLE "collections" (
	"id" text PRIMARY KEY NOT NULL,
	"source_work_id" text NOT NULL,
	"slug" text NOT NULL,
	"name" text NOT NULL,
	"name_arabic" text,
	"sort_key" integer NOT NULL,
	"tradition_id" text NOT NULL,
	"source_id" text NOT NULL,
	"compiler_name" text,
	"bibliographic_work_id" text,
	"registry_version" text NOT NULL,
	"first_seen_dataset_version_id" text NOT NULL,
	"changed_in_dataset_version_id" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_in_dataset_version_id" text,
	CONSTRAINT "collections_source_work_id_key" UNIQUE("source_work_id"),
	CONSTRAINT "collections_slug_key" UNIQUE("slug"),
	CONSTRAINT "collections_name_key" UNIQUE("name"),
	CONSTRAINT "collections_sort_key_key" UNIQUE("sort_key")
);
--> statement-breakpoint
CREATE TABLE "hadiths" (
	"id" text PRIMARY KEY NOT NULL,
	"record_id" text NOT NULL,
	"source_record_id" text,
	"provider_hadith_id" text,
	"collection_id" text NOT NULL,
	"collection_sort_key" integer NOT NULL,
	"source_display_label" text,
	"tradition_id" text NOT NULL,
	"book_id" text,
	"chapter_id" text,
	"volume" text,
	"chapter_no" text,
	"chapter_title" text,
	"chapter_title_folded" text,
	"category" text,
	"category_folded" text,
	"hadith_no" text,
	"hadith_no_int" integer GENERATED ALWAYS AS (case when hadith_no ~ '^[0-9]+$' then hadith_no::integer end) STORED,
	"text_ar" text,
	"text_ar_normalized" text,
	"arabic_sha256" text NOT NULL,
	"sanad" text,
	"sanad_confidence" text,
	"matn_ar" text,
	"attributed_to" text,
	"narration_level" "narration_level",
	"chain_type" text,
	"school" text,
	"url" text,
	"page_ref" text,
	"provenance_source" text,
	"translation_disposition" text,
	"quality_excluded" boolean DEFAULT false NOT NULL,
	"quality_exclusion_reason" text,
	"source_text_status" "source_text_status" DEFAULT 'missing' NOT NULL,
	"chain_status" "chain_status" DEFAULT 'extraction_failed' NOT NULL,
	"grading_status" "grading_status" DEFAULT 'none_recorded' NOT NULL,
	"first_seen_dataset_version_id" text NOT NULL,
	"changed_in_dataset_version_id" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_in_dataset_version_id" text,
	CONSTRAINT "hadiths_record_id_key" UNIQUE("record_id")
);
--> statement-breakpoint
CREATE TABLE "sources" (
	"id" text PRIMARY KEY NOT NULL,
	"slug" text NOT NULL,
	"name" text NOT NULL,
	"release_state" text NOT NULL,
	"first_seen_dataset_version_id" text NOT NULL,
	"changed_in_dataset_version_id" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_in_dataset_version_id" text,
	CONSTRAINT "sources_slug_key" UNIQUE("slug")
);
--> statement-breakpoint
CREATE TABLE "traditions" (
	"id" text PRIMARY KEY NOT NULL,
	"code" "hadith_tradition" NOT NULL,
	"name_arabic" text,
	"normalized_name" text NOT NULL,
	"grade_scheme" "grade_scheme" NOT NULL,
	"first_seen_dataset_version_id" text NOT NULL,
	"changed_in_dataset_version_id" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_in_dataset_version_id" text,
	CONSTRAINT "traditions_code_key" UNIQUE("code")
);
--> statement-breakpoint
CREATE TABLE "translations" (
	"id" text PRIMARY KEY NOT NULL,
	"hadith_id" text NOT NULL,
	"language" text NOT NULL,
	"text" text NOT NULL,
	"text_tsv" "tsvector" GENERATED ALWAYS AS (to_tsvector('english'::regconfig, text)) STORED NOT NULL,
	"matn_text" text,
	"state" "translation_state" NOT NULL,
	"quality_status" text NOT NULL,
	"review_state_raw" text,
	"source" text,
	"model" text,
	"translator" text,
	"provenance_source" text,
	"source_record_id" text,
	"arabic_sha256" text NOT NULL,
	"first_seen_dataset_version_id" text NOT NULL,
	"changed_in_dataset_version_id" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_in_dataset_version_id" text,
	CONSTRAINT "translations_hadith_id_language_key" UNIQUE("hadith_id","language")
);
--> statement-breakpoint
CREATE TABLE "narrator_aliases" (
	"id" text PRIMARY KEY NOT NULL,
	"narrator_id" text NOT NULL,
	"surface" text NOT NULL,
	"normalized_surface" text NOT NULL,
	"alias_kind" text NOT NULL,
	"first_seen_dataset_version_id" text NOT NULL,
	"changed_in_dataset_version_id" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_in_dataset_version_id" text
);
--> statement-breakpoint
CREATE TABLE "narrator_lexicon_profiles" (
	"narrator_id" text PRIMARY KEY NOT NULL,
	"bundle_id" text NOT NULL,
	"raw_profile_sha256" text NOT NULL,
	"lexicon_grade_label" text,
	"bio" text,
	"tabaqah_raw" text,
	"geographic_region" text,
	"birth_year_hijri" integer,
	"birth_year_gregorian" integer,
	"birth_year_hijri_raw" text,
	"birth_year_gregorian_raw" text,
	"birth_source_text" text,
	"birth_place" text,
	"death_year_hijri" integer,
	"death_year_gregorian" integer,
	"death_year_hijri_raw" text,
	"death_year_gregorian_raw" text,
	"death_source_text" text,
	"death_place" text,
	"death_reason" text,
	"review_state" "evidence_review_state" DEFAULT 'lexicon_unverified' NOT NULL,
	"source_status" text NOT NULL,
	"source_locator" text,
	"first_seen_dataset_version_id" text NOT NULL,
	"changed_in_dataset_version_id" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_in_dataset_version_id" text,
	CONSTRAINT "narrator_lexicon_profiles_bundle_id_key" UNIQUE("bundle_id")
);
--> statement-breakpoint
CREATE TABLE "narrator_teachers" (
	"student_id" text NOT NULL,
	"teacher_id" text NOT NULL,
	"evidence_fields" text[] NOT NULL,
	"evidence_count" integer NOT NULL,
	"reciprocal" boolean NOT NULL,
	"review_state" text NOT NULL,
	"first_seen_dataset_version_id" text NOT NULL,
	"changed_in_dataset_version_id" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_in_dataset_version_id" text,
	CONSTRAINT "narrator_teachers_pkey" PRIMARY KEY("student_id","teacher_id")
);
--> statement-breakpoint
CREATE TABLE "narrators" (
	"id" text PRIMARY KEY NOT NULL,
	"authority" "narrator_authority" DEFAULT 'rawi' NOT NULL,
	"authority_key" text NOT NULL,
	"scholar_indx" integer,
	"name" text NOT NULL,
	"name_ar" text,
	"name_en" text,
	"name_ar_normalized" text,
	"name_en_folded" text,
	"first_seen_dataset_version_id" text NOT NULL,
	"changed_in_dataset_version_id" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_in_dataset_version_id" text,
	CONSTRAINT "narrators_scholar_indx_key" UNIQUE("scholar_indx"),
	CONSTRAINT "narrators_authority_authority_key_key" UNIQUE("authority","authority_key"),
	CONSTRAINT "narrators_rawi_scholar_indx_check" CHECK ("narrators"."authority" <> 'rawi' or "narrators"."scholar_indx" is not null)
);
--> statement-breakpoint
CREATE TABLE "bibliographic_works" (
	"id" text PRIMARY KEY NOT NULL,
	"title" text NOT NULL,
	"title_ar" text,
	"author" text,
	"author_narrator_id" text,
	"tradition_id" text,
	"author_death_year_hijri" integer,
	"openiti_uri" text,
	"first_seen_dataset_version_id" text NOT NULL,
	"changed_in_dataset_version_id" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_in_dataset_version_id" text
);
--> statement-breakpoint
CREATE TABLE "citations" (
	"id" text PRIMARY KEY NOT NULL,
	"work_id" text NOT NULL,
	"edition_id" text,
	"volume" text,
	"page" text,
	"locator" text,
	"url" text,
	"quote_ar" text,
	"quote_en" text,
	"retrieved_at" timestamp with time zone,
	"review_state" "evidence_review_state" NOT NULL,
	"first_seen_dataset_version_id" text NOT NULL,
	"changed_in_dataset_version_id" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_in_dataset_version_id" text
);
--> statement-breakpoint
CREATE TABLE "editions" (
	"id" text PRIMARY KEY NOT NULL,
	"work_id" text NOT NULL,
	"editor" text,
	"publisher" text,
	"place" text,
	"year" text,
	"locator_scheme" text,
	"url" text,
	"rights_status" "rights_status" NOT NULL,
	"first_seen_dataset_version_id" text NOT NULL,
	"changed_in_dataset_version_id" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_in_dataset_version_id" text
);
--> statement-breakpoint
CREATE TABLE "chain_absence_dispositions" (
	"id" text PRIMARY KEY NOT NULL,
	"collection_id" text,
	"hadith_id" text,
	"reason" text NOT NULL,
	"citation_id" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"created_by" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_by" text NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_by" text,
	CONSTRAINT "chain_absence_dispositions_one_target_check" CHECK (num_nonnulls("chain_absence_dispositions"."collection_id", "chain_absence_dispositions"."hadith_id") = 1)
);
--> statement-breakpoint
CREATE TABLE "chain_mentions" (
	"id" text PRIMARY KEY NOT NULL,
	"chain_id" text NOT NULL,
	"hadith_id" text NOT NULL,
	"position" integer NOT NULL,
	"surface_ar" text NOT NULL,
	"surface_normalized" text NOT NULL,
	"teacher_context_normalized" text,
	"student_context_normalized" text,
	"review_unit_id" text NOT NULL,
	"review_unit_fine_id" text NOT NULL,
	"link_kind" "link_kind" DEFAULT 'unclassified' NOT NULL,
	"resolution" "mention_resolution" DEFAULT 'unresolved' NOT NULL,
	"resolution_basis" "resolution_basis",
	"narrator_id" text,
	"decision_id" text,
	"confidence" real,
	"extraction_method" text,
	"first_seen_dataset_version_id" text NOT NULL,
	"changed_in_dataset_version_id" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_in_dataset_version_id" text,
	CONSTRAINT "chain_mentions_chain_id_position_key" UNIQUE("chain_id","position"),
	CONSTRAINT "chain_mentions_resolved_confidence_check" CHECK ("chain_mentions"."narrator_id" is null or "chain_mentions"."confidence" is not null)
);
--> statement-breakpoint
CREATE TABLE "chains" (
	"id" text PRIMARY KEY NOT NULL,
	"hadith_id" text NOT NULL,
	"branch" integer NOT NULL,
	"length" integer NOT NULL,
	"resolved" boolean NOT NULL,
	"verified_link_count" integer DEFAULT 0 NOT NULL,
	"extraction_method" text NOT NULL,
	"confidence" real,
	"sanad_confidence" text,
	"first_seen_dataset_version_id" text NOT NULL,
	"changed_in_dataset_version_id" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_in_dataset_version_id" text,
	CONSTRAINT "chains_hadith_id_branch_key" UNIQUE("hadith_id","branch")
);
--> statement-breakpoint
CREATE TABLE "narrator_surface_decisions" (
	"id" text PRIMARY KEY DEFAULT gen_random_uuid()::text NOT NULL,
	"scope" "decision_scope" NOT NULL,
	"unit_id" text NOT NULL,
	"surface_normalized" text NOT NULL,
	"teacher_context_normalized" text,
	"student_context_normalized" text,
	"collection_id" text NOT NULL,
	"decision_kind" "surface_decision_kind" NOT NULL,
	"target_narrator_id" text,
	"derived_relation" text,
	"analytics_excluded" boolean DEFAULT false NOT NULL,
	"citation_id" text,
	"cited_basis_note" text,
	"reviewer" text NOT NULL,
	"attributed_scholar" text,
	"reviewed_at" timestamp with time zone NOT NULL,
	"notes" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"created_by" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_by" text NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_by" text,
	CONSTRAINT "narrator_surface_decisions_derived_scope_check" CHECK ("narrator_surface_decisions"."decision_kind" <> 'derived_relation' or "narrator_surface_decisions"."scope" in ('teacher_and_student_context', 'mention')),
	CONSTRAINT "narrator_surface_decisions_target_check" CHECK (("narrator_surface_decisions"."decision_kind" in ('same_as', 'derived_relation')) = ("narrator_surface_decisions"."target_narrator_id" is not null))
);
--> statement-breakpoint
CREATE TABLE "hadith_assessments" (
	"id" text PRIMARY KEY NOT NULL,
	"hadith_id" text NOT NULL,
	"tradition_id" text NOT NULL,
	"grade_scheme" "grade_scheme" NOT NULL,
	"ordinal" integer NOT NULL,
	"kind" "assessment_kind" NOT NULL,
	"grader" text,
	"grade_raw" text NOT NULL,
	"grade_canonical" "grade_canonical",
	"grade_detail" text,
	"citation_raw" text,
	"cited_work" text,
	"cited_volume" text,
	"cited_page" text,
	"citation_id" text,
	"source_field" text NOT NULL,
	"review_state" "evidence_review_state" NOT NULL,
	"first_seen_dataset_version_id" text NOT NULL,
	"changed_in_dataset_version_id" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_in_dataset_version_id" text,
	CONSTRAINT "hadith_assessments_natural_key" UNIQUE("hadith_id","tradition_id","source_field","ordinal")
);
--> statement-breakpoint
CREATE TABLE "narrator_assessments" (
	"id" text PRIMARY KEY NOT NULL,
	"narrator_id" text NOT NULL,
	"tradition_id" text,
	"kind" "narrator_assessment_kind" NOT NULL,
	"verdict" "narrator_verdict" NOT NULL,
	"critic" text,
	"quote_ar" text,
	"quote_en" text,
	"tadil_text" text,
	"jarh_text" text,
	"is_companion" boolean,
	"disagreement" boolean DEFAULT false NOT NULL,
	"critic_quote_count" integer,
	"provenance" text NOT NULL,
	"citation_id" text,
	"status" "curation_status" DEFAULT 'proposed' NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"created_by" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_by" text NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_by" text,
	CONSTRAINT "narrator_assessments_published_tradition_check" CHECK ("narrator_assessments"."status" <> 'published' or "narrator_assessments"."tradition_id" is not null),
	CONSTRAINT "narrator_assessments_published_citation_check" CHECK ("narrator_assessments"."status" <> 'published' or "narrator_assessments"."citation_id" is not null)
);
--> statement-breakpoint
CREATE TABLE "narrator_bios" (
	"narrator_id" text PRIMARY KEY NOT NULL,
	"is_prophet" boolean DEFAULT false NOT NULL,
	"tabaqah_class" "tabaqah_class",
	"name_en_clean" text,
	"name_ar_clean" text,
	"kunya" text,
	"nasab" text,
	"nisba" text,
	"geographic_region" text,
	"death_year_hijri" integer,
	"death_year_gregorian" integer,
	"bio_summary" text,
	"provenance" text NOT NULL,
	"citation_id" text,
	"status" "curation_status" DEFAULT 'proposed' NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"created_by" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_by" text NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_by" text,
	CONSTRAINT "narrator_bios_published_citation_check" CHECK ("narrator_bios"."status" <> 'published' or "narrator_bios"."citation_id" is not null)
);
--> statement-breakpoint
CREATE TABLE "historical_events" (
	"id" text PRIMARY KEY NOT NULL,
	"title" text NOT NULL,
	"title_arabic" text,
	"description" text,
	"significance" text,
	"start_year_hijri" integer,
	"end_year_hijri" integer,
	"start_year_gregorian" integer,
	"end_year_gregorian" integer,
	"category" "event_category",
	"location_name" text,
	"location_id" text,
	"verification_status" "event_verification" DEFAULT 'unverified' NOT NULL,
	"publication_ready" boolean DEFAULT false NOT NULL,
	"citation_source" text,
	"citation_locator" text,
	"citation_url" text,
	"citation_retrieved_at" timestamp with time zone,
	"citation_id" text,
	"origin" "record_origin" NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"created_by" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_by" text NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_by" text,
	CONSTRAINT "historical_events_year_order_check" CHECK ("historical_events"."start_year_hijri" is null or "historical_events"."end_year_hijri" is null or "historical_events"."end_year_hijri" >= "historical_events"."start_year_hijri"),
	CONSTRAINT "historical_events_publication_gate_check" CHECK (not "historical_events"."publication_ready" or ("historical_events"."verification_status" in ('human_verified', 'source_verified') and nullif(trim("historical_events"."citation_source"), '') is not null and (nullif(trim("historical_events"."citation_locator"), '') is not null or nullif(trim("historical_events"."citation_url"), '') is not null)))
);
--> statement-breakpoint
CREATE TABLE "locations" (
	"id" text PRIMARY KEY NOT NULL,
	"name" text NOT NULL,
	"name_arabic" text,
	"modern_country" text,
	"region" text,
	"description" text,
	"latitude" double precision,
	"longitude" double precision,
	"verification_status" "event_verification" DEFAULT 'unverified' NOT NULL,
	"origin" "record_origin" NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"created_by" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_by" text NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_by" text,
	CONSTRAINT "locations_latitude_check" CHECK ("locations"."latitude" between -90 and 90),
	CONSTRAINT "locations_longitude_check" CHECK ("locations"."longitude" between -180 and 180)
);
--> statement-breakpoint
CREATE TABLE "narrator_events" (
	"id" bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY (sequence name "narrator_events_id_seq" INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 START WITH 1 CACHE 1),
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"created_by" text NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_by" text,
	"narrator_id" text NOT NULL,
	"event_id" text NOT NULL,
	"role" text DEFAULT 'Participant' NOT NULL
);
--> statement-breakpoint
CREATE TABLE "narrator_locations" (
	"id" bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY (sequence name "narrator_locations_id_seq" INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 START WITH 1 CACHE 1),
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"created_by" text NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_by" text,
	"narrator_id" text NOT NULL,
	"location_id" text NOT NULL,
	"relation" "location_relation" NOT NULL
);
--> statement-breakpoint
CREATE TABLE "commentaries" (
	"id" text PRIMARY KEY NOT NULL,
	"type" text,
	"text" text NOT NULL,
	"text_arabic" text,
	"author" text,
	"source_work" text,
	"reference" text,
	"citation_id" text,
	"status" "curation_status" DEFAULT 'proposed' NOT NULL,
	"origin" "record_origin" NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"created_by" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_by" text NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_by" text
);
--> statement-breakpoint
CREATE TABLE "commentary_hadiths" (
	"id" bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY (sequence name "commentary_hadiths_id_seq" INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 START WITH 1 CACHE 1),
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"created_by" text NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_by" text,
	"commentary_id" text NOT NULL,
	"hadith_id" text NOT NULL,
	"bound_arabic_sha256" text NOT NULL
);
--> statement-breakpoint
CREATE TABLE "commentary_narrators" (
	"id" bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY (sequence name "commentary_narrators_id_seq" INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 START WITH 1 CACHE 1),
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"created_by" text NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_by" text,
	"commentary_id" text NOT NULL,
	"narrator_id" text NOT NULL
);
--> statement-breakpoint
CREATE TABLE "cross_parallels" (
	"id" text PRIMARY KEY NOT NULL,
	"pipeline_key" text,
	"hadith_id" text NOT NULL,
	"bound_arabic_sha256" text NOT NULL,
	"source_text_id" text NOT NULL,
	"religious_tradition_id" text NOT NULL,
	"parallel_type" "parallel_type" NOT NULL,
	"isra_iliyyat_status" "isra_iliyyat_status" DEFAULT 'NONE' NOT NULL,
	"confidence_level" "confidence_level" DEFAULT 'MEDIUM' NOT NULL,
	"hadith_excerpt_en" text,
	"source_translation_id" text,
	"source_text_original" text,
	"source_text_en" text,
	"scholarly_analysis" text,
	"origin" "record_origin" NOT NULL,
	"status" "curation_status" NOT NULL,
	"research_run_id" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"created_by" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_by" text NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_by" text
);
--> statement-breakpoint
CREATE TABLE "hadith_motif_tags" (
	"id" bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY (sequence name "hadith_motif_tags_id_seq" INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 START WITH 1 CACHE 1),
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"created_by" text NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_by" text,
	"hadith_id" text NOT NULL,
	"motif_tag_id" text NOT NULL
);
--> statement-breakpoint
CREATE TABLE "location_religious_traditions" (
	"id" bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY (sequence name "location_religious_traditions_id_seq" INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 START WITH 1 CACHE 1),
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"created_by" text NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_by" text,
	"location_id" text NOT NULL,
	"religious_tradition_id" text NOT NULL
);
--> statement-breakpoint
CREATE TABLE "motif_tags" (
	"id" text PRIMARY KEY NOT NULL,
	"name" text NOT NULL,
	"category" "motif_category" NOT NULL,
	"description" text,
	"origin" "record_origin" NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"created_by" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_by" text NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_by" text
);
--> statement-breakpoint
CREATE TABLE "narrator_religious_traditions" (
	"id" bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY (sequence name "narrator_religious_traditions_id_seq" INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 START WITH 1 CACHE 1),
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"created_by" text NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_by" text,
	"narrator_id" text NOT NULL,
	"religious_tradition_id" text NOT NULL
);
--> statement-breakpoint
CREATE TABLE "parallel_motif_tags" (
	"id" bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY (sequence name "parallel_motif_tags_id_seq" INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 START WITH 1 CACHE 1),
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"created_by" text NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_by" text,
	"parallel_id" text NOT NULL,
	"motif_tag_id" text NOT NULL
);
--> statement-breakpoint
CREATE TABLE "parallel_research_runs" (
	"id" text PRIMARY KEY NOT NULL,
	"hadith_id" text NOT NULL,
	"faith_code" text NOT NULL,
	"effort" text NOT NULL,
	"outcome" "research_outcome" NOT NULL,
	"translation_id" text,
	"parallel_id" text,
	"error" text,
	"requested_by" text NOT NULL,
	"started_at" timestamp with time zone NOT NULL,
	"finished_at" timestamp with time zone
);
--> statement-breakpoint
CREATE TABLE "religious_traditions" (
	"id" text PRIMARY KEY NOT NULL,
	"name" text NOT NULL,
	"name_arabic" text,
	"description" text,
	"geographic_origin" text,
	"geographic_heartlands" text[] DEFAULT '{}'::text[] NOT NULL,
	"research_faith_code" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"created_by" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_by" text NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_by" text
);
--> statement-breakpoint
CREATE TABLE "schools_of_thought" (
	"id" text PRIMARY KEY NOT NULL,
	"name" text NOT NULL,
	"name_arabic" text,
	"founder" text,
	"description" text,
	"category" "school_category" NOT NULL,
	"founded_century_hijri" integer,
	"parent_school_id" text,
	"religious_tradition_id" text,
	"tradition_id" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"created_by" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_by" text NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_by" text
);
--> statement-breakpoint
CREATE TABLE "source_texts" (
	"id" text PRIMARY KEY NOT NULL,
	"religious_tradition_id" text NOT NULL,
	"title" text NOT NULL,
	"title_original" text,
	"author" text,
	"approximate_date_ce" text,
	"description" text,
	"canonical_reference" text,
	"origin" "record_origin" NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"created_by" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_by" text NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_by" text
);
--> statement-breakpoint
ALTER TABLE "books" ADD CONSTRAINT "books_collection_id_fk" FOREIGN KEY ("collection_id") REFERENCES "public"."collections"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "books" ADD CONSTRAINT "books_first_seen_dataset_version_id_fk" FOREIGN KEY ("first_seen_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "books" ADD CONSTRAINT "books_changed_in_dataset_version_id_fk" FOREIGN KEY ("changed_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "books" ADD CONSTRAINT "books_retired_in_dataset_version_id_fk" FOREIGN KEY ("retired_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chapters" ADD CONSTRAINT "chapters_collection_id_fk" FOREIGN KEY ("collection_id") REFERENCES "public"."collections"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chapters" ADD CONSTRAINT "chapters_book_id_fk" FOREIGN KEY ("book_id") REFERENCES "public"."books"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chapters" ADD CONSTRAINT "chapters_first_seen_dataset_version_id_fk" FOREIGN KEY ("first_seen_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chapters" ADD CONSTRAINT "chapters_changed_in_dataset_version_id_fk" FOREIGN KEY ("changed_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chapters" ADD CONSTRAINT "chapters_retired_in_dataset_version_id_fk" FOREIGN KEY ("retired_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "collection_rights" ADD CONSTRAINT "collection_rights_collection_id_fk" FOREIGN KEY ("collection_id") REFERENCES "public"."collections"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "collections" ADD CONSTRAINT "collections_tradition_id_fk" FOREIGN KEY ("tradition_id") REFERENCES "public"."traditions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "collections" ADD CONSTRAINT "collections_source_id_fk" FOREIGN KEY ("source_id") REFERENCES "public"."sources"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "collections" ADD CONSTRAINT "collections_bibliographic_work_id_fk" FOREIGN KEY ("bibliographic_work_id") REFERENCES "public"."bibliographic_works"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "collections" ADD CONSTRAINT "collections_first_seen_dataset_version_id_fk" FOREIGN KEY ("first_seen_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "collections" ADD CONSTRAINT "collections_changed_in_dataset_version_id_fk" FOREIGN KEY ("changed_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "collections" ADD CONSTRAINT "collections_retired_in_dataset_version_id_fk" FOREIGN KEY ("retired_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "hadiths" ADD CONSTRAINT "hadiths_collection_id_fk" FOREIGN KEY ("collection_id") REFERENCES "public"."collections"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "hadiths" ADD CONSTRAINT "hadiths_tradition_id_fk" FOREIGN KEY ("tradition_id") REFERENCES "public"."traditions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "hadiths" ADD CONSTRAINT "hadiths_book_id_fk" FOREIGN KEY ("book_id") REFERENCES "public"."books"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "hadiths" ADD CONSTRAINT "hadiths_chapter_id_fk" FOREIGN KEY ("chapter_id") REFERENCES "public"."chapters"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "hadiths" ADD CONSTRAINT "hadiths_first_seen_dataset_version_id_fk" FOREIGN KEY ("first_seen_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "hadiths" ADD CONSTRAINT "hadiths_changed_in_dataset_version_id_fk" FOREIGN KEY ("changed_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "hadiths" ADD CONSTRAINT "hadiths_retired_in_dataset_version_id_fk" FOREIGN KEY ("retired_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "sources" ADD CONSTRAINT "sources_first_seen_dataset_version_id_fk" FOREIGN KEY ("first_seen_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "sources" ADD CONSTRAINT "sources_changed_in_dataset_version_id_fk" FOREIGN KEY ("changed_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "sources" ADD CONSTRAINT "sources_retired_in_dataset_version_id_fk" FOREIGN KEY ("retired_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "traditions" ADD CONSTRAINT "traditions_first_seen_dataset_version_id_fk" FOREIGN KEY ("first_seen_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "traditions" ADD CONSTRAINT "traditions_changed_in_dataset_version_id_fk" FOREIGN KEY ("changed_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "traditions" ADD CONSTRAINT "traditions_retired_in_dataset_version_id_fk" FOREIGN KEY ("retired_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "translations" ADD CONSTRAINT "translations_hadith_id_fk" FOREIGN KEY ("hadith_id") REFERENCES "public"."hadiths"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "translations" ADD CONSTRAINT "translations_first_seen_dataset_version_id_fk" FOREIGN KEY ("first_seen_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "translations" ADD CONSTRAINT "translations_changed_in_dataset_version_id_fk" FOREIGN KEY ("changed_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "translations" ADD CONSTRAINT "translations_retired_in_dataset_version_id_fk" FOREIGN KEY ("retired_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_aliases" ADD CONSTRAINT "narrator_aliases_narrator_id_fk" FOREIGN KEY ("narrator_id") REFERENCES "public"."narrators"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_aliases" ADD CONSTRAINT "narrator_aliases_first_seen_dataset_version_id_fk" FOREIGN KEY ("first_seen_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_aliases" ADD CONSTRAINT "narrator_aliases_changed_in_dataset_version_id_fk" FOREIGN KEY ("changed_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_aliases" ADD CONSTRAINT "narrator_aliases_retired_in_dataset_version_id_fk" FOREIGN KEY ("retired_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_lexicon_profiles" ADD CONSTRAINT "narrator_lexicon_profiles_narrator_id_fk" FOREIGN KEY ("narrator_id") REFERENCES "public"."narrators"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_lexicon_profiles" ADD CONSTRAINT "narrator_lexicon_profiles_first_seen_dataset_version_id_fk" FOREIGN KEY ("first_seen_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_lexicon_profiles" ADD CONSTRAINT "narrator_lexicon_profiles_changed_in_dataset_version_id_fk" FOREIGN KEY ("changed_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_lexicon_profiles" ADD CONSTRAINT "narrator_lexicon_profiles_retired_in_dataset_version_id_fk" FOREIGN KEY ("retired_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_teachers" ADD CONSTRAINT "narrator_teachers_student_id_fk" FOREIGN KEY ("student_id") REFERENCES "public"."narrators"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_teachers" ADD CONSTRAINT "narrator_teachers_teacher_id_fk" FOREIGN KEY ("teacher_id") REFERENCES "public"."narrators"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_teachers" ADD CONSTRAINT "narrator_teachers_first_seen_dataset_version_id_fk" FOREIGN KEY ("first_seen_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_teachers" ADD CONSTRAINT "narrator_teachers_changed_in_dataset_version_id_fk" FOREIGN KEY ("changed_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_teachers" ADD CONSTRAINT "narrator_teachers_retired_in_dataset_version_id_fk" FOREIGN KEY ("retired_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrators" ADD CONSTRAINT "narrators_first_seen_dataset_version_id_fk" FOREIGN KEY ("first_seen_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrators" ADD CONSTRAINT "narrators_changed_in_dataset_version_id_fk" FOREIGN KEY ("changed_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrators" ADD CONSTRAINT "narrators_retired_in_dataset_version_id_fk" FOREIGN KEY ("retired_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "bibliographic_works" ADD CONSTRAINT "bibliographic_works_author_narrator_id_fk" FOREIGN KEY ("author_narrator_id") REFERENCES "public"."narrators"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "bibliographic_works" ADD CONSTRAINT "bibliographic_works_tradition_id_fk" FOREIGN KEY ("tradition_id") REFERENCES "public"."traditions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "bibliographic_works" ADD CONSTRAINT "bibliographic_works_first_seen_dataset_version_id_fk" FOREIGN KEY ("first_seen_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "bibliographic_works" ADD CONSTRAINT "bibliographic_works_changed_in_dataset_version_id_fk" FOREIGN KEY ("changed_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "bibliographic_works" ADD CONSTRAINT "bibliographic_works_retired_in_dataset_version_id_fk" FOREIGN KEY ("retired_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "citations" ADD CONSTRAINT "citations_work_id_fk" FOREIGN KEY ("work_id") REFERENCES "public"."bibliographic_works"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "citations" ADD CONSTRAINT "citations_edition_id_fk" FOREIGN KEY ("edition_id") REFERENCES "public"."editions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "citations" ADD CONSTRAINT "citations_first_seen_dataset_version_id_fk" FOREIGN KEY ("first_seen_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "citations" ADD CONSTRAINT "citations_changed_in_dataset_version_id_fk" FOREIGN KEY ("changed_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "citations" ADD CONSTRAINT "citations_retired_in_dataset_version_id_fk" FOREIGN KEY ("retired_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "editions" ADD CONSTRAINT "editions_work_id_fk" FOREIGN KEY ("work_id") REFERENCES "public"."bibliographic_works"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "editions" ADD CONSTRAINT "editions_first_seen_dataset_version_id_fk" FOREIGN KEY ("first_seen_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "editions" ADD CONSTRAINT "editions_changed_in_dataset_version_id_fk" FOREIGN KEY ("changed_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "editions" ADD CONSTRAINT "editions_retired_in_dataset_version_id_fk" FOREIGN KEY ("retired_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chain_absence_dispositions" ADD CONSTRAINT "chain_absence_dispositions_collection_id_fk" FOREIGN KEY ("collection_id") REFERENCES "public"."collections"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chain_absence_dispositions" ADD CONSTRAINT "chain_absence_dispositions_hadith_id_fk" FOREIGN KEY ("hadith_id") REFERENCES "public"."hadiths"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chain_absence_dispositions" ADD CONSTRAINT "chain_absence_dispositions_citation_id_fk" FOREIGN KEY ("citation_id") REFERENCES "public"."citations"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chain_mentions" ADD CONSTRAINT "chain_mentions_chain_id_fk" FOREIGN KEY ("chain_id") REFERENCES "public"."chains"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chain_mentions" ADD CONSTRAINT "chain_mentions_hadith_id_fk" FOREIGN KEY ("hadith_id") REFERENCES "public"."hadiths"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chain_mentions" ADD CONSTRAINT "chain_mentions_narrator_id_fk" FOREIGN KEY ("narrator_id") REFERENCES "public"."narrators"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chain_mentions" ADD CONSTRAINT "chain_mentions_decision_id_fk" FOREIGN KEY ("decision_id") REFERENCES "public"."narrator_surface_decisions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chain_mentions" ADD CONSTRAINT "chain_mentions_first_seen_dataset_version_id_fk" FOREIGN KEY ("first_seen_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chain_mentions" ADD CONSTRAINT "chain_mentions_changed_in_dataset_version_id_fk" FOREIGN KEY ("changed_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chain_mentions" ADD CONSTRAINT "chain_mentions_retired_in_dataset_version_id_fk" FOREIGN KEY ("retired_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chains" ADD CONSTRAINT "chains_hadith_id_fk" FOREIGN KEY ("hadith_id") REFERENCES "public"."hadiths"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chains" ADD CONSTRAINT "chains_first_seen_dataset_version_id_fk" FOREIGN KEY ("first_seen_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chains" ADD CONSTRAINT "chains_changed_in_dataset_version_id_fk" FOREIGN KEY ("changed_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chains" ADD CONSTRAINT "chains_retired_in_dataset_version_id_fk" FOREIGN KEY ("retired_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_surface_decisions" ADD CONSTRAINT "narrator_surface_decisions_collection_id_fk" FOREIGN KEY ("collection_id") REFERENCES "public"."collections"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_surface_decisions" ADD CONSTRAINT "narrator_surface_decisions_target_narrator_id_fk" FOREIGN KEY ("target_narrator_id") REFERENCES "public"."narrators"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_surface_decisions" ADD CONSTRAINT "narrator_surface_decisions_citation_id_fk" FOREIGN KEY ("citation_id") REFERENCES "public"."citations"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "hadith_assessments" ADD CONSTRAINT "hadith_assessments_hadith_id_fk" FOREIGN KEY ("hadith_id") REFERENCES "public"."hadiths"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "hadith_assessments" ADD CONSTRAINT "hadith_assessments_tradition_id_fk" FOREIGN KEY ("tradition_id") REFERENCES "public"."traditions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "hadith_assessments" ADD CONSTRAINT "hadith_assessments_citation_id_fk" FOREIGN KEY ("citation_id") REFERENCES "public"."citations"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "hadith_assessments" ADD CONSTRAINT "hadith_assessments_first_seen_dataset_version_id_fk" FOREIGN KEY ("first_seen_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "hadith_assessments" ADD CONSTRAINT "hadith_assessments_changed_in_dataset_version_id_fk" FOREIGN KEY ("changed_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "hadith_assessments" ADD CONSTRAINT "hadith_assessments_retired_in_dataset_version_id_fk" FOREIGN KEY ("retired_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_assessments" ADD CONSTRAINT "narrator_assessments_narrator_id_fk" FOREIGN KEY ("narrator_id") REFERENCES "public"."narrators"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_assessments" ADD CONSTRAINT "narrator_assessments_tradition_id_fk" FOREIGN KEY ("tradition_id") REFERENCES "public"."traditions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_assessments" ADD CONSTRAINT "narrator_assessments_citation_id_fk" FOREIGN KEY ("citation_id") REFERENCES "public"."citations"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_bios" ADD CONSTRAINT "narrator_bios_narrator_id_fk" FOREIGN KEY ("narrator_id") REFERENCES "public"."narrators"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_bios" ADD CONSTRAINT "narrator_bios_citation_id_fk" FOREIGN KEY ("citation_id") REFERENCES "public"."citations"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "historical_events" ADD CONSTRAINT "historical_events_location_id_fk" FOREIGN KEY ("location_id") REFERENCES "public"."locations"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "historical_events" ADD CONSTRAINT "historical_events_citation_id_fk" FOREIGN KEY ("citation_id") REFERENCES "public"."citations"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_events" ADD CONSTRAINT "narrator_events_narrator_id_fk" FOREIGN KEY ("narrator_id") REFERENCES "public"."narrators"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_events" ADD CONSTRAINT "narrator_events_event_id_fk" FOREIGN KEY ("event_id") REFERENCES "public"."historical_events"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_locations" ADD CONSTRAINT "narrator_locations_narrator_id_fk" FOREIGN KEY ("narrator_id") REFERENCES "public"."narrators"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_locations" ADD CONSTRAINT "narrator_locations_location_id_fk" FOREIGN KEY ("location_id") REFERENCES "public"."locations"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "commentaries" ADD CONSTRAINT "commentaries_citation_id_fk" FOREIGN KEY ("citation_id") REFERENCES "public"."citations"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "commentary_hadiths" ADD CONSTRAINT "commentary_hadiths_commentary_id_fk" FOREIGN KEY ("commentary_id") REFERENCES "public"."commentaries"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "commentary_hadiths" ADD CONSTRAINT "commentary_hadiths_hadith_id_fk" FOREIGN KEY ("hadith_id") REFERENCES "public"."hadiths"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "commentary_narrators" ADD CONSTRAINT "commentary_narrators_commentary_id_fk" FOREIGN KEY ("commentary_id") REFERENCES "public"."commentaries"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "commentary_narrators" ADD CONSTRAINT "commentary_narrators_narrator_id_fk" FOREIGN KEY ("narrator_id") REFERENCES "public"."narrators"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "cross_parallels" ADD CONSTRAINT "cross_parallels_hadith_id_fk" FOREIGN KEY ("hadith_id") REFERENCES "public"."hadiths"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "cross_parallels" ADD CONSTRAINT "cross_parallels_source_text_id_fk" FOREIGN KEY ("source_text_id") REFERENCES "public"."source_texts"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "cross_parallels" ADD CONSTRAINT "cross_parallels_religious_tradition_id_fk" FOREIGN KEY ("religious_tradition_id") REFERENCES "public"."religious_traditions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "cross_parallels" ADD CONSTRAINT "cross_parallels_source_translation_id_fk" FOREIGN KEY ("source_translation_id") REFERENCES "public"."translations"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "cross_parallels" ADD CONSTRAINT "cross_parallels_research_run_id_fk" FOREIGN KEY ("research_run_id") REFERENCES "public"."parallel_research_runs"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "hadith_motif_tags" ADD CONSTRAINT "hadith_motif_tags_hadith_id_fk" FOREIGN KEY ("hadith_id") REFERENCES "public"."hadiths"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "hadith_motif_tags" ADD CONSTRAINT "hadith_motif_tags_motif_tag_id_fk" FOREIGN KEY ("motif_tag_id") REFERENCES "public"."motif_tags"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "location_religious_traditions" ADD CONSTRAINT "location_religious_traditions_location_id_fk" FOREIGN KEY ("location_id") REFERENCES "public"."locations"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "location_religious_traditions" ADD CONSTRAINT "location_religious_traditions_religious_tradition_id_fk" FOREIGN KEY ("religious_tradition_id") REFERENCES "public"."religious_traditions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_religious_traditions" ADD CONSTRAINT "narrator_religious_traditions_narrator_id_fk" FOREIGN KEY ("narrator_id") REFERENCES "public"."narrators"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_religious_traditions" ADD CONSTRAINT "narrator_religious_traditions_religious_tradition_id_fk" FOREIGN KEY ("religious_tradition_id") REFERENCES "public"."religious_traditions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "parallel_motif_tags" ADD CONSTRAINT "parallel_motif_tags_parallel_id_fk" FOREIGN KEY ("parallel_id") REFERENCES "public"."cross_parallels"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "parallel_motif_tags" ADD CONSTRAINT "parallel_motif_tags_motif_tag_id_fk" FOREIGN KEY ("motif_tag_id") REFERENCES "public"."motif_tags"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "parallel_research_runs" ADD CONSTRAINT "parallel_research_runs_hadith_id_fk" FOREIGN KEY ("hadith_id") REFERENCES "public"."hadiths"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "parallel_research_runs" ADD CONSTRAINT "parallel_research_runs_translation_id_fk" FOREIGN KEY ("translation_id") REFERENCES "public"."translations"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "parallel_research_runs" ADD CONSTRAINT "parallel_research_runs_parallel_id_fk" FOREIGN KEY ("parallel_id") REFERENCES "public"."cross_parallels"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "schools_of_thought" ADD CONSTRAINT "schools_of_thought_parent_school_id_fk" FOREIGN KEY ("parent_school_id") REFERENCES "public"."schools_of_thought"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "schools_of_thought" ADD CONSTRAINT "schools_of_thought_religious_tradition_id_fk" FOREIGN KEY ("religious_tradition_id") REFERENCES "public"."religious_traditions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "schools_of_thought" ADD CONSTRAINT "schools_of_thought_tradition_id_fk" FOREIGN KEY ("tradition_id") REFERENCES "public"."traditions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "source_texts" ADD CONSTRAINT "source_texts_religious_tradition_id_fk" FOREIGN KEY ("religious_tradition_id") REFERENCES "public"."religious_traditions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
CREATE INDEX "curation_audit_entity_idx" ON "curation_audit" USING btree ("entity_type","entity_id","occurred_at" DESC NULLS LAST);--> statement-breakpoint
CREATE UNIQUE INDEX "dataset_versions_is_current_key" ON "dataset_versions" USING btree ("is_current") WHERE "dataset_versions"."is_current";--> statement-breakpoint
CREATE INDEX "books_collection_id_idx" ON "books" USING btree ("collection_id");--> statement-breakpoint
CREATE INDEX "chapters_collection_id_idx" ON "chapters" USING btree ("collection_id");--> statement-breakpoint
CREATE INDEX "chapters_book_id_idx" ON "chapters" USING btree ("book_id");--> statement-breakpoint
CREATE INDEX "collections_tradition_id_idx" ON "collections" USING btree ("tradition_id");--> statement-breakpoint
CREATE INDEX "hadiths_browse_order_idx" ON "hadiths" USING btree ("collection_sort_key","hadith_no_int","id");--> statement-breakpoint
CREATE INDEX "hadiths_collection_id_idx" ON "hadiths" USING btree ("collection_id");--> statement-breakpoint
CREATE INDEX "hadiths_tradition_id_idx" ON "hadiths" USING btree ("tradition_id");--> statement-breakpoint
CREATE INDEX "hadiths_book_id_idx" ON "hadiths" USING btree ("book_id");--> statement-breakpoint
CREATE INDEX "hadiths_chapter_id_idx" ON "hadiths" USING btree ("chapter_id");--> statement-breakpoint
CREATE INDEX "hadiths_source_display_label_idx" ON "hadiths" USING btree ("source_display_label");--> statement-breakpoint
CREATE INDEX "hadiths_chapter_title_folded_trgm_idx" ON "hadiths" USING gin ("chapter_title_folded" gin_trgm_ops);--> statement-breakpoint
CREATE INDEX "hadiths_category_folded_trgm_idx" ON "hadiths" USING gin ("category_folded" gin_trgm_ops);--> statement-breakpoint
CREATE INDEX "translations_text_tsv_english_idx" ON "translations" USING gin ("text_tsv") WHERE "translations"."language" = 'en';--> statement-breakpoint
CREATE INDEX "narrator_aliases_narrator_id_idx" ON "narrator_aliases" USING btree ("narrator_id");--> statement-breakpoint
CREATE INDEX "narrator_aliases_normalized_surface_idx" ON "narrator_aliases" USING btree ("normalized_surface");--> statement-breakpoint
CREATE INDEX "narrator_teachers_teacher_id_idx" ON "narrator_teachers" USING btree ("teacher_id");--> statement-breakpoint
CREATE INDEX "narrators_name_ar_normalized_trgm_idx" ON "narrators" USING gin ("name_ar_normalized" gin_trgm_ops);--> statement-breakpoint
CREATE INDEX "narrators_name_en_folded_trgm_idx" ON "narrators" USING gin ("name_en_folded" gin_trgm_ops);--> statement-breakpoint
CREATE INDEX "narrators_display_name_idx" ON "narrators" USING btree (coalesce("name_en", "name"));--> statement-breakpoint
CREATE INDEX "chain_mentions_narrator_id_idx" ON "chain_mentions" USING btree ("narrator_id") WHERE "chain_mentions"."narrator_id" is not null;--> statement-breakpoint
CREATE INDEX "chain_mentions_hadith_id_idx" ON "chain_mentions" USING btree ("hadith_id");--> statement-breakpoint
CREATE INDEX "chain_mentions_review_unit_id_idx" ON "chain_mentions" USING btree ("review_unit_id");--> statement-breakpoint
CREATE INDEX "chain_mentions_review_unit_fine_id_idx" ON "chain_mentions" USING btree ("review_unit_fine_id");--> statement-breakpoint
CREATE INDEX "chain_mentions_surface_normalized_idx" ON "chain_mentions" USING btree ("surface_normalized");--> statement-breakpoint
CREATE UNIQUE INDEX "narrator_surface_decisions_live_unit_key" ON "narrator_surface_decisions" USING btree ("scope","unit_id") WHERE "narrator_surface_decisions"."retired_at" is null;--> statement-breakpoint
CREATE INDEX "narrator_surface_decisions_target_narrator_id_idx" ON "narrator_surface_decisions" USING btree ("target_narrator_id");--> statement-breakpoint
CREATE INDEX "hadith_assessments_hadith_id_idx" ON "hadith_assessments" USING btree ("hadith_id");--> statement-breakpoint
CREATE INDEX "hadith_assessments_tradition_grade_idx" ON "hadith_assessments" USING btree ("tradition_id","grade_canonical");--> statement-breakpoint
CREATE INDEX "narrator_assessments_narrator_tradition_idx" ON "narrator_assessments" USING btree ("narrator_id","tradition_id");--> statement-breakpoint
CREATE INDEX "historical_events_year_range_idx" ON "historical_events" USING btree ("start_year_hijri","end_year_hijri");--> statement-breakpoint
CREATE INDEX "historical_events_category_idx" ON "historical_events" USING btree ("category");--> statement-breakpoint
CREATE INDEX "historical_events_published_start_idx" ON "historical_events" USING btree ("start_year_hijri") WHERE "historical_events"."publication_ready";--> statement-breakpoint
CREATE UNIQUE INDEX "narrator_events_live_key" ON "narrator_events" USING btree ("narrator_id","event_id","role") WHERE "narrator_events"."retired_at" is null;--> statement-breakpoint
CREATE INDEX "narrator_events_event_id_idx" ON "narrator_events" USING btree ("event_id");--> statement-breakpoint
CREATE UNIQUE INDEX "narrator_locations_live_key" ON "narrator_locations" USING btree ("narrator_id","location_id","relation") WHERE "narrator_locations"."retired_at" is null;--> statement-breakpoint
CREATE INDEX "narrator_locations_location_id_idx" ON "narrator_locations" USING btree ("location_id");--> statement-breakpoint
CREATE INDEX "commentaries_created_at_idx" ON "commentaries" USING btree ("created_at" DESC NULLS LAST);--> statement-breakpoint
CREATE UNIQUE INDEX "commentary_hadiths_live_key" ON "commentary_hadiths" USING btree ("commentary_id","hadith_id") WHERE "commentary_hadiths"."retired_at" is null;--> statement-breakpoint
CREATE INDEX "commentary_hadiths_hadith_id_idx" ON "commentary_hadiths" USING btree ("hadith_id");--> statement-breakpoint
CREATE UNIQUE INDEX "commentary_narrators_live_key" ON "commentary_narrators" USING btree ("commentary_id","narrator_id") WHERE "commentary_narrators"."retired_at" is null;--> statement-breakpoint
CREATE INDEX "commentary_narrators_narrator_id_idx" ON "commentary_narrators" USING btree ("narrator_id");--> statement-breakpoint
CREATE UNIQUE INDEX "cross_parallels_live_pipeline_key_key" ON "cross_parallels" USING btree ("pipeline_key") WHERE "cross_parallels"."retired_at" is null;--> statement-breakpoint
CREATE INDEX "cross_parallels_hadith_id_idx" ON "cross_parallels" USING btree ("hadith_id");--> statement-breakpoint
CREATE INDEX "cross_parallels_tradition_type_idx" ON "cross_parallels" USING btree ("religious_tradition_id","parallel_type");--> statement-breakpoint
CREATE INDEX "cross_parallels_created_at_idx" ON "cross_parallels" USING btree ("created_at" DESC NULLS LAST);--> statement-breakpoint
CREATE UNIQUE INDEX "hadith_motif_tags_live_key" ON "hadith_motif_tags" USING btree ("hadith_id","motif_tag_id") WHERE "hadith_motif_tags"."retired_at" is null;--> statement-breakpoint
CREATE INDEX "hadith_motif_tags_motif_tag_id_idx" ON "hadith_motif_tags" USING btree ("motif_tag_id");--> statement-breakpoint
CREATE UNIQUE INDEX "location_religious_traditions_live_key" ON "location_religious_traditions" USING btree ("location_id","religious_tradition_id") WHERE "location_religious_traditions"."retired_at" is null;--> statement-breakpoint
CREATE INDEX "location_religious_traditions_religious_tradition_id_idx" ON "location_religious_traditions" USING btree ("religious_tradition_id");--> statement-breakpoint
CREATE UNIQUE INDEX "motif_tags_live_name_key" ON "motif_tags" USING btree ("name") WHERE "motif_tags"."retired_at" is null;--> statement-breakpoint
CREATE INDEX "motif_tags_category_idx" ON "motif_tags" USING btree ("category");--> statement-breakpoint
CREATE UNIQUE INDEX "narrator_religious_traditions_live_key" ON "narrator_religious_traditions" USING btree ("narrator_id","religious_tradition_id") WHERE "narrator_religious_traditions"."retired_at" is null;--> statement-breakpoint
CREATE INDEX "narrator_religious_traditions_religious_tradition_id_idx" ON "narrator_religious_traditions" USING btree ("religious_tradition_id");--> statement-breakpoint
CREATE UNIQUE INDEX "parallel_motif_tags_live_key" ON "parallel_motif_tags" USING btree ("parallel_id","motif_tag_id") WHERE "parallel_motif_tags"."retired_at" is null;--> statement-breakpoint
CREATE INDEX "parallel_motif_tags_motif_tag_id_idx" ON "parallel_motif_tags" USING btree ("motif_tag_id");--> statement-breakpoint
CREATE INDEX "parallel_research_runs_hadith_faith_idx" ON "parallel_research_runs" USING btree ("hadith_id","faith_code");--> statement-breakpoint
CREATE UNIQUE INDEX "religious_traditions_live_name_key" ON "religious_traditions" USING btree ("name") WHERE "religious_traditions"."retired_at" is null;--> statement-breakpoint
CREATE UNIQUE INDEX "religious_traditions_live_research_faith_code_key" ON "religious_traditions" USING btree ("research_faith_code") WHERE "religious_traditions"."retired_at" is null;--> statement-breakpoint
CREATE UNIQUE INDEX "schools_of_thought_live_name_key" ON "schools_of_thought" USING btree ("name") WHERE "schools_of_thought"."retired_at" is null;--> statement-breakpoint
CREATE UNIQUE INDEX "source_texts_live_canonical_reference_key" ON "source_texts" USING btree ("canonical_reference") WHERE "source_texts"."retired_at" is null;--> statement-breakpoint
CREATE INDEX "source_texts_religious_tradition_id_idx" ON "source_texts" USING btree ("religious_tradition_id");