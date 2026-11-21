/** `npm run db:load -- --bundle <projection dir> [--purpose <text>] [--report <file.json>]`. See src/db/load/AGENTS.md. */
import { writeFileSync } from 'node:fs';
import { parseArgs } from 'node:util';
import { developmentDatabaseUrl, openLoaderClient } from './connection';
import { loadProjection } from './load';
import { formatChecks } from './verify-data';

async function main() {
  const { values } = parseArgs({
    options: {
      bundle: { type: 'string' },
      purpose: { type: 'string', default: 'development_load' },
      report: { type: 'string' },
    },
  });
  if (!values.bundle) throw new Error('usage: npm run db:load -- --bundle <projection directory>');
  const sql = openLoaderClient(developmentDatabaseUrl());
  const started = Date.now();
  try {
    const result = await loadProjection(sql, {
      projectionDirectory: values.bundle,
      loadPurpose: values.purpose!,
      loadedBy: 'system:db-load',
      log: (message) => console.log(`[load] ${message}`),
    });
    console.log(`\n${formatChecks(result.checks)}`);
    console.log(
      `\n[load] ${result.mode} version ${result.versionId}: ${result.rowsChanged} rows changed ` +
        `(facets ${result.facetRowsChanged}), network refreshed: ${result.networkRefreshed}, ${Date.now() - started} ms`,
    );
    if (values.report) {
      writeFileSync(values.report, `${JSON.stringify({ ...result, elapsedMs: Date.now() - started }, null, 2)}\n`, 'utf8');
    }
  } finally {
    await sql.end({ timeout: 5 });
  }
}

main().catch((error: unknown) => {
  console.error(`[load] failed: ${error instanceof Error ? error.message : String(error)}`);
  process.exit(1);
});
