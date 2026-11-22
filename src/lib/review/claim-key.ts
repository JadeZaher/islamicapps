/**
 * Claim keys: the semantic address of every reviewable claim (what is asserted, not which machine row proposed it).
 * Pure, no I/O except node:crypto. See src/lib/review/AGENTS.md §Claim keys.
 */
import { createHash } from 'node:crypto';

/** Every kind of claim a reader can see and a reviewer can review. */
export const CLAIM_KINDS = [
  'identity',
  'correspondence',
  'translation',
  'grading',
  'narrator_verdict',
  'biography',
  'rijal_link',
  'history',
  'quran_citation',
  'numbering',
  'chain_structure',
] as const;
export type ClaimKind = (typeof CLAIM_KINDS)[number];

/** Field a reviewer is permitted for; several claim kinds share one field. */
export const REVIEW_FIELDS = ['identity', 'text', 'translation', 'grading', 'biography', 'history', 'quran'] as const;
export type ReviewField = (typeof REVIEW_FIELDS)[number];

export const FIELD_FOR_CLAIM: Readonly<Record<ClaimKind, ReviewField>> = {
  identity: 'identity',
  correspondence: 'text',
  translation: 'translation',
  grading: 'grading',
  narrator_verdict: 'grading',
  biography: 'biography',
  rijal_link: 'biography',
  history: 'history',
  quran_citation: 'quran',
  numbering: 'text',
  chain_structure: 'identity',
};

const HADITH = String.raw`hadith:[a-z0-9-]+:[^|\s]+(?:\|[^|\s]*\|[^|\s]*)?`;
const MENTION = String.raw`mention:[^|\s]+`;
const NARRATOR = String.raw`narrator:[a-z0-9-]+:[^|\s]+`;
const TOKEN = String.raw`[^|\s]+`;

/**
 * Key grammar per kind: `<kind>|<part>|<part>...`. Hadith ids may themselves contain `|` (OpenITI ids end
 * `|<number>|<page>`), so each pattern names its parts explicitly.
 */
const KEY_PATTERNS: Readonly<Record<ClaimKind, RegExp>> = {
  identity: new RegExp(`^identity\\|${MENTION}\\|${NARRATOR}$`),
  correspondence: new RegExp(`^correspondence\\|(${HADITH})\\|(${HADITH})$`),
  translation: new RegExp(`^translation\\|${HADITH}\\|[a-z]{2,3}$`),
  grading: new RegExp(`^grading\\|assessment:${TOKEN}$`),
  narrator_verdict: new RegExp(`^narrator_verdict\\|${TOKEN}$`),
  biography: new RegExp(`^biography\\|${NARRATOR}\\|(death_year|birth_year|generation|residence|death_place|birth_place|tabaqa)\\|${TOKEN}$`),
  rijal_link: new RegExp(`^rijal_link\\|${NARRATOR}\\|[a-z0-9_]+\\|${TOKEN}$`),
  history: new RegExp(`^history\\|(event|epoch):${TOKEN}\\|(start|end|date|place|participant)$`),
  quran_citation: new RegExp(`^quran_citation\\|${HADITH}\\|\\d+\\|\\d+\\|\\d{1,3}:\\d{1,3}(-\\d{1,3})?$`),
  numbering: new RegExp(`^numbering\\|${HADITH}\\|[a-z0-9_]+$`),
  /** 0019: which routes a report's Arabic writes (the chain reader's claim; datasets/hadith-data/chain-reader). */
  chain_structure: new RegExp(`^chain_structure\\|${HADITH}$`),
};

export function isClaimKind(value: unknown): value is ClaimKind {
  return typeof value === 'string' && (CLAIM_KINDS as readonly string[]).includes(value);
}

/** Null when the key is well formed for its kind, else the reason. */
export function claimKeyProblem(kind: ClaimKind, key: string): string | null {
  if (!key.startsWith(`${kind}|`)) return `key must start with "${kind}|"`;
  if (!KEY_PATTERNS[kind].test(key)) return `key does not match the ${kind} grammar`;
  if (kind === 'correspondence') {
    const [, a, b] = KEY_PATTERNS.correspondence.exec(key)!;
    if (!(Buffer.compare(Buffer.from(a), Buffer.from(b)) < 0)) return 'correspondence pair must be in byte order (a < b)';
  }
  if (kind === 'quran_citation') {
    const parts = key.split('|');
    const start = Number(parts[parts.length - 3]);
    const end = Number(parts[parts.length - 2]);
    if (!(end > start)) return 'span end must be greater than start';
  }
  return null;
}

/** Byte-order compare, the same order as the database's `collate "C"` pair check. */
function byteOrder(a: string, b: string): [string, string] {
  return Buffer.compare(Buffer.from(a), Buffer.from(b)) < 0 ? [a, b] : [b, a];
}

export const claimKey = {
  identity: (mentionId: string, narratorId: string) => `identity|${mentionId}|${narratorId}`,
  correspondence: (hadithA: string, hadithB: string) => {
    const [a, b] = byteOrder(hadithA, hadithB);
    return `correspondence|${a}|${b}`;
  },
  translation: (hadithId: string, language: string) => `translation|${hadithId}|${language}`,
  grading: (assessmentId: string) => `grading|${assessmentId}`,
};

/** SHA-256 hex of UTF-8 text. */
export function sha256Hex(text: string): string {
  return createHash('sha256').update(text, 'utf8').digest('hex');
}

/**
 * The content hash a review binds to: SHA-256 over the claim key and the hashes of every text the claim depends on,
 * joined by U+001F in the order given. A change to any bound text changes the hash, so an old review goes stale
 * instead of silently carrying over.
 */
export function claimContentSha256(key: string, boundTextHashes: readonly string[]): string {
  return sha256Hex([key, ...boundTextHashes].join('\u001f'));
}

export const SHA256_PATTERN = /^[0-9a-f]{64}$/;
