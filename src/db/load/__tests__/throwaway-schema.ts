/** Builds a disposable copy of the load-relevant schema inside the development database, then drops it. */
import { randomBytes } from 'node:crypto';
import type { LoaderSql } from '../connection';
import { PIPELINE_TABLES, quoteIdentifier } from '../tables';

/** Tables the loader, the facet function, the views or the checks read, besides the pipeline tables. */
const SUPPORT_TABLES = [
  'dataset_versions',
  'collection_rights',
  'chain_absence_dispositions',
  'narrator_surface_decisions',
  'narrator_bios',
  'narrator_assessments',
  'historical_events',
  'cross_parallels',
  // 0019: read by narrator_transmissions (the per-work setting) and written by src/db/ops/chain-fix-apply.ts.
  'chain_fix_work_settings',
  'chain_fixes',
  'chain_fix_submissions',
  'chain_fix_decisions',
  'chain_fix_reviews',
  'chain_fix_applications',
];
/** Created in dependency order; definitions read from `public` so they track the migrations. */
const VIEWS = ['narrator_lifespans', 'public_hadiths', 'public_translations', 'public_chain_links'];
const FUNCTIONS = ['refresh_publication_facets', 'refresh_network'];

export function throwawaySchemaName(): string {
  return `load_test_${randomBytes(4).toString('hex')}`;
}

/** `admin` must be a client whose search_path is the default (`public` first). */
export async function createThrowawaySchema(admin: LoaderSql, schema: string): Promise<void> {
  const target = quoteIdentifier(schema);
  await admin.unsafe(`create schema ${target}`);
  for (const table of [...SUPPORT_TABLES, ...PIPELINE_TABLES.map((spec) => spec.name)]) {
    await admin.unsafe(`create table ${target}.${quoteIdentifier(table)} (like public.${quoteIdentifier(table)} including all)`);
  }
  // pg_get_viewdef prints names unqualified while public is on the search_path, so the definitions re-bind
  // to the throwaway tables when executed with the throwaway schema first.
  const definitions = new Map<string, string>();
  for (const view of [...VIEWS, 'narrator_transmissions']) {
    const [{ definition }] = await admin.unsafe<{ definition: string }[]>(
      `select pg_get_viewdef(to_regclass('public.' || $1), true) as definition`,
      [view],
    );
    definitions.set(view, definition);
  }
  const functionSources = new Map<string, string>();
  for (const name of FUNCTIONS) {
    const [{ source }] = await admin.unsafe<{ source: string }[]>(
      `select pg_get_functiondef(p.oid) as source from pg_proc p where p.pronamespace = 'public'::regnamespace and p.proname = $1`,
      [name],
    );
    const rebound = source
      .replace(`FUNCTION public.${name}(`, `FUNCTION ${target}.${name}(`)
      .replace(/SET search_path TO 'public', 'pg_temp'/, `SET search_path TO '${schema}', 'public', 'pg_temp'`);
    if (rebound === source || !rebound.includes(`'${schema}'`)) throw new Error(`could not re-bind function ${name}`);
    functionSources.set(name, rebound);
  }
  await admin.begin(async (transaction) => {
    const tx = transaction as unknown as LoaderSql;
    await tx.unsafe(`set local search_path = ${target}, public`);
    for (const view of VIEWS) {
      if (view === 'public_chain_links') continue;
      await tx.unsafe(`create view ${target}.${quoteIdentifier(view)} as ${definitions.get(view)}`);
    }
    await tx.unsafe(`create materialized view ${target}.narrator_transmissions as ${definitions.get('narrator_transmissions')}`);
    await tx.unsafe(`create unique index on ${target}.narrator_transmissions (student_id, teacher_id)`);
    await tx.unsafe(`create view ${target}.public_chain_links as ${definitions.get('public_chain_links')}`);
    for (const source of functionSources.values()) await tx.unsafe(source);
  });
}

export async function dropThrowawaySchema(admin: LoaderSql, schema: string): Promise<void> {
  if (!schema.startsWith('load_test_')) throw new Error(`refusing to drop non-test schema ${schema}`);
  await admin.unsafe(`drop schema if exists ${quoteIdentifier(schema)} cascade`);
}
