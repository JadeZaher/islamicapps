/** Comparative study: faiths, source texts, motif tags, parallels; public reads and curated writes (sections 5.11, 9.2). */
import 'server-only';
import { sql, type SQL } from 'drizzle-orm';
import { crossParallels, motifTags, religiousTraditions, sourceTexts } from '@/db/schema';
import type {
  ComparativeStat,
  MotifTagRecord,
  Paginated,
  ParallelRecord,
  ReligiousTraditionRecord,
  SourceTextRecord,
  TraditionConnections,
} from './contracts';
import type { ConfidenceLevel, CurationStatus, IsraIliyyatStatus, MotifCategory, ParallelType } from './enums';
import { mapMotifTag, mapParallel, mapSourceText, text } from './mappers';
import { andAll, clampPage, oneRow, paginated, rows, withReadRetry, type PageRequest } from './sql-helpers';
import { allowlistedPatch, audit, CurationError, curationWrite, lockLiveRow, newId, txRows, type Transaction } from './write';

// ─── shared SQL ─────────────────────────────────────────────────────────────

/** Parallel object for alias `p` joined to `h` (hadith), `st` (source text) and `rt` (faith). */
export function parallelObject(excerpt: SQL): SQL {
  return sql`json_build_object(
    'id', p.id, 'hadith_id', p.hadith_id, 'parallel_type', p.parallel_type, 'isra_iliyyat_status', p.isra_iliyyat_status,
    'confidence_level', p.confidence_level, 'hadith_excerpt_en', ${excerpt},
    'source_text_original', p.source_text_original, 'source_text_en', p.source_text_en,
    'scholarly_analysis', p.scholarly_analysis, 'origin', p.origin, 'status', p.status, 'created_at', p.created_at,
    'hadith', json_build_object('id', h.id, 'chapter_title', h.chapter_title, 'category', h.category),
    'source_text_id', st.id, 'source_text_title', st.title, 'canonical_reference', st.canonical_reference,
    'religious_tradition_id', rt.id, 'tradition_name', rt.name,
    'motif_tags', coalesce((
      select json_agg(json_build_object('id', m.id, 'name', m.name, 'category', m.category, 'description', m.description)
                      order by m.category, m.name)
      from parallel_motif_tags pm join motif_tags m on m.id = pm.motif_tag_id and m.retired_at is null
      where pm.parallel_id = p.id and pm.retired_at is null), '[]'::json))`;
}

/** Joins for alias `p` under a hadith relation; only live source texts and faiths. */
export function parallelJoins(hadithRelation: SQL): SQL {
  return sql`join ${hadithRelation} h on h.id = p.hadith_id
    join source_texts st on st.id = p.source_text_id and st.retired_at is null
    join religious_traditions rt on rt.id = p.religious_tradition_id and rt.retired_at is null`;
}

/** Public: `hadith_excerpt_en` only when the hadith's English is itself public (section 9.2). */
const PUBLIC_EXCERPT = sql`case when exists (select 1 from public_translations pt where pt.hadith_id = p.hadith_id and pt.language = 'en')
                               then p.hadith_excerpt_en end`;

/** Public parallels: live, published, on a public hadith. */
const PUBLIC_PARALLEL = sql`p.retired_at is null and p.status = 'published'`;

export interface ParallelFilters {
  tradition_id?: string;
  parallel_type?: ParallelType;
  isra_iliyyat_status?: IsraIliyyatStatus;
  motif_category?: MotifCategory;
  confidence_level?: ConfidenceLevel;
}

function parallelFilterPredicates(filters: ParallelFilters): SQL[] {
  return [
    filters.tradition_id ? sql`p.religious_tradition_id = ${filters.tradition_id}` : undefined,
    filters.parallel_type ? sql`p.parallel_type = ${filters.parallel_type}` : undefined,
    filters.isra_iliyyat_status ? sql`p.isra_iliyyat_status = ${filters.isra_iliyyat_status}` : undefined,
    filters.confidence_level ? sql`p.confidence_level = ${filters.confidence_level}` : undefined,
    filters.motif_category
      ? sql`exists (select 1 from parallel_motif_tags pm join motif_tags m on m.id = pm.motif_tag_id and m.retired_at is null
                    where pm.parallel_id = p.id and pm.retired_at is null and m.category = ${filters.motif_category})`
      : undefined,
  ].filter((predicate): predicate is SQL => Boolean(predicate));
}

/** Pages parallels newest first with a total, under the given relation, gate and excerpt rule. */
export async function pageParallels(
  hadithRelation: SQL,
  gate: SQL,
  excerpt: SQL,
  request?: PageRequest,
): Promise<Paginated<ParallelRecord>> {
  const window = clampPage(request, Number.MAX_SAFE_INTEGER);
  const row = await oneRow<{ total: number; items: Record<string, unknown>[] }>(sql`
    select (select count(*)::int from cross_parallels p ${parallelJoins(hadithRelation)} where ${gate}) as total,
           coalesce((select json_agg(${parallelObject(excerpt)} order by p.created_at desc, p.id)
                     from (select p.* from cross_parallels p ${parallelJoins(hadithRelation)} where ${gate}
                           order by p.created_at desc, p.id limit ${window.limit} offset ${window.offset}) p
                     ${parallelJoins(hadithRelation)}), '[]'::json) as items
  `);
  return paginated((row?.items ?? []).map(mapParallel), row?.total ?? 0, window);
}

// ─── public reads ───────────────────────────────────────────────────────────

export async function listPublicParallels(request?: PageRequest): Promise<Paginated<ParallelRecord>> {
  return pageParallels(sql`public_hadiths`, PUBLIC_PARALLEL, PUBLIC_EXCERPT, request);
}

/** Filtered public parallels, at most 100, ordered by faith then type (searchParallels). */
export async function searchPublicParallels(filters: ParallelFilters = {}): Promise<ParallelRecord[]> {
  const found = await withReadRetry(() =>
    rows<{ item: Record<string, unknown> }>(sql`
      select ${parallelObject(PUBLIC_EXCERPT)} as item
      from cross_parallels p ${parallelJoins(sql`public_hadiths`)}
      where ${andAll([PUBLIC_PARALLEL, ...parallelFilterPredicates(filters)])}
      order by rt.name, p.parallel_type, p.created_at desc, p.id
      limit 100
    `),
  );
  return found.map((row) => mapParallel(row.item));
}

export async function getPublicParallelsForHadith(hadithId: string): Promise<ParallelRecord[]> {
  const found = await withReadRetry(() =>
    rows<{ item: Record<string, unknown> }>(sql`
      select ${parallelObject(PUBLIC_EXCERPT)} as item
      from cross_parallels p ${parallelJoins(sql`public_hadiths`)}
      where ${PUBLIC_PARALLEL} and p.hadith_id = ${hadithId}
      order by p.created_at, p.id
    `),
  );
  return found.map((row) => mapParallel(row.item));
}

/** Counts of public parallels per faith and type. */
export async function getComparativeStats(): Promise<ComparativeStat[]> {
  const found = await withReadRetry(() =>
    rows<{ tradition: string; type: string; count: number }>(sql`
      select rt.name as tradition, p.parallel_type::text as type, count(*)::int as count
      from cross_parallels p ${parallelJoins(sql`public_hadiths`)}
      where ${PUBLIC_PARALLEL}
      group by rt.name, p.parallel_type
      order by rt.name, p.parallel_type
    `),
  );
  return found.map((row) => ({ tradition: row.tradition, type: row.type, count: Number(row.count) }));
}

/** Live faiths with counts of live source texts and narrator links. */
export async function listReligiousTraditions(): Promise<ReligiousTraditionRecord[]> {
  const found = await withReadRetry(() =>
    rows<Record<string, unknown>>(sql`
      select rt.*,
             (select count(*)::int from source_texts st where st.religious_tradition_id = rt.id and st.retired_at is null) as source_count,
             (select count(*)::int from narrator_religious_traditions nr
               where nr.religious_tradition_id = rt.id and nr.retired_at is null) as narrator_count
      from religious_traditions rt
      where rt.retired_at is null
      order by rt.name
    `),
  );
  return found.map((row) => ({
    id: String(row.id),
    name: String(row.name),
    name_arabic: text(row.name_arabic),
    description: text(row.description),
    geographic_origin: text(row.geographic_origin),
    geographic_heartlands: (row.geographic_heartlands as string[] | null) ?? [],
    source_count: Number(row.source_count),
    narrator_count: Number(row.narrator_count),
  }));
}

export async function listSourceTexts(filters: { tradition_name?: string } = {}): Promise<SourceTextRecord[]> {
  const found = await withReadRetry(() =>
    rows<Record<string, unknown>>(sql`
      select st.*, rt.name as tradition_name
      from source_texts st
      join religious_traditions rt on rt.id = st.religious_tradition_id
      where st.retired_at is null ${filters.tradition_name ? sql`and rt.name = ${filters.tradition_name}` : sql``}
      order by rt.name, st.title, st.id
    `),
  );
  return found.map(mapSourceText);
}

export async function listMotifTags(category?: MotifCategory): Promise<MotifTagRecord[]> {
  const found = await withReadRetry(() =>
    rows<Record<string, unknown>>(sql`
      select * from motif_tags m
      where m.retired_at is null ${category ? sql`and m.category = ${category}` : sql``}
      order by m.category, m.name
    `),
  );
  return found.map(mapMotifTag);
}

/** Faiths a narrator is linked to, and public hadiths through the narrator that carry published parallels (limit 50). */
export async function getTraditionConnectionsForNarrator(narratorId: string): Promise<TraditionConnections> {
  const row = await oneRow<{ traditions: Record<string, unknown>[]; parallels: Record<string, unknown>[] }>(sql`
    select
      coalesce((select json_agg(json_build_object('id', rt.id, 'name', rt.name, 'name_arabic', rt.name_arabic,
                                                  'description', rt.description) order by rt.name)
                from narrator_religious_traditions nr
                join religious_traditions rt on rt.id = nr.religious_tradition_id and rt.retired_at is null
                where nr.narrator_id = ${narratorId} and nr.retired_at is null), '[]'::json) as traditions,
      coalesce((select json_agg(x order by x.sort_key, x.hadith_no_int nulls last, x.parallel_id)
                from (
                  select distinct h.id as hadith_id, coalesce(h.chapter_title, h.category) as hadith_title,
                         h.collection_sort_key as sort_key, h.hadith_no_int,
                         p.id as parallel_id, p.parallel_type, p.isra_iliyyat_status,
                         rt.id as tradition_id, rt.name as tradition_name,
                         st.title as source_title, st.canonical_reference
                  from public_chain_links l
                  join cross_parallels p on p.hadith_id = l.hadith_id and ${PUBLIC_PARALLEL}
                  ${parallelJoins(sql`public_hadiths`)}
                  where l.narrator_id = ${narratorId} and l.is_link
                  order by h.collection_sort_key, h.hadith_no_int nulls last, p.id
                  limit 50) x), '[]'::json) as parallels
  `);
  return {
    traditions: (row?.traditions ?? []).map((tradition) => ({
      id: String(tradition.id),
      name: String(tradition.name),
      name_arabic: text(tradition.name_arabic),
      description: text(tradition.description),
    })),
    hadiths_with_parallels: (row?.parallels ?? []).map((entry) => ({
      hadith: { id: String(entry.hadith_id), title: text(entry.hadith_title) },
      parallel: {
        id: String(entry.parallel_id),
        parallel_type: String(entry.parallel_type),
        isra_iliyyat_status: String(entry.isra_iliyyat_status),
      },
      tradition: { id: String(entry.tradition_id), name: String(entry.tradition_name) },
      source_text: { title: String(entry.source_title), canonical_reference: text(entry.canonical_reference) },
    })),
  };
}

// ─── writes ─────────────────────────────────────────────────────────────────

async function requireLive(tx: Transaction, table: string, id: string, label: string): Promise<void> {
  const [found] = await txRows(tx, sql`select 1 from ${sql.identifier(table)} where id = ${id} and retired_at is null`);
  if (!found) throw new CurationError('not_found', `${label} not found.`);
}

/** Retires every live link row in `table` whose `column` equals `id`; returns how many. */
async function retireLinks(tx: Transaction, actor: string, table: string, column: string, id: string): Promise<number> {
  const retired = await txRows(
    tx,
    sql`update ${sql.identifier(table)} set retired_at = now(), retired_by = ${actor}
        where ${sql.identifier(column)} = ${id} and retired_at is null returning id`,
  );
  return retired.length;
}

async function retireEntity(tx: Transaction, actor: string, table: string, id: string): Promise<void> {
  await txRows(tx, sql`update ${sql.identifier(table)} set retired_at = now(), retired_by = ${actor}, updated_at = now(),
                        updated_by = ${actor} where id = ${id}`);
}

export interface ReligiousTraditionInput {
  name: string;
  name_arabic?: string | null;
  description?: string | null;
  geographic_origin?: string | null;
  geographic_heartlands?: string[];
}

const TRADITION_COLUMNS = {
  name: 'name',
  name_arabic: 'nameArabic',
  description: 'description',
  geographic_origin: 'geographicOrigin',
  geographic_heartlands: 'geographicHeartlands',
} as const;

export async function createReligiousTradition(actor: string, input: ReligiousTraditionInput): Promise<string> {
  const id = newId();
  return curationWrite(actor, async (tx) => {
    const [created] = await tx
      .insert(religiousTraditions)
      .values({
        id,
        name: input.name,
        nameArabic: input.name_arabic ?? null,
        description: input.description ?? null,
        geographicOrigin: input.geographic_origin ?? null,
        geographicHeartlands: input.geographic_heartlands ?? [],
        createdBy: actor,
        updatedBy: actor,
      })
      .returning();
    await audit(tx, { actor, action: 'create', entityType: 'religious_tradition', entityId: id, after: created });
    return id;
  });
}

export async function updateReligiousTradition(actor: string, id: string, patch: Partial<ReligiousTraditionInput>): Promise<void> {
  const set = allowlistedPatch(
    patch.geographic_heartlands === undefined ? patch : { ...patch, geographic_heartlands: patch.geographic_heartlands ?? [] },
    TRADITION_COLUMNS,
  );
  if (Object.keys(set).length === 0) return;
  await curationWrite(actor, async (tx) => {
    const before = await lockLiveRow(tx, 'religious_traditions', id, 'Tradition');
    const [after] = await tx
      .update(religiousTraditions)
      .set({ ...(set as Partial<typeof religiousTraditions.$inferInsert>), updatedAt: new Date(), updatedBy: actor })
      .where(sql`${religiousTraditions.id} = ${id}`)
      .returning();
    await audit(tx, { actor, action: 'update', entityType: 'religious_tradition', entityId: id, before, after });
  });
}

/** Refused while live parallels or source texts reference the faith (an explicit check: soft deletes never fire the FK). */
export async function retireReligiousTradition(actor: string, id: string): Promise<void> {
  await curationWrite(actor, async (tx) => {
    const before = await lockLiveRow(tx, 'religious_traditions', id, 'Tradition');
    const [referenced] = await txRows(tx, sql`
      select 1 where exists (select 1 from cross_parallels where religious_tradition_id = ${id} and retired_at is null)
                  or exists (select 1 from source_texts where religious_tradition_id = ${id} and retired_at is null)`);
    if (referenced) throw new CurationError('refused', 'Live parallels or source texts still belong to this tradition.');
    await retireEntity(tx, actor, 'religious_traditions', id);
    const links =
      (await retireLinks(tx, actor, 'narrator_religious_traditions', 'religious_tradition_id', id)) +
      (await retireLinks(tx, actor, 'location_religious_traditions', 'religious_tradition_id', id));
    await audit(tx, { actor, action: 'retire', entityType: 'religious_tradition', entityId: id, before, after: { retired_links: links } });
  });
}

export interface SourceTextInput {
  title: string;
  religious_tradition_id: string;
  title_original?: string | null;
  author?: string | null;
  approximate_date_ce?: string | null;
  canonical_reference?: string | null;
  description?: string | null;
}

const SOURCE_TEXT_COLUMNS = {
  title: 'title',
  religious_tradition_id: 'religiousTraditionId',
  title_original: 'titleOriginal',
  author: 'author',
  approximate_date_ce: 'approximateDateCe',
  canonical_reference: 'canonicalReference',
  description: 'description',
} as const;

/** Resolves a faith by ID or, for legacy callers, by live name. */
export async function resolveReligiousTraditionId(tx: Transaction, idOrName: { id?: string | null; name?: string | null }): Promise<string> {
  const [found] = await txRows<{ id: string }>(
    tx,
    idOrName.id
      ? sql`select id from religious_traditions where id = ${idOrName.id} and retired_at is null`
      : sql`select id from religious_traditions where name = ${idOrName.name ?? ''} and retired_at is null`,
  );
  if (!found) throw new CurationError('not_found', 'Tradition not found.');
  return found.id;
}

/** Creates a source text in its faith; the separate link call of the Neo4j era is part of create (section 9.2). */
export async function createSourceText(
  actor: string,
  input: Omit<SourceTextInput, 'religious_tradition_id'> & { religious_tradition_id?: string | null; tradition_name?: string | null },
): Promise<string> {
  const id = newId();
  return curationWrite(actor, async (tx) => {
    const traditionId = await resolveReligiousTraditionId(tx, { id: input.religious_tradition_id, name: input.tradition_name });
    const [created] = await tx
      .insert(sourceTexts)
      .values({
        id,
        religiousTraditionId: traditionId,
        title: input.title,
        titleOriginal: input.title_original ?? null,
        author: input.author ?? null,
        approximateDateCe: input.approximate_date_ce ?? null,
        canonicalReference: input.canonical_reference ?? null,
        description: input.description ?? null,
        origin: 'manual',
        createdBy: actor,
        updatedBy: actor,
      })
      .returning();
    await audit(tx, { actor, action: 'create', entityType: 'source_text', entityId: id, after: created });
    return id;
  });
}

export async function updateSourceText(actor: string, id: string, patch: Partial<SourceTextInput>): Promise<void> {
  const set = allowlistedPatch(patch, SOURCE_TEXT_COLUMNS);
  if (Object.keys(set).length === 0) return;
  await curationWrite(actor, async (tx) => {
    const before = await lockLiveRow(tx, 'source_texts', id, 'Source text');
    if (patch.religious_tradition_id) await requireLive(tx, 'religious_traditions', patch.religious_tradition_id, 'Tradition');
    const [after] = await tx
      .update(sourceTexts)
      .set({ ...(set as Partial<typeof sourceTexts.$inferInsert>), updatedAt: new Date(), updatedBy: actor })
      .where(sql`${sourceTexts.id} = ${id}`)
      .returning();
    await audit(tx, { actor, action: 'update', entityType: 'source_text', entityId: id, before, after });
  });
}

export async function retireSourceText(actor: string, id: string): Promise<void> {
  await curationWrite(actor, async (tx) => {
    const before = await lockLiveRow(tx, 'source_texts', id, 'Source text');
    const [referenced] = await txRows(tx, sql`select 1 from cross_parallels where source_text_id = ${id} and retired_at is null limit 1`);
    if (referenced) throw new CurationError('refused', 'Live parallels still cite this source text.');
    await retireEntity(tx, actor, 'source_texts', id);
    await audit(tx, { actor, action: 'retire', entityType: 'source_text', entityId: id, before });
  });
}

export async function createMotifTag(
  actor: string,
  input: { name: string; category: MotifCategory; description?: string | null },
): Promise<string> {
  const id = newId();
  return curationWrite(actor, async (tx) => {
    const [created] = await tx
      .insert(motifTags)
      .values({
        id,
        name: input.name,
        category: input.category,
        description: input.description ?? null,
        origin: 'manual',
        createdBy: actor,
        updatedBy: actor,
      })
      .returning();
    await audit(tx, { actor, action: 'create', entityType: 'motif_tag', entityId: id, after: created });
    return id;
  });
}

export async function retireMotifTag(actor: string, id: string): Promise<void> {
  await curationWrite(actor, async (tx) => {
    const before = await lockLiveRow(tx, 'motif_tags', id, 'Motif tag');
    await retireEntity(tx, actor, 'motif_tags', id);
    const links =
      (await retireLinks(tx, actor, 'hadith_motif_tags', 'motif_tag_id', id)) +
      (await retireLinks(tx, actor, 'parallel_motif_tags', 'motif_tag_id', id));
    await audit(tx, { actor, action: 'retire', entityType: 'motif_tag', entityId: id, before, after: { retired_links: links } });
  });
}

/** Inserts a live link unless one exists (`on conflict` names the partial unique index's predicate). */
async function insertLink(
  tx: Transaction,
  actor: string,
  link: { table: string; columns: [string, string]; values: [string, string]; entityType: string },
): Promise<void> {
  const [left, right] = link.columns.map((column) => sql.identifier(column));
  const inserted = await txRows<{ id: number }>(
    tx,
    sql`insert into ${sql.identifier(link.table)} (${left}, ${right}, created_by)
        values (${link.values[0]}, ${link.values[1]}, ${actor})
        on conflict (${left}, ${right}) where retired_at is null do nothing
        returning id`,
  );
  if (inserted[0]) {
    await audit(tx, {
      actor,
      action: 'link',
      entityType: link.entityType,
      entityId: String(inserted[0].id),
      after: { [link.columns[0]]: link.values[0], [link.columns[1]]: link.values[1] },
    });
  }
}

/** Retires the live link for a pair; returns whether one existed. */
async function retirePair(
  tx: Transaction,
  actor: string,
  link: { table: string; columns: [string, string]; values: [string, string]; entityType: string },
): Promise<boolean> {
  const [left, right] = link.columns.map((column) => sql.identifier(column));
  const retired = await txRows<{ id: number }>(
    tx,
    sql`update ${sql.identifier(link.table)} set retired_at = now(), retired_by = ${actor}
        where ${left} = ${link.values[0]} and ${right} = ${link.values[1]} and retired_at is null returning id`,
  );
  for (const row of retired) {
    await audit(tx, { actor, action: 'unlink', entityType: link.entityType, entityId: String(row.id) });
  }
  return retired.length > 0;
}

export async function tagHadith(actor: string, hadithId: string, motifTagId: string): Promise<void> {
  await curationWrite(actor, async (tx) => {
    await requireLive(tx, 'hadiths', hadithId, 'Hadith');
    await requireLive(tx, 'motif_tags', motifTagId, 'Motif tag');
    await insertLink(tx, actor, {
      table: 'hadith_motif_tags',
      columns: ['hadith_id', 'motif_tag_id'],
      values: [hadithId, motifTagId],
      entityType: 'hadith_motif_tag',
    });
  });
}

export async function untagHadith(actor: string, hadithId: string, motifTagId: string): Promise<void> {
  await curationWrite(actor, async (tx) => {
    await retirePair(tx, actor, {
      table: 'hadith_motif_tags',
      columns: ['hadith_id', 'motif_tag_id'],
      values: [hadithId, motifTagId],
      entityType: 'hadith_motif_tag',
    });
  });
}

async function tagParallelInTransaction(tx: Transaction, actor: string, parallelId: string, motifTagId: string) {
  await requireLive(tx, 'motif_tags', motifTagId, 'Motif tag');
  await insertLink(tx, actor, {
    table: 'parallel_motif_tags',
    columns: ['parallel_id', 'motif_tag_id'],
    values: [parallelId, motifTagId],
    entityType: 'parallel_motif_tag',
  });
}

export async function tagParallel(actor: string, parallelId: string, motifTagId: string): Promise<void> {
  await curationWrite(actor, async (tx) => {
    await requireLive(tx, 'cross_parallels', parallelId, 'Parallel');
    await tagParallelInTransaction(tx, actor, parallelId, motifTagId);
  });
}

export interface CrossParallelInput {
  hadith_id: string;
  source_text_id: string;
  tradition_id: string;
  parallel_type: ParallelType;
  isra_iliyyat_status?: IsraIliyyatStatus;
  confidence_level?: ConfidenceLevel;
  hadith_excerpt_en?: string | null;
  source_text_original?: string | null;
  source_text_en?: string | null;
  scholarly_analysis?: string | null;
  motif_tag_ids?: string[];
}

/** True when the hadith is currently served by `public_hadiths`. */
async function isPublicHadith(tx: Transaction, hadithId: string): Promise<boolean> {
  const [found] = await txRows(tx, sql`select 1 from public_hadiths where id = ${hadithId}`);
  return Boolean(found);
}

/**
 * Creates a manual parallel and its motif tags in one transaction, bound to the hadith's Arabic hash. A manual
 * parallel starts `published` only when its hadith is public (the publishParallel gate), otherwise `proposed`.
 */
export async function createCrossParallel(actor: string, input: CrossParallelInput): Promise<string> {
  const id = newId();
  return curationWrite(actor, async (tx) => {
    const [hadith] = await txRows<{ arabic_sha256: string }>(
      tx,
      sql`select arabic_sha256 from hadiths where id = ${input.hadith_id} and retired_at is null`,
    );
    if (!hadith) throw new CurationError('not_found', 'Hadith not found.');
    await requireLive(tx, 'source_texts', input.source_text_id, 'Source text');
    await requireLive(tx, 'religious_traditions', input.tradition_id, 'Tradition');
    const status: CurationStatus = (await isPublicHadith(tx, input.hadith_id)) ? 'published' : 'proposed';
    const [created] = await tx
      .insert(crossParallels)
      .values({
        id,
        hadithId: input.hadith_id,
        boundArabicSha256: hadith.arabic_sha256,
        sourceTextId: input.source_text_id,
        religiousTraditionId: input.tradition_id,
        parallelType: input.parallel_type,
        israIliyyatStatus: input.isra_iliyyat_status ?? 'NONE',
        confidenceLevel: input.confidence_level ?? 'MEDIUM',
        hadithExcerptEn: input.hadith_excerpt_en ?? null,
        sourceTextOriginal: input.source_text_original ?? null,
        sourceTextEn: input.source_text_en ?? null,
        scholarlyAnalysis: input.scholarly_analysis ?? null,
        origin: 'manual',
        status,
        createdBy: actor,
        updatedBy: actor,
      })
      .returning();
    for (const tagId of input.motif_tag_ids ?? []) await tagParallelInTransaction(tx, actor, id, tagId);
    await audit(tx, { actor, action: 'create', entityType: 'cross_parallel', entityId: id, after: created });
    return id;
  });
}

export type ParallelPatch = Partial<
  Pick<
    CrossParallelInput,
    | 'parallel_type'
    | 'isra_iliyyat_status'
    | 'confidence_level'
    | 'hadith_excerpt_en'
    | 'source_text_original'
    | 'source_text_en'
    | 'scholarly_analysis'
  >
>;

/** Typed allowlist: replaces the Cypher key interpolation of the Neo4j action (section 9.2). `status` is excluded. */
const PARALLEL_COLUMNS = {
  parallel_type: 'parallelType',
  isra_iliyyat_status: 'israIliyyatStatus',
  confidence_level: 'confidenceLevel',
  hadith_excerpt_en: 'hadithExcerptEn',
  source_text_original: 'sourceTextOriginal',
  source_text_en: 'sourceTextEn',
  scholarly_analysis: 'scholarlyAnalysis',
} as const;

export async function updateParallel(actor: string, id: string, patch: ParallelPatch): Promise<void> {
  const set = allowlistedPatch(patch, PARALLEL_COLUMNS);
  if (Object.keys(set).length === 0) return;
  await curationWrite(actor, async (tx) => {
    const before = await lockLiveRow(tx, 'cross_parallels', id, 'Parallel');
    const [after] = await tx
      .update(crossParallels)
      .set({ ...(set as Partial<typeof crossParallels.$inferInsert>), updatedAt: new Date(), updatedBy: actor })
      .where(sql`${crossParallels.id} = ${id}`)
      .returning();
    await audit(tx, { actor, action: 'update', entityType: 'cross_parallel', entityId: id, before, after });
  });
}

export async function retireParallel(actor: string, id: string): Promise<void> {
  await curationWrite(actor, async (tx) => {
    const before = await lockLiveRow(tx, 'cross_parallels', id, 'Parallel');
    await retireEntity(tx, actor, 'cross_parallels', id);
    const links = await retireLinks(tx, actor, 'parallel_motif_tags', 'parallel_id', id);
    await audit(tx, { actor, action: 'retire', entityType: 'cross_parallel', entityId: id, before, after: { retired_links: links } });
  });
}

/** Sets a parallel's review status; `published` requires its hadith to be in `public_hadiths` (section 9.3). */
export async function publishParallel(actor: string, id: string, status: CurationStatus): Promise<void> {
  await curationWrite(actor, async (tx) => {
    const before = await lockLiveRow(tx, 'cross_parallels', id, 'Parallel');
    if (status === 'published' && !(await isPublicHadith(tx, String(before.hadith_id)))) {
      throw new CurationError('refused', 'A parallel can be published only on a hadith the public site shows.');
    }
    const [after] = await tx
      .update(crossParallels)
      .set({ status, updatedAt: new Date(), updatedBy: actor })
      .where(sql`${crossParallels.id} = ${id}`)
      .returning();
    await audit(tx, { actor, action: `status:${status}`, entityType: 'cross_parallel', entityId: id, before, after });
  });
}

export async function linkNarratorToTradition(actor: string, narratorId: string, traditionId: string): Promise<void> {
  await curationWrite(actor, async (tx) => {
    await requireLive(tx, 'narrators', narratorId, 'Narrator');
    await requireLive(tx, 'religious_traditions', traditionId, 'Tradition');
    await insertLink(tx, actor, {
      table: 'narrator_religious_traditions',
      columns: ['narrator_id', 'religious_tradition_id'],
      values: [narratorId, traditionId],
      entityType: 'narrator_religious_tradition',
    });
  });
}

export async function unlinkNarratorFromTradition(actor: string, narratorId: string, traditionId: string): Promise<void> {
  await curationWrite(actor, async (tx) => {
    await retirePair(tx, actor, {
      table: 'narrator_religious_traditions',
      columns: ['narrator_id', 'religious_tradition_id'],
      values: [narratorId, traditionId],
      entityType: 'narrator_religious_tradition',
    });
  });
}

export async function linkLocationToTradition(actor: string, locationId: string, traditionId: string): Promise<void> {
  await curationWrite(actor, async (tx) => {
    await requireLive(tx, 'locations', locationId, 'Location');
    await requireLive(tx, 'religious_traditions', traditionId, 'Tradition');
    await insertLink(tx, actor, {
      table: 'location_religious_traditions',
      columns: ['location_id', 'religious_tradition_id'],
      values: [locationId, traditionId],
      entityType: 'location_religious_tradition',
    });
  });
}
