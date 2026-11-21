/** COPY FROM STDIN into UNLOGGED staging tables `load_<table>` (section 4.3 step 5). */
import { createReadStream } from 'node:fs';
import { pipeline } from 'node:stream/promises';
import type { LoaderSql } from './connection';
import { quoteIdentifier } from './tables';

export function stagingTableName(table: string): string {
  return quoteIdentifier(`load_${table}`);
}

/** Creates `load_<table>` with the live column types of `header`, then streams the CSV in. Returns rows staged. */
export async function stageTable(sql: LoaderSql, table: string, header: string[], csvPath: string): Promise<number> {
  const staging = stagingTableName(table);
  const columns = header.map(quoteIdentifier).join(', ');
  await sql.unsafe(`drop table if exists ${staging}`);
  await sql.unsafe(`create unlogged table ${staging} as select ${columns} from ${quoteIdentifier(table)} with no data`);
  // HEADER MATCH: the server itself rejects a CSV whose header names differ from the column list.
  const writable = await sql
    .unsafe(`copy ${staging} (${columns}) from stdin with (format csv, header match, encoding 'UTF8')`)
    .writable();
  await pipeline(createReadStream(csvPath), writable);
  const [{ staged }] = await sql.unsafe<{ staged: number }[]>(`select count(*)::int as staged from ${staging}`);
  return staged;
}

export async function dropStaging(sql: LoaderSql, tables: string[]): Promise<void> {
  for (const table of tables) await sql.unsafe(`drop table if exists ${stagingTableName(table)}`);
}
