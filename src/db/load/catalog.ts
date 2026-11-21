/** Live-catalog reader: classifies every pipeline-table column so CSV headers can be checked exactly. */
import type { LoaderSql } from './connection';
import { PIPELINE_BOOKKEEPING_COLUMNS, PIPELINE_TABLES, type PipelineTableSpec } from './tables';

/** A live column and who writes it. */
export interface CatalogColumn {
  name: string;
  dataType: string;
  nullable: boolean;
  role: 'csv' | 'bookkeeping' | 'generated' | 'loader_derived';
}

export type Catalog = Record<string, CatalogColumn[]>;

/** Reads information_schema for the pipeline tables in the session's current schema. */
export async function readCatalog(sql: LoaderSql): Promise<Catalog> {
  const rows = await sql<
    { table_name: string; column_name: string; data_type: string; is_generated: string; is_nullable: string }[]
  >`
    select table_name, column_name, data_type, is_generated, is_nullable
    from information_schema.columns
    where table_schema = current_schema() and table_name = any(${PIPELINE_TABLES.map((table) => table.name)})
    order by table_name, ordinal_position`;
  const catalog: Catalog = {};
  for (const table of PIPELINE_TABLES) {
    const live = rows.filter((row) => row.table_name === table.name);
    if (live.length === 0) throw new Error(`catalog: table ${table.name} not found in current schema`);
    catalog[table.name] = live.map((row) => ({
      name: row.column_name,
      dataType: row.data_type,
      nullable: row.is_nullable === 'YES',
      role: classify(table, row.column_name, row.is_generated === 'ALWAYS'),
    }));
  }
  return catalog;
}

function classify(table: PipelineTableSpec, column: string, generated: boolean): CatalogColumn['role'] {
  if (generated) return 'generated';
  if ((PIPELINE_BOOKKEEPING_COLUMNS as readonly string[]).includes(column)) return 'bookkeeping';
  if (table.loaderDerived.includes(column)) return 'loader_derived';
  return 'csv';
}

/** Exact header check: the CSV columns must equal the live `csv` columns as a set. Returns mismatch messages. */
export function headerMismatches(catalog: Catalog, table: string, header: string[]): string[] {
  const expected = new Set((catalog[table] ?? []).filter((column) => column.role === 'csv').map((column) => column.name));
  const actual = new Set(header);
  const problems: string[] = [];
  if (actual.size !== header.length) problems.push(`${table}: duplicate CSV column`);
  for (const name of actual) if (!expected.has(name)) problems.push(`${table}: CSV column ${name} is not a live loadable column`);
  for (const name of expected) if (!actual.has(name)) problems.push(`${table}: live column ${name} missing from CSV`);
  return problems;
}
