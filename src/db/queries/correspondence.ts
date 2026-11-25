/** A report's family: the report, every telling the display rule links to it, and all their chains. Public views only;
 * reviewer reads pass REVIEW_FAMILY_RELATIONS (correspondence-review.ts). See src/db/AGENTS.md §Report correspondences. */
import 'server-only';
import { sql, type SQL } from 'drizzle-orm';
import type {
  ChainDisposition,
  ChainGraph,
  CorrespondenceClass,
  FamilyTelling,
  HadithTraditionCode,
  ReportFamily,
  TellingCorrespondence,
} from './contracts';
import { englishAttribution } from './hadith';
import {
  chainEdges,
  chainNodesJson,
  PUBLIC_CHAIN_RELATIONS,
  readerPromptLateralSql,
  REVIEW_CHAIN_RELATIONS,
  stampReviewMarkSql,
  toChainNode,
  type ChainRelations,
} from './isnad';
import { text } from './mappers';
import { oneRow } from './sql-helpers';
import { hadithRelationsFor, isCuratorVisibility, PUBLIC_VISIBILITY, type ReadVisibility } from './visibility';

/** At most this many corresponding reports per family (the largest star cluster holds 61). */
export const FAMILY_CAP = 60;

/**
 * Works whose number is not a citable reference even through `reportNumber` (audit 2026-11-21, src/db/queries/AGENTS.md
 * §Report families): Musnad Ahmad repeats 3,616 numbers over 23,529 rows (485 non-numeric, such as `1]`); Musnad
 * al-Shafi'i has none. Thaqalayn works are citable through the number in the provider URL, not the stored chapter number.
 */
export const UNCITABLE_NUMBERING_WORKS: ReadonlySet<string> = new Set(['sunni:ahmad', 'sunni:shafii']);

/** Where a family read draws reports, correspondences and chains from. */
export interface FamilyRelations {
  /** Columns of `hadiths`, restricted to the reports the reader may see. */
  hadiths: SQL;
  /** Columns of `report_correspondence_display`. */
  correspondences: SQL;
  chains: ChainRelations;
  /** Columns of `translations`, restricted to the English the reader may see. */
  translations: SQL;
}

export const PUBLIC_FAMILY_RELATIONS: FamilyRelations = {
  hadiths: sql`public_hadiths`,
  correspondences: sql`public_report_correspondences`,
  chains: PUBLIC_CHAIN_RELATIONS,
  translations: sql`public_translations`,
};

const LIVE_TRANSLATIONS = sql`(select x.* from translations x where x.retired_at is null)`;

/** The family relations for a resolved visibility: hadiths through the shared resolver (`hadithRelationsFor`). */
export function familyRelationsFor(visibility: ReadVisibility): FamilyRelations {
  if (!isCuratorVisibility(visibility)) return PUBLIC_FAMILY_RELATIONS;
  const relations = hadithRelationsFor(visibility);
  return {
    hadiths: sql`(select h.* from ${relations.hadiths} h where ${relations.liveHadith})`,
    correspondences: sql`report_correspondence_display`,
    chains: REVIEW_CHAIN_RELATIONS,
    translations: LIVE_TRANSLATIONS,
  };
}

/** Every live report, whatever its publication state: the /admin review screens (correspondence-review.ts). */
export const CURATOR_FAMILY_RELATIONS: FamilyRelations = {
  hadiths: sql`(select h.* from hadiths h where h.retired_at is null)`,
  correspondences: sql`report_correspondence_display`,
  chains: REVIEW_CHAIN_RELATIONS,
  translations: LIVE_TRANSLATIONS,
};

const CLASS_RANK = sql`case x.relation_class when 'same_wording' then 0 when 'same_report_variant_wording' then 1
                       when 'partial_overlap' then 2 else 3 end`;

/**
 * One statement: the corresponding reports ranked (reviewer-confirmed first, then the closest wording), the cap applied,
 * and the tellings with their chains as JSON. Nothing is returned when the report itself is not visible.
 */
function familyStatement(relations: FamilyRelations, hadithId: string, cap: number): SQL {
  return sql`
    with corresponding as materialized (
      select x.corresponding_hadith_id as id, x.relation_class, x.jaccard, x.containment, x.scope, x.decision,
             x.reviewed_relation, x.confirmed,
             row_number() over (order by x.confirmed desc, ${CLASS_RANK}, coalesce(x.jaccard, 0) desc,
                                         x.corresponding_hadith_id collate "C") as rank
      from ${relations.correspondences} x
      where x.hadith_id = ${hadithId}
    ),
    members as materialized (
      select h.id, 0::bigint as rank from ${relations.hadiths} h where h.id = ${hadithId}
      union all
      select c.id, c.rank from corresponding c
      where c.rank <= ${cap} and exists (select 1 from ${relations.hadiths} h where h.id = ${hadithId})
    )
    select
      (select count(*)::int from corresponding) as total,
      (
        select json_agg(json_build_object(
                 'hadith_id', h.id, 'record_id', h.record_id, 'is_focal', m.rank = 0, 'tradition', t.code,
                 'collection_id', h.collection_id, 'source_work', col.name, 'source_work_id', col.source_work_id,
                 'hadith_no', h.hadith_no, 'volume', h.volume, 'url', h.url, 'page_ref', h.page_ref,
                 'chapter', h.chapter_title, 'text_ar', h.text_ar,
                 'matn_ar', h.matn_ar, 'sanad', h.sanad,
                 'english', case when tr.text is not null then json_build_object(
                   'text', tr.text, 'state', tr.state, 'translator', tr.translator, 'english_model', tr.model,
                   'english_source', tr.source, 'source_slug', src.slug, 'source_work_id', col.source_work_id) end,
                 'correspondence', case when m.rank > 0 then json_build_object(
                   'relation_class', c.relation_class, 'jaccard', c.jaccard, 'containment', c.containment,
                   'scope', c.scope, 'decision', c.decision, 'reviewed_relation', c.reviewed_relation,
                   'confirmed', c.confirmed) end)
               order by m.rank)
        from members m
        join ${relations.hadiths} h on h.id = m.id
        join collections col on col.id = h.collection_id
        join sources src on src.id = col.source_id
        join traditions t on t.id = h.tradition_id
        left join corresponding c on c.id = m.id and m.rank > 0
        left join lateral (
          select x.text, x.state, x.translator, x.model, x.source from ${relations.translations} x
          where x.hadith_id = h.id and x.language = 'en'
          order by x.id limit 1
        ) tr on true
      ) as tellings,
      ${chainNodesJson(relations.chains, sql`array(select id from members)`)} as nodes,
      (select json_object_agg(d.hadith_id, json_build_object('fix_id', d.fix_id, 'disposition', d.disposition, 'models', d.models,
                'runs', d.runs, 'decided_at', d.decided_at, 'awaiting_final_review', d.awaiting_final_review,
                'prompt_version', rp.prompt_version, 'prompt_path', rp.prompt_path, 'prompt_sha256', rp.prompt_sha256,
                'ai_review', ${stampReviewMarkSql(sql`d.ai_review`)}))
       from public_chain_fix_dispositions d
       left join lateral ${readerPromptLateralSql(sql`d.fix_id`)} rp on true
       where d.hadith_id in (select id from members)) as dispositions
  `;
}

function toCorrespondence(value: unknown): TellingCorrespondence | null {
  if (!value || typeof value !== 'object') return null;
  const row = value as Record<string, unknown>;
  const number = (field: unknown) => (field === null || field === undefined ? null : Number(field));
  return {
    relation_class: (text(row.relation_class) as CorrespondenceClass | null) ?? null,
    jaccard: number(row.jaccard),
    containment: number(row.containment),
    scope: (text(row.scope) as TellingCorrespondence['scope']) ?? null,
    decision: (text(row.decision) as TellingCorrespondence['decision']) ?? null,
    reviewed_relation: (text(row.reviewed_relation) as TellingCorrespondence['reviewed_relation']) ?? null,
    confirmed: row.confirmed === true,
  };
}

function toTellingEnglish(value: unknown): FamilyTelling['english'] {
  if (!value || typeof value !== 'object') return null;
  const row = value as Record<string, unknown>;
  const englishText = text(row.text);
  if (!englishText) return null;
  return { text: englishText, attribution: englishAttribution(String(row.state), row) };
}

/** Reads one family through the given relations; null when the report is not visible to this reader. */
export async function readReportFamily(relations: FamilyRelations, hadithId: string, cap = FAMILY_CAP): Promise<ReportFamily | null> {
  const row = await oneRow<{ total: number; tellings: Record<string, unknown>[] | null; nodes: Record<string, unknown>[] | null; dispositions: Record<string, ChainDisposition> | null }>(
    familyStatement(relations, hadithId, cap),
  );
  if (!row?.tellings || row.tellings.length === 0) return null;

  const nodesByHadith = new Map<string, ReturnType<typeof toChainNode>[]>();
  for (const node of row.nodes ?? []) {
    const id = String(node.hadith_id);
    nodesByHadith.set(id, [...(nodesByHadith.get(id) ?? []), toChainNode(node)]);
  }
  const tellings: FamilyTelling[] = row.tellings.map((telling) => {
    const id = String(telling.hadith_id);
    const tradition = String(telling.tradition) as HadithTraditionCode;
    const sourceWork = String(telling.source_work);
    const sourceWorkId = String(telling.source_work_id);
    const nodes = nodesByHadith.get(id) ?? [];
    const chain: ChainGraph = { hadith_id: id, tradition, source_work: sourceWork, chain_schema: 'v2', nodes, edges: chainEdges(nodes),
      disposition: row.dispositions?.[id] ?? null };
    return {
      hadith_id: id,
      record_id: String(telling.record_id),
      is_focal: telling.is_focal === true,
      tradition,
      collection_id: String(telling.collection_id),
      source_work: sourceWork,
      source_work_id: sourceWorkId,
      hadith_no: text(telling.hadith_no),
      numbering_citable: !UNCITABLE_NUMBERING_WORKS.has(sourceWorkId),
      volume: text(telling.volume),
      url: text(telling.url),
      page_ref: text(telling.page_ref),
      chapter: text(telling.chapter),
      text_ar: text(telling.text_ar),
      matn_ar: text(telling.matn_ar),
      sanad: text(telling.sanad),
      english: toTellingEnglish(telling.english),
      correspondence: telling.is_focal === true ? null : toCorrespondence(telling.correspondence),
      chain,
    };
  });
  const total = Number(row.total ?? 0);
  return { hadith_id: hadithId, tellings, correspondences_total: total, capped: total > cap, cap };
}

/** Public family of a public report: public tellings only, through the public views. */
export async function getReportFamily(hadithId: string, cap = FAMILY_CAP): Promise<ReportFamily | null> {
  return readReportFamily(PUBLIC_FAMILY_RELATIONS, hadithId, cap);
}

/** The family under a resolved request visibility (never constructed here: see src/lib/auth/visibility.ts). */
export async function getVisibleReportFamily(hadithId: string, visibility: ReadVisibility = PUBLIC_VISIBILITY, cap = FAMILY_CAP): Promise<ReportFamily | null> {
  return readReportFamily(familyRelationsFor(visibility), hadithId, cap);
}
