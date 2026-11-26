CREATE TABLE "temporal_assertions" (
	"id" text PRIMARY KEY NOT NULL,
	"event_id" text,
	"epoch_id" text,
	"collection_id" text,
	"boundary" text,
	"predicate" text NOT NULL,
	"year_min" integer,
	"year_max" integer,
	"calendar" "calendar" DEFAULT 'hijri' NOT NULL,
	"precision" text,
	"alternatives" integer[] DEFAULT '{}'::integer[] NOT NULL,
	"month_day" text,
	"stated_ar" text,
	"statement_en" text,
	"date_basis" text,
	"qualifier" text,
	"reckoning" text,
	"attributed_to" text,
	"perspective" jsonb,
	"flags" text[] DEFAULT '{}'::text[] NOT NULL,
	"note" text,
	"citation_id" text NOT NULL,
	"review_state" "evidence_review_state" DEFAULT 'candidate_only' NOT NULL,
	"ai_review" jsonb,
	"human_reviews" jsonb DEFAULT '[]'::jsonb NOT NULL,
	"supersedes_assertion_id" text,
	"first_seen_dataset_version_id" text NOT NULL,
	"changed_in_dataset_version_id" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_in_dataset_version_id" text,
	CONSTRAINT "temporal_assertions_subject_check" CHECK (num_nonnulls("temporal_assertions"."event_id", "temporal_assertions"."epoch_id", "temporal_assertions"."collection_id") = 1),
	CONSTRAINT "temporal_assertions_boundary_check" CHECK ("temporal_assertions"."boundary" is null or ("temporal_assertions"."epoch_id" is not null and "temporal_assertions"."boundary" in ('start', 'end'))),
	CONSTRAINT "temporal_assertions_year_range_check" CHECK ("temporal_assertions"."year_min" is null or "temporal_assertions"."year_max" is null or "temporal_assertions"."year_max" >= "temporal_assertions"."year_min"),
	CONSTRAINT "temporal_assertions_date_basis_check" CHECK ("temporal_assertions"."date_basis" is null or "temporal_assertions"."date_basis" in ('passage', 'section_heading')),
	CONSTRAINT "temporal_assertions_perspective_check" CHECK ("temporal_assertions"."perspective" is null or jsonb_typeof("temporal_assertions"."perspective") = 'object'),
	CONSTRAINT "temporal_assertions_ai_review_check" CHECK ("temporal_assertions"."ai_review" is null or jsonb_typeof("temporal_assertions"."ai_review") = 'object'),
	CONSTRAINT "temporal_assertions_human_reviews_check" CHECK (jsonb_typeof("temporal_assertions"."human_reviews") = 'array')
);
--> statement-breakpoint
ALTER TABLE "citations" ADD COLUMN "source_span" jsonb;--> statement-breakpoint
ALTER TABLE "citations" ADD COLUMN "source_sha256" text;--> statement-breakpoint
ALTER TABLE "citations" ADD COLUMN "source_file" text;--> statement-breakpoint
ALTER TABLE "historical_events" ADD COLUMN "key" text;--> statement-breakpoint
ALTER TABLE "historical_events" ADD COLUMN "tradition_context" "hadith_tradition";--> statement-breakpoint
ALTER TABLE "historical_events" ADD COLUMN "ai_review" jsonb;--> statement-breakpoint
ALTER TABLE "historical_events" ADD COLUMN "human_reviews" jsonb DEFAULT '[]'::jsonb NOT NULL;--> statement-breakpoint
ALTER TABLE "locations" ADD COLUMN "kind" text;--> statement-breakpoint
ALTER TABLE "locations" ADD COLUMN "forms_ar" text[] DEFAULT '{}'::text[] NOT NULL;--> statement-breakpoint
ALTER TABLE "locations" ADD COLUMN "ambiguous_forms" jsonb;--> statement-breakpoint
ALTER TABLE "locations" ADD COLUMN "cited_in_citation_ids" text[] DEFAULT '{}'::text[] NOT NULL;--> statement-breakpoint
ALTER TABLE "locations" ADD COLUMN "coordinates_basis" text;--> statement-breakpoint
ALTER TABLE "narrator_events" ADD COLUMN "citation_id" text;--> statement-breakpoint
ALTER TABLE "narrator_events" ADD COLUMN "stated_ar" text;--> statement-breakpoint
ALTER TABLE "narrator_events" ADD COLUMN "ai_review" jsonb;--> statement-breakpoint
ALTER TABLE "narrator_events" ADD COLUMN "human_reviews" jsonb DEFAULT '[]'::jsonb NOT NULL;--> statement-breakpoint
ALTER TABLE "temporal_assertions" ADD CONSTRAINT "temporal_assertions_collection_id_fk" FOREIGN KEY ("collection_id") REFERENCES "public"."collections"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "temporal_assertions" ADD CONSTRAINT "temporal_assertions_citation_id_fk" FOREIGN KEY ("citation_id") REFERENCES "public"."citations"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "temporal_assertions" ADD CONSTRAINT "temporal_assertions_supersedes_assertion_id_fk" FOREIGN KEY ("supersedes_assertion_id") REFERENCES "public"."temporal_assertions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "temporal_assertions" ADD CONSTRAINT "temporal_assertions_first_seen_dataset_version_id_fk" FOREIGN KEY ("first_seen_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "temporal_assertions" ADD CONSTRAINT "temporal_assertions_changed_in_dataset_version_id_fk" FOREIGN KEY ("changed_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "temporal_assertions" ADD CONSTRAINT "temporal_assertions_retired_in_dataset_version_id_fk" FOREIGN KEY ("retired_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
CREATE INDEX "temporal_assertions_event_id_idx" ON "temporal_assertions" USING btree ("event_id");--> statement-breakpoint
CREATE INDEX "temporal_assertions_epoch_id_idx" ON "temporal_assertions" USING btree ("epoch_id");--> statement-breakpoint
CREATE INDEX "temporal_assertions_collection_id_idx" ON "temporal_assertions" USING btree ("collection_id");--> statement-breakpoint
CREATE INDEX "temporal_assertions_citation_id_idx" ON "temporal_assertions" USING btree ("citation_id");--> statement-breakpoint
ALTER TABLE "narrator_events" ADD CONSTRAINT "narrator_events_citation_id_fk" FOREIGN KEY ("citation_id") REFERENCES "public"."citations"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
CREATE UNIQUE INDEX "historical_events_live_key_key" ON "historical_events" USING btree ("key") WHERE "historical_events"."retired_at" is null and "historical_events"."key" is not null;--> statement-breakpoint
CREATE INDEX "narrator_events_citation_id_idx" ON "narrator_events" USING btree ("citation_id");--> statement-breakpoint
ALTER TABLE "citations" ADD CONSTRAINT "citations_source_span_check" CHECK ("citations"."source_span" is null or jsonb_typeof("citations"."source_span") = 'object');--> statement-breakpoint
ALTER TABLE "citations" ADD CONSTRAINT "citations_source_sha256_check" CHECK ("citations"."source_sha256" is null or "citations"."source_sha256" ~ '^[0-9a-f]{64}$');--> statement-breakpoint
ALTER TABLE "citations" ADD CONSTRAINT "citations_source_file_check" CHECK ("citations"."source_file" is null or btrim("citations"."source_file") <> '');--> statement-breakpoint
ALTER TABLE "historical_events" ADD CONSTRAINT "historical_events_ai_review_check" CHECK ("historical_events"."ai_review" is null or jsonb_typeof("historical_events"."ai_review") = 'object');--> statement-breakpoint
ALTER TABLE "historical_events" ADD CONSTRAINT "historical_events_human_reviews_check" CHECK (jsonb_typeof("historical_events"."human_reviews") = 'array');--> statement-breakpoint
ALTER TABLE "locations" ADD CONSTRAINT "locations_ambiguous_forms_check" CHECK ("locations"."ambiguous_forms" is null or jsonb_typeof("locations"."ambiguous_forms") = 'object');--> statement-breakpoint
ALTER TABLE "narrator_events" ADD CONSTRAINT "narrator_events_ai_review_check" CHECK ("narrator_events"."ai_review" is null or jsonb_typeof("narrator_events"."ai_review") = 'object');--> statement-breakpoint
ALTER TABLE "narrator_events" ADD CONSTRAINT "narrator_events_human_reviews_check" CHECK (jsonb_typeof("narrator_events"."human_reviews") = 'array');