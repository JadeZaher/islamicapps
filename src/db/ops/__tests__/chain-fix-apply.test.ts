/**
 * Flow test: a real slice loaded into a throwaway schema; one accepted fix applied, then reverted. After the revert the report's
 * chains, mentions and candidates equal the rows the application recorded (`base_rows`), column by column.
 * Run: npx tsx --test src/db/ops/__tests__/chain-fix-apply.test.ts   (needs DATABASE_URL and a projection with the 0019 columns)
 */
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { existsSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { after, before, test } from 'node:test';
import { chainSha256 } from '../../../../reviews/ai/tools/chain-fix-lib';
import { developmentDatabaseUrl, openLoaderClient, type LoaderSql } from '../../load/connection';
import { loadProjection } from '../../load/load';
import { createThrowawaySchema, dropThrowawaySchema, throwawaySchemaName } from '../../load/__tests__/throwaway-schema';
import { applyOverride, liveRows, revertFix, type Override } from '../chain-fix-apply';

const PROJECTION = process.env.CHAIN_FIX_TEST_PROJECTION ?? 'datasets/hadith-data/development/compiler-chain-fix-2026-11-22/projection';
const schema = throwawaySchemaName();
const FIX_ID = 'chain-fix:0123456789abcdef01234567';
let admin: LoaderSql;
let loader: LoaderSql;

before(async () => {
  assert.ok(existsSync(path.join(PROJECTION, 'canonical', 'manifest.json')), `no projection at ${PROJECTION}; set CHAIN_FIX_TEST_PROJECTION`);
  const output = path.join(mkdtempSync(path.join(tmpdir(), 'chain-fix-apply-')), 'slice');
  execFileSync('python', ['datasets/hadith-data/pg_export/slice_projection.py', '--projection', PROJECTION, '--output', output, '--per-tradition', '3'],
    { stdio: ['ignore', 'ignore', 'inherit'] });
  const databaseUrl = developmentDatabaseUrl();
  admin = openLoaderClient(databaseUrl);
  await createThrowawaySchema(admin, schema);
  loader = openLoaderClient(databaseUrl, schema);
  await loadProjection(loader, { projectionDirectory: output, loadPurpose: 'flow_test', loadedBy: 'system:chain-fix-apply-test', minimumLiveHadiths: 1 });
});

after(async () => {
  await loader?.end({ timeout: 5 });
  await dropThrowawaySchema(admin, schema);
  await admin?.end({ timeout: 5 });
});

test('an accepted fix is written as the model reading, feeds no list, and its revert restores the rows exactly', async () => {
  // A one-branch chain checked by rule whose positions 2 and 3 stand as a pair; the "reading" drops its second name.
  const [{ hadith_id: hadithId }] = await loader.unsafe<{ hadith_id: string }[]>(
    `select c.hadith_id from chains c
     join chain_mentions a on a.chain_id = c.id and a.position = 2 and a.narrator_id is not null
     join chain_mentions b on b.chain_id = c.id and b.position = 3 and b.narrator_id is not null
     where c.retired_at is null and c.structure_status = 'checked_by_rule' and c.length >= 4
       and not exists (select 1 from chains o where o.hadith_id = c.hadith_id and o.branch > 0 and o.retired_at is null)
     order by c.hadith_id limit 1`,
  );
  const pairsOf = async () => (await loader.unsafe<{ pairs: number }[]>(
    `select count(*)::int as pairs from narrator_transmissions t
     join chain_mentions a on a.narrator_id = t.student_id and a.hadith_id = $1 and a.retired_at is null
     join chain_mentions b on b.chain_id = a.chain_id and b.position = a.position + 1 and b.narrator_id = t.teacher_id`, [hadithId]))[0].pairs;
  await loader.unsafe('select refresh_network()');
  assert.ok((await pairsOf()) > 0, 'the rule-built chain feeds the lists before the fix');
  const [{ id: version }] = await loader.unsafe<{ id: string }[]>('select id from dataset_versions where is_current');
  const [{ arabic_sha256: arabicSha256 }] = await loader.unsafe<{ arabic_sha256: string }[]>('select arabic_sha256 from hadiths where id = $1', [hadithId]);
  const base = await liveRows(loader, hadithId);
  const chain = base.chains[0];
  const mentions = base.chain_mentions.filter((m) => m.chain_id === chain.id).sort((a, b) => Number(a.position) - Number(b.position));
  const kept = mentions.filter((_, position) => position !== 1);
  const prefix = String(chain.id).replace(/^chain:/, 'mention:');
  const override: Override = {
    hadith_id: hadithId,
    record_id: hadithId.replace(/^hadith:/, ''),
    fix_id: FIX_ID,
    arabic_sha256: arabicSha256,
    effect: 'replace_routes',
    structure_status: 'read_by_model',
    base_chain_sha256: chainSha256([{ chain_id: String(chain.id), branch: 0, structure_status: null,
      mentions: mentions.map((m) => ({ id: String(m.id), position: Number(m.position), surface_ar: String(m.surface_ar) })) }]),
    planned: {
      chains: [{
        id: String(chain.id), branch: 0, length: kept.length, suspension: null, extraction_method: 'chain_fix_reader',
        mentions: kept.map((m, position) => ({
          id: `${prefix}:${String(position).padStart(4, '0')}`, position, surface_ar: String(m.surface_ar), surface_normalized: String(m.surface_normalized),
          teacher_context_normalized: null, student_context_normalized: null, review_unit_id: String(m.review_unit_id),
          review_unit_fine_id: String(m.review_unit_fine_id), reader_kind: 'narrator', link_kind_if_new: 'unclassified', span: [0, 1],
          kept_mention_id: String(m.id), carry_identity: true,
        })),
      }],
    },
  };
  await loader.unsafe(`insert into chain_fixes (id, hadith_id, arabic_sha256, reader_text_sha256, text_layout, routes_key, fix_kinds, planned, created_by)
                       values ($1, $2, $3, $3, 'full_text', 'k', array['link_removed'], $4::text::jsonb, 'test')`,
    [FIX_ID, hadithId, arabicSha256, JSON.stringify(override.planned)]);

  await loader.begin(async (tx) => assert.equal(await applyOverride(tx as unknown as LoaderSql, override, version), true));
  const applied = await liveRows(loader, hadithId);
  assert.deepEqual(applied.chains.map((c) => [c.chain_fix_id, c.structure_status, c.length]), [[FIX_ID, 'read_by_model', kept.length]]);
  assert.equal(applied.chains[0].compiler_narrator_id, chain.compiler_narrator_id, 'the compiler head stays with the report');
  assert.equal(applied.chain_mentions.length, mentions.length - 1);
  // Carried names keep their identity (the engine decides who carries; here every kept name does).
  assert.deepEqual(applied.chain_mentions.map((m) => m.narrator_id), kept.map((m) => m.narrator_id));
  const [{ retired }] = await loader.unsafe<{ retired: number }[]>(
    `select count(*)::int as retired from chain_mentions where hadith_id = $1 and retired_at is not null`, [hadithId]);
  assert.equal(retired, 1, 'the dropped name is retired, never deleted');

  await loader.unsafe('select refresh_network()');
  // The work setting is off (0019 ships it off everywhere): the model reading, identities and all, feeds no list.
  assert.equal(await pairsOf(), 0, 'a chain read by model and awaiting review feeds no teacher or student list');

  await loader.begin(async (tx) => assert.equal(await revertFix(tx as unknown as LoaderSql, FIX_ID, version), hadithId));
  assert.deepEqual(await liveRows(loader, hadithId), base);
  const actions = await loader.unsafe<{ action: string }[]>('select action from chain_fix_applications where fix_id = $1 order by id', [FIX_ID]);
  assert.deepEqual(actions.map((row) => row.action), ['applied', 'reverted']);
});
