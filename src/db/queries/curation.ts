/** Section 9.3 curation writes: bio and verdict status, collection rights, surface decisions, absences, network refresh. */
import 'server-only';
import { sql } from 'drizzle-orm';
import { chainAbsenceDispositions, collectionRights, narratorAssessments, narratorBios, narratorSurfaceDecisions } from '@/db/schema';
import { REVIEWED_CITATION } from './assessment';
import type { CurationStatus, DecisionScope, EnglishPolicy, RightsStatus, SurfaceDecisionKind } from './enums';
import { audit, CurationError, curationWrite, newId, txRows, type Transaction } from './write';

/** Throws unless the citation exists, is live and is reviewed (section 5.8). */
async function requireReviewedCitation(tx: Transaction, citationId: string | null | undefined, subject: string): Promise<void> {
  if (!citationId) throw new CurationError('refused', `${subject} needs a citation before it can be published.`);
  const [cited] = await txRows(tx, sql`select 1 from citations c where c.id = ${citationId} and ${REVIEWED_CITATION}`);
  if (!cited) throw new CurationError('refused', `${subject} cites a citation that is retired or not yet reviewed.`);
}

/** Sets a curated bio's status; `published` needs a live reviewed citation. */
export async function setBioStatus(actor: string, narratorId: string, status: CurationStatus): Promise<void> {
  await curationWrite(actor, async (tx) => {
    const [before] = await txRows<{ image: Record<string, unknown> }>(
      tx,
      sql`select to_jsonb(b) as image from narrator_bios b where b.narrator_id = ${narratorId} and b.retired_at is null for update`,
    );
    if (!before) throw new CurationError('not_found', 'Narrator bio not found.');
    if (status === 'published') await requireReviewedCitation(tx, before.image.citation_id as string | null, 'A bio');
    const [after] = await tx
      .update(narratorBios)
      .set({ status, updatedAt: new Date(), updatedBy: actor })
      .where(sql`${narratorBios.narratorId} = ${narratorId}`)
      .returning();
    await audit(tx, { actor, action: `status:${status}`, entityType: 'narrator_bio', entityId: narratorId, before: before.image, after });
  });
}

/** Sets a verdict's status; `published` also needs a tradition (verdicts are tradition-scoped). */
export async function setVerdictStatus(actor: string, assessmentId: string, status: CurationStatus): Promise<void> {
  await curationWrite(actor, async (tx) => {
    const [before] = await txRows<{ image: Record<string, unknown> }>(
      tx,
      sql`select to_jsonb(a) as image from narrator_assessments a where a.id = ${assessmentId} and a.retired_at is null for update`,
    );
    if (!before) throw new CurationError('not_found', 'Verdict not found.');
    if (status === 'published') {
      if (!before.image.tradition_id) throw new CurationError('refused', 'A verdict needs a tradition before it can be published.');
      await requireReviewedCitation(tx, before.image.citation_id as string | null, 'A verdict');
    }
    const [after] = await tx
      .update(narratorAssessments)
      .set({ status, updatedAt: new Date(), updatedBy: actor })
      .where(sql`${narratorAssessments.id} = ${assessmentId}`)
      .returning();
    await audit(tx, { actor, action: `status:${status}`, entityType: 'narrator_assessment', entityId: assessmentId, before: before.image, after });
  });
}

export interface CollectionRightsInput {
  rights_status: RightsStatus;
  english_policy: EnglishPolicy;
  rights_note?: string | null;
  citation?: string | null;
}

/**
 * Records the owner's rights decision for one work (owner-only in practice; audited). `hadith_embeddings.is_public`
 * is not updated: that table ships with step 11.
 */
export async function setCollectionRights(actor: string, collectionId: string, input: CollectionRightsInput): Promise<void> {
  await curationWrite(actor, async (tx) => {
    const [collection] = await txRows(tx, sql`select 1 from collections where id = ${collectionId} and retired_at is null`);
    if (!collection) throw new CurationError('not_found', 'Collection not found.');
    const [before] = await txRows<{ image: Record<string, unknown> }>(
      tx,
      sql`select to_jsonb(r) as image from collection_rights r where r.collection_id = ${collectionId} for update`,
    );
    await upsertRights(tx, actor, collectionId, input, before?.image);
  });
}

/** Upserts one work's rights row and appends its `set_rights` audit row, inside the caller's transaction. */
async function upsertRights(
  tx: Transaction,
  actor: string,
  collectionId: string,
  input: CollectionRightsInput,
  before: Record<string, unknown> | undefined,
): Promise<void> {
  const [after] = await tx
    .insert(collectionRights)
    .values({
      collectionId,
      rightsStatus: input.rights_status,
      englishPolicy: input.english_policy,
      rightsNote: input.rights_note ?? null,
      citation: input.citation ?? null,
      createdBy: actor,
      updatedBy: actor,
    })
    .onConflictDoUpdate({
      target: collectionRights.collectionId,
      set: {
        rightsStatus: input.rights_status,
        englishPolicy: input.english_policy,
        rightsNote: input.rights_note ?? null,
        citation: input.citation ?? null,
        updatedAt: new Date(),
        updatedBy: actor,
        retiredAt: null,
        retiredBy: null,
      },
    })
    .returning();
  await audit(tx, { actor, action: 'set_rights', entityType: 'collection_rights', entityId: collectionId, before, after });
}

export interface RightsDecision extends CollectionRightsInput {
  /** `collections.source_work_id` of the work the decision is about. */
  source_work_id: string;
}

export interface RightsDecisionsOutcome {
  written: string[];
  unchanged: string[];
}

/**
 * Records many rights decisions in ONE transaction, idempotently: a work whose live row already says the same is left
 * untouched (no write, no audit row), so a re-run changes nothing. Refuses when any named work is not loaded or when
 * a loaded work has no decision, so a partial record can never be committed.
 */
export async function recordRightsDecisions(actor: string, decisions: readonly RightsDecision[]): Promise<RightsDecisionsOutcome> {
  return curationWrite(actor, async (tx) => {
    const works = await txRows<{ id: string; source_work_id: string }>(
      tx,
      sql`select id, source_work_id from collections where retired_at is null order by source_work_id`,
    );
    const byWork = new Map(works.map((work) => [work.source_work_id, work.id]));
    const unknown = decisions.filter((decision) => !byWork.has(decision.source_work_id)).map((decision) => decision.source_work_id);
    if (unknown.length > 0) throw new CurationError('not_found', `Works not loaded in this database: ${unknown.join(', ')}.`);
    const named = new Set(decisions.map((decision) => decision.source_work_id));
    const missing = works.filter((work) => !named.has(work.source_work_id)).map((work) => work.source_work_id);
    if (missing.length > 0) throw new CurationError('refused', `Loaded works without a decision: ${missing.join(', ')}.`);

    const outcome: RightsDecisionsOutcome = { written: [], unchanged: [] };
    for (const decision of decisions) {
      const collectionId = byWork.get(decision.source_work_id)!;
      const [before] = await txRows<{ image: Record<string, unknown> }>(
        tx,
        sql`select to_jsonb(r) as image from collection_rights r where r.collection_id = ${collectionId} for update`,
      );
      const image = before?.image;
      const same =
        image !== undefined &&
        image.retired_at === null &&
        image.rights_status === decision.rights_status &&
        image.english_policy === decision.english_policy &&
        image.rights_note === (decision.rights_note ?? null) &&
        image.citation === (decision.citation ?? null);
      if (same) {
        outcome.unchanged.push(decision.source_work_id);
        continue;
      }
      await upsertRights(tx, actor, collectionId, decision, image);
      outcome.written.push(decision.source_work_id);
    }
    return outcome;
  });
}

/** Calls `apply_decision(unit_id)` when the database has it; reports false while that function is not shipped. */
async function applyDecisionIfAvailable(tx: Transaction, unitId: string): Promise<boolean> {
  const [available] = await txRows<{ present: boolean }>(
    tx,
    sql`select to_regprocedure('apply_decision(text)') is not null as present`,
  );
  if (!available?.present) return false;
  await txRows(tx, sql`select apply_decision(${unitId})`);
  return true;
}

export interface SurfaceDecisionInput {
  scope: DecisionScope;
  unit_id: string;
  decision_kind: SurfaceDecisionKind;
  target_narrator_id?: string | null;
  derived_relation?: string | null;
  citation_id?: string | null;
  cited_basis_note?: string | null;
  /** The scholar the curator attributes the identification to; the reviewer is always the session actor. */
  attributed_scholar?: string | null;
  notes?: string | null;
}

export interface DecisionResult {
  id: string;
  /** False until `apply_decision` ships with the loader's decision replay (src/db/AGENTS.md "Deferred"). */
  applied: boolean;
}

/**
 * Records a human identity decision for a review unit, retiring the previous live decision for the unit in the
 * same transaction. The unit's surface and contexts are copied from its mentions.
 */
export async function decideSurfaceUnit(actor: string, input: SurfaceDecisionInput): Promise<DecisionResult> {
  const id = newId();
  return curationWrite(actor, async (tx) => {
    const unitColumn = input.scope === 'teacher_context' ? sql`m.review_unit_id` : sql`m.review_unit_fine_id`;
    const [unit] = await txRows<{
      surface_normalized: string;
      teacher_context_normalized: string | null;
      student_context_normalized: string | null;
      collection_id: string;
    }>(
      tx,
      input.scope === 'mention'
        ? sql`select m.surface_normalized, m.teacher_context_normalized, m.student_context_normalized, h.collection_id
              from chain_mentions m join hadiths h on h.id = m.hadith_id
              where m.id = ${input.unit_id} and m.retired_at is null`
        : sql`select m.surface_normalized, m.teacher_context_normalized, m.student_context_normalized, h.collection_id
              from chain_mentions m join hadiths h on h.id = m.hadith_id
              where ${unitColumn} = ${input.unit_id} and m.retired_at is null
              order by m.id limit 1`,
    );
    if (!unit) throw new CurationError('not_found', 'Review unit not found.');
    const previous = await txRows<{ image: Record<string, unknown> }>(
      tx,
      sql`update narrator_surface_decisions d set retired_at = now(), retired_by = ${actor}, updated_at = now(), updated_by = ${actor}
          where d.scope = ${input.scope} and d.unit_id = ${input.unit_id} and d.retired_at is null
          returning to_jsonb(d) as image`,
    );
    const now = new Date();
    const [created] = await tx
      .insert(narratorSurfaceDecisions)
      .values({
        id,
        scope: input.scope,
        unitId: input.unit_id,
        surfaceNormalized: unit.surface_normalized,
        // Every scope is keyed by the teacher context; only the narrower scopes also bind the student.
        teacherContextNormalized: unit.teacher_context_normalized,
        studentContextNormalized: input.scope === 'teacher_context' ? null : unit.student_context_normalized,
        collectionId: unit.collection_id,
        decisionKind: input.decision_kind,
        targetNarratorId: input.target_narrator_id ?? null,
        derivedRelation: input.derived_relation ?? null,
        citationId: input.citation_id ?? null,
        citedBasisNote: input.cited_basis_note ?? null,
        reviewer: actor,
        attributedScholar: input.attributed_scholar ?? null,
        reviewedAt: now,
        notes: input.notes ?? null,
        createdBy: actor,
        updatedBy: actor,
      })
      .returning();
    const applied = await applyDecisionIfAvailable(tx, input.unit_id);
    await audit(tx, {
      actor,
      action: 'decide',
      entityType: 'narrator_surface_decision',
      entityId: id,
      before: previous[0]?.image,
      after: { ...created, applied },
    });
    return { id, applied };
  });
}

/** Retires a live decision; its mentions fall back to their automatic resolution once `apply_decision` runs. */
export async function retireSurfaceDecision(actor: string, decisionId: string): Promise<DecisionResult> {
  return curationWrite(actor, async (tx) => {
    const [retired] = await txRows<{ image: Record<string, unknown> }>(
      tx,
      sql`update narrator_surface_decisions d set retired_at = now(), retired_by = ${actor}, updated_at = now(), updated_by = ${actor}
          where d.id = ${decisionId} and d.retired_at is null
          returning to_jsonb(d) as image`,
    );
    if (!retired) throw new CurationError('not_found', 'Decision not found.');
    const applied = await applyDecisionIfAvailable(tx, String(retired.image.unit_id));
    await audit(tx, { actor, action: 'retire', entityType: 'narrator_surface_decision', entityId: decisionId, before: retired.image, after: { applied } });
    return { id: decisionId, applied };
  });
}

export interface ChainAbsenceInput {
  /** Exactly one of collection_id and hadith_id. */
  collection_id?: string | null;
  hadith_id?: string | null;
  reason: string;
  citation_id?: string | null;
}

/** Records that a report or a whole work has no isnad by nature, then refreshes the facets of the affected hadiths. */
export async function recordChainAbsence(actor: string, input: ChainAbsenceInput): Promise<{ id: string; refreshed: number }> {
  if (Boolean(input.collection_id) === Boolean(input.hadith_id)) {
    throw new CurationError('invalid', 'Give exactly one of a collection or a hadith.');
  }
  const id = newId();
  return curationWrite(actor, async (tx) => {
    const [created] = await tx
      .insert(chainAbsenceDispositions)
      .values({
        id,
        collectionId: input.collection_id ?? null,
        hadithId: input.hadith_id ?? null,
        reason: input.reason,
        citationId: input.citation_id ?? null,
        createdBy: actor,
        updatedBy: actor,
      })
      .returning();
    const [refresh] = await txRows<{ changed: number }>(
      tx,
      input.hadith_id
        ? sql`select refresh_publication_facets(array[${input.hadith_id}]::text[]) as changed`
        : sql`select refresh_publication_facets(array(select id from hadiths where collection_id = ${input.collection_id}
                                                      and retired_at is null)) as changed`,
    );
    await audit(tx, { actor, action: 'create', entityType: 'chain_absence_disposition', entityId: id, after: created });
    return { id, refreshed: Number(refresh?.changed ?? 0) };
  });
}

/** Refreshes `narrator_transmissions` once; returns false when skipped because a load, migration or refresh runs. */
export async function refreshNetwork(actor: string): Promise<{ refreshed: boolean }> {
  return curationWrite(actor, async (tx) => {
    // The refresh itself can take longer than the curation lock timeout allows.
    await tx.execute(sql`set local lock_timeout = '30s'`);
    const [result] = await txRows<{ refreshed: boolean }>(tx, sql`select refresh_network() as refreshed`);
    const refreshed = result?.refreshed === true;
    await audit(tx, { actor, action: 'refresh', entityType: 'narrator_transmissions', entityId: 'network', after: { refreshed } });
    return { refreshed };
  });
}
