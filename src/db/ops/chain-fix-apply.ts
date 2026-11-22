/**
 * Write accepted chain fixes to the database, or revert them (0019; src/db/AGENTS.md §Chain fixes). One transaction per
 * report; chain and mention ids are the projection's own (`chain:<record>:<branch>`), so the next load, which replays the same
 * overrides, rewrites the same rows. Holds the loader's data-write lock, so it never meets a load.
 *
 *   npm run db:chain-fixes -- --database production --confirm-production [--dry-run]
 *   npm run db:chain-fixes -- --database production --confirm-production --revert <chain-fix:id> [...]
 *   npm run db:chain-fixes -- --database production --confirm-production --revert-rejected
 *
 * Identity rule (docs/review/chain-fix-pipeline.md §Identities): a kept name keeps its candidates; it keeps its standing
 * identity only when both neighbours are unchanged (same fine review unit). A new or changed name starts unresolved.
 */
import { gunzipSync } from 'node:zlib';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import postgres from 'postgres';
import { DATA_WRITE_LOCK_KEY } from '../advisory-locks';
import { resolveTargetDatabase } from '../target-database';
import {
  APPLICATION_FORMAT,
  appendRecords,
  argumentsOf,
  chainSha256,
  DEFAULT_OVERRIDES,
  DEFAULT_STORE,
  readReviews,
  readSubmissions,
  storePaths,
  utcNow,
  type BaseChain,
  type FixState,
  type PlannedChain,
} from '../../../reviews/ai/tools/chain-fix-lib';

type Sql = postgres.Sql | postgres.TransactionSql;
type Row = Record<string, unknown>;
const ACTOR = 'chain-fix-apply';

/** One row of `accepted_overrides.jsonl.gz` (`datasets/hadith-data/chain-fixes/replay.py`). */
export interface Override {
  hadith_id: string;
  record_id: string;
  fix_id: string;
  arabic_sha256: string;
  effect: 'replace_routes' | 'set_status' | 'annotate';
  structure_status: 'read_by_model' | 'verified_by_reviewer' | null;
  base_chain_sha256: string;
  planned: { chains: PlannedChain[] } | null;
}

const DERIVED_MENTION_COLUMNS = ['link_kind', 'resolution', 'resolution_basis', 'narrator_id', 'decision_id', 'confidence', 'extraction_method', 'identity_withheld_reason'] as const;
const LATIN_COLUMNS = ['name_latin', 'name_latin_basis', 'name_latin_narrator_id'] as const;
const candidateId = (mentionId: string, basis: string, narratorId: string) =>
  `candidate:${mentionId.replace(/^mention:/, '')}:${basis}:${narratorId.replace(/^narrator:/, '')}`;

export function readOverrides(file: string): Override[] {
  return gunzipSync(readFileSync(file)).toString('utf8').split('\n').filter(Boolean).map((line) => JSON.parse(line) as Override);
}

/** The live rows of one report, as stored (to_jsonb keeps every column, so a revert is exact). */
export type LiveRows = { chains: Row[]; chain_mentions: Row[]; chain_mention_candidates: Row[] };

export async function liveRows(sql: Sql, hadithId: string): Promise<LiveRows> {
  const chains = await sql<{ row: Row }[]>`select to_jsonb(c) as row from chains c where c.hadith_id = ${hadithId} and c.retired_at is null order by c.branch`;
  const mentions = await sql<{ row: Row }[]>`select to_jsonb(m) as row from chain_mentions m where m.hadith_id = ${hadithId} and m.retired_at is null order by m.id`;
  const candidates = await sql<{ row: Row }[]>`select to_jsonb(k) as row from chain_mention_candidates k where k.hadith_id = ${hadithId} and k.retired_at is null order by k.id`;
  return { chains: chains.map((r) => r.row), chain_mentions: mentions.map((r) => r.row), chain_mention_candidates: candidates.map((r) => r.row) };
}

function asBase(rows: Awaited<ReturnType<typeof liveRows>>): BaseChain[] {
  return rows.chains.map((chain) => ({
    chain_id: String(chain.id),
    branch: Number(chain.branch),
    structure_status: (chain.structure_status as string | null) ?? null,
    mentions: rows.chain_mentions
      .filter((m) => m.chain_id === chain.id)
      .sort((a, b) => Number(a.position) - Number(b.position))
      .map((m) => ({ id: String(m.id), position: Number(m.position), surface_ar: String(m.surface_ar) })),
  }));
}

async function retireOutside(sql: Sql, table: 'chains' | 'chain_mentions' | 'chain_mention_candidates', hadithId: string, keep: string[], version: string) {
  await sql`update ${sql(table)} set retired_at = now(), retired_in_dataset_version_id = ${version}, updated_at = now()
            where hadith_id = ${hadithId} and retired_at is null and not (id = any(${keep}))`;
}

/** Write one replace_routes fix: upsert planned chains, mentions and carried candidates by id; retire what the fix drops. */
export async function writeRoutes(sql: Sql, override: Override, base: Awaited<ReturnType<typeof liveRows>>, version: string) {
  const planned = override.planned!.chains;
  const oldMentions = new Map(base.chain_mentions.map((m) => [String(m.id), m]));
  const sanadConfidence = (base.chains[0]?.sanad_confidence as string | null | undefined) ?? null;
  // The work's compiler heads every route of the report alike (0019); a fix changes routes, not who compiled the work.
  const compilerNarratorId = (base.chains[0]?.compiler_narrator_id as string | null | undefined) ?? null;
  const compilerLink = (base.chains[0]?.compiler_link as string | null | undefined) ?? null;
  const written = { chains: [] as string[], chain_mentions: [] as string[], chain_mention_candidates: [] as string[] };
  for (const chain of planned) {
    await sql`
      insert into chains (id, hadith_id, branch, length, resolved, extraction_method, confidence, sanad_confidence, suspension,
                          missing_link_after, structure_status, structure_reasons, chain_fix_id, compiler_narrator_id, compiler_link,
                          first_seen_dataset_version_id, changed_in_dataset_version_id)
      values (${chain.id}, ${override.hadith_id}, ${chain.branch}, ${chain.length}, false, ${chain.extraction_method}, null, ${sanadConfidence},
              ${chain.suspension}, null, ${override.structure_status}, null, ${override.fix_id}, ${compilerNarratorId},
              ${compilerNarratorId ? (chain.suspension ? 'indirect' : compilerLink) : null}, ${version}, ${version})
      on conflict (id) do update set branch = excluded.branch, length = excluded.length, resolved = false,
        extraction_method = excluded.extraction_method, confidence = null, sanad_confidence = excluded.sanad_confidence,
        suspension = excluded.suspension, missing_link_after = null, structure_status = excluded.structure_status,
        structure_reasons = null, chain_fix_id = excluded.chain_fix_id, compiler_narrator_id = excluded.compiler_narrator_id,
        compiler_link = excluded.compiler_link, changed_in_dataset_version_id = excluded.changed_in_dataset_version_id,
        updated_at = now(), retired_at = null, retired_in_dataset_version_id = null`;
    written.chains.push(chain.id);
    for (const mention of chain.mentions) {
      const old = mention.kept_mention_id ? oldMentions.get(mention.kept_mention_id) : undefined;
      const derived: Row = mention.carry_identity && old
        ? Object.fromEntries(DERIVED_MENTION_COLUMNS.map((column) => [column, old[column] ?? null]))
        : { link_kind: mention.link_kind_if_new, resolution: 'unresolved', resolution_basis: null, narrator_id: null, decision_id: null, confidence: null, extraction_method: null, identity_withheld_reason: null };
      // The Latin form of the same written name stays; one taken from an identity goes with the identity.
      const latin: Row = old && (mention.carry_identity || old.name_latin_basis !== 'identity_name')
        ? Object.fromEntries(LATIN_COLUMNS.map((column) => [column, old[column] ?? null]))
        : { name_latin: null, name_latin_basis: null, name_latin_narrator_id: null };
      await sql`
        insert into chain_mentions (id, chain_id, hadith_id, position, surface_ar, surface_normalized, teacher_context_normalized,
          student_context_normalized, review_unit_id, review_unit_fine_id, link_kind, resolution, resolution_basis, narrator_id,
          decision_id, confidence, extraction_method, identity_withheld_reason, name_latin, name_latin_basis, name_latin_narrator_id,
          inherited_from_mention_id, first_seen_dataset_version_id, changed_in_dataset_version_id)
        values (${mention.id}, ${chain.id}, ${override.hadith_id}, ${mention.position}, ${mention.surface_ar}, ${mention.surface_normalized},
          ${mention.teacher_context_normalized}, ${mention.student_context_normalized}, ${mention.review_unit_id}, ${mention.review_unit_fine_id},
          ${derived.link_kind as string}::link_kind, ${derived.resolution as string}::mention_resolution, ${derived.resolution_basis as string | null}::resolution_basis,
          ${derived.narrator_id as string | null}, ${derived.decision_id as string | null}, ${derived.confidence as number | null},
          ${derived.extraction_method as string | null}, ${derived.identity_withheld_reason as string | null}, ${latin.name_latin as string | null},
          ${latin.name_latin_basis as string | null}::name_latin_basis, ${latin.name_latin_narrator_id as string | null}, null, ${version}, ${version})
        on conflict (id) do update set chain_id = excluded.chain_id, position = excluded.position, surface_ar = excluded.surface_ar,
          surface_normalized = excluded.surface_normalized, teacher_context_normalized = excluded.teacher_context_normalized,
          student_context_normalized = excluded.student_context_normalized, review_unit_id = excluded.review_unit_id,
          review_unit_fine_id = excluded.review_unit_fine_id, link_kind = excluded.link_kind, resolution = excluded.resolution,
          resolution_basis = excluded.resolution_basis, narrator_id = excluded.narrator_id, decision_id = excluded.decision_id,
          confidence = excluded.confidence, extraction_method = excluded.extraction_method,
          identity_withheld_reason = excluded.identity_withheld_reason, name_latin = excluded.name_latin,
          name_latin_basis = excluded.name_latin_basis, name_latin_narrator_id = excluded.name_latin_narrator_id,
          inherited_from_mention_id = null, changed_in_dataset_version_id = excluded.changed_in_dataset_version_id,
          updated_at = now(), retired_at = null, retired_in_dataset_version_id = null`;
      written.chain_mentions.push(mention.id);
      // A kept name keeps every identity candidate, source_position included: it indexes the source's own list, not our chain.
      for (const candidate of base.chain_mention_candidates.filter((c) => old && c.mention_id === old.id)) {
        const id = candidateId(mention.id, String(candidate.basis), String(candidate.narrator_id));
        await sql`
          insert into chain_mention_candidates (id, mention_id, hadith_id, narrator_id, basis, detail, source_position, source_ref,
            source_assertion_origin, first_seen_dataset_version_id, changed_in_dataset_version_id)
          values (${id}, ${mention.id}, ${override.hadith_id}, ${candidate.narrator_id as string}, ${candidate.basis as string}::mention_candidate_basis,
            ${candidate.detail as string | null}, ${candidate.source_position as number | null}, ${candidate.source_ref as string | null},
            ${candidate.source_assertion_origin as string | null}, ${version}, ${version})
          on conflict (id) do update set mention_id = excluded.mention_id, narrator_id = excluded.narrator_id, basis = excluded.basis,
            detail = excluded.detail, source_position = excluded.source_position, source_ref = excluded.source_ref,
            source_assertion_origin = excluded.source_assertion_origin, changed_in_dataset_version_id = excluded.changed_in_dataset_version_id,
            updated_at = now(), retired_at = null, retired_in_dataset_version_id = null`;
        written.chain_mention_candidates.push(id);
      }
    }
  }
  // Children before parents is not needed (no deletes); retire in any order.
  await retireOutside(sql, 'chain_mention_candidates', override.hadith_id, written.chain_mention_candidates, version);
  await retireOutside(sql, 'chain_mentions', override.hadith_id, written.chain_mentions, version);
  await retireOutside(sql, 'chains', override.hadith_id, written.chains, version);
  return written;
}

/** Restore the rows an application recorded, exactly (every column), and retire what the fix added. */
export async function restoreRows(sql: Sql, hadithId: string, rows: { chains: Row[]; chain_mentions: Row[]; chain_mention_candidates: Row[] }, version: string) {
  for (const table of ['chains', 'chain_mentions', 'chain_mention_candidates'] as const) {
    const columns = (await sql<{ column_name: string }[]>`
      select column_name from information_schema.columns
      where table_schema = current_schema() and table_name = ${table} and is_generated = 'NEVER' order by ordinal_position`).map((c) => c.column_name);
    const updatable = columns.filter((column) => column !== 'id');
    for (const row of rows[table]) {
      await sql`
        insert into ${sql(table)} (${sql(columns)})
        select ${sql(columns)} from jsonb_populate_record(null::${sql(table)}, ${sql.json(row as postgres.JSONValue)})
        on conflict (id) do update set ${sql.unsafe(updatable.map((column) => `"${column}" = excluded."${column}"`).join(', '))}`;
    }
  }
  for (const table of ['chain_mention_candidates', 'chain_mentions', 'chains'] as const) {
    await retireOutside(sql, table, hadithId, rows[table].map((row) => String(row.id)), version);
  }
}

/** Mirror the file store into the five chain-fix tables (immutable rows inserted once; a changed state retires the live decision). */
export async function syncMirror(sql: Sql, storeRoot: string) {
  const paths = storePaths(storeRoot);
  const submissions = readSubmissions(paths);
  const states = (JSON.parse(readFileSync(paths.state, 'utf8')) as { fixes: FixState[] }).fixes;
  const live = new Set((await sql<{ id: string }[]>`select id from hadiths where id = any(${[...new Set(submissions.map((s) => s.hadith_id))]})`).map((r) => r.id));
  for (const s of submissions.filter((x) => live.has(x.hadith_id))) {
    await sql`insert into chain_fixes (id, hadith_id, arabic_sha256, reader_text_sha256, text_layout, routes_key, fix_kinds, planned, created_by)
              values (${s.fix_id}, ${s.hadith_id}, ${s.arabic_sha256}, ${s.reader_text_sha256}, ${s.text_layout}, ${s.routes_key}, ${s.fix_kinds},
                      ${sql.json(s.planned as unknown as postgres.JSONValue)}, ${ACTOR}) on conflict (id) do nothing`;
    await sql`insert into chain_fix_submissions (id, fix_id, hadith_id, view, reading, base_chain_sha256, base_read_from, reason, evidence,
                computed_evidence, external_citation, specialist_id, specialist_version, prompt_path, prompt_version, prompt_sha256, model_id,
                provider_runtime, orchestrator_run_id, packet_path, packet_sha256, packet_item_id, started_at, finished_at, submitted_at, created_by)
              values (${s.submission_id}, ${s.fix_id}, ${s.hadith_id}, ${s.view}, ${sql.json(s.reading as unknown as postgres.JSONValue)},
                ${s.base.chain_sha256}, ${s.base.read_from}, ${s.reason}, ${sql.json(s.evidence as unknown as postgres.JSONValue)},
                ${sql.json(s.computed_evidence as unknown as postgres.JSONValue)}, ${s.external_citation ? sql.json(s.external_citation as unknown as postgres.JSONValue) : null},
                ${s.specialist_id}, ${s.specialist_version}, ${s.prompt_path}, ${s.prompt_version}, ${s.prompt_sha256}, ${s.model_id},
                ${s.provider_runtime}, ${s.orchestrator_run_id}, ${s.packet_path}, ${s.packet_sha256}, ${s.packet_item_id}, ${s.started_at},
                ${s.finished_at}, ${s.submitted_at}, ${ACTOR}) on conflict (id) do nothing`;
  }
  for (const r of readReviews(paths).filter((x) => live.has(x.hadith_id))) {
    await sql`insert into chain_fix_reviews (id, fix_id, reviewer_kind, reviewer, model_id, prompt_path, prompt_sha256, decision, superseded_by_fix_id,
                note, citation, reviewed_at, created_by)
              values (${r.review_id}, ${r.fix_id}, ${r.reviewer_kind}, ${r.reviewer}, ${r.model_id}, ${r.prompt_path}, ${r.prompt_sha256}, ${r.decision},
                ${r.superseded_by}, ${r.note}, ${r.citation ? sql.json(r.citation as unknown as postgres.JSONValue) : null}, ${r.reviewed_at}, ${ACTOR})
              on conflict (id) do nothing`;
  }
  const now = utcNow();
  // Retire first, insert after: the live-effect index allows one effect per report at a time.
  const changed: FixState[] = [];
  for (const state of states.filter((x) => live.has(x.hadith_id))) {
    const [current] = await sql<{ id: string; state: string; effect: string | null; structure_status: string | null; runs: number; dissenting_runs: number }[]>`
      select id, state, effect, structure_status, runs, dissenting_runs from chain_fix_decisions where fix_id = ${state.fix_id} and retired_at is null`;
    if (current && current.state === state.state && current.effect === state.effect && current.structure_status === state.structure_status
        && current.runs === state.runs.length && current.dissenting_runs === state.dissenting_runs) continue;
    if (current) await sql`update chain_fix_decisions set retired_at = now(), retired_by = ${ACTOR}, updated_at = now(), updated_by = ${ACTOR} where id = ${current.id}`;
    changed.push(Object.assign(state, { supersedes: current?.id ?? null }));
  }
  for (const state of changed as (FixState & { supersedes: string | null })[]) {
    await sql`insert into chain_fix_decisions (fix_id, hadith_id, state, effect, structure_status, runs, text_only_runs, dissenting_runs, models,
                hold_codes, why, decided_at, supersedes_decision_id, created_by, updated_by)
              values (${state.fix_id}, ${state.hadith_id}, ${state.state}, ${state.effect}, ${state.structure_status}, ${state.runs.length},
                ${state.text_only_runs}, ${state.dissenting_runs}, ${state.models}, ${state.state === 'held' ? state.holds : []}, ${state.why}, ${now},
                ${state.supersedes}, ${ACTOR}, ${ACTOR})`;
  }
  return changed.length;
}

async function main(): Promise<number> {
  const argv = process.argv.slice(2);
  const args = argumentsOf(argv);
  if (args.has('help')) {
    console.log('see the header of src/db/ops/chain-fix-apply.ts');
    return 0;
  }
  const target = resolveTargetDatabase(argv, { required: true });
  const storeRoot = args.get('store') ?? DEFAULT_STORE;
  const dryRun = args.has('dry-run');
  const reverting = args.has('revert') || args.has('revert-rejected');
  const sql = postgres(target.url, { max: 1, idle_timeout: 0, max_lifetime: null, prepare: false, onnotice: () => {},
    connection: { application_name: ACTOR, statement_timeout: 120_000, lock_timeout: 5_000 } });
  const applications: object[] = [];
  let touched = 0;
  try {
    const [{ locked }] = await sql<{ locked: boolean }[]>`select pg_try_advisory_lock(${String(DATA_WRITE_LOCK_KEY)}::bigint) as locked`;
    if (!locked) throw new Error('a load or migration holds the data-write lock; try again after it finishes');
    const [{ id: version }] = await sql<{ id: string }[]>`select id from dataset_versions where is_current`;
    await sql.begin(async (tx) => console.log(`mirror: ${await syncMirror(tx, storeRoot)} decision rows changed`));

    if (reverting) {
      const paths = storePaths(storeRoot);
      const queue = JSON.parse(readFileSync(paths.queue, 'utf8')) as { rejected_but_in_database: string[] };
      const fixIds = args.has('revert-rejected') ? queue.rejected_but_in_database : argv.filter((value, index) => argv[index - 1] === '--revert');
      for (const fixId of fixIds) {
        await sql.begin(async (tx) => {
          const hadithId = await revertFix(tx, fixId, version);
          if (!hadithId) return;
          applications.push({ format: APPLICATION_FORMAT, fix_id: fixId, hadith_id: hadithId, action: 'reverted', at: utcNow(), dataset_version_id: version });
          touched += 1;
          if (dryRun) throw new DryRun();
        }).catch(swallowDryRun);
      }
    } else {
      for (const override of readOverrides(args.get('overrides') ?? DEFAULT_OVERRIDES)) {
        await sql.begin(async (tx) => {
          if (!(await applyOverride(tx, override, version))) return;
          applications.push({ format: APPLICATION_FORMAT, fix_id: override.fix_id, hadith_id: override.hadith_id, action: 'applied', at: utcNow(), dataset_version_id: version });
          touched += 1;
          if (dryRun) throw new DryRun();
        }).catch(swallowDryRun);
      }
    }
    // The teacher-student view once per batch, not per report.
    if (touched > 0 && !dryRun) console.log(`refresh_network: ${JSON.stringify(await sql`select refresh_network() as refreshed`)}`);
    if (!dryRun) appendRecords(path.join(storePaths(storeRoot).applications, `${utcNow().slice(0, 10)}.jsonl`), applications);
    console.log(`${dryRun ? 'dry run, rolled back: would have ' : ''}${reverting ? 'reverted' : 'applied'} ${touched} report(s)`);
    return 0;
  } finally {
    await sql.end({ timeout: 5 });
  }
}

/** Apply one override inside `tx`; returns false (and says why) when it must wait or be re-read. */
export async function applyOverride(tx: Sql, override: Override, version: string): Promise<boolean> {
  const [hadith] = await tx<{ arabic_sha256: string }[]>`select arabic_sha256 from hadiths where id = ${override.hadith_id} and retired_at is null for update`;
  if (!hadith) return skip(`${override.fix_id}: ${override.hadith_id} is not live`);
  if (hadith.arabic_sha256 !== override.arabic_sha256) return skip(`${override.fix_id}: the Arabic changed since it was read (stays queued)`);
  const base = await liveRows(tx, override.hadith_id);
  const fixIds = new Set(base.chains.map((c) => c.chain_fix_id as string | null));
  if (fixIds.size === 1 && fixIds.has(override.fix_id)) {
    // Already written; a later human confirmation only changes the status.
    if (override.structure_status && base.chains.some((c) => c.structure_status !== override.structure_status)) {
      await tx`update chains set structure_status = ${override.structure_status}, updated_at = now(), changed_in_dataset_version_id = ${version}
               where hadith_id = ${override.hadith_id} and retired_at is null`;
    }
    return false;
  }
  if ([...fixIds].some((id) => id && id !== override.fix_id)) return skip(`${override.fix_id}: another fix is in the database for this report; revert it first`);
  if (chainSha256(asBase(base)) !== override.base_chain_sha256) return skip(`${override.fix_id}: the stored chain changed since the readers were compared with it; re-submit`);
  let written: Row = { chains: base.chains.map((c) => c.id) };
  if (override.effect === 'replace_routes') written = await writeRoutes(tx, override, base, version);
  else {
    await tx`update chains set chain_fix_id = ${override.fix_id}, updated_at = now(), changed_in_dataset_version_id = ${version}
               ${override.effect === 'set_status' ? tx`, structure_status = ${override.structure_status}, structure_reasons = null` : tx``}
             where hadith_id = ${override.hadith_id} and retired_at is null`;
  }
  await tx`select refresh_publication_facets(${[override.hadith_id]})`;
  await tx`insert into chain_fix_applications (fix_id, hadith_id, action, effect, base_rows, written_ids, dataset_version_id, created_by)
           values (${override.fix_id}, ${override.hadith_id}, 'applied', ${override.effect}, ${tx.json(base as unknown as postgres.JSONValue)},
             ${tx.json(written as postgres.JSONValue)}, ${version}, ${ACTOR})`;
  return true;
}

/** Revert the latest application of one fix inside `tx`: the rows as they were, column by column. False when not applied. */
export async function revertFix(tx: Sql, fixId: string, version: string): Promise<string | null> {
  const [last] = await tx<{ hadith_id: string; action: string; effect: string; base_rows: LiveRows }[]>`
    select hadith_id, action, effect, base_rows from chain_fix_applications where fix_id = ${fixId} order by id desc limit 1`;
  if (!last || last.action !== 'applied') {
    skip(`${fixId}: not applied`);
    return null;
  }
  await tx`select 1 from hadiths where id = ${last.hadith_id} for update`;
  const before = await liveRows(tx, last.hadith_id);
  await restoreRows(tx, last.hadith_id, last.base_rows, version);
  await tx`select refresh_publication_facets(${[last.hadith_id]})`;
  await tx`insert into chain_fix_applications (fix_id, hadith_id, action, effect, base_rows, written_ids, dataset_version_id, created_by)
           values (${fixId}, ${last.hadith_id}, 'reverted', ${last.effect}, ${tx.json(before as unknown as postgres.JSONValue)},
             ${tx.json({ chains: last.base_rows.chains.map((r) => r.id), chain_mentions: last.base_rows.chain_mentions.map((r) => r.id) } as postgres.JSONValue)},
             ${version}, ${ACTOR})`;
  return last.hadith_id;
}

function skip(message: string): false {
  console.log(`skip ${message}`);
  return false;
}

class DryRun extends Error {}
function swallowDryRun(error: unknown) {
  if (!(error instanceof DryRun)) throw error;
}

if (require.main === module) {
  main().then(
    (code) => (process.exitCode = code),
    (error) => {
      console.error(`FAIL ${error instanceof Error ? error.message : String(error)}`);
      process.exitCode = 1;
    },
  );
}
