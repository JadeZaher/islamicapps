/**
 * PROPOSAL, not schema: the review, contribution and discussion tables. It type-checks against the live schema but is
 * outside src/db/schema, so drizzle-kit never generates it. Rationale and migration plan: docs/review/README.md.
 *
 * Ownership (one writer per table): `ai_reviews` is pipeline-owned (the loader writes it from the rule procedures and
 * from reviews/ai/records). Every other table here is owned by one "contribution service": in phase 1 that service is
 * the pipeline step that loads reviews/ files from the public repository; in phase 2 it is the app's server actions,
 * and the file importer becomes a caller of the same code path. Never both at once.
 */
import { sql } from 'drizzle-orm';
import { bigint, boolean, check, index, integer, jsonb, pgEnum, pgTable, primaryKey, text, timestamp, uniqueIndex, type AnyPgColumn } from 'drizzle-orm/pg-core';
import { curationBookkeeping, isLive, pipelineBookkeeping, pipelineBookkeepingForeignKeys, restrictForeignKey } from '../../src/db/schema/columns';
import { hadiths } from '../../src/db/schema/corpus';
import { hadithTraditionEnum } from '../../src/db/schema/enums';
import { bibliographicWorks, editions } from '../../src/db/schema/evidence';
import { epochs, historicalEvents, locations } from '../../src/db/schema/history';
import { narrators } from '../../src/db/schema/narrators';

// ── Enums ──────────────────────────────────────────────────────────────────────────────────────────────────────────

/** src/lib/review/claim-key.ts CLAIM_KINDS. */
export const claimKindEnum = pgEnum('claim_kind', [
  'identity', 'correspondence', 'translation', 'grading', 'narrator_verdict', 'biography', 'rijal_link', 'history', 'quran_citation', 'numbering',
]);
/** The two kinds of AI review, never blurred. */
export const aiReviewKindEnum = pgEnum('ai_review_kind', ['rule', 'specialist']);
export const aiReviewOutcomeEnum = pgEnum('ai_review_outcome', ['supports', 'contradicts', 'contested', 'insufficient_evidence']);
export const aiUncertaintyEnum = pgEnum('ai_uncertainty', ['low', 'medium', 'high']);
/** A person's stated view; `cannot_decide` maps the existing `undecidable` / `uncertain` decisions. */
export const reviewStanceEnum = pgEnum('review_stance', ['agrees', 'qualifies', 'disagrees', 'cannot_decide']);
export const reviewFieldEnum = pgEnum('review_field', ['identity', 'text', 'translation', 'grading', 'biography', 'history', 'quran']);
export const contributorCapabilityEnum = pgEnum('contributor_capability', ['review', 'discuss', 'propose', 'endorse', 'moderate']);
export const contributionOriginEnum = pgEnum('contribution_origin', ['repository_file', 'app']);
export const anchorKindEnum = pgEnum('anchor_kind', [
  'report', 'tellings', 'chain', 'mention', 'claim', 'text_span', 'narrator', 'rijal_entry', 'event', 'era', 'place', 'perspective_cell',
]);
/** An anchor is never dropped: a changed text or chain marks it for re-anchoring. */
export const anchorStateEnum = pgEnum('anchor_state', ['current', 'reanchored', 'needs_reanchoring']);
export const postAuthorKindEnum = pgEnum('post_author_kind', ['person', 'ai']);
/** Grounds for withdrawing a post. Disagreement is deliberately not one. */
export const moderationReasonEnum = pgEnum('moderation_reason', ['adab', 'off_topic', 'personal_information', 'copyright', 'duplicate', 'author_request']);

/** Claim address shared by AI reviews, human reviews and claim anchors: semantic key plus routing FKs. */
function claimColumns() {
  return {
    claimKind: claimKindEnum('claim_kind').notNull(),
    /** `identity|<mention>|<narrator>` etc. (claim-key.ts): what is asserted, not which machine row proposed it. */
    claimKey: text('claim_key').notNull(),
    /** SHA-256 over the key and every bound text hash; a changed text makes older reviews stale, never wrong-current. */
    contentSha256: text('content_sha256').notNull(),
    /** Routing for "show on this report / this narrator page"; null when the claim has no such subject. */
    hadithId: text('hadith_id'),
    narratorId: text('narrator_id'),
  };
}
const sha256Check = (name: string, column: AnyPgColumn) => check(name, sql`${column} ~ '^[0-9a-f]{64}$'`);

// ── AI review (pipeline) ───────────────────────────────────────────────────────────────────────────────────────────

/**
 * One AI review of one claim. Rule rows carry procedure id, version and code hash and no model; specialist rows carry
 * the specialist, prompt version and hash, the exact model, runtime, UTC start and finish, packet hash, reasons,
 * evidence spans and uncertainty. Loaded from rule output and from reviews/ai/records/*.jsonl.
 */
export const aiReviews = pgTable(
  'ai_reviews',
  {
    id: text('id').primaryKey(),
    ...claimColumns(),
    reviewKind: aiReviewKindEnum('review_kind').notNull(),
    outcome: aiReviewOutcomeEnum('outcome').notNull(),
    // rule
    procedureId: text('procedure_id'),
    procedureVersion: text('procedure_version'),
    codeSha256: text('code_sha256'),
    // specialist
    specialistId: text('specialist_id'),
    specialistVersion: text('specialist_version'),
    promptVersion: text('prompt_version'),
    promptSha256: text('prompt_sha256'),
    modelId: text('model_id'),
    providerRuntime: text('provider_runtime'),
    startedAt: timestamp('started_at', { withTimezone: true }),
    finishedAt: timestamp('finished_at', { withTimezone: true }),
    packetSha256: text('packet_sha256'),
    reading: text('reading'),
    reasons: jsonb('reasons').$type<string[]>().notNull().default(sql`'[]'::jsonb`),
    /** Rule: the measurement (scores, sources compared). Specialist: the quoted spans relied on. */
    evidence: jsonb('evidence').notNull().default(sql`'{}'::jsonb`),
    uncertainty: aiUncertaintyEnum('uncertainty'),
    uncertaintyNote: text('uncertainty_note'),
    proposals: jsonb('proposals').notNull().default(sql`'[]'::jsonb`),
    /** reviews/ai/records/<specialist>/<batch>.jsonl line, or the rule's output file. */
    recordRef: text('record_ref').notNull(),
    ...pipelineBookkeeping(),
  },
  (table) => [
    restrictForeignKey('ai_reviews_hadith_id_fk', table.hadithId, hadiths.id),
    restrictForeignKey('ai_reviews_narrator_id_fk', table.narratorId, narrators.id),
    sha256Check('ai_reviews_content_sha256_check', table.contentSha256),
    check(
      'ai_reviews_kind_fields_check',
      sql`(${table.reviewKind} = 'rule' and num_nonnulls(${table.procedureId}, ${table.procedureVersion}, ${table.codeSha256}) = 3
             and num_nonnulls(${table.specialistId}, ${table.modelId}, ${table.promptSha256}, ${table.packetSha256}, ${table.startedAt}, ${table.finishedAt}) = 0)
          or (${table.reviewKind} = 'specialist' and ${table.procedureId} is null
             and num_nonnulls(${table.specialistId}, ${table.specialistVersion}, ${table.promptVersion}, ${table.promptSha256}, ${table.modelId},
                              ${table.providerRuntime}, ${table.startedAt}, ${table.finishedAt}, ${table.packetSha256}, ${table.uncertainty}) = 10
             and ${table.finishedAt} >= ${table.startedAt})`,
    ),
    uniqueIndex('ai_reviews_rule_key').on(table.claimKey, table.procedureId, table.procedureVersion).where(sql`${table.reviewKind} = 'rule' and ${table.retiredAt} is null`),
    uniqueIndex('ai_reviews_specialist_key')
      .on(table.claimKey, table.specialistId, table.promptSha256, table.modelId, table.startedAt)
      .where(sql`${table.reviewKind} = 'specialist'`),
    index('ai_reviews_claim_key_idx').on(table.claimKey),
    index('ai_reviews_hadith_id_idx').on(table.hadithId).where(sql`${table.hadithId} is not null`),
    index('ai_reviews_narrator_id_idx').on(table.narratorId).where(sql`${table.narratorId} is not null`),
    ...pipelineBookkeepingForeignKeys('ai_reviews', table),
  ],
);

// ── Contributors (replaces the fixed curator list; design §5.15 `contributors`, roles moved to permissions) ─────

export const contributors = pgTable(
  'contributors',
  {
    /** `contributor:github:<handle>` while contributions arrive as repository files. */
    id: text('id').primaryKey(),
    handle: text('handle').notNull(),
    displayName: text('display_name').notNull(),
    affiliation: text('affiliation'),
    traditionContext: hadithTraditionEnum('tradition_context'),
    profileUrl: text('profile_url'),
    orcid: text('orcid'),
    origin: contributionOriginEnum('origin').notNull(),
    ...curationBookkeeping(),
  },
  (table) => [uniqueIndex('contributors_handle_key').on(table.handle)],
);

/** "Endorsement", not ijaza: one reviewer vouches for another's competence in one field (glossary caution). */
export const contributorEndorsements = pgTable(
  'contributor_endorsements',
  {
    id: text('id').primaryKey(),
    endorserId: text('endorser_id').notNull(),
    endorseeId: text('endorsee_id').notNull(),
    field: reviewFieldEnum('field').notNull(),
    statement: text('statement').notNull(),
    endorsedOn: timestamp('endorsed_on', { withTimezone: true }).notNull(),
    ...curationBookkeeping(),
  },
  (table) => [
    restrictForeignKey('contributor_endorsements_endorser_id_fk', table.endorserId, contributors.id),
    restrictForeignKey('contributor_endorsements_endorsee_id_fk', table.endorseeId, contributors.id),
    check('contributor_endorsements_not_self_check', sql`${table.endorserId} <> ${table.endorseeId}`),
  ],
);

/** Dated grants; revoking retires a row, so "who could review on the day" stays answerable. */
export const contributorPermissions = pgTable(
  'contributor_permissions',
  {
    id: bigint('id', { mode: 'number' }).primaryKey().generatedAlwaysAsIdentity(),
    contributorId: text('contributor_id').notNull(),
    capability: contributorCapabilityEnum('capability').notNull(),
    /** Null means every field. */
    field: reviewFieldEnum('field'),
    grantedBy: text('granted_by').notNull(),
    grantedOn: timestamp('granted_on', { withTimezone: true }).notNull(),
    endorsementId: text('endorsement_id'),
    ...curationBookkeeping(),
  },
  (table) => [
    restrictForeignKey('contributor_permissions_contributor_id_fk', table.contributorId, contributors.id),
    restrictForeignKey('contributor_permissions_endorsement_id_fk', table.endorsementId, contributorEndorsements.id),
    uniqueIndex('contributor_permissions_live_key').on(table.contributorId, table.capability, table.field).where(isLive(table.retiredAt)),
  ],
);

// ── Human reviews (replaces design §5.15 `submission_reviews`; generalises both decision tables) ─────────────────

export const humanReviews = pgTable(
  'human_reviews',
  {
    id: text('id').primaryKey(),
    ...claimColumns(),
    reviewerId: text('reviewer_id').notNull(),
    stance: reviewStanceEnum('stance').notNull(),
    note: text('note').notNull(),
    language: text('language').notNull(),
    traditionContext: hadithTraditionEnum('tradition_context'),
    /** A person may draft with a model; the review is still theirs and is labelled "AI-assisted drafting". */
    aiAssistedModelId: text('ai_assisted_model_id'),
    aiAssistedRole: text('ai_assisted_role'),
    origin: contributionOriginEnum('origin').notNull(),
    /** reviews/entries/<handle>/<id>.json at <commit>, or the app request id. */
    originRef: text('origin_ref').notNull(),
    submittedAt: timestamp('submitted_at', { withTimezone: true }).notNull(),
    supersedesReviewId: text('supersedes_review_id'),
    /** Optional thread the review opened or joined. */
    threadId: text('thread_id'),
    ...curationBookkeeping(),
  },
  (table) => [
    restrictForeignKey('human_reviews_reviewer_id_fk', table.reviewerId, contributors.id),
    restrictForeignKey('human_reviews_hadith_id_fk', table.hadithId, hadiths.id),
    restrictForeignKey('human_reviews_narrator_id_fk', table.narratorId, narrators.id),
    restrictForeignKey('human_reviews_supersedes_review_id_fk', table.supersedesReviewId, table.id),
    sha256Check('human_reviews_content_sha256_check', table.contentSha256),
    check('human_reviews_ai_assist_check', sql`num_nonnulls(${table.aiAssistedModelId}, ${table.aiAssistedRole}) in (0, 2)`),
    check('human_reviews_retired_check', sql`num_nonnulls(${table.retiredAt}, ${table.retiredBy}) in (0, 2)`),
    /** One live view per reviewer per claim: a changed mind supersedes, never overwrites. */
    uniqueIndex('human_reviews_live_reviewer_claim_key').on(table.reviewerId, table.claimKey).where(isLive(table.retiredAt)),
    index('human_reviews_claim_key_idx').on(table.claimKey),
    index('human_reviews_hadith_id_idx').on(table.hadithId).where(sql`${table.hadithId} is not null`),
    index('human_reviews_narrator_id_idx').on(table.narratorId).where(sql`${table.narratorId} is not null`),
  ],
);

// ── Discussion (replaces design §5.15 `submission_comments`) ──────────────────────────────────────────────────────

/**
 * A precise context. Exactly the columns of its kind are set (check). Shared by every thread on the same context, so
 * re-anchoring once fixes them all; every state change is a curation_audit row (before/after), so no history table.
 */
export const discussionAnchors = pgTable(
  'discussion_anchors',
  {
    id: text('id').primaryKey(),
    kind: anchorKindEnum('kind').notNull(),
    /** Canonical string of the typed reference (unique), e.g. `mention|mention:k6:19122:0000:0001`. */
    anchorKey: text('anchor_key').notNull(),
    hadithId: text('hadith_id'),
    tellingHadithIds: text('telling_hadith_ids').array(),
    chainId: text('chain_id'),
    mentionId: text('mention_id'),
    position: integer('position'),
    narratorId: text('narrator_id'),
    claimKind: claimKindEnum('claim_kind'),
    claimKey: text('claim_key'),
    /** `text_ar` or `translation:<lang>`; code-point offsets into that text. */
    spanField: text('span_field'),
    spanStart: integer('span_start'),
    spanEnd: integer('span_end'),
    quoteText: text('quote_text'),
    rijalWork: text('rijal_work'),
    rijalEntry: text('rijal_entry'),
    eventId: text('event_id'),
    epochId: text('epoch_id'),
    locationId: text('location_id'),
    perspectiveRowKey: text('perspective_row_key'),
    perspectiveAspect: text('perspective_aspect'),
    /** Hash of what the anchor was made against (report text, mention surface, claim content). */
    boundSha256: text('bound_sha256'),
    state: anchorStateEnum('state').notNull().default('current'),
    ...curationBookkeeping(),
  },
  (table) => [
    uniqueIndex('discussion_anchors_anchor_key').on(table.anchorKey),
    restrictForeignKey('discussion_anchors_hadith_id_fk', table.hadithId, hadiths.id),
    restrictForeignKey('discussion_anchors_narrator_id_fk', table.narratorId, narrators.id),
    restrictForeignKey('discussion_anchors_event_id_fk', table.eventId, historicalEvents.id),
    restrictForeignKey('discussion_anchors_epoch_id_fk', table.epochId, epochs.id),
    restrictForeignKey('discussion_anchors_location_id_fk', table.locationId, locations.id),
    check(
      'discussion_anchors_kind_columns_check',
      sql`case ${table.kind}
        when 'report' then ${table.hadithId} is not null and ${table.boundSha256} is not null
        when 'tellings' then cardinality(${table.tellingHadithIds}) >= 2
        when 'chain' then num_nonnulls(${table.hadithId}, ${table.chainId}) = 2
        when 'mention' then num_nonnulls(${table.hadithId}, ${table.chainId}, ${table.mentionId}, ${table.position}, ${table.boundSha256}) = 5
        when 'claim' then num_nonnulls(${table.claimKind}, ${table.claimKey}, ${table.boundSha256}) = 3
        when 'text_span' then num_nonnulls(${table.hadithId}, ${table.spanField}, ${table.spanStart}, ${table.spanEnd}, ${table.quoteText}, ${table.boundSha256}) = 6 and ${table.spanEnd} > ${table.spanStart}
        when 'narrator' then ${table.narratorId} is not null
        when 'rijal_entry' then num_nonnulls(${table.rijalWork}, ${table.rijalEntry}) = 2
        when 'event' then ${table.eventId} is not null
        when 'era' then ${table.epochId} is not null
        when 'place' then ${table.locationId} is not null
        when 'perspective_cell' then num_nonnulls(${table.perspectiveRowKey}, ${table.perspectiveAspect}) = 2 and num_nonnulls(${table.narratorId}, ${table.hadithId}) = 1
      end`,
    ),
    index('discussion_anchors_hadith_id_idx').on(table.hadithId).where(sql`${table.hadithId} is not null`),
    index('discussion_anchors_narrator_id_idx').on(table.narratorId).where(sql`${table.narratorId} is not null`),
    index('discussion_anchors_claim_key_idx').on(table.claimKey).where(sql`${table.claimKey} is not null`),
    index('discussion_anchors_mention_id_idx').on(table.mentionId).where(sql`${table.mentionId} is not null`),
    index('discussion_anchors_needs_reanchoring_idx').on(table.state).where(sql`${table.state} = 'needs_reanchoring'`),
  ],
);

export const discussionThreads = pgTable(
  'discussion_threads',
  {
    id: text('id').primaryKey(),
    anchorId: text('anchor_id').notNull(),
    title: text('title').notNull(),
    language: text('language').notNull(),
    /** The opener's declared lens; a facet, never a default ordering. */
    traditionContext: hadithTraditionEnum('tradition_context'),
    openedBy: text('opened_by').notNull(),
    archived: boolean('archived').notNull().default(false),
    ...curationBookkeeping(),
  },
  (table) => [
    restrictForeignKey('discussion_threads_anchor_id_fk', table.anchorId, discussionAnchors.id),
    restrictForeignKey('discussion_threads_opened_by_fk', table.openedBy, contributors.id),
    index('discussion_threads_anchor_id_idx').on(table.anchorId),
  ],
);

/** A post by a named person, or a labelled AI post (summary or draft) requested by a named person. */
export const discussionPosts = pgTable(
  'discussion_posts',
  {
    id: text('id').primaryKey(),
    threadId: text('thread_id').notNull(),
    parentPostId: text('parent_post_id'),
    authorKind: postAuthorKindEnum('author_kind').notNull(),
    authorId: text('author_id'),
    aiModelId: text('ai_model_id'),
    aiRole: text('ai_role'),
    aiRequestedBy: text('ai_requested_by'),
    /** A post that states a fact can be checked against the citation standard; a question or opinion need not cite. */
    assertsFact: boolean('asserts_fact').notNull().default(false),
    moderationReason: moderationReasonEnum('moderation_reason'),
    ...curationBookkeeping(),
  },
  (table) => [
    restrictForeignKey('discussion_posts_thread_id_fk', table.threadId, discussionThreads.id),
    restrictForeignKey('discussion_posts_parent_post_id_fk', table.parentPostId, table.id),
    restrictForeignKey('discussion_posts_author_id_fk', table.authorId, contributors.id),
    restrictForeignKey('discussion_posts_ai_requested_by_fk', table.aiRequestedBy, contributors.id),
    check(
      'discussion_posts_author_check',
      sql`(${table.authorKind} = 'person' and ${table.authorId} is not null and num_nonnulls(${table.aiModelId}, ${table.aiRole}, ${table.aiRequestedBy}) = 0)
          or (${table.authorKind} = 'ai' and ${table.authorId} is null and num_nonnulls(${table.aiModelId}, ${table.aiRole}, ${table.aiRequestedBy}) = 3)`,
    ),
    check('discussion_posts_moderation_check', sql`${table.moderationReason} is null or ${table.retiredAt} is not null`),
    index('discussion_posts_thread_id_idx').on(table.threadId),
  ],
);

/** Every version of a post; the current one is the highest revision. Edits never overwrite. */
export const discussionPostRevisions = pgTable(
  'discussion_post_revisions',
  {
    postId: text('post_id').notNull(),
    revision: integer('revision').notNull(),
    body: text('body').notNull(),
    language: text('language').notNull(),
    editedAt: timestamp('edited_at', { withTimezone: true }).notNull().defaultNow(),
    editedBy: text('edited_by').notNull(),
  },
  (table) => [
    primaryKey({ name: 'discussion_post_revisions_pkey', columns: [table.postId, table.revision] }),
    restrictForeignKey('discussion_post_revisions_post_id_fk', table.postId, discussionPosts.id),
  ],
);

// ── One citation table for every contribution (docs/review/citations.md) ─────────────────────────────────────────

export const contributionCitations = pgTable(
  'contribution_citations',
  {
    id: bigint('id', { mode: 'number' }).primaryKey().generatedAlwaysAsIdentity(),
    humanReviewId: text('human_review_id'),
    postId: text('post_id'),
    postRevision: integer('post_revision'),
    ordinal: integer('ordinal').notNull(),
    workId: text('work_id'),
    workAuthor: text('work_author').notNull(),
    workTitle: text('work_title').notNull(),
    workTradition: text('work_tradition').notNull(),
    editionId: text('edition_id'),
    editionAsNamed: text('edition_as_named').notNull(),
    /** shura-citation/1 locator: print | web | dataset | quran. */
    locator: jsonb('locator').notNull(),
    passageText: text('passage_text').notNull(),
    passageLanguage: text('passage_language').notNull(),
    passageSpan: jsonb('passage_span'),
    sourceCode: text('source_code').notNull(),
    licence: text('licence').notNull(),
    checkedAgainstSha256: text('checked_against_sha256').notNull(),
    /** An in-archive report cited as evidence (another telling, say). */
    citesHadithId: text('cites_hadith_id'),
  },
  (table) => [
    restrictForeignKey('contribution_citations_human_review_id_fk', table.humanReviewId, humanReviews.id),
    restrictForeignKey('contribution_citations_work_id_fk', table.workId, bibliographicWorks.id),
    restrictForeignKey('contribution_citations_edition_id_fk', table.editionId, editions.id),
    restrictForeignKey('contribution_citations_cites_hadith_id_fk', table.citesHadithId, hadiths.id),
    check('contribution_citations_one_owner_check', sql`(${table.humanReviewId} is not null) <> (${table.postId} is not null and ${table.postRevision} is not null)`),
    sha256Check('contribution_citations_checked_sha256_check', table.checkedAgainstSha256),
    check('contribution_citations_locator_kind_check', sql`${table.locator} ->> 'kind' in ('print', 'web', 'dataset', 'quran')`),
    index('contribution_citations_human_review_id_idx').on(table.humanReviewId),
    index('contribution_citations_post_idx').on(table.postId, table.postRevision),
  ],
);

/*
 * Views (hand-written SQL, sketched):
 *
 * claim_review_summary(claim_key, current_content_sha256, rule_outcome, specialist_outcomes, agrees, qualifies,
 *   disagrees, cannot_decide, stale, display_state): one row per claim; human counts are over live reviews whose
 *   content_sha256 equals the claim's current hash, one per reviewer. Same rule as src/lib/review/summary.ts.
 *
 * discussion_surfaces(page_kind, page_id, thread_id, via): where each thread is shown.
 *   report page H   <- anchors with hadith_id = H (report, chain, mention, claim, span, perspective cell);
 *                      anchors whose tellings include H; via 'telling' for anchors on reports linked to H in
 *                      public_report_correspondences (one hop, labelled with that telling's work and tradition).
 *   narrator page N <- anchors with narrator_id = N; mention anchors whose mention has any live candidate or
 *                      standing identity naming N (via 'name in a chain'); claim anchors whose claim names N;
 *                      rijal_entry anchors linked to N.
 *   event/era/place <- their own anchors.
 *   Read-time join: identities change between loads, so who a thread "touches" is never frozen at creation.
 *
 * perspective_rows(subject_kind, subject_id, row_key, row_kind, tradition, aspect, value, claim_key, cited): the
 *   matrix of src/lib/review/perspectives.ts, a union over narrator_assessments, rijal entries, cited biographical
 *   assertions, lexicon values ("not yet cited"), dataset profiles, ai_reviews and human_reviews.
 */
