/** Writes the live pipeline-table catalog as JSON for `export_postgres.py --catalog`. Usage: tsx src/db/load/dump-catalog.ts <out.json> */
import { writeFileSync } from 'node:fs';
import { readCatalog } from './catalog';
import { developmentDatabaseUrl, openLoaderClient } from './connection';

async function main() {
  const outputPath = process.argv[2];
  if (!outputPath) throw new Error('usage: tsx src/db/load/dump-catalog.ts <out.json>');
  const sql = openLoaderClient(developmentDatabaseUrl());
  try {
    const catalog = await readCatalog(sql);
    writeFileSync(outputPath, `${JSON.stringify(catalog, null, 2)}\n`, 'utf8');
    console.log(`[catalog] ${Object.keys(catalog).length} pipeline tables written to ${outputPath}`);
  } finally {
    await sql.end({ timeout: 5 });
  }
}

main().catch((error: unknown) => {
  console.error(`[catalog] failed: ${error instanceof Error ? error.message : String(error)}`);
  process.exit(1);
});
