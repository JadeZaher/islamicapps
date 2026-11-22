/**
 * Chain fixes (0019): model readers' readings of a report's chains, their agreement, final review and database writes.
 * Design: docs/review/chain-fix-pipeline.md; rationale: src/db/AGENTS.md §Chain fixes. One writer: src/db/ops/chain-fix-apply.ts.
 */
import { sql } from 'drizzle-orm';
import { bigint, boolean, check, index, integer, jsonb, pgTable, pgView, text, timestamp, uniqueIndex } from 'drizzle-orm/pg-core';
import { curationBookkeeping, isLive, restrictForeignKey } from './columns';
import { collections, hadiths } from './corpus';
import { datasetVersions } from './operations';

export const CHAIN_FIX_KINDS = ['no_change', 'link_added', 'link_removed', 'surface_changed', 'route_split', 'routes_merged', 'shared_tail_attached', 'chain_removed', 'chain_added'] as const;
export const CHAIN_FIX_STATES = ['submitted', 'disputed', 'outvoted', 'held', 'accepted', 'confirmed', 'rejected', 'superseded', 'stale'] as const;
/** The two structure statuses a fix sets (added to `chains_structure_status_check`); "verified" only after a human confirmation. */
export const CHAIN_FIX_STRUCTURE_STATUSES = ['read_by_model', 'verified_by_reviewer'] as const;

/** A reading of one report's chains bound to the exact text; readers agree on it, reviewers judge it. Immutable. */
export const chainFixes = pgTable(
  'chain_fixes',
  {
    id: text('id').primaryKey(),
    hadithId: text('hadith_id').notNull(),
    arabicSha256: text('arabic_sha256').notNull(),
    readerTextSha256: text('reader_text_sha256').notNull(),
    textLayout: text('text_layout').notNull(),
    routesKey: text('routes_key').notNull(),
    fixKinds: text('fix_kinds').array().notNull(),
    planned: jsonb('planned').notNull(),
    /** 0021: `no_chain_by_reading` when the readers found no isnad in the text (no planned chain); null for a reading with routes. */
    disposition: text('disposition'),
    createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
    createdBy: text('created_by').notNull(),
  },
  (table) => [
    restrictForeignKey('chain_fixes_hadith_id_fk', table.hadithId, hadiths.id),
    check(
      'chain_fixes_disposition_check',
      sql`${table.disposition} is null or (${table.disposition} = 'no_chain_by_reading' and jsonb_array_length(${table.planned} -> 'chains') = 0)`,
    ),
    check('chain_fixes_id_check', sql`${table.id} ~ '^chain-fix:[0-9a-f]{24}$'`),
    check('chain_fixes_hashes_check', sql`${table.arabicSha256} ~ '^[0-9a-f]{64}$' and ${table.readerTextSha256} ~ '^[0-9a-f]{64}$'`),
    check('chain_fixes_text_layout_check', sql`${table.textLayout} in ('full_text', 'chain_field_then_matn')`),
    check(
      'chain_fixes_fix_kinds_check',
      sql`cardinality(${table.fixKinds}) > 0 and ${table.fixKinds} <@ array['no_change', 'link_added', 'link_removed', 'surface_changed', 'route_split', 'routes_merged', 'shared_tail_attached', 'chain_removed', 'chain_added']::text[]
        and (not ('no_change' = any (${table.fixKinds})) or cardinality(${table.fixKinds}) = 1)`,
    ),
    check('chain_fixes_planned_check', sql`jsonb_typeof(${table.planned}) = 'object' and jsonb_typeof(${table.planned} -> 'chains') = 'array'`),
    index('chain_fixes_hadith_id_idx').on(table.hadithId),
  ],
);

/** One reader run's submission of a fix, with its full provenance and quotes. Immutable. */
export const chainFixSubmissions = pgTable(
  'chain_fix_submissions',
  {
    id: text('id').primaryKey(),
    fixId: text('fix_id').notNull(),
    hadithId: text('hadith_id').notNull(),
    view: text('view').notNull(),
    reading: jsonb('reading').notNull(),
    baseChainSha256: text('base_chain_sha256').notNull(),
    baseReadFrom: text('base_read_from').notNull(),
    reason: text('reason').notNull(),
    evidence: jsonb('evidence').notNull(),
    computedEvidence: jsonb('computed_evidence').notNull(),
    externalCitation: jsonb('external_citation'),
    reviewKind: text('review_kind').notNull().default('specialist'),
    specialistId: text('specialist_id').notNull(),
    specialistVersion: text('specialist_version').notNull(),
    promptPath: text('prompt_path').notNull(),
    promptVersion: text('prompt_version').notNull(),
    promptSha256: text('prompt_sha256').notNull(),
    /** 0021 (v3_2: 0022): the reader tool (v3, v3_1, v3_2) that validated, expanded and held a v3-shaped reading; the prompt columns name what the reader ran. */
    toolVersion: text('tool_version'),
    /** 0021: the earlier reports an inherited reading takes names from ({ref, previous_report_id, supplies, surfaces}). */
    inheritedFrom: jsonb('inherited_from'),
    modelId: text('model_id').notNull(),
    providerRuntime: text('provider_runtime').notNull(),
    orchestratorRunId: text('orchestrator_run_id').notNull(),
    packetPath: text('packet_path').notNull(),
    packetSha256: text('packet_sha256').notNull(),
    packetItemId: text('packet_item_id').notNull(),
    startedAt: timestamp('started_at', { withTimezone: true }).notNull(),
    finishedAt: timestamp('finished_at', { withTimezone: true }).notNull(),
    submittedAt: timestamp('submitted_at', { withTimezone: true }).notNull(),
    createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
    createdBy: text('created_by').notNull(),
  },
  (table) => [
    restrictForeignKey('chain_fix_submissions_fix_id_fk', table.fixId, chainFixes.id),
    restrictForeignKey('chain_fix_submissions_hadith_id_fk', table.hadithId, hadiths.id),
    // 0020: `text_and_context` (reader v3): the text and the sources' context, never the stored chain; blind for agreement.
    check('chain_fix_submissions_view_check', sql`${table.view} in ('text_only', 'text_and_context', 'text_and_stored_chain')`),
    check('chain_fix_submissions_review_kind_check', sql`${table.reviewKind} = 'specialist'`),
    check('chain_fix_submissions_prompt_sha256_check', sql`${table.promptSha256} ~ '^[0-9a-f]{64}$'`),
    check('chain_fix_submissions_tool_version_check', sql`${table.toolVersion} is null or ${table.toolVersion} in ('v3', 'v3_1', 'v3_2')`),
    check('chain_fix_submissions_inherited_from_check', sql`${table.inheritedFrom} is null or jsonb_typeof(${table.inheritedFrom}) = 'array'`),
    check('chain_fix_submissions_times_check', sql`${table.finishedAt} >= ${table.startedAt} and ${table.submittedAt} >= ${table.finishedAt}`),
    check('chain_fix_submissions_provenance_check', sql`btrim(${table.modelId}) <> '' and btrim(${table.providerRuntime}) <> '' and btrim(${table.orchestratorRunId}) <> ''`),
    check('chain_fix_submissions_evidence_check', sql`jsonb_typeof(${table.evidence}) = 'array' and jsonb_array_length(${table.evidence}) > 0 and btrim(${table.reason}) <> ''`),
    check(
      'chain_fix_submissions_external_citation_check',
      sql`${table.externalCitation} is null or (btrim(coalesce(${table.externalCitation} ->> 'quote', '')) <> ''
        and (coalesce(${table.externalCitation} ->> 'url', '') ~ '^https?://\\S+$' or btrim(coalesce(${table.externalCitation} ->> 'edition_locator', '')) <> ''))`,
    ),
    index('chain_fix_submissions_fix_id_idx').on(table.fixId),
    index('chain_fix_submissions_hadith_id_idx').on(table.hadithId),
  ],
);

/** The decided state of a fix; revising retires the live row (`supersedes_decision_id`): retired rows are the transitions. */
export const chainFixDecisions = pgTable(
  'chain_fix_decisions',
  {
    id: text('id').primaryKey().default(sql`gen_random_uuid()::text`),
    fixId: text('fix_id').notNull(),
    hadithId: text('hadith_id').notNull(),
    state: text('state').notNull(),
    effect: text('effect'),
    structureStatus: text('structure_status'),
    runs: integer('runs').notNull(),
    textOnlyRuns: integer('text_only_runs').notNull(),
    dissentingRuns: integer('dissenting_runs').notNull(),
    models: text('models').array().notNull(),
    /** Why the tool holds a reading for a third reader or a person (chain-reader/context/HOLDS.md); empty unless held. */
    holdCodes: text('hold_codes').array().notNull().default(sql`'{}'::text[]`),
    why: text('why').notNull(),
    decidedAt: timestamp('decided_at', { withTimezone: true }).notNull(),
    supersedesDecisionId: text('supersedes_decision_id'),
    ...curationBookkeeping(),
  },
  (table) => [
    restrictForeignKey('chain_fix_decisions_fix_id_fk', table.fixId, chainFixes.id),
    restrictForeignKey('chain_fix_decisions_hadith_id_fk', table.hadithId, hadiths.id),
    check(
      'chain_fix_decisions_state_check',
      sql`${table.state} in ('submitted', 'disputed', 'outvoted', 'held', 'accepted', 'confirmed', 'rejected', 'superseded', 'stale')`,
    ),
    check(
      'chain_fix_decisions_hold_codes_check',
      sql`(${table.state} = 'held') = (cardinality(${table.holdCodes}) > 0) or ${table.state} in ('confirmed', 'rejected', 'superseded')`,
    ),
    check(
      'chain_fix_decisions_effect_check',
      sql`(${table.state} in ('accepted', 'confirmed')) = (${table.effect} is not null)
        and (${table.effect} is null or ${table.effect} in ('replace_routes', 'set_status', 'annotate'))
        and ((${table.effect} = 'annotate' or ${table.effect} is null) = (${table.structureStatus} is null))
        and (${table.structureStatus} is null or (${table.structureStatus} = 'verified_by_reviewer') = (${table.state} = 'confirmed'))
        and (${table.structureStatus} is null or ${table.structureStatus} in ('read_by_model', 'verified_by_reviewer'))`,
    ),
    check(
      'chain_fix_decisions_agreement_check',
      sql`${table.state} <> 'accepted' or ${table.effect} = 'annotate' or (${table.runs} >= 2 and ${table.textOnlyRuns} >= 1 and ${table.runs} >= 2 * ${table.dissentingRuns})`,
    ),
    check('chain_fix_decisions_counts_check', sql`${table.runs} >= 1 and ${table.textOnlyRuns} between 0 and ${table.runs} and ${table.dissentingRuns} >= 0`),
    uniqueIndex('chain_fix_decisions_live_fix_key').on(table.fixId).where(isLive(table.retiredAt)),
    uniqueIndex('chain_fix_decisions_live_effect_key').on(table.hadithId).where(sql`${table.retiredAt} is null and ${table.effect} is not null`),
  ],
);

/** One row per review by one reviewer; many per fix. Human: name and date. AI: model and prompt. The latest per reviewer counts. */
export const chainFixReviews = pgTable(
  'chain_fix_reviews',
  {
    id: text('id').primaryKey(),
    fixId: text('fix_id').notNull(),
    reviewerKind: text('reviewer_kind').notNull(),
    reviewer: text('reviewer').notNull(),
    modelId: text('model_id'),
    promptPath: text('prompt_path'),
    promptSha256: text('prompt_sha256'),
    decision: text('decision').notNull(),
    supersededByFixId: text('superseded_by_fix_id'),
    note: text('note').notNull(),
    citation: jsonb('citation'),
    reviewedAt: timestamp('reviewed_at', { withTimezone: true }).notNull(),
    createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
    createdBy: text('created_by').notNull(),
  },
  (table) => [
    restrictForeignKey('chain_fix_reviews_fix_id_fk', table.fixId, chainFixes.id),
    restrictForeignKey('chain_fix_reviews_superseded_by_fix_id_fk', table.supersededByFixId, chainFixes.id),
    check('chain_fix_reviews_reviewer_check', sql`btrim(${table.reviewer}) <> '' and btrim(${table.note}) <> ''`),
    check(
      'chain_fix_reviews_kind_check',
      sql`(${table.reviewerKind} = 'human' and ${table.modelId} is null and ${table.promptPath} is null and ${table.promptSha256} is null)
        or (${table.reviewerKind} = 'ai' and btrim(coalesce(${table.modelId}, '')) <> '' and btrim(coalesce(${table.promptPath}, '')) <> '' and ${table.promptSha256} ~ '^[0-9a-f]{64}$')`,
    ),
    check(
      'chain_fix_reviews_decision_check',
      sql`${table.decision} in ('confirmed', 'rejected', 'superseded') and (${table.decision} = 'superseded') = (${table.supersededByFixId} is not null)`,
    ),
    check(
      'chain_fix_reviews_citation_check',
      sql`${table.citation} is null or (btrim(coalesce(${table.citation} ->> 'quote', '')) <> ''
        and (coalesce(${table.citation} ->> 'url', '') ~ '^https?://\\S+$' or btrim(coalesce(${table.citation} ->> 'edition_locator', '')) <> ''))`,
    ),
    index('chain_fix_reviews_fix_id_idx').on(table.fixId),
  ],
);

/** Every database write of a fix, with the rows as they were before it (an exact revert) and the load version. */
export const chainFixApplications = pgTable(
  'chain_fix_applications',
  {
    id: bigint('id', { mode: 'number' }).primaryKey().generatedAlwaysAsIdentity(),
    fixId: text('fix_id').notNull(),
    hadithId: text('hadith_id').notNull(),
    action: text('action').notNull(),
    effect: text('effect').notNull(),
    baseRows: jsonb('base_rows').notNull(),
    writtenIds: jsonb('written_ids').notNull(),
    datasetVersionId: text('dataset_version_id').notNull(),
    createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
    createdBy: text('created_by').notNull(),
  },
  (table) => [
    restrictForeignKey('chain_fix_applications_fix_id_fk', table.fixId, chainFixes.id),
    restrictForeignKey('chain_fix_applications_hadith_id_fk', table.hadithId, hadiths.id),
    restrictForeignKey('chain_fix_applications_dataset_version_id_fk', table.datasetVersionId, datasetVersions.id),
    check('chain_fix_applications_action_check', sql`${table.action} in ('applied', 'reverted')`),
    check('chain_fix_applications_effect_check', sql`${table.effect} in ('replace_routes', 'set_status', 'annotate')`),
    check(
      'chain_fix_applications_base_rows_check',
      sql`jsonb_typeof(${table.baseRows} -> 'chains') = 'array' and jsonb_typeof(${table.baseRows} -> 'chain_mentions') = 'array'
        and jsonb_typeof(${table.baseRows} -> 'chain_mention_candidates') = 'array'`,
    ),
    index('chain_fix_applications_fix_id_idx').on(table.fixId),
  ],
);

/**
 * Per work: may a chain read by model and awaiting final review feed teacher and student lists? Absent or false: no
 * (owner 2026-11-22: shipped off for every work; lifted per work once its agreed-reading error rate is measured).
 * Curation-owned; read by `narrator_transmissions` and by `chain-fix-decide`.
 */
export const chainFixWorkSettings = pgTable(
  'chain_fix_work_settings',
  {
    collectionId: text('collection_id').primaryKey(),
    readByModelInNetwork: boolean('read_by_model_in_network').notNull().default(false),
    note: text('note').notNull(),
    ...curationBookkeeping(),
  },
  (table) => [
    restrictForeignKey('chain_fix_work_settings_collection_id_fk', table.collectionId, collections.id),
    check('chain_fix_work_settings_note_check', sql`btrim(${table.note}) <> ''`),
  ],
);

/** Public view: the label under a public chain read by a model (hand-written SQL, drizzle/core/0019). */
export const publicChainFixLabels = pgView('public_chain_fix_labels', {
  chainId: text('chain_id').notNull(),
  hadithId: text('hadith_id').notNull(),
  fixId: text('fix_id').notNull(),
  state: text('state').notNull(),
  effect: text('effect').notNull(),
  structureStatus: text('structure_status'),
  models: text('models').array().notNull(),
  runs: integer('runs').notNull(),
  decidedAt: timestamp('decided_at', { withTimezone: true }).notNull(),
  awaitingFinalReview: boolean('awaiting_final_review').notNull(),
  humanConfirmations: jsonb('human_confirmations').notNull(),
}).existing();

/** Public view (0021): a report whose applied fix found no isnad in the text; its chains are retired, the page says so. */
export const publicChainFixDispositions = pgView('public_chain_fix_dispositions', {
  hadithId: text('hadith_id').notNull(),
  fixId: text('fix_id').notNull(),
  disposition: text('disposition').notNull(),
  state: text('state').notNull(),
  models: text('models').array().notNull(),
  runs: integer('runs').notNull(),
  decidedAt: timestamp('decided_at', { withTimezone: true }).notNull(),
  awaitingFinalReview: boolean('awaiting_final_review').notNull(),
}).existing();

/** Public view (0021): what a model-read mention is beyond a name written in the chain (`imam_in_text`, `inherited`), from the fix's plan. */
export const publicChainFixMentionKinds = pgView('public_chain_fix_mention_kinds', {
  mentionId: text('mention_id').notNull(),
  chainId: text('chain_id').notNull(),
  hadithId: text('hadith_id').notNull(),
  readerKind: text('reader_kind').notNull(),
}).existing();
