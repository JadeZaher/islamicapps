/** Reviewer-mode correspondence reads on live base tables (rule 9). Curator callers only: /admin and curation actions. */
import 'server-only';
import { sql } from 'drizzle-orm';
import type { CorrespondenceClass, CorrespondenceDecision, CorrespondenceReviewedRelation, Paginated, ReportFamily } from './contracts';
import { CURATOR_FAMILY_RELATIONS, FAMILY_CAP, readReportFamily, UNCITABLE_NUMBERING_WORKS } from './correspondence';
import { text } from './mappers';
import { clampPage, oneRow, paginated, type PageRequest } from './sql-helpers';

/** Curator preview of a family: unpublished reports included, same display rule. */
export async function getReportFamilyForReview(hadithId: string, cap = FAMILY_CAP): Promise<ReportFamily | null> {
  return readReportFamily(CURATOR_FAMILY_RELATIONS, hadithId, cap);
}

export type ReviewQueueStatus = 'unreviewed' | 'decided' | 'all';
export type ReviewQueueScope = 'cross_tradition' | 'cross_work_same_tradition' | 'same_work' | 'all';

export interface ReviewQueueFilters {
  status?: ReviewQueueStatus;
  scope?: ReviewQueueScope;
  relationClass?: CorrespondenceClass | 'all';
  /** Only pairs below the display threshold (reviewer material), or only above it. */
  shown?: 'shown' | 'hidden' | 'all';
}

export interface ReviewSide {
  hadith_id: string;
  tradition: string;
  source_work: string;
  source_work_id: string;
  /** Null where the work's numbering is not citable (UNCITABLE_NUMBERING_WORKS). */
  hadith_no: string | null;
}

export interface ReviewQueueItem {
  id: string;
  a: ReviewSide;
  b: ReviewSide;
  relation_class: CorrespondenceClass;
  jaccard: number;
  containment: number;
  /** The class's own measure: containment for a shared passage, Jaccard otherwise. */
  measure: number;
  scope: string;
  shown: boolean;
  decision: CorrespondenceDecision | null;
}

/** Candidate pairs for review, newest method only, cross-tradition and lowest bands first by default. */
export async function listCorrespondencesForReview(filters: ReviewQueueFilters = {}, request?: PageRequest): Promise<Paginated<ReviewQueueItem>> {
  const window = clampPage(request, Number.MAX_SAFE_INTEGER);
  const status = filters.status ?? 'unreviewed';
  const scope = filters.scope ?? 'cross_tradition';
  const relationClass = filters.relationClass ?? 'all';
  const shown = filters.shown ?? 'all';
  const row = await oneRow<{ counted: number; items: Record<string, unknown>[] | null }>(sql`
    with filtered as not materialized (
      select c.id, c.hadith_id_a, c.hadith_id_b, c.relation_class, c.jaccard, c.containment, c.scope,
             case when c.relation_class = 'partial_overlap' then c.containment else c.jaccard end as measure,
             (s.candidate_id is not null) as shown, d.decision
      from report_correspondence_candidates c
      left join report_correspondence_shown_pairs s on s.candidate_id = c.id
      left join report_correspondence_decisions d
             on d.hadith_id_a = c.hadith_id_a and d.hadith_id_b = c.hadith_id_b and d.retired_at is null
      where c.retired_at is null
        and (${scope} = 'all' or c.scope::text = ${scope})
        and (${relationClass} = 'all' or c.relation_class::text = ${relationClass})
        and (${status} = 'all' or (${status} = 'decided') = (d.id is not null))
        and (${shown} = 'all' or (${shown} = 'shown') = (s.candidate_id is not null))
    ),
    page as (
      select f.* from filtered f
      order by f.measure, f.id
      limit ${window.limit} offset ${window.offset}
    )
    select
      (select count(*)::int from (select 1 from filtered limit 1001) capped) as counted,
      (select json_agg(json_build_object(
                'id', p.id, 'relation_class', p.relation_class, 'jaccard', p.jaccard, 'containment', p.containment, 'measure', p.measure,
                'scope', p.scope, 'shown', p.shown, 'decision', p.decision,
                'a', json_build_object('hadith_id', ha.id, 'tradition', ta.code, 'source_work', ca.name, 'source_work_id', ca.source_work_id, 'hadith_no', ha.hadith_no),
                'b', json_build_object('hadith_id', hb.id, 'tradition', tb.code, 'source_work', cb.name, 'source_work_id', cb.source_work_id, 'hadith_no', hb.hadith_no))
              order by p.measure, p.id)
       from page p
       join hadiths ha on ha.id = p.hadith_id_a join collections ca on ca.id = ha.collection_id join traditions ta on ta.id = ha.tradition_id
       join hadiths hb on hb.id = p.hadith_id_b join collections cb on cb.id = hb.collection_id join traditions tb on tb.id = hb.tradition_id
      ) as items
  `);
  const side = (value: unknown): ReviewSide => {
    const raw = value as ReviewSide;
    return { ...raw, hadith_no: UNCITABLE_NUMBERING_WORKS.has(raw.source_work_id) ? null : raw.hadith_no };
  };
  const items = (row?.items ?? []).map((item) => ({
    id: String(item.id),
    a: side(item.a),
    b: side(item.b),
    relation_class: item.relation_class as CorrespondenceClass,
    jaccard: Number(item.jaccard),
    containment: Number(item.containment),
    measure: Number(item.measure),
    scope: String(item.scope),
    shown: item.shown === true,
    decision: (text(item.decision) as CorrespondenceDecision | null) ?? null,
  }));
  return paginated(items, row?.counted ?? 0, window, true);
}

export interface PairSide extends ReviewSide {
  record_id: string;
  text_ar: string | null;
  matn_ar: string | null;
  arabic_sha256: string;
  public: boolean;
}

export interface PairDecisionRecord {
  id: string;
  decision: CorrespondenceDecision;
  reviewed_relation: CorrespondenceReviewedRelation | null;
  note: string | null;
  decided_by: string;
  decided_at: string;
  retired_at: string | null;
  /** The texts are still the ones the reviewer saw. A stale decision is re-queued, never applied. */
  bound: boolean;
}

export interface PairForReview {
  a: PairSide;
  b: PairSide;
  candidate: {
    id: string;
    relation_class: CorrespondenceClass;
    jaccard: number;
    containment: number;
    scope: string;
    score_band: string;
    shown: boolean;
  } | null;
  decisions: PairDecisionRecord[];
}

/** Both texts, the machine scores and every decision ever recorded for the pair (live first). */
export async function getCorrespondencePairForReview(hadithIdA: string, hadithIdB: string): Promise<PairForReview | null> {
  const row = await oneRow<{ pair: Record<string, unknown> | null }>(sql`
    select json_build_object(
      'a', (select json_build_object('hadith_id', h.id, 'record_id', h.record_id, 'tradition', t.code, 'source_work', c.name, 'source_work_id', c.source_work_id,
                                     'hadith_no', h.hadith_no, 'text_ar', h.text_ar, 'matn_ar', h.matn_ar,
                                     'arabic_sha256', h.arabic_sha256, 'public', exists (select 1 from public_hadiths p where p.id = h.id))
            from hadiths h join collections c on c.id = h.collection_id join traditions t on t.id = h.tradition_id
            where h.id = ${hadithIdA} and h.retired_at is null),
      'b', (select json_build_object('hadith_id', h.id, 'record_id', h.record_id, 'tradition', t.code, 'source_work', c.name, 'source_work_id', c.source_work_id,
                                     'hadith_no', h.hadith_no, 'text_ar', h.text_ar, 'matn_ar', h.matn_ar,
                                     'arabic_sha256', h.arabic_sha256, 'public', exists (select 1 from public_hadiths p where p.id = h.id))
            from hadiths h join collections c on c.id = h.collection_id join traditions t on t.id = h.tradition_id
            where h.id = ${hadithIdB} and h.retired_at is null),
      'candidate', (select json_build_object('id', c.id, 'relation_class', c.relation_class, 'jaccard', c.jaccard,
                                             'containment', c.containment, 'scope', c.scope, 'score_band', c.score_band,
                                             'shown', exists (select 1 from report_correspondence_shown_pairs s where s.candidate_id = c.id))
                    from report_correspondence_candidates c
                    where c.hadith_id_a = ${hadithIdA} and c.hadith_id_b = ${hadithIdB} and c.retired_at is null
                    order by c.method_version desc limit 1),
      'decisions', (select coalesce(json_agg(json_build_object(
                             'id', d.id, 'decision', d.decision, 'reviewed_relation', d.reviewed_relation, 'note', d.note,
                             'decided_by', d.decided_by, 'decided_at', d.decided_at, 'retired_at', d.retired_at,
                             'bound', d.bound_arabic_sha256_a = ha.arabic_sha256 and d.bound_arabic_sha256_b = hb.arabic_sha256)
                           order by d.retired_at is not null, d.decided_at desc), '[]'::json)
                    from report_correspondence_decisions d
                    join hadiths ha on ha.id = d.hadith_id_a join hadiths hb on hb.id = d.hadith_id_b
                    where d.hadith_id_a = ${hadithIdA} and d.hadith_id_b = ${hadithIdB})
    ) as pair
  `);
  const pair = row?.pair;
  if (!pair?.a || !pair.b) return null;
  const result = pair as unknown as PairForReview;
  for (const sideOf of [result.a, result.b]) if (UNCITABLE_NUMBERING_WORKS.has(sideOf.source_work_id)) sideOf.hadith_no = null;
  return result;
}
