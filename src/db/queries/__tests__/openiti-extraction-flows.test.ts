/**
 * OpenITI extraction fields through the public seams: the detail reader, then the report page of a production build
 * (`next start`) on the fixture schema. Real reports cut from the loaded projection (fixtures/openiti-extraction.json,
 * pg_export/slice_openiti_extraction_fixture.py). Requires `npx next build`.
 * Run: npx tsx --conditions=react-server src/db/queries/__tests__/openiti-extraction-flows.test.ts
 */
import assert from 'node:assert/strict';
import { spawn, spawnSync, type ChildProcess } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { FIXTURE_VERSION_ID, prepareFixtureDatabase, type FixtureDatabase } from './fixture-database';
import { flow, runFlows } from './harness';
import { getPublicHadith } from '../hadith';
import { hadithPath } from '../../../lib/hadith-address';
import { reportReference } from '../../../lib/citation/reference';
import { norm } from '../../../lib/attribution/classify-attribution';

const ROOT = path.resolve(__dirname, '../../../..');
const PORT = Number(process.env.OPENITI_HTTP_PORT || 3931);
const BASE = `http://127.0.0.1:${PORT}`;

const CONFIDENT = 'hadith:openiti:ibadi:rabi_0001|1|';
const CONTINUATION = 'hadith:openiti:ibadi:rabi_0001b|1|';
const COMMENTARY = 'hadith:openiti:ibadi:rabi_0225|225|V01P060';
const LOW = 'hadith:openiti:zaydi:zayd_0010|10|V01P067';
const SPLIT_PARENT = 'hadith:openiti:zaydi:zayd_0007|7|V01P064';
const SPLIT_CHILD = 'hadith:openiti:zaydi:zayd_0007#2|7|V01P064';
const RETIRED = 'hadith:openiti:zaydi:zayd_0009|9|V01P065';

interface FixtureReport extends Record<string, unknown> {
  id: string;
  text_ar: string;
  sanad_ar: string | null;
  matn_ar: string | null;
  source_notes: Array<{ kind: string; text_ar: string }> | null;
}
interface ExtractionFixture {
  hadiths: FixtureReport[];
  retired: Array<{ id: string; record_id: string; source_record_id: string; hadith_no: string; page_ref: string; text_ar: string; arabic_sha256: string; provenance: string }>;
}

const extraction = JSON.parse(readFileSync(path.join(__dirname, 'fixtures/openiti-extraction.json'), 'utf8')) as ExtractionFixture;
const report = (id: string): FixtureReport => {
  const found = extraction.hadiths.find((row) => row.id === id);
  assert.ok(found, `${id} is in the fixture`);
  return found;
};
const collapse = (value: string) => value.replace(/\s+/g, ' ').trim();

let fixture: FixtureDatabase;
let server: ChildProcess | undefined;

/** Puts the real reports into the fixture schema; the fixture's older rabi_0001b row is replaced by the real one. */
async function loadCases(): Promise<void> {
  const { sql } = fixture;
  const pipeline = { first_seen_dataset_version_id: FIXTURE_VERSION_ID, changed_in_dataset_version_id: FIXTURE_VERSION_ID };
  for (const row of extraction.hadiths) {
    const values = { ...row, book_id: null, chapter_id: null };
    await sql`insert into hadiths ${sql({ ...values, ...pipeline })}
      on conflict (id) do update set ${sql(values)}`;
  }
  const [retired] = extraction.retired;
  const sibling = report(SPLIT_PARENT);
  await sql`insert into hadiths ${sql({
    id: retired.id,
    record_id: retired.record_id,
    source_record_id: retired.source_record_id,
    collection_id: sibling.collection_id as string,
    collection_sort_key: sibling.collection_sort_key as number,
    tradition_id: sibling.tradition_id as string,
    hadith_no: retired.hadith_no,
    text_ar: retired.text_ar,
    text_ar_normalized: norm(retired.text_ar),
    arabic_sha256: retired.arabic_sha256,
    page_ref: retired.page_ref,
    provenance_source: retired.provenance,
    ...pipeline,
    retired_in_dataset_version_id: FIXTURE_VERSION_ID,
    retired_at: new Date(),
  })}`;
  await sql`select refresh_publication_facets(array(select id from hadiths))`;
}

function startServer(): Promise<void> {
  server = spawn(process.execPath, [path.join(ROOT, 'node_modules/next/dist/bin/next'), 'start', '-p', String(PORT), '-H', '127.0.0.1'], {
    cwd: ROOT,
    env: { ...process.env, DATABASE_URL: fixture.url, SITE_URL: BASE, NODE_ENV: 'production', AUTH_ENABLED: '', PRIVATE_PREVIEW: '' },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  return (async () => {
    for (let attempt = 0; attempt < 60; attempt++) {
      try {
        await fetch(`${BASE}/api/health`);
        return;
      } catch {
        await new Promise((resolve) => setTimeout(resolve, 500));
      }
    }
    throw new Error('next start did not answer within 30 s.');
  })();
}

function stopServer(): void {
  if (!server?.pid) return;
  if (process.platform === 'win32') spawnSync('taskkill', ['/pid', String(server.pid), '/T', '/F'], { stdio: 'ignore' });
  else server.kill('SIGTERM');
  server = undefined;
}

async function page(id: string): Promise<{ status: number; html: string }> {
  const response = await fetch(`${BASE}${hadithPath(id)}`);
  return { status: response.status, html: await response.text() };
}

/** The visible text of an HTML fragment (tags removed, entities of the characters used here decoded). */
const visibleText = (html: string) => collapse(html.replace(/<[^>]+>/g, ' ').replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&#x27;/g, "'"));

// ---- The reader (getPublicHadith) -------------------------------------------------------------------------------

flow('confident split: the Arabic chain span and the matn tile the report text', async () => {
  const detail = await getPublicHadith(CONFIDENT);
  assert.ok(detail);
  assert.equal(detail.split_confidence, 'high');
  assert.ok(detail.sanad_ar && detail.matn_ar);
  assert.equal(collapse(`${detail.sanad_ar} ${detail.matn_ar}`), collapse(detail.text_ar!));
  assert.equal(detail.chain_continues_from, null);
  assert.deepEqual(detail.source_notes, []);
});

flow('continuation chain: the report names the report whose chain it repeats', async () => {
  const detail = await getPublicHadith(CONTINUATION);
  assert.ok(detail);
  assert.equal(detail.chain_continues_from?.id, CONFIDENT);
  assert.equal(detail.chain_continues_from?.hadith_no, '1');
  assert.match(detail.sanad_ar ?? '', /^وبهذا السند/);
});

flow('low confidence: whole text, no span and no matn', async () => {
  const detail = await getPublicHadith(LOW);
  assert.ok(detail);
  assert.equal(detail.split_confidence, 'low');
  assert.equal(detail.sanad_ar, null);
  assert.equal(detail.matn_ar, null);
  assert.ok(detail.text_ar && detail.text_ar.length > 0);
});

flow('split child: its own address (the # is part of the id), the parent number, "part 2"', async () => {
  const child = await getPublicHadith(SPLIT_CHILD);
  const parent = await getPublicHadith(SPLIT_PARENT);
  assert.ok(child && parent);
  assert.equal(child.hadith_no, parent.hadith_no);
  assert.notEqual(child.text_ar, parent.text_ar);
  const fields = (detail: typeof child) => ({ id: detail.id, hadithNo: detail.hadith_no, url: null, volume: null, pageRef: detail.page_ref, bookNumber: null });
  assert.equal(reportReference(fields(child)), 'No. 7, part 2 (vol. 1, p. 64)');
  assert.equal(reportReference(fields(parent)), 'No. 7 (vol. 1, p. 64)');
});

flow('retired absorbed id: the row is kept (retire, not delete) but unknown to readers (no redirect)', async () => {
  const [kept] = await fixture.sql<{ retired: boolean }[]>`select retired_at is not null as retired from hadiths where id = ${RETIRED}`;
  assert.equal(kept?.retired, true);
  assert.equal(await getPublicHadith(RETIRED), null);
});

flow('commentary: source notes come as labelled kinds and are never inside the report text', async () => {
  const detail = await getPublicHadith(COMMENTARY);
  assert.ok(detail);
  assert.deepEqual(detail.source_notes.map((note) => note.kind).sort(), ['compiler_comment', 'editor_footnote']);
  for (const note of detail.source_notes) assert.ok(!collapse(detail.text_ar!).includes(collapse(note.text_ar)), note.kind);
});

// ---- The report page (next start) -------------------------------------------------------------------------------

flow('page, confident split: chain span in the isnad section, matn alone in the text section', async () => {
  const { status, html } = await page(CONFIDENT);
  assert.equal(status, 200);
  const row = report(CONFIDENT);
  const text = visibleText(html);
  assert.ok(text.includes('Matn · report text'));
  const textSection = visibleText(html.slice(html.indexOf('id="matn-heading"'), html.indexOf('id="isnad-heading"')));
  const isnadSection = visibleText(html.slice(html.indexOf('id="isnad-heading"')));
  assert.ok(textSection.includes(collapse(row.matn_ar!)) && !textSection.includes(collapse(row.sanad_ar!)));
  assert.ok(isnadSection.includes(collapse(row.sanad_ar!)));
  assert.ok(!text.includes('Chain continues from'));
});

flow('page, continuation: "Chain continues from No. 1" links to that report', async () => {
  const { status, html } = await page(CONTINUATION);
  assert.equal(status, 200);
  assert.ok(visibleText(html).includes('Chain continues from No. 1'));
  assert.ok(html.includes(`href="${hadithPath(CONFIDENT)}"`));
});

flow('page, low confidence: the whole text once, under "Text as in the source"', async () => {
  const { status, html } = await page(LOW);
  assert.equal(status, 200);
  const text = visibleText(html);
  assert.ok(text.includes('Text as in the source') && !text.includes('Matn · report text'));
  assert.equal(text.split(collapse(report(LOW).text_ar)).length - 1, 1);
});

flow('page, split child: reachable through its encoded # and headed "part 2"', async () => {
  const { status, html } = await page(SPLIT_CHILD);
  assert.equal(status, 200);
  assert.ok(visibleText(html).includes('7, part 2'));
});

flow('page, retired absorbed id: 404', async () => {
  assert.equal((await page(RETIRED)).status, 404);
});

flow('page, commentary: a labelled, credited block below the text, apart from it', async () => {
  const { status, html } = await page(COMMENTARY);
  assert.equal(status, 200);
  const row = report(COMMENTARY);
  const notesAt = html.indexOf('id="notes-heading"');
  assert.ok(notesAt > html.indexOf('id="matn-heading"'));
  const above = visibleText(html.slice(0, notesAt));
  const notes = visibleText(html.slice(notesAt));
  assert.ok(notes.includes('Notes in the source edition') && notes.includes("Compiler's remark") && notes.includes("Editor's footnote"));
  assert.ok(/data-source-ref="OITI"/.test(html.slice(notesAt)));
  for (const note of row.source_notes!) {
    assert.ok(notes.includes(collapse(note.text_ar)));
    assert.ok(!above.includes(collapse(note.text_ar)), 'a note never appears in the text above');
  }
});

async function main(): Promise<void> {
  if (!existsSync(path.join(ROOT, '.next/BUILD_ID'))) throw new Error('Run `npx next build` first.');
  fixture = await prepareFixtureDatabase(process.env.QUERY_FIXTURE_SCHEMA || 'openiti_fixture');
  await loadCases();
  await startServer();
  await runFlows(async () => {
    stopServer();
    await fixture.close();
  });
}

main().catch(async (error) => {
  console.error(error);
  stopServer();
  await fixture?.close().catch(() => undefined);
  process.exit(1);
});
