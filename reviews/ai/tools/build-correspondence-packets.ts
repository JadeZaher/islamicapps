/**
 * Build correspondence review packets from production (SELECT only, one READ ONLY transaction).
 * Run: npx tsx reviews/ai/tools/build-correspondence-packets.ts [--batch pilot-1] [--seed pilot-1] [--per-stratum 5]
 * The reviewer sees both texts and their locators, never the scores, class or band. See reviews/ai/README.md.
 */
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { claimContentSha256, claimKey, sha256Hex } from '../../../src/lib/review/claim-key';
import { chunk, glossaryExcerpt, neutralOrder, REPOSITORY_ROOT, withProductionReadOnly, writeBatch, type BuiltPacket } from './packet-common';
import { promptInfo, type PacketItem, type PacketItemBody, type PacketManifestItem } from './specialist-lib';

const SPECIALIST = 'correspondence';
const argument = (name: string, fallback: string) => {
  const index = process.argv.indexOf(`--${name}`);
  return index >= 0 ? process.argv[index + 1] : fallback;
};
const BATCH = argument('batch', 'pilot-1');
const SEED = argument('seed', BATCH);
const PER_STRATUM = Number(argument('per-stratum', '5'));
const ITEMS_PER_PACKET = 6;

/** Pairs with a recorded reading (one reader, diagnostics/report-correspondence/README.md §Precision examples). */
const GOLD: readonly { a: string; b: string; outcome: 'supports' | 'contradicts'; reading: string; source: string }[] = [
  { a: 'hadith:k6:19825', b: 'hadith:thaqalayn:e4c7d3b25369713d76eb9a54', outcome: 'supports', reading: 'same_report', source: 'report-correspondence README example 1' },
  { a: 'hadith:pure-canon:pc_73535', b: 'hadith:thaqalayn:52082747757d55b14c7970b8', outcome: 'supports', reading: 'same_report_variant', source: 'report-correspondence README example 2' },
  { a: 'hadith:openiti:zaydi:zayd_0613|613|V01P382', b: 'hadith:thaqalayn:ac5af7210a58861b0fcf63a9', outcome: 'supports', reading: 'shared_passage', source: 'report-correspondence README example 3' },
  { a: 'hadith:k6:33185', b: 'hadith:thaqalayn:e532c2d8d54f19057995a200', outcome: 'contradicts', reading: 'shared_formula_or_verse', source: 'report-correspondence README example 5 (same frame, different three)' },
  { a: 'hadith:pure-canon:pc_29780', b: 'hadith:thaqalayn:466e90b70a62c5cf0454e4da', outcome: 'contradicts', reading: 'shared_formula_or_verse', source: 'report-correspondence README example 6 (only the shahada is shared)' },
];
/** The owner brief's worked example: included for reading, with no recorded answer. */
const WORKED_EXAMPLE = { a: 'hadith:k6:19122', b: 'hadith:thaqalayn:06c871a7dec1feb72290ba14' };

const STRATA: readonly { name: string; where: string }[] = [
  { name: 'same_wording', where: `relation_class = 'same_wording'` },
  { name: 'variant_shown', where: `relation_class = 'same_report_variant_wording' and jaccard >= 0.4 and scope <> 'cross_tradition'` },
  { name: 'variant_below_display', where: `relation_class = 'same_report_variant_wording' and jaccard < 0.4` },
  { name: 'partial_shown', where: `relation_class = 'partial_overlap' and containment >= 0.7` },
  { name: 'partial_below_display', where: `relation_class = 'partial_overlap' and containment < 0.7` },
  { name: 'cross_tradition_shown', where: `scope = 'cross_tradition' and (relation_class = 'same_wording' or (relation_class = 'same_report_variant_wording' and jaccard >= 0.4) or (relation_class = 'partial_overlap' and containment >= 0.7))` },
];

async function main() {
  const prompt = promptInfo(path.join(REPOSITORY_ROOT, 'reviews', 'ai', 'prompts', `${SPECIALIST}.md`));
  const result = await withProductionReadOnly(async (sql) => {
    const version = await sql`select id from dataset_versions where is_current`;
    const strata = new Map<string, { a: string; b: string; stratum: string; view: string }>();
    const add = (a: string, b: string, stratum: string, view: string) => {
      const key = claimKey.correspondence(a, b);
      if (!strata.has(key)) strata.set(key, { a, b, stratum, view });
    };
    for (const gold of GOLD) add(gold.a, gold.b, 'gold', 'recorded reading');
    add(WORKED_EXAMPLE.a, WORKED_EXAMPLE.b, 'worked_example', 'owner brief example');
    for (const stratum of STRATA) {
      const rows = await sql.unsafe(
        `select hadith_id_a, hadith_id_b, relation_class::text, jaccard, containment, scope::text
         from report_correspondence_candidates where retired_at is null and ${stratum.where}
         order by sha256(convert_to($1 || id, 'UTF8')) limit $2`,
        [SEED, PER_STRATUM],
      );
      for (const row of rows) {
        add(row.hadith_id_a, row.hadith_id_b, stratum.name, `class=${row.relation_class}; jaccard=${Number(row.jaccard).toFixed(2)}; containment=${Number(row.containment).toFixed(2)}; scope=${row.scope}`);
      }
    }
    const ids = [...new Set([...strata.values()].flatMap((pair) => [pair.a, pair.b]))];
    const reports = await sql`
      select h.id, h.text_ar, h.arabic_sha256, h.hadith_no, col.name as work
      from hadiths h join collections col on col.id = h.collection_id where h.id = any(${ids})`;
    return { version: version[0]?.id as string | undefined, strata, reports };
  });

  const reportById = new Map(result.reports.map((row) => [row.id as string, row]));
  const built: { item: PacketItemBody; claim: Omit<PacketManifestItem, 'item_id' | 'claim_id'> }[] = [];
  for (const [key, pair] of neutralOrder([...result.strata.entries()], ([entryKey]) => entryKey, SEED)) {
    const first = reportById.get(pair.a);
    const second = reportById.get(pair.b);
    if (!first || !second) {
      console.warn(`skipped ${key}: a report is not loaded`);
      continue;
    }
    const [textA, textB] = neutralOrder([first, second], (row) => row.id as string, `${SEED}:${key}`);
    const gold = GOLD.find((row) => claimKey.correspondence(row.a, row.b) === key);
    built.push({
      item: {
        text_a: { locator: `${textA.work}, no. ${textA.hadith_no}`, text_sha256: textA.arabic_sha256 },
        text_b: { locator: `${textB.work}, no. ${textB.hadith_no}`, text_sha256: textB.arabic_sha256 },
        passages: [
          { id: 'A', text: textA.text_ar as string },
          { id: 'B', text: textB.text_ar as string },
        ],
      },
      claim: {
        claim_kind: 'correspondence',
        claim_key: key,
        content_sha256: claimContentSha256(key, [first.id < second.id ? first.arabic_sha256 : second.arabic_sha256, first.id < second.id ? second.arabic_sha256 : first.arabic_sha256]),
        stratum: pair.stratum,
        pipeline_view: `${pair.view}; A=${textA.id}; B=${textB.id}`,
        ...(gold ? { known_answer: { outcome: gold.outcome, reading: gold.reading, source: gold.source } } : {}),
      },
    });
  }

  const packets: BuiltPacket[] = chunk(built, ITEMS_PER_PACKET).map((group) => ({
    items: group.map((entry, index) => ({ item_id: `I${index + 1}`, claim_ids: [`I${index + 1}`], ...entry.item })),
    manifest: group.map((entry, index) => ({ item_id: `I${index + 1}`, claim_id: `I${index + 1}`, ...entry.claim })),
  }));
  const written = writeBatch({
    specialistId: SPECIALIST,
    promptVersion: prompt.version,
    batch: BATCH,
    packets,
    glossary: glossaryExcerpt(['matn', 'isnad', 'report-correspondence', 'shared-formula-only', 'tahwil']),
    batchInfo: {
      specialist_id: SPECIALIST,
      prompt_version: prompt.version,
      prompt_sha256: prompt.sha256,
      batch: BATCH,
      seed: SEED,
      drawn_from: { database: 'production (SELECT only, READ ONLY transaction)', dataset_version_id: result.version ?? null },
      sampling: `per stratum, the first ${PER_STRATUM} live candidates by sha256(seed || candidate id); gold and worked-example pairs always included`,
      strata: Object.fromEntries(STRATA.map((stratum) => [stratum.name, stratum.where])),
      items: built.length,
      code_sha256: sha256Hex(readFileSync(__filename, 'utf8')),
    },
  });
  console.log(`wrote ${written.length} packets, ${built.length} items:\n${written.join('\n')}`);
}

main().catch((error: unknown) => {
  console.error(error instanceof Error ? error.message : error);
  process.exit(1);
});
