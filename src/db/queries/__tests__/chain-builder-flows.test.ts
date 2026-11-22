/**
 * Chain builder flows against real rows of projection 2026.11.22.x (fixtures/chain-builder.json, cut by
 * datasets/hadith-data/pg_export/slice_chain_builder_fixture.py), loaded into a private schema of the development database
 * built from the migration stream. See src/db/AGENTS.md §Chain builder.
 * Run: npx tsx --conditions=react-server src/db/queries/__tests__/chain-builder-flows.test.ts
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import type { Sql } from 'postgres';
import { FIXTURE_VERSION_ID, prepareEmptySchema } from './fixture-database';
import { flow, runFlows } from './harness';
import { getChainGraph } from '../isnad';
import { getNarratorNetwork } from '../narrator';

const RABI_PARENT = 'hadith:openiti:ibadi:rabi_0331|331|V01P084';
const RABI_CONTINUATION = 'hadith:openiti:ibadi:rabi_0332|332|V01P084'; // «ومن طريقه»: Abu ʿUbayda, Jabir, Ibn ʿAbbas
const RIDA_OPENING = 'hadith:openiti:imami:rida_0001|1|V01P439';
const RIDA_CONTINUATION = 'hadith:openiti:imami:rida_0003|3|V01P441'; // «وباسناده المذكور قال: قال رسول الله»
const ZAYD = 'hadith:openiti:zaydi:zayd_0170|170|V01P167'; // «زيد بن علي عن أبيه عن جده عن علي»
const BALAGH = 'hadith:openiti:ibadi:rabi_0425|425|V01P114';
const JABIR = 'narrator:riwayat:N0001547';

type Row = Record<string, string | null>;
const TABLES = [
  'traditions', 'sources', 'collections', 'books', 'chapters', 'hadiths', 'narrators', 'narrator_source_profiles',
  'narrator_lexicon_profiles', 'narrator_teachers', 'chains', 'chain_mentions', 'chain_mention_candidates',
];
const JSON_COLUMNS: Record<string, string[]> = {
  hadiths: ['source_notes'], narrator_lexicon_profiles: ['source_fields'], narrator_source_profiles: ['assertions'],
};

let sql: Sql;
let close: () => Promise<void>;

/** Inserts the projection rows as the loader merges them, then refreshes facets and the network as the loader does. */
async function loadFixture(): Promise<void> {
  const data = JSON.parse(readFileSync(path.join(__dirname, 'fixtures/chain-builder.json'), 'utf8')) as Record<string, unknown>;
  await sql`insert into dataset_versions ${sql({
    id: FIXTURE_VERSION_ID, source_bundle_sha256: 'fixture', input_dataset_sha256: 'fixture', rawis_sha256: 'fixture',
    legacy_master_sha256: 'fixture', extractor_version: 'fixture', extractor_sha256: 'fixture', bundle_version: '2026-11-22',
    bundle_schema_version: 1, source_release_state: 'test_fixture', release_class: 'release', load_purpose: 'chain builder flow tests',
    load_status: 'complete', is_current: true, attribution_disclaimer: 'Test fixture.', loaded_by: 'system:chain-builder-fixture',
  })}`;
  for (const table of TABLES) {
    const rows = (data[table] as Row[]).map((row) => {
      const typed: Record<string, unknown> = { ...row, first_seen_dataset_version_id: FIXTURE_VERSION_ID, changed_in_dataset_version_id: FIXTURE_VERSION_ID };
      for (const column of JSON_COLUMNS[table] ?? []) typed[column] = row[column] === null ? null : JSON.parse(row[column]!);
      if (table === 'narrator_teachers') typed.evidence_fields = String(row.evidence_fields).replace(/^\{|\}$/g, '').split(',');
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
  await sql`insert into collection_rights (collection_id, rights_status, english_policy, created_by, updated_by)
            select id, 'cleared', 'source_provided_and_machine_allowed', 'system:chain-builder-fixture', 'system:chain-builder-fixture' from collections`;
  await sql`select refresh_publication_facets(array(select id from hadiths))`;
  await sql`refresh materialized view narrator_transmissions`;
}

flow('a continuation shows the names it repeats, marked, and they feed the teacher list', async () => {
  const graph = await getChainGraph(RABI_CONTINUATION);
  assert.deepEqual(graph.nodes.map((node) => node.surface_ar), ['أبو عبيدة', 'جابر بن زيد', 'ابن عباس']);
  assert.ok(graph.nodes.every((node) => node.inherited_from_mention_id?.startsWith(`mention:${RABI_PARENT.slice('hadith:'.length)}:`)));
  const jabir = graph.nodes.find((node) => node.surface_ar === 'جابر بن زيد');
  assert.equal(jabir?.narrator_id, JABIR, 'the inherited name keeps its written mention identity');

  const network = await getNarratorNetwork(JABIR);
  assert.ok(network.teachers.some((peer) => peer.id === graph.nodes[2].narrator_id), 'Ibn ʿAbbas is listed as a teacher of Jabir');
  const [{ hadith_count }] = await sql<{ hadith_count: number }[]>`
    select hadith_count from narrator_transmissions where student_id = ${JABIR} and teacher_id = ${graph.nodes[2].narrator_id!}`;
  assert.equal(hadith_count, 2, 'the written report and its continuation both count');
});

flow('Sahifat al-Rida: the opening report stores the Imam chain, and a continuation carries it', async () => {
  const opening = (await getChainGraph(RIDA_OPENING)).nodes.map((node) => node.surface_ar);
  assert.equal(opening[0], 'علي بن موسى الرضى');
  assert.equal(opening[opening.length - 1], 'علي بن أبي طالب');
  assert.ok(!opening.some((surface) => surface.includes('الطائي')), 'no editorial transmitter is a mention');
  const continuation = await getChainGraph(RIDA_CONTINUATION);
  assert.deepEqual(continuation.nodes.map((node) => node.surface_ar), opening);
  assert.ok(!continuation.nodes.some((node) => /باسناده|المذكور/.test(node.surface_ar)), 'the opener is never a mention');
});

flow('Musnad Zayd: «عن أبيه عن جده عن علي» reads through report No. 1 and forms the Imam pairs', async () => {
  const nodes = (await getChainGraph(ZAYD)).nodes;
  assert.deepEqual(nodes.map((node) => node.narrator_id), ['narrator:imam:zayd', 'narrator:imam:4', 'narrator:imam:3', 'narrator:imam:1']);
  assert.deepEqual(nodes.map((node) => node.surface_ar).slice(1, 3), ['أبيه', 'جده'], 'the surfaces stay as written');
  assert.ok(nodes.every((node) => node.standing_basis === 'named_in_opening_isnad'));
  const network = await getNarratorNetwork('narrator:imam:zayd');
  assert.ok(network.teachers.some((peer) => peer.id === 'narrator:imam:4'), "Zayd's father is his teacher");
});

flow('a balagh is a labelled gap: no pair forms across it', async () => {
  const nodes = (await getChainGraph(BALAGH)).nodes;
  const gap = nodes.find((node) => node.link_kind === 'anonymous');
  assert.ok(gap, 'the balagh is a mention of its own');
  assert.equal(gap.narrator_id, null, 'an unnamed transmitter never carries an identity, so no pair can form through it');
  assert.ok(nodes.some((node) => node.position > gap.position), 'the named source after the balagh is kept');
});

async function main(): Promise<void> {
  ({ sql, close } = await prepareEmptySchema('chain_builder_fixture'));
  await loadFixture();
  await runFlows(async () => {
    await sql.unsafe('drop schema if exists chain_builder_fixture cascade');
    await close();
  });
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
