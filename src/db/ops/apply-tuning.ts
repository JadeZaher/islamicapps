/**
 * Applies src/db/ops/railway-tuning.sql with ALTER SYSTEM (outside any transaction), reloads the configuration and
 * prints which settings still wait for a restart. Never restarts the server. Needs an explicit target:
 *
 *   npx tsx src/db/ops/apply-tuning.ts --database production --confirm-production
 *
 * See src/db/AGENTS.md §Server tuning.
 */
import { readFileSync } from 'node:fs';
import path from 'node:path';
import postgres from 'postgres';
import { connectionOptions } from '../connection-options';
import { resolveTargetDatabase } from '../target-database';

/** `alter system set <name> = <value>` statements of the operator file, comments removed. */
export function tuningStatements(source: string): string[] {
  return source
    .split('\n')
    .map((line) => line.replace(/--.*$/, '').trim())
    .filter((line) => line.length > 0)
    .join(' ')
    .split(';')
    .map((statement) => statement.trim())
    .filter((statement) => /^alter system set [a-z_]+ = /i.test(statement));
}

async function main() {
  const target = resolveTargetDatabase(process.argv, { required: true });
  const statements = tuningStatements(readFileSync(path.resolve('src/db/ops/railway-tuning.sql'), 'utf8'));
  const names = statements.map((statement) => statement.split(/\s+/)[3]);
  const sql = postgres(target.url, { ...connectionOptions(target.url, 1), onnotice: () => {} });
  try {
    for (const statement of statements) await sql.unsafe(statement);
    await sql`select pg_reload_conf()`;
    await new Promise((resolve) => setTimeout(resolve, 1_000));
    const rows = await sql<{ name: string; setting: string; unit: string | null; context: string; pending_restart: boolean }[]>`
      select name, setting, unit, context, pending_restart from pg_settings where name = any(${names}) order by name`;
    console.log(`Applied ${statements.length} settings on the ${target.name} server (reloaded, not restarted):`);
    for (const row of rows) {
      console.log(`  ${row.name.padEnd(32)} ${`${row.setting}${row.unit ? ` ${row.unit}` : ''}`.padEnd(14)} ${row.context}${row.pending_restart ? '  RESTART PENDING' : ''}`);
    }
  } finally {
    await sql.end({ timeout: 5 });
  }
}

if (/apply-tuning\.ts$/.test(process.argv[1] ?? '')) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.message : error);
    process.exit(1);
  });
}
