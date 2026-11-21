-- epochs and published_epochs (design section 5.9), promoted 2026-11-21 from src/db/ops/pending/epochs.pending.sql
-- (written by the history lane while 0007 was in progress). Idempotent, so a database that already ran the
-- pending file is unaffected. Unqualified names: the query fixture runs this inside its private schema.

CREATE TABLE IF NOT EXISTS "epochs" (
	"id" text PRIMARY KEY NOT NULL,
	"name" text NOT NULL,
	"name_arabic" text,
	"alternate_names" jsonb DEFAULT '[]'::jsonb NOT NULL,
	"parent_epoch_id" text,
	"tradition_context" "hadith_tradition",
	"start_year_hijri" integer,
	"start_year_hijri_latest" integer,
	"end_year_hijri" integer,
	"end_year_hijri_latest" integer,
	"boundary_note" text,
	"overview" text,
	"verification_status" "event_verification" DEFAULT 'unverified' NOT NULL,
	"publication_ready" boolean DEFAULT false NOT NULL,
	"citation_id" text,
	"origin" "record_origin" NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"created_by" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_by" text NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_by" text,
	CONSTRAINT "epochs_parent_epoch_id_fk" FOREIGN KEY ("parent_epoch_id") REFERENCES "epochs"("id") ON DELETE restrict ON UPDATE no action,
	CONSTRAINT "epochs_citation_id_fk" FOREIGN KEY ("citation_id") REFERENCES "citations"("id") ON DELETE restrict ON UPDATE no action,
	CONSTRAINT "epochs_alternate_names_check" CHECK (jsonb_typeof("alternate_names") = 'array'),
	CONSTRAINT "epochs_start_range_check" CHECK ("start_year_hijri_latest" IS NULL OR ("start_year_hijri" IS NOT NULL AND "start_year_hijri_latest" >= "start_year_hijri")),
	CONSTRAINT "epochs_end_range_check" CHECK ("end_year_hijri_latest" IS NULL OR ("end_year_hijri" IS NOT NULL AND "end_year_hijri_latest" >= "end_year_hijri")),
	CONSTRAINT "epochs_year_order_check" CHECK ("start_year_hijri" IS NULL OR "end_year_hijri" IS NULL OR coalesce("end_year_hijri_latest", "end_year_hijri") >= "start_year_hijri"),
	CONSTRAINT "epochs_publication_gate_check" CHECK (NOT "publication_ready" OR ("verification_status" IN ('human_verified', 'source_verified') AND "citation_id" IS NOT NULL))
);
--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "epochs_year_range_idx" ON "epochs" ("start_year_hijri", "end_year_hijri") WHERE "retired_at" IS NULL;
--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "epochs_parent_epoch_id_idx" ON "epochs" ("parent_epoch_id");
--> statement-breakpoint
-- published_epochs: the write gate again on read, plus a live, reviewed citation (section 5.8), with outer bounds.
CREATE OR REPLACE VIEW "published_epochs" AS
SELECT e.*,
       e.start_year_hijri                                     AS epoch_start,
       coalesce(e.end_year_hijri_latest, e.end_year_hijri)    AS epoch_end
FROM epochs e
JOIN citations c ON c.id = e.citation_id AND c.retired_at IS NULL AND c.review_state IN ('human_verified', 'source_verified')
WHERE e.retired_at IS NULL
  AND e.start_year_hijri IS NOT NULL
  AND e.publication_ready
  AND e.verification_status IN ('human_verified', 'source_verified');
