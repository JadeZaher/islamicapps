/**
 * Write accepted chain fixes to the database, or revert them (0019; src/db/AGENTS.md §Chain fixes). One transaction per
 * report; chain and mention ids are the projection's own (`chain:<record>:<branch>`), so the next load, which replays the same
 * overrides, rewrites the same rows. Holds the loader's data-write lock, so it never meets a load.
 *
 *   npm run db:chain-fixes -- --database production --confirm-production [--dry-run]
 *   npm run db:chain-fixes -- --database production --confirm-production --revert <chain-fix:id> [...]
 *   npm run db:chain-fixes -- --database production --confirm-production --revert-rejected
 *   [--plan <file.json>]   writes what was (or, with --dry-run, would be) written, per report and in total
 *   --dry-run --no-mirror --store <scratch> --overrides <scratch file>   a store-free rehearsal: nothing is mirrored; each report's
 *                          transaction inserts its fix row, applies, records the tally and is rolled back (no row stays)
 *
 * Identity rule (docs/review/chain-fix-pipeline.md §Identities): a kept name keeps its candidates; it keeps its standing
 * identity only when both neighbours are unchanged (same fine review unit). A new or changed name starts unresolved. An
 * inherited name repeats its cited written mention (surface, candidates, a Latin form not taken from an identity). The
 * projection replays the same rule (`datasets/hadith-data/chain-fixes/replay.py` `rewrite_rows`): keep the two in step.
 */
import { gunzipSync } from 'node:zlib';
import { readFileSync, writeFileSync } from 'node:fs';
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
  type VariantRemark,
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
  reader_text_sha256?: string;
  text_layout?: string;
  fix_kinds?: string[];
  planned: { chains: PlannedChain[]; variant_remarks?: VariantRemark[] } | null;
  /** A remark about another version, kept with the fix (never a route, never a row); the page reads it from `chain_fixes.planned`. */
  variant_remarks?: VariantRemark[];
  /** `no_chain_by_reading`: no planned chain; the report's chains retire and the page says it writes none. */
  disposition?: string | null;
}

/** What one application writes, for the plan and the report (identity carry per docs/review/chain-fix-pipeline.md §Identities). */
export interface ApplicationTally {
  chains_retired: number;
  chains_written: number;
  mentions_written: number;
  mentions_kept_identity: number;
  mentions_kept_candidates_only: number;
  mentions_new: number;
  mentions_inherited: number;
  mentions_named_in_text: number;
}
const emptyTally = (): ApplicationTally => ({ chains_retired: 0, chains_written: 0, mentions_written: 0, mentions_kept_identity: 0,
  mentions_kept_candidates_only: 0, mentions_new: 0, mentions_inherited: 0, mentions_named_in_text: 0 });

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

/** The written mentions inherited names repeat, as live now (row and candidates); a missing one is absent from the map. */
async function citedMentions(sql: Sql, override: Override): Promise<Map<string, { row: Row; candidates: Row[]; chainStatus: string | null }>> {
  const ids = [...new Set((override.planned?.chains ?? []).flatMap((chain) => chain.mentions.map((m) => m.inherited_from_mention_id).filter((id): id is string => !!id)))];
  const out = new Map<string, { row: Row; candidates: Row[]; chainStatus: string | null }>();
  if (ids.length === 0) return out;
  const rows = await sql<{ row: Row; chain_status: string | null }[]>`
    select to_jsonb(m) as row, c.structure_status as chain_status from chain_mentions m join chains c on c.id = m.chain_id and c.retired_at is null
    where m.id = any(${ids}) and m.retired_at is null and m.inherited_from_mention_id is null`;
  const candidates = await sql<{ row: Row }[]>`select to_jsonb(k) as row from chain_mention_candidates k where k.mention_id = any(${ids}) and k.retired_at is null order by k.id`;
  for (const { row, chain_status: chainStatus } of rows) {
    out.set(String(row.id), { row, chainStatus, candidates: candidates.map((k) => k.row).filter((k) => k.mention_id === row.id) });
  }
  return out;
}

/** Upsert rows by id in one statement; `update` lists the columns a conflict overwrites (a retired row comes back live). */
async function upsertRows(sql: Sql, table: 'chains' | 'chain_mentions' | 'chain_mention_candidates', rows: Row[], update: readonly string[]) {
  if (rows.length === 0) return;
  const columns = Object.keys(rows[0]);
  await sql.unsafe(
    `insert into ${table} (${columns.map((c) => `"${c}"`).join(', ')})
     select ${columns.map((c) => `"${c}"`).join(', ')} from jsonb_populate_recordset(null::${table}, $1::text::jsonb)
     on conflict (id) do update set ${update.map((c) => `"${c}" = excluded."${c}"`).join(', ')},
       updated_at = now(), retired_at = null, retired_in_dataset_version_id = null`,
    [JSON.stringify(rows)],
  );
}

/** Write one replace_routes fix: upsert planned chains, mentions and carried candidates by id; retire what the fix drops. */
export async function writeRoutes(sql: Sql, override: Override, base: Awaited<ReturnType<typeof liveRows>>, version: string,
                                  tally: ApplicationTally = emptyTally()) {
  const planned = override.planned!.chains;
  const oldMentions = new Map(base.chain_mentions.map((m) => [String(m.id), m]));
  const cited = await citedMentions(sql, override);
  const sanadConfidence = (base.chains[0]?.sanad_confidence as string | null | undefined) ?? null;
  // The work's compiler heads every route of the report alike (0019); a fix changes routes, not who compiled the work.
  const compilerNarratorId = (base.chains[0]?.compiler_narrator_id as string | null | undefined) ?? null;
  const compilerLink = (base.chains[0]?.compiler_link as string | null | undefined) ?? null;
  const written = { chains: [] as string[], chain_mentions: [] as string[], chain_mention_candidates: [] as string[] };
  const chainRows: Row[] = [];
  const mentionRows: Row[] = [];
  const candidateRows: Row[] = [];
  for (const chain of planned) {
    chainRows.push({ id: chain.id, hadith_id: override.hadith_id, branch: chain.branch, length: chain.length, resolved: false,
      extraction_method: chain.extraction_method, confidence: null, sanad_confidence: sanadConfidence, suspension: chain.suspension,
      missing_link_after: null, structure_status: override.structure_status, structure_reasons: null, chain_fix_id: override.fix_id,
      compiler_narrator_id: compilerNarratorId,
      // The route's own mark (work_register.py `route_links`, planned by the engine); a plan without one copies the first chain's.
      compiler_link: compilerNarratorId ? (chain.suspension ? 'indirect' : (chain.compiler_link ?? compilerLink)) : null,
      first_seen_dataset_version_id: version, changed_in_dataset_version_id: version });
    written.chains.push(chain.id);
    for (const mention of chain.mentions) {
      const inherited = mention.inherited_from_mention_id ? cited.get(mention.inherited_from_mention_id) : undefined;
      if (mention.inherited_from_mention_id && !inherited) throw new Error(`${override.fix_id}: inherited mention ${mention.inherited_from_mention_id} is not live`);
      // An inherited name takes its Latin form and candidates from the written mention it repeats, never its identity.
      const old = inherited ? inherited.row : mention.kept_mention_id ? oldMentions.get(mention.kept_mention_id) : undefined;
      const carried = Boolean(mention.carry_identity && old && !inherited);
      if (inherited) tally.mentions_inherited += 1;
      else if (carried && old?.narrator_id) tally.mentions_kept_identity += 1;
      else if (old) tally.mentions_kept_candidates_only += 1;
      else tally.mentions_new += 1;
      if (mention.reader_kind === 'imam_in_text') tally.mentions_named_in_text += 1;
      tally.mentions_written += 1;
      const derived: Row = carried && old
        ? Object.fromEntries(DERIVED_MENTION_COLUMNS.map((column) => [column, old[column] ?? null]))
        : { link_kind: mention.link_kind_if_new, resolution: 'unresolved', resolution_basis: null, narrator_id: null, decision_id: null, confidence: null, extraction_method: null, identity_withheld_reason: null };
      // The Latin form of the same written name stays; one taken from an identity goes with the identity.
      const latin: Row = old && (carried || old.name_latin_basis !== 'identity_name')
        ? Object.fromEntries(LATIN_COLUMNS.map((column) => [column, old[column] ?? null]))
        : { name_latin: null, name_latin_basis: null, name_latin_narrator_id: null };
      mentionRows.push({ id: mention.id, chain_id: chain.id, hadith_id: override.hadith_id, position: mention.position, surface_ar: mention.surface_ar,
        surface_normalized: mention.surface_normalized, teacher_context_normalized: mention.teacher_context_normalized,
        student_context_normalized: mention.student_context_normalized, review_unit_id: mention.review_unit_id,
        review_unit_fine_id: mention.review_unit_fine_id, ...derived, ...latin, inherited_from_mention_id: mention.inherited_from_mention_id ?? null,
        first_seen_dataset_version_id: version, changed_in_dataset_version_id: version });
      written.chain_mentions.push(mention.id);
      // A kept name keeps every identity candidate, source_position included: it indexes the source's own list, not our chain.
      const sourceCandidates = inherited ? inherited.candidates : base.chain_mention_candidates.filter((c) => old && c.mention_id === old.id);
      for (const candidate of sourceCandidates) {
        const id = candidateId(mention.id, String(candidate.basis), String(candidate.narrator_id));
        candidateRows.push({ id, mention_id: mention.id, hadith_id: override.hadith_id, narrator_id: candidate.narrator_id, basis: candidate.basis,
          detail: candidate.detail ?? null, source_position: candidate.source_position ?? null, source_ref: candidate.source_ref ?? null,
          source_assertion_origin: candidate.source_assertion_origin ?? null, first_seen_dataset_version_id: version, changed_in_dataset_version_id: version });
        written.chain_mention_candidates.push(id);
      }
    }
  }
  // One statement per table: rows typed by the table's own row type (jsonb_populate_recordset), parents before children.
  await upsertRows(sql, 'chains', chainRows, ['branch', 'length', 'resolved', 'extraction_method', 'confidence', 'sanad_confidence', 'suspension',
    'missing_link_after', 'structure_status', 'structure_reasons', 'chain_fix_id', 'compiler_narrator_id', 'compiler_link', 'changed_in_dataset_version_id']);
  await upsertRows(sql, 'chain_mentions', mentionRows, ['chain_id', 'position', 'surface_ar', 'surface_normalized', 'teacher_context_normalized',
    'student_context_normalized', 'review_unit_id', 'review_unit_fine_id', ...DERIVED_MENTION_COLUMNS, ...LATIN_COLUMNS, 'inherited_from_mention_id',
    'changed_in_dataset_version_id']);
  await upsertRows(sql, 'chain_mention_candidates', candidateRows, ['mention_id', 'narrator_id', 'basis', 'detail', 'source_position', 'source_ref',
    'source_assertion_origin', 'changed_in_dataset_version_id']);
  // Children before parents is not needed (no deletes); retire in any order.
  await retireOutside(sql, 'chain_mention_candidates', override.hadith_id, written.chain_mention_candidates, version);
  await retireOutside(sql, 'chain_mentions', override.hadith_id, written.chain_mentions, version);
  await retireOutside(sql, 'chains', override.hadith_id, written.chains, version);
  tally.chains_written += planned.length;
  tally.chains_retired += base.chains.filter((chain) => !written.chains.includes(String(chain.id))).length;
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
  // Immutable rows already mirrored are skipped in one read (a batch mirrors in seconds, not one round trip per row).
  const knownSubmissions = new Set((await sql<{ id: string }[]>`select id from chain_fix_submissions where id = any(${submissions.map((x) => x.submission_id)})`).map((r) => r.id));
  const knownFixes = new Set((await sql<{ id: string }[]>`select id from chain_fixes where id = any(${[...new Set(submissions.map((x) => x.fix_id))]})`).map((r) => r.id));
  for (const s of submissions.filter((x) => live.has(x.hadith_id) && !knownSubmissions.has(x.submission_id))) {
    if (!knownFixes.has(s.fix_id)) {
      knownFixes.add(s.fix_id);
      await sql`insert into chain_fixes (id, hadith_id, arabic_sha256, reader_text_sha256, text_layout, routes_key, fix_kinds, planned, disposition, created_by)
                values (${s.fix_id}, ${s.hadith_id}, ${s.arabic_sha256}, ${s.reader_text_sha256}, ${s.text_layout}, ${s.routes_key}, ${s.fix_kinds},
                        ${sql.json(s.planned as unknown as postgres.JSONValue)}, ${s.disposition ?? null}, ${ACTOR}) on conflict (id) do nothing`;
    }
    await sql`insert into chain_fix_submissions (id, fix_id, hadith_id, view, reading, base_chain_sha256, base_read_from, reason, evidence,
                computed_evidence, external_citation, specialist_id, specialist_version, prompt_path, prompt_version, prompt_sha256, tool_version, inherited_from, model_id,
                provider_runtime, orchestrator_run_id, packet_path, packet_sha256, packet_item_id, started_at, finished_at, submitted_at, created_by)
              values (${s.submission_id}, ${s.fix_id}, ${s.hadith_id}, ${s.view}, ${sql.json(s.reading as unknown as postgres.JSONValue)},
                ${s.base.chain_sha256}, ${s.base.read_from}, ${s.reason}, ${sql.json(s.evidence as unknown as postgres.JSONValue)},
                ${sql.json(s.computed_evidence as unknown as postgres.JSONValue)}, ${s.external_citation ? sql.json(s.external_citation as unknown as postgres.JSONValue) : null},
                ${s.specialist_id}, ${s.specialist_version}, ${s.prompt_path}, ${s.prompt_version}, ${s.prompt_sha256}, ${s.tool_version ?? null},
                ${s.inherited_from ? sql.json(s.inherited_from as unknown as postgres.JSONValue) : null}, ${s.model_id},
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
  const liveStates = states.filter((x) => live.has(x.hadith_id));
  const decisions = new Map((await sql<{ id: string; fix_id: string; state: string; effect: string | null; structure_status: string | null; runs: number; dissenting_runs: number; hold_codes: string[] }[]>`
    select id, fix_id, state, effect, structure_status, runs, dissenting_runs, hold_codes from chain_fix_decisions
    where fix_id = any(${liveStates.map((x) => x.fix_id)}) and retired_at is null`).map((row) => [row.fix_id, row]));
  for (const state of liveStates) {
    const current = decisions.get(state.fix_id);
    if (current && current.state === state.state && current.effect === state.effect && current.structure_status === state.structure_status
        && current.runs === state.runs.length && current.dissenting_runs === state.dissenting_runs
        && current.hold_codes.join(',') === (state.state === 'held' ? state.holds : []).join(',')) continue;
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
  const plan: { fix_id: string; hadith_id: string; effect: string; disposition: string | null; tally: ApplicationTally }[] = [];
  const skipped: { fix_id: string; hadith_id: string; why: string }[] = [];
  let touched = 0;
  try {
    const [{ locked }] = await sql<{ locked: boolean }[]>`select pg_try_advisory_lock(${String(DATA_WRITE_LOCK_KEY)}::bigint) as locked`;
    if (!locked) throw new Error('a load or migration holds the data-write lock; try again after it finishes');
    const [{ id: version }] = await sql<{ id: string }[]>`select id from dataset_versions where is_current`;
    if (args.has('no-mirror') && !dryRun) throw new Error('--no-mirror is a rehearsal option: it needs --dry-run');
    if (!args.has('no-mirror')) await sql.begin(async (tx) => console.log(`mirror: ${await syncMirror(tx, storeRoot)} decision rows changed`));

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
        const tally = emptyTally();
        await sql.begin(async (tx) => {
          // A rehearsal mirrors nothing: the fix row the chain rows point at lives only inside this rolled-back transaction.
          if (args.has('no-mirror')) await insertRehearsalFix(tx, override);
          const outcome = await applyOverride(tx, override, version, tally);
          if (outcome !== true) {
            if (outcome) skipped.push({ fix_id: override.fix_id, hadith_id: override.hadith_id, why: outcome });
            return;
          }
          applications.push({ format: APPLICATION_FORMAT, fix_id: override.fix_id, hadith_id: override.hadith_id, action: 'applied', at: utcNow(), dataset_version_id: version });
          plan.push({ fix_id: override.fix_id, hadith_id: override.hadith_id, effect: override.effect, disposition: override.disposition ?? null, tally });
          touched += 1;
          if (dryRun) throw new DryRun();
        }).catch(swallowDryRun);
      }
    }
    // The teacher-student view once per batch, not per report.
    if (touched > 0 && !dryRun) console.log(`refresh_network: ${JSON.stringify(await sql`select refresh_network() as refreshed`)}`);
    if (!dryRun) appendRecords(path.join(storePaths(storeRoot).applications, `${utcNow().slice(0, 10)}.jsonl`), applications);
    if (!reverting) {
      const total = plan.reduce((sum, item) => { for (const key of Object.keys(sum) as (keyof ApplicationTally)[]) sum[key] += item.tally[key]; return sum; }, emptyTally());
      const byEffect = Object.fromEntries([...new Set(plan.map((item) => `${item.effect}${item.disposition ? `:${item.disposition}` : ''}`))].map((key) =>
        [key, plan.filter((item) => `${item.effect}${item.disposition ? `:${item.disposition}` : ''}` === key).length]));
      console.log(`plan: ${JSON.stringify({ reports: plan.length, by_effect: byEffect, ...total, skipped: skipped.length })}`);
      for (const item of skipped) console.log(`skipped ${item.fix_id} ${item.hadith_id}: ${item.why}`);
      if (args.get('plan')) writeFileSync(args.get('plan')!, `${JSON.stringify({ dry_run: dryRun, total, by_effect: byEffect, reports: plan, skipped }, null, 1)}\n`);
    }
    console.log(`${dryRun ? 'dry run, rolled back: would have ' : ''}${reverting ? 'reverted' : 'applied'} ${touched} report(s)`);
    return 0;
  } finally {
    await sql.end({ timeout: 5 });
  }
}

/** The fix row a rehearsal needs (chains point at it): from the override alone, inside a transaction that is always rolled back. */
async function insertRehearsalFix(tx: Sql, override: Override) {
  await tx`insert into chain_fixes (id, hadith_id, arabic_sha256, reader_text_sha256, text_layout, routes_key, fix_kinds, planned, disposition, created_by)
           values (${override.fix_id}, ${override.hadith_id}, ${override.arabic_sha256}, ${override.reader_text_sha256 ?? override.arabic_sha256},
                   ${override.text_layout ?? 'full_text'}, 'rehearsal', ${override.fix_kinds?.length ? override.fix_kinds : ['no_change']},
                   ${tx.json((override.planned ?? { chains: [] }) as unknown as postgres.JSONValue)}, ${override.disposition ?? null}, ${ACTOR})
           on conflict (id) do nothing`;
}

/**
 * Apply one override inside `tx`: true when written; otherwise why it waits or must be re-read (stale), or false when it is
 * already in the database.
 */
export async function applyOverride(tx: Sql, override: Override, version: string, tally: ApplicationTally = emptyTally()): Promise<true | false | string> {
  const [hadith] = await tx<{ arabic_sha256: string }[]>`select arabic_sha256 from hadiths where id = ${override.hadith_id} and retired_at is null for update`;
  if (!hadith) return skip(`${override.fix_id}: ${override.hadith_id} is not live`);
  if (hadith.arabic_sha256 !== override.arabic_sha256) return skip(`${override.fix_id}: stale: the Arabic changed since it was read (stays queued)`);
  const base = await liveRows(tx, override.hadith_id);
  const fixIds = new Set(base.chains.map((c) => c.chain_fix_id as string | null));
  const [last] = await tx<{ action: string }[]>`select action from chain_fix_applications where fix_id = ${override.fix_id} order by id desc limit 1`;
  const noChainStands = base.chains.length === 0 && Boolean(override.disposition) && last?.action === 'applied';
  if ((fixIds.size === 1 && fixIds.has(override.fix_id)) || noChainStands) {
    // Already written (by this tool or a load's replay); a later human confirmation only changes the status.
    if (override.structure_status && base.chains.some((c) => c.structure_status !== override.structure_status)) {
      await tx`update chains set structure_status = ${override.structure_status}, updated_at = now(), changed_in_dataset_version_id = ${version}
               where hadith_id = ${override.hadith_id} and retired_at is null`;
    }
    return false;
  }
  if ([...fixIds].some((id) => id && id !== override.fix_id)) return skip(`${override.fix_id}: another fix is in the database for this report; revert it first`);
  if (chainSha256(asBase(base)) !== override.base_chain_sha256) return skip(`${override.fix_id}: stale: the stored chain changed since the readers were compared with it; re-submit`);
  // Later reports that repeat this report's mentions would be left pointing at rewritten rows (hold cited_by_later_report).
  if (override.effect === 'replace_routes') {
    const [{ citing }] = await tx<{ citing: number }[]>`
      select count(*)::int as citing from chain_mentions m join chain_mentions w on w.id = m.inherited_from_mention_id
      where w.hadith_id = ${override.hadith_id} and w.retired_at is null and m.hadith_id <> w.hadith_id and m.retired_at is null`;
    if (citing > 0) return skip(`${override.fix_id}: held: ${citing} mention(s) of later reports repeat this report's chain; record the archive hold (chain-fix-hold.ts --scan)`);
  }
  // An inherited name repeats a written mention that must still stand, unchanged, in a rule-checked or verified chain.
  for (const chain of override.planned?.chains ?? []) {
    for (const mention of chain.mentions.filter((m) => m.inherited_from_mention_id)) {
      const cited = (await citedMentions(tx, { ...override, planned: { chains: [{ ...chain, mentions: [mention] }] } })).get(mention.inherited_from_mention_id!);
      if (!cited || cited.row.surface_ar !== mention.surface_ar || !['checked_by_rule', 'verified_by_reviewer'].includes(String(cited.chainStatus))) {
        return skip(`${override.fix_id}: stale: the earlier report's mention ${mention.inherited_from_mention_id} changed or is no longer rule-checked; re-submit`);
      }
    }
  }
  let written: Row = { chains: base.chains.map((c) => c.id) };
  if (override.effect === 'replace_routes') written = await writeRoutes(tx, override, base, version, tally);
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

function skip(message: string): string {
  console.log(`skip ${message}`);
  return message;
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
