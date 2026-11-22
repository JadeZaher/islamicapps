/**
 * Chain chronology guard flows against real rows of projection 2026.11.21.6 (fixtures/chronology.json, cut by
 * datasets/hadith-data/pg_export/slice_chronology_fixture.py), loaded into a private schema of the development database
 * built from the migration stream. See src/db/AGENTS.md §Chain chronology guard.
 * Run: npx tsx --conditions=react-server src/db/queries/__tests__/chronology-flows.test.ts
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import type { Sql } from 'postgres';
import { FIXTURE_VERSION_ID, prepareEmptySchema } from './fixture-database';
import { flow, runFlows } from './harness';
import { getChainGraph } from '../isnad';
import { getNarratorNetwork } from '../narrator';
import { getNarratorAppearances } from '../narrator-sources';

const UMAR = 'narrator:rawi:3';
const AWZAI = 'narrator:rawi:20024';
const LATER_UMAR_REPORT = 'hadith:k6:28147'; // «حدثنا محمود بن خالد حدثنا عمر عن الأوزاعي»
const TAHWIL_REPORT = 'hadith:k6:28195'; // two routes in one chain; al-Awzaʿi at positions 2 and 6

type Row = Record<string, string | null>;
interface ChronologyFixture {
  reports: string[];
  [table: string]: unknown;
}

const TABLES = [
  'traditions', 'sources', 'collections', 'books', 'chapters', 'hadiths', 'narrators', 'narrator_lexicon_profiles',
  'narrator_teachers', 'chains', 'chain_mentions', 'chain_mention_candidates',
];
const JSON_COLUMNS: Record<string, string[]> = { narrator_lexicon_profiles: ['source_fields'] };

let sql: Sql;
let close: () => Promise<void>;
let data: ChronologyFixture;

/** Inserts the projection rows as the loader merges them, then refreshes facets and the network as the loader does. */
async function loadFixture(): Promise<void> {
  data = JSON.parse(readFileSync(path.join(__dirname, 'fixtures/chronology.json'), 'utf8')) as ChronologyFixture;
  await sql`insert into dataset_versions ${sql({
    id: FIXTURE_VERSION_ID, source_bundle_sha256: 'fixture', input_dataset_sha256: 'fixture', rawis_sha256: 'fixture',
    legacy_master_sha256: 'fixture', extractor_version: 'fixture', extractor_sha256: 'fixture', bundle_version: '2026-11-21',
    bundle_schema_version: 1, source_release_state: 'test_fixture', release_class: 'release', load_purpose: 'chronology flow tests',
    load_status: 'complete', is_current: true, attribution_disclaimer: 'Test fixture.', loaded_by: 'system:chronology-fixture',
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
            select id, 'cleared', 'source_provided_and_machine_allowed', 'system:chronology-fixture', 'system:chronology-fixture' from collections`;
  await sql`select refresh_publication_facets(array(select id from hadiths))`;
  await sql`refresh materialized view narrator_transmissions`;
}

flow('a later ʿUmar read as the Companion: no identity, the candidate stays with its reason, in the chain and on his page', async () => {
  const graph = await getChainGraph(LATER_UMAR_REPORT);
  const umar = graph.nodes.find((node) => node.surface_ar === 'عمر');
  assert.ok(umar, 'the chain names عمر');
  assert.equal(umar.is_link, false);
  assert.equal(umar.narrator_id, null);
  assert.ok(umar.candidates.some((candidate) => candidate.narrator_id === UMAR && candidate.basis === 'source_index_confirmed_by_text'));
  assert.match(umar.identity_withheld_reason ?? '', /^chronology: the person named here died in 23 AH, before the next transmitter was born/);
  assert.notEqual(umar.name_latin_basis, 'identity_name', 'a withheld identity never names the mention');

  const appearances = await getNarratorAppearances(UMAR);
  const here = appearances.items.find((item) => item.hadith_id === LATER_UMAR_REPORT);
  assert.ok(here, "the report is still listed on ʿUmar's page as a candidate position");
  assert.equal(here.standing_basis, null);
  assert.match(here.identity_withheld_reason ?? '', /died in 23 AH/);
});

flow("ʿUmar's teachers no longer include al-Awzaʿi (both reports that named him)", async () => {
  const network = await getNarratorNetwork(UMAR);
  assert.deepEqual(network.teachers.filter((peer) => peer.id === AWZAI), []);
  const stored = await sql`select count(*)::int as n from narrator_transmissions where student_id = ${UMAR} and teacher_id = ${AWZAI}`;
  assert.equal(stored[0].n, 0, 'neither report forms the pair once the identity is withheld and the seam is guarded');
});

flow('a flattened tahwil forms no pair between the two occurrences of al-Awzaʿi', async () => {
  const chain = (await sql<{ position: number; narrator_id: string | null }[]>`
    select position, narrator_id from chain_mentions where hadith_id = ${TAHWIL_REPORT} and chain_id like '%:0000' order by position`);
  const occurrences = chain.filter((row) => row.narrator_id === AWZAI).map((row) => row.position);
  assert.ok(occurrences.length >= 2, 'al-Awzaʿi stands twice in the flattened chain');
  const [first, last] = [occurrences[0], occurrences[occurrences.length - 1]];
  const inside = chain.filter((row) => row.position >= first && row.position < last && row.narrator_id)
    .map((row) => [row.narrator_id, chain.find((next) => next.position === row.position + 1)?.narrator_id])
    .filter((pair): pair is [string, string] => Boolean(pair[1]));
  assert.ok(inside.length > 0, 'the window holds identified neighbours');
  for (const [student, teacher] of inside) {
    const formed = await sql`select 1 from narrator_transmissions where student_id = ${student} and teacher_id = ${teacher}`;
    assert.equal(formed.length, 0, `${student} <- ${teacher} crosses the seam`);
  }
});

flow('an irsal pair stays in the chain but is never listed as teacher and student; undated pairs stay', async () => {
  const [impossible] = await sql<{ student_id: string; teacher_id: string }[]>`
    select student_id, teacher_id from narrator_transmissions where temporal_plausibility = 'impossible' order by 1, 2 limit 1`;
  assert.ok(impossible, 'the fixture keeps one standing pair whose student was born after the teacher died');
  const network = await getNarratorNetwork(impossible.student_id);
  assert.ok(!network.teachers.some((peer) => peer.id === impossible.teacher_id), 'impossible pair listed as a teacher');
  const [{ shown }] = await sql<{ shown: number }[]>`
    select count(*)::int as shown from narrator_transmissions where student_id = ${impossible.student_id} and temporal_plausibility <> 'impossible'`;
  assert.equal(network.teacher_total, shown, 'the total counts only possible pairs');
  const [{ undated }] = await sql<{ undated: number }[]>`
    select count(*)::int as undated from narrator_transmissions where temporal_plausibility = 'unknown'`;
  assert.ok(undated > 0, 'pairs without years are kept');
});

async function main(): Promise<void> {
  ({ sql, close } = await prepareEmptySchema('chronology_fixture'));
  await loadFixture();
  await runFlows(async () => {
    await sql.unsafe('drop schema if exists chronology_fixture cascade');
    await close();
  });
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
