/**
 * Pure, client-safe: how a mention's identity candidates group into people and whether they disagree. Mirrors
 * `contests` in datasets/hadith-data/pg_export/external_identity.py. See src/db/AGENTS.md §External identity.
 */
import type { ChainMentionCandidate, IdentityBasis, MentionIdentity } from './contracts';

/** Labels, never contests (owner 2026-11-21): kunya-only names and a shared Imam kunya left undecided. */
export const NON_CONTESTING_BASES: ReadonlySet<IdentityBasis> = new Set(['name_kunya_only', 'imam_kunya_candidate']);

/** Strongest basis first: the order candidates are listed and labelled in. */
export const BASIS_ORDER: IdentityBasis[] = [
  'reviewer_decision',
  'source_index_confirmed_by_text',
  'imam_kunya_convention',
  'source_hadith_kg_confirmed_by_text',
  'source_riwayat_confirmed_by_text',
  'source_index',
  'source_hadith_kg',
  'source_riwayat',
  'name_exact',
  'name_spelling_fold',
  'name_kunya_only',
  'imam_kunya_candidate',
];

/** A candidate that can contest another: not a label basis and not aimed at a placeholder record. */
export function isContesting(candidate: ChainMentionCandidate): boolean {
  return !NON_CONTESTING_BASES.has(candidate.basis) && !candidate.placeholder;
}

/** The registry a person key belongs to (`rawi`, `hadith-kg`, `riwayat`, `imam`). */
function keyAuthority(key: string): string {
  return key.split(':')[1] ?? key;
}

export function personKey(candidate: ChainMentionCandidate): string {
  return candidate.person_key ?? candidate.narrator_id;
}

/** One narrator record a mention's candidates name, with every basis that names it, strongest first. */
export interface IdentityRecord {
  narratorId: string;
  candidate: ChainMentionCandidate;
  candidates: ChainMentionCandidate[];
}

/** Every record the candidates name for one person (records linked to each other share a person key). */
export interface IdentityGroup {
  personKey: string;
  records: IdentityRecord[];
  /** Every candidate of the group is a label (kunya-only, shared Imam kunya, placeholder record). */
  labelOnly: boolean;
}

/** Groups by person key, in the order of the strongest basis in each group. */
export function groupCandidates(candidates: ChainMentionCandidate[]): IdentityGroup[] {
  const ordered = [...candidates].sort(
    (left, right) => BASIS_ORDER.indexOf(left.basis) - BASIS_ORDER.indexOf(right.basis) || left.narrator_id.localeCompare(right.narrator_id),
  );
  const groups = new Map<string, IdentityGroup>();
  for (const candidate of ordered) {
    const key = personKey(candidate);
    const group = groups.get(key) ?? { personKey: key, records: [], labelOnly: true };
    let record = group.records.find((item) => item.narratorId === candidate.narrator_id);
    if (!record) {
      record = { narratorId: candidate.narrator_id, candidate, candidates: [] };
      group.records.push(record);
    }
    record.candidates.push(candidate);
    if (isContesting(candidate)) group.labelOnly = false;
    groups.set(key, group);
  }
  return [...groups.values()];
}

/**
 * `differ` only when two contesting groups name different people of one registry (known to differ); records in
 * different registries with no link between them are not comparable, so they are listed, not called a disagreement.
 */
export function mentionIdentity(candidates: ChainMentionCandidate[]): MentionIdentity {
  if (candidates.length === 0) return 'unidentified';
  const byAuthority = new Map<string, Set<string>>();
  for (const candidate of candidates.filter(isContesting)) {
    const key = personKey(candidate);
    byAuthority.set(keyAuthority(key), (byAuthority.get(keyAuthority(key)) ?? new Set()).add(key));
  }
  return [...byAuthority.values()].some((people) => people.size > 1) ? 'differ' : 'agreed';
}
