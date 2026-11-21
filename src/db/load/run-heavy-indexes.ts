/**
 * Runs src/db/ops/indexes-heavy.sql outside any transaction (CREATE INDEX CONCURRENTLY), then prints sizes.
 * Development by default; `--database production --confirm-production` for the live database.
 */
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { resolveTargetDatabase } from '../target-database';
import { openLoaderClient } from './connection';

/** Splits the operator file into statements; it holds no functions or quoted semicolons. */
function statements(source: string): string[] {
  return source
    .split('\n')
    .filter((line) => !line.trim().startsWith('--'))
    .join('\n')
    .split(';')
    .map((statement) => statement.trim())
    .filter((statement) => statement.length > 0);
}

async function main() {
  const target = resolveTargetDatabase(process.argv, { required: false });
  console.log(`[heavy-indexes] target: ${target.name} database`);
  const sql = openLoaderClient(target.url);
  try {
    await sql.unsafe('set statement_timeout = 0');
    for (const statement of statements(readFileSync(path.resolve('src/db/ops/indexes-heavy.sql'), 'utf8'))) {
      const started = Date.now();
      await sql.unsafe(statement);
      console.log(`[heavy-indexes] ${statement.split('\n')[0]} (${Date.now() - started} ms)`);
    }
    const [index] = await sql.unsafe<{ size: string; valid: boolean }[]>(
      `select pg_size_pretty(pg_relation_size('hadiths_text_ar_normalized_trgm_idx')) as size, i.indisvalid as valid
       from pg_index i where i.indexrelid = 'hadiths_text_ar_normalized_trgm_idx'::regclass`,
    );
    console.log(`[heavy-indexes] hadiths_text_ar_normalized_trgm_idx: ${index.size}, valid=${index.valid}`);
  } finally {
    await sql.end({ timeout: 5 });
  }
}

main().catch((error: unknown) => {
  console.error(`[heavy-indexes] failed: ${error instanceof Error ? error.message : String(error)}`);
  process.exit(1);
});
