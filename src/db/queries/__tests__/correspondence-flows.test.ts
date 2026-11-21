/**
 * Report-family flows against a fixture schema of real rows (fixtures/correspondence.json, cut from the loaded
 * projection by datasets/hadith-data/pg_export/slice_correspondence_fixture.py). The last flow drives the
 * /hadith/[id]/chains route over HTTP against `next start` when a build exists.
 * Run: npx tsx --conditions=react-server src/db/queries/__tests__/correspondence-flows.test.ts
 */
import assert from 'node:assert/strict';
import { spawn, spawnSync, type ChildProcess } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { prepareFixtureDatabase, FIXTURE_ACTOR, FIXTURE_VERSION_ID, type FixtureDatabase } from './fixture-database';
import { flow, rejection, runFlows } from './harness';
import { getReportFamily } from '../correspondence';
import { decideCorrespondence } from '../correspondence-decisions';
import { getReportFamilyForReview } from '../correspondence-review';
import { buildFamilyGraph, mergeKey } from '../family-graph';
import type { ReportFamily } from '../contracts';
import { reportNumber } from '../../../lib/citation/reference';

const ROOT = path.resolve(__dirname, '../../../..');
const FOCAL = 'hadith:k6:19122'; // Sunan Abi Da'ud
const NASAI = 'hadith:k6:29550';
const MAANI = 'hadith:thaqalayn:06c871a7dec1feb72290ba14'; // Ma'ani al-Akhbar (Imami)
const IBADI_LOW = 'hadith:openiti:ibadi:rabi_0975|975|V01P273'; // variant at Jaccard 0.38: below the display threshold
const ZAYDI_FIRST = 'hadith:openiti:zaydi:zayd_0001|1|V01P059'; // a corpus fixture report with no correspondence
const SHARED_NARRATOR = 'narrator:rawi:11014'; // standing identity in five chains of the family
const PORT = Number(process.env.CHAINS_ROUTE_PORT || 3918);

type Rows = Record<string, unknown>[];
interface CorrespondenceFixture {
  generated_from: { projection_content_sha256: string };
  collections: Rows;
  hadiths: Rows;
  chains: Rows;
  chain_mentions: Rows;
  chain_mention_candidates: Rows;
  narrators: Rows;
  report_correspondence_candidates: Rows;
  report_correspondence_cluster_members: Rows;
}

let fixture: FixtureDatabase;
let data: CorrespondenceFixture;
const actor = 'curator:fixture-reviewer';

/** Adds the family's real rows to the fixture schema; every work is rights-cleared, so the public read sees them. */
async function loadCorrespondenceRows(): Promise<void> {
  data = JSON.parse(readFileSync(path.join(__dirname, 'fixtures/correspondence.json'), 'utf8')) as CorrespondenceFixture;
  const { sql } = fixture;
  const pipeline = { first_seen_dataset_version_id: FIXTURE_VERSION_ID, changed_in_dataset_version_id: FIXTURE_VERSION_ID };
  const [{ top }] = await sql<{ top: number }[]>`select coalesce(max(sort_key), 0)::int as top from collections`;
  const insert = async (table: string, rows: Rows) => {
    if (rows.length) await sql`insert into ${sql(table)} ${sql(rows.map((row) => ({ ...row, ...pipeline })) as never)} on conflict do nothing`;
  };
  // Works already in the corpus fixture keep their row; new ones take sort keys after it.
  await insert('collections', data.collections.map((row, index) => ({ ...row, sort_key: top + index + 1 })));
  await sql`insert into collection_rights ${sql(
    data.collections.map((row) => ({ collection_id: row.id as string, rights_status: 'cleared', created_by: FIXTURE_ACTOR, updated_by: FIXTURE_ACTOR })),
  )} on conflict do nothing`;
  await sql`insert into sources ${sql(
    [...new Set(data.collections.map((row) => row.source_id as string))].map((id) => ({
      id, slug: id.replace('source:', ''), name: id.replace('source:', ''), release_state: 'unreviewed_local_snapshot', ...pipeline,
    })),
  )} on conflict do nothing`;
  await insert('narrators', data.narrators);
  // Browse structure (books, chapters) is not part of a family read; the fixture leaves it out.
  await insert('hadiths', data.hadiths.map((row) => ({ ...row, book_id: null, chapter_id: null })));
  await insert('chains', data.chains);
  await insert('chain_mentions', data.chain_mentions);
  await insert('chain_mention_candidates', data.chain_mention_candidates);
  await insert('report_correspondence_candidates', data.report_correspondence_candidates);
  await insert('report_correspondence_cluster_members', data.report_correspondence_cluster_members);
  await sql`select refresh_publication_facets(array(select id from hadiths))`;
}

const ids = (family: ReportFamily | null) => (family?.tellings ?? []).map((telling) => telling.hadith_id);
const arabicSha = (id: string) => data.hadiths.find((row) => row.id === id)!.arabic_sha256 as string;

flow('family: a report with tellings in two traditions returns each telling with all its chains in order', async () => {
  const family = await getReportFamily(FOCAL);
  assert.ok(family);
  assert.equal(family.tellings[0].hadith_id, FOCAL);
  assert.equal(family.tellings[0].is_focal, true);
  assert.equal(family.tellings[0].correspondence, null);
  // The seven pairs the display rule shows; the Ibadi pair below the threshold is not among them.
  assert.equal(family.correspondences_total, 7);
  assert.equal(family.capped, false);
  assert.ok(!ids(family).includes(IBADI_LOW));
  assert.deepEqual([...new Set(family.tellings.map((telling) => telling.tradition))].sort(), ['Imami', 'Sunni']);
  const maani = family.tellings.find((telling) => telling.hadith_id === MAANI)!;
  assert.equal(maani.source_work, "Ma'ani al-Akhbar");
  // Thaqalayn's stored hadith_no is the chapter: the reference takes the report's number from the provider URL.
  assert.equal(maani.numbering_citable, true);
  const urlNumber = /\/(\d+)\/?$/.exec(maani.url ?? '')?.[1];
  assert.ok(urlNumber, 'the Thaqalayn URL carries the number');
  assert.equal(reportNumber({ id: maani.hadith_id, hadithNo: maani.hadith_no, url: maani.url, volume: maani.volume, pageRef: null, bookNumber: null }), urlNumber);
  assert.equal(maani.correspondence?.confirmed, false);
  // Every chain of every telling, positions as stored, and each mention in the fixture appears exactly once.
  for (const telling of family.tellings) {
    const expected = data.chain_mentions.filter((row) => row.hadith_id === telling.hadith_id);
    assert.equal(telling.chain.nodes.length, expected.length, `${telling.hadith_id} mentions`);
    const byChain = new Map<string, number[]>();
    for (const node of telling.chain.nodes) byChain.set(node.chain_id, [...(byChain.get(node.chain_id) ?? []), node.position]);
    for (const positions of byChain.values()) assert.deepEqual(positions, positions.map((_, index) => index));
    const first = expected.find((row) => row.position === 0 && row.chain_id === telling.chain.nodes[0]?.chain_id);
    if (first) assert.equal(telling.chain.nodes[0].surface_ar, first.surface_ar);
  }
});

flow('family: a pair hidden by publication is hidden publicly but kept for a curator', async () => {
  const maaniCollection = data.hadiths.find((row) => row.id === MAANI)!.collection_id as string;
  await fixture.sql`update collection_rights set rights_status = 'pending' where collection_id = ${maaniCollection}`;
  try {
    assert.ok(!ids(await getReportFamily(FOCAL)).includes(MAANI));
    assert.ok(ids(await getReportFamilyForReview(FOCAL)).includes(MAANI));
  } finally {
    await fixture.sql`update collection_rights set rights_status = 'cleared' where collection_id = ${maaniCollection}`;
  }
});

flow('curation: a rejected pair disappears and a confirmed low-score pair appears, each with its audit row', async () => {
  const rejected = await decideCorrespondence(actor, {
    hadith_id_a: NASAI, hadith_id_b: FOCAL, seen_arabic_sha256_a: arabicSha(NASAI), seen_arabic_sha256_b: arabicSha(FOCAL), decision: 'rejected',
    reviewed_relation: 'shared_formula_only',
  });
  const confirmed = await decideCorrespondence(actor, {
    hadith_id_a: FOCAL, hadith_id_b: IBADI_LOW, seen_arabic_sha256_a: arabicSha(FOCAL), seen_arabic_sha256_b: arabicSha(IBADI_LOW), decision: 'confirmed',
  });
  const family = await getReportFamily(FOCAL);
  assert.ok(!ids(family).includes(NASAI), 'the rejected pair is gone');
  const ibadi = family!.tellings.find((telling) => telling.hadith_id === IBADI_LOW);
  assert.ok(ibadi, 'the confirmed low-score pair is shown');
  assert.equal(ibadi.correspondence?.confirmed, true);
  assert.equal(family!.tellings[1].hadith_id, IBADI_LOW, 'reviewer-confirmed tellings rank first');
  const audits = await fixture.sql<{ entity_id: string; action: string }[]>`
    select entity_id, action from curation_audit where entity_type = 'report_correspondence_decision' order by id`;
  assert.deepEqual(audits.map((row) => [row.entity_id, row.action]), [
    [rejected.id, 'correspondence:rejected'],
    [confirmed.id, 'correspondence:confirmed'],
  ]);

  // Revising supersedes: one live decision, the old one retired and pointed at, nothing deleted.
  const revised = await decideCorrespondence(actor, {
    hadith_id_a: FOCAL, hadith_id_b: NASAI, seen_arabic_sha256_a: arabicSha(FOCAL), seen_arabic_sha256_b: arabicSha(NASAI), decision: 'confirmed',
  });
  assert.equal(revised.superseded, rejected.id);
  const rows = await fixture.sql<{ id: string; retired: boolean }[]>`
    select id, retired_at is not null as retired from report_correspondence_decisions
    where hadith_id_b = ${NASAI} or hadith_id_a = ${NASAI} order by created_at`;
  assert.deepEqual(rows.map((row) => row.retired), [true, false]);
  assert.ok(ids(await getReportFamily(FOCAL)).includes(NASAI));

  // A decision against text the reviewer did not see is refused; a confirmation cannot carry a "not one report" reading.
  const stale = await rejection(decideCorrespondence(actor, {
    hadith_id_a: FOCAL, hadith_id_b: MAANI, seen_arabic_sha256_a: '0'.repeat(64), seen_arabic_sha256_b: arabicSha(MAANI), decision: 'rejected',
  }));
  assert.equal(stale.code, 'conflict');
  const contradiction = await rejection(decideCorrespondence(actor, {
    hadith_id_a: FOCAL, hadith_id_b: MAANI, seen_arabic_sha256_a: arabicSha(FOCAL), seen_arabic_sha256_b: arabicSha(MAANI), decision: 'confirmed',
    reviewed_relation: 'shared_quran_quotation',
  }));
  assert.equal(contradiction.code, 'invalid');

  // A changed text re-queues a decision rather than reapplying it: the confirmed Ibadi pair drops out.
  await fixture.sql`update hadiths set arabic_sha256 = repeat('f', 64) where id = ${IBADI_LOW}`;
  try {
    assert.ok(!ids(await getReportFamily(FOCAL)).includes(IBADI_LOW));
  } finally {
    await fixture.sql`update hadiths set arabic_sha256 = ${arabicSha(IBADI_LOW)} where id = ${IBADI_LOW}`;
  }
});

flow('graph: a narrator with a standing identity in several chains is one node; an identical unidentified name stays one per chain', async () => {
  const family = (await getReportFamily(FOCAL))!;
  const graph = buildFamilyGraph(family.tellings);
  const shared = graph.nodes.filter((node) => node.narrator_id === SHARED_NARRATOR);
  assert.equal(shared.length, 1);
  const chainsThrough = new Set(family.tellings.flatMap((telling) => telling.chain.nodes).filter((node) => node.narrator_id === SHARED_NARRATOR && node.is_link).map((node) => node.chain_id));
  assert.ok(chainsThrough.size >= 2);
  assert.deepEqual(shared[0].chain_ids, [...chainsThrough].sort());

  // أبيه ("his father") is written in two chains with no identity: two nodes, never merged on the text.
  const abihi = family.tellings.flatMap((telling) => telling.chain.nodes).filter((node) => !node.is_link && node.surface_ar.replace(/[إأآ]/g, 'ا') === 'ابيه');
  assert.ok(new Set(abihi.map((node) => node.chain_id)).size >= 2);
  const keys = new Set(abihi.map(mergeKey));
  assert.equal(keys.size, abihi.length);
  for (const key of keys) assert.ok(graph.nodes.some((node) => node.key === key && node.kind === 'mention'));

  // Every edge points down; works sit on the bottom layer; the shared-only view keeps the shared narrator.
  const layer = new Map(graph.nodes.map((node) => [node.key, node.layer]));
  assert.ok(graph.edges.every((edge) => layer.get(edge.source)! < layer.get(edge.target)!));
  assert.ok(graph.nodes.filter((node) => node.kind === 'work').every((node) => node.layer === graph.layers - 1));
  const compact = buildFamilyGraph(family.tellings, { sharedOnly: true });
  assert.ok(compact.nodes.some((node) => node.narrator_id === SHARED_NARRATOR));
  assert.ok(compact.nodes.length < graph.nodes.length);
  assert.deepEqual(buildFamilyGraph(family.tellings), graph, 'layout is deterministic');
});

flow('family: a report with no correspondences returns just itself', async () => {
  const family = await getReportFamily(ZAYDI_FIRST);
  assert.ok(family);
  assert.deepEqual(ids(family), [ZAYDI_FIRST]);
  assert.equal(family.correspondences_total, 0);
  assert.equal(await getReportFamily('hadith:does-not-exist'), null);
});

let server: ChildProcess | undefined;
flow('route: /hadith/[id]/chains renders for a known report and answers not-found for an unknown one', async () => {
  if (!existsSync(path.join(ROOT, '.next/BUILD_ID'))) throw new Error('Run `npx next build` first: this flow drives the built route.');
  server = spawn(process.execPath, [path.join(ROOT, 'node_modules/next/dist/bin/next'), 'start', '-p', String(PORT), '-H', '127.0.0.1'], {
    cwd: ROOT,
    env: { ...process.env, DATABASE_URL: fixture.url, NODE_ENV: 'production' },
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
  const known = await fetch(`${base}/hadith/k6/19122/chains`);
  const html = await known.text();
  assert.equal(known.status, 200);
  assert.match(html, /Tellings and chains/);
  assert.match(html, /Ma&#x27;ani al-Akhbar|Ma'ani al-Akhbar/);
  assert.match(html, /data-source-ref="THQ"/, 'the Imami tellings credit their text source');
  assert.match(html, /data-source-ref="K6I"/, 'machine-reviewed identities credit the K6 source index');
  const unknown = await fetch(`${base}/hadith/k6/999999999/chains`);
  assert.match(await unknown.text(), /not found/i);
  console.log(`    (unknown report: HTTP ${unknown.status})`);
});

function stopServer(): void {
  if (!server?.pid) return;
  if (process.platform === 'win32') spawnSync('taskkill', ['/pid', String(server.pid), '/T', '/F'], { stdio: 'ignore' });
  else server.kill('SIGTERM');
}

async function main() {
  fixture = await prepareFixtureDatabase(process.env.QUERY_FIXTURE_SCHEMA || 'correspondence_fixture');
  await loadCorrespondenceRows();
  await runFlows(async () => {
    stopServer();
    await fixture.close();
  });
}

main().catch(async (error) => {
  console.error(error);
  stopServer();
  await fixture?.close();
  process.exitCode = 1;
});
