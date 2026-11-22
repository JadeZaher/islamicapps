ALTER TYPE "public"."narrator_authority" ADD VALUE 'work_register';--> statement-breakpoint
CREATE TABLE "chain_fix_applications" (
	"id" bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY (sequence name "chain_fix_applications_id_seq" INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 START WITH 1 CACHE 1),
	"fix_id" text NOT NULL,
	"hadith_id" text NOT NULL,
	"action" text NOT NULL,
	"effect" text NOT NULL,
	"base_rows" jsonb NOT NULL,
	"written_ids" jsonb NOT NULL,
	"dataset_version_id" text NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"created_by" text NOT NULL,
	CONSTRAINT "chain_fix_applications_action_check" CHECK ("chain_fix_applications"."action" in ('applied', 'reverted')),
	CONSTRAINT "chain_fix_applications_effect_check" CHECK ("chain_fix_applications"."effect" in ('replace_routes', 'set_status', 'annotate')),
	CONSTRAINT "chain_fix_applications_base_rows_check" CHECK (jsonb_typeof("chain_fix_applications"."base_rows" -> 'chains') = 'array' and jsonb_typeof("chain_fix_applications"."base_rows" -> 'chain_mentions') = 'array'
        and jsonb_typeof("chain_fix_applications"."base_rows" -> 'chain_mention_candidates') = 'array')
);
--> statement-breakpoint
CREATE TABLE "chain_fix_decisions" (
	"id" text PRIMARY KEY DEFAULT gen_random_uuid()::text NOT NULL,
	"fix_id" text NOT NULL,
	"hadith_id" text NOT NULL,
	"state" text NOT NULL,
	"effect" text,
	"structure_status" text,
	"runs" integer NOT NULL,
	"text_only_runs" integer NOT NULL,
	"dissenting_runs" integer NOT NULL,
	"models" text[] NOT NULL,
	"hold_codes" text[] DEFAULT '{}'::text[] NOT NULL,
	"why" text NOT NULL,
	"decided_at" timestamp with time zone NOT NULL,
	"supersedes_decision_id" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"created_by" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_by" text NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_by" text,
	CONSTRAINT "chain_fix_decisions_state_check" CHECK ("chain_fix_decisions"."state" in ('submitted', 'disputed', 'outvoted', 'held', 'accepted', 'confirmed', 'rejected', 'superseded', 'stale')),
	CONSTRAINT "chain_fix_decisions_hold_codes_check" CHECK (("chain_fix_decisions"."state" = 'held') = (cardinality("chain_fix_decisions"."hold_codes") > 0) or "chain_fix_decisions"."state" in ('confirmed', 'rejected', 'superseded')),
	CONSTRAINT "chain_fix_decisions_effect_check" CHECK (("chain_fix_decisions"."state" in ('accepted', 'confirmed')) = ("chain_fix_decisions"."effect" is not null)
        and ("chain_fix_decisions"."effect" is null or "chain_fix_decisions"."effect" in ('replace_routes', 'set_status', 'annotate'))
        and (("chain_fix_decisions"."effect" = 'annotate' or "chain_fix_decisions"."effect" is null) = ("chain_fix_decisions"."structure_status" is null))
        and ("chain_fix_decisions"."structure_status" is null or ("chain_fix_decisions"."structure_status" = 'verified_by_reviewer') = ("chain_fix_decisions"."state" = 'confirmed'))
        and ("chain_fix_decisions"."structure_status" is null or "chain_fix_decisions"."structure_status" in ('read_by_model', 'verified_by_reviewer'))),
	CONSTRAINT "chain_fix_decisions_agreement_check" CHECK ("chain_fix_decisions"."state" <> 'accepted' or "chain_fix_decisions"."effect" = 'annotate' or ("chain_fix_decisions"."runs" >= 2 and "chain_fix_decisions"."text_only_runs" >= 1 and "chain_fix_decisions"."runs" >= 2 * "chain_fix_decisions"."dissenting_runs")),
	CONSTRAINT "chain_fix_decisions_counts_check" CHECK ("chain_fix_decisions"."runs" >= 1 and "chain_fix_decisions"."text_only_runs" between 0 and "chain_fix_decisions"."runs" and "chain_fix_decisions"."dissenting_runs" >= 0)
);
--> statement-breakpoint
CREATE TABLE "chain_fix_reviews" (
	"id" text PRIMARY KEY NOT NULL,
	"fix_id" text NOT NULL,
	"reviewer_kind" text NOT NULL,
	"reviewer" text NOT NULL,
	"model_id" text,
	"prompt_path" text,
	"prompt_sha256" text,
	"decision" text NOT NULL,
	"superseded_by_fix_id" text,
	"note" text NOT NULL,
	"citation" jsonb,
	"reviewed_at" timestamp with time zone NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"created_by" text NOT NULL,
	CONSTRAINT "chain_fix_reviews_reviewer_check" CHECK (btrim("chain_fix_reviews"."reviewer") <> '' and btrim("chain_fix_reviews"."note") <> ''),
	CONSTRAINT "chain_fix_reviews_kind_check" CHECK (("chain_fix_reviews"."reviewer_kind" = 'human' and "chain_fix_reviews"."model_id" is null and "chain_fix_reviews"."prompt_path" is null and "chain_fix_reviews"."prompt_sha256" is null)
        or ("chain_fix_reviews"."reviewer_kind" = 'ai' and btrim(coalesce("chain_fix_reviews"."model_id", '')) <> '' and btrim(coalesce("chain_fix_reviews"."prompt_path", '')) <> '' and "chain_fix_reviews"."prompt_sha256" ~ '^[0-9a-f]{64}$')),
	CONSTRAINT "chain_fix_reviews_decision_check" CHECK ("chain_fix_reviews"."decision" in ('confirmed', 'rejected', 'superseded') and ("chain_fix_reviews"."decision" = 'superseded') = ("chain_fix_reviews"."superseded_by_fix_id" is not null)),
	CONSTRAINT "chain_fix_reviews_citation_check" CHECK ("chain_fix_reviews"."citation" is null or (btrim(coalesce("chain_fix_reviews"."citation" ->> 'quote', '')) <> ''
        and (coalesce("chain_fix_reviews"."citation" ->> 'url', '') ~ '^https?://\S+$' or btrim(coalesce("chain_fix_reviews"."citation" ->> 'edition_locator', '')) <> '')))
);
--> statement-breakpoint
CREATE TABLE "chain_fix_submissions" (
	"id" text PRIMARY KEY NOT NULL,
	"fix_id" text NOT NULL,
	"hadith_id" text NOT NULL,
	"view" text NOT NULL,
	"reading" jsonb NOT NULL,
	"base_chain_sha256" text NOT NULL,
	"base_read_from" text NOT NULL,
	"reason" text NOT NULL,
	"evidence" jsonb NOT NULL,
	"computed_evidence" jsonb NOT NULL,
	"external_citation" jsonb,
	"review_kind" text DEFAULT 'specialist' NOT NULL,
	"specialist_id" text NOT NULL,
	"specialist_version" text NOT NULL,
	"prompt_path" text NOT NULL,
	"prompt_version" text NOT NULL,
	"prompt_sha256" text NOT NULL,
	"model_id" text NOT NULL,
	"provider_runtime" text NOT NULL,
	"orchestrator_run_id" text NOT NULL,
	"packet_path" text NOT NULL,
	"packet_sha256" text NOT NULL,
	"packet_item_id" text NOT NULL,
	"started_at" timestamp with time zone NOT NULL,
	"finished_at" timestamp with time zone NOT NULL,
	"submitted_at" timestamp with time zone NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"created_by" text NOT NULL,
	CONSTRAINT "chain_fix_submissions_view_check" CHECK ("chain_fix_submissions"."view" in ('text_only', 'text_and_stored_chain')),
	CONSTRAINT "chain_fix_submissions_review_kind_check" CHECK ("chain_fix_submissions"."review_kind" = 'specialist'),
	CONSTRAINT "chain_fix_submissions_prompt_sha256_check" CHECK ("chain_fix_submissions"."prompt_sha256" ~ '^[0-9a-f]{64}$'),
	CONSTRAINT "chain_fix_submissions_times_check" CHECK ("chain_fix_submissions"."finished_at" >= "chain_fix_submissions"."started_at" and "chain_fix_submissions"."submitted_at" >= "chain_fix_submissions"."finished_at"),
	CONSTRAINT "chain_fix_submissions_provenance_check" CHECK (btrim("chain_fix_submissions"."model_id") <> '' and btrim("chain_fix_submissions"."provider_runtime") <> '' and btrim("chain_fix_submissions"."orchestrator_run_id") <> ''),
	CONSTRAINT "chain_fix_submissions_evidence_check" CHECK (jsonb_typeof("chain_fix_submissions"."evidence") = 'array' and jsonb_array_length("chain_fix_submissions"."evidence") > 0 and btrim("chain_fix_submissions"."reason") <> ''),
	CONSTRAINT "chain_fix_submissions_external_citation_check" CHECK ("chain_fix_submissions"."external_citation" is null or (btrim(coalesce("chain_fix_submissions"."external_citation" ->> 'quote', '')) <> ''
        and (coalesce("chain_fix_submissions"."external_citation" ->> 'url', '') ~ '^https?://\S+$' or btrim(coalesce("chain_fix_submissions"."external_citation" ->> 'edition_locator', '')) <> '')))
);
--> statement-breakpoint
CREATE TABLE "chain_fix_work_settings" (
	"collection_id" text PRIMARY KEY NOT NULL,
	"read_by_model_in_network" boolean DEFAULT false NOT NULL,
	"note" text NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"created_by" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_by" text NOT NULL,
	"retired_at" timestamp with time zone,
	"retired_by" text,
	CONSTRAINT "chain_fix_work_settings_note_check" CHECK (btrim("chain_fix_work_settings"."note") <> '')
);
--> statement-breakpoint
CREATE TABLE "chain_fixes" (
	"id" text PRIMARY KEY NOT NULL,
	"hadith_id" text NOT NULL,
	"arabic_sha256" text NOT NULL,
	"reader_text_sha256" text NOT NULL,
	"text_layout" text NOT NULL,
	"routes_key" text NOT NULL,
	"fix_kinds" text[] NOT NULL,
	"planned" jsonb NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"created_by" text NOT NULL,
	CONSTRAINT "chain_fixes_id_check" CHECK ("chain_fixes"."id" ~ '^chain-fix:[0-9a-f]{24}$'),
	CONSTRAINT "chain_fixes_hashes_check" CHECK ("chain_fixes"."arabic_sha256" ~ '^[0-9a-f]{64}$' and "chain_fixes"."reader_text_sha256" ~ '^[0-9a-f]{64}$'),
	CONSTRAINT "chain_fixes_text_layout_check" CHECK ("chain_fixes"."text_layout" in ('full_text', 'chain_field_then_matn')),
	CONSTRAINT "chain_fixes_fix_kinds_check" CHECK (cardinality("chain_fixes"."fix_kinds") > 0 and "chain_fixes"."fix_kinds" <@ array['no_change', 'link_added', 'link_removed', 'surface_changed', 'route_split', 'routes_merged', 'shared_tail_attached', 'chain_removed', 'chain_added']::text[]
        and (not ('no_change' = any ("chain_fixes"."fix_kinds")) or cardinality("chain_fixes"."fix_kinds") = 1)),
	CONSTRAINT "chain_fixes_planned_check" CHECK (jsonb_typeof("chain_fixes"."planned") = 'object' and jsonb_typeof("chain_fixes"."planned" -> 'chains') = 'array')
);
--> statement-breakpoint
ALTER TABLE "narrator_source_profiles" DROP CONSTRAINT "narrator_source_profiles_source_check";--> statement-breakpoint
ALTER TABLE "chains" DROP CONSTRAINT "chains_structure_status_check";--> statement-breakpoint
ALTER TABLE "chains" ADD COLUMN "chain_fix_id" text;--> statement-breakpoint
ALTER TABLE "chains" ADD COLUMN "compiler_narrator_id" text;--> statement-breakpoint
ALTER TABLE "chains" ADD COLUMN "compiler_link" text;--> statement-breakpoint
ALTER TABLE "chain_fix_applications" ADD CONSTRAINT "chain_fix_applications_fix_id_fk" FOREIGN KEY ("fix_id") REFERENCES "public"."chain_fixes"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chain_fix_applications" ADD CONSTRAINT "chain_fix_applications_hadith_id_fk" FOREIGN KEY ("hadith_id") REFERENCES "public"."hadiths"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chain_fix_applications" ADD CONSTRAINT "chain_fix_applications_dataset_version_id_fk" FOREIGN KEY ("dataset_version_id") REFERENCES "public"."dataset_versions"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chain_fix_decisions" ADD CONSTRAINT "chain_fix_decisions_fix_id_fk" FOREIGN KEY ("fix_id") REFERENCES "public"."chain_fixes"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chain_fix_decisions" ADD CONSTRAINT "chain_fix_decisions_hadith_id_fk" FOREIGN KEY ("hadith_id") REFERENCES "public"."hadiths"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chain_fix_reviews" ADD CONSTRAINT "chain_fix_reviews_fix_id_fk" FOREIGN KEY ("fix_id") REFERENCES "public"."chain_fixes"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chain_fix_reviews" ADD CONSTRAINT "chain_fix_reviews_superseded_by_fix_id_fk" FOREIGN KEY ("superseded_by_fix_id") REFERENCES "public"."chain_fixes"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chain_fix_submissions" ADD CONSTRAINT "chain_fix_submissions_fix_id_fk" FOREIGN KEY ("fix_id") REFERENCES "public"."chain_fixes"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chain_fix_submissions" ADD CONSTRAINT "chain_fix_submissions_hadith_id_fk" FOREIGN KEY ("hadith_id") REFERENCES "public"."hadiths"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chain_fix_work_settings" ADD CONSTRAINT "chain_fix_work_settings_collection_id_fk" FOREIGN KEY ("collection_id") REFERENCES "public"."collections"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chain_fixes" ADD CONSTRAINT "chain_fixes_hadith_id_fk" FOREIGN KEY ("hadith_id") REFERENCES "public"."hadiths"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
CREATE INDEX "chain_fix_applications_fix_id_idx" ON "chain_fix_applications" USING btree ("fix_id");--> statement-breakpoint
CREATE UNIQUE INDEX "chain_fix_decisions_live_fix_key" ON "chain_fix_decisions" USING btree ("fix_id") WHERE "chain_fix_decisions"."retired_at" is null;--> statement-breakpoint
CREATE UNIQUE INDEX "chain_fix_decisions_live_effect_key" ON "chain_fix_decisions" USING btree ("hadith_id") WHERE "chain_fix_decisions"."retired_at" is null and "chain_fix_decisions"."effect" is not null;--> statement-breakpoint
CREATE INDEX "chain_fix_reviews_fix_id_idx" ON "chain_fix_reviews" USING btree ("fix_id");--> statement-breakpoint
CREATE INDEX "chain_fix_submissions_fix_id_idx" ON "chain_fix_submissions" USING btree ("fix_id");--> statement-breakpoint
CREATE INDEX "chain_fix_submissions_hadith_id_idx" ON "chain_fix_submissions" USING btree ("hadith_id");--> statement-breakpoint
CREATE INDEX "chain_fixes_hadith_id_idx" ON "chain_fixes" USING btree ("hadith_id");--> statement-breakpoint
ALTER TABLE "chains" ADD CONSTRAINT "chains_chain_fix_id_fk" FOREIGN KEY ("chain_fix_id") REFERENCES "public"."chain_fixes"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chains" ADD CONSTRAINT "chains_compiler_narrator_id_fk" FOREIGN KEY ("compiler_narrator_id") REFERENCES "public"."narrators"("id") ON DELETE restrict ON UPDATE no action;--> statement-breakpoint
CREATE INDEX "chains_chain_fix_id_idx" ON "chains" USING btree ("chain_fix_id") WHERE "chains"."chain_fix_id" is not null;--> statement-breakpoint
CREATE INDEX "chains_compiler_narrator_id_idx" ON "chains" USING btree ("compiler_narrator_id") WHERE "chains"."compiler_narrator_id" is not null;--> statement-breakpoint
ALTER TABLE "narrator_source_profiles" ADD CONSTRAINT "narrator_source_profiles_source_check" CHECK ("narrator_source_profiles"."source" in ('hadith_kg', 'riwayat', 'imam_register', 'work_register'));--> statement-breakpoint
ALTER TABLE "chains" ADD CONSTRAINT "chains_compiler_check" CHECK (("chains"."compiler_narrator_id" is null) = ("chains"."compiler_link" is null) and ("chains"."compiler_link" is null or "chains"."compiler_link" in ('direct', 'indirect')));--> statement-breakpoint
ALTER TABLE "chains" ADD CONSTRAINT "chains_structure_status_check" CHECK ("chains"."structure_status" is null or ("chains"."structure_status" = 'checked_by_rule' and "chains"."structure_reasons" is null) or ("chains"."structure_status" = 'uncertain' and cardinality("chains"."structure_reasons") > 0) or ("chains"."structure_status" in ('read_by_model', 'verified_by_reviewer') and "chains"."structure_reasons" is null and "chains"."chain_fix_id" is not null));
--> statement-breakpoint
-- Hand-written (src/db/AGENTS.md §Chain fixes, §Compiler as first transmitter). Expand only.
-- Per-work setting, shipped off for every work (owner 2026-11-22): a chain read by model and awaiting final review feeds no list.
INSERT INTO "chain_fix_work_settings" ("collection_id", "read_by_model_in_network", "note", "created_by", "updated_by")
SELECT c.id, false, 'owner 2026-11-22: off until the agreed-reading error rate is measured for this work', 'migration:0019', 'migration:0019'
FROM "collections" c
WHERE c.retired_at IS NULL
ON CONFLICT ("collection_id") DO NOTHING;
--> statement-breakpoint
CREATE OR REPLACE VIEW "public_chain_links" AS
SELECT m.id,
       m.chain_id,
       m.hadith_id,
       c.branch,
       m.position,
       m.surface_ar,
       m.link_kind,
       m.resolution,
       (link.id IS NOT NULL)                                         AS is_link,
       link.id                                                       AS narrator_id,
       CASE WHEN link.id IS NOT NULL THEN m.confidence END           AS confidence,
       m.name_latin,
       m.name_latin_basis,
       m.name_latin_narrator_id,
       CASE WHEN link.id IS NOT NULL THEN m.extraction_method END    AS standing_basis,
       m.identity_withheld_reason,
       m.inherited_from_mention_id,
       c.suspension                                                  AS chain_suspension,
       c.missing_link_after                                          AS chain_missing_link_after,
       c.structure_status                                            AS chain_structure_status,
       c.structure_reasons                                           AS chain_structure_reasons,
       c.chain_fix_id                                                AS chain_fix_id,
       c.compiler_narrator_id                                        AS chain_compiler_narrator_id,
       c.compiler_link                                               AS chain_compiler_link
FROM chain_mentions m
JOIN chains c ON c.id = m.chain_id AND c.retired_at IS NULL
JOIN public_hadiths h ON h.id = m.hadith_id
LEFT JOIN narrators link
       ON link.id = m.narrator_id
      AND link.retired_at IS NULL
      AND m.resolution IN ('source_index', 'human_verified', 'derived_relation_verified')
WHERE m.retired_at IS NULL;
--> statement-breakpoint
-- public_chain_fix_labels: what the chain view says under a public chain read by a model. One row per live chain that names a
-- fix whose live decision has an effect: the models, when, whether awaiting final review, and every human confirmation.
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
                 WHERE r.decision = 'confirmed'), '[]'::jsonb) AS human_confirmations
FROM chains c
JOIN chain_fixes f ON f.id = c.chain_fix_id
JOIN chain_fix_decisions d ON d.fix_id = f.id AND d.retired_at IS NULL AND d.effect IS NOT NULL
JOIN public_hadiths h ON h.id = c.hadith_id
WHERE c.retired_at IS NULL
  AND f.arabic_sha256 = h.arabic_sha256;
--> statement-breakpoint
-- narrator_transmissions (0017 body) with two changes: (1) the structure guard names what may feed lists: rule-checked,
-- human-verified, and read-by-model only where the work's setting allows it (off everywhere at 0019); (2) the work's compiler
-- is the student of position 0 when the chain says he heard him (compiler_link = 'direct', no suspension).
DROP MATERIALIZED VIEW "narrator_transmissions";
--> statement-breakpoint
CREATE MATERIALIZED VIEW "narrator_transmissions" AS
WITH feeding AS (
  SELECT c.id, c.hadith_id, c.compiler_narrator_id, c.compiler_link, c.suspension
  FROM chains c
  WHERE c.retired_at IS NULL
    AND (c.structure_status IS NULL
         OR c.structure_status IN ('checked_by_rule', 'verified_by_reviewer')
         OR (c.structure_status = 'read_by_model'
             AND EXISTS (SELECT 1 FROM hadiths h
                         JOIN chain_fix_work_settings s ON s.collection_id = h.collection_id
                         WHERE h.id = c.hadith_id AND s.retired_at IS NULL AND s.read_by_model_in_network)))
),
standing AS (
  SELECT m.chain_id, m.hadith_id, m.position, m.narrator_id, m.confidence, m.extraction_method, m.resolution_basis
  FROM chain_mentions m
  JOIN feeding c ON c.id = m.chain_id
  WHERE m.retired_at IS NULL
    AND m.narrator_id IS NOT NULL
    AND m.resolution IN ('source_index', 'human_verified', 'derived_relation_verified')
    -- 0015: an unnamed transmitter or a back-reference is a label, never one side of a pair
    AND m.link_kind NOT IN ('anonymous', 'not_a_narrator')
),
seams AS (
  SELECT chain_id, min(position) AS first_pos, max(position) AS last_pos
  FROM standing
  GROUP BY chain_id, narrator_id
  HAVING count(*) > 1
),
pairs AS (
  SELECT a.narrator_id AS student_id, b.narrator_id AS teacher_id,
         a.hadith_id, a.position AS student_pos, b.position AS teacher_pos,
         least(a.confidence, b.confidence) AS confidence,
         a.extraction_method
  FROM standing a
  JOIN standing b ON b.chain_id = a.chain_id AND b.position = a.position + 1
  WHERE ((a.resolution_basis = 'source_index' AND b.resolution_basis = 'source_index')
      OR (a.resolution_basis = 'human_decision' AND b.resolution_basis = 'human_decision'))
    AND NOT EXISTS (SELECT 1 FROM seams s
                    WHERE s.chain_id = a.chain_id AND s.first_pos <= a.position AND s.last_pos >= b.position)
  UNION ALL
  -- 0019: the compiler of the work (derived, never written) and the shaykh at position 0; student position -1
  SELECT c.compiler_narrator_id AS student_id, b.narrator_id AS teacher_id,
         b.hadith_id, -1 AS student_pos, b.position AS teacher_pos,
         b.confidence AS confidence,
         'compiler_of_work' AS extraction_method
  FROM feeding c
  JOIN standing b ON b.chain_id = c.id AND b.position = 0
  JOIN narrators cn ON cn.id = c.compiler_narrator_id AND cn.retired_at IS NULL
  WHERE c.compiler_link = 'direct'
    AND c.suspension IS NULL
    AND b.narrator_id <> c.compiler_narrator_id
    AND b.resolution_basis IN ('source_index', 'human_decision')
),
grouped AS (
  SELECT p.student_id, p.teacher_id,
         count(DISTINCT p.hadith_id)::int                                 AS hadith_count,
         -- one occurrence per report position pair, not per tahwil or co-transmitter branch
         count(DISTINCT (p.hadith_id, p.student_pos, p.teacher_pos))::int AS occurrence_count,
         max(p.confidence)                                                AS confidence,
         array_agg(DISTINCT coalesce(p.extraction_method, 'unspecified')) AS extraction_methods
  FROM pairs p
  GROUP BY p.student_id, p.teacher_id
)
SELECT g.student_id, g.teacher_id, g.hadith_count, g.occurrence_count, g.confidence, g.extraction_methods,
       CASE
         WHEN r.rule IS NOT NULL AND r.attested                            THEN 'disputed'
         WHEN r.rule IS NOT NULL                                           THEN 'impossible'
         WHEN sl.disputed OR tl.disputed                                   THEN 'disputed'
         WHEN nullif(sl.birth_max, 0) <= nullif(tl.death_min, 0)           THEN 'plausible'
         ELSE 'unknown'
       END                                                                 AS temporal_plausibility,
       CASE
         WHEN r.rule IS NOT NULL AND r.attested
           THEN 'the lexicon lists this teacher, but its years say ' || r.rule
         WHEN r.rule IS NOT NULL THEN r.rule || ', on the most permissive bounds'
         WHEN sl.disputed OR tl.disputed THEN 'verified lifespan claims conflict'
       END                                                                 AS temporal_reason
FROM grouped g
LEFT JOIN narrator_lifespans sl ON sl.narrator_id = g.student_id
LEFT JOIN narrator_lifespans tl ON tl.narrator_id = g.teacher_id
CROSS JOIN LATERAL (
  SELECT CASE
           WHEN nullif(sl.birth_min, 0) > nullif(tl.death_max, 0)      THEN 'student born after teacher died'
           WHEN nullif(tl.birth_min, 0) > nullif(sl.death_max, 0)      THEN 'teacher born after student died'
           WHEN nullif(tl.death_min, 0) > nullif(sl.death_max, 0) + 60 THEN 'teacher died more than 60 years after student'
         END AS rule,
         EXISTS (SELECT 1 FROM narrator_teachers t
                 WHERE t.student_id = g.student_id AND t.teacher_id = g.teacher_id AND t.retired_at IS NULL) AS attested
) r;
--> statement-breakpoint
CREATE UNIQUE INDEX "narrator_transmissions_pair_key" ON "narrator_transmissions" ("student_id", "teacher_id");
--> statement-breakpoint
CREATE INDEX "narrator_transmissions_teacher_id_idx" ON "narrator_transmissions" ("teacher_id");
