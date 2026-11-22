/**
 * Read-only production reads for the chain-fix tools: a report's current text (as the reader read it), its hash, its work
 * and its live stored chain. One READ ONLY transaction on a read-only session (packet-common.ts).
 */
import { withProductionReadOnly } from './packet-common';
import type { BaseChain } from './chain-fix-lib';

/** Works whose packets give the source's chain field, a blank line, then the text (chain-reader/tools/build_pilot.py). */
export const CHAIN_FIELD_WORKS = new Set(['ahmad', 'darimi', 'muwatta']);

export async function readLiveReports(hadithIds: string[]) {
  const unique = [...new Set(hadithIds)];
  const out = new Map<string, { record_id: string; source_work_id: string; tradition: string; arabic_sha256: string; reader_text: string; chains: BaseChain[] }>();
  if (unique.length === 0) return out;
  await withProductionReadOnly(async (sql) => {
    const reports = await sql<{ id: string; record_id: string; text_ar: string | null; sanad: string | null; arabic_sha256: string; source_work_id: string; tradition: string }[]>`
      select h.id, h.record_id, h.text_ar, h.sanad, h.arabic_sha256, c.source_work_id, t.code::text as tradition
      from hadiths h join collections c on c.id = h.collection_id join traditions t on t.id = h.tradition_id
      where h.id = any(${unique}) and h.retired_at is null`;
    const mentions = await sql<{ chain_id: string; branch: number; structure_status: string | null; id: string; position: number; surface_ar: string; inherited_from_mention_id: string | null; hadith_id: string }[]>`
      select c.id as chain_id, c.branch, c.structure_status, m.id, m.position, m.surface_ar, m.inherited_from_mention_id, c.hadith_id
      from chains c join chain_mentions m on m.chain_id = c.id and m.retired_at is null
      where c.hadith_id = any(${unique}) and c.retired_at is null
      order by c.hadith_id, c.branch, m.position`;
    for (const report of reports) {
      const work = report.source_work_id.split(':').pop() ?? '';
      const sanad = (report.sanad ?? '').trim();
      const textAr = report.text_ar ?? '';
      const chains = new Map<string, BaseChain>();
      for (const row of mentions.filter((m) => m.hadith_id === report.id)) {
        const chain = chains.get(row.chain_id) ?? { chain_id: row.chain_id, branch: row.branch, structure_status: row.structure_status, mentions: [] };
        chain.mentions.push({ id: row.id, position: row.position, surface_ar: row.surface_ar, inherited_from_mention_id: row.inherited_from_mention_id });
        chains.set(row.chain_id, chain);
      }
      out.set(report.id, {
        record_id: report.record_id,
        source_work_id: report.source_work_id,
        tradition: report.tradition.toLowerCase(),
        arabic_sha256: report.arabic_sha256,
        reader_text: CHAIN_FIELD_WORKS.has(work) && sanad ? `${sanad}\n\n${textAr}` : textAr,
        chains: [...chains.values()],
      });
    }
  });
  return out;
}

/**
 * The earlier report a packet's previous-report entry stands for, when the reports file does not name it (batch 001's v3
 * packets): the one live report of the same collection whose reader text starts with that entry's text. Null unless unique.
 */
export async function findPreviousByText(lookups: { hadith_id: string; prefix: string }[]): Promise<Map<string, string | null>> {
  const out = new Map<string, string | null>();
  if (lookups.length === 0) return out;
  await withProductionReadOnly(async (sql) => {
    for (const lookup of lookups) {
      const rows = await sql<{ id: string }[]>`
        select p.id from hadiths h join hadiths p on p.collection_id = h.collection_id and p.retired_at is null and p.id <> h.id
        where h.id = ${lookup.hadith_id} and left(p.text_ar, ${lookup.prefix.length}) = ${lookup.prefix}
        limit 2`;
      out.set(`${lookup.hadith_id}\u001f${lookup.prefix}`, rows.length === 1 ? rows[0].id : null);
    }
  });
  return out;
}

/** Per report: the later reports whose live chains repeat its live mentions (`inherited_from_mention_id`); a fix there would break them. */
export async function readCitingReports(hadithIds: string[]): Promise<Map<string, string[]>> {
  const out = new Map<string, string[]>();
  const unique = [...new Set(hadithIds)];
  if (unique.length === 0) return out;
  await withProductionReadOnly(async (sql) => {
    const rows = await sql<{ cited: string; citing: string }[]>`
      select distinct w.hadith_id as cited, m.hadith_id as citing
      from chain_mentions m join chain_mentions w on w.id = m.inherited_from_mention_id and w.retired_at is null
      where w.hadith_id = any(${unique}) and m.hadith_id <> w.hadith_id and m.retired_at is null
      order by 1, 2`;
    for (const row of rows) out.set(row.cited, [...(out.get(row.cited) ?? []), row.citing]);
  });
  return out;
}
