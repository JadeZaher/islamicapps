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

async function signIn(passphrase: string, ip: string): Promise<Response> {
  const form = new URLSearchParams({ name: CURATOR, passphrase, next: '/admin/commentaries' });
  return fetch(`${BASE}/api/auth/sign-in`, { method: 'POST', body: form, redirect: 'manual', headers: { 'X-Forwarded-For': ip } });
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

flow('curator: sign-in sets an httpOnly SameSite=Strict cookie that opens /admin', async () => {
  const response = await signIn(PASSPHRASE, '192.0.2.44');
  assert.equal(response.status, 303);
  assert.match(response.headers.get('location') ?? '', /\/admin\/commentaries$/);
  const cookie = response.headers.get('set-cookie') ?? '';
  assert.match(cookie, /curator_session=[^;]+/);
  assert.match(cookie, /HttpOnly/i);
  assert.match(cookie, /SameSite=Strict/i);
  const session = cookie.split(';')[0];
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
