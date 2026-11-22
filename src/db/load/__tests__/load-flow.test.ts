/**
 * Flow test: real rows from the four traditions, loaded into a throwaway schema of the development database.
 * Run: npx tsx --test src/db/load/__tests__/load-flow.test.ts   (needs DATABASE_URL and a full projection)
 */
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { existsSync, mkdtempSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { after, before, test } from 'node:test';
import { developmentDatabaseUrl, openLoaderClient, type LoaderSql } from '../connection';
import { loadProjection } from '../load';
import { createThrowawaySchema, dropThrowawaySchema, throwawaySchemaName } from './throwaway-schema';

const PROJECTION = process.env.LOAD_TEST_PROJECTION ?? 'datasets/hadith-data/development/openiti-fix-2026-11-21/projection-v5';
const SLICER = 'datasets/hadith-data/pg_export/slice_projection.py';

interface Expectations {
  content_sha256: string;
  rows: Record<string, number>;
  hadiths_by_tradition: Record<string, number>;
  chain: { id: string; surfaces: string[] };
  omitted_hadith: string | null;
  changed_hadith: string | null;
  correspondence_pair: string | null;
  hadith_ids: string[];
  hadiths_with_chains: string[];
}

function slice(output: string, omitHadith?: string, changeHadith?: string): Expectations {
  const args = [SLICER, '--projection', PROJECTION, '--output', output, '--per-tradition', '3'];
  if (omitHadith) args.push('--omit-hadith', omitHadith);
  if (changeHadith) args.push('--change-hadith', changeHadith);
  execFileSync('python', args, { stdio: ['ignore', 'ignore', 'inherit'] });
  return JSON.parse(readFileSync(path.join(output, 'expectations.json'), 'utf8')) as Expectations;
}

// A missing projection fails the test: a skipped flow test reads as a pass and hides a broken loader.
const projectionExists = existsSync(path.join(PROJECTION, 'canonical', 'manifest.json'));
const schema = throwawaySchemaName();
let admin: LoaderSql;
let loader: LoaderSql;
let first: Expectations;
let second: Expectations;
let firstDirectory: string;
let secondDirectory: string;

before(async () => {
  assert.ok(projectionExists, `no projection at ${PROJECTION}: build it (pg_export/AGENTS.md) or set LOAD_TEST_PROJECTION`);
  const workspace = mkdtempSync(path.join(tmpdir(), 'load-flow-'));
  firstDirectory = path.join(workspace, 'slice-a');
  first = slice(firstDirectory);
  // The second bundle omits one Sunni hadith that has a chain (its chain, mentions and English must retire) and
  // changes one other hadith's category (one updated row, everything else untouched).
  const omitted = first.hadiths_with_chains.find((id) => id.startsWith('hadith:k6:'))!;
  const changed = first.hadith_ids.find((id) => id !== omitted && id.startsWith('hadith:thaqalayn:'))!;
  secondDirectory = path.join(workspace, 'slice-b');
  second = slice(secondDirectory, omitted, changed);
  const databaseUrl = developmentDatabaseUrl();
  admin = openLoaderClient(databaseUrl);
  await createThrowawaySchema(admin, schema);
  loader = openLoaderClient(databaseUrl, schema);
});

after(async () => {
  await loader?.end({ timeout: 5 });
  await dropThrowawaySchema(admin, schema);
  await admin?.end({ timeout: 5 });
});

const options = (projectionDirectory: string) => ({
  projectionDirectory,
  loadPurpose: 'flow_test',
  loadedBy: 'system:load-flow-test',
  minimumLiveHadiths: 1,
});

test('a real four-tradition slice loads, reloads unchanged, and retires what a later bundle omits', async () => {
  // First load: every table gets exactly the slice's rows; the version becomes current and complete.
  const loaded = await loadProjection(loader, options(firstDirectory));
  assert.equal(loaded.mode, 'new');
  for (const [table, rows] of Object.entries(first.rows)) {
    const [{ live }] = await loader.unsafe<{ live: number }[]>(`select count(*)::int as live from "${table}" where retired_at is null`);
    assert.equal(live, rows, `${table} live rows`);
  }
  const byTradition = await loader.unsafe<{ tradition_id: string; n: number }[]>(
    'select tradition_id, count(*)::int as n from hadiths group by 1 order by 1',
  );
  assert.deepEqual(Object.fromEntries(byTradition.map((row) => [row.tradition_id, row.n])), first.hadiths_by_tradition);
  assert.equal(Object.keys(first.hadiths_by_tradition).length, 4, 'all four traditions present');

  // A chain reads back in order, surfaces byte for byte.
  const chain = await loader.unsafe<{ position: number; surface_ar: string }[]>(
    'select position, surface_ar from chain_mentions where chain_id = $1 order by position',
    [first.chain.id],
  );
  assert.deepEqual(chain.map((row) => row.surface_ar), first.chain.surfaces);
  assert.deepEqual(chain.map((row) => row.position), first.chain.surfaces.map((_, index) => index));

  // Facets were computed, and nothing is public without a rights decision.
  const [{ extraction_failed_with_chain }] = await loader.unsafe<{ extraction_failed_with_chain: number }[]>(
    `select count(*)::int as extraction_failed_with_chain from hadiths h
     where h.chain_status = 'extraction_failed' and exists (select 1 from chains c where c.hadith_id = h.id)`,
  );
  assert.equal(extraction_failed_with_chain, 0);
  const [{ visible }] = await loader.unsafe<{ visible: number }[]>('select count(*)::int as visible from public_hadiths');
  assert.equal(visible, 0);

  // Identity candidates loaded with the slice; a disagreement keeps both identities and settles neither. A kunya-only
  // candidate is a label, never a disagreement (owner decision 2026-11-21), so it is left out of the count.
  const [{ differing, differing_verified }] = await loader.unsafe<{ differing: number; differing_verified: number }[]>(
    `with differing as (select mention_id from chain_mention_candidates where retired_at is null and basis <> 'name_kunya_only'
                        group by mention_id having count(distinct narrator_id) > 1)
     select count(*)::int as differing,
            count(m.narrator_id)::int as differing_verified
     from differing d join chain_mentions m on m.id = d.mention_id`,
  );
  assert.ok(differing > 0, 'the slice includes a mention whose candidates disagree');
  assert.equal(differing_verified, 0);

  // The cross-tradition correspondence pair loaded with both Arabic hashes bound to the loaded texts.
  assert.ok(first.correspondence_pair, 'the slice includes a cross-tradition correspondence pair');
  const [pair] = await loader.unsafe<{ bound: boolean; scope: string }[]>(
    `select (c.arabic_sha256_a = a.arabic_sha256 and c.arabic_sha256_b = b.arabic_sha256) as bound, c.scope::text
     from report_correspondence_candidates c join hadiths a on a.id = c.hadith_id_a join hadiths b on b.id = c.hadith_id_b
     where c.id = $1`,
    [first.correspondence_pair],
  );
  assert.deepEqual(pair, { bound: true, scope: 'cross_tradition' });

  // Reloading the same bundle changes zero rows.
  const reloaded = await loadProjection(loader, options(firstDirectory));
  assert.equal(reloaded.mode, 'reload');
  assert.equal(reloaded.rowsChanged, 0);

  // A bundle that omits one hadith retires it and its dependents; nothing is deleted.
  const omitted = second.omitted_hadith!;
  const third = await loadProjection(loader, options(secondDirectory));
  assert.equal(third.mode, 'new');
  const [hadith] = await loader.unsafe<{ retired_at: Date | null; retired_in_dataset_version_id: string | null }[]>(
    'select retired_at, retired_in_dataset_version_id from hadiths where id = $1',
    [omitted],
  );
  assert.ok(hadith.retired_at, 'omitted hadith is retired');
  assert.equal(hadith.retired_in_dataset_version_id, second.content_sha256);
  const [{ live_dependents, retired_dependents }] = await loader.unsafe<{ live_dependents: number; retired_dependents: number }[]>(
    `select (select count(*) from chains where hadith_id = $1 and retired_at is null)
          + (select count(*) from chain_mentions where hadith_id = $1 and retired_at is null)
          + (select count(*) from translations where hadith_id = $1 and retired_at is null) as live_dependents,
            (select count(*) from chains where hadith_id = $1 and retired_at is not null)
          + (select count(*) from chain_mentions where hadith_id = $1 and retired_at is not null) as retired_dependents`,
    [omitted],
  );
  assert.equal(Number(live_dependents), 0);
  assert.ok(Number(retired_dependents) > 0, 'the omitted hadith had a chain that is now retired');
  const hadithMerge = third.merge.find((entry) => entry.table === 'hadiths')!;
  assert.deepEqual([hadithMerge.inserted, hadithMerge.updated, hadithMerge.retired], [0, 1, 1]);
  const [{ category, changed_in }] = await loader.unsafe<{ category: string; changed_in: string }[]>(
    'select category, changed_in_dataset_version_id as changed_in from hadiths where id = $1',
    [second.changed_hadith],
  );
  assert.match(category, /\[changed by slice\]$/);
  assert.equal(changed_in, second.content_sha256);
  // Only the changed row and the omitted report's dependents moved; unrelated tables are untouched.
  for (const entry of third.merge.filter((merge) => ['narrators', 'collections', 'traditions'].includes(merge.table))) {
    assert.equal(entry.inserted + entry.updated + entry.retired, 0, `${entry.table} untouched`);
  }
  const [{ current }] = await loader.unsafe<{ current: string }[]>('select id as current from dataset_versions where is_current');
  assert.equal(current, second.content_sha256);
});
