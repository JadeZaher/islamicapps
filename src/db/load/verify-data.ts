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

/** Verified-link resolutions since 0006 (src/db/AGENTS.md §Verified link). A name match is never one. */
const RENDERING_RESOLUTIONS = `('source_index', 'human_verified', 'derived_relation_verified')`;
const NAME_BASES = `('name_exact', 'name_spelling_fold', 'name_kunya_only')`;
/** Labels, never contests (owner 2026-11-21): kunya-only names, an unqualified shared Imam kunya, placeholder targets. */
const NON_CONTESTING = `('name_kunya_only', 'imam_kunya_candidate')`;
/**
 * Person key of every narrator, for comparing two claims (src/db/AGENTS.md §External identity): its lexicon link
 * candidate, else (Riwayat) the link of its one hadith-kg crosswalk id, else that hadith-kg narrator, else itself.
 * Mirrors `PersonKeys.key` in datasets/hadith-data/pg_export/external_identity.py.
 */
const PERSON_KEYS = `person_keys as materialized (
  select n.id, coalesce(l.rawi_narrator_id, kl.rawi_narrator_id, kg.kg_id, n.id) as person
  from narrators n
  left join lateral (select min(x.rawi_narrator_id) as rawi_narrator_id from narrator_link_candidates x
                     where x.external_narrator_id = n.id and x.retired_at is null) l on true
  left join lateral (select 'narrator:hadith-kg:' || min(e.external_id) as kg_id from narrator_external_ids e
                     where e.narrator_id = n.id and e.namespace = 'kg' and e.retired_at is null and n.authority = 'riwayat'
                     having count(distinct e.external_id) = 1
                        and exists (select 1 from narrators k where k.id = 'narrator:hadith-kg:' || min(e.external_id))) kg on true
  left join lateral (select min(x.rawi_narrator_id) as rawi_narrator_id from narrator_link_candidates x
                     where x.external_narrator_id = kg.kg_id and x.retired_at is null) kl on true
  where n.retired_at is null)`;
/** grading-recovery's NON_RULING_CLASSES keys (whitespace removed, Persian ya and kaf folded); the projection excludes them. */
const NON_RULING_TERMS = `('لميخرجه', 'لميذكره', 'لميذكرعندهشيء', 'لميذكرالطريق', 'لميحقق', 'لاواسطة', 'سكتعنه', 'كالسابق', 'كالسابقأيضا', 'مثلالسندالسابق', 'بالسندالسابق')`;

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
  /** A chain `c` that may feed teacher and student lists (0019): the same rule as narrator_transmissions' `feeding` CTE. */
  const FEEDING = `(c.structure_status in ('checked_by_rule', 'verified_by_reviewer')
    or (c.structure_status = 'read_by_model' and exists (
          select 1 from hadiths fh join chain_fix_work_settings fs on fs.collection_id = fh.collection_id
          where fh.id = c.hadith_id and fs.retired_at is null and fs.read_by_model_in_network)))`;

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
    'no narrator_id on a non-verified resolution; resolved mentions carry confidence',
    `select count(*)::int as value from chain_mentions where retired_at is null and narrator_id is not null
       and (resolution not in ${RENDERING_RESOLUTIONS} or confidence is null)`,
  );
  // Identity candidates (owner decisions 2026-11-21, src/db/AGENTS.md §Identity candidates).
  await check(
    'every live candidate sits on a live mention of the same hadith and names a live narrator',
    `select count(*)::int as value from chain_mention_candidates c
     left join chain_mentions m on m.id = c.mention_id and m.retired_at is null
     left join narrators n on n.id = c.narrator_id and n.retired_at is null
     where c.retired_at is null and (m.id is null or n.id is null or m.hadith_id <> c.hadith_id)`,
  );
  await check(
    'no candidate targets a placeholder except the labelled kinds: name_kunya_only on kunya-only lexicon rows, an unconfirmed external claim on its own placeholder record',
    `select count(*)::int as value from chain_mention_candidates c join narrators n on n.id = c.narrator_id
     where c.retired_at is null
       and ((n.placeholder_reason is not null
             and not (c.basis = 'name_kunya_only' and n.placeholder_reason = 'kunya_only_name')
             and not (c.basis::text in ('source_hadith_kg', 'source_riwayat') and n.authority::text in ('hadith_kg', 'riwayat')))
         or (c.basis = 'name_kunya_only' and n.placeholder_reason is distinct from 'kunya_only_name'))`,
  );
  await check(
    'no automatic name candidate on a non-Sunni report (sanads stay per tradition)',
    `select count(*)::int as value from chain_mention_candidates c join hadiths h on h.id = c.hadith_id
     where c.retired_at is null and c.basis in ${NAME_BASES} and h.tradition_id <> 'tradition:sunni'`,
  );
  await check(
    'an automatic (machine-reviewed) narrator_id rests on the evidence its extraction_method names',
    `select count(*)::int as value from chain_mentions m
     where m.retired_at is null and m.narrator_id is not null and m.decision_id is null
       and not (m.resolution = 'source_index' and (
         (m.extraction_method in ('source_index_confirmed_by_text', 'source_hadith_kg_confirmed_by_text',
                                  'imam_kunya_convention', 'named_in_opening_isnad', 'edition_identification')
          and exists (select 1 from chain_mention_candidates c where c.mention_id = m.id and c.retired_at is null
                        and c.narrator_id = m.narrator_id and c.basis::text = m.extraction_method))
         or (m.extraction_method = 'source_riwayat_confirmed_by_text'
             and exists (select 1 from chain_mention_candidates c
                         left join narrator_source_profiles p on p.narrator_id = c.narrator_id and p.retired_at is null
                         where c.mention_id = m.id and c.retired_at is null and c.narrator_id = m.narrator_id
                           and c.basis::text = 'source_riwayat_confirmed_by_text'
                           and c.source_assertion_origin <> 'riwayat_automatic_linking' and p.label_reason is null))
         or (m.extraction_method = 'two_sources_agree'
             and exists (select 1 from chain_mention_candidates k where k.mention_id = m.id and k.retired_at is null
                           and k.narrator_id = m.narrator_id and k.basis in ('source_index', 'source_index_confirmed_by_text'))
             and exists (select 1 from chain_mention_candidates g
                         join narrator_link_candidates x on x.external_narrator_id = g.narrator_id and x.retired_at is null
                         where g.mention_id = m.id and g.retired_at is null and x.rawi_narrator_id = m.narrator_id
                           and g.basis::text in ('source_hadith_kg', 'source_hadith_kg_confirmed_by_text')))))`,
  );
  await check(
    'an automatic (machine-reviewed) link is uncontested: no two contesting candidates of the mention name different people of one authority',
    `with ${PERSON_KEYS},
     contested as (
       select distinct c.mention_id
       from chain_mention_candidates c
       join narrators n on n.id = c.narrator_id and n.placeholder_reason is null
       join person_keys k on k.id = c.narrator_id
       where c.retired_at is null and c.basis::text not in ${NON_CONTESTING}
       group by c.mention_id, split_part(k.person, ':', 2) having count(distinct k.person) > 1)
     select count(*)::int as value from chain_mentions m join contested x on x.mention_id = m.id
     where m.retired_at is null and m.narrator_id is not null and m.decision_id is null
       and m.extraction_method <> 'edition_identification'`,
  );
  await check(
    'the machine-reviewed tier never rests on a Riwayat automatic link',
    `select count(*)::int as value from chain_mentions m
     where m.retired_at is null and m.narrator_id is not null and m.decision_id is null
       and m.extraction_method = 'source_riwayat_confirmed_by_text'
       and not exists (select 1 from chain_mention_candidates c where c.mention_id = m.id and c.retired_at is null
                         and c.narrator_id = m.narrator_id and c.source_assertion_origin <> 'riwayat_automatic_linking')`,
  );
  await check(
    'an Imam-kunya candidate or resolution exists only in an Imami chain',
    `select (select count(*) from chain_mention_candidates c join hadiths h on h.id = c.hadith_id
             where c.retired_at is null and c.basis::text in ('imam_kunya_convention', 'imam_kunya_candidate')
               and h.tradition_id <> 'tradition:imami')
          + (select count(*) from chain_mentions m join hadiths h on h.id = m.hadith_id
             where m.retired_at is null and m.extraction_method = 'imam_kunya_convention'
               and h.tradition_id <> 'tradition:imami')
          + (select count(*) from chain_mention_candidates c join narrators n on n.id = c.narrator_id
             where c.retired_at is null
               and ((c.basis::text like 'imam_kunya_%' and n.authority::text <> 'imam_register')
                 or (n.authority::text = 'imam_register' and c.basis::text not like 'imam_kunya_%'
                     and c.basis::text <> 'named_in_opening_isnad')))
          as value`,
  );
  // Chain builder (0014; src/db/AGENTS.md §Chain builder).
  await check(
    "an inherited mention repeats a live written mention of the same collection, with the same surface, in a chain that inherits (an OpenITI continuation or a Thaqalayn «وبهذا الإسناد»)",
    `select count(*)::int as value from chain_mentions m
     join hadiths h on h.id = m.hadith_id
     join chains c on c.id = m.chain_id
     left join chain_mentions w on w.id = m.inherited_from_mention_id and w.retired_at is null
       and w.inherited_from_mention_id is null and w.surface_ar = m.surface_ar
     left join hadiths wh on wh.id = w.hadith_id and wh.collection_id = h.collection_id
     where m.retired_at is null and m.inherited_from_mention_id is not null
       and (wh.id is null or (h.sanad_inherits_from is null and c.extraction_method <> 'thaqalayn_inherited_chain'))`,
  );
  await check(
    'an unnamed transmitter or a back-reference carries no automatic identity (so no machine-reviewed pair touches one)',
    `select count(*)::int as value from chain_mentions m where m.retired_at is null and m.narrator_id is not null
       and m.decision_id is null and m.link_kind in ('anonymous', 'not_a_narrator')`,
  );
  await check(
    "an edition identification (edition_identification) names a lexicon row, only in a Sunni report, with its citation",
    `select count(*)::int as value from chain_mention_candidates c
     join hadiths h on h.id = c.hadith_id join narrators n on n.id = c.narrator_id
     where c.retired_at is null and c.basis::text = 'edition_identification'
       and (h.tradition_id <> 'tradition:sunni' or n.authority::text <> 'rawi' or nullif(trim(c.detail), '') is null)`,
  );
  await check(
    'the opening-isnad rule (named_in_opening_isnad) names only register rows, only in the works whose opening isnad is read (Musnad Zayd, Musnad al-Rabi)',
    `select count(*)::int as value from chain_mention_candidates c
     join hadiths h on h.id = c.hadith_id join narrators n on n.id = c.narrator_id
     where c.retired_at is null and c.basis::text = 'named_in_opening_isnad'
       and (h.collection_id not in ('collection:zaydi:musnad-zayd', 'collection:ibadi:musnad-rabi')
            or n.authority::text not in ('imam_register', 'work_register'))`,
  );
  await check(
    'external-authority narrators carry their source: one live profile naming that source, and no profile on a lexicon row',
    `select (select count(*) from narrators n
             left join narrator_source_profiles p on p.narrator_id = n.id and p.retired_at is null
             where n.retired_at is null and n.authority::text in ('hadith_kg', 'riwayat', 'imam_register', 'work_register')
               and (p.narrator_id is null or p.source <> n.authority::text or nullif(trim(p.licence), '') is null))
          + (select count(*) from narrator_source_profiles p join narrators n on n.id = p.narrator_id
             where p.retired_at is null and n.authority::text not in ('hadith_kg', 'riwayat', 'imam_register', 'work_register'))
          + (select count(*) from chain_mention_candidates c join narrators n on n.id = c.narrator_id
             where c.retired_at is null and c.source_ref is not null
               and n.authority::text <> case when c.basis::text like 'source_hadith_kg%' then 'hadith_kg' else 'riwayat' end)
          as value`,
  );
  await check(
    "Latin names: the provider's English only on Imami Thaqalayn reports; an identity name names a live narrator",
    `select count(*)::int as value from chain_mentions m join hadiths h on h.id = m.hadith_id
     left join narrators n on n.id = m.name_latin_narrator_id and n.retired_at is null
     where m.retired_at is null
       and ((m.name_latin_basis = 'provider_english'
             and (h.tradition_id <> 'tradition:imami' or m.hadith_id not like 'hadith:thaqalayn:%'))
         or (m.name_latin_basis = 'identity_name' and n.id is null))`,
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
    'public_translations: complete, hash-bound, state within policy, machine English with model and provenance',
    `select count(*)::int as value from public_translations t join hadiths h on h.id = t.hadith_id
     join collection_rights r on r.collection_id = h.collection_id
     where t.quality_status <> 'complete' or t.arabic_sha256 <> h.arabic_sha256
        or not (t.state in ('human_verified', 'source_verified')
                or (t.state = 'source_provided'
                    and r.english_policy::text in ('source_provided_allowed', 'source_provided_and_machine_allowed'))
                or (t.state = 'machine_unreviewed' and r.english_policy::text = 'source_provided_and_machine_allowed'
                    and t.model is not null and t.provenance_source is not null))`,
  );
  // Machine English (0018): every live machine row is complete, hash-bound, names its model and provenance; unknown_provenance never.
  await check(
    'machine English rows: complete, hash-bound, model and provenance recorded, no unknown_provenance',
    `select count(*)::int as value from translations t join hadiths h on h.id = t.hadith_id
     where t.retired_at is null
       and (t.state::text = 'unknown_provenance'
            or ((t.state = 'machine_unreviewed' or t.review_state_raw = 'machine_unreviewed')
                and (t.state <> 'machine_unreviewed' or t.quality_status <> 'complete' or t.arabic_sha256 <> h.arabic_sha256
                     or nullif(trim(t.model), '') is null or nullif(trim(t.provenance_source), '') is null
                     or nullif(trim(t.source), '') is null)))`,
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
    'no candidate-only rows in canonical tables (unknown-provenance English; machine English has its own check)',
    `select (select count(*) from translations where retired_at is null and state::text = 'unknown_provenance')
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
  // Chain structure gate (src/db/AGENTS.md §Chain structure gate): every live chain is assessed, and every pair in the
  // network stands in at least one live chain checked by rule.
  await check(
    'every live chain carries a structure status',
    `select count(*)::int as value from chains where retired_at is null and structure_status is null`,
  );
  // 0019: checked by rule or verified by a reviewer; a chain read by model only where its work's setting allows it (off for
  // every work at 0019); and a compiler pair only from a direct, unsuspended chain whose position 0 is the teacher.
  await check(
    'every narrator_transmissions pair stands in a live chain that may feed lists (adjacent mentions, or the compiler and position 0)',
    `select count(*)::int as value from narrator_transmissions nt
     where not exists (select 1 from chain_mentions a
                       join chain_mentions b on b.chain_id = a.chain_id and b.position = a.position + 1 and b.retired_at is null
                       join chains c on c.id = a.chain_id and c.retired_at is null
                       where a.retired_at is null and a.narrator_id = nt.student_id and b.narrator_id = nt.teacher_id
                         and ${FEEDING})
       and not exists (select 1 from chains c
                       join chain_mentions b on b.chain_id = c.id and b.position = 0 and b.retired_at is null
                       where c.retired_at is null and c.compiler_narrator_id = nt.student_id and b.narrator_id = nt.teacher_id
                         and c.compiler_link = 'direct' and c.suspension is null and ${FEEDING})`,
  );
  // Compiler as first transmitter (0019; src/db/AGENTS.md §Compiler as first transmitter).
  await check(
    'a compiler head names a live narrator, never a position the chain already writes, and only in a work with a compiler',
    `select count(*)::int as value from chains c
     left join narrators n on n.id = c.compiler_narrator_id and n.retired_at is null
     where c.retired_at is null and c.compiler_narrator_id is not null
       and (n.id is null
            or exists (select 1 from chain_mentions m where m.chain_id = c.id and m.retired_at is null
                         and m.narrator_id = c.compiler_narrator_id))`,
  );
  await check(
    'a work-register record carries its own profile and is named on a mention only by the work itself (named_in_opening_isnad)',
    `select (select count(*) from chain_mention_candidates c join narrators n on n.id = c.narrator_id
             where c.retired_at is null and n.authority::text = 'work_register' and c.basis::text <> 'named_in_opening_isnad')
          + (select count(*) from narrators n
             left join narrator_source_profiles p on p.narrator_id = n.id and p.retired_at is null and p.source = 'work_register'
             where n.retired_at is null and n.authority::text = 'work_register' and p.narrator_id is null)
          as value`,
  );
  // Chain fixes (0019; src/db/AGENTS.md §Chain fixes, docs/review/chain-fix-pipeline.md §Invariants).
  await check(
    'chain fixes: a live chain that names a fix reads the report\'s current Arabic',
    `select count(*)::int as value from chains c
     join chain_fixes f on f.id = c.chain_fix_id join hadiths h on h.id = c.hadith_id
     where c.retired_at is null and f.arabic_sha256 is distinct from h.arabic_sha256`,
  );
  await check(
    'chain fixes: a live chain names a fix only while that fix\'s live decision has an effect',
    `select count(*)::int as value from chains c
     left join chain_fix_decisions d on d.fix_id = c.chain_fix_id and d.retired_at is null and d.effect is not null
     where c.retired_at is null and c.chain_fix_id is not null and d.id is null`,
  );
  await check(
    'chain fixes: a model-read or reviewer-verified report names one fix, applied and not rejected',
    `select count(*)::int as value from (
       select c.hadith_id from chains c
       where c.retired_at is null and c.structure_status in ('read_by_model', 'verified_by_reviewer')
       group by c.hadith_id
       having count(distinct c.chain_fix_id) <> 1
           or not exists (select 1 from chain_fix_applications a
                          where a.fix_id = min(c.chain_fix_id) and a.action = 'applied'
                            and a.id = (select max(b.id) from chain_fix_applications b where b.fix_id = a.fix_id))
           or exists (select 1 from chain_fix_decisions d where d.fix_id = min(c.chain_fix_id) and d.retired_at is null
                        and d.state = 'rejected')) bad`,
  );
  await check(
    'chain fixes: a chain\'s fix status is the one its live decision gives',
    `select count(*)::int as value from chains c
     join chain_fix_decisions d on d.fix_id = c.chain_fix_id and d.retired_at is null
     where c.retired_at is null and d.effect in ('replace_routes', 'set_status') and c.structure_status is distinct from d.structure_status`,
  );
  await check(
    'chain fixes: "verified" (verified_by_reviewer) only with a named human whose latest review confirms, and none rejecting',
    `with latest as (
       select distinct on (fix_id, reviewer) fix_id, reviewer, decision from chain_fix_reviews
       where reviewer_kind = 'human' order by fix_id, reviewer, reviewed_at desc, id desc)
     select count(*)::int as value from chains c
     where c.retired_at is null and c.structure_status = 'verified_by_reviewer'
       and (not exists (select 1 from latest l where l.fix_id = c.chain_fix_id and l.decision = 'confirmed')
            or exists (select 1 from latest l where l.fix_id = c.chain_fix_id and l.decision = 'rejected'))`,
  );
  await check(
    'chain fixes: an automatically accepted changed reading has two reader runs, one blind to the stored chain',
    `select count(*)::int as value from chain_fix_decisions d
     where d.retired_at is null and d.state = 'accepted' and d.effect <> 'annotate'
       and ((select count(distinct s.orchestrator_run_id) from chain_fix_submissions s where s.fix_id = d.fix_id) < 2
            or not exists (select 1 from chain_fix_submissions s where s.fix_id = d.fix_id and s.view in ('text_only', 'text_and_context')))`,
  );
  await check(
    'chain fixes: in a chain a fix rewrote, an identity always has its carried candidate (a new name never invents one)',
    `select count(*)::int as value from chain_mentions m
     join chains c on c.id = m.chain_id and c.retired_at is null and c.extraction_method = 'chain_fix_reader'
     where m.retired_at is null and m.narrator_id is not null and m.decision_id is null
       and not exists (select 1 from chain_mention_candidates k where k.mention_id = m.id and k.narrator_id = m.narrator_id
                         and k.retired_at is null)`,
  );
  await check(
    'chain fixes: every review names its reviewer, a note and a date; an AI review names its model and prompt',
    `select count(*)::int as value from chain_fix_reviews
     where btrim(reviewer) = '' or btrim(note) = '' or reviewed_at is null
        or (reviewer_kind = 'ai' and (model_id is null or prompt_path is null or prompt_sha256 is null))`,
  );

  // Chain chronology guard (src/db/AGENTS.md §Chain chronology guard): a withheld identity keeps its candidates.
  await check(
    'a withheld identity has no automatic narrator_id and keeps a confirmed candidate',
    `select count(*)::int as value from chain_mentions m
     where m.retired_at is null and m.identity_withheld_reason is not null
       and (m.resolution_basis = 'source_index'
            or not exists (select 1 from chain_mention_candidates c
                           where c.mention_id = m.id and c.retired_at is null
                             and (c.basis::text in ('source_index_confirmed_by_text', 'source_hadith_kg_confirmed_by_text',
                                                    'source_riwayat_confirmed_by_text', 'imam_kunya_convention')
                                  -- 0019 bare kunya rule: withheld from the source's own claim, confirmed or not
                                  or (m.identity_withheld_reason like 'kunya only:%'
                                      and c.basis::text in ('source_index', 'source_hadith_kg', 'source_riwayat')))))`,
  );
  await check(
    'no machine-reviewed pair in narrator_transmissions is impossible on the lexicon years outside irsal range',
    `select count(*)::int as value from narrator_transmissions nt
     join narrator_lifespans sl on sl.narrator_id = nt.student_id
     join narrator_lifespans tl on tl.narrator_id = nt.teacher_id
     where nt.temporal_plausibility = 'impossible'
       and (nullif(tl.birth_min, 0) > nullif(sl.death_max, 0) or nullif(tl.death_min, 0) > nullif(sl.death_max, 0) + 60
            or nullif(sl.birth_min, 0) > nullif(tl.death_max, 0) + 20)
       and exists (select 1 from chain_mentions a join chain_mentions b on b.chain_id = a.chain_id and b.position = a.position + 1
                   where a.narrator_id = nt.student_id and b.narrator_id = nt.teacher_id
                     and a.retired_at is null and b.retired_at is null
                     and a.resolution_basis = 'source_index' and b.resolution_basis = 'source_index'
                     and (select count(*) from chain_mentions x where x.chain_id = a.chain_id and x.retired_at is null
                            and x.narrator_id in (nt.student_id, nt.teacher_id)) = 2)`,
  );
  // Matn (review 2026-11-21): a stored matn is the report's own, its Arabic letters inside the report's own text.
  await check(
    'a stored matn is contained in its own report text (Arabic letters compared)',
    `select count(*)::int as value from hadiths
     where retired_at is null and matn_ar is not null
       and strpos(regexp_replace(coalesce(text_ar, ''), '[^ء-ي]', '', 'g'), regexp_replace(matn_ar, '[^ء-ي]', '', 'g')) = 0`,
  );
  // OpenITI report structure (src/db/AGENTS.md §OpenITI extraction fields): spans are the report's own, never rewritten.
  await check(
    'a stored Arabic chain span is contained in its own text, and a low-confidence split stores no span',
    `select count(*)::int as value from hadiths
     where retired_at is null
       and ((sanad_ar is not null and strpos(coalesce(text_ar, ''), sanad_ar) = 0)
            or (split_confidence = 'low' and (sanad_ar is not null or matn_ar is not null)))`,
  );
  await check(
    'a chain continued from another report names a live report of the same collection',
    `select count(*)::int as value from hadiths h
     left join hadiths p on p.id = h.sanad_inherits_from and p.retired_at is null
     where h.retired_at is null and h.sanad_inherits_from is not null
       and (p.id is null or p.collection_id <> h.collection_id or p.id = h.id)`,
  );
  await check(
    'source notes are a list of known kinds with Arabic text',
    `select count(*)::int as value from hadiths h
     where h.retired_at is null and h.source_notes is not null
       and exists (select 1 from jsonb_array_elements(h.source_notes) n
                   where n->>'kind' not in ('compiler_comment', 'arranger_note', 'editor_footnote', 'note')
                      or nullif(trim(n->>'text_ar'), '') is null)`,
  );
  await check(
    'no non-ruling (not included, silent, back-reference) stored as an assessment',
    `select count(*)::int as value from hadith_assessments where retired_at is null
       and regexp_replace(translate(grade_raw, 'یک', 'يك'), '[^ء-ي]', '', 'g') in ${NON_RULING_TERMS}`,
  );
  // Report correspondences (src/db/AGENTS.md §Report correspondences).
  await check(
    'correspondence candidates: both reports live and distinct, ordered a < b, bound to the loaded Arabic',
    `select count(*)::int as value from report_correspondence_candidates c
     left join hadiths a on a.id = c.hadith_id_a and a.retired_at is null
     left join hadiths b on b.id = c.hadith_id_b and b.retired_at is null
     where c.retired_at is null
       and (a.id is null or b.id is null or not (c.hadith_id_a collate "C" < c.hadith_id_b collate "C")
            or c.arabic_sha256_a <> a.arabic_sha256 or c.arabic_sha256_b <> b.arabic_sha256)`,
  );
  await check(
    'correspondence cluster members name live reports, and every live candidate pair has both reports as members',
    `select (select count(*) from report_correspondence_cluster_members m
             left join hadiths h on h.id = m.hadith_id and h.retired_at is null
             left join hadiths s on s.id = m.star_centre_hadith_id and s.retired_at is null
             where m.retired_at is null and (h.id is null or s.id is null))
          + (select count(*) from report_correspondence_candidates c
             where c.retired_at is null and exists (
               select 1 from (values (c.hadith_id_a), (c.hadith_id_b)) side(id)
               where not exists (select 1 from report_correspondence_cluster_members m
                                 where m.retired_at is null and m.method_version = c.method_version and m.hadith_id = side.id)))
          as value`,
  );
  await check(
    'correspondence decisions: at most one live per pair, ordered a < b, both reports exist',
    `select count(*)::int as value from report_correspondence_decisions d
     left join hadiths a on a.id = d.hadith_id_a left join hadiths b on b.id = d.hadith_id_b
     where d.retired_at is null and (a.id is null or b.id is null or not (d.hadith_id_a collate "C" < d.hadith_id_b collate "C"))`,
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
    // Not fatal: a rejected fix stays applied only until the revert runs in the same operator step as the review sync.
    chain_fixes_rejected_but_applied: await scalar(
      sql,
      `select count(*)::int as value from chain_fix_decisions d
       where d.retired_at is null and d.state = 'rejected'
         and 'applied' = (select a.action from chain_fix_applications a where a.fix_id = d.fix_id order by a.id desc limit 1)`,
    ),
    compiler_heads: await sql.unsafe(
      `select compiler_link, count(*)::int as chains from chains where retired_at is null and compiler_narrator_id is not null
       group by 1 order by 1`,
    ),
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
    identity_candidates: await sql.unsafe(
      `select h.tradition_id, c.basis, count(*)::int as candidates
       from chain_mention_candidates c join hadiths h on h.id = c.hadith_id
       where c.retired_at is null group by 1, 2 order by 1, 2`,
    ),
    standing_identity: await sql.unsafe(
      `select h.tradition_id, m.extraction_method, count(*)::int as mentions
       from chain_mentions m join hadiths h on h.id = m.hadith_id
       where m.retired_at is null and m.narrator_id is not null group by 1, 2 order by 1, 2`,
    ),
    latin_names: await sql.unsafe(
      `select h.tradition_id, coalesce(m.name_latin_basis::text, 'none') as basis, count(*)::int as mentions
       from chain_mentions m join hadiths h on h.id = m.hadith_id
       where m.retired_at is null group by 1, 2 order by 1, 2`,
    ),
    narrators_by_authority: await sql.unsafe(
      `select authority, count(*)::int as narrators from narrators where retired_at is null group by 1 order by 1`,
    ),
    transmissions: await scalar(sql, 'select count(*)::int as value from narrator_transmissions'),
    report_correspondences: await sql.unsafe(
      `select c.scope, c.relation_class, count(*)::int as pairs,
              count(*) filter (where s.candidate_id is not null)::int as shown
       from report_correspondence_candidates c
       left join report_correspondence_shown_pairs s on s.candidate_id = c.id
       where c.retired_at is null group by 1, 2 order by 1, 2`,
    ),
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
