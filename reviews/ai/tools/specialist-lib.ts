/**
 * Specialist AI review: packet and output shapes, the output validator and the review record. Pure except
 * `promptInfo`/`sha256File`, which read one file. Format and isolation rules: reviews/ai/README.md.
 */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

export const PACKET_FORMAT = 'shura-review-packet/1';
export const OUTPUT_FORMAT = 'shura-specialist-output/1';
export const RECORD_FORMAT = 'shura-ai-review-record/1';

export const OUTCOMES = ['supports', 'contradicts', 'contested', 'insufficient_evidence'] as const;
export type Outcome = (typeof OUTCOMES)[number];
export const UNCERTAINTY = ['low', 'medium', 'high'] as const;

/** Specialist-specific `reading` vocabularies; absent means the specialist gives no reading. */
export const READINGS: Readonly<Record<string, readonly string[]>> = {
  correspondence: [
    'same_report',
    'same_report_variant',
    'shared_passage',
    'shared_formula_or_verse',
    'same_ruling_different_speaker',
    'unrelated',
    'cannot_determine',
  ],
};

/** The outcome each correspondence reading maps to; `contested` is allowed with any reading (prompt §How to judge). */
const CORRESPONDENCE_OUTCOME_FOR_READING: Readonly<Record<string, Outcome>> = {
  same_report: 'supports',
  same_report_variant: 'supports',
  shared_passage: 'supports',
  shared_formula_or_verse: 'contradicts',
  unrelated: 'contradicts',
  same_ruling_different_speaker: 'contested',
  cannot_determine: 'insufficient_evidence',
};

export interface PacketPassage {
  id: string;
  text: string;
  [key: string]: unknown;
}

export interface PacketItem {
  item_id: string;
  /** The claim ids the reviewer must answer for this item (item id, or item id + candidate label). */
  claim_ids: string[];
  /** Every quotable text of the item by passage id ("report", "A", "B", "P1", ...). */
  passages: PacketPassage[];
  [key: string]: unknown;
}

/** An item before its ids are assigned (builders fill item_id and claim_ids per packet). */
export interface PacketItemBody {
  passages: PacketPassage[];
  [key: string]: unknown;
}

export interface Packet {
  format: typeof PACKET_FORMAT;
  packet_id: string;
  specialist_id: string;
  prompt_version: string;
  items: PacketItem[];
  glossary: { term: string; definition: string }[];
  [key: string]: unknown;
}

export interface Verdict {
  claim_id: string;
  outcome: Outcome;
  reading?: string;
  reasons: string[];
  evidence: { passage_id: string; quote: string }[];
  uncertainty: (typeof UNCERTAINTY)[number];
  uncertainty_note?: string;
  proposals?: { kind: string; text: string }[];
}

export interface SpecialistOutput {
  format: typeof OUTPUT_FORMAT;
  specialist_id: string;
  prompt_version: string;
  packet_id: string;
  verdicts: Verdict[];
}

/** Words that would tell a reviewer what the pipeline concluded; a packet must not contain them as keys. */
export const LEAKING_KEYS = [
  'basis',
  'score',
  'jaccard',
  'containment',
  'relation_class',
  'score_band',
  'confidence',
  'resolution',
  'outcome',
  'expected',
  'known_answer',
  'verified',
  'detail',
  'agreement_class',
  'tier',
];

/** Keys anywhere in the packet that leak a verdict (checked by the builders and the validator). */
export function packetLeaks(packet: unknown): string[] {
  const found = new Set<string>();
  const walk = (value: unknown) => {
    if (Array.isArray(value)) value.forEach(walk);
    else if (value && typeof value === 'object') {
      for (const [key, inner] of Object.entries(value)) {
        if (LEAKING_KEYS.includes(key)) found.add(key);
        walk(inner);
      }
    }
  };
  walk(packet);
  return [...found].sort();
}

const isString = (value: unknown): value is string => typeof value === 'string';
const isNonEmptyString = (value: unknown): value is string => isString(value) && value.trim().length > 0;

/**
 * Every problem with a specialist's output for a packet; empty when it may be recorded. Checks the envelope, one
 * verdict per claim id and no others, the vocabularies, and that every quote is an exact substring of the passage
 * it names (a fabricated or normalised quote fails).
 */
export function validateSpecialistOutput(packet: Packet, raw: unknown, promptVersion: string): string[] {
  const problems: string[] = [];
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return ['output is not a JSON object'];
  const output = raw as Record<string, unknown>;
  const allowedTop = new Set(['format', 'specialist_id', 'prompt_version', 'packet_id', 'verdicts']);
  for (const key of Object.keys(output)) if (!allowedTop.has(key)) problems.push(`unknown top-level field "${key}"`);
  if (output.format !== OUTPUT_FORMAT) problems.push(`format must be "${OUTPUT_FORMAT}"`);
  if (output.specialist_id !== packet.specialist_id) problems.push(`specialist_id must be "${packet.specialist_id}"`);
  if (output.prompt_version !== promptVersion) problems.push(`prompt_version must be "${promptVersion}"`);
  if (output.packet_id !== packet.packet_id) problems.push(`packet_id must be "${packet.packet_id}"`);
  if (!Array.isArray(output.verdicts)) return [...problems, 'verdicts must be an array'];

  const passagesByClaim = new Map<string, Map<string, string>>();
  for (const item of packet.items) {
    const passages = new Map(item.passages.map((passage) => [passage.id, passage.text]));
    for (const claimId of item.claim_ids) passagesByClaim.set(claimId, passages);
  }
  const readings = READINGS[packet.specialist_id];
  const seen = new Set<string>();

  output.verdicts.forEach((value, index) => {
    const where = `verdicts[${index}]`;
    if (!value || typeof value !== 'object') {
      problems.push(`${where} is not an object`);
      return;
    }
    const verdict = value as Record<string, unknown>;
    const allowed = new Set(['claim_id', 'outcome', 'reading', 'reasons', 'evidence', 'uncertainty', 'uncertainty_note', 'proposals']);
    for (const key of Object.keys(verdict)) if (!allowed.has(key)) problems.push(`${where}: unknown field "${key}"`);
    const claimId = verdict.claim_id;
    if (!isString(claimId) || !passagesByClaim.has(claimId)) {
      problems.push(`${where}: claim_id ${JSON.stringify(claimId)} is not in the packet`);
      return;
    }
    if (seen.has(claimId)) problems.push(`${where}: claim_id ${claimId} answered twice`);
    seen.add(claimId);
    const outcome = verdict.outcome as Outcome;
    if (!OUTCOMES.includes(outcome)) problems.push(`${where}: outcome ${JSON.stringify(verdict.outcome)} is not one of ${OUTCOMES.join(', ')}`);
    if (readings) {
      if (!isString(verdict.reading) || !readings.includes(verdict.reading)) problems.push(`${where}: reading must be one of ${readings.join(', ')}`);
      else if (packet.specialist_id === 'correspondence' && outcome !== 'contested' && CORRESPONDENCE_OUTCOME_FOR_READING[verdict.reading] !== outcome) {
        problems.push(`${where}: reading ${verdict.reading} goes with outcome ${CORRESPONDENCE_OUTCOME_FOR_READING[verdict.reading]}`);
      }
    } else if (verdict.reading !== undefined) problems.push(`${where}: this specialist gives no reading`);
    if (!Array.isArray(verdict.reasons) || verdict.reasons.length === 0 || !verdict.reasons.every(isNonEmptyString)) {
      problems.push(`${where}: reasons must be a non-empty list of sentences`);
    }
    if (!UNCERTAINTY.includes(verdict.uncertainty as (typeof UNCERTAINTY)[number])) problems.push(`${where}: uncertainty must be low, medium or high`);
    if (verdict.uncertainty_note !== undefined && !isString(verdict.uncertainty_note)) problems.push(`${where}: uncertainty_note must be text`);
    const evidence = Array.isArray(verdict.evidence) ? verdict.evidence : null;
    if (!evidence) problems.push(`${where}: evidence must be a list`);
    else {
      if ((outcome === 'supports' || outcome === 'contradicts') && evidence.length === 0) {
        problems.push(`${where}: ${outcome} needs at least one evidence quote`);
      }
      const passages = passagesByClaim.get(claimId)!;
      evidence.forEach((entry, evidenceIndex) => {
        const span = entry as { passage_id?: unknown; quote?: unknown };
        const text = isString(span.passage_id) ? passages.get(span.passage_id) : undefined;
        if (text === undefined) problems.push(`${where}.evidence[${evidenceIndex}]: passage_id ${JSON.stringify(span.passage_id)} is not in this item`);
        else if (!isNonEmptyString(span.quote) || !text.includes(span.quote)) {
          problems.push(`${where}.evidence[${evidenceIndex}]: quote is not an exact substring of ${String(span.passage_id)}`);
        }
      });
    }
    if (verdict.proposals !== undefined) {
      const ok = Array.isArray(verdict.proposals) && verdict.proposals.every((proposal) => isNonEmptyString((proposal as { kind?: unknown }).kind) && isNonEmptyString((proposal as { text?: unknown }).text));
      if (!ok) problems.push(`${where}: proposals must be a list of {kind, text}`);
    }
  });
  for (const claimId of passagesByClaim.keys()) if (!seen.has(claimId)) problems.push(`no verdict for claim_id ${claimId}`);
  return problems;
}

export function sha256Hex(data: string | Buffer): string {
  return createHash('sha256').update(data).digest('hex');
}

export function sha256File(path: string): string {
  return sha256Hex(readFileSync(path));
}

/** Version from a prompt file's front matter and the SHA-256 of its exact bytes. */
export function promptInfo(path: string): { version: string; specialist: string; sha256: string } {
  const bytes = readFileSync(path);
  const text = bytes.toString('utf8');
  const front = /^---\n([\s\S]*?)\n---\n/.exec(text.replace(/\r\n/g, '\n'));
  if (!front) throw new Error(`${path}: no front matter`);
  const field = (name: string) => new RegExp(`^${name}:\\s*(.+)$`, 'm').exec(front[1])?.[1].trim();
  const version = field('version');
  // The chain reader's prompt lives in datasets/hadith-data/chain-reader/ and names itself `reader:` (referenced, never copied).
  const specialist = field('specialist') ?? field('reader');
  if (!version || !specialist) throw new Error(`${path}: front matter needs specialist and version`);
  return { version, specialist, sha256: sha256Hex(bytes) };
}

/** Hidden half of a packet: which claim each item stands for. Never shown to the reviewer. */
export interface PacketManifestItem {
  item_id: string;
  claim_id: string;
  claim_kind: string;
  claim_key: string;
  content_sha256: string;
  stratum: string;
  /** What the pipeline concluded, for scoring the specialist afterwards. */
  pipeline_view: string;
  /** Present only for gold items with an answer recorded elsewhere. */
  known_answer?: { outcome: Outcome; reading?: string; source: string };
}

export interface RunMetadata {
  model_id: string;
  provider_runtime: string;
  started_at: string;
  finished_at: string;
  orchestrator_run_id: string;
}

export const UTC_TIMESTAMP = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$/;

/** One review record per verdict, ready to append to reviews/ai/records/<specialist>/<batch>.jsonl. */
export function buildSpecialistRecords(input: {
  packet: Packet;
  packetPath: string;
  packetSha256: string;
  manifest: PacketManifestItem[];
  output: SpecialistOutput;
  outputSha256: string;
  prompt: { path: string; version: string; sha256: string };
  specialistVersion: string;
  run: RunMetadata;
}): Record<string, unknown>[] {
  const { run } = input;
  if (!UTC_TIMESTAMP.test(run.started_at) || !UTC_TIMESTAMP.test(run.finished_at)) throw new Error('started_at and finished_at must be UTC ISO timestamps ending in Z');
  if (run.finished_at < run.started_at) throw new Error('finished_at is before started_at');
  if (!run.model_id.trim() || !run.provider_runtime.trim()) throw new Error('model_id and provider_runtime are required');
  const byClaim = new Map(input.manifest.map((item) => [item.claim_id, item]));
  return input.output.verdicts.map((verdict) => {
    const claim = byClaim.get(verdict.claim_id);
    if (!claim) throw new Error(`manifest has no claim ${verdict.claim_id}`);
    return {
      format: RECORD_FORMAT,
      record_id: `ai-review:${input.packet.specialist_id}:${sha256Hex(`${input.packetSha256}\u001f${verdict.claim_id}\u001f${run.model_id}\u001f${run.started_at}`).slice(0, 24)}`,
      review_kind: 'specialist',
      specialist_id: input.packet.specialist_id,
      specialist_version: input.specialistVersion,
      prompt_path: input.prompt.path,
      prompt_version: input.prompt.version,
      prompt_sha256: input.prompt.sha256,
      model_id: run.model_id,
      provider_runtime: run.provider_runtime,
      started_at: run.started_at,
      finished_at: run.finished_at,
      orchestrator_run_id: run.orchestrator_run_id,
      packet_path: input.packetPath,
      packet_id: input.packet.packet_id,
      packet_sha256: input.packetSha256,
      output_sha256: input.outputSha256,
      item_id: claim.item_id,
      claim_id: verdict.claim_id,
      claim_kind: claim.claim_kind,
      claim_key: claim.claim_key,
      content_sha256: claim.content_sha256,
      outcome: verdict.outcome,
      reading: verdict.reading ?? null,
      reasons: verdict.reasons,
      evidence: verdict.evidence,
      uncertainty: verdict.uncertainty,
      uncertainty_note: verdict.uncertainty_note ?? null,
      proposals: verdict.proposals ?? [],
    };
  });
}

/** Agreement of recorded verdicts with known answers: counts only, per item listed. */
export function scoreAgainstKnownAnswers(manifest: PacketManifestItem[], verdicts: Verdict[]) {
  const byClaim = new Map(verdicts.map((verdict) => [verdict.claim_id, verdict]));
  const rows = manifest
    .filter((item) => item.known_answer)
    .map((item) => {
      const verdict = byClaim.get(item.claim_id);
      const agrees = !!verdict && verdict.outcome === item.known_answer!.outcome;
      return { claim_id: item.claim_id, expected: item.known_answer!.outcome, got: verdict?.outcome ?? null, agrees };
    });
  return { known: rows.length, agree: rows.filter((row) => row.agrees).length, rows };
}
