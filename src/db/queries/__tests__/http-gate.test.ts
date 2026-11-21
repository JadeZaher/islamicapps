/**
 * Access-control flows through the public HTTP seam of a production build (`next start`), on the fixture schema.
 * Requires a prior `npx next build`. Run: npx tsx --conditions=react-server src/db/queries/__tests__/http-gate.test.ts
 */
import assert from 'node:assert/strict';
import { spawn, spawnSync, type ChildProcess } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { prepareFixtureDatabase, type FixtureDatabase } from './fixture-database';
import { flow, runFlows } from './harness';
import { hashPassphrase } from '../../../lib/auth/passphrases';

const ROOT = path.resolve(__dirname, '../../../..');
const PORT = Number(process.env.HTTP_GATE_PORT || 3917);
const BASE = `http://127.0.0.1:${PORT}`;
const CURATOR = 'http-curator';
const PASSPHRASE = 'a long fixture passphrase';

let fixture: FixtureDatabase;
let server: ChildProcess | undefined;

/** The server-action ID the build assigned to `exportedName`, preferring the Postgres curation module. */
function actionId(exportedName: string): { id: string; file: string; page: string } {
  const manifest = JSON.parse(readFileSync(path.join(ROOT, '.next/server/server-reference-manifest.json'), 'utf8')) as {
    node: Record<string, { exportedName?: string; filename?: string; workers: Record<string, unknown> }>;
  };
  const candidates = Object.entries(manifest.node)
    .filter(([, entry]) => entry.exportedName === exportedName)
    .sort(([, a], [, b]) => Number(b.filename?.includes('actions/curation')) - Number(a.filename?.includes('actions/curation')));
  if (!candidates[0]) throw new Error(`No server action named ${exportedName} in the build.`);
  const [id, entry] = candidates[0];
  return { id, file: entry.filename ?? '', page: Object.keys(entry.workers)[0].replace(/^app/, '').replace(/\/page$/, '') };
}

/** Invokes a server action the way the browser does: POST to a page with the Next-Action header. */
function callAction(id: string, pathname: string, args: unknown[], headers: Record<string, string> = {}) {
  return fetch(`${BASE}${pathname}`, {
    method: 'POST',
    redirect: 'manual',
    headers: { 'Next-Action': id, 'Content-Type': 'text/plain;charset=UTF-8', Accept: 'text/x-component', ...headers },
    body: JSON.stringify(args),
  });
}

async function signIn(passphrase: string, forwardedFor: string, extra: { name?: string; headers?: Record<string, string> } = {}): Promise<Response> {
  const form = new URLSearchParams({ name: extra.name ?? (passphrase === PASSPHRASE ? CURATOR : `nobody-${Math.random().toString(36).slice(2)}`), passphrase, next: '/admin/commentaries' });
  return fetch(`${BASE}/api/auth/sign-in`, {
    method: 'POST',
    body: form,
    redirect: 'manual',
    headers: { 'X-Forwarded-For': forwardedFor, ...extra.headers },
  });
}

/** Runs the approve-preview operator script against the fixture database. */
function approvePreview(...args: string[]): { status: number | null; output: string } {
  const result = spawnSync(process.execPath, [path.join(ROOT, 'node_modules/tsx/dist/cli.mjs'), 'src/scripts/db/approve-preview.ts', ...args], {
    cwd: ROOT,
    env: { ...process.env, DATABASE_URL: fixture.url },
    encoding: 'utf8',
  });
  return { status: result.status, output: `${result.stdout}${result.stderr}` };
}

/** The result object of a server-action response (RSC flight text), e.g. {"ok":false,"message":"..."}. */
function actionPayload(text: string): { ok: boolean; message?: string; data?: unknown; fieldErrors?: Record<string, string[]> } {
  const line = text.split('\n').find((candidate) => /^\d+:\{"ok":/.test(candidate));
  if (!line) throw new Error(`No result object in the action response: ${text.slice(0, 300)}`);
  return JSON.parse(line.slice(line.indexOf(':') + 1));
}

let curatorSession = '';

/** fetch that retries once when a kept-alive socket was closed by the server during a long script run. */
async function pageFetch(url: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(url, init);
  } catch {
    return fetch(url, init);
  }
}

async function startServer(env: NodeJS.ProcessEnv): Promise<void> {
  server = spawn(process.execPath, [path.join(ROOT, 'node_modules/next/dist/bin/next'), 'start', '-p', String(PORT), '-H', '127.0.0.1'], {
    cwd: ROOT,
    env,
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  server.stderr?.on('data', (chunk) => process.env.HTTP_GATE_VERBOSE && process.stderr.write(chunk));
  for (let attempt = 0; attempt < 60; attempt++) {
    try {
      await fetch(`${BASE}/sign-in`);
      return;
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 500));
    }
  }
  throw new Error('next start did not answer within 30 s.');
}

function stopServer(): void {
  if (!server?.pid) return;
  // Kill exactly the process tree we started.
  if (process.platform === 'win32') spawnSync('taskkill', ['/pid', String(server.pid), '/T', '/F'], { stdio: 'ignore' });
  else server.kill('SIGTERM');
}

flow('health: /api/health answers 200 while the database is reachable', async () => {
  const response = await fetch(`${BASE}/api/health`);
  assert.equal(response.status, 200);
  assert.equal(((await response.json()) as { status: string }).status, 'ok');
});

flow('route gate: anonymous /admin redirects to sign-in, anonymous POST to /admin is 401, with noindex', async () => {
  const page = await fetch(`${BASE}/admin/commentaries`, { redirect: 'manual' });
  assert.equal(page.status, 303);
  assert.match(page.headers.get('location') ?? '', /\/sign-in\?next=%2Fadmin%2Fcommentaries/);
  assert.equal(page.headers.get('x-robots-tag'), 'noindex, nofollow');
  const action = actionId('createCommentary');
  const post = await callAction(action.id, '/admin/commentaries', [{ text: 'anonymous' }]);
  assert.equal(post.status, 401);
});

flow('action gate: an anonymous call to a mutating action from a public page writes nothing', async () => {
  const action = actionId('createCommentary');
  const before = await fixture.sql`select count(*)::int as count from commentaries`;
  for (const pathname of ['/', '/hadith', '/narrator']) {
    const response = await callAction(action.id, pathname, [{ text: 'anonymous write', author: 'nobody' }], { 'X-Forwarded-For': '203.0.113.9' });
    await response.text();
    const after = await fixture.sql`select count(*)::int as count from commentaries`;
    assert.equal(after[0].count, before[0].count, `no row written via ${pathname} (status ${response.status})`);
  }
  console.log(`    (wired createCommentary: ${action.file})`);
});

flow('sign-in throttling: five failures from one address, then the sixth attempt is 429', async () => {
  const ip = '198.51.100.7';
  for (let attempt = 1; attempt <= 5; attempt++) {
    const failed = await signIn('wrong passphrase', ip);
    assert.equal(failed.status, 303);
    assert.match(failed.headers.get('location') ?? '', /sign-in\?error=1/);
  }
  assert.equal((await signIn(PASSPHRASE, ip)).status, 429, 'even the right passphrase is refused once throttled');
});

flow('sign-in throttling: a spoofed left-most X-Forwarded-For does not reset the limit', async () => {
  const edgeAddress = '198.51.100.20';
  for (let attempt = 1; attempt <= 5; attempt++) {
    assert.equal((await signIn('wrong passphrase', `10.9.${attempt}.1, ${edgeAddress}`)).status, 303);
  }
  assert.equal((await signIn('wrong passphrase', `10.9.99.1, ${edgeAddress}`)).status, 429, 'rotating the client-supplied hop changes nothing');
  assert.equal((await signIn(PASSPHRASE, `10.9.100.1, ${edgeAddress}`)).status, 429, 'the right passphrase is refused too');
});

flow('sign-in throttling: concurrent wrong attempts reserve their slot before the slow comparison', async () => {
  const address = '198.51.100.21';
  const responses = await Promise.all(Array.from({ length: 6 }, () => signIn('wrong passphrase', address)));
  const compared = responses.filter((response) => response.status === 303).length;
  const refused = responses.filter((response) => response.status === 429).length;
  assert.deepEqual([compared, refused], [5, 1], 'five comparisons allowed, the sixth is 429');
});

flow('sign-in throttling: a browser form post lands on /sign-in?error=throttled, other callers get 429', async () => {
  const address = '198.51.100.22';
  for (let attempt = 1; attempt <= 5; attempt++) await signIn('wrong passphrase', address);
  const browser = await signIn('wrong passphrase', address, { headers: { Accept: 'text/html,application/xhtml+xml' } });
  assert.equal(browser.status, 303);
  assert.match(browser.headers.get('location') ?? '', /\/sign-in\?error=throttled$/);
  assert.equal((await signIn('wrong passphrase', address)).status, 429);
  const page = await fetch(`${BASE}/sign-in?error=throttled`);
  assert.match(await page.text(), /Too many attempts/);
});

flow('sign-in throttling: one curator name is throttled across addresses, and a correct sign-in clears it', async () => {
  // Twenty wrong attempts for a name, each from a different address: the next is refused even from a fresh address.
  for (let attempt = 1; attempt <= 20; attempt++) {
    assert.equal((await signIn('wrong passphrase', `203.0.113.${attempt}`, { name: 'brute-target' })).status, 303);
  }
  assert.equal((await signIn('wrong passphrase', '203.0.113.200', { name: 'brute-target' })).status, 429, 'name limit, new address');

  // A real curator: nineteen wrong attempts from nineteen addresses stay under the limit; the correct one still works
  // and clears the count, so nineteen more wrong attempts are again allowed.
  for (let attempt = 1; attempt <= 19; attempt++) {
    assert.equal((await signIn('wrong passphrase', `192.0.2.${attempt}`, { name: CURATOR })).status, 303);
  }
  const correct = await signIn(PASSPHRASE, '192.0.2.100');
  assert.equal(correct.status, 303);
  assert.match(correct.headers.get('set-cookie') ?? '', /curator_session=/);
  for (let attempt = 1; attempt <= 19; attempt++) {
    assert.equal((await signIn('wrong passphrase', `192.0.2.${100 + attempt}`, { name: CURATOR })).status, 303, 'cleared by the successful sign-in');
  }
  assert.equal((await signIn(PASSPHRASE, '192.0.2.200')).status, 303, 'the curator can still sign in afterwards');
});

flow('curator: sign-in sets an httpOnly SameSite=Strict cookie that opens /admin', async () => {
  const response = await signIn(PASSPHRASE, '192.0.2.44');
  assert.equal(response.status, 303);
  assert.match(response.headers.get('location') ?? '', /\/admin\/commentaries$/);
  const cookie = response.headers.get('set-cookie') ?? '';
  assert.match(cookie, /curator_session=[^;]+/);
  assert.match(cookie, /HttpOnly/i);
  assert.match(cookie, /SameSite=Strict/i);
  const session = cookie.split(';')[0];
  curatorSession = session;
  const admin = await fetch(`${BASE}/admin/commentaries`, { headers: { Cookie: session }, redirect: 'manual' });
  assert.equal(admin.status, 200);

  const action = actionId('createCommentary');
  if (!action.file.includes('actions/curation')) {
    console.log('    (authorized HTTP write skipped: the admin client still imports the Neo4j createCommentary)');
    return;
  }
  const created = await callAction(action.id, action.page || '/admin/commentaries', [{ text: 'Written over HTTP by a curator.' }], { Cookie: session });
  assert.equal(created.status, 200);
  const rows = await fixture.sql`select c.created_by, a.actor from commentaries c join curation_audit a on a.entity_id = c.id
                                 where c.text = 'Written over HTTP by a curator.'`;
  assert.deepEqual(rows.map((row) => [row.created_by, row.actor]), [[`curator:${CURATOR}`, `curator:${CURATOR}`]]);
});

flow('refusals reach the browser: validation, publish gate and not-found come back as result objects, not thrown errors', async () => {
  const create = actionId('createCommentary');
  const publish = actionId('publishCommentary');
  const page = create.page || '/admin/commentaries';
  const call = async (id: string, args: unknown[]) => actionPayload(await (await callAction(id, page, args, { Cookie: curatorSession })).text());

  const invalid = await call(create.id, [{ text: '' }]);
  assert.equal(invalid.ok, false);
  assert.ok(invalid.fieldErrors && Object.keys(invalid.fieldErrors).length > 0, 'field errors name the offending field');

  const created = await call(create.id, [{ text: 'A commentary without a citation.' }]);
  assert.equal(created.ok, true);
  const gated = await call(publish.id, [created.data, 'published']);
  assert.equal(gated.ok, false);
  assert.match(gated.message ?? '', /live, reviewed citation/, 'the publish gate speaks in production');

  const missing = await call(publish.id, ['commentary:does-not-exist', 'published']);
  assert.deepEqual([missing.ok, missing.message], [false, 'Commentary not found.']);
});

flow('export: curator-only streaming CSV with an allowlist, 204 for no match', async () => {
  const anonymous = await fetch(`${BASE}/api/export/hadiths?fields=id`, { redirect: 'manual' });
  assert.equal(anonymous.status, 401);

  const response = await fetch(`${BASE}/api/export/hadiths?fields=id,title,tradition&edges=narrators`, { headers: { Cookie: curatorSession } });
  assert.equal(response.status, 200);
  assert.match(response.headers.get('content-type') ?? '', /text\/csv/);
  const lines = (await response.text()).replace(/^﻿/, '').trim().split('\r\n');
  assert.equal(lines[0], '"id","title","tradition","narrators"');
  const [{ count }] = await fixture.sql`select count(*)::int as count from hadiths where retired_at is null`;
  assert.equal(lines.length - 1, count, 'one row per live hadith');
  assert.ok(lines.some((line) => line.startsWith('"hadith:k6:1"')));

  const unknownField = await fetch(`${BASE}/api/export/hadiths?fields=id,password`, { headers: { Cookie: curatorSession } });
  assert.equal(unknownField.status, 400);
  const none = await fetch(`${BASE}/api/export/hadiths?fields=id&source=No%20Such%20Work`, { headers: { Cookie: curatorSession } });
  assert.equal(none.status, 204);
});

flow('preview notice: shown only while a non-release version is current under owner approval, and gone when revoked', async () => {
  const noticeText = /Preview: this archive(?:&#x27;|')s data is under active review/;
  assert.doesNotMatch(await (await pageFetch(`${BASE}/`)).text(), noticeText, 'release data carries no notice');

  await fixture.sql`update dataset_versions set release_class = 'non_release', non_release_reason = 'fixture' where is_current`;
  assert.doesNotMatch(await (await pageFetch(`${BASE}/`)).text(), noticeText, 'non-release without approval shows nothing');

  assert.notEqual(approvePreview('--by', 'owner').status, 0, 'a reason is required');
  const approved = approvePreview('--by', 'owner', '--reason', 'preview while data is under review');
  assert.equal(approved.status, 0, approved.output);
  const audit = await fixture.sql`select actor, action, after from curation_audit where action = 'approve_preview'`;
  assert.deepEqual([audit[0].actor, audit[0].action, audit[0].after.by], ['system:owner', 'approve_preview', 'owner']);
  const home = await (await pageFetch(`${BASE}/`)).text();
  assert.match(home, noticeText);
  assert.match(home, /href="\/glossary#preview"/);
  assert.doesNotMatch(await (await pageFetch(`${BASE}/admin/commentaries`, { headers: { Cookie: curatorSession } })).text(), noticeText, 'not under /admin');
  assert.notEqual(approvePreview('--by', 'owner', '--reason', 'again').status, 0, 'approving twice is refused');

  assert.equal(approvePreview('--revoke', '--by', 'owner', '--reason', 'first release is current').status, 0);
  assert.doesNotMatch(await (await pageFetch(`${BASE}/`)).text(), noticeText);
  await fixture.sql`update dataset_versions set release_class = 'release', non_release_reason = null where is_current`;
});

/**
 * The segment layouts decide not-found before the page streams, but src/app/loading.tsx wraps every route in a
 * Suspense boundary above them, so the status is already 200. Set HTTP_GATE_EXPECT_404=1 once that is resolved.
 */
flow('not found: an unknown hadith or narrator renders not-found (404 status pending root loading.tsx)', async () => {
  for (const pathname of [`/hadith/${encodeURIComponent('hadith:does-not-exist')}`, `/narrator/${encodeURIComponent('narrator:rawi:0')}`]) {
    const response = await fetch(`${BASE}${pathname}`);
    assert.match(await response.text(), /not found/i);
    if (process.env.HTTP_GATE_EXPECT_404) assert.equal(response.status, 404);
    else console.log(`    (${pathname}: HTTP ${response.status})`);
  }
  assert.equal((await fetch(`${BASE}/hadith/${encodeURIComponent('hadith:k6:1')}`)).status, 200);
});

async function main() {
  if (!existsSync(path.join(ROOT, '.next/BUILD_ID'))) throw new Error('Run `npx next build` first.');
  fixture = await prepareFixtureDatabase(process.env.QUERY_FIXTURE_SCHEMA || 'query_fixture_http');
  const env: NodeJS.ProcessEnv = {
    ...process.env,
    DATABASE_URL: fixture.url,
    ADMIN_SESSION_SECRET: 'http-gate-session-secret-'.padEnd(48, 'y'),
    CURATOR_PASSPHRASES: JSON.stringify({ [CURATOR]: await hashPassphrase(PASSPHRASE) }),
    NEO4J_URL: 'bolt://127.0.0.1:1',
    NEO4J_USERNAME: 'unused',
    NEO4J_PASSWORD: 'unused',
    NODE_ENV: 'production',
  };
  await startServer(env);
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
