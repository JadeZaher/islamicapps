/** Catalog verification: the live database matches src/db/schema and the hand-written migrations. Exits 1 on mismatch. */
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { config as loadEnvironment } from 'dotenv';
import { is } from 'drizzle-orm';
import {
  PgMaterializedView,
  PgTable,
  PgView,
  getMaterializedViewConfig,
  getTableConfig,
  getViewConfig,
  isPgEnum,
  type PgColumn,
} from 'drizzle-orm/pg-core';
import postgres from 'postgres';
import { connectionOptions, requireDatabaseUrl } from './connection-options';
import * as schema from './schema';

/**
 * 40 launch tables, chain_mention_candidates (0006), the three report-correspondence tables (0007), epochs (0008) and
 * narrator_source_profiles, narrator_external_ids, narrator_link_candidates (0010).
 * Views: the 5 launch views, public_chain_mention_candidates (0006), report_correspondence_shown_pairs,
 * report_correspondence_display and public_report_correspondences (0007), published_epochs (0008) and
 * public_chain_mention_candidates_v2 (0011).
 */
const EXPECTED_TABLE_COUNT = 48;
const EXPECTED_VIEW_COUNT = 11;
const EXPECTED_MATERIALIZED_VIEW_COUNT = 1;
const REQUIRED_EXTENSIONS = ['pg_trgm', 'unaccent'];
/** Indexes created by hand-written migrations, not by drizzle-kit. */
const HAND_WRITTEN_INDEXES = ['narrator_transmissions_pair_key', 'narrator_transmissions_teacher_id_idx'];
/** Built by src/db/ops/indexes-heavy.sql after a load; allowed but not required. */
const OPTIONAL_INDEXES = ['hadiths_text_ar_normalized_trgm_idx'];
const FILLFACTOR_90_TABLES = ['hadiths', 'chains', 'chain_mentions'];
const EXPECTED_FUNCTIONS: Record<string, { securityDefiner: boolean }> = {
  refresh_publication_facets: { securityDefiner: false },
  refresh_network: { securityDefiner: true },
};

const failures: string[] = [];
function expect(condition: boolean, message: string) {
  if (!condition) failures.push(message);
}
function sameSet(label: string, expected: Iterable<string>, actual: Iterable<string>) {
  const expectedSet = new Set(expected);
  const actualSet = new Set(actual);
  for (const name of expectedSet) expect(actualSet.has(name), `${label}: missing ${name}`);
  for (const name of actualSet) expect(expectedSet.has(name), `${label}: unexpected ${name}`);
}

const schemaObjects = Object.values(schema) as unknown[];
const tables = schemaObjects.filter((value): value is PgTable => is(value, PgTable)).map(getTableConfig);
const views = schemaObjects.filter((value): value is PgView => is(value, PgView)).map(getViewConfig);
const materializedViews = schemaObjects
  .filter((value): value is PgMaterializedView => is(value, PgMaterializedView))
  .map(getMaterializedViewConfig);
const enums = schemaObjects.filter(isPgEnum);

function columnNames(fields: Record<string, unknown>): string[] {
  return Object.values(fields).map((column) => (column as PgColumn).name);
}

async function main() {
  loadEnvironment({ path: '.env.local', quiet: true });
  const databaseUrl = requireDatabaseUrl();
  const sql = postgres(databaseUrl, connectionOptions(databaseUrl, 1));
  try {
    // Extensions.
    const extensionRows = await sql<{ extname: string; extversion: string }[]>`
      select extname, extversion from pg_extension order by extname`;
    const installed = new Map(extensionRows.map((row) => [row.extname, row.extversion]));
    for (const extension of REQUIRED_EXTENSIONS) expect(installed.has(extension), `extension missing: ${extension}`);

    // Relations in public.
    const relationRows = await sql<{ relname: string; relkind: string }[]>`
      select c.relname, c.relkind from pg_class c join pg_namespace n on n.oid = c.relnamespace
      where n.nspname = 'public' and c.relkind in ('r', 'p', 'v', 'm')`;
    const byKind = (kinds: string[]) => relationRows.filter((row) => kinds.includes(row.relkind)).map((row) => row.relname);
    const actualTables = byKind(['r', 'p']);
    const actualViews = byKind(['v']);
    const actualMaterializedViews = byKind(['m']);
    expect(tables.length === EXPECTED_TABLE_COUNT, `schema declares ${tables.length} tables, expected ${EXPECTED_TABLE_COUNT}`);
    expect(actualTables.length === EXPECTED_TABLE_COUNT, `database has ${actualTables.length} tables, expected ${EXPECTED_TABLE_COUNT}`);
    expect(actualViews.length === EXPECTED_VIEW_COUNT, `database has ${actualViews.length} views, expected ${EXPECTED_VIEW_COUNT}`);
    expect(
      actualMaterializedViews.length === EXPECTED_MATERIALIZED_VIEW_COUNT,
      `database has ${actualMaterializedViews.length} materialized views, expected ${EXPECTED_MATERIALIZED_VIEW_COUNT}`,
    );
    sameSet('tables', tables.map((table) => table.name), actualTables);
    sameSet('views', views.map((view) => view.name), actualViews);
    sameSet('materialized views', materializedViews.map((view) => view.name), actualMaterializedViews);

    // Columns: name, SQL type, nullability, generated (tables); names (views).
    const columnRows = await sql<
      { relname: string; attname: string; sql_type: string; not_null: boolean; generated: string }[]
    >`
      select c.relname, a.attname, format_type(a.atttypid, a.atttypmod) as sql_type,
             a.attnotnull as not_null, a.attgenerated as generated
      from pg_attribute a
      join pg_class c on c.oid = a.attrelid
      join pg_namespace n on n.oid = c.relnamespace
      where n.nspname = 'public' and c.relkind in ('r', 'p', 'v', 'm') and a.attnum > 0 and not a.attisdropped`;
    const columnsByRelation = new Map<string, Map<string, (typeof columnRows)[number]>>();
    for (const row of columnRows) {
      if (!columnsByRelation.has(row.relname)) columnsByRelation.set(row.relname, new Map());
      columnsByRelation.get(row.relname)!.set(row.attname, row);
    }
    let columnCount = 0;
    for (const table of tables) {
      const actual = columnsByRelation.get(table.name) ?? new Map();
      sameSet(`columns of ${table.name}`, table.columns.map((column) => column.name), actual.keys());
      for (const column of table.columns) {
        const row = actual.get(column.name);
        if (!row) continue;
        columnCount += 1;
        const expectedType = column.getSQLType().replace(/"/g, '');
        expect(row.sql_type === expectedType, `${table.name}.${column.name}: type ${row.sql_type}, expected ${expectedType}`);
        expect(row.not_null === column.notNull, `${table.name}.${column.name}: not null ${row.not_null}, expected ${column.notNull}`);
        const expectGenerated = column.generated !== undefined;
        expect((row.generated === 's') === expectGenerated, `${table.name}.${column.name}: generated mismatch`);
      }
    }
    for (const view of [...views, ...materializedViews]) {
      const actual = columnsByRelation.get(view.name) ?? new Map();
      sameSet(`columns of view ${view.name}`, columnNames(view.selectedFields), actual.keys());
    }

    // Constraints: primary keys, unique, foreign keys (with on delete restrict), checks.
    const constraintRows = await sql<
      {
        table_name: string;
        conname: string;
        contype: string;
        columns: string[];
        foreign_table: string | null;
        foreign_columns: string[] | null;
        on_delete: string;
      }[]
    >`
      select c.relname as table_name, con.conname, con.contype,
             array(select a.attname from unnest(con.conkey) with ordinality k(attnum, ord)
                   join pg_attribute a on a.attrelid = con.conrelid and a.attnum = k.attnum order by k.ord)::text[] as columns,
             fc.relname as foreign_table,
             case when con.contype = 'f' then
               array(select a.attname from unnest(con.confkey) with ordinality k(attnum, ord)
                     join pg_attribute a on a.attrelid = con.confrelid and a.attnum = k.attnum order by k.ord)::text[]
             end as foreign_columns,
             con.confdeltype as on_delete
      from pg_constraint con
      join pg_class c on c.oid = con.conrelid
      join pg_namespace n on n.oid = c.relnamespace
      left join pg_class fc on fc.oid = con.confrelid
      where n.nspname = 'public' and con.contype in ('p', 'u', 'f', 'c')`;
    const constraintsOf = (tableName: string, type: string) =>
      constraintRows.filter((row) => row.table_name === tableName && row.contype === type);

    let foreignKeyCount = 0;
    let checkCount = 0;
    let uniqueCount = 0;
    for (const table of tables) {
      // Primary key.
      const primaryKeys = constraintsOf(table.name, 'p');
      const declaredPrimary =
        table.primaryKeys[0]?.columns.map((column) => column.name) ??
        table.columns.filter((column) => column.primary).map((column) => column.name);
      expect(primaryKeys.length === 1, `${table.name}: ${primaryKeys.length} primary keys`);
      if (primaryKeys[0]) {
        expect(
          primaryKeys[0].columns.join(',') === declaredPrimary.join(','),
          `${table.name}: primary key (${primaryKeys[0].columns}) expected (${declaredPrimary})`,
        );
      }

      // Unique constraints.
      const actualUnique = constraintsOf(table.name, 'u');
      sameSet(
        `unique constraints of ${table.name}`,
        table.uniqueConstraints.map((constraint) => constraint.getName() ?? ''),
        actualUnique.map((row) => row.conname),
      );
      uniqueCount += actualUnique.length;

      // Foreign keys.
      const actualForeignKeys = new Map(constraintsOf(table.name, 'f').map((row) => [row.conname, row]));
      sameSet(
        `foreign keys of ${table.name}`,
        table.foreignKeys.map((foreignKey) => foreignKey.getName()),
        actualForeignKeys.keys(),
      );
      for (const foreignKey of table.foreignKeys) {
        const row = actualForeignKeys.get(foreignKey.getName());
        if (!row) continue;
        foreignKeyCount += 1;
        const reference = foreignKey.reference();
        const expectedForeignTable = getTableConfig(reference.foreignTable).name;
        const label = `${table.name}.${foreignKey.getName()}`;
        expect(row.columns.join(',') === reference.columns.map((c) => c.name).join(','), `${label}: columns ${row.columns}`);
        expect(row.foreign_table === expectedForeignTable, `${label}: references ${row.foreign_table}, expected ${expectedForeignTable}`);
        expect(
          (row.foreign_columns ?? []).join(',') === reference.foreignColumns.map((c) => c.name).join(','),
          `${label}: foreign columns ${row.foreign_columns}`,
        );
        expect(row.on_delete === 'r', `${label}: on delete '${row.on_delete}', expected restrict ('r')`);
      }

      // Checks.
      const actualChecks = constraintsOf(table.name, 'c');
      sameSet(`checks of ${table.name}`, table.checks.map((check) => check.name), actualChecks.map((row) => row.conname));
      checkCount += actualChecks.length;
    }

    // Indexes that are not backing a constraint.
    const indexRows = await sql<{ indexname: string; tablename: string }[]>`
      select i.relname as indexname, t.relname as tablename
      from pg_index x
      join pg_class i on i.oid = x.indexrelid
      join pg_class t on t.oid = x.indrelid
      join pg_namespace n on n.oid = t.relnamespace
      where n.nspname = 'public'
        and not exists (select 1 from pg_constraint con where con.conindid = x.indexrelid)`;
    const expectedIndexes = [
      ...tables.flatMap((table) => table.indexes.map((index) => index.config.name ?? '')),
      ...HAND_WRITTEN_INDEXES,
    ];
    const actualIndexes = indexRows.map((row) => row.indexname).filter((name) => !OPTIONAL_INDEXES.includes(name));
    sameSet('indexes', expectedIndexes, actualIndexes);

    // Enums: name and labels in order.
    const enumRows = await sql<{ typname: string; labels: string[] }[]>`
      select t.typname, array_agg(e.enumlabel order by e.enumsortorder)::text[] as labels
      from pg_type t join pg_enum e on e.enumtypid = t.oid
      join pg_namespace n on n.oid = t.typnamespace
      where n.nspname = 'public' group by t.typname`;
    const actualEnums = new Map(enumRows.map((row) => [row.typname, row.labels]));
    sameSet('enums', enums.map((enumType) => enumType.enumName), actualEnums.keys());
    for (const enumType of enums) {
      const labels = actualEnums.get(enumType.enumName);
      if (labels) {
        expect(labels.join(',') === enumType.enumValues.join(','), `enum ${enumType.enumName}: labels ${labels}`);
      }
    }

    // Functions.
    const functionRows = await sql<{ proname: string; prosecdef: boolean }[]>`
      select p.proname, p.prosecdef from pg_proc p join pg_namespace n on n.oid = p.pronamespace
      where n.nspname = 'public' and p.proname = any(${Object.keys(EXPECTED_FUNCTIONS)})`;
    for (const [name, { securityDefiner }] of Object.entries(EXPECTED_FUNCTIONS)) {
      const row = functionRows.find((candidate) => candidate.proname === name);
      expect(row !== undefined, `function missing: ${name}`);
      if (row) expect(row.prosecdef === securityDefiner, `function ${name}: security definer ${row.prosecdef}`);
    }

    // Storage parameters.
    const storageRows = await sql<{ relname: string; reloptions: string[] | null }[]>`
      select relname, reloptions from pg_class c join pg_namespace n on n.oid = c.relnamespace
      where n.nspname = 'public' and relname = any(${FILLFACTOR_90_TABLES})`;
    for (const tableName of FILLFACTOR_90_TABLES) {
      const row = storageRows.find((candidate) => candidate.relname === tableName);
      expect((row?.reloptions ?? []).includes('fillfactor=90'), `${tableName}: fillfactor=90 not set`);
    }

    // Applied migrations equal the journal.
    const journal = JSON.parse(readFileSync(path.resolve(process.cwd(), 'drizzle/core/meta/_journal.json'), 'utf8')) as {
      entries: unknown[];
    };
    const [{ applied }] = await sql<{ applied: number }[]>`select count(*)::int as applied from drizzle.__drizzle_migrations`;
    expect(applied === journal.entries.length, `applied migrations ${applied}, journal has ${journal.entries.length}`);

    // The verified-link predicate (0006) must not count name matches: exact_registry is a candidate, never a link.
    const [{ definition }] = await sql<{ definition: string }[]>`select pg_get_viewdef('public_chain_links'::regclass) as definition`;
    expect(!definition.includes('exact_registry'), 'public_chain_links still treats exact_registry as a verified link');
    expect(definition.includes('source_index'), 'public_chain_links does not treat confirmed source_index as a verified link');

    // The extended tier (0011): Riwayat's automatic linker and label-like records never carry it; the pre-0010 view keeps
    // only the bases a build before 0010 understands.
    const [{ tier }] = await sql<{ tier: string }[]>`select pg_get_viewdef('public_chain_mention_candidates_v2'::regclass) as tier`;
    expect(tier.includes("'riwayat_automatic_linking'") && tier.includes('label_reason IS NULL'),
      'public_chain_mention_candidates_v2 lets an automatic link or a label carry the machine-reviewed tier');
    const [{ legacy }] = await sql<{ legacy: string }[]>`select pg_get_viewdef('public_chain_mention_candidates'::regclass) as legacy`;
    expect(!legacy.includes('source_riwayat') && legacy.includes("'name_kunya_only'"),
      'public_chain_mention_candidates exposes bases added in 0010 to a build that predates them');

    // The correspondence display rule (0007): rejected pairs never shown, confirmed pairs always, decisions hash-bound.
    const [{ shown }] = await sql<{ shown: string }[]>`select pg_get_viewdef('report_correspondence_shown_pairs'::regclass) as shown`;
    expect(shown.includes("'rejected'") && shown.includes("'confirmed'"), 'report_correspondence_shown_pairs lost the reviewer-decision rule');
    expect(shown.includes('bound_arabic_sha256_a'), 'report_correspondence_shown_pairs no longer binds decisions to the Arabic');

    // The English publication rule (0009): machine English only under the new policy, unknown provenance never.
    const [{ english }] = await sql<{ english: string }[]>`select pg_get_viewdef('public_translations'::regclass) as english`;
    expect(english.includes("'machine_unreviewed'") && english.includes("'source_provided_and_machine_allowed'"),
      'public_translations does not carry the 0009 machine-English policy');
    expect(!english.includes('unknown_provenance'), 'public_translations exposes English of unknown provenance');
    expect(english.includes("'complete'") && english.includes('arabic_sha256'), 'public_translations lost the quality or hash gate');

    // The chain chronology guard (0013): symmetric impossibility, the 60-year bound and the repeated-narrator seam.
    const [{ network }] = await sql<{ network: string }[]>`select pg_get_viewdef('narrator_transmissions'::regclass) as network`;
    expect(network.includes('teacher born after student died') && network.includes('+ 60') && network.includes('first_pos'),
      'narrator_transmissions lost the 0013 chronology or seam guard');
    const [{ withheld }] = await sql<{ withheld: string }[]>`select pg_get_viewdef('public_chain_links'::regclass) as withheld`;
    expect(withheld.includes('identity_withheld_reason'), 'public_chain_links does not expose identity_withheld_reason');
    // The chain builder (0014): continuations name the written mention they repeat; the opening-isnad rule is a tier basis.
    expect(withheld.includes('inherited_from_mention_id'), 'public_chain_links does not expose inherited_from_mention_id');
    expect(tier.includes("'named_in_opening_isnad'"), 'public_chain_mention_candidates_v2 does not count named_in_opening_isnad');
    // 0015: chains say when they rely on another; an unnamed transmitter or a back-reference never stands in a pair.
    expect(withheld.includes('chain_suspension'), 'public_chain_links does not expose chain_suspension');
    expect(withheld.includes('chain_missing_link_after'), 'public_chain_links does not expose chain_missing_link_after');
    expect(tier.includes("'edition_identification'"), 'public_chain_mention_candidates_v2 does not count edition_identification');
    expect(network.includes("'anonymous'") && network.includes("'not_a_narrator'") && network.includes('first_pos'),
      'narrator_transmissions lost the 0015 anonymous-gap guard or the 0013 seam guard');

    console.log(
      [
        `server:              ${(await sql<{ version: string }[]>`select current_setting('server_version') as version`)[0].version}`,
        `extensions:          ${[...installed].map(([name, version]) => `${name} ${version}`).join(', ')}`,
        `tables:              ${actualTables.length} (expected ${EXPECTED_TABLE_COUNT})`,
        `views:               ${actualViews.length} (expected ${EXPECTED_VIEW_COUNT}): ${actualViews.sort().join(', ')}`,
        `materialized views:  ${actualMaterializedViews.length} (expected ${EXPECTED_MATERIALIZED_VIEW_COUNT}): ${actualMaterializedViews.join(', ')}`,
        `table columns:       ${columnCount} checked`,
        `foreign keys:        ${foreignKeyCount} present, all on delete restrict (schema declares ${tables.reduce((sum, table) => sum + table.foreignKeys.length, 0)})`,
        `unique constraints:  ${uniqueCount}`,
        `check constraints:   ${checkCount}`,
        `indexes (non-constraint): ${actualIndexes.length} (expected ${expectedIndexes.length})`,
        `enums:               ${actualEnums.size} (schema declares ${enums.length})`,
        `functions:           ${functionRows.map((row) => row.proname).sort().join(', ')}`,
        `migrations applied:  ${applied} of ${journal.entries.length}`,
      ].join('\n'),
    );
  } finally {
    await sql.end({ timeout: 5 });
  }

  if (failures.length > 0) {
    console.error(`\nFAIL: ${failures.length} mismatch(es)`);
    for (const failure of failures) console.error(`  - ${failure}`);
    process.exit(1);
  }
  console.log('\nOK: catalog matches src/db/schema and drizzle/core');
}

main().catch((error: unknown) => {
  console.error(`[verify] failed: ${error instanceof Error ? error.message : String(error)}`);
  process.exit(1);
});
