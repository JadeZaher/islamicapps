/**
 * External identity, Latin names and English flows against real rows of projection 2026.11.21.4
 * (fixtures/external-identity.json, cut by datasets/hadith-data/pg_export/slice_identity_fixture.py), loaded the way the
 * loader writes them into a private schema of the development database. The last flow drives the routes over HTTP
 * against `next start` when a build exists. See src/db/AGENTS.md §External identity.
 * Run: npx tsx --conditions=react-server src/db/queries/__tests__/identity-flows.test.ts
 */
import assert from 'node:assert/strict';
import { spawn, spawnSync, type ChildProcess } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import type { Sql } from 'postgres';
import { FIXTURE_VERSION_ID, prepareEmptySchema } from './fixture-database';
import { flow, runFlows } from './harness';
import { getReportFamily } from '../correspondence';
import { getVisibleHadith } from '../hadith';
import { groupCandidates } from '../identity-groups';
import { getChainGraph } from '../isnad';
import { getNarratorNetwork } from '../narrator';
import { getExternalLinkCandidates, getNarratorAppearances, getNarratorSourceRecord } from '../narrator-sources';
import { PUBLIC_VISIBILITY } from '../visibility';
import type { ChainGraph, ChainNode } from '../contracts';

const ROOT = path.resolve(__dirname, '../../../..');
const PORT = Number(process.env.IDENTITY_ROUTE_PORT || 3919);
const ABU_DAWUD = 'hadith:k6:19122';
const MAANI = 'hadith:thaqalayn:06c871a7dec1feb72290ba14'; // Ma'ani al-Akhbar: ... عن أبا عبد الله
const MAANI_LONG = 'hadith:thaqalayn:77fead5f962be2476f87fea5'; // the owner's example (أحمد بن محمد بن الهيثم العجلي)
const KAFI = 'hadith:thaqalayn:002a373b1a4f1f07e1668ef7';
const BUKHARI_TWO_SOURCES = 'hadith:k6:10'; // آدم بن أبي إياس: K6 index and hadith-kg name one man
const MUSLIM_AUTOMATIC = 'hadith:k6:10845'; // ليث: Riwayat's automatic link beside the K6 identity
const LABEL_REPORT = 'hadith:k6:10044'; // يحيى بن أيوب: a Riwayat id held by several records
const SUNNI_KUNYA = 'hadith:k6:22393'; // a bare أبي عبد الله in a Sunni chain
const IBADI = 'hadith:openiti:ibadi:rabi_0003|3|V01P006';
const ZAYDI = 'hadith:openiti:zaydi:zayd_0001|1|V01P059';
const SADIQ = 'narrator:imam:6';
const RIWAYAT_ANNOTATED = 'narrator:riwayat:N0000441'; // شعبة from hadith-kg's annotation, confirmed by the text
const RIWAYAT_LABEL = 'narrator:riwayat:N0001038';
const LEXICON_ADAM = 'narrator:rawi:20404';

type Row = Record<string, string | null>;
interface IdentityFixture {
  generated_from: { projection_content_sha256: string; projection_version: string };
  reports: string[];
  [table: string]: unknown;
}

/** Load order (foreign keys) and the jsonb columns the CSV carries as text. */
const TABLES = [
  'traditions', 'sources', 'collections', 'books', 'chapters', 'hadiths', 'translations', 'narrators',
  'narrator_source_profiles', 'narrator_external_ids', 'narrator_link_candidates', 'chains', 'chain_mentions',
  'chain_mention_candidates', 'report_correspondence_candidates', 'report_correspondence_cluster_members',
];
const JSON_COLUMNS: Record<string, string[]> = { narrator_source_profiles: ['assertions'], narrator_link_candidates: ['evidence'] };

let sql: Sql;
let url: string;
let close: () => Promise<void>;
let data: IdentityFixture;

/** Inserts the projection rows as the loader merges them: every column from the CSV, typed by the live table. */
async function loadFixture(): Promise<void> {
  data = JSON.parse(readFileSync(path.join(__dirname, 'fixtures/external-identity.json'), 'utf8')) as IdentityFixture;
  await sql`insert into dataset_versions ${sql({
    id: FIXTURE_VERSION_ID, source_bundle_sha256: 'fixture', input_dataset_sha256: 'fixture', rawis_sha256: 'fixture',
    legacy_master_sha256: 'fixture', extractor_version: 'fixture', extractor_sha256: 'fixture', bundle_version: '2026-11-21',
    bundle_schema_version: 1, source_release_state: 'test_fixture', release_class: 'release', load_purpose: 'identity flow tests',
    load_status: 'complete', is_current: true, attribution_disclaimer: 'Test fixture.', loaded_by: 'system:identity-fixture',
  })}`;
  for (const table of TABLES) {
    const rows = (data[table] as Row[]).map((row) => {
      const typed: Record<string, unknown> = { ...row, first_seen_dataset_version_id: FIXTURE_VERSION_ID, changed_in_dataset_version_id: FIXTURE_VERSION_ID };
      for (const column of JSON_COLUMNS[table] ?? []) typed[column] = JSON.parse(row[column]!);
      return typed;
    });
    if (rows.length === 0) continue;
    const columns = Object.keys(rows[0]);
    await sql.unsafe(
      `insert into ${table} (${columns.map((column) => `"${column}"`).join(', ')})
       select ${columns.map((column) => `"${column}"`).join(', ')} from json_populate_recordset(null::${table}, $1::json)`,
      [rows as never],
    );
  }
  await sql`update narrators set name_en_folded = lower(unaccent(name_en))`;
  // Every work cleared with the policy production records (npm run db:record-rights).
  await sql`insert into collection_rights (collection_id, rights_status, english_policy, created_by, updated_by)
            select id, 'cleared', 'source_provided_and_machine_allowed', 'system:identity-fixture', 'system:identity-fixture' from collections`;
  await sql`select refresh_publication_facets(array(select id from hadiths))`;
  await sql`refresh materialized view narrator_transmissions`;
}

function node(graph: ChainGraph, surface: string, branch = 0): ChainNode {
  const found = graph.nodes.find((item) => item.surface_ar === surface && item.branch === branch);
  assert.ok(found, `no "${surface}" in branch ${branch} of ${graph.hadith_id}`);
  return found;
}

flow('Imami chain: every name carries a Latin form with its basis, and the Imam kunya stands as al-Sadiq', async () => {
  const graph = await getChainGraph(MAANI);
  assert.equal(graph.tradition, 'Imami');
  const latin = graph.nodes.map((item) => [item.surface_ar, item.name_latin, item.name_latin_basis]);
  assert.deepEqual(latin, [
    ['الحسين بن إبراهيم بن أحمد بن هشام المكتب', null, null], // المكتب has two readings: Arabic alone, never guessed
    ['علي بن إبراهيم', 'Ali ibn Ibrahim', 'provider_english'],
    ['أبيه', 'father', 'provider_english'],
    ['محمد بن أبي عمير', 'Muhammad ibn Abi Umayr', 'provider_english'],
    ['إبراهيم بن زياد الكرخي', 'Ibrahim bin Ziyad Al-Karkhi', 'provider_english'],
    ['أبا عبد الله', 'Jaʿfar ibn Muhammad al-Sadiq', 'identity_name'],
  ]);
  const imam = node(graph, 'أبا عبد الله');
  assert.equal(imam.is_link, true);
  assert.equal(imam.narrator_id, SADIQ);
  assert.equal(imam.standing_basis, 'imam_kunya_convention');
  assert.deepEqual(imam.candidates.map((candidate) => [candidate.basis, candidate.narrator_id, candidate.tier_basis]), [
    ['imam_kunya_convention', SADIQ, true],
  ]);
  const unidentified = node(graph, 'الحسين بن إبراهيم بن أحمد بن هشام المكتب');
  assert.equal(unidentified.candidates.length, 0);
  assert.equal(unidentified.identity, 'unidentified');
});

flow("the owner's example chain reads in Latin, and a shifted provider alignment is refused", async () => {
  const graph = await getChainGraph(MAANI_LONG);
  assert.equal(node(graph, 'أحمد بن محمد بن الهيثم العجلي').name_latin, 'Ahmad ibn Muhammad al-Haysam al-Ajali');
  // Thaqalayn's English for this key is the next narrator's name ("Tamim ibn Buhlool") in every pairing: refused.
  const bakr = node(graph, 'بكر بن عبد الله بن حبيب');
  assert.deepEqual([bakr.name_latin, bakr.name_latin_basis], ['Bakr ibn ʿAbd Allah ibn Habib', 'transliteration_table']);
  assert.equal(node(graph, 'خير الجعافر جعفر بن محمد').name_latin, null);
});

flow('an Imam kunya resolves only in Imami chains: a bare أبي عبد الله in a Sunni chain stays a source claim', async () => {
  const graph = await getChainGraph(SUNNI_KUNYA);
  const kunya = node(graph, 'أبي عبد الله');
  assert.equal(kunya.is_link, false);
  assert.ok(kunya.candidates.every((candidate) => !candidate.basis.startsWith('imam_kunya')));
  assert.deepEqual(kunya.candidates.map((candidate) => candidate.basis), ['source_riwayat']);
  const stored = await sql`select count(*)::int as n from chain_mention_candidates c join hadiths h on h.id = c.hadith_id
                           where c.basis::text like 'imam_kunya_%' and h.tradition_id <> 'tradition:imami'`;
  assert.equal(stored[0].n, 0);
});

flow('two independent sources agree: K6 and hadith-kg name one man, machine-reviewed under their own label', async () => {
  const graph = await getChainGraph(BUKHARI_TWO_SOURCES);
  const adam = node(graph, 'آدم بن أبي إياس');
  assert.equal(adam.narrator_id, LEXICON_ADAM);
  assert.equal(adam.standing_basis, 'two_sources_agree');
  assert.equal(adam.identity, 'agreed');
  const groups = groupCandidates(adam.candidates);
  const standing = groups.find((group) => group.records.some((record) => record.narratorId === LEXICON_ADAM))!;
  assert.deepEqual(standing.records.map((record) => record.narratorId).sort(), ['narrator:hadith-kg:2', LEXICON_ADAM, 'narrator:riwayat:N0001098'],
    'the hadith-kg and Riwayat records are the same person through their link candidates, not a disagreement');
  assert.ok(adam.candidates.every((candidate) => !(candidate.basis === 'source_index' && candidate.tier_basis)), 'an unconfirmed index alone is not a tier basis');
});

flow("Riwayat's automatic link is shown, labelled, and never carries the tier", async () => {
  const graph = await getChainGraph(MUSLIM_AUTOMATIC);
  const layth = node(graph, 'ليث');
  const automatic = layth.candidates.find((candidate) => candidate.origin === 'riwayat_automatic_linking');
  assert.ok(automatic, 'the automatic link is shown');
  assert.equal(automatic.basis, 'source_riwayat_confirmed_by_text');
  assert.equal(automatic.tier_basis, false);
  assert.equal(layth.standing_basis, 'source_index_confirmed_by_text');
  assert.equal(layth.narrator_id, 'narrator:rawi:20023');
  const resting = await sql`select count(*)::int as n from chain_mentions m where m.extraction_method = 'source_riwayat_confirmed_by_text'
    and not exists (select 1 from chain_mention_candidates c where c.mention_id = m.id and c.narrator_id = m.narrator_id
                    and c.source_assertion_origin <> 'riwayat_automatic_linking')`;
  assert.equal(resting[0].n, 0);
});

flow('a label-like Riwayat record is a candidate only and its page says it names a label', async () => {
  const graph = await getChainGraph(LABEL_REPORT);
  const yahya = node(graph, 'يحيى بن أيوب');
  const label = yahya.candidates.find((candidate) => candidate.narrator_id === RIWAYAT_LABEL)!;
  assert.equal(label.label_reason, 'name_held_by_several_ids');
  assert.equal(label.tier_basis, false);
  assert.notEqual(yahya.narrator_id, RIWAYAT_LABEL);
  const record = await getNarratorSourceRecord(RIWAYAT_LABEL);
  assert.equal(record?.label_reason, 'name_held_by_several_ids');
  assert.equal(record?.authority, 'riwayat');
});

flow('an external-authority narrator page: its record, credit, chains (paged) and teachers and students', async () => {
  const record = await getNarratorSourceRecord(RIWAYAT_ANNOTATED);
  assert.ok(record);
  assert.equal(record.authority, 'riwayat');
  assert.equal(record.source_key, 'N0000441');
  assert.equal(record.label_reason, null);
  assert.ok(record.assertions.every(([key]) => !['rank', 'madhhab', 'has_tadlis'].includes(key)), 'no verdict-like field is shown');
  const appearances = await getNarratorAppearances(RIWAYAT_ANNOTATED, { page: 1 });
  assert.deepEqual(appearances.items.map((item) => [item.hadith_id, item.branch, item.position, item.standing_basis]), [
    [BUKHARI_TWO_SOURCES, 0, 1, 'source_riwayat_confirmed_by_text'],
    [BUKHARI_TWO_SOURCES, 1, 1, 'source_riwayat_confirmed_by_text'],
  ]);
  const imamChains = await getNarratorAppearances(SADIQ, { page: 1, pageSize: 1 });
  assert.ok(imamChains.total >= 2 && imamChains.items.length === 1, 'paged');
  const network = await getNarratorNetwork(RIWAYAT_ANNOTATED);
  assert.ok(network.teachers.length + network.students.length > 0, 'machine-reviewed neighbours appear in the network');
  assert.equal(await getNarratorSourceRecord(LEXICON_ADAM), null, 'a lexicon narrator has no external record');
  assert.deepEqual((await getExternalLinkCandidates(LEXICON_ADAM)).map((link) => link.narrator_id), ['narrator:hadith-kg:2', 'narrator:riwayat:N0001098']);
});

flow('English renders with its label where public, and is absent (no row) for Ibadi and Zaydi', async () => {
  const abuDawud = await getVisibleHadith(ABU_DAWUD, PUBLIC_VISIBILITY);
  assert.equal(abuDawud?.english_attribution?.label, 'Source-provided English, not reviewed here');
  assert.match(abuDawud?.text_en ?? '', /cursed the woman who adds some false hair/);
  const family = await getReportFamily(ABU_DAWUD);
  assert.ok(family);
  for (const telling of family.tellings) {
    assert.ok(telling.english, `${telling.hadith_id} has public English in the family view`);
    assert.equal(telling.english.attribution.label, 'Source-provided English, not reviewed here');
    assert.ok(telling.english.attribution.reference?.detail?.startsWith('Translation:'));
  }
  assert.equal((await getVisibleHadith(IBADI, PUBLIC_VISIBILITY))?.english_attribution, null);
  assert.equal((await getVisibleHadith(ZAYDI, PUBLIC_VISIBILITY))?.english_attribution, null);
});

let server: ChildProcess | undefined;
flow('routes: chains, reports and narrator pages render names, links, English and the no-English line', async () => {
  if (!existsSync(path.join(ROOT, '.next/BUILD_ID'))) throw new Error('Run `npx next build` first: this flow drives the built routes.');
  server = spawn(process.execPath, [path.join(ROOT, 'node_modules/next/dist/bin/next'), 'start', '-p', String(PORT), '-H', '127.0.0.1'], {
    cwd: ROOT,
    env: { ...process.env, DATABASE_URL: url, SITE_URL: `http://127.0.0.1:${PORT}`, NODE_ENV: 'production', AUTH_ENABLED: '' },
    stdio: 'ignore',
  });
  const base = `http://127.0.0.1:${PORT}`;
  for (let attempt = 0; attempt < 60; attempt++) {
    try {
      await fetch(`${base}/api/health`);
      break;
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 500));
    }
  }
  const page = async (route: string) => {
    const response = await fetch(`${base}${route}`);
    assert.equal(response.status, 200, route);
    return response.text();
  };
  const chains = await page('/hadith/k6/19122/chains');
  assert.match(chains, /data-name-latin="provider_english"/, 'Imami names carry the provider English');
  assert.match(chains, /href="\/narrator\/narrator%3Aimam%3A6"/, 'the Imam kunya links to the Imam register page');
  assert.match(chains, /machine-reviewed: the Imam(&#x27;|')s kunya in Imami usage/);
  assert.match(chains, /Source-provided English, not reviewed here/);
  assert.match(chains, /data-source-ref="THQ"/);
  assert.match(chains, /data-source-ref="RWY"/, 'Riwayat claims are credited');
  const report = await page('/hadith/k6/19122');
  assert.match(report, /cursed the woman who adds some false hair/);
  assert.match(report, /data-english-label/);
  assert.match(await page('/hadith/k6/10'), /machine-reviewed: two sources agree/);
  const ibadi = await page('/hadith/openiti/ibadi/rabi_0003%7C3%7CV01P006');
  assert.match(ibadi, /No English available yet/);
  assert.match(await page('/hadith/openiti/zaydi/zayd_0001%7C1%7CV01P059'), /No English available yet/);
  await page('/hadith/thaqalayn/002a373b1a4f1f07e1668ef7/chains');
  const riwayat = await page(`/narrator/${encodeURIComponent(RIWAYAT_ANNOTATED)}`);
  assert.match(riwayat, /Record in the Riwayat corpus/);
  assert.match(riwayat, /Named in chains/);
  assert.match(riwayat, /data-source-ref="RWY"/);
  assert.match(await page(`/narrator/${encodeURIComponent(RIWAYAT_LABEL)}`), /names a label as written in chains, not an established person/);
  assert.match(await page(`/narrator/${encodeURIComponent(LEXICON_ADAM)}`), /Records in other sources/);
});

function stopServer(): void {
  if (!server?.pid) return;
  if (process.platform === 'win32') spawnSync('taskkill', ['/pid', String(server.pid), '/T', '/F'], { stdio: 'ignore' });
  else server.kill('SIGTERM');
}

async function main() {
  ({ sql, url, close } = await prepareEmptySchema(process.env.QUERY_FIXTURE_SCHEMA || 'identity_fixture'));
  await loadFixture();
  await runFlows(async () => {
    stopServer();
    await close();
  });
}

main().catch(async (error) => {
  console.error(error);
  stopServer();
  await close?.();
  process.exitCode = 1;
});
