/** Section 11.4 data invariants. Run inside the load transaction, or on demand: `tsx src/db/load/verify-data.ts`. */
import type { LoaderSql } from './connection';
import type { MergeResult } from './merge';
import { PIPELINE_TABLES, quoteIdentifier } from './tables';

export interface DataCheck {
  name: string;
  ok: boolean;
  detail: string;
}

export interface DataCheckOptions {
  /** Live row count per pipeline table must equal these (the projection manifest's row counts). */
  expectedLiveRows?: Record<string, number>;
  /** Merge results of the load being checked, for the exact-retirement invariant. */
  mergeResults?: MergeResult[];
  /** Section 9b floor; the flow test lowers it for a small slice. */
  minimumLiveHadiths?: number;
}

export interface DataCheckReport {
  checks: DataCheck[];
  /** Reported, not fatal (section 11.4 last rows and server settings). */
  reported: Record<string, unknown>;
}

const RENDERING_RESOLUTIONS = `('exact_registry', 'human_verified', 'derived_relation_verified')`;

async function scalar(sql: LoaderSql, query: string): Promise<number> {
  const [row] = await sql.unsafe<{ value: number }[]>(query);
  return Number(row.value);
}

/** Every single-column foreign key declared in `public`, checked by anti-join in the session's current schema. */
async function orphanForeignKeyChecks(sql: LoaderSql): Promise<DataCheck[]> {
  const foreignKeys = await sql.unsafe<
    { conname: string; table_name: string; column_name: string; foreign_table: string; foreign_column: string }[]
  >(`
    select con.conname, c.relname as table_name, a.attname as column_name, fc.relname as foreign_table, fa.attname as foreign_column
    from pg_constraint con
    join pg_class c on c.oid = con.conrelid
    join pg_class fc on fc.oid = con.confrelid
    join pg_attribute a on a.attrelid = con.conrelid and a.attnum = con.conkey[1]
    join pg_attribute fa on fa.attrelid = con.confrelid and fa.attnum = con.confkey[1]
    where con.contype = 'f' and con.connamespace = 'public'::regnamespace and cardinality(con.conkey) = 1
      and to_regclass(quote_ident(current_schema()) || '.' || quote_ident(c.relname)) is not null
      and to_regclass(quote_ident(current_schema()) || '.' || quote_ident(fc.relname)) is not null
    order by con.conname`);
  let orphans = 0;
  const offenders: string[] = [];
  for (const foreignKey of foreignKeys) {
    const count = await scalar(
      sql,
      `select count(*)::int as value from ${quoteIdentifier(foreignKey.table_name)} c
       where c.${quoteIdentifier(foreignKey.column_name)} is not null and not exists (
         select 1 from ${quoteIdentifier(foreignKey.foreign_table)} p
         where p.${quoteIdentifier(foreignKey.foreign_column)} = c.${quoteIdentifier(foreignKey.column_name)})`,
    );
    orphans += count;
    if (count > 0) offenders.push(`${foreignKey.conname}=${count}`);
  }
  return [{
    name: 'zero orphan foreign keys',
    ok: orphans === 0,
    detail: `${foreignKeys.length} foreign keys checked; ${orphans} orphans${offenders.length ? ` (${offenders.join(', ')})` : ''}`,
  }];
}

/** Runs every check; the caller fails the load (or exits non-zero) when any `ok` is false. */
export async function runDataChecks(sql: LoaderSql, options: DataCheckOptions = {}): Promise<DataCheckReport> {
  const checks: DataCheck[] = [];
  const check = async (name: string, query: string, expectZero = true) => {
    const value = await scalar(sql, query);
    checks.push({ name, ok: expectZero ? value === 0 : value > 0, detail: `${expectZero ? 'violations' : 'value'}: ${value}` });
  };

  const current = await sql.unsafe<
    { id: string; attribution_disclaimer: string; release_class: string; public_override_by: string | null; source_release_state: string; curation_manifest_sha256: string | null }[]
  >(`select id, attribution_disclaimer, release_class, public_override_by, source_release_state, curation_manifest_sha256
     from dataset_versions where is_current`);
  checks.push({
    name: 'exactly one current dataset version, carrying the attribution disclaimer',
    ok: current.length === 1 && (current[0].attribution_disclaimer ?? '').trim() !== '',
    detail: `current versions: ${current.length}`,
  });
  if (current.length === 1) {
    const version = current[0];
    const publicRows = await scalar(sql, 'select count(*)::int as value from public_hadiths');
    const servable = version.release_class === 'release' || version.public_override_by !== null;
    checks.push({
      name: 'a non-release current version is public only with a recorded override',
      ok: servable || publicRows === 0,
      detail: `release_class=${version.release_class}, override=${version.public_override_by !== null}, public_hadiths=${publicRows}`,
    });
    checks.push({
      name: 'development_nonrelease carries curation_manifest_sha256',
      ok: version.source_release_state !== 'development_nonrelease' || version.curation_manifest_sha256 !== null,
      detail: `source_release_state=${version.source_release_state}`,
    });
  }

  const minimum = options.minimumLiveHadiths ?? 50_000;
  const liveHadiths = await scalar(sql, 'select count(*)::int as value from hadiths where retired_at is null');
  const liveNarrators = await scalar(sql, 'select count(*)::int as value from narrators where retired_at is null');
  checks.push({
    name: `at least ${minimum} live hadiths and one live narrator`,
    ok: liveHadiths >= minimum && liveNarrators >= 1,
    detail: `hadiths=${liveHadiths}, narrators=${liveNarrators}`,
  });

  await check(
    'every live hadith has its live tradition and live collection, and they agree',
    `select count(*)::int as value from hadiths h
     left join collections c on c.id = h.collection_id and c.retired_at is null
     left join traditions t on t.id = h.tradition_id and t.retired_at is null
     where h.retired_at is null and (c.id is null or t.id is null or c.tradition_id <> h.tradition_id)`,
  );
  await check(
    'Arabic round trip: SHA-256 recomputed in the database equals arabic_sha256',
    `select count(*)::int as value from hadiths
     where retired_at is null and encode(sha256(convert_to(coalesce(text_ar, ''), 'UTF8')), 'hex') <> arabic_sha256`,
  );
  await check(
    'translations bound to their hadith Arabic hash',
    `select count(*)::int as value from translations t join hadiths h on h.id = t.hadith_id
     where t.retired_at is null and t.arabic_sha256 <> h.arabic_sha256`,
  );
  await check(
    'no narrator_id on a non-rendering resolution (source_index excepted); resolved mentions carry confidence',
    `select count(*)::int as value from chain_mentions where retired_at is null and narrator_id is not null
       and (resolution not in ${RENDERING_RESOLUTIONS.slice(0, -1)}, 'source_index') or confidence is null)`,
  );
  await check(
    'source_index links never on Imami reports',
    `select count(*)::int as value from chain_mentions m join hadiths h on h.id = m.hadith_id
     where m.retired_at is null and m.resolution = 'source_index' and h.tradition_id = 'tradition:imami'`,
  );
  await check(
    'live decisions have a reviewer and time; no derived_relation decision has the coarse scope',
    `select count(*)::int as value from narrator_surface_decisions where retired_at is null
       and (nullif(trim(reviewer), '') is null or reviewed_at is null
            or (decision_kind = 'derived_relation' and scope = 'teacher_context'))`,
  );
  await check(
    'chain positions contiguous 0..length-1 in every live chain',
    `select count(*)::int as value from chains c
     left join (select chain_id, count(*) as n, min(position) as lo, max(position) as hi, count(distinct position) as d
                from chain_mentions where retired_at is null group by chain_id) m on m.chain_id = c.id
     where c.retired_at is null
       and (coalesce(m.n, 0) <> c.length or m.lo <> 0 or m.hi <> c.length - 1 or m.d <> c.length)`,
  );
  await check(
    'public_translations: complete, hash-bound, state within policy',
    `select count(*)::int as value from public_translations t join hadiths h on h.id = t.hadith_id
     join collection_rights r on r.collection_id = h.collection_id
     where t.quality_status <> 'complete' or t.arabic_sha256 <> h.arabic_sha256
        or not (t.state in ('human_verified', 'source_verified')
                or (t.state = 'source_provided' and r.english_policy = 'source_provided_allowed'))`,
  );
  await check(
    'no cross_parallels.source_translation_id outside translations',
    `select count(*)::int as value from cross_parallels p where p.source_translation_id is not null
       and not exists (select 1 from translations t where t.id = p.source_translation_id)`,
  );
  await check(
    'no hadith_assessments placeholder grade',
    `select count(*)::int as value from hadith_assessments where retired_at is null
       and (nullif(trim(grade_raw), '') is null or grade_raw in ('no_extant_evaluation', 'ungraded_placeholder'))`,
  );
  await check(
    'no candidate-only rows in canonical tables',
    `select (select count(*) from translations where retired_at is null
               and (state in ('machine_unreviewed', 'unknown_provenance') or review_state_raw = 'machine_unreviewed'))
          + (select count(*) from hadith_assessments where retired_at is null and review_state = 'candidate_only')
          + (select count(*) from citations where retired_at is null and review_state = 'candidate_only') as value`,
  );
  await check(
    'no published verdict, bio or event with a missing, retired or unreviewed citation',
    `select (select count(*) from narrator_assessments a left join citations c on c.id = a.citation_id
             where a.retired_at is null and a.status = 'published'
               and (c.id is null or c.retired_at is not null or c.review_state not in ('human_verified', 'source_verified')))
          + (select count(*) from narrator_bios b left join citations c on c.id = b.citation_id
             where b.retired_at is null and b.status = 'published'
               and (c.id is null or c.retired_at is not null or c.review_state not in ('human_verified', 'source_verified')))
          + (select count(*) from historical_events e left join citations c on c.id = e.citation_id
             where e.retired_at is null and e.publication_ready and e.citation_id is not null
               and (c.id is null or c.retired_at is not null or c.review_state not in ('human_verified', 'source_verified'))) as value`,
  );
  await check(
    'no published event fails the publication gate',
    `select count(*)::int as value from historical_events e where e.retired_at is null and e.publication_ready
       and (e.verification_status not in ('human_verified', 'source_verified') or nullif(trim(e.citation_source), '') is null
            or (nullif(trim(e.citation_locator), '') is null and nullif(trim(e.citation_url), '') is null))`,
  );
  await check(
    'every narrator_transmissions row has plausibility, confidence and extraction methods',
    `select count(*)::int as value from narrator_transmissions
     where temporal_plausibility is null or confidence is null or cardinality(extraction_methods) = 0`,
  );
  checks.push(...(await orphanForeignKeyChecks(sql)));

  if (options.expectedLiveRows) {
    const mismatches: string[] = [];
    for (const table of PIPELINE_TABLES) {
      const expected = options.expectedLiveRows[table.name];
      const live = await scalar(sql, `select count(*)::int as value from ${quoteIdentifier(table.name)} where retired_at is null`);
      if (live !== expected) mismatches.push(`${table.name}: live ${live}, manifest ${expected}`);
    }
    checks.push({
      name: 'live rows per table equal the projection manifest',
      ok: mismatches.length === 0,
      detail: mismatches.length ? mismatches.join('; ') : `${PIPELINE_TABLES.length} tables match`,
    });
  }
  if (options.mergeResults) {
    const inexact = options.mergeResults.filter((result) => result.retired !== result.expectedRetired);
    checks.push({
      name: 'retirement is exact: retired = live before minus staged',
      ok: inexact.length === 0,
      detail: inexact.length ? inexact.map((r) => `${r.table}: ${r.retired} vs ${r.expectedRetired}`).join('; ') : 'all tables exact',
    });
  }

  const reported: Record<string, unknown> = {
    orphaned_decisions: await scalar(
      sql,
      `select count(*)::int as value from narrator_surface_decisions d where d.retired_at is null and not exists (
         select 1 from chain_mentions m where m.retired_at is null and (
           (d.scope = 'teacher_context' and m.review_unit_id = d.unit_id) or
           (d.scope = 'teacher_and_student_context' and m.review_unit_fine_id = d.unit_id) or
           (d.scope = 'mention' and m.id = d.unit_id)))`,
    ),
    facets: await sql.unsafe(
      `select tradition_id, source_text_status, chain_status, grading_status, count(*)::int as hadiths
       from hadiths where retired_at is null group by 1, 2, 3, 4 order by 1, 2, 3, 4`,
    ),
    mention_resolution: await sql.unsafe(
      `select h.tradition_id, m.resolution, m.resolution_basis, count(*)::int as mentions
       from chain_mentions m join hadiths h on h.id = m.hadith_id where m.retired_at is null group by 1, 2, 3 order by 1, 2, 3`,
    ),
    transmissions: await scalar(sql, 'select count(*)::int as value from narrator_transmissions'),
    server_settings: await sql.unsafe(
      `select name, setting, unit from pg_settings where name in ('max_connections', 'shared_buffers') order by name`,
    ),
  };
  return { checks, reported };
}

export function failedChecks(report: DataCheckReport): DataCheck[] {
  return report.checks.filter((entry) => !entry.ok);
}

export function formatChecks(report: DataCheckReport): string {
  return report.checks.map((entry) => `${entry.ok ? 'PASS' : 'FAIL'}  ${entry.name}  (${entry.detail})`).join('\n');
}
