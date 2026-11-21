/** Commentaries: admin list and CRUD, publish gate, public reads (sections 5.10, 9.1, 9.3). */
import 'server-only';
import { sql, type SQL } from 'drizzle-orm';
import { commentaries, commentaryHadiths, commentaryNarrators } from '@/db/schema';
import { REVIEWED_CITATION } from './assessment';
import type { CommentaryRecord } from './contracts';
import type { CurationStatus } from './enums';
import { mapCommentary } from './mappers';
import { rows, withReadRetry } from './sql-helpers';
import { allowlistedPatch, audit, CurationError, curationWrite, lockLiveRow, newId, txRows, type Transaction } from './write';

export interface CommentaryInput {
  text: string;
  text_arabic?: string | null;
  author?: string | null;
  source_work?: string | null;
  /** Free text; '' is stored as null (section 5.10). */
  type?: string | null;
  reference?: string | null;
  hadith_id?: string | null;
  narrator_id?: string | null;
}

/** `status` is deliberately absent: it changes only through publishCommentary. */
export type CommentaryPatch = Partial<Omit<CommentaryInput, 'hadith_id' | 'narrator_id'>> & { citation_id?: string | null };

const COMMENTARY_COLUMNS = {
  text: 'text',
  text_arabic: 'textArabic',
  author: 'author',
  source_work: 'sourceWork',
  type: 'type',
  reference: 'reference',
  citation_id: 'citationId',
} as const;

/** One commentary object with its first live hadith and narrator link (correlated, so rows never multiply). */
export function commentaryObject(hadithRelation: SQL): SQL {
  return sql`to_jsonb(c) || jsonb_build_object(
    'hadith', (select jsonb_build_object('id', h.id, 'chapter_title', h.chapter_title, 'category', h.category,
                                         'hadith_no', h.hadith_no, 'collection_name', col.name)
               from commentary_hadiths ch
               join ${hadithRelation} h on h.id = ch.hadith_id
               join collections col on col.id = h.collection_id
               where ch.commentary_id = c.id and ch.retired_at is null
               order by ch.id limit 1),
    'narrator', (select jsonb_build_object('id', n.id, 'name', n.name, 'name_en', n.name_en, 'name_ar', n.name_ar)
                 from commentary_narrators cn join narrators n on n.id = cn.narrator_id
                 where cn.commentary_id = c.id and cn.retired_at is null
                 order by cn.id limit 1))`;
}

/** Published commentaries about a narrator (public). */
export async function getPublishedCommentariesForNarrator(narratorId: string): Promise<CommentaryRecord[]> {
  const found = await withReadRetry(() =>
    rows<{ item: Record<string, unknown> }>(sql`
      select ${commentaryObject(sql`public_hadiths`)} as item
      from commentaries c
      join commentary_narrators cn on cn.commentary_id = c.id and cn.retired_at is null
      where cn.narrator_id = ${narratorId} and c.retired_at is null and c.status = 'published'
      order by c.created_at desc, c.id
    `),
  );
  return found.map((row) => mapCommentary(row.item));
}

/** Published commentaries on a public hadith. */
export async function getPublishedCommentariesForHadith(hadithId: string): Promise<CommentaryRecord[]> {
  const found = await withReadRetry(() =>
    rows<{ item: Record<string, unknown> }>(sql`
      select ${commentaryObject(sql`public_hadiths`)} as item
      from commentaries c
      join commentary_hadiths ch on ch.commentary_id = c.id and ch.retired_at is null
      join public_hadiths h on h.id = ch.hadith_id
      where ch.hadith_id = ${hadithId} and c.retired_at is null and c.status = 'published'
      order by c.created_at desc, c.id
    `),
  );
  return found.map((row) => mapCommentary(row.item));
}

async function linkHadith(tx: Transaction, actor: string, commentaryId: string, hadithId: string) {
  const [hadith] = await txRows<{ arabic_sha256: string }>(
    tx,
    sql`select arabic_sha256 from hadiths where id = ${hadithId} and retired_at is null`,
  );
  if (!hadith) throw new CurationError('not_found', 'Hadith not found.');
  await tx.insert(commentaryHadiths).values({
    commentaryId,
    hadithId,
    // Binds the commentary to the exact Arabic it was written against (curation drift check).
    boundArabicSha256: hadith.arabic_sha256,
    createdBy: actor,
  });
}

async function linkNarrator(tx: Transaction, actor: string, commentaryId: string, narratorId: string) {
  const [narrator] = await txRows(tx, sql`select 1 from narrators where id = ${narratorId} and retired_at is null`);
  if (!narrator) throw new CurationError('not_found', 'Narrator not found.');
  await tx.insert(commentaryNarrators).values({ commentaryId, narratorId, createdBy: actor });
}

/** Creates a `proposed` commentary and its links in one transaction. */
export async function createCommentary(actor: string, input: CommentaryInput): Promise<string> {
  const id = newId();
  return curationWrite(actor, async (tx) => {
    const [created] = await tx
      .insert(commentaries)
      .values({
        id,
        text: input.text,
        textArabic: input.text_arabic ?? null,
        author: input.author ?? null,
        sourceWork: input.source_work ?? null,
        type: input.type || null,
        reference: input.reference ?? null,
        origin: 'manual',
        createdBy: actor,
        updatedBy: actor,
      })
      .returning();
    if (input.hadith_id) await linkHadith(tx, actor, id, input.hadith_id);
    if (input.narrator_id) await linkNarrator(tx, actor, id, input.narrator_id);
    await audit(tx, {
      actor,
      action: 'create',
      entityType: 'commentary',
      entityId: id,
      after: { ...created, hadith_id: input.hadith_id ?? null, narrator_id: input.narrator_id ?? null },
    });
    return id;
  });
}

export async function updateCommentary(actor: string, id: string, patch: CommentaryPatch): Promise<void> {
  const set = allowlistedPatch({ ...patch, ...(patch.type !== undefined ? { type: patch.type || null } : {}) }, COMMENTARY_COLUMNS);
  if (Object.keys(set).length === 0) return;
  await curationWrite(actor, async (tx) => {
    const before = await lockLiveRow(tx, 'commentaries', id, 'Commentary');
    if (patch.citation_id) {
      const [citation] = await txRows(tx, sql`select 1 from citations where id = ${patch.citation_id} and retired_at is null`);
      if (!citation) throw new CurationError('not_found', 'Citation not found.');
    }
    const [after] = await tx
      .update(commentaries)
      .set({ ...(set as Partial<typeof commentaries.$inferInsert>), updatedAt: new Date(), updatedBy: actor })
      .where(sql`${commentaries.id} = ${id}`)
      .returning();
    await audit(tx, { actor, action: 'update', entityType: 'commentary', entityId: id, before, after });
  });
}

/** "Delete" retires the commentary and its live links (question 7: nothing is hard-deleted). */
export async function retireCommentary(actor: string, id: string): Promise<void> {
  await curationWrite(actor, async (tx) => {
    const before = await lockLiveRow(tx, 'commentaries', id, 'Commentary');
    await txRows(tx, sql`update commentaries set retired_at = now(), retired_by = ${actor}, updated_at = now(),
                          updated_by = ${actor} where id = ${id}`);
    const hadithLinks = await txRows(tx, sql`update commentary_hadiths set retired_at = now(), retired_by = ${actor}
                                             where commentary_id = ${id} and retired_at is null returning id`);
    const narratorLinks = await txRows(tx, sql`update commentary_narrators set retired_at = now(), retired_by = ${actor}
                                               where commentary_id = ${id} and retired_at is null returning id`);
    await audit(tx, {
      actor,
      action: 'retire',
      entityType: 'commentary',
      entityId: id,
      before,
      after: { retired_links: hadithLinks.length + narratorLinks.length },
    });
  });
}

/**
 * Sets the review status. `published` requires a live, reviewed citation: no owner commentary policy is
 * recorded yet (question 10), so the citation is the only route to publication.
 */
export async function publishCommentary(actor: string, id: string, status: CurationStatus): Promise<void> {
  await curationWrite(actor, async (tx) => {
    const before = await lockLiveRow(tx, 'commentaries', id, 'Commentary');
    if (status === 'published') {
      const [cited] = await txRows(
        tx,
        sql`select 1 from commentaries cm join citations c on c.id = cm.citation_id and ${REVIEWED_CITATION}
            where cm.id = ${id}`,
      );
      if (!cited) throw new CurationError('refused', 'A commentary needs a live, reviewed citation before it can be published.');
    }
    const [after] = await tx
      .update(commentaries)
      .set({ status, updatedAt: new Date(), updatedBy: actor })
      .where(sql`${commentaries.id} = ${id}`)
      .returning();
    await audit(tx, { actor, action: `status:${status}`, entityType: 'commentary', entityId: id, before, after });
  });
}
