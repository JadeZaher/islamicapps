/** On-demand section 11.4 checks: `tsx src/db/load/verify-data-cli.ts [--bundle <projection dir>]`. Exits 1 on any failure. */
import { parseArgs } from 'node:util';
import { developmentDatabaseUrl, openLoaderClient } from './connection';
import { verifyProjection } from './manifest';
import { failedChecks, formatChecks, runDataChecks } from './verify-data';

async function main() {
  const { values } = parseArgs({ options: { bundle: { type: 'string' } } });
  const expectedLiveRows = values.bundle
    ? Object.fromEntries((await verifyProjection(values.bundle)).manifest.files.map((file) => [file.table, file.row_count]))
    : undefined;
  const sql = openLoaderClient(developmentDatabaseUrl());
  try {
    const report = await runDataChecks(sql, { expectedLiveRows });
    console.log(formatChecks(report));
    console.log(`\nreported: ${JSON.stringify(report.reported, null, 2)}`);
    const failures = failedChecks(report);
    if (failures.length > 0) {
      console.error(`\nFAIL: ${failures.length} data invariant(s) violated`);
      process.exitCode = 1;
    } else {
      console.log('\nOK: all section 11.4 data invariants hold');
    }
  } finally {
    await sql.end({ timeout: 5 });
  }
}

main().catch((error: unknown) => {
  console.error(`[verify-data] failed: ${error instanceof Error ? error.message : String(error)}`);
  process.exit(1);
});
