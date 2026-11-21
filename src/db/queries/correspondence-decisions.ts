/** Reviewer decisions on report pairs: one curated write, retire-and-supersede, audit row in the same transaction. */
import 'server-only';
import { sql } from 'drizzle-orm';
import {
  reportCorrespondenceDecisionEnum,
  reportCorrespondenceDecisions,
  reportCorrespondenceReviewedRelationEnum,
} from '@/db/schema';
import type { CorrespondenceDecision, CorrespondenceReviewedRelation } from './contracts';
import { audit, CurationError, curationWrite, newId, txRows } from './write';

export const CORRESPONDENCE_DECISIONS = reportCorrespondenceDecisionEnum.enumValues;
export const CORRESPONDENCE_REVIEWED_RELATIONS = reportCorrespondenceReviewedRelationEnum.enumValues;

export interface CorrespondenceDecisionInput {
  hadith_id_a: string;
  hadith_id_b: string;
  /** The Arabic hashes the reviewer was shown; a write against changed text is refused. */
  seen_arabic_sha256_a: string;
  seen_arabic_sha256_b: string;
  decision: CorrespondenceDecision;
  reviewed_relation?: CorrespondenceReviewedRelation | null;
  note?: string | null;
}

export interface CorrespondenceDecisionResult {
  id: string;
  superseded: string | null;
}

/** Byte order, as the tables' `collate "C"` checks use: the unordered pair is stored once. */
export function orderPair(left: string, right: string): [string, string] {
  return Buffer.compare(Buffer.from(left), Buffer.from(right)) < 0 ? [left, right] : [right, left];
}

/**
 * Records a reviewer's decision on a pair, retiring the live one (if any) in the same transaction and pointing the new
 * row at it. Refused when the two texts are no longer the ones the reviewer saw, or when the pair is one report.
 */
export async function decideCorrespondence(actor: string, input: CorrespondenceDecisionInput): Promise<CorrespondenceDecisionResult> {
  if (input.hadith_id_a === input.hadith_id_b) throw new CurationError('invalid', 'A report cannot correspond to itself.');
  const [a, b] = orderPair(input.hadith_id_a, input.hadith_id_b);
  const swapped = a !== input.hadith_id_a;
  const seenA = swapped ? input.seen_arabic_sha256_b : input.seen_arabic_sha256_a;
  const seenB = swapped ? input.seen_arabic_sha256_a : input.seen_arabic_sha256_b;
  const id = newId();
  return curationWrite(actor, async (tx) => {
    const texts = await txRows<{ id: string; arabic_sha256: string }>(
      tx,
      sql`select id, arabic_sha256 from hadiths where id in (${a}, ${b}) and retired_at is null`,
    );
    if (texts.length !== 2) throw new CurationError('not_found', 'One of the two reports does not exist.');
    const hash = new Map(texts.map((row) => [row.id, row.arabic_sha256]));
    if (hash.get(a) !== seenA || hash.get(b) !== seenB) {
      throw new CurationError('conflict', 'The Arabic of one of these reports has changed since it was shown. Reload and review again.');
    }
    const [previous] = await txRows<{ id: string; image: Record<string, unknown> }>(
      tx,
      sql`select d.id, to_jsonb(d) as image from report_correspondence_decisions d
          where d.hadith_id_a = ${a} and d.hadith_id_b = ${b} and d.retired_at is null for update`,
    );
    if (previous) {
      await tx.execute(sql`update report_correspondence_decisions set retired_at = now(), retired_by = ${actor},
                           updated_at = now(), updated_by = ${actor} where id = ${previous.id}`);
    }
    const [after] = await tx
      .insert(reportCorrespondenceDecisions)
      .values({
        id,
        hadithIdA: a,
        hadithIdB: b,
        boundArabicSha256A: seenA,
        boundArabicSha256B: seenB,
        decision: input.decision,
        reviewedRelation: input.reviewed_relation ?? null,
        note: input.note ?? null,
        decidedBy: actor,
        supersedesDecisionId: previous?.id ?? null,
        createdBy: actor,
        updatedBy: actor,
      })
      .returning();
    await audit(tx, {
      actor,
      action: `correspondence:${input.decision}`,
      entityType: 'report_correspondence_decision',
      entityId: id,
      before: previous?.image,
      after,
    });
    return { id, superseded: previous?.id ?? null };
  });
}
