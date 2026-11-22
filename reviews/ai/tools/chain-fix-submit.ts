/**
 * Submit chain-reader readings as chain fixes: validate each (the reader's own validator), bind it to the exact text by
 * SHA-256, compare it with the stored chain, and append it to reviews/ai/records/chain-fixes/submissions/<run id>.jsonl.
 * All or nothing: one bad fix refuses the whole envelope, with one line per problem. See reviews/ai/prompts/chain-fix-submission.md.
 * The format follows from the registered prompt the run names (`registeredPrompt`): v1 (routes with offsets), v2 (levels;
 * expanded by chain-reader/context), v3 (an envelope from chain-reader/v3/to_submission.py: `reader_output_v3` is expanded,
 * validated and held by chain-reader/v3; `run.second_reader` is recorded as a second run of the same reading, agreement
 * `canonical_equal_v3`), text (text and metadata checks: proposals only). A reader's other findings
 * (`fixes`, `text_check`, `metadata_check`) are filed as proposals in `proposals/<run id>.jsonl`, never applied.
 */
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import {
  appendRecords,
  argumentsOf,
  chainSha256,
  CHAIN_READER_SPECIALIST,
  DEFAULT_STORE,
  ENVELOPE_FORMAT,
  fixFieldProblems,
  fixIdOf,
  isBlindView,
  registeredPrompt,
  PROPOSAL_FORMAT,
  PROPOSAL_TARGET,
  proposalIdOf,
  readProposals,
  type Proposal,
  type ReaderFormat,
  readerPrompt,
  readSubmissions,
  REPOSITORY_ROOT,
  routesKey,
  runEngine,
  runProblems,
  storePaths,
  submissionIdOf,
  SUBMISSION_FORMAT,
  utcNow,
  type BaseChain,
  type EngineItem,
  type Submission,
  type View,
} from './chain-fix-lib';
import { sha256Hex } from './specialist-lib';

const USAGE = `usage: npx tsx reviews/ai/tools/chain-fix-submit.ts --envelope <envelope.json> --reports <reports.jsonl>
         [--database production] [--store <dir>] [--check-only]

  --envelope   ${ENVELOPE_FORMAT}: {"format", "run": {model_id, provider_runtime, run_id, started_at, finished_at,
               prompt_sha256, view}, "packet": "<packet .jsonl path>", "fixes": [{"output": <reader JSON>, "reason",
               "evidence": [{"quote"}], "external_citation": null | {"url" | "edition_locator", "quote"}}]}
  --reports    the packet's hidden half: one row per packet id with hadith_id, tradition, work, text_layout, stored_chains
               (chain-reader/pilot/reports.jsonl has this shape)
  --database   check the text hash and read the stored chain from production (read-only) instead of the snapshot
  --check-only validate and print, write nothing
Exit 0: every fix recorded (or already recorded). Exit 1: nothing recorded; each line says what to correct.`;

interface ReportRow {
  id: string;
  hadith_id: string;
  tradition: string;
  work: string;
  text: string;
  text_layout: string;
  snapshot_at?: string;
  stored_chains: { chain_id: string; branch: number; structure_status: string | null; surfaces: string[] }[];
}
interface LiveReport {
  record_id: string;
  source_work_id: string;
  tradition: string;
  arabic_sha256: string;
  reader_text: string;
  chains: BaseChain[];
}

const readJsonLines = <T>(file: string): T[] => readFileSync(file, 'utf8').split('\n').filter((line) => line.trim()).map((line) => JSON.parse(line) as T);

/** The text_ar inside a reader text (Pure Canon packets put the source's chain field and a blank line before it). */
function textArOf(layout: string, readerText: string): string {
  if (layout !== 'chain_field_then_matn') return readerText;
  const split = readerText.indexOf('\n\n');
  return split >= 0 ? readerText.slice(split + 2) : readerText;
}

function snapshotBase(row: ReportRow): BaseChain[] {
  return row.stored_chains.map((chain) => ({
    chain_id: chain.chain_id,
    branch: chain.branch,
    structure_status: chain.structure_status,
    mentions: chain.surfaces.map((surface, position) => ({
      id: `${chain.chain_id.replace(/^chain:/, 'mention:')}:${String(position).padStart(4, '0')}`,
      position,
      surface_ar: surface,
    })),
  }));
}

async function liveReports(hadithIds: string[]): Promise<Map<string, LiveReport>> {
  const { readLiveReports } = await import('./chain-fix-database');
  return readLiveReports(hadithIds);
}

async function main(): Promise<number> {
  const args = argumentsOf(process.argv.slice(2));
  if (args.has('help') || !args.get('envelope') || !args.get('reports')) {
    console.log(USAGE);
    return args.has('help') ? 0 : 2;
  }
  const problems: string[] = [];
  let envelope: Record<string, unknown>;
  try {
    envelope = JSON.parse(readFileSync(args.get('envelope')!, 'utf8')) as Record<string, unknown>;
  } catch (error) {
    console.error(`FAIL envelope: not readable JSON (${error instanceof Error ? error.message : String(error)})`);
    return 1;
  }
  if (envelope.format !== ENVELOPE_FORMAT) problems.push(`format: must be "${ENVELOPE_FORMAT}"`);
  const run = (envelope.run ?? {}) as Record<string, unknown>;
  // Any registered reader prompt is accepted, and the format follows from it; an unregistered hash is refused.
  const registered = registeredPrompt(run.prompt_sha256);
  const readerFormat = (registered?.format ?? (run.reader_format as ReaderFormat | undefined) ?? 'v1') as ReaderFormat;
  const prompt = registered ?? readerPrompt(['v1', 'v2', 'v3', 'text'].includes(readerFormat) ? readerFormat : 'v1');
  problems.push(...runProblems(run, prompt.sha256));
  const second = run.second_reader as Record<string, unknown> | undefined;
  if (second !== undefined) {
    // The second pass of a v3 envelope: its own model, run and times; the reading is the first pass's (canonical-equal).
    problems.push(...runProblems({ ...second, provider_runtime: run.provider_runtime, view: run.view, prompt_sha256: run.prompt_sha256 }, prompt.sha256)
      .map((problem) => problem.replace(/^run\./, 'run.second_reader.')));
    if (second.run_id === run.run_id) problems.push('run.second_reader.run_id: the second reader is another run');
  }
  const fixes = Array.isArray(envelope.fixes) ? (envelope.fixes as Record<string, unknown>[]) : [];
  if (fixes.length === 0) problems.push('fixes: a non-empty list');
  // The packet path as the envelope writes it: from the repository root, or from chain-reader/ (where v3/RUN.md runs
  // to_submission.py), or from the envelope's own folder.
  const packetPath = typeof envelope.packet === 'string'
    ? [path.resolve(REPOSITORY_ROOT, envelope.packet), path.resolve(REPOSITORY_ROOT, 'datasets', 'hadith-data', 'chain-reader', envelope.packet),
      path.resolve(path.dirname(path.resolve(args.get('envelope')!)), envelope.packet)].find((candidate) => existsSync(candidate)) ?? envelope.packet
    : '';
  let packet = new Map<string, Record<string, unknown>>();
  let packetSha256 = '';
  try {
    const bytes = readFileSync(packetPath);
    packetSha256 = sha256Hex(bytes);
    packet = new Map(readJsonLines<Record<string, unknown>>(packetPath).map((item) => [String(item.id), item]));
  } catch {
    problems.push(`packet: ${String(envelope.packet)} is not a readable packet file (.jsonl of {"id", "text"})`);
  }
  const reports = new Map(readJsonLines<ReportRow>(args.get('reports')!).map((row) => [row.id, row]));
  if (problems.length > 0) return fail(problems);

  const view = run.view as View;
  type Pending = EngineItem & { report: ReportRow; fix: Record<string, unknown>; live?: LiveReport; baseChains: BaseChain[] };
  const items: Pending[] = [];
  const outputIds = fixes.map((fix) => String((fix.output as { id?: unknown } | undefined)?.id ?? ''));
  if (args.has('database') && args.get('database') !== 'production') return fail(['--database: only "production" is supported (read-only)']);
  const live = args.get('database') === 'production'
    ? await liveReports(outputIds.map((id) => reports.get(id)?.hadith_id).filter((id): id is string => !!id))
    : null;

  fixes.forEach((fix, index) => {
    const where = `fixes[${index}]`;
    problems.push(...fixFieldProblems(fix, where));
    const id = outputIds[index];
    const item = packet.get(id);
    const report = reports.get(id);
    if (!item) return void problems.push(`${where}.output.id: ${JSON.stringify(id)} is not an item of the packet`);
    if (!report) return void problems.push(`${where}.output.id: ${id} has no row in --reports`);
    if (typeof item.text !== 'string' || item.text !== report.text) return void problems.push(`${where}: stale text: the packet's text for ${id} (sha ${sha256Hex(String(item.text))}) is not the report's current text (sha ${sha256Hex(report.text)}); re-read the current text`);
    // A v2 packet carries a context block (work conventions, the sources' own claims, previous reports), never the stored
    // chain: a reading from it is still blind to the stored chain and to other readers.
    const allowed = view === 'text_only' && readerFormat === 'v1' ? ['id', 'text'] : ['id', 'text', 'context'];
    if (isBlindView(view) && Object.keys(item).some((key) => !allowed.includes(key))) {
      return void problems.push(`${where}: the packet shows more than ${allowed.join(', ')} (${Object.keys(item).join(', ')}); a ${view} reading needs a packet without the stored chain`);
    }
    if (isBlindView(view) && /"stored_(chains?|surfaces)"/.test(JSON.stringify(item.context ?? null))) {
      return void problems.push(`${where}: the packet's context carries the stored chain; a ${view} reading needs a packet without it`);
    }
    if (readerFormat === 'v3' && (typeof fix.reader_output_v3 !== 'object' || fix.reader_output_v3 === null)) {
      return void problems.push(`${where}.reader_output_v3: a v3 reading carries the reader's unchanged output (to_submission.py writes it)`);
    }
    const text = item.text;
    let base: BaseChain[] = snapshotBase(report);
    let sourceWorkId = `${report.tradition}:${report.work}`;
    if (live) {
      const current = live.get(report.hadith_id);
      if (!current) return void problems.push(`${where}: ${report.hadith_id} is not a live report in production`);
      if (current.reader_text !== text) {
        return void problems.push(`${where}: stale text: ${report.hadith_id} now reads differently from the packet (hash ${sha256Hex(current.reader_text)}, packet ${sha256Hex(text)}); re-read the current text`);
      }
      base = current.chains;
      sourceWorkId = current.source_work_id;
    }
    const inherited = base.flatMap((chain) => chain.mentions).filter((mention) => mention.inherited_from_mention_id);
    if (inherited.length > 0) return void problems.push(`${where}: ${report.hadith_id}'s stored chain repeats names from an earlier report (${inherited[0].id}); out of scope for a reader of this text`);
    items.push({
      key: String(index),
      text,
      expected_id: id,
      output: readerFormat === 'v3' ? fix.reader_output_v3 : fix.output,
      base: { chains: base.map((chain) => ({ branch: chain.branch, mentions: chain.mentions })) },
      record_id: report.hadith_id.replace(/^hadith:/, ''),
      source_work_id: sourceWorkId,
      evidence: Array.isArray(fix.evidence) ? (fix.evidence as { quote: string }[]).map((entry) => entry.quote) : [],
      require_coverage: view === 'text_and_stored_chain',
      reader_format: readerFormat,
      context: item.context,
      report,
      fix,
      live: live?.get(report.hadith_id),
      baseChains: base,
    });
  });
  if (problems.length > 0) return fail(problems);

  const results = runEngine(items.map((item): EngineItem => ({
    key: item.key, text: item.text, expected_id: item.expected_id, output: item.output, base: item.base, record_id: item.record_id,
    source_work_id: item.source_work_id, evidence: item.evidence, require_coverage: item.require_coverage,
    reader_format: item.reader_format, context: item.context,
  })));
  for (const result of results) for (const error of result.errors) problems.push(`fixes[${result.key}] (${items[Number(result.key)].expected_id}): ${error}`);
  if (problems.length > 0) return fail(problems);

  const submittedAt = utcNow();
  // Findings beyond chain structure: filed for reviewers with their sources and the reader's provenance, never applied.
  const proposals: Proposal[] = results.flatMap((result) => {
    const item = items[Number(result.key)];
    const arabicSha256 = item.live ? item.live.arabic_sha256 : sha256Hex(textArOf(item.report.text_layout, item.text));
    return result.proposals.map((finding) => ({
      format: PROPOSAL_FORMAT,
      proposal_id: proposalIdOf(item.report.hadith_id, finding.kind, finding.reason, finding.evidence, String(run.run_id)),
      hadith_id: item.report.hadith_id,
      record_id: item.record_id,
      source_work_id: item.source_work_id,
      kind: finding.kind,
      target: PROPOSAL_TARGET[finding.kind] ?? 'other',
      reason: finding.reason,
      confidence: finding.confidence,
      differences: finding.differences,
      compared: finding.compared ?? [],
      evidence: finding.evidence,
      arabic_sha256: arabicSha256,
      reader_format: readerFormat,
      model_id: String(run.model_id),
      provider_runtime: String(run.provider_runtime),
      orchestrator_run_id: String(run.run_id),
      prompt_path: prompt.path,
      prompt_sha256: prompt.sha256,
      packet_path: path.relative(REPOSITORY_ROOT, packetPath).replace(/\\/g, '/'),
      packet_sha256: packetSha256,
      packet_item_id: item.expected_id,
      submitted_at: submittedAt,
    }));
  });
  const records: Submission[] = results.filter((result) => result.planned !== null).map((result) => {
    const item = items[Number(result.key)];
    const baseChains = item.baseChains;
    const textAr = textArOf(item.report.text_layout, item.text);
    const arabicSha256 = item.live ? item.live.arabic_sha256 : sha256Hex(textAr);
    const readerTextSha256 = sha256Hex(item.text);
    const key = routesKey(result.planned!);
    const fixId = fixIdOf(item.report.hadith_id, arabicSha256, readerTextSha256, key);
    const { fix_kinds: fixKinds, ...comparison } = result.comparison!;
    return {
      format: SUBMISSION_FORMAT,
      submission_id: submissionIdOf(fixId, String(run.run_id), String(run.model_id)),
      fix_id: fixId,
      routes_key: key,
      hadith_id: item.report.hadith_id,
      record_id: item.record_id,
      source_work_id: item.source_work_id,
      tradition: item.live?.tradition ?? item.report.tradition,
      text_layout: item.report.text_layout,
      arabic_sha256: arabicSha256,
      reader_text_sha256: readerTextSha256,
      text_checked_against: item.live ? 'database' : 'snapshot',
      base: { chains: baseChains, chain_sha256: chainSha256(baseChains), read_from: item.live ? `production@${submittedAt}` : `snapshot@${item.report.snapshot_at ?? 'unknown'}` },
      reading: { ...result.reading!, offsets_repaired: result.offsets_repaired },
      fix_kinds: fixKinds,
      comparison,
      planned: result.planned!,
      reason: String(item.fix.reason).trim(),
      evidence: item.evidence.map((quote) => ({ quote })),
      computed_evidence: result.computed_evidence,
      external_citation: (item.fix.external_citation as Submission['external_citation']) ?? null,
      view,
      reader_format: readerFormat,
      holds: result.holds,
      derived_links: result.derived_links,
      review_kind: 'specialist',
      label: 'AI reviewed',
      specialist_id: CHAIN_READER_SPECIALIST.id,
      specialist_version: CHAIN_READER_SPECIALIST.version,
      prompt_path: prompt.path,
      prompt_version: prompt.version,
      prompt_sha256: prompt.sha256,
      model_id: String(run.model_id),
      provider_runtime: String(run.provider_runtime),
      orchestrator_run_id: String(run.run_id),
      packet_path: path.relative(REPOSITORY_ROOT, packetPath).replace(/\\/g, '/'),
      packet_sha256: packetSha256,
      packet_item_id: item.expected_id,
      started_at: String(run.started_at),
      finished_at: String(run.finished_at),
      submitted_at: submittedAt,
    };
  });

  // A v3 envelope's second pass: the same reading recorded as that run's, so the agreement rule counts two independent runs.
  if (second !== undefined) {
    for (const record of [...records]) {
      records.push({
        ...record,
        submission_id: submissionIdOf(record.fix_id, String(second.run_id), String(second.model_id)),
        model_id: String(second.model_id),
        orchestrator_run_id: String(second.run_id),
        started_at: String(second.started_at),
        finished_at: String(second.finished_at),
        agreement_basis: 'canonical_equal_v3',
      });
    }
  }
  for (const record of records) {
    const held = record.holds?.length ? ` (held: ${record.holds.map((hold) => hold.code).join(', ')})` : '';
    console.log(`ok   ${record.packet_item_id} ${record.hadith_id}: ${record.fix_kinds.join(', ')}${record.reading.offsets_repaired ? ' (offsets re-found from the surfaces)' : ''}${held} -> ${record.fix_id}`);
  }
  for (const proposal of proposals) console.log(`prop ${proposal.packet_item_id} ${proposal.hadith_id}: ${proposal.kind} -> ${proposal.proposal_id}`);
  if (args.has('check-only')) return 0;
  const paths = storePaths(args.get('store') ?? DEFAULT_STORE);
  const knownProposals = new Set(readProposals(paths).map((proposal) => proposal.proposal_id));
  appendRecords(path.join(paths.proposals, `${String(run.run_id)}.jsonl`), proposals.filter((proposal) => !knownProposals.has(proposal.proposal_id)));
  const known = new Set(readSubmissions(paths).map((s) => s.submission_id));
  const fresh = records.filter((record) => !known.has(record.submission_id));
  for (const record of records) if (known.has(record.submission_id)) console.log(`dup  ${record.packet_item_id}: already recorded as ${record.submission_id}; nothing to do`);
  for (const runId of [...new Set(fresh.map((record) => record.orchestrator_run_id))]) {
    appendRecords(path.join(paths.submissions, `${runId}.jsonl`), fresh.filter((record) => record.orchestrator_run_id === runId));
  }
  console.log(`recorded ${fresh.length} of ${records.length} in ${path.relative(REPOSITORY_ROOT, paths.submissions).replace(/\\/g, '/')}/${String(run.run_id)}.jsonl`);
  return 0;
}

function fail(problems: string[]): number {
  for (const problem of problems) console.error(`FAIL ${problem}`);
  console.error(`nothing recorded: correct the ${problems.length} problem(s) above and submit the whole envelope again`);
  return 1;
}

main().then(
  (code) => (process.exitCode = code),
  (error) => {
    console.error(`FAIL ${error instanceof Error ? error.message : String(error)}`);
    process.exitCode = 1;
  },
);
