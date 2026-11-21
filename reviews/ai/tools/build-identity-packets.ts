/**
 * Build isnad-identity review packets from production (SELECT only, one READ ONLY transaction).
 * Run: npx tsx reviews/ai/tools/build-identity-packets.ts [--batch pilot-1] [--seed pilot-1] [--per-stratum 8]
 * Strata, gold items and isolation rules: reviews/ai/README.md §Packets and docs/review/specialist-plan.md §Pilot.
 */
import { readFileSync } from 'node:fs';
import { gunzipSync } from 'node:zlib';
import path from 'node:path';
import { claimContentSha256, claimKey, sha256Hex } from '../../../src/lib/review/claim-key';
import { chunk, glossaryExcerpt, neutralOrder, REPOSITORY_ROOT, withProductionReadOnly, writeBatch, type BuiltPacket } from './packet-common';
import { promptInfo, type PacketItem, type PacketItemBody, type PacketManifestItem } from './specialist-lib';

const SPECIALIST = 'isnad-identity';
const argument = (name: string, fallback: string) => {
  const index = process.argv.indexOf(`--${name}`);
  return index >= 0 ? process.argv[index + 1] : fallback;
};
const BATCH = argument('batch', 'pilot-1');
const SEED = argument('seed', BATCH);
const PER_STRATUM = Number(argument('per-stratum', '8'));
const ITEMS_PER_PACKET = 8;

/** Known answers, each with where the reading is recorded. Outcome is for the named candidate narrator. */
const GOLD: readonly { mentionId: string; narratorId: string; outcome: 'supports' | 'contradicts'; source: string }[] = [
  { mentionId: 'mention:k6:28255:0000:0004', narratorId: 'narrator:rawi:11046', outcome: 'contradicts', source: 'diagnostics/source-identity/README.md, disagreement example 1 (K6 is wrong: قيس بن أبي غرزة is not قيس بن أبي حازم)' },
  { mentionId: 'mention:k6:29504:0000:0001', narratorId: 'narrator:rawi:30002', outcome: 'contradicts', source: 'diagnostics/source-identity/README.md, example 4 (a transmitter inside the chain, not the compiler)' },
  { mentionId: 'mention:k6:1074:0000:0000', narratorId: 'narrator:rawi:30330', outcome: 'supports', source: 'diagnostics/source-identity/README.md, example 6 (أبو اليمان is al-Hakam b. Nafi)' },
  { mentionId: 'mention:k6:5500:0000:0001', narratorId: 'narrator:rawi:20278', outcome: 'supports', source: 'diagnostics/source-identity/README.md, example 8 (غندر is Muhammad b. Jaʿfar)' },
  { mentionId: 'mention:k6:19122:0001:0001', narratorId: 'narrator:rawi:20031', outcome: 'supports', source: 'docs/review/README.md worked example (Taqrib entry 7557; Musaddad from Yahya from Ubayd Allah)' },
];

const ASSERTED_BY: Readonly<Record<string, string>> = {
  source_index: 'Six-books source narrator index (K6, Kaggle fahd09/hadith-dataset)',
  source_index_confirmed_by_text: 'Six-books source narrator index (K6, Kaggle fahd09/hadith-dataset)',
  name_exact: 'Narrator lexicon (Muslim Scholars Database)',
  name_spelling_fold: 'Narrator lexicon (Muslim Scholars Database)',
  name_kunya_only: 'Narrator lexicon (Muslim Scholars Database)',
  imam_kunya_convention: "The archive's convention table for the Imams' kunyas in Imami chains",
};

interface ImamConventions {
  imams: { ordinal: number; id: string; name_ar: string; name_latin: string; known_as: string }[];
  kunyas: { kunya: string; shared_by: number[] }[];
}

/** Taqrib entries for lexicon rows that link to exactly one entry (biography-verification sidecars). */
function loadTaqribByScholar(): Map<string, { entry: string; page: string; passage: string }> {
  const directory = path.join(REPOSITORY_ROOT, 'datasets', 'hadith-data', 'diagnostics', 'biography-verification');
  const readJsonl = (file: string) =>
    gunzipSync(readFileSync(path.join(directory, file)))
      .toString('utf8')
      .split('\n')
      .filter(Boolean)
      .map((line) => JSON.parse(line) as Record<string, unknown>);
  const entries = new Map<string, { entry: string; page: string; passage: string }>();
  for (const row of readJsonl('rijal_entries_taqrib.jsonl.gz')) {
    entries.set(String(row.entry_number), { entry: String(row.entry_number), page: String(row.start_page), passage: String(row.passage_ar) });
  }
  const byScholar = new Map<string, { entry: string; page: string; passage: string }>();
  for (const link of readJsonl('lexicon_rijal_links.jsonl.gz')) {
    if (link.source !== 'ibn_hajar_taqrib' || link.status !== 'unique') continue;
    const entry = entries.get(String(link.entry_number));
    if (entry) byScholar.set(String(link.scholar_indx), entry);
  }
  return byScholar;
}

async function main() {
  const prompt = promptInfo(path.join(REPOSITORY_ROOT, 'reviews', 'ai', 'prompts', `${SPECIALIST}.md`));
  const conventions = JSON.parse(
    readFileSync(path.join(REPOSITORY_ROOT, 'datasets', 'hadith-data', 'pg_export', 'imam_kunya_conventions.json'), 'utf8'),
  ) as ImamConventions;
  const taqrib = loadTaqribByScholar();

  const result = await withProductionReadOnly(async (sql) => {
    const version = await sql`select id from dataset_versions where is_current`;
    const uncontested = await sql`
      select m.id from chain_mentions m where m.retired_at is null and m.narrator_id is not null
      order by sha256(convert_to(${SEED}::text || m.id, 'UTF8')) limit ${PER_STRATUM}`;
    const contested = await sql`
      select c.mention_id as id from chain_mention_candidates c
      where c.retired_at is null and c.basis <> 'name_kunya_only'
      group by c.mention_id having count(distinct c.narrator_id) > 1
      order by sha256(convert_to(${SEED}::text || c.mention_id, 'UTF8')) limit ${PER_STRATUM}`;
    const nameOnly = await sql`
      select c.mention_id as id from chain_mention_candidates c where c.retired_at is null
      group by c.mention_id having bool_and(c.basis in ('name_exact', 'name_spelling_fold'))
      order by sha256(convert_to(${SEED}::text || c.mention_id, 'UTF8')) limit ${PER_STRATUM}`;
    const imamKunya = await sql`
      select m.id from chain_mentions m join hadiths h on h.id = m.hadith_id
      where m.retired_at is null and h.tradition_id = 'tradition:imami' and m.surface_ar in ('أبي عبد الله', 'أبا عبد الله')
        and (position(m.surface_ar || ' عليه السلام' in h.text_ar) > 0 or position(m.surface_ar || ' (ع)' in h.text_ar) > 0)
      order by sha256(convert_to(${SEED}::text || m.id, 'UTF8')) limit ${Math.max(4, Math.floor(PER_STRATUM / 2))}`;

    const strata = new Map<string, string>();
    for (const row of GOLD) strata.set(row.mentionId, 'gold');
    for (const [name, rows] of [['ai_reviewed_uncontested', uncontested], ['contested', contested], ['name_match_only', nameOnly], ['imam_kunya', imamKunya]] as const) {
      for (const row of rows) if (!strata.has(row.id as string)) strata.set(row.id as string, name);
    }
    const mentionIds = [...strata.keys()];
    const mentions = await sql`
      select m.id, m.chain_id, m.hadith_id, m.position, m.surface_ar, m.resolution::text, m.narrator_id,
             h.text_ar, h.arabic_sha256, h.hadith_no, h.tradition_id, col.name as work
      from chain_mentions m join hadiths h on h.id = m.hadith_id join collections col on col.id = h.collection_id
      where m.id = any(${mentionIds})`;
    const chainIds = [...new Set(mentions.map((row) => row.chain_id as string))];
    const chainRows = await sql`select chain_id, position, surface_ar from chain_mentions where chain_id = any(${chainIds}) and retired_at is null order by chain_id, position`;
    const candidates = await sql`
      select c.mention_id, c.narrator_id, c.basis::text as basis
      from chain_mention_candidates c where c.mention_id = any(${mentionIds}) and c.retired_at is null`;
    const narratorIds = [...new Set(candidates.map((row) => row.narrator_id as string))];
    const narrators = await sql`
      select n.id, n.name, n.name_ar, n.scholar_indx, p.death_year_hijri_raw, p.tabaqah_raw, p.death_place
      from narrators n left join narrator_lexicon_profiles p on p.narrator_id = n.id where n.id = any(${narratorIds})`;
    return { version: version[0]?.id as string | undefined, strata, mentions, chainRows, candidates, narrators };
  });

  const narratorById = new Map(result.narrators.map((row) => [row.id as string, row]));
  const chainById = new Map<string, { position: number; surface_ar: string }[]>();
  for (const row of result.chainRows) {
    const list = chainById.get(row.chain_id as string) ?? [];
    list.push({ position: row.position as number, surface_ar: row.surface_ar as string });
    chainById.set(row.chain_id as string, list);
  }
  const imamByOrdinal = new Map(conventions.imams.map((imam) => [imam.ordinal, imam]));
  const builtItems: { item: PacketItemBody; claims: Omit<PacketManifestItem, 'item_id' | 'claim_id'>[]; mentionId: string }[] = [];

  for (const mention of neutralOrder(result.mentions, (row) => row.id as string, SEED)) {
    const mentionId = mention.id as string;
    const stratum = result.strata.get(mentionId)!;
    const byNarrator = new Map<string, Set<string>>();
    for (const row of result.candidates.filter((candidate) => candidate.mention_id === mentionId)) {
      const set = byNarrator.get(row.narrator_id as string) ?? new Set<string>();
      set.add(row.basis as string);
      byNarrator.set(row.narrator_id as string, set);
    }
    if (stratum === 'imam_kunya') {
      const kunya = conventions.kunyas.find((entry) => entry.kunya === 'أبو عبد الله');
      for (const ordinal of kunya?.shared_by ?? []) byNarrator.set(imamByOrdinal.get(ordinal)!.id, new Set(['imam_kunya_convention']));
    }
    if (byNarrator.size === 0) continue;

    const passages: { id: string; text: string; [key: string]: unknown }[] = [{ id: 'report', text: mention.text_ar as string, text_sha256: mention.arabic_sha256 }];
    const candidateEntries = neutralOrder([...byNarrator.entries()], ([id]) => id, `${SEED}:${mentionId}`).map(([narratorId, bases], index) => {
      const label = `C${index + 1}`;
      const narrator = narratorById.get(narratorId);
      const imam = conventions.imams.find((entry) => entry.id === narratorId);
      const rijal = narrator?.scholar_indx != null ? taqrib.get(String(narrator.scholar_indx)) : undefined;
      let passageId: string | null = null;
      if (rijal) {
        passageId = `P${passages.length}`;
        passages.push({
          id: passageId,
          text: rijal.passage,
          work: 'Ibn Hajar al-Asqalani, Taqrib al-Tahdhib',
          edition: 'ed. Muhammad Awwama, Dar al-Rashid, Syria, 1406/1986; OpenITI 0852IbnHajarCasqalani.TaqribTahdhib.JK000121-ara1',
          locator: `entry ${rijal.entry}, ${rijal.page}`,
          about: label,
        });
      }
      return {
        narratorId,
        bases,
        entry: {
          label,
          names: imam ? [imam.name_ar, imam.name_latin, imam.known_as] : [narrator?.name_ar, narrator?.name].filter(Boolean),
          recorded_death_year: imam ? null : (narrator?.death_year_hijri_raw ?? null),
          recorded_generation: imam ? null : (narrator?.tabaqah_raw ?? null),
          recorded_death_place: imam ? null : (narrator?.death_place ?? null),
          asserted_by: [...new Set([...bases].map((basis) => ASSERTED_BY[basis] ?? 'unknown source'))].sort(),
          rijal_passage: passageId,
        },
      };
    });

    builtItems.push({
      mentionId,
      item: {
        report: { locator: `${mention.work}, no. ${mention.hadith_no}`, text_sha256: mention.arabic_sha256 },
        chain: (chainById.get(mention.chain_id as string) ?? []).map((row) => ({ position: row.position, as_written: row.surface_ar })),
        target_position: mention.position,
        target_as_written: mention.surface_ar,
        candidates: candidateEntries.map((candidate) => candidate.entry),
        passages,
      },
      claims: candidateEntries.map((candidate) => {
        const key = claimKey.identity(mentionId, candidate.narratorId);
        const gold = GOLD.find((row) => row.mentionId === mentionId && row.narratorId === candidate.narratorId);
        return {
          claim_kind: 'identity',
          claim_key: key,
          content_sha256: claimContentSha256(key, [mention.arabic_sha256 as string, sha256Hex(mention.surface_ar as string)]),
          stratum,
          pipeline_view: `bases=${[...candidate.bases].sort().join('+')}; resolution=${mention.resolution}; standing=${mention.narrator_id === candidate.narratorId}`,
          ...(gold ? { known_answer: { outcome: gold.outcome, source: gold.source } } : {}),
          label: candidate.entry.label,
        } as Omit<PacketManifestItem, 'item_id' | 'claim_id'> & { label: string };
      }),
    });
  }

  const packets: BuiltPacket[] = chunk(builtItems, ITEMS_PER_PACKET).map((group) => {
    const items: PacketItem[] = [];
    const manifest: PacketManifestItem[] = [];
    group.forEach((built, index) => {
      const itemId = `I${index + 1}`;
      const claims = built.claims as (Omit<PacketManifestItem, 'item_id' | 'claim_id'> & { label: string })[];
      items.push({ item_id: itemId, claim_ids: claims.map((claim) => `${itemId}.${claim.label}`), ...built.item });
      for (const { label, ...claim } of claims) manifest.push({ item_id: itemId, claim_id: `${itemId}.${label}`, ...claim });
    });
    return { items, manifest };
  });

  const written = writeBatch({
    specialistId: SPECIALIST,
    promptVersion: prompt.version,
    batch: BATCH,
    packets,
    glossary: glossaryExcerpt(['isnad', 'mention', 'kunya', 'ism', 'nasab', 'nisba', 'laqab', 'derived-relation', 'tabaqa', 'rijal', 'mushtarak']),
    batchInfo: {
      specialist_id: SPECIALIST,
      prompt_version: prompt.version,
      prompt_sha256: prompt.sha256,
      batch: BATCH,
      seed: SEED,
      drawn_from: { database: 'production (SELECT only, READ ONLY transaction)', dataset_version_id: result.version ?? null },
      sampling: `per stratum, the first ${PER_STRATUM} mentions by sha256(seed || mention id); gold items always included`,
      strata: Object.fromEntries([...new Set(result.strata.values())].map((name) => [name, [...result.strata.values()].filter((value) => value === name).length])),
      items: builtItems.length,
      code_sha256: sha256Hex(readFileSync(__filename, 'utf8')),
    },
  });
  console.log(`wrote ${written.length} packets, ${builtItems.length} items:\n${written.join('\n')}`);
}

main().catch((error: unknown) => {
  console.error(error instanceof Error ? error.message : error);
  process.exit(1);
});
