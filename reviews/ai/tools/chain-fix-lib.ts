/**
 * Chain-fix pipeline: submission, store, agreement rule, final review and the replayed overrides file. Arabic rules
 * (validation, comparison, planned rows) are in datasets/hadith-data/chain-fixes/chain_fix_engine.py, called once per
 * invocation. Design: docs/review/chain-fix-pipeline.md; rationale: reviews/ai/AGENTS.md §Chain fixes.
 */
import { spawnSync } from 'node:child_process';
import {
  closeSync,
  existsSync,
  mkdirSync,
  openSync,
  readdirSync,
  readFileSync,
  renameSync,
  statSync,
  unlinkSync,
  writeFileSync,
  writeSync,
} from 'node:fs';
import path from 'node:path';
import { gzipSync } from 'node:zlib';
import { sha256Hex, UTC_TIMESTAMP } from './specialist-lib';

export const REPOSITORY_ROOT = path.resolve(__dirname, '..', '..', '..');
export const ENVELOPE_FORMAT = 'shura-chain-fix-envelope/1';
/** Agreed readings that find no isnad in the text (chain-reader/v3_1/to_submission_v3_1.py): the stored chain retires. */
export const NO_CHAIN_ENVELOPE_FORMAT = 'shura-chain-no-chain-envelope/1';
/** The one disposition a no-chain fix carries; the page says the report writes no chain. */
export const NO_CHAIN_DISPOSITION = 'no_chain_by_reading';
export const SUBMISSION_FORMAT = 'shura-chain-fix-submission/1';
export const REVIEW_FORMAT = 'shura-chain-fix-review/1';
export const TRANSITION_FORMAT = 'shura-chain-fix-transition/1';
export const APPLICATION_FORMAT = 'shura-chain-fix-application/1';
export const OVERRIDE_FORMAT = 'shura-chain-fix-override/1';
export const PROPOSAL_FORMAT = 'shura-reader-proposal/1';
export const PROPOSAL_REVIEW_FORMAT = 'shura-reader-proposal-review/1';
export const ARCHIVE_HOLD_FORMAT = 'shura-chain-fix-archive-hold/1';
export const DEFAULT_STORE = path.join(REPOSITORY_ROOT, 'reviews', 'ai', 'records', 'chain-fixes');
export const DEFAULT_OVERRIDES = path.join(REPOSITORY_ROOT, 'datasets', 'hadith-data', 'chain-fixes', 'accepted_overrides.jsonl.gz');
export const ENGINE_PATH = path.join(REPOSITORY_ROOT, 'datasets', 'hadith-data', 'chain-fixes', 'chain_fix_engine.py');

/** The chain reader as /method lists it (src/lib/review/procedures.ts is the one registry). */
export { CHAIN_READER_SPECIALIST } from '../../../src/lib/review/procedures';
/** The v1 entry this pipeline was built with, kept for records written before 0019. */
export const CHAIN_READER_SPECIALIST_V1 = {
  kind: 'specialist',
  id: 'chain-reader',
  version: '1.0.0',
  claimKinds: ['chain_structure'],
  title: 'Isnad reader',
  status: 'pilot_ready',
  question: 'Which routes of transmission does this report’s Arabic write, name by name?',
  prompt: 'datasets/hadith-data/chain-reader/prompt.md',
  packet: ['The report’s Arabic exactly as stored (Pure Canon: the source’s chain field, a blank line, then the text)', 'Nothing else: no stored chain, no other reader'],
  recommendedModel: 'claude-haiku-4-5',
  modelReason: 'A mechanical reading checked by a validator and by a second independent reader; disputes go to a human.',
  notThisModel: [],
  measured: null,
  unmeasured: 'Pilot set built (datasets/hadith-data/chain-reader/pilot/, 284 labelled reports); agreement precision not yet measured.',
} as const;

/** What a reader saw: the text alone; the text and the sources' context (reader v3), never the stored chain; or the stored chain too. */
export const VIEWS = ['text_only', 'text_and_context', 'text_and_stored_chain'] as const;
/** Blind to the stored chain (and to every other reader): counts as the independent run the agreement rule needs. */
export const isBlindView = (view: string) => view === 'text_only' || view === 'text_and_context';
export type View = (typeof VIEWS)[number];
export const REVIEW_DECISIONS = ['confirmed', 'rejected', 'superseded'] as const;
export type ReviewDecision = (typeof REVIEW_DECISIONS)[number];
/** `accepted` is "agreed and passed the auto-apply rule" (in the store everything agreed passes it: see the design note). */
export const STATES = ['submitted', 'disputed', 'outvoted', 'held', 'accepted', 'confirmed', 'rejected', 'superseded', 'stale', 'awaiting_human', 'set_aside_by_ai'] as const;
/** Reader output formats, one per registered prompt: v1 (routes with offsets), v2 (levels, expanded by the tool), v3 to v3_4 (groups with context), text (text and metadata checks only). */
export const READER_FORMATS = ['v1', 'v2', 'v3', 'v3_1', 'v3_2', 'v3_4', 'text'] as const;
export type ReaderFormat = (typeof READER_FORMATS)[number];
/** Each format's prompt, hashed on every submission (a reading under an older prompt is re-run, not recorded). */
export const READER_PROMPTS: Record<ReaderFormat, string> = {
  v1: 'datasets/hadith-data/chain-reader/prompt.md',
  v2: 'datasets/hadith-data/chain-reader/context/prompt-v2.md',
  v3: 'datasets/hadith-data/chain-reader/v3/prompt-v3.md',
  v3_1: 'datasets/hadith-data/chain-reader/v3_1/prompt-v3_1.md',
  v3_2: 'datasets/hadith-data/chain-reader/v3_2/prompt-v3_2.md',
  v3_4: 'datasets/hadith-data/chain-reader/v3_4/prompt-v3_4.md',
  text: 'datasets/hadith-data/chain-reader/context/prompt-v2-text.md',
};
/**
 * The reader tool that validated, expanded and held a v3-shaped reading (chain_fix_engine.py `TOOLS`). Separate from the prompt:
 * batch 001 was read under prompt v3 and re-triaged by tool v3_1; a v3.1 reading needs tool v3_1. Absent: the prompt's own tool.
 */
export const TOOL_VERSIONS = ['v3', 'v3_1', 'v3_2', 'v3_3', 'v3_4'] as const;
export type ToolVersion = (typeof TOOL_VERSIONS)[number];
/** Formats whose reading is the reader's own v3-shaped output (`reader_output_v3`), expanded and held by a reader tool. */
export type V3ShapedFormat = 'v3' | 'v3_1' | 'v3_2' | 'v3_4';
export const isV3Shaped = (format: string): format is V3ShapedFormat => format === 'v3' || format === 'v3_1' || format === 'v3_2' || format === 'v3_4';
/** Tools that may read a reading made under each v3-shaped prompt (chain_fix_engine.py `TOOLS_FOR_FORMAT`): a later tool reads an earlier prompt's output, never the reverse. */
export const TOOLS_FOR_FORMAT: Record<V3ShapedFormat, readonly ToolVersion[]> = {
  v3: ['v3', 'v3_1', 'v3_2', 'v3_3', 'v3_4'], v3_1: ['v3_1', 'v3_2', 'v3_3', 'v3_4'], v3_2: ['v3_2', 'v3_3', 'v3_4'], v3_4: ['v3_4'],
};
/** Holds the owner lifted (code -> ruling): a lifted code no longer keeps a fix back; its record stays. reviews/ai/AGENTS.md §Rule-checked ruling. */
export const LIFTED_HOLD_CODES: Record<string, string> = {
  stored_chain_checked_by_rule: 'owner ruling 2026-11-22: the agreed reading is applied and the report leaves teacher and student lists until a reviewer confirms',
};
/** The AI reviewer's prompts by version (chain-reader/reviewer); 1.0.0 is the pilot's only. */
export const REVIEWER_PROMPTS: Record<string, string> = {
  '1.1.0': 'datasets/hadith-data/chain-reader/reviewer/prompt-reviewer-v1_1.md',
  '1.0.0': 'datasets/hadith-data/chain-reader/reviewer/prompt-reviewer-v1.md',
};
export const REVIEWER_SPECIALIST_ID = 'chain-reviewer';
/** What a review by the AI reviewer led to (review_rules_v1_1.ACTION_CLASS keys). */
export type ReviewOutcome = 'apply_reading' | 'apply_reader_a' | 'apply_reader_b' | 'apply_correction' | 'apply_no_chain' | 'label_ai_reviewed' | 'label_disputed'
  | 'queue_for_human' | 'keep_held' | 'discard_reading' | 'revert_to_stored' | 'human_decides';
/** An AI review's mark on a fix's state (model, run, time); never worded "verified". */
export interface AiMark {
  model_id: string;
  run_id: string;
  at: string;
  review_id: string;
  outcome: ReviewOutcome;
  decision: string;
}
/** A previous report an inherited reading takes names from (to_submission_v3_1.py `inherited_from`), resolved to the archive. */
export interface InheritedSource {
  ref: string;
  previous_report_id: string | null;
  supplies: string | null;
  surfaces: string[];
}
export interface Hold {
  code: string;
  detail: string;
}
export type State = (typeof STATES)[number];

export interface Link {
  surface: string;
  start: number;
  end: number;
  kind: string;
}
export interface BaseMention {
  id: string;
  position: number;
  surface_ar: string;
  inherited_from_mention_id?: string | null;
}
export interface BaseChain {
  chain_id: string;
  branch: number;
  structure_status: string | null;
  mentions: BaseMention[];
}
export interface PlannedMention {
  id: string;
  position: number;
  surface_ar: string;
  surface_normalized: string;
  teacher_context_normalized: string | null;
  student_context_normalized: string | null;
  review_unit_id: string;
  review_unit_fine_id: string;
  reader_kind: string;
  link_kind_if_new: string;
  /** Offsets in the reader text; null for a name inherited from an earlier report. */
  span: [number, number] | null;
  kept_mention_id: string | null;
  carry_identity: boolean;
  /** The cited report's written mention this one repeats (its root), for an inherited name. */
  inherited_from_mention_id?: string | null;
}
export interface PlannedChain {
  id: string;
  branch: number;
  length: number;
  suspension: string | null;
  extraction_method: string;
  mentions: PlannedMention[];
  /** The compiler's own `direct`/`indirect` mark for this route, from its opening words (work_register.py `route_links`); absent on the first chain and on fixes planned before it. */
  compiler_link?: 'direct' | 'indirect';
  /** Tool v3.4: the saying (1 = first in the text) whose chain this route is; the page heads it "Chain of the first saying". */
  saying?: number;
}
/** Tool v3.4: one saying of a two-saying report, its page label and opening words (an exact stretch of the reader text). */
export interface PlannedSaying {
  saying: number;
  label: string;
  opens: string;
  start: number;
  end: number;
}
/** A remark that another version names another transmitter («بمثل حديث X»): kept with the fix and shown under the chain, never a route. */
export interface VariantRemark {
  /** The transmitters the other version names, levels of alternatives (as the reader wrote them). */
  surfaces: string[][];
  /** The sentence of the remark, an exact stretch of the reader text. */
  quote: string;
  start: number;
  end: number;
  /** Which reader pass wrote it (`a`, `b`); a remark that only one pass wrote is marked so. */
  passes: ('a' | 'b')[];
  /** The runs behind each pass, filled by the submit tool. */
  by?: { pass: 'a' | 'b'; run_id: string; model_id: string }[];
}
export interface PlannedChains {
  chains: PlannedChain[];
  variant_remarks?: VariantRemark[];
  sayings?: PlannedSaying[];
}
export interface ExternalCitation {
  url?: string;
  edition_locator?: string;
  quote: string;
}

export interface Submission {
  format: typeof SUBMISSION_FORMAT;
  submission_id: string;
  fix_id: string;
  routes_key: string;
  hadith_id: string;
  record_id: string;
  source_work_id: string;
  tradition: string;
  text_layout: string;
  arabic_sha256: string;
  reader_text_sha256: string;
  text_checked_against: 'database' | 'snapshot';
  base: { chains: BaseChain[]; chain_sha256: string; read_from: string };
  reading: { routes: { links: Link[]; shared_tail_from: number | null }[]; matn_start: number; notes: string[]; offsets_repaired: boolean };
  fix_kinds: string[];
  comparison: Record<string, unknown>;
  planned: PlannedChains;
  reason: string;
  evidence: { quote: string }[];
  computed_evidence: { quote: string; start: number; end: number; for: string }[];
  external_citation: ExternalCitation | null;
  view: View;
  /** v1 unless the reader wrote levels (v2); a v2 reading is expanded and validated by chain-reader/context. */
  reader_format?: ReaderFormat;
  /** Why the tool holds this reading (chain-reader/context/HOLDS.md, v3/HOLDS.md): never auto-applied while any stands. */
  holds?: Hold[];
  /** Derived links (kind, origin) the reading carries beside the written ones: the page labels them; planned rows never hold them. */
  derived_links?: DerivedLink[];
  /** How this run's reading was found equal to another's: `canonical_equal_v3` for the second pass of a v3 envelope. */
  agreement_basis?: string;
  /** The reader tool (v3, v3_1) that validated, expanded and held this reading; the prompt fields name what the reader ran. */
  tool_version?: ToolVersion;
  /** `no_chain_by_reading`: the readers found no isnad in the text; applying retires the stored chain. */
  disposition?: typeof NO_CHAIN_DISPOSITION | null;
  /** The previous reports an inherited reading takes names from, as submitted and resolved. */
  inherited_from?: InheritedSource[];
  /** v3.2: remarks that another version names another transmitter, recorded with the fix (the union of both passes), never a route. */
  variant_remarks?: VariantRemark[];
  /** A fix written from the AI reviewer's correction (two runs, the same routes): the readers' fix it corrects. */
  corrects_fix_id?: string;
  review_kind: 'specialist';
  label: 'AI reviewed';
  specialist_id: string;
  specialist_version: string;
  prompt_path: string;
  prompt_version: string;
  prompt_sha256: string;
  model_id: string;
  provider_runtime: string;
  orchestrator_run_id: string;
  packet_path: string;
  packet_sha256: string;
  packet_item_id: string;
  started_at: string;
  finished_at: string;
  submitted_at: string;
}

export interface Review {
  format: typeof REVIEW_FORMAT;
  review_id: string;
  fix_id: string;
  hadith_id: string;
  reviewer_kind: 'human' | 'ai';
  reviewer: string;
  model_id: string | null;
  prompt_path: string | null;
  prompt_sha256: string | null;
  /** A human's decision; null on an AI reviewer's row, whose vocabulary is `review_decision` (only a human confirmation is "verified"). */
  decision: ReviewDecision | null;
  superseded_by: string | null;
  note: string;
  citation: ExternalCitation | null;
  reviewed_at: string;
  /** AI reviewer rows (chain-review-record.ts): the reviewer's own decision, what review_rules_v1_1.outcome did with it, and the run. */
  review_decision?: string;
  outcome?: ReviewOutcome;
  /** The fix's holds and status when the review was recorded: an apply outcome stands only while no hold has come since. */
  codes_at_review?: string[];
  status_at_review?: 'held' | 'pending' | 'applied';
  run_id?: string;
  pass?: number;
  packet_path?: string;
  packet_sha256?: string;
  packet_item_id?: string;
  started_at?: string;
  finished_at?: string;
  specialist_version?: string;
  uncertainty?: string;
  question?: string | null;
  reasons?: unknown[];
  variant_verdicts?: unknown[];
  corrected_reading?: unknown;
  /** The second independent review a correction needs: its run and whether it wrote the same routes. */
  second_run_id?: string | null;
  second_run_agrees?: boolean | null;
}

/** Bytes of a prompt file and its front matter `version` (the reader prompt says `reader:`, a specialist prompt `specialist:`). */
export function readerPrompt(format: ReaderFormat = 'v1'): { path: string; version: string; sha256: string } {
  const relative = READER_PROMPTS[format];
  const bytes = readFileSync(path.join(REPOSITORY_ROOT, relative));
  const front = /^---\n([\s\S]*?)\n---\n/.exec(bytes.toString('utf8').replace(/\r\n/g, '\n'));
  const version = front && /^version:\s*(.+)$/m.exec(front[1])?.[1].trim();
  if (!version) throw new Error(`${relative}: no version in front matter`);
  return { path: relative, version, sha256: sha256Hex(bytes) };
}

/** SHA-256 of the stored chain as surfaces per branch: the apply refuses a report whose live chain no longer hashes to it. */
export function chainSha256(chains: readonly BaseChain[]): string {
  const canonical = [...chains].sort((a, b) => a.branch - b.branch).map((chain) => [chain.branch, chain.mentions.map((mention) => mention.surface_ar)]);
  return sha256Hex(JSON.stringify(canonical));
}

/** What is applied, per route: span and link kind. Route order is canonical (text order), so two readers agree regardless of order. */
export function routesKey(planned: { chains: PlannedChain[] }): string {
  // A written name is its span; an inherited one is the mention it repeats (written keys are unchanged from before 0021).
  return sha256Hex(JSON.stringify(planned.chains.map((chain) => [chain.suspension, chain.mentions.map((m) =>
    m.span ? [m.span[0], m.span[1], m.link_kind_if_new] : ['inherited', m.inherited_from_mention_id ?? null, m.link_kind_if_new])])));
}

export const fixIdOf = (hadithId: string, arabicSha256: string, readerTextSha256: string, key: string) =>
  `chain-fix:${sha256Hex([hadithId, arabicSha256, readerTextSha256, key].join('\u001f')).slice(0, 24)}`;
export const submissionIdOf = (fixId: string, runId: string, modelId: string) =>
  `chain-fix-submission:${sha256Hex([fixId, runId, modelId].join('\u001f')).slice(0, 24)}`;

const isText = (value: unknown): value is string => typeof value === 'string' && value.trim().length > 0;
const SAFE_NAME = /^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$/;
const GENERIC_MODELS = new Set(['model', 'ai', 'claude', 'haiku', 'gpt', 'llm', 'unknown']);

/**
 * The registered reader prompts (the registry: READER_PROMPTS, each file hashed as it stands now). A reading is accepted under
 * any registered prompt and refused under any other hash; its format follows from the prompt it ran under.
 */
export function registeredPrompt(sha256: unknown): { format: ReaderFormat; path: string; version: string; sha256: string } | null {
  for (const format of READER_FORMATS) {
    const prompt = readerPrompt(format);
    if (prompt.sha256 === sha256) return { format, ...prompt };
  }
  return null;
}

/** Problems with the run half of an envelope (who read, under which prompt, when). */
export function runProblems(run: Record<string, unknown>, currentPromptSha256: string): string[] {
  const problems: string[] = [];
  if (!isText(run.model_id) || GENERIC_MODELS.has(run.model_id.toLowerCase()) || !/\d/.test(run.model_id)) {
    problems.push('run.model_id: give the exact model id the runtime reports (for example claude-haiku-4-5)');
  }
  if (!isText(run.provider_runtime)) problems.push('run.provider_runtime: say how the reader ran (for example "Claude Code subagent, fresh context")');
  if (!isText(run.run_id) || !SAFE_NAME.test(run.run_id)) problems.push('run.run_id: letters, digits, dot, dash or underscore, one id per reader run');
  for (const key of ['started_at', 'finished_at']) {
    if (!isText(run[key]) || !UTC_TIMESTAMP.test(run[key] as string)) problems.push(`run.${key}: UTC time like 2026-11-22T14:00:00Z`);
  }
  if (isText(run.started_at) && isText(run.finished_at) && run.finished_at < run.started_at) problems.push('run.finished_at is before run.started_at');
  if (!VIEWS.includes(run.view as View)) problems.push(`run.view: one of ${VIEWS.join(', ')} (text_only when the reader saw only the text)`);
  if (run.reader_format !== undefined && !READER_FORMATS.includes(run.reader_format as ReaderFormat)) {
    problems.push(`run.reader_format: one of ${READER_FORMATS.join(', ')} (v1 when absent)`);
  }
  if (run.prompt_sha256 !== currentPromptSha256) {
    problems.push(`run.prompt_sha256: ${String(run.prompt_sha256)} is not a registered reader prompt (${READER_FORMATS.map((format) => `${READER_PROMPTS[format]} ${readerPrompt(format).sha256.slice(0, 12)}`).join('; ')}); re-run the reader with a registered prompt`);
  }
  return problems;
}

/** Problems with one fix's reason and optional external citation (the quotes are checked by the engine). */
export function fixFieldProblems(fix: Record<string, unknown>, where: string): string[] {
  const problems: string[] = [];
  if (!isText(fix.reason) || (fix.reason as string).length > 400) problems.push(`${where}.reason: one or two sentences (at most 400 characters)`);
  if (!Array.isArray(fix.evidence) || !fix.evidence.every((entry) => isText((entry as { quote?: unknown })?.quote))) {
    problems.push(`${where}.evidence: a list of {"quote": "<words copied exactly from the text>"}`);
  }
  const citation = fix.external_citation as Record<string, unknown> | null | undefined;
  if (citation !== undefined && citation !== null) {
    const hasUrl = isText(citation.url) && /^https?:\/\/\S+$/.test(citation.url);
    const hasEdition = isText(citation.edition_locator);
    if (!hasUrl && !hasEdition) problems.push(`${where}.external_citation: give "url" (http or https) or "edition_locator" (work, volume, page)`);
    if (!isText(citation.quote)) problems.push(`${where}.external_citation.quote: the exact words you relied on from that source`);
  }
  return problems;
}

export interface EngineItem {
  key: string;
  text: string;
  expected_id: string;
  output: unknown;
  base: { chains: { branch: number; mentions: { id: string; surface_ar: string }[] }[] };
  record_id: string;
  source_work_id: string;
  evidence: string[];
  require_coverage: boolean;
  reader_format?: ReaderFormat;
  context?: unknown;
  /** v3: the second reader's output, so `needs_ruling` holds only when both readers set it (holds_v3.py). */
  other_output?: unknown;
  /** v3.2 tool: the pipeline carries variant remarks, so a reading with one is not held for it (`--variant-notes-supported`). */
  variant_notes_supported?: boolean;
  /** v3.4 tool: the pipeline stores each route's saying, so a two-saying reading is not held for it (`--sayings-supported`). */
  sayings_supported?: boolean;
  tool_version?: ToolVersion;
  /** Per `inherited_from` ref: the previous report's live chains (status and mentions), for inherited names. */
  previous?: Record<string, { hadith_id: string; chains: BaseChain[] }>;
}
/** A link the reader derived (compiler head, inherited from an earlier report) or named from the text (an Imam), with its origin. */
export interface DerivedLink {
  route: number;
  position: number;
  kind: 'compiler_head' | 'inherited' | 'imam_in_text';
  surface: string;
  origin: string | null;
  span: [number, number] | null;
}
/** A reader's finding beyond the chain, as the engine returns it (validate_v2.py `fixes`, `text_check`, `metadata_check`). */
export interface ReaderFinding {
  kind: string;
  reason: string;
  evidence: unknown[];
  confidence: string;
  differences: { ours: string; theirs: string; source: string; field?: string; url?: string }[];
  compared?: string[];
}
export interface EngineResult {
  key: string;
  errors: string[];
  reading: Submission['reading'] | null;
  offsets_repaired: boolean;
  comparison: (Record<string, unknown> & { fix_kinds: string[] }) | null;
  planned: PlannedChains | null;
  computed_evidence: Submission['computed_evidence'];
  holds: Hold[];
  proposals: ReaderFinding[];
  needs_ruling: boolean;
  derived_links: DerivedLink[];
  disposition: typeof NO_CHAIN_DISPOSITION | null;
  /** v3.2: variant groups kept as remarks about another version, never routes. */
  variant_remarks?: VariantRemark[];
  /** The evidence quotes as the text writes them (its own vowel marks), located letters-exact. */
  evidence_quotes?: string[];
}

/**
 * A reader's proposal beyond chain structure (identity, lexicon date, duplicate records, garbled text, translation, text or
 * metadata differing from a source). Never applied automatically: reviewers decide (reviews/ai/AGENTS.md §Proposals).
 */
export interface Proposal {
  format: typeof PROPOSAL_FORMAT;
  proposal_id: string;
  hadith_id: string;
  record_id: string;
  source_work_id: string;
  kind: string;
  target: 'chain' | 'narrator_identity' | 'narrator_lexicon' | 'report_text' | 'report_metadata' | 'translation' | 'other';
  reason: string;
  confidence: string;
  /** Both readings, each with its source: ours (the archive) and theirs (a source code or a URL / edition locator). */
  differences: ReaderFinding['differences'];
  compared: string[];
  evidence: unknown[];
  arabic_sha256: string;
  reader_format: ReaderFormat;
  model_id: string;
  provider_runtime: string;
  orchestrator_run_id: string;
  prompt_path: string;
  prompt_sha256: string;
  packet_path: string;
  packet_sha256: string;
  packet_item_id: string;
  submitted_at: string;
}
export interface ProposalReview {
  format: typeof PROPOSAL_REVIEW_FORMAT;
  review_id: string;
  proposal_id: string;
  reviewer: string;
  decision: 'accepted' | 'rejected';
  note: string;
  reviewed_at: string;
}
export const PROPOSAL_TARGET: Record<string, Proposal['target']> = {
  chain_differs_from_source: 'chain',
  wrong_identity: 'narrator_identity',
  lexicon_date_impossible: 'narrator_lexicon',
  lexicon_records_look_like_one_person: 'narrator_lexicon',
  text_garbled: 'report_text',
  text_differs_from_source: 'report_text',
  text_truncated_or_merged: 'report_text',
  translation_contradicts_arabic: 'translation',
  wrong_number: 'report_metadata',
  wrong_book_or_chapter: 'report_metadata',
  grading_missing_or_misattributed: 'report_metadata',
  locator_missing: 'report_metadata',
};
export const proposalIdOf = (hadithId: string, kind: string, reason: string, evidence: unknown, runId: string) =>
  `reader-proposal:${sha256Hex([hadithId, kind, reason, JSON.stringify(evidence), runId].join('\u001f')).slice(0, 24)}`;

/** Each proposal's status: `proposed` until a reviewer decides; the latest review per reviewer counts, any rejection wins. */
export function proposalStatuses(proposals: Proposal[], reviews: ProposalReview[]): { proposal: Proposal; status: 'proposed' | 'accepted_by_reviewer' | 'rejected_by_reviewer'; reviewers: string[] }[] {
  const latest = new Map<string, ProposalReview>();
  for (const review of [...reviews].sort((a, b) => a.reviewed_at.localeCompare(b.reviewed_at))) latest.set(`${review.proposal_id}\u001f${review.reviewer}`, review);
  const byProposal = new Map<string, ProposalReview[]>();
  for (const review of latest.values()) byProposal.set(review.proposal_id, [...(byProposal.get(review.proposal_id) ?? []), review]);
  const unique = new Map(proposals.map((proposal) => [proposal.proposal_id, proposal]));
  return [...unique.values()].map((proposal) => {
    const decided = byProposal.get(proposal.proposal_id) ?? [];
    const status = decided.some((r) => r.decision === 'rejected') ? 'rejected_by_reviewer' : decided.some((r) => r.decision === 'accepted') ? 'accepted_by_reviewer' : 'proposed';
    return { proposal, status, reviewers: decided.map((r) => r.reviewer).sort() };
  });
}

/** One call to the Python engine for every item (validate.py, comparison, planned rows). */
export function runEngine(items: EngineItem[]): EngineResult[] {
  if (items.length === 0) return [];
  const python = process.env.CHAIN_FIX_PYTHON ?? 'python';
  const result = spawnSync(python, ['-I', ENGINE_PATH], { input: Buffer.from(JSON.stringify({ items }), 'utf8'), maxBuffer: 512 * 1024 * 1024 });
  if (result.error) throw new Error(`could not run ${python}: ${result.error.message}`);
  if (result.status !== 0) throw new Error(`chain_fix_engine.py failed:\n${result.stderr.toString('utf8')}`);
  return (JSON.parse(result.stdout.toString('utf8')) as { results: EngineResult[] }).results;
}

// ---------------------------------------------------------------------------------------------------------------- store

export interface StorePaths {
  root: string;
  submissions: string;
  reviews: string;
  applications: string;
  transitions: string;
  state: string;
  queue: string;
  proposals: string;
  proposalReviews: string;
  /** Holds the pipeline records from archive facts (not the reader's), appended by chain-fix-hold.ts; read by the decide rule. */
  archiveHolds: string;
}
export function storePaths(root: string = DEFAULT_STORE): StorePaths {
  return {
    root,
    submissions: path.join(root, 'submissions'),
    reviews: path.join(root, 'reviews'),
    applications: path.join(root, 'applications'),
    transitions: path.join(root, 'transitions.jsonl'),
    state: path.join(root, 'state.json'),
    queue: path.join(root, 'queue.json'),
    proposals: path.join(root, 'proposals'),
    proposalReviews: path.join(root, 'proposal-reviews'),
    archiveHolds: path.join(root, 'archive-holds.jsonl'),
  };
}

const sleep = (milliseconds: number) => Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, milliseconds);

/** Exclusive lock by `open(..., 'wx')`: one writer per file; a lock older than two minutes is a crashed writer's and is taken over. */
export function withLock<T>(lockPath: string, work: () => T): T {
  mkdirSync(path.dirname(lockPath), { recursive: true });
  const deadline = Date.now() + 30_000;
  for (;;) {
    try {
      const handle = openSync(lockPath, 'wx');
      writeSync(handle, `${process.pid}\n`);
      closeSync(handle);
      break;
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== 'EEXIST') throw error;
      if (existsSync(lockPath) && Date.now() - statSync(lockPath).mtimeMs > 120_000) unlinkSync(lockPath);
      else if (Date.now() > deadline) throw new Error(`${lockPath} is held by another writer; try again`);
      else sleep(50);
    }
  }
  try {
    return work();
  } finally {
    unlinkSync(lockPath);
  }
}

/** Append lines to an append-only JSONL file under its lock (whole lines, one write). */
export function appendRecords(file: string, records: readonly object[]): void {
  if (records.length === 0) return;
  withLock(`${file}.lock`, () => {
    const handle = openSync(file, 'a');
    try {
      writeSync(handle, records.map((record) => JSON.stringify(record)).join('\n') + '\n');
    } finally {
      closeSync(handle);
    }
  });
}

function readJsonl<T>(directory: string): T[] {
  if (!existsSync(directory)) return [];
  return readdirSync(directory)
    .filter((name) => name.endsWith('.jsonl'))
    .sort()
    .flatMap((name) => readFileSync(path.join(directory, name), 'utf8').split('\n').filter(Boolean).map((line) => JSON.parse(line) as T));
}

export const readSubmissions = (paths: StorePaths) => readJsonl<Submission>(paths.submissions);
export const readReviews = (paths: StorePaths) => readJsonl<Review>(paths.reviews);
export const readProposals = (paths: StorePaths) => readJsonl<Proposal>(paths.proposals);
export const readProposalReviews = (paths: StorePaths) => readJsonl<ProposalReview>(paths.proposalReviews);
/** An archive hold: a fact about the archive (not the reading) that keeps a fix from being applied (reviews/ai/AGENTS.md §Chain fixes). */
export interface ArchiveHold {
  format: typeof ARCHIVE_HOLD_FORMAT;
  fix_id: string;
  hadith_id: string;
  code: string;
  detail: string;
  at: string;
  by: string;
}
export const readArchiveHolds = (paths: StorePaths): ArchiveHold[] =>
  existsSync(paths.archiveHolds) ? readFileSync(paths.archiveHolds, 'utf8').split('\n').filter(Boolean).map((line) => JSON.parse(line) as ArchiveHold) : [];
export const readApplications = (paths: StorePaths) => readJsonl<{ fix_id: string; action: 'applied' | 'reverted'; at: string }>(paths.applications);

/** Write a derived file atomically (temp file, then rename), so a reader never sees half of it. */
export function writeAtomically(file: string, data: string | Buffer): void {
  mkdirSync(path.dirname(file), { recursive: true });
  const temporary = `${file}.${process.pid}.tmp`;
  writeFileSync(temporary, data);
  renameSync(temporary, file);
}

// ------------------------------------------------------------------------------------------------------ the decide rule

export interface FixState {
  fix_id: string;
  hadith_id: string;
  record_id: string;
  tradition: string;
  work: string;
  state: State;
  effect: 'replace_routes' | 'set_status' | 'annotate' | null;
  structure_status: 'read_by_model' | 'verified_by_reviewer' | null;
  fix_kinds: string[];
  runs: string[];
  models: string[];
  text_only_runs: number;
  dissenting_runs: number;
  database: 'not_applied' | 'applied' | 'reverted';
  human_confirmations: number;
  human_rejections: number;
  ai_objections: number;
  reviewers: string[];
  representative_submission_id: string;
  /** Hold codes of any current run of this reading (HOLDS.md); a held reading is never applied. Lifted codes (LIFTED_HOLD_CODES) are not here. */
  holds: string[];
  /** Codes the owner lifted that this reading carried (kept for the record; they no longer hold it). */
  lifted_holds: string[];
  /** The AI reviewer confirmed it (or cleared its holds and it was applied): "AI reviewed (<model>), <date>". */
  ai_review: AiMark | null;
  /** The AI reviewer did not confirm an applied reading: it stays applied, labelled disputed, its correction queued for a second review. */
  ai_disputed: AiMark | null;
  /** This fix was written from the AI reviewer's correction, repeated by a second independent review. */
  ai_corrected: { corrects_fix_id: string; runs: string[]; models: string[]; at: string } | null;
  why: string;
}

/** Every hold code any of these runs carries, sorted and distinct. */
const holdCodes = (runs: Submission[]) => [...new Set(runs.flatMap((s) => (s.holds ?? []).map((hold) => hold.code)))].sort();

const latestPerReviewer = (reviews: Review[]) => {
  const latest = new Map<string, Review>();
  for (const review of [...reviews].sort((a, b) => a.reviewed_at.localeCompare(b.reviewed_at) || a.review_id.localeCompare(b.review_id))) {
    latest.set(`${review.reviewer_kind}\u001f${review.reviewer}`, review);
  }
  return [...latest.values()];
};

/** The latest review of a fix by the AI reviewer tier (a row with `outcome`), or null. */
const latestAiReview = (reviews: Review[]) =>
  [...reviews].filter((r) => r.reviewer_kind === 'ai' && r.outcome).sort((a, b) => a.reviewed_at.localeCompare(b.reviewed_at) || a.review_id.localeCompare(b.review_id)).at(-1) ?? null;

const aiMark = (review: Review): AiMark => ({
  model_id: review.model_id ?? '', run_id: review.run_id ?? '', at: review.reviewed_at, review_id: review.review_id, outcome: review.outcome!, decision: review.review_decision ?? '',
});

/** Outcomes that apply a held or pending reading (review_rules_v1_1.ACTION_CLASS "apply" for the readers' own fix). */
const APPLY_READING = new Set<ReviewOutcome>(['apply_reading', 'apply_reader_a']);

/**
 * Every fix's state from the store, deterministically. Per report, only submissions bound to the newest text are current;
 * per run, its latest reading counts. Agreement: one reading has at least two runs, at least one of them blind to the stored
 * chain, and at least twice the runs of every other reading together. Final review: the latest review per reviewer counts;
 * any human rejection rejects; else a human confirmation confirms. The AI reviewer moves a fix only as its recorded outcome
 * (review_rules_v1_1.outcome, computed at recording time on the fix's state then) says, and any human decision wins over it.
 * Codes the owner lifted (LIFTED_HOLD_CODES) no longer hold a fix. Rationale: reviews/ai/AGENTS.md §AI review tier.
 */
export function computeStates(submissions: Submission[], reviews: Review[], applications: { fix_id: string; action: string; at: string }[],
                              archiveHolds: ArchiveHold[] = []): FixState[] {
  const archiveCodes = new Map<string, string[]>();
  for (const hold of archiveHolds) archiveCodes.set(hold.fix_id, [...new Set([...(archiveCodes.get(hold.fix_id) ?? []), hold.code])]);
  const allHoldsOf = (fixId: string, runs: Submission[]) => [...new Set([...holdCodes(runs), ...(archiveCodes.get(fixId) ?? [])])].sort();
  const holdsOf = (fixId: string, runs: Submission[]) => allHoldsOf(fixId, runs).filter((code) => !(code in LIFTED_HOLD_CODES));
  const unique = new Map<string, Submission>();
  for (const submission of submissions) if (!unique.has(submission.submission_id)) unique.set(submission.submission_id, submission);
  const byReport = new Map<string, Submission[]>();
  for (const submission of unique.values()) byReport.set(submission.hadith_id, [...(byReport.get(submission.hadith_id) ?? []), submission]);
  const reviewsByFix = new Map<string, Review[]>();
  for (const review of reviews) reviewsByFix.set(review.fix_id, [...(reviewsByFix.get(review.fix_id) ?? []), review]);
  const database = new Map<string, FixState['database']>();
  for (const application of [...applications].sort((a, b) => a.at.localeCompare(b.at))) database.set(application.fix_id, application.action === 'applied' ? 'applied' : 'reverted');

  const states: FixState[] = [];
  for (const [hadithId, all] of [...byReport.entries()].sort(([a], [b]) => a.localeCompare(b))) {
    const binding = (s: Submission) => `${s.arabic_sha256}\u001f${s.reader_text_sha256}`;
    const newest = [...all].sort((a, b) => b.submitted_at.localeCompare(a.submitted_at))[0];
    const current = all.filter((s) => binding(s) === binding(newest));
    const latestByRun = new Map<string, Submission>();
    for (const s of [...current].sort((a, b) => a.submitted_at.localeCompare(b.submitted_at))) latestByRun.set(s.orchestrator_run_id, s);
    // A fix written from the AI reviewer's correction is not a reader's reading: it takes no part in the agreement count.
    const counted = [...latestByRun.values()].filter((s) => !s.corrects_fix_id);
    const corrections = [...latestByRun.values()].filter((s) => s.corrects_fix_id);
    const byFix = new Map<string, Submission[]>();
    for (const s of counted) byFix.set(s.fix_id, [...(byFix.get(s.fix_id) ?? []), s]);
    const correctionRuns = new Map<string, Submission[]>();
    for (const s of corrections) correctionRuns.set(s.fix_id, [...(correctionRuns.get(s.fix_id) ?? []), s]);

    const ranked = [...byFix.entries()].sort((a, b) => b[1].length - a[1].length || a[0].localeCompare(b[0]));
    const [leaderId, leaderRuns] = ranked[0] ?? ['', []];
    const dissent = ranked.slice(1).reduce((sum, [, runs]) => sum + runs.length, 0);
    const tied = ranked.length > 1 && ranked[1][1].length === leaderRuns.length;
    const leaderBlind = leaderRuns.filter((s) => isBlindView(s.view)).length;
    const agreed = !tied && leaderRuns.length >= 2 && leaderBlind >= 1 && leaderRuns.length >= 2 * dissent;

    const humanLatest = (fixId: string) => latestPerReviewer(reviewsByFix.get(fixId) ?? []).filter((r) => r.reviewer_kind === 'human');
    // A human confirmation of one reading of a disputed report settles it; the other readings are superseded by it.
    const allFixIds = [...byFix.keys(), ...correctionRuns.keys()];
    const humanConfirmed = new Set(allFixIds.filter((fixId) => {
      const latest = humanLatest(fixId);
      return latest.some((r) => r.decision === 'confirmed') && !latest.some((r) => r.decision === 'rejected');
    }));
    // A correction (two reviews, the same routes) replaces the reading it corrects, unless a human has decided either.
    const correctedBy = new Map<string, string>();
    for (const [fixId, runs] of correctionRuns) if (runs.length >= 2 && humanLatest(fixId).every((r) => r.decision !== 'rejected')) correctedBy.set(runs[0].corrects_fix_id!, fixId);

    for (const [fixId, runs] of [...byFix, ...correctionRuns]) {
      const isCorrection = correctionRuns.has(fixId);
      const representative = [...runs].sort((a, b) => (a.text_checked_against === 'database' ? 0 : 1) - (b.text_checked_against === 'database' ? 0 : 1) || b.submitted_at.localeCompare(a.submitted_at))[0];
      const isNoChange = representative.fix_kinds.includes('no_change');
      const latest = latestPerReviewer(reviewsByFix.get(fixId) ?? []);
      const humans = latest.filter((r) => r.reviewer_kind === 'human');
      const rejections = humans.filter((r) => r.decision === 'rejected').length;
      const confirmations = humans.filter((r) => r.decision === 'confirmed').length;
      const supersededBy = humans.find((r) => r.decision === 'superseded')?.superseded_by ?? null;
      const ai = latestAiReview(reviewsByFix.get(fixId) ?? []);
      const holds = holdsOf(fixId, runs);
      const inDatabase = database.get(fixId) === 'applied';
      let aiReview: AiMark | null = null;
      let aiDisputed: AiMark | null = null;
      let state: State;
      let why: string;
      if (rejections > 0) {
        state = 'rejected';
        why = 'a human reviewer rejected it';
      } else if (supersededBy) {
        state = 'superseded';
        why = `a human reviewer marked it superseded by ${supersededBy}`;
      } else if (confirmations > 0) {
        state = 'confirmed';
        why = 'a human reviewer confirmed it';
      } else if (humanConfirmed.size > 0) {
        state = 'superseded';
        why = `a human reviewer confirmed another reading of this report (${[...humanConfirmed].join(', ')})`;
      } else if (isCorrection) {
        state = runs.length >= 2 ? 'accepted' : 'awaiting_human';
        why = runs.length >= 2 ? `the AI reviewer's correction, written alike by ${runs.length} independent reviews` : 'one review wrote this correction; a second independent review must repeat it';
      } else if (correctedBy.has(fixId)) {
        state = 'superseded';
        why = `the AI reviewer's correction ${correctedBy.get(fixId)} (two reviews, the same routes) replaces it`;
      } else if (ai && (ai.outcome === 'apply_correction' || ai.outcome === 'apply_no_chain') && !inDatabase) {
        state = 'awaiting_human';
        why = "two reviews wrote the same correction, but it is not yet written as a fix (chain-review-record.ts): listed for a person";
      } else if (ai && ai.outcome === 'queue_for_human' && !inDatabase) {
        state = 'awaiting_human';
        why = 'the AI reviewer did not confirm it and nothing the rule allows applies: listed for a person';
      } else if (ai && ai.outcome === 'keep_held' && holds.length === 0 && !inDatabase) {
        // A referral of a cleared, not yet applied reading keeps it back (pending behaves as held).
        state = 'held';
        why = 'held: the AI reviewer referred it to a person (referred_by_ai_reviewer)';
        holds.push('referred_by_ai_reviewer');
      } else if (ai && (ai.outcome === 'revert_to_stored' || (ai.outcome === 'discard_reading' && !inDatabase))) {
        state = 'set_aside_by_ai';
        why = ai.outcome === 'revert_to_stored' ? 'the AI reviewer kept the stored chain, which differs from this reading: reverted and listed for a person'
          : 'the AI reviewer kept the stored chain: set aside, never applied, listed for a person';
      } else if (holds.length > 0 && ai && APPLY_READING.has(ai.outcome!) && holds.every((code) => (ai.codes_at_review ?? []).includes(code)) && fixId === leaderId && agreed) {
        // review_rules_v1_1: a confirmation of a held reading whose every hold the reviewer may clear applies it (holds checked again: a hold
        // that came after the review keeps it back).
        state = 'accepted';
        why = `the AI reviewer confirmed it and cleared its holds (${holds.join(', ')}); ${runs.length} independent readers agree`;
        aiReview = aiMark(ai);
      } else if (holds.length > 0) {
        // Held by the tool (HOLDS.md) or by an archive fact: never auto-applied, whatever the agreement; queued for a third reader or a person.
        state = 'held';
        why = `held: ${holds.join(', ')}; queued for a third reader or a person`;
      } else if (fixId === leaderId && agreed) {
        state = 'accepted';
        why = `${runs.length} independent readers agree (${leaderBlind} blind to the stored chain)${dissent ? `, over ${dissent} dissenting` : ''}`;
        if (ai && (ai.outcome === 'label_ai_reviewed' || APPLY_READING.has(ai.outcome!))) aiReview = aiMark(ai);
        // An applied reading the reviewer did not confirm stays applied (never reverted by a correction or a referral), labelled disputed.
        if (ai && ai.outcome === 'label_disputed') aiDisputed = aiMark(ai);
        // Reviewed while pending, applied since: never reverted by a referral or a set-aside, labelled disputed instead.
        if (ai && inDatabase && ['queue_for_human', 'keep_held', 'discard_reading', 'apply_correction', 'apply_no_chain'].includes(ai.outcome!)) aiDisputed = aiMark(ai);
      } else if (agreed) {
        state = 'outvoted';
        why = `another reading has ${leaderRuns.length} readers against this one's ${runs.length}`;
      } else if (byFix.size > 1) {
        state = 'disputed';
        why = 'readers disagree; nothing is applied until a third reader or a human settles it';
      } else if (isNoChange) {
        state = 'accepted';
        why = 'a lone reader read the stored chain unchanged: recorded beside it, nothing replaced';
      } else {
        state = 'submitted';
        why = runs.some((s) => isBlindView(s.view)) ? 'one reader so far; waiting for a second, independent reader' : 'no reader blind to the stored chain yet';
      }
      const live = state === 'accepted' || state === 'confirmed';
      const uncertain = representative.base.chains.some((chain) => chain.structure_status === 'uncertain');
      const lone = runs.length < 2;
      let effect: FixState['effect'] = null;
      if (live) effect = !isNoChange ? 'replace_routes' : uncertain && (!lone || state === 'confirmed') ? 'set_status' : 'annotate';
      if (isCorrection && live && isNoChange) effect = 'set_status';
      const lifted = allHoldsOf(fixId, runs).filter((code) => code in LIFTED_HOLD_CODES);
      states.push({
        fix_id: fixId,
        hadith_id: hadithId,
        record_id: representative.record_id,
        tradition: representative.tradition,
        work: representative.source_work_id,
        state,
        effect,
        structure_status: effect === 'annotate' || !live ? null : state === 'confirmed' ? 'verified_by_reviewer' : 'read_by_model',
        fix_kinds: representative.fix_kinds,
        runs: runs.map((s) => s.orchestrator_run_id).sort(),
        models: [...new Set(runs.map((s) => s.model_id))].sort(),
        text_only_runs: runs.filter((s) => isBlindView(s.view)).length,
        dissenting_runs: isCorrection ? 0 : counted.length - runs.length,
        database: database.get(fixId) ?? 'not_applied',
        human_confirmations: confirmations,
        human_rejections: rejections,
        ai_objections: latest.filter((r) => r.reviewer_kind === 'ai' && (r.outcome ? r.outcome === 'label_disputed' || r.outcome === 'queue_for_human' : r.decision !== 'confirmed')).length,
        reviewers: latest.map((r) => `${r.reviewer_kind}:${r.reviewer}`).sort(),
        representative_submission_id: representative.submission_id,
        holds,
        lifted_holds: lifted,
        ai_review: aiReview,
        ai_disputed: aiDisputed,
        ai_corrected: isCorrection && runs.length >= 2
          ? { corrects_fix_id: representative.corrects_fix_id!, runs: runs.map((s) => s.orchestrator_run_id).sort(), models: [...new Set(runs.map((s) => s.model_id))].sort(), at: [...runs].map((s) => s.submitted_at).sort().at(-1)! }
          : null,
        why: inDatabase && !live ? `${why} (still in the database: revert it)` : why,
      });
    }
    // Submissions bound to older text: kept, never applied.
    for (const s of all.filter((x) => binding(x) !== binding(newest))) {
      if (states.some((state) => state.fix_id === s.fix_id)) continue;
      states.push({
        fix_id: s.fix_id, hadith_id: hadithId, record_id: s.record_id, tradition: s.tradition, work: s.source_work_id, state: 'stale', effect: null,
        structure_status: null, fix_kinds: s.fix_kinds, runs: [s.orchestrator_run_id], models: [s.model_id], text_only_runs: isBlindView(s.view) ? 1 : 0,
        dissenting_runs: 0, database: database.get(s.fix_id) ?? 'not_applied', human_confirmations: 0, human_rejections: 0, ai_objections: 0, reviewers: [],
        representative_submission_id: s.submission_id, holds: [], lifted_holds: [], ai_review: null, ai_disputed: null, ai_corrected: null,
        why: 'read from an older text of this report; re-read the current text',
      });
    }
  }
  return states.sort((a, b) => a.hadith_id.localeCompare(b.hadith_id) || a.fix_id.localeCompare(b.fix_id));
}
/** The rows the projection replays: one per report with an accepted or confirmed fix, sorted, gzip with no timestamp. */
export function buildOverrides(states: FixState[], submissions: Submission[]): Buffer {
  const byId = new Map(submissions.map((s) => [s.submission_id, s]));
  const lines = states
    .filter((state) => state.effect !== null)
    .map((state) => {
      const s = byId.get(state.representative_submission_id)!;
      return JSON.stringify({
        format: OVERRIDE_FORMAT,
        hadith_id: s.hadith_id,
        record_id: s.record_id,
        fix_id: state.fix_id,
        arabic_sha256: s.arabic_sha256,
        reader_text_sha256: s.reader_text_sha256,
        text_layout: s.text_layout,
        effect: state.effect,
        structure_status: state.structure_status,
        state: state.state,
        fix_kinds: state.fix_kinds,
        base_chain_sha256: s.base.chain_sha256,
        planned: state.effect === 'replace_routes' ? s.planned : null,
        // A variant remark rides on any effect (a stored chain confirmed can carry one too); never a route.
        ...(s.planned.variant_remarks?.length ? { variant_remarks: s.planned.variant_remarks } : {}),
        disposition: s.disposition ?? null,
        read_by: { models: state.models, runs: state.runs, prompt_sha256: s.prompt_sha256, prompt_version: s.prompt_version, tool_version: s.tool_version ?? null },
      });
    });
  return gzipSync(Buffer.from(lines.length ? `${lines.join('\n')}\n` : '', 'utf8'), { level: 9 });
}

/**
 * Recompute every state under the store lock, append a transition for each change, rewrite the derived state, queue and
 * overrides files. Used by decide and by review, so a rejection leaves the overrides in the same call.
 */
export function reconcile(paths: StorePaths, overridesPath: string, now: string): { states: FixState[]; transitions: object[] } {
  return withLock(path.join(paths.root, 'store.lock'), () => {
    const submissions = readSubmissions(paths);
    const states = computeStates(submissions, readReviews(paths), readApplications(paths), readArchiveHolds(paths));
    const previous = new Map<string, string>(
      existsSync(paths.state) ? (JSON.parse(readFileSync(paths.state, 'utf8')) as { fixes: FixState[] }).fixes.map((f) => [f.fix_id, f.state]) : [],
    );
    const transitions = states
      .filter((state) => previous.get(state.fix_id) !== state.state)
      .map((state) => ({ format: TRANSITION_FORMAT, fix_id: state.fix_id, hadith_id: state.hadith_id, from: previous.get(state.fix_id) ?? null, to: state.state, at: now, why: state.why }));
    mkdirSync(paths.root, { recursive: true });
    appendRecords(paths.transitions, transitions);
    writeAtomically(paths.state, `${JSON.stringify({ format: 'shura-chain-fix-state/1', note: 'Derived by chain-fix-decide.ts; never edit.', fixes: states }, null, 1)}\n`);
    const queue = {
      format: 'shura-chain-fix-queue/1',
      awaiting_final_review: states.filter((s) => s.state === 'accepted').map((s) => s.fix_id),
      disputed: states.filter((s) => s.state === 'disputed').map((s) => s.fix_id),
      held: states.filter((s) => s.state === 'held').map((s) => ({ fix_id: s.fix_id, holds: s.holds })),
      awaiting_second_reader: states.filter((s) => s.state === 'submitted').map((s) => s.fix_id),
      rejected_but_in_database: states.filter((s) => s.state === 'rejected' && s.database === 'applied').map((s) => s.fix_id),
      // AI reviewer tier (review_rules_v1_1): what a person or a second review must look at, and what must leave the database.
      awaiting_human: states.filter((s) => s.state === 'awaiting_human').map((s) => s.fix_id),
      ai_disputed_awaiting_second_review: states.filter((s) => s.ai_disputed).map((s) => ({ fix_id: s.fix_id, run_id: s.ai_disputed!.run_id, decision: s.ai_disputed!.decision })),
      set_aside_by_ai: states.filter((s) => s.state === 'set_aside_by_ai').map((s) => s.fix_id),
      // Out of the overrides but still written: the reverted-by-AI reading and a reading an applied correction replaces (revert before the apply).
      revert_before_apply: states.filter((s) => s.database === 'applied' && !['accepted', 'confirmed', 'rejected'].includes(s.state)).map((s) => s.fix_id),
    };
    writeAtomically(paths.queue, `${JSON.stringify(queue, null, 1)}\n`);
    writeAtomically(overridesPath, buildOverrides(states, submissions));
    return { states, transitions };
  });
}

/** Minimal argument reader shared by the CLIs: `--name value` and bare `--flag`. */
export function argumentsOf(argv: string[]): { get: (name: string) => string | undefined; has: (name: string) => boolean } {
  return {
    get: (name) => {
      const index = argv.indexOf(`--${name}`);
      return index >= 0 && index + 1 < argv.length && !argv[index + 1].startsWith('--') ? argv[index + 1] : undefined;
    },
    has: (name) => argv.includes(`--${name}`),
  };
}

export const utcNow = () => new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
