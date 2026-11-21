/**
 * Query-layer flow tests against the fixture schema (real bundle rows). One flow per reader or curator journey.
 * Run: npx tsx --conditions=react-server src/db/queries/__tests__/flows.test.ts
 */
import assert from 'node:assert/strict';
import { prepareFixtureDatabase, type FixtureDatabase } from './fixture-database';
import { flow, rejection, runFlows } from './harness';
import { attempt } from '../../../app/actions/curation/result';
import { historicalEventCreateSchema, historicalEventPatchSchema } from '../../../app/actions/curation/schemas';
import { UnauthorizedError } from '../../../lib/auth/require-curator';
import * as commentary from '../commentary';
import * as comparative from '../comparative';
import { listParallelsForReview } from '../comparative-review';
import { setCollectionRights } from '../curation';
import { getPublicHadith, searchPublicHadiths } from '../hadith';
import { searchHadithsForReview } from '../hadith-review';
import { checkDatabase } from '../health';
import { getChainGraph } from '../isnad';
import { createLocation, listLocations } from '../location';
import { getNarratorDetail, getNarratorNetwork, listNarrators, searchNarratorsTypeahead } from '../narrator';
import { getNarratorForReview } from '../narrator-review';
import { CurationError, curationWrite } from '../write';
import { hashPassphrase, checkCuratorPassphrase } from '../../../lib/auth/passphrases';
import { createSessionToken, curatorActor, verifyCuratorToken } from '../../../lib/auth/session';

const BUKHARI_1 = 'hadith:k6:1';
const MUSLIM_RESOLVED = 'hadith:k6:11089';
const MUSLIM_TWO_BRANCHES = 'hadith:k6:10200';
const KAFI_SAHIH = 'hadith:thaqalayn:0020ba715081e8ba3e669657';
const IBADI_NIYYAT = 'hadith:openiti:ibadi:rabi_0001b|1|';
const ZAYDI_FIRST = 'hadith:openiti:zaydi:zayd_0001|1|V01P059';
const MALIK = 'narrator:rawi:20001';
const HUSAYN_BIN_MUHAMMAD = 'narrator:rawi:39284';
const MARWAN_BIN_MUHAMMAD = 'narrator:rawi:20640';

const CURATOR_NAME = 'fixture-curator';
const CURATOR_PASSPHRASE = 'correct horse battery staple';

let fixture: FixtureDatabase;
let actor: string;

const auditRows = (entityId: string) =>
  fixture.sql<{ actor: string; action: string; before: Record<string, unknown> | null; after: Record<string, unknown> | null }[]>`
    select actor, action, before, after from curation_audit where entity_id = ${entityId} order by id`;

flow('health: the database answers select 1 within the timeout', async () => {
  const health = await checkDatabase(5000);
  assert.equal(health.ok, true);
});

flow('browse: tradition filter pages through public hadiths in the one ordering contract', async () => {
  const first = await searchPublicHadiths('', { tradition: 'Imami' }, { page: 1, pageSize: 2 });
  const second = await searchPublicHadiths('', { tradition: 'Imami' }, { page: 2, pageSize: 2 });
  assert.equal(first.total, 3);
  assert.equal(first.totalPages, 2);
  assert.deepEqual(first.items.map((hadith) => hadith.hadith_no), ['4', '41']);
  assert.deepEqual(second.items.map((hadith) => hadith.hadith_no), ['60']);
  assert.ok([...first.items, ...second.items].every((hadith) => hadith.tradition === 'Imami' && hadith.source === 'Al-Kafi'));

  // Legacy alias resolves; an unknown value is an empty page, never an enum cast error (rule 8).
  const legacy = await searchPublicHadiths('', { tradition: 'Shia' }, { page: 1 });
  assert.equal(legacy.total, 3);
  const unknown = await searchPublicHadiths('', { tradition: 'Martian' }, { page: 1 });
  assert.deepEqual([unknown.total, unknown.items.length], [0, 0]);
});

flow('hadith detail: text, gated English and per-tradition grades with no default grade', async () => {
  const bukhari = await getPublicHadith(BUKHARI_1);
  assert.ok(bukhari);
  assert.match(bukhari.text_ar ?? '', /إنما الأعمال بالنيات/);
  assert.match(bukhari.text_english ?? '', /intentions/);
  assert.equal(bukhari.english_attribution?.state, 'source_provided');
  assert.equal(bukhari.variations[0].source, 'hadith_node');

  // Sahih Muslim's provider English is not cleared for publication (english_policy reviewed_only).
  const muslim = await getPublicHadith(MUSLIM_RESOLVED);
  assert.ok(muslim);
  assert.equal(muslim.text_english, null);

  const kafi = await getPublicHadith(KAFI_SAHIH);
  assert.ok(kafi);
  assert.deepEqual(kafi.assessments.map((group) => group.tradition), ['Sunni', 'Imami', 'Zaydi', 'Ibadi']);
  const imami = kafi.assessments.find((group) => group.tradition === 'Imami')!;
  assert.deepEqual(imami.assessments.map((assessment) => [assessment.grade_raw, assessment.grade_canonical, assessment.grader]), [
    ['صحيح', 'sahih', 'Allamah Baqir al-Majlisi'],
  ]);
  assert.ok(kafi.assessments.filter((group) => group.tradition !== 'Imami').every((group) => group.assessments.length === 0));
  assert.ok(bukhari.assessments.every((group) => group.assessments.length === 0), 'no grade is invented');

  assert.equal(await getPublicHadith('hadith:does-not-exist'), null);
});

flow('isnad: every name in order as written, every identity candidate with its basis, links only where verified', async () => {
  // Sahih Muslim k6:10008, real candidates: agreeing, disagreeing, unidentified and kunya-only names in one chain.
  const chain = await getChainGraph('hadith:k6:10008');
  assert.deepEqual([chain.tradition, chain.source_work], ['Sunni', 'Sahih Muslim']);
  assert.deepEqual(chain.nodes.map((node) => node.surface_ar), [
    'داود بن رشيد', 'الوليد بن مسلم', 'سعيد بن عبد العزيز', 'إسماعيل بن عبيد الله', 'أم الدرداء', 'أبي الدرداء',
  ]);
  const view = chain.nodes.map((node) => ({
    identity: node.identity,
    candidates: node.candidates.map((candidate) => `${candidate.narrator_id.replace('narrator:rawi:', '')}:${candidate.basis}`),
  }));
  assert.deepEqual(view, [
    // The name matcher and the source index name the same man: one identity, both bases.
    { identity: 'agreed', candidates: ['30248:source_index', '30248:name_exact'] },
    // They name different men: both are kept and neither is preferred.
    { identity: 'differ', candidates: ['20733:source_index', '17993:name_exact'] },
    { identity: 'differ', candidates: ['20638:source_index', '4501:name_spelling_fold'] },
    { identity: 'unidentified', candidates: [] },
    // A lexicon entry recorded only by its kunya: matched, and marked as such.
    { identity: 'agreed', candidates: ['11457:name_kunya_only'] },
    { identity: 'agreed', candidates: ['37:source_index'] },
  ]);
  assert.ok(chain.nodes.every((node) => !node.is_link && node.narrator_id === null), 'no candidate here is verified');
  assert.equal(chain.nodes[4].candidates[0].name_ar, 'أم الدرداء');
  assert.deepEqual(
    chain.edges.map((edge) => [edge.source, edge.target]),
    chain.nodes.slice(0, -1).map((node, index) => [node.node_id, chain.nodes[index + 1].node_id]),
  );

  // Source index confirmed by the Arabic, uncontested: verified links, and the candidates still say why.
  const bukhari = await getChainGraph(BUKHARI_1);
  assert.equal(bukhari.nodes[0].surface_ar, 'الحميدي عبد الله بن الزبير');
  assert.deepEqual(bukhari.nodes.map((node) => node.narrator_id), fixture.identity.verified
    .filter((row) => row.mention_id.startsWith('mention:k6:1:')).map((row) => row.narrator_id));
  assert.ok(bukhari.nodes.every((node) => node.is_link && node.candidates[0].basis === 'source_index_confirmed_by_text'));
  assert.ok(bukhari.nodes.every((node) => node.verdict === null), 'no published verdict in Sunni scope for these narrators');

  // A confirmed source index that a name match contests is shown, not settled.
  const muslim = await getChainGraph(MUSLIM_RESOLVED);
  assert.deepEqual(muslim.nodes.map((node) => node.position), [0, 1, 2, 3, 4]);
  assert.ok(muslim.nodes.every((node) => !node.is_link));
  // Position 4: a source index and a kunya-only match name different people; a kunya-only match is a label, never a
  // contest (owner decision 2026-11-21), so the mention reads as agreed and the kunya match is shown as a note.
  assert.deepEqual(muslim.nodes.map((node) => node.identity), ['agreed', 'differ', 'agreed', 'agreed', 'agreed']);
  assert.ok(muslim.nodes[4].candidates.some((candidate) => candidate.basis === 'name_kunya_only'));

  const branches = await getChainGraph(MUSLIM_TWO_BRANCHES);
  assert.deepEqual(branches.nodes.map((node) => [node.branch, node.position]), [[0, 0], [1, 0]]);
  assert.equal(branches.edges.length, 0, 'no edge crosses branches');

  // Sanads stay per tradition: no automatic name match on an Imami report.
  const kafi = await getChainGraph(KAFI_SAHIH);
  assert.ok(kafi.nodes.length > 0 && kafi.nodes.every((node) => node.identity === 'unidentified'));
});

flow('narrator: teachers and students from transmissions, tradition-scoped verdicts, lexicon hidden publicly', async () => {
  // Transmissions come only from verified links: Sunan al-Darimi k6:11880 reads الدارمي عن مروان عن الليث.
  const network = await getNarratorNetwork(MARWAN_BIN_MUHAMMAD);
  assert.deepEqual(network.teachers.map((peer) => peer.id), ['narrator:rawi:20023']);
  assert.deepEqual(network.students.map((peer) => peer.id), ['narrator:rawi:30025']);
  assert.deepEqual([network.teacher_total, network.student_total], [1, 1]);
  assert.match(network.attribution_disclaimer ?? '', /Test fixture/);
  // A name match alone (حسين بن محمد in k6:11089, contested by the source index) creates no transmission.
  const husaynNetwork = await getNarratorNetwork(HUSAYN_BIN_MUHAMMAD);
  assert.deepEqual([husaynNetwork.teacher_total, husaynNetwork.student_total], [0, 0]);

  const marwan = await getNarratorDetail(MARWAN_BIN_MUHAMMAD);
  assert.ok(marwan);
  assert.equal(marwan.name_arabic, 'مروان بن محمد بن حسان الأسدي');
  assert.deepEqual(marwan.hadiths.items.map((hadith) => hadith.id), ['hadith:k6:11880']);

  const malik = await getNarratorDetail(MALIK);
  assert.ok(malik);
  assert.deepEqual(malik.verdicts.map((verdict) => [verdict.tradition, verdict.verdict, verdict.status]), [['Sunni', 'thiqa_thabt', 'published']]);
  assert.equal(malik.lexicon, null, 'lexicon dates are hidden on public pages (question 4)');

  const reviewed = await getNarratorForReview(MALIK);
  assert.ok(reviewed);
  assert.equal(reviewed.verdicts.length, 2, 'reviewer mode also sees the unscoped Phase-0 import');
  assert.equal(reviewed.lexicon?.death_year_hijri, 179);

  assert.equal(await getNarratorDetail('narrator:rawi:does-not-exist'), null);
});

flow('search: Arabic matches inside particles and ignores harakat; English is full-text over public English only', async () => {
  const arabic = await searchPublicHadiths('الأعمال بالنيات', {}, { page: 1 });
  assert.deepEqual(arabic.items.map((hadith) => hadith.id).sort(), [BUKHARI_1, IBADI_NIYYAT].sort());
  const vocalized = await searchPublicHadiths('الأَعْمَالُ بِالنِّيَّاتِ', {}, { page: 1 });
  assert.deepEqual(vocalized.items.map((hadith) => hadith.id).sort(), [BUKHARI_1, IBADI_NIYYAT].sort());
  const tooShort = await searchPublicHadiths('لا', {}, { page: 1 });
  assert.equal(tooShort.total, 0);

  const english = await searchPublicHadiths('intentions', {}, { page: 1 });
  assert.deepEqual(english.items.map((hadith) => hadith.id), [BUKHARI_1]);
  // Fatima bint Qais appears only in Sahih Muslim's unpublished English, so the public search cannot find it.
  const hiddenEnglish = await searchPublicHadiths('Fatima', {}, { page: 1 });
  assert.equal(hiddenEnglish.total, 0);
  const reviewer = await searchHadithsForReview('Fatima', {}, { page: 1 });
  assert.deepEqual(reviewer.items.map((hadith) => hadith.id), [MUSLIM_RESOLVED]);

  assert.deepEqual((await listNarrators('مالك')).items.map((narrator) => narrator.id), [MALIK]);
  assert.deepEqual((await listNarrators('maalik')).items.map((narrator) => narrator.id), [MALIK]);
  assert.deepEqual((await searchNarratorsTypeahead('Husayn')).map((narrator) => narrator.id).sort(), ['narrator:rawi:29289', HUSAYN_BIN_MUHAMMAD].sort());
});

flow('curator sign-in: a configured name and passphrase yields a session; anything else does not', async () => {
  assert.equal(await checkCuratorPassphrase(CURATOR_NAME, CURATOR_PASSPHRASE), true);
  assert.equal(await checkCuratorPassphrase(CURATOR_NAME, 'wrong passphrase'), false);
  assert.equal(await checkCuratorPassphrase('unknown-curator', CURATOR_PASSPHRASE), false);

  const token = await createSessionToken(CURATOR_NAME, process.env.ADMIN_SESSION_SECRET!);
  const session = await verifyCuratorToken(token);
  assert.equal(session?.name, CURATOR_NAME);
  actor = curatorActor(session!.name);

  const [payload, signature] = token.split('.');
  const forged = `${Buffer.from(JSON.stringify({ n: 'intruder', e: 4102444800 })).toString('base64url')}.${signature}`;
  assert.equal(await verifyCuratorToken(forged), null, 'a payload with someone else’s signature is refused');
  assert.equal(await verifyCuratorToken(`${payload}.${signature}x`), null);
  const expired = await createSessionToken(CURATOR_NAME, process.env.ADMIN_SESSION_SECRET!, Math.floor(Date.now() / 1000) - 13 * 3600);
  assert.equal(await verifyCuratorToken(expired), null);

  // Revocation: removing the curator's entry ends the session at once.
  const configured = process.env.CURATOR_PASSPHRASES;
  process.env.CURATOR_PASSPHRASES = '{}';
  assert.equal(await verifyCuratorToken(token), null);
  process.env.CURATOR_PASSPHRASES = configured;
});

flow('commentary: create, edit, publish gate, publish, retire; every change audited in the same transaction', async () => {
  const id = await commentary.createCommentary(actor, {
    text: 'Fixture commentary (test only).',
    author: 'Fixture author',
    type: '',
    hadith_id: BUKHARI_1,
    narrator_id: MALIK,
  });
  const [created] = await fixture.sql`select status, type, created_by from commentaries where id = ${id}`;
  assert.deepEqual({ ...created }, { status: 'proposed', type: null, created_by: actor });
  const [link] = await fixture.sql`select ch.bound_arabic_sha256 = h.arabic_sha256 as bound from commentary_hadiths ch
                                   join hadiths h on h.id = ch.hadith_id where ch.commentary_id = ${id}`;
  assert.equal(link.bound, true, 'the link is bound to the Arabic it was written against');

  await commentary.updateCommentary(actor, id, { text: 'Fixture commentary, edited.' });
  const publishRefused = await rejection(commentary.publishCommentary(actor, id, 'published'));
  assert.equal((publishRefused as CurationError).code, 'refused');
  assert.deepEqual(await commentary.getPublishedCommentariesForNarrator(MALIK), []);

  await commentary.updateCommentary(actor, id, { citation_id: 'citation:fixture:taqrib-malik' });
  await commentary.publishCommentary(actor, id, 'published');
  assert.deepEqual((await commentary.getPublishedCommentariesForNarrator(MALIK)).map((row) => row.id), [id]);

  await commentary.retireCommentary(actor, id);
  assert.deepEqual(await commentary.getPublishedCommentariesForNarrator(MALIK), []);
  const [retired] = await fixture.sql`select retired_by, (select count(*)::int from commentary_hadiths where commentary_id = ${id}
                                      and retired_at is null) as live_links from commentaries where id = ${id}`;
  assert.deepEqual({ ...retired }, { retired_by: actor, live_links: 0 }, 'retired, never deleted');

  const audits = await auditRows(id);
  assert.deepEqual(audits.map((row) => row.action), ['create', 'update', 'update', 'status:published', 'retire']);
  assert.ok(audits.every((row) => row.actor === actor));
  assert.equal(audits[1].before?.text, 'Fixture commentary (test only).');
  assert.equal(audits[1].after?.text, 'Fixture commentary, edited.');
});

flow('result contract: expected refusals become { ok: false, message }, unexpected failures still throw', async () => {
  const validation = await attempt(async () => historicalEventCreateSchema.parse({}));
  assert.equal(validation.ok, false);
  assert.ok(!validation.ok && validation.fieldErrors && Object.keys(validation.fieldErrors).length > 0);

  const refusals: Array<[string, () => Promise<unknown>, string]> = [
    ['not found', () => commentary.updateCommentary(actor, 'commentary:missing', { text: 'x' }), 'Commentary not found.'],
    ['not signed in', async () => { throw new UnauthorizedError(); }, 'Sign in as a curator to make changes.'],
    ['no actor', () => curationWrite('', async () => 'unreachable'), 'A named curator is required.'],
  ];
  for (const [label, run, message] of refusals) {
    const result = await attempt(run);
    assert.deepEqual(result.ok ? null : result.message, message, label);
  }
  assert.deepEqual(await attempt(async () => 42), { ok: true, data: 42 });
  await assert.rejects(attempt(async () => { throw new Error('database exploded'); }), /database exploded/);
});

flow('refusals: no actor, unknown id, and writes during a load are refused without changing data', async () => {
  const anonymous = await rejection(curationWrite('', async () => 'unreachable'));
  assert.equal((anonymous as CurationError).code, 'unauthorized');

  const unknown = await rejection(commentary.updateCommentary(actor, 'commentary:missing', { text: 'x' }));
  assert.equal((unknown as CurationError).code, 'not_found');

  await fixture.sql`insert into dataset_versions (id, source_bundle_sha256, input_dataset_sha256, rawis_sha256, legacy_master_sha256,
      extractor_version, extractor_sha256, bundle_version, bundle_schema_version, source_release_state, release_class,
      load_purpose, load_status, attribution_disclaimer, loaded_by)
    values ('dv:fixture-loading', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 1, 'test_fixture', 'release', 'load in progress', 'loading', 'x', 'system:loader')`;
  const before = await listLocations();
  const duringLoad = await rejection(createLocation(actor, { name: 'Fixture place' }));
  assert.equal((duringLoad as CurationError).code, 'load_in_progress');
  assert.equal((await listLocations()).total, before.total);
  await fixture.sql`update dataset_versions set load_status = 'failed' where id = 'dv:fixture-loading'`;

  const zero = await createLocation(actor, { name: 'Fixture equator point', latitude: 0, longitude: 0 });
  const [stored] = await fixture.sql`select latitude, longitude from locations where id = ${zero}`;
  assert.deepEqual([stored.latitude, stored.longitude], [0, 0], 'a coordinate of 0 is kept (rule 7)');
});

flow('comparative: curated parallels list and filter publicly only when published on a public hadith', async () => {
  const faith = await comparative.createReligiousTradition(actor, { name: 'Fixture faith', geographic_heartlands: ['Fixture'] });
  const source = await comparative.createSourceText(actor, { title: 'Fixture source text', religious_tradition_id: faith });
  const tag = await comparative.createMotifTag(actor, { name: 'Fixture motif', category: 'WISDOM' });
  const onBukhari = await comparative.createCrossParallel(actor, {
    hadith_id: BUKHARI_1,
    source_text_id: source,
    tradition_id: faith,
    parallel_type: 'SHARED_SOURCE',
    hadith_excerpt_en: 'Fixture excerpt.',
    motif_tag_ids: [tag],
  });
  const onMuslim = await comparative.createCrossParallel(actor, {
    hadith_id: MUSLIM_RESOLVED,
    source_text_id: source,
    tradition_id: faith,
    parallel_type: 'DISPUTED',
    hadith_excerpt_en: 'Fixture excerpt.',
  });

  // Withdrawing Zaydi rights takes its hadiths off the public site; a parallel there cannot be published.
  const zaydiCollection = 'collection:zaydi:musnad-zayd';
  await setCollectionRights(actor, zaydiCollection, { rights_status: 'pending', english_policy: 'reviewed_only' });
  const onZaydi = await comparative.createCrossParallel(actor, {
    hadith_id: ZAYDI_FIRST,
    source_text_id: source,
    tradition_id: faith,
    parallel_type: 'SHARED_SOURCE',
  });
  const gate = await rejection(comparative.publishParallel(actor, onZaydi, 'published'));
  assert.equal((gate as CurationError).code, 'refused');
  assert.equal((await auditRows(zaydiCollection)).at(-1)?.action, 'set_rights');

  const listed = await comparative.listPublicParallels({ page: 1 });
  assert.deepEqual(listed.items.map((parallel) => parallel.id).sort(), [onBukhari, onMuslim].sort());
  const byId = new Map(listed.items.map((parallel) => [parallel.id, parallel]));
  assert.equal(byId.get(onBukhari)?.hadith_excerpt_en, 'Fixture excerpt.');
  assert.equal(byId.get(onMuslim)?.hadith_excerpt_en, null, 'no English excerpt where the hadith’s English is not public');
  assert.deepEqual(byId.get(onBukhari)?.motif_tags.map((motif) => motif.name), ['Fixture motif']);

  assert.deepEqual((await comparative.searchPublicParallels({ parallel_type: 'DISPUTED' })).map((parallel) => parallel.id), [onMuslim]);
  assert.deepEqual((await comparative.searchPublicParallels({ motif_category: 'WISDOM' })).map((parallel) => parallel.id), [onBukhari]);
  // Ordered by faith, then the parallel_type enum's declared order.
  assert.deepEqual(await comparative.getComparativeStats(), [
    { tradition: 'Fixture faith', type: 'SHARED_SOURCE', count: 1 },
    { tradition: 'Fixture faith', type: 'DISPUTED', count: 1 },
  ]);
  assert.equal((await listParallelsForReview()).total, 3, 'reviewer mode sees the proposed Zaydi parallel');

  const blocked = await rejection(comparative.retireReligiousTradition(actor, faith));
  assert.equal((blocked as CurationError).code, 'refused', 'a faith with live parallels cannot be retired');

  await setCollectionRights(actor, zaydiCollection, { rights_status: 'cleared', english_policy: 'reviewed_only' });
});

flow('action input: legacy event categories and year aliases map onto canonical columns, unknown values are refused', async () => {
  const created = historicalEventCreateSchema.parse({ title: 'Fixture', category: 'Political', year_hijri: '35', description: '' });
  assert.deepEqual([created.category, created.start_year_hijri, created.description], ['POLITICAL', 35, null]);
  assert.equal('year_hijri' in created, false);
  assert.equal(historicalEventCreateSchema.safeParse({ title: 'Fixture', category: 'Mythical' }).success, false);
  const patch = historicalEventPatchSchema.parse({ significance: '' });
  assert.deepEqual(Object.keys(patch), ['significance'], 'only sent keys reach the update allowlist (rule 5)');
});

async function main() {
  fixture = await prepareFixtureDatabase();
  process.env.ADMIN_SESSION_SECRET = 'fixture-session-secret-'.padEnd(48, 'x');
  process.env.CURATOR_PASSPHRASES = JSON.stringify({ [CURATOR_NAME]: await hashPassphrase(CURATOR_PASSPHRASE) });
  await runFlows(async () => {
    await fixture.close();
    const { getDatabase } = await import('../../client');
    await getDatabase().$client.end({ timeout: 5 });
  });
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
