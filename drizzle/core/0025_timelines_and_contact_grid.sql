CREATE TABLE "external_tradition_parallels" (
	"id" text PRIMARY KEY NOT NULL,
	"hadith_id" text NOT NULL,
	"tradition_source" text NOT NULL,
	"relation_type" text NOT NULL,
	"source_work" text NOT NULL,
	"locator" text,
	"note" text,
	"citation_id" text NOT NULL,
	"review_state" "evidence_review_state" DEFAULT 'candidate_only' NOT NULL,
	"first_seen_dataset_version_id" text NOT NULL,
	"changed_in_dataset_version_id" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_in_dataset_version_id" text,
	CONSTRAINT "external_tradition_parallels_tradition_source_check" CHECK ("external_tradition_parallels"."tradition_source" in ('biblical', 'midrash_talmud', 'syriac_christian', 'sasanian_andarz', 'pre_islamic_poetry', 'other')),
	CONSTRAINT "external_tradition_parallels_relation_type_check" CHECK ("external_tradition_parallels"."relation_type" in ('direct_quote', 'structural_parallel', 'shared_motif', 'polemical_response'))
);
--> statement-breakpoint
CREATE TABLE "narrator_affiliations" (
	"id" text PRIMARY KEY NOT NULL,
	"narrator_id" text NOT NULL,
	"kind" text NOT NULL,
	"label" text NOT NULL,
	"note" text,
	"citation_id" text NOT NULL,
	"review_state" "evidence_review_state" DEFAULT 'candidate_only' NOT NULL,
	"first_seen_dataset_version_id" text NOT NULL,
	"changed_in_dataset_version_id" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_in_dataset_version_id" text,
	CONSTRAINT "narrator_affiliations_kind_check" CHECK ("narrator_affiliations"."kind" in ('tribe', 'mawla_of', 'legal_school', 'theological_tendency', 'political_faction', 'convert_background', 'profession'))
);
--> statement-breakpoint
CREATE TABLE "narrator_residences" (
	"id" text PRIMARY KEY NOT NULL,
	"narrator_id" text NOT NULL,
	"location_id" text NOT NULL,
	"year_min" integer,
	"year_max" integer,
	"precision" text,
	"role" text NOT NULL,
	"citation_id" text NOT NULL,
	"review_state" "evidence_review_state" DEFAULT 'candidate_only' NOT NULL,
	"first_seen_dataset_version_id" text NOT NULL,
	"changed_in_dataset_version_id" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_in_dataset_version_id" text,
	CONSTRAINT "narrator_residences_year_range_check" CHECK ("narrator_residences"."year_min" is null or "narrator_residences"."year_max" is null or "narrator_residences"."year_max" >= "narrator_residences"."year_min"),
	CONSTRAINT "narrator_residences_role_check" CHECK ("narrator_residences"."role" in ('born', 'studied', 'taught', 'qadi', 'governor', 'rihla_visit', 'died'))
);
--> statement-breakpoint
CREATE TABLE "place_snapshots" (
	"id" text PRIMARY KEY NOT NULL,
	"location_id" text NOT NULL,
	"year_min" integer,
	"year_max" integer,
	"precision" text,
	"polity_or_ruler" text,
	"dominant_schools" text[] DEFAULT '{}'::text[] NOT NULL,
	"religious_communities" jsonb DEFAULT '{}'::jsonb NOT NULL,
	"languages" text[] DEFAULT '{}'::text[] NOT NULL,
	"ethnographic_notes" text,
	"citation_id" text NOT NULL,
	"review_state" "evidence_review_state" DEFAULT 'candidate_only' NOT NULL,
	"first_seen_dataset_version_id" text NOT NULL,
	"changed_in_dataset_version_id" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_in_dataset_version_id" text,
	CONSTRAINT "place_snapshots_year_range_check" CHECK ("place_snapshots"."year_min" is null or "place_snapshots"."year_max" is null or "place_snapshots"."year_max" >= "place_snapshots"."year_min"),
	CONSTRAINT "place_snapshots_religious_communities_check" CHECK (jsonb_typeof("place_snapshots"."religious_communities") = 'object')
);
--> statement-breakpoint
CREATE TABLE "timeline_tracks" (
	"id" text PRIMARY KEY NOT NULL,
	"slug" text NOT NULL,
	"title" text NOT NULL,
	"category" text NOT NULL,
	"scope" text NOT NULL,
	"description" text,
	"first_seen_dataset_version_id" text NOT NULL,
	"changed_in_dataset_version_id" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_in_dataset_version_id" text,
	CONSTRAINT "timeline_tracks_slug_key" UNIQUE("slug"),
	CONSTRAINT "timeline_tracks_category_check" CHECK ("timeline_tracks"."category" in ('political', 'world_event', 'technological', 'intellectual_movement', 'demographic_shift', 'legal_theological', 'trade_pilgrimage')),
	CONSTRAINT "timeline_tracks_scope_check" CHECK ("timeline_tracks"."scope" in ('global', 'regional', 'city'))
);
--> statement-breakpoint
ALTER TABLE "historical_events" ADD COLUMN "track_id" text;--> statement-breakpoint
ALTER TABLE "external_tradition_parallels" ADD CONSTRAINT "external_tradition_parallels_hadith_id_fk" FOREIGN KEY ("hadith_id") REFERENCES "public"."hadiths"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "external_tradition_parallels" ADD CONSTRAINT "external_tradition_parallels_citation_id_fk" FOREIGN KEY ("citation_id") REFERENCES "public"."citations"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "external_tradition_parallels" ADD CONSTRAINT "external_tradition_parallels_first_seen_dataset_version_id_fk" FOREIGN KEY ("first_seen_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "external_tradition_parallels" ADD CONSTRAINT "external_tradition_parallels_changed_in_dataset_version_id_fk" FOREIGN KEY ("changed_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "external_tradition_parallels" ADD CONSTRAINT "external_tradition_parallels_retired_in_dataset_version_id_fk" FOREIGN KEY ("retired_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_affiliations" ADD CONSTRAINT "narrator_affiliations_narrator_id_fk" FOREIGN KEY ("narrator_id") REFERENCES "public"."narrators"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_affiliations" ADD CONSTRAINT "narrator_affiliations_citation_id_fk" FOREIGN KEY ("citation_id") REFERENCES "public"."citations"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_affiliations" ADD CONSTRAINT "narrator_affiliations_first_seen_dataset_version_id_fk" FOREIGN KEY ("first_seen_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_affiliations" ADD CONSTRAINT "narrator_affiliations_changed_in_dataset_version_id_fk" FOREIGN KEY ("changed_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_affiliations" ADD CONSTRAINT "narrator_affiliations_retired_in_dataset_version_id_fk" FOREIGN KEY ("retired_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_residences" ADD CONSTRAINT "narrator_residences_narrator_id_fk" FOREIGN KEY ("narrator_id") REFERENCES "public"."narrators"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_residences" ADD CONSTRAINT "narrator_residences_location_id_fk" FOREIGN KEY ("location_id") REFERENCES "public"."locations"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_residences" ADD CONSTRAINT "narrator_residences_citation_id_fk" FOREIGN KEY ("citation_id") REFERENCES "public"."citations"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_residences" ADD CONSTRAINT "narrator_residences_first_seen_dataset_version_id_fk" FOREIGN KEY ("first_seen_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_residences" ADD CONSTRAINT "narrator_residences_changed_in_dataset_version_id_fk" FOREIGN KEY ("changed_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "narrator_residences" ADD CONSTRAINT "narrator_residences_retired_in_dataset_version_id_fk" FOREIGN KEY ("retired_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "place_snapshots" ADD CONSTRAINT "place_snapshots_location_id_fk" FOREIGN KEY ("location_id") REFERENCES "public"."locations"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "place_snapshots" ADD CONSTRAINT "place_snapshots_citation_id_fk" FOREIGN KEY ("citation_id") REFERENCES "public"."citations"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "place_snapshots" ADD CONSTRAINT "place_snapshots_first_seen_dataset_version_id_fk" FOREIGN KEY ("first_seen_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "place_snapshots" ADD CONSTRAINT "place_snapshots_changed_in_dataset_version_id_fk" FOREIGN KEY ("changed_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "place_snapshots" ADD CONSTRAINT "place_snapshots_retired_in_dataset_version_id_fk" FOREIGN KEY ("retired_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "timeline_tracks" ADD CONSTRAINT "timeline_tracks_first_seen_dataset_version_id_fk" FOREIGN KEY ("first_seen_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "timeline_tracks" ADD CONSTRAINT "timeline_tracks_changed_in_dataset_version_id_fk" FOREIGN KEY ("changed_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "timeline_tracks" ADD CONSTRAINT "timeline_tracks_retired_in_dataset_version_id_fk" FOREIGN KEY ("retired_in_dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
CREATE INDEX "external_tradition_parallels_hadith_id_idx" ON "external_tradition_parallels" USING btree ("hadith_id");--> statement-breakpoint
CREATE INDEX "external_tradition_parallels_tradition_source_idx" ON "external_tradition_parallels" USING btree ("tradition_source");--> statement-breakpoint
CREATE INDEX "external_tradition_parallels_citation_id_idx" ON "external_tradition_parallels" USING btree ("citation_id");--> statement-breakpoint
CREATE INDEX "external_tradition_parallels_review_state_idx" ON "external_tradition_parallels" USING btree ("review_state");--> statement-breakpoint
CREATE INDEX "narrator_affiliations_narrator_id_idx" ON "narrator_affiliations" USING btree ("narrator_id");--> statement-breakpoint
CREATE INDEX "narrator_affiliations_kind_idx" ON "narrator_affiliations" USING btree ("kind");--> statement-breakpoint
CREATE INDEX "narrator_affiliations_citation_id_idx" ON "narrator_affiliations" USING btree ("citation_id");--> statement-breakpoint
CREATE INDEX "narrator_affiliations_review_state_idx" ON "narrator_affiliations" USING btree ("review_state");--> statement-breakpoint
CREATE INDEX "narrator_residences_narrator_id_idx" ON "narrator_residences" USING btree ("narrator_id");--> statement-breakpoint
CREATE INDEX "narrator_residences_location_id_idx" ON "narrator_residences" USING btree ("location_id");--> statement-breakpoint
CREATE INDEX "narrator_residences_year_range_idx" ON "narrator_residences" USING btree ("year_min","year_max");--> statement-breakpoint
CREATE INDEX "narrator_residences_citation_id_idx" ON "narrator_residences" USING btree ("citation_id");--> statement-breakpoint
CREATE INDEX "narrator_residences_review_state_idx" ON "narrator_residences" USING btree ("review_state");--> statement-breakpoint
CREATE INDEX "place_snapshots_location_id_idx" ON "place_snapshots" USING btree ("location_id");--> statement-breakpoint
CREATE INDEX "place_snapshots_year_range_idx" ON "place_snapshots" USING btree ("year_min","year_max");--> statement-breakpoint
CREATE INDEX "place_snapshots_location_year_range_idx" ON "place_snapshots" USING btree ("location_id","year_min","year_max");--> statement-breakpoint
CREATE INDEX "place_snapshots_citation_id_idx" ON "place_snapshots" USING btree ("citation_id");--> statement-breakpoint
CREATE INDEX "place_snapshots_review_state_idx" ON "place_snapshots" USING btree ("review_state");--> statement-breakpoint
CREATE INDEX "timeline_tracks_category_idx" ON "timeline_tracks" USING btree ("category");--> statement-breakpoint
ALTER TABLE "historical_events" ADD CONSTRAINT "historical_events_track_id_fk" FOREIGN KEY ("track_id") REFERENCES "public"."timeline_tracks"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
CREATE INDEX "historical_events_track_id_idx" ON "historical_events" USING btree ("track_id");