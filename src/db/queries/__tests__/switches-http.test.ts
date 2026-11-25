/**
 * AUTH_ENABLED and PRIVATE_PREVIEW through the public HTTP seam of a production build (`next start`), on the
 * fixture schema: auth off (default), private preview on, preview misconfigured, and SITE_URL as the only origin in
 * production. Requires `npx next build`.
 * Run: npx tsx --conditions=react-server src/db/queries/__tests__/switches-http.test.ts
 */
import assert from 'node:assert/strict';
import { spawn, spawnSync, type ChildProcess } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { prepareFixtureDatabase, type FixtureDatabase } from './fixture-database';
import { flow, runFlows } from './harness';
import { hashPassphrase } from '../../../lib/auth/passphrases';

const ROOT = path.resolve(__dirname, '../../../..');
const PORT = Number(process.env.SWITCHES_HTTP_PORT || 3927);
const BASE = `http://127.0.0.1:${PORT}`;
const CURATOR = 'preview-curator';
const PASSPHRASE = 'a throwaway preview passphrase';
const HIDDEN_REPORT = '/hadith/openiti/zaydi/zayd_0001%7C1%7CV01P059';
const HIDDEN_WORK = 'Musnad al-Imam Zayd ibn Ali';

let fixture: FixtureDatabase;

/** fetch that retries once when a kept-alive socket was closed by the server (as http-gate.test.ts does). */
const nativeFetch = globalThis.fetch;
globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
  try {
    return await nativeFetch(input, init);
  } catch {
    return nativeFetch(input, init);
  }
}) as typeof fetch;
let server: ChildProcess | undefined;
let baseEnv: NodeJS.ProcessEnv;

async function startServer(env: NodeJS.ProcessEnv): Promise<void> {
  server = spawn(process.execPath, [path.join(ROOT, 'node_modules/next/dist/bin/next'), 'start', '-p', String(PORT), '-H', '127.0.0.1'], {
    cwd: ROOT,
    env,
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  server.stderr?.on('data', (chunk) => process.env.HTTP_GATE_VERBOSE && process.stderr.write(chunk));
  for (let attempt = 0; attempt < 60; attempt++) {
    try {
      await fetch(`${BASE}/api/health`);
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
  server = undefined;
}

/** A mutating curation action that a public (non-admin) page bundles, so it can be posted without /admin. */
function publicCurationAction(): { id: string; page: string } | null {
  const manifest = JSON.parse(readFileSync(path.join(ROOT, '.next/server/server-reference-manifest.json'), 'utf8')) as {
    node: Record<string, { exportedName?: string; filename?: string; workers: Record<string, unknown> }>;
  };
  for (const [id, entry] of Object.entries(manifest.node)) {
    if (!/actions\/curation/.test(entry.filename ?? '')) continue;
    if (!/^(create|update|delete|publish|retire|set|add|remove)/.test(entry.exportedName ?? '')) continue;
    const page = Object.keys(entry.workers).find((worker) => !worker.startsWith('app/admin'));
    if (page) return { id, page: page.replace(/^app/, '').replace(/\/page$/, '') || '/' };
  }
  return null;
}

// ---- Phase 1: defaults (AUTH_ENABLED and PRIVATE_PREVIEW unset) --------------------------------------------------

flow('auth off: sign-in, auth API, admin and export answer 404, not a redirect or a form', async () => {
  for (const [method, pathname] of [
    ['GET', '/sign-in'],
    ['GET', '/admin'],
    ['GET', '/admin/commentaries'],
    ['POST', '/api/auth/sign-in'],
    ['POST', '/api/auth/sign-out'],
    ['GET', '/api/export/hadiths'],
  ] as const) {
    const response = await fetch(`${BASE}${pathname}`, { method, redirect: 'manual' });
    assert.equal(response.status, 404, `${method} ${pathname}`);
    assert.equal(response.headers.get('location'), null);
  }
});

flow('auth off: a curation action posted from a public page is refused with the result object', async () => {
  const action = publicCurationAction();
  if (!action) {
    console.log('    (no curation action is bundled by a public page; covered by browse-flows "switches")');
    return;
  }
  const response = await fetch(`${BASE}${action.page}`, {
    method: 'POST',
    redirect: 'manual',
    headers: { 'Next-Action': action.id, 'Content-Type': 'text/plain;charset=UTF-8', Accept: 'text/x-component' },
    body: JSON.stringify([{}]),
  });
  const text = await response.text();
  assert.doesNotMatch(text, /"ok":true/);
});

flow('auth off: no sign-in or admin link anywhere a reader goes', async () => {
  for (const pathname of ['/', '/collections', '/sources', '/hadith/k6/1']) {
    const html = await (await fetch(`${BASE}${pathname}`)).text();
    assert.doesNotMatch(html, /href="\/(sign-in|admin)/, pathname);
  }
});

flow('preview off: anonymous sees only public rows; an uncleared work is absent', async () => {
  const collections = await fetch(`${BASE}/collections`);
  assert.equal(collections.status, 200);
  const html = await collections.text();
  assert.ok(html.includes('Sahih Muslim'));
  assert.ok(!html.includes(HIDDEN_WORK), 'uncleared work listed publicly');
  assert.match(await (await fetch(`${BASE}${HIDDEN_REPORT}`)).text(), /not found/i);
  assert.equal(collections.headers.get('x-robots-tag'), null);
});

flow('addresses: the old ID URL redirects permanently to the new address, which serves the report', async () => {
  const legacy = await fetch(`${BASE}/hadith/${encodeURIComponent('hadith:k6:10008')}`, { redirect: 'manual' });
  assert.equal(legacy.status, 308);
  assert.equal(new URL(legacy.headers.get('location') ?? '', BASE).pathname, '/hadith/k6/10008');
  const report = await fetch(`${BASE}/hadith/k6/10008`);
  assert.equal(report.status, 200);
  const html = await report.text();
  assert.ok(html.includes('rel="prev"') || html.includes('rel="next"'), 'previous/next links');
  assert.ok(html.includes('Cite this report'));
});

flow('credit: a report page that shows text carries a source reference and the dataset version', async () => {
  for (const pathname of [
    '/hadith/k6/1',
    '/hadith/thaqalayn/00131e142163d4a8132e3552',
    '/hadith/openiti/ibadi/rabi_0002%7C2%7CV01P006',
    // The family view shows the same text (and every telling's) on its own route: it must credit it too.
    '/hadith/k6/1/chains',
    '/hadith/thaqalayn/00131e142163d4a8132e3552/chains',
  ]) {
    const html = await (await fetch(`${BASE}${pathname}`)).text();
    assert.match(html, /data-source-ref="(SUN|THQ|OITI)"/, pathname);
    assert.match(html, /data-source-ref="[A-Z0-9]+"[^>]*><span[^>]*>Text: </, `${pathname}: the text credit`);
    assert.match(html, /data-dataset-version="dv:query-fixture"/, pathname);
  }
  const sources = await (await fetch(`${BASE}/sources`)).text();
  for (const anchor of ['thq', 'oiti', 'sun', 'nmc', 'msd', 'k6i', 'rij', 'hkg', 'rwy']) assert.ok(sources.includes(`id="${anchor}"`), anchor);
});

flow('crawling: a release version is indexable, names its sitemap, and serves it', async () => {
  const robots = await (await fetch(`${BASE}/robots.txt`)).text();
  assert.match(robots, /Allow: \//);
  assert.match(robots, /Sitemap: .*\/sitemap\.xml/);
  assert.equal((await fetch(`${BASE}/sitemap.xml`)).status, 200);
  assert.doesNotMatch(await (await fetch(`${BASE}/collections`)).text(), /name="robots" content="noindex/);
});

flow('crawling: a non-release version is noindex and has no sitemap', async () => {
  await fixture.sql`update dataset_versions set release_class = 'non_release' where is_current`;
  try {
    assert.match(await (await fetch(`${BASE}/collections`)).text(), /<meta name="robots" content="noindex, nofollow"/);
    assert.doesNotMatch(await (await fetch(`${BASE}/robots.txt`)).text(), /Sitemap/);
    assert.equal((await fetch(`${BASE}/sitemap.xml`)).status, 404);
  } finally {
    await fixture.sql`update dataset_versions set release_class = 'release' where is_current`;
  }
});

// ---- Phase 2: PRIVATE_PREVIEW=1 with a configured curator --------------------------------------------------------

let session = '';

flow('preview on: restart with PRIVATE_PREVIEW=1 and a throwaway curator', async () => {
  stopServer();
  await startServer({
    ...baseEnv,
    PRIVATE_PREVIEW: '1',
    ADMIN_SESSION_SECRET: 'switches-http-session-secret-'.padEnd(48, 'q'),
    CURATOR_PASSPHRASES: JSON.stringify({ [CURATOR]: await hashPassphrase(PASSPHRASE) }),
  });
});

flow('preview on: anonymous is redirected to sign-in from every page; sign-in, health and robots stay open; all noindex', async () => {
  for (const pathname of ['/', '/collections', '/hadith/k6/1', '/sources', '/narrator', HIDDEN_REPORT]) {
    const response = await fetch(`${BASE}${pathname}`, { redirect: 'manual' });
    assert.equal(response.status, 303, pathname);
    const location = new URL(response.headers.get('location') ?? '', BASE);
    assert.equal(location.pathname, '/sign-in');
    assert.equal(location.searchParams.get('next'), new URL(pathname, BASE).pathname);
    assert.equal(response.headers.get('x-robots-tag'), 'noindex, nofollow');
  }
  const post = await fetch(`${BASE}/collections`, { method: 'POST', redirect: 'manual', headers: { 'Next-Action': 'x' } });
  assert.equal(post.status, 401);
  for (const pathname of ['/sign-in', '/api/health', '/robots.txt']) {
    const response = await fetch(`${BASE}${pathname}`, { redirect: 'manual' });
    assert.equal(response.status, 200, pathname);
    assert.equal(response.headers.get('x-robots-tag'), 'noindex, nofollow', pathname);
  }
  assert.match(await (await fetch(`${BASE}/robots.txt`)).text(), /Disallow: \//);
});

flow('preview on: a curator signs in, returns to the page asked for, and sees unpublished rows under the banner', async () => {
  await fixture.sql`update collection_rights set rights_status = 'pending' where collection_id = 'collection:zaydi:musnad-zayd'`;
  const signIn = await fetch(`${BASE}/api/auth/sign-in`, {
    method: 'POST',
    redirect: 'manual',
    body: new URLSearchParams({ name: CURATOR, passphrase: PASSPHRASE, next: '/collections' }),
    headers: { 'X-Forwarded-For': '203.0.113.40' },
  });
  assert.equal(signIn.status, 303);
  assert.equal(new URL(signIn.headers.get('location') ?? '', BASE).pathname, '/collections');
  session = /curator_session=([^;]+)/.exec(signIn.headers.get('set-cookie') ?? '')?.[1] ?? '';
  assert.ok(session, 'session cookie');
  const headers = { Cookie: `curator_session=${session}` };
  const collections = await fetch(`${BASE}/collections`, { headers });
  assert.equal(collections.status, 200);
  assert.equal(collections.headers.get('x-robots-tag'), 'noindex, nofollow');
  const html = await collections.text();
  assert.ok(html.includes('Private curator preview'), 'banner');
  assert.ok(html.includes(HIDDEN_WORK), 'curator sees the uncleared work');
  const report = await fetch(`${BASE}${HIDDEN_REPORT}`, { headers });
  assert.equal(report.status, 200);
  assert.match(await report.text(), /data-source-ref="OITI"/);
});

// ---- Phase 3: PRIVATE_PREVIEW=1 without a working sign-in --------------------------------------------------------

flow('preview misconfigured: the server refuses to start', async () => {
  stopServer();
  const child = spawn(process.execPath, [path.join(ROOT, 'node_modules/next/dist/bin/next'), 'start', '-p', String(PORT + 1), '-H', '127.0.0.1'], {
    cwd: ROOT,
    env: { ...baseEnv, PRIVATE_PREVIEW: '1', ADMIN_SESSION_SECRET: '', CURATOR_PASSPHRASES: '' },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let output = '';
  child.stdout?.on('data', (chunk) => (output += chunk));
  child.stderr?.on('data', (chunk) => (output += chunk));
  const code = await new Promise<number | null>((resolve) => {
    const timer = setTimeout(() => {
      if (child.pid) spawnSync('taskkill', ['/pid', String(child.pid), '/T', '/F'], { stdio: 'ignore' });
      resolve(null);
    }, 30_000);
    child.on('exit', (exitCode) => {
      clearTimeout(timer);
      resolve(exitCode);
    });
  });
  assert.equal(code, 1, `expected exit 1, output: ${output.slice(-400)}`);
  assert.match(output, /Refusing to start: PRIVATE_PREVIEW=1 needs ADMIN_SESSION_SECRET/);
});

// ---- Phase 4: SITE_URL is the only origin in production (host-header injection) ---------------------------------

const SITE_PORT = PORT + 2;
const SITE_URL = 'https://archive.example.org';
const FORGED = 'attacker.example';

/** Starts `next start` on `port` and waits for /api/health, or returns the exit code when it refuses to start. */
async function startChild(env: NodeJS.ProcessEnv, port: number): Promise<{ child: ChildProcess; exitCode: number | null; output: () => string }> {
  const child = spawn(process.execPath, [path.join(ROOT, 'node_modules/next/dist/bin/next'), 'start', '-p', String(port), '-H', '127.0.0.1'], {
    cwd: ROOT,
    env,
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let output = '';
  child.stdout?.on('data', (chunk) => (output += chunk));
  child.stderr?.on('data', (chunk) => (output += chunk));
  let exitCode: number | null = null;
  child.on('exit', (code) => (exitCode = code ?? -1));
  for (let attempt = 0; attempt < 60 && exitCode === null; attempt++) {
    try {
      await nativeFetch(`http://127.0.0.1:${port}/api/health`);
      return { child, exitCode: null, output: () => output };
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 500));
    }
  }
  return { child, exitCode, output: () => output };
}

function killChild(child: ChildProcess): void {
  if (!child.pid || child.exitCode !== null) return;
  if (process.platform === 'win32') spawnSync('taskkill', ['/pid', String(child.pid), '/T', '/F'], { stdio: 'ignore' });
  else child.kill('SIGTERM');
}

/** GET with forged Host and X-Forwarded-* headers (node:http, since fetch will not send a custom Host). */
function forgedGet(port: number, pathname: string): Promise<{ status: number; location: string | null; body: string }> {
  return new Promise((resolve, reject) => {
    const request = http.request(
      {
        host: '127.0.0.1',
        port,
        path: pathname,
        headers: { Host: FORGED, 'X-Forwarded-Host': FORGED, 'X-Forwarded-Proto': 'http' },
      },
      (response) => {
        let body = '';
        response.setEncoding('utf8');
        response.on('data', (chunk) => (body += chunk));
        response.on('end', () => resolve({ status: response.statusCode ?? 0, location: response.headers.location ?? null, body }));
      },
    );
    request.on('error', reject);
    request.end();
  });
}

flow('site origin: forged Host and X-Forwarded-Host never reach the cite block, canonical link or a redirect', async () => {
  const started = await startChild({ ...baseEnv, SITE_URL }, SITE_PORT);
  try {
    assert.equal(started.exitCode, null, `server did not start: ${started.output().slice(-400)}`);
    const report = await forgedGet(SITE_PORT, '/hadith/k6/10008');
    assert.equal(report.status, 200);
    assert.ok(report.body.includes(`rel="canonical" href="${SITE_URL}/hadith/k6/10008"`), 'canonical link uses SITE_URL');
    assert.ok(report.body.includes(`${SITE_URL}/hadith/k6/10008. Accessed`), 'cite block address uses SITE_URL');
    assert.ok(!report.body.includes(FORGED), 'no forged host anywhere in the page');
    const legacy = await forgedGet(SITE_PORT, `/hadith/${encodeURIComponent('hadith:k6:10008')}`);
    assert.equal(legacy.status, 308);
    assert.equal(legacy.location, `${SITE_URL}/hadith/k6/10008`);
  } finally {
    killChild(started.child);
  }
});

flow('site origin: production without SITE_URL refuses to start', async () => {
  const started = await startChild({ ...baseEnv, SITE_URL: '' }, SITE_PORT + 1);
  killChild(started.child);
  assert.equal(started.exitCode, 1, `expected exit 1, output: ${started.output().slice(-400)}`);
  assert.match(started.output(), /Refusing to start: SITE_URL is not set/);
});

async function main() {
  if (!existsSync(path.join(ROOT, '.next/BUILD_ID'))) throw new Error('Run `npx next build` first.');
  fixture = await prepareFixtureDatabase(process.env.QUERY_FIXTURE_SCHEMA || 'switches_fixture_http');
  await fixture.sql`update collection_rights set rights_status = 'pending' where collection_id = 'collection:zaydi:musnad-zayd'`;
  baseEnv = {
    ...process.env,
    DATABASE_URL: fixture.url,
    AUTH_ENABLED: '',
    PRIVATE_PREVIEW: '',
    ADMIN_SESSION_SECRET: '',
    CURATOR_PASSPHRASES: '',
    SITE_URL: BASE,
    NODE_ENV: 'production',
  };
  await startServer(baseEnv);
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
