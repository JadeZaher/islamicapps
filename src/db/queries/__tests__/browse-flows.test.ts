/**
 * Reading in order, addresses, citation, visibility and source credit, through the query functions on the fixture
 * database (real rows). Run: npx tsx --conditions=react-server src/db/queries/__tests__/browse-flows.test.ts
 */
import assert from 'node:assert/strict';
import { readdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { NextRequest } from 'next/server';
import { FIXTURE_VERSION_ID, prepareFixtureDatabase, type FixtureDatabase } from './fixture-database';
import { flow, runFlows } from './harness';

const ROOT = path.resolve(__dirname, '../../../..');
const SECRET = 'browse-flow-session-secret-'.padEnd(48, 'z');
const ZAYD = ['hadith:openiti:zaydi:zayd_0001|1|V01P059', 'hadith:openiti:zaydi:zayd_0002|2|V01P060', 'hadith:openiti:zaydi:zayd_0003|3|V01P061'];
const MUSLIM_IN_SOURCE_ORDER = ['hadith:k6:10008', 'hadith:k6:10200', 'hadith:k6:11089', 'hadith:k6:11880', 'hadith:k6:13881'];

let fixture: FixtureDatabase;

// Imported after DATABASE_URL points at the fixture schema (the client reads it on first use).
async function modules() {
  const [browse, hadith, version, visibility, auth, session, switches, address, reference, cite, registry, credit, structure, proxy] =
    await Promise.all([
      import('../browse'),
      import('../hadith'),
      import('../dataset-version'),
      import('../visibility'),
      import('../../../lib/auth/visibility'),
      import('../../../lib/auth/session'),
      import('../../../lib/auth/switches'),
      import('../../../lib/hadith-address'),
      import('../../../lib/citation/reference'),
      import('../../../lib/citation/cite'),
      import('../../../lib/sources/registry'),
      import('../../../lib/sources/report-credit'),
      import('../../../app/collections/structure'),
      import('../../../proxy'),
    ]);
  return { browse, hadith, version, visibility, auth, session, switches, address, reference, cite, registry, credit, structure, proxy };
}
let m: Awaited<ReturnType<typeof modules>>;

flow('addresses: every ID shape round-trips; legacy and canonical paths map onto each other', async () => {
  const cases: Array<[string, string]> = [
    ['hadith:k6:10008', '/hadith/k6/10008'],
    ['hadith:thaqalayn:00131e142163d4a8132e3552', '/hadith/thaqalayn/00131e142163d4a8132e3552'],
    ['hadith:pure-canon:pc_9', '/hadith/pure-canon/pc_9'],
    ['hadith:openiti:ibadi:rabi_0001|1|', '/hadith/openiti/ibadi/rabi_0001%7C1%7C'],
  ];
  for (const [id, canonical] of cases) {
    assert.equal(m.address.hadithPath(id), canonical);
    assert.deepEqual(m.address.parseHadithPath(canonical), { id, rest: '' });
    assert.equal(m.address.canonicalForLegacyPath(`/hadith/${encodeURIComponent(id)}`), canonical);
  }
  assert.deepEqual(m.address.parseHadithPath('/hadith/k6/10008/chains'), { id: 'hadith:k6:10008', rest: '/chains' });
  assert.equal(m.address.canonicalForLegacyPath(`/hadith/${encodeURIComponent('hadith:k6:10008')}/chains`), '/hadith/k6/10008/chains');
  assert.equal(m.address.parseHadithPath('/hadith/k6'), null);
  assert.equal(m.address.canonicalForLegacyPath('/hadith/k6/10008'), null);
  assert.equal(m.address.hadithPath('hadith:unknown-shape'), `/hadith/${encodeURIComponent('hadith:unknown-shape')}`);
});

flow('addresses: the proxy 308-redirects the old ID URL to the new address and serves the new one by rewrite', async () => {
  // The Location comes from SITE_URL, never from the request's host (src/lib/AGENTS.md §Site origin).
  const previous = process.env.SITE_URL;
  try {
    process.env.SITE_URL = 'https://site.test';
    const legacy = await m.proxy.proxy(new NextRequest(`http://forged.test/hadith/${encodeURIComponent('hadith:k6:10008')}?x=1`));
    assert.equal(legacy.status, 308);
    assert.equal(legacy.headers.get('location'), 'https://site.test/hadith/k6/10008?x=1');
    delete process.env.SITE_URL;
    const unset = await m.proxy.proxy(new NextRequest(`http://forged.test/hadith/${encodeURIComponent('hadith:k6:10008')}`));
    assert.equal(unset.headers.get('location'), 'http://localhost:3000/hadith/k6/10008', 'outside production a non-loopback host is ignored');
  } finally {
    if (previous === undefined) delete process.env.SITE_URL;
    else process.env.SITE_URL = previous;
  }
  const canonical = await m.proxy.proxy(new NextRequest('http://archive.test/hadith/k6/10008'));
  assert.match(canonical.headers.get('x-middleware-rewrite') ?? '', /\/hadith\/hadith%3Ak6%3A10008$/);
});

flow('numbering: each provider is referred to by its own scheme (table)', async () => {
  const table: Array<[Parameters<typeof m.reference.reportReference>[0], string]> = [
    [{ id: 'hadith:k6:10200', hadithNo: ' 2880 ', url: null, volume: null, pageRef: null, bookNumber: '16' }, 'Book 16, Hadith 2880'],
    [{ id: 'hadith:k6:10103', hadithNo: '0', url: null, volume: null, pageRef: null, bookNumber: '14' }, 'Book 14, unnumbered (record 10103)'],
    [{ id: 'hadith:thaqalayn:x', hadithNo: '41', url: 'https://thaqalayn.net/hadith/1/2/41/1', volume: '5', pageRef: null, bookNumber: '5' }, 'Volume 5, Book 2, Chapter 41, Hadith 1'],
    [{ id: 'hadith:openiti:zaydi:zayd_0001|1|V01P059', hadithNo: '1', url: null, volume: '1', pageRef: 'V01P059', bookNumber: '1' }, 'No. 1 (vol. 1, p. 59)'],
    [{ id: 'hadith:pure-canon:pc_48289', hadithNo: null, url: null, volume: null, pageRef: null, bookNumber: null }, 'Record pc_48289 (no number in this copy)'],
  ];
  for (const [fields, expected] of table) assert.equal(m.reference.reportReference(fields), expected);
});

flow('browse: a chapter reads in source order across a page boundary', async () => {
  const outline = await m.browse.getBookOutline('musnad_zayd', '1', m.visibility.PUBLIC_VISIBILITY);
  assert.ok(outline, 'Zaydi book outline');
  assert.equal(outline.chapters.length, 1);
  const chapterKey = outline.chapters[0].key;
  const scope = { workSlug: 'musnad_zayd', bookNumber: '1', chapterKey };
  const first = await m.browse.listReportsInOrder(scope, { page: 1, pageSize: 2 }, m.visibility.PUBLIC_VISIBILITY);
  const second = await m.browse.listReportsInOrder(scope, { page: 2, pageSize: 2 }, m.visibility.PUBLIC_VISIBILITY);
  assert.equal(first.total, 3);
  assert.equal(first.totalPages, 2);
  assert.deepEqual([...first.items, ...second.items].map((item) => item.id), ZAYD);
  assert.deepEqual(first.items.map((item) => item.reference), ['No. 1 (vol. 1, p. 59)', 'No. 2 (vol. 1, p. 60)']);
});

flow('browse: works index lists all four traditions alphabetically; a work without chapters says so honestly', async () => {
  const traditions = await m.browse.listWorksByTradition(m.visibility.PUBLIC_VISIBILITY);
  assert.deepEqual(traditions.map((group) => group.tradition), ['Ibadi', 'Imami', 'Sunni', 'Zaydi']);
  const muslim = await m.browse.getWorkOutline('muslim', m.visibility.PUBLIC_VISIBILITY);
  assert.ok(muslim);
  assert.equal(muslim.structure.withChapter, 0);
  assert.match(m.structure.structureNote(muslim.structure) ?? '', /books of this work but not their chapters/);
  assert.equal(m.structure.structureNote({ namespace: 'pure-canon', reports: 10, withBook: 0, withChapter: 0, withNumber: 10, distinctNumbers: 4 })?.includes('numbers repeat'), true);
});

flow('report context: previous/next within the work, with none before the first or after the last', async () => {
  const first = await m.browse.getReportContext(MUSLIM_IN_SOURCE_ORDER[0], m.visibility.PUBLIC_VISIBILITY);
  const last = await m.browse.getReportContext(MUSLIM_IN_SOURCE_ORDER[4], m.visibility.PUBLIC_VISIBILITY);
  assert.ok(first && last);
  assert.equal(first.previous, null);
  assert.equal(first.next?.id, MUSLIM_IN_SOURCE_ORDER[1]);
  assert.deepEqual([first.position, first.total], [1, 5]);
  assert.equal(last.next, null);
  assert.equal(last.previous?.id, MUSLIM_IN_SOURCE_ORDER[3]);
  assert.deepEqual([last.position, last.total], [5, 5]);
  const middle = await m.browse.getReportContext(MUSLIM_IN_SOURCE_ORDER[2], m.visibility.PUBLIC_VISIBILITY);
  assert.equal(middle?.book?.label, 'Book 19');
  assert.equal(middle?.tradition, 'Sunni');
});

flow('English label and credit: source-provided credits the translator; machine names its model or says it is missing', async () => {
  const cases: Array<[{ state: string; translator: string | null; model: string | null }, string, string, string]> = [
    [{ state: 'source_provided', translator: null, model: null }, 'Source-provided English, not reviewed here', 'SUN', 'Translation: Muhammad Muhsin Khan'],
    [{ state: 'machine_unreviewed', translator: null, model: 'tencent/hy-mt2-30b-a3b' }, 'Unreviewed machine translation (tencent/hy-mt2-30b-a3b)', 'SWI', 'Machine translation (tencent/hy-mt2-30b-a3b), not reviewed'],
    [{ state: 'machine_unreviewed', translator: null, model: null }, 'Unreviewed machine translation (model not recorded)', 'SWI', 'Machine translation (model not recorded), not reviewed'],
  ];
  for (const [english, label, code, detail] of cases) {
    assert.equal(m.credit.englishLabel(english), label);
    const reference = m.credit.englishReference({ sourceSlug: 'sunnah-com', sourceWorkId: 'sunni:bukhari', english });
    assert.deepEqual([reference?.role, reference?.code, reference?.detail], ['English', code, detail]);
  }
});

flow('citation: names the work, reference, dataset version, address and access date, and credits the source', async () => {
  const context = await m.browse.getReportContext('hadith:thaqalayn:00131e142163d4a8132e3552', m.visibility.PUBLIC_VISIBILITY);
  const version = await m.version.getCurrentDatasetVersion();
  assert.ok(context && version);
  assert.equal(version.id, FIXTURE_VERSION_ID);
  const references = m.credit.reportSourceReferences({
    sourceSlug: context.work.sourceSlug,
    sourceWorkId: context.work.sourceWorkId,
    workName: context.work.name,
    url: context.url,
    number: context.number,
    english: context.english,
  });
  const text = m.cite.citationText({
    workName: context.work.name,
    reference: context.reference,
    version: { label: version.label, shortId: version.shortId },
    address: `https://archive.test${m.address.hadithPath(context.id)}`,
    origin: 'https://archive.test',
    accessed: '2026-11-21',
    references,
  });
  assert.match(text, /^Al-Kafi, Volume 5, Book 2, Chapter 41, Hadith 1\. Shura wa Istehsan/);
  assert.ok(text.includes(`dataset version ${version.shortId}`), text);
  assert.ok(text.includes('https://archive.test/hadith/thaqalayn/00131e142163d4a8132e3552. Accessed 2026-11-21.'));
  assert.ok(text.includes('Text: Thaqalayn (Stichting Thaqalayn) [THQ], Al-Kafi, al-Kulayni; CC BY 4.0; https://archive.test/sources#thq'), text);
  assert.equal(references[0].external, 'https://thaqalayn.com/hadith/1/2/41/1');
});

flow('credit: every loaded work and every registered source work has a source record and a work credit', async () => {
  const loaded = await fixture.sql<{ source_slug: string; source_work_id: string }[]>`
    select s.slug as source_slug, c.source_work_id from collections c join sources s on s.id = c.source_id where c.retired_at is null`;
  const registryFile = JSON.parse(readFileSync(path.join(ROOT, 'datasets/hadith-data/neo4j_export/source_work_registry.json'), 'utf8')) as {
    source_works: Array<{ source_slug: string; source_work_id: string }>;
  };
  const works = [...loaded, ...registryFile.source_works];
  assert.equal(registryFile.source_works.length, 34);
  for (const work of works) {
    assert.ok(m.registry.sourceForDatabaseSlug(work.source_slug), `no source record for ${work.source_slug}`);
    assert.ok(m.registry.WORK_CREDITS[work.source_work_id], `no work credit for ${work.source_work_id}`);
  }
  const cards = readdirSync(path.join(ROOT, 'datasets/sources')).filter((file) => file.endsWith('.md') && !file.startsWith('_') && file !== 'README.md');
  const covered = new Set(m.registry.SOURCES.flatMap((record) => record.sourceCards));
  for (const card of cards) assert.ok(covered.has(card.replace(/\.md$/, '')), `source card ${card} has no registry record`);
  assert.equal(new Set(m.registry.SOURCES.map((record) => record.code)).size, m.registry.SOURCES.length, 'codes are unique');
  for (const id of MUSLIM_IN_SOURCE_ORDER) assert.equal(m.registry.sourceCodeForHadithId(id), 'SUN');
});

flow('credit: every report with text yields a Text source reference, and English adds its translator', async () => {
  const hadithIds = (await fixture.sql<{ id: string }[]>`select id from hadiths where text_ar is not null`).map((row) => row.id);
  assert.ok(hadithIds.length >= 10);
  for (const id of hadithIds) {
    const context = await m.browse.getReportContext(id, m.visibility.PUBLIC_VISIBILITY);
    assert.ok(context, id);
    const references = m.credit.reportSourceReferences({ ...context.work, workName: context.work.name, url: context.url, number: context.number, english: context.english });
    assert.equal(references[0]?.role, 'Text', `${id} has no text credit`);
    if (context.english) assert.equal(references[1]?.role, 'English', `${id} shows English without a credit`);
  }
  const bukhari = await m.browse.getReportContext('hadith:k6:1', m.visibility.PUBLIC_VISIBILITY);
  const references = m.credit.reportSourceReferences({ ...bukhari!.work, workName: bukhari!.work.name, url: bukhari!.url, number: bukhari!.number, english: bukhari!.english });
  assert.equal(references[1]?.detail, 'Translation: Muhammad Muhsin Khan');
  assert.equal(references[0].external, 'https://sunnah.com/bukhari:1');
});

flow('visibility: anonymous is public whatever the switch; a curator sees unpublished rows only when signed in under preview', async () => {
  const hidden = ZAYD[0];
  await fixture.sql`update collection_rights set rights_status = 'pending' where collection_id = 'collection:zaydi:musnad-zayd'`;
  try {
    process.env.ADMIN_SESSION_SECRET = SECRET;
    process.env.CURATOR_PASSPHRASES = JSON.stringify({ reviewer: 'scrypt$unused' });
    const token = await m.session.createSessionToken('reviewer', SECRET);
    const forged = `${token.slice(0, -2)}xx`;
    const on = { ...process.env, PRIVATE_PREVIEW: '1' };
    const off = { ...process.env, PRIVATE_PREVIEW: undefined };

    const anonymousOn = await m.auth.visibilityForSessionToken(undefined, on);
    const anonymousOff = await m.auth.visibilityForSessionToken(undefined, off);
    const forgedOn = await m.auth.visibilityForSessionToken(forged, on);
    const curatorOff = await m.auth.visibilityForSessionToken(token, off);
    const curatorOn = await m.auth.visibilityForSessionToken(token, on);
    assert.deepEqual([anonymousOn, anonymousOff, forgedOn, curatorOff], ['public', 'public', 'public', 'public']);
    assert.equal(curatorOn, 'curator');
    process.env.CURATOR_PASSPHRASES = JSON.stringify({ someone_else: 'scrypt$unused' });
    assert.equal(await m.auth.visibilityForSessionToken(token, { ...process.env, PRIVATE_PREVIEW: '1' }), 'public', 'revoked curator');

    for (const visibility of [anonymousOn, anonymousOff, forgedOn, curatorOff]) {
      assert.equal(await m.hadith.getVisibleHadith(hidden, visibility), null);
      assert.equal(await m.browse.getReportContext(hidden, visibility), null);
      const zaydi = (await m.browse.listWorksByTradition(visibility)).find((group) => group.tradition === 'Zaydi');
      assert.deepEqual(zaydi?.works, []);
    }
    assert.equal((await m.hadith.getVisibleHadith(hidden, curatorOn))?.id, hidden);
    assert.equal((await m.browse.getReportContext(hidden, curatorOn))?.next?.id, ZAYD[1]);
    const zaydi = (await m.browse.listWorksByTradition(curatorOn)).find((group) => group.tradition === 'Zaydi');
    assert.equal(zaydi?.works[0]?.reportCount, 3);
  } finally {
    await fixture.sql`update collection_rights set rights_status = 'cleared' where collection_id = 'collection:zaydi:musnad-zayd'`;
  }
});

flow('switches: auth defaults off, preview implies auth and refuses to run unconfigured, return paths stay on-site', async () => {
  const s = m.switches;
  assert.equal(s.authEnabled({}), false);
  assert.equal(s.authEnabled({ AUTH_ENABLED: 'true' }), false);
  assert.equal(s.authEnabled({ AUTH_ENABLED: '1' }), true);
  assert.equal(s.authEnabled({ PRIVATE_PREVIEW: '1' }), true);
  assert.match(s.previewConfigurationProblem({ PRIVATE_PREVIEW: '1' }) ?? '', /ADMIN_SESSION_SECRET/);
  assert.match(s.previewConfigurationProblem({ PRIVATE_PREVIEW: '1', ADMIN_SESSION_SECRET: SECRET }) ?? '', /CURATOR_PASSPHRASES/);
  assert.equal(s.previewConfigurationProblem({ PRIVATE_PREVIEW: '1', ADMIN_SESSION_SECRET: SECRET, CURATOR_PASSPHRASES: '{"a":"x"}' }), null);
  for (const pathname of ['/sign-in', '/admin', '/admin/commentaries', '/api/auth/sign-in', '/api/export/hadiths']) assert.ok(s.isAuthSurface(pathname), pathname);
  for (const pathname of ['/administrator', '/collections', '/api/health']) assert.ok(!s.isAuthSurface(pathname), pathname);
  const table: Array<[string | undefined, boolean, string]> = [
    ['/admin/x', false, '/admin/x'],
    ['/collections', false, '/admin'],
    ['/collections', true, '/collections'],
    ['//evil.test', true, '/admin'],
    ['/\\evil.test', true, '/admin'],
    ['https://evil.test', true, '/admin'],
    [undefined, true, '/admin'],
  ];
  for (const [next, preview, expected] of table) assert.equal(s.safeReturnPath(next, preview), expected, String(next));

  // Auth off: every curation action refuses through the existing result object, before any session code runs.
  const saved = { auth: process.env.AUTH_ENABLED, preview: process.env.PRIVATE_PREVIEW };
  delete process.env.AUTH_ENABLED;
  delete process.env.PRIVATE_PREVIEW;
  try {
    const { attempt } = await import('../../../app/actions/curation/result');
    const { requireCurator } = await import('../../../lib/auth/require-curator');
    assert.deepEqual(await attempt(() => requireCurator()), { ok: false, message: 'Curation is not enabled on this deployment.' });
  } finally {
    if (saved.auth !== undefined) process.env.AUTH_ENABLED = saved.auth;
    if (saved.preview !== undefined) process.env.PRIVATE_PREVIEW = saved.preview;
  }
});

async function main() {
  fixture = await prepareFixtureDatabase(process.env.QUERY_FIXTURE_SCHEMA || 'browse_fixture');
  m = await modules();
  await runFlows(async () => {
    await fixture.close();
    const { getDatabase } = await import('../../client');
    await getDatabase().$client.end({ timeout: 5 });
  });
}

main().catch(async (error) => {
  console.error(error);
  await fixture?.close();
  process.exitCode = 1;
});
