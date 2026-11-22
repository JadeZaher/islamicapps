/**
 * Chain structure gate flows against real rows of projection 2026.11.22.9 (fixtures/structure.json, cut by
 * datasets/hadith-data/pg_export/slice_structure_fixture.py), loaded into a private schema of the development database
 * built from the migration stream. See src/db/AGENTS.md §Chain structure gate.
 * Run: npx tsx --conditions=react-server src/db/queries/__tests__/structure-flows.test.ts
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import type { Sql } from 'postgres';
import { CHAIN_STRUCTURE_REASON_LABEL, structureNote } from '../../../app/hadith/[id]/components/chain-structure';
import { FIXTURE_VERSION_ID, prepareEmptySchema } from './fixture-database';
import { flow, runFlows } from './harness';
import { getChainGraph } from '../isnad';
import { getNarratorNetwork } from '../narrator';

type Row = Record<string, string | null>;
interface StructureFixture {
  reports: string[];
  chosen: { uncertain_report: string; checked_report: string; student: string; uncertain_teacher: string; checked_teacher: string };
  [table: string]: unknown;
}

const TABLES = [
  'traditions', 'sources', 'collections', 'books', 'chapters', 'hadiths', 'narrators', 'narrator_lexicon_profiles',
  'chains', 'chain_mentions', 'chain_mention_candidates',
];
const JSON_COLUMNS: Record<string, string[]> = { narrator_lexicon_profiles: ['source_fields'] };

let sql: Sql;
let close: () => Promise<void>;
let data: StructureFixture;

/** Inserts the projection rows as the loader merges them, then refreshes facets and the network as the loader does. */
async function loadFixture(): Promise<void> {
  data = JSON.parse(readFileSync(path.join(__dirname, 'fixtures/structure.json'), 'utf8')) as StructureFixture;
  await sql`insert into dataset_versions ${sql({
    id: FIXTURE_VERSION_ID, source_bundle_sha256: 'fixture', input_dataset_sha256: 'fixture', rawis_sha256: 'fixture',
    legacy_master_sha256: 'fixture', extractor_version: 'fixture', extractor_sha256: 'fixture', bundle_version: '2026-11-22',
    bundle_schema_version: 1, source_release_state: 'test_fixture', release_class: 'release', load_purpose: 'structure gate flow tests',
    load_status: 'complete', is_current: true, attribution_disclaimer: 'Test fixture.', loaded_by: 'system:structure-fixture',
  })}`;
  for (const table of TABLES) {
    const rows = (data[table] as Row[]).map((row) => {
      const typed: Record<string, unknown> = { ...row, first_seen_dataset_version_id: FIXTURE_VERSION_ID, changed_in_dataset_version_id: FIXTURE_VERSION_ID };
      for (const column of JSON_COLUMNS[table] ?? []) typed[column] = row[column] === null ? null : JSON.parse(row[column]!);
      if (table === 'chains') typed.structure_reasons = row.structure_reasons ? row.structure_reasons.replace(/^\{|\}$/g, '').split(',') : null;
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
            select id, 'cleared', 'source_provided_and_machine_allowed', 'system:structure-fixture', 'system:structure-fixture' from collections`;
  await sql`select refresh_publication_facets(array(select id from hadiths))`;
  await sql`refresh materialized view narrator_transmissions`;
}

flow("a pair standing only in an uncertain chain is not a teacher; a pair in a checked chain is", async () => {
  const { student, uncertain_teacher: uncertainTeacher, checked_teacher: checkedTeacher } = data.chosen;
  const network = await getNarratorNetwork(student);
  const teachers = network.teachers.map((peer) => peer.id);
  assert.ok(teachers.includes(checkedTeacher), 'the teacher from the checked chain is listed');
  assert.ok(!teachers.includes(uncertainTeacher), 'the teacher read only from the uncertain chain is not listed');
  const teacherSide = await getNarratorNetwork(uncertainTeacher);
  assert.ok(!teacherSide.students.some((peer) => peer.id === student), 'nor is the student on the teacher\'s page');
});

flow('the uncertain chain is shown as stored, with its status, reasons and the plain line', async () => {
  const graph = await getChainGraph(data.chosen.uncertain_report);
  const stored = (data.chain_mentions as Row[]).filter((row) => row.hadith_id === data.chosen.uncertain_report);
  assert.equal(graph.nodes.length, stored.length, 'every stored name is still shown');
  const head = graph.nodes.find((node) => node.position === 0 && node.chain_structure_status === 'uncertain');
  assert.ok(head, 'a chain of the report is uncertain');
  assert.ok((head.chain_structure_reasons ?? []).length > 0, 'with its reasons');
  for (const code of head.chain_structure_reasons ?? []) assert.ok(CHAIN_STRUCTURE_REASON_LABEL[code], `no plain wording for ${code}`);
  const note = structureNote(head) ?? '';
  assert.match(note, /has not been checked; it is not used for teacher and student lists/);
  assert.doesNotMatch(note, /verified/i);

  const checked = await getChainGraph(data.chosen.checked_report);
  assert.ok(checked.nodes.every((node) => node.chain_structure_status === 'checked_by_rule'));
  assert.equal(structureNote(checked.nodes[0]), null, 'a checked chain carries no line');
});

async function main(): Promise<void> {
  ({ sql, close } = await prepareEmptySchema('structure_fixture'));
  await loadFixture();
  await runFlows(async () => {
    await sql.unsafe('drop schema if exists structure_fixture cascade');
    await close();
  });
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
