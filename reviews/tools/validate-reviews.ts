/**
 * Validate the human-review files under reviews/ (format: reviews/README.md): reviewer profiles, endorsements and
 * reviews. Standalone: not wired into the loader. Run: npx tsx reviews/tools/validate-reviews.ts [reviews-dir]
 */
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import path from 'node:path';
import { claimKeyProblem, FIELD_FOR_CLAIM, isClaimKind, REVIEW_FIELDS, SHA256_PATTERN, type ReviewField } from '../../src/lib/review/claim-key';
import { citationProblems, TRADITIONS } from '../../src/lib/review/citation-standard';
import { STANCES } from '../../src/lib/review/summary';

export const REVIEWER_FORMAT = 'shura-reviewer/1';
export const ENDORSEMENT_FORMAT = 'shura-endorsement/1';
export const REVIEW_FORMAT = 'shura-review/1';
export const CAPABILITIES = ['review', 'discuss', 'propose', 'endorse'] as const;

const HANDLE = /^[a-z0-9](?:[a-z0-9-]{0,37}[a-z0-9])?$/;
const DATE = /^\d{4}-\d{2}-\d{2}$/;
const REVIEW_ID = /^rv-\d{4}-\d{2}-\d{2}-[a-z0-9-]+-\d{3,}$/;
const nonEmpty = (value: unknown): value is string => typeof value === 'string' && value.trim().length > 0;

interface Permission {
  capability: (typeof CAPABILITIES)[number];
  fields: (ReviewField | 'all')[];
  granted_by: string;
  granted_on: string;
  basis: 'owner' | 'endorsement';
  endorsement_id?: string;
}

function unknownKeys(object: Record<string, unknown>, allowed: readonly string[], where: string): string[] {
  return Object.keys(object).filter((key) => !allowed.includes(key)).map((key) => `${where}: unknown field "${key}"`);
}

/** True when `handle` held `capability` for `field` on `date` (grants are dated; nothing is revoked by deletion). */
export function holds(reviewers: Map<string, Record<string, unknown>>, handle: string, capability: string, field: string, date: string): boolean {
  const profile = reviewers.get(handle);
  const permissions = (profile?.permissions as Permission[] | undefined) ?? [];
  const retired = (profile?.retired_on as string | undefined) ?? null;
  if (retired && retired <= date) return false;
  return permissions.some(
    (permission) =>
      permission.capability === capability &&
      (permission.fields.includes('all') || permission.fields.includes(field as ReviewField)) &&
      permission.granted_on <= date,
  );
}

/**
 * Every problem in a set of files keyed by path relative to the reviews/ root (forward slashes). `modelIds` are the
 * model registry ids an `ai_assistance.model` may name.
 */
export function validateReviewFiles(files: ReadonlyMap<string, string>, modelIds: ReadonlySet<string>): string[] {
  const problems: string[] = [];
  const parsed = new Map<string, Record<string, unknown>>();
  for (const [file, text] of files) {
    if (!file.endsWith('.json')) continue;
    try {
      const value = JSON.parse(text) as unknown;
      if (!value || typeof value !== 'object' || Array.isArray(value)) problems.push(`${file}: not a JSON object`);
      else parsed.set(file, value as Record<string, unknown>);
    } catch {
      problems.push(`${file}: not valid JSON`);
    }
  }

  // Reviewer profiles: reviewers/<handle>.json
  const reviewers = new Map<string, Record<string, unknown>>();
  for (const [file, profile] of parsed) {
    const match = /^reviewers\/([^/]+)\.json$/.exec(file);
    if (!match) continue;
    problems.push(...unknownKeys(profile, ['format', 'handle', 'display_name', 'affiliation', 'tradition_context', 'profile_url', 'orcid', 'permissions', 'retired_on', 'retired_reason'], file));
    if (profile.format !== REVIEWER_FORMAT) problems.push(`${file}: format must be "${REVIEWER_FORMAT}"`);
    if (profile.handle !== match[1] || !HANDLE.test(match[1])) problems.push(`${file}: handle must equal the file name and be a lowercase GitHub-style handle`);
    if (!nonEmpty(profile.display_name)) problems.push(`${file}: display_name is required (reviews are never anonymous)`);
    if (profile.tradition_context != null && !(TRADITIONS as readonly string[]).includes(String(profile.tradition_context))) {
      problems.push(`${file}: tradition_context must be Ibadi, Imami, Sunni, Zaydi or null`);
    }
    if (profile.retired_on != null && (!DATE.test(String(profile.retired_on)) || !nonEmpty(profile.retired_reason))) {
      problems.push(`${file}: retired_on needs a date and a retired_reason`);
    }
    const permissions = Array.isArray(profile.permissions) ? (profile.permissions as Record<string, unknown>[]) : null;
    if (!permissions) problems.push(`${file}: permissions must be a list`);
    else
      permissions.forEach((permission, index) => {
        const where = `${file}: permissions[${index}]`;
        problems.push(...unknownKeys(permission, ['capability', 'fields', 'granted_by', 'granted_on', 'basis', 'endorsement_id'], where));
        if (!(CAPABILITIES as readonly string[]).includes(String(permission.capability))) problems.push(`${where}: capability must be one of ${CAPABILITIES.join(', ')}`);
        const fields = permission.fields;
        if (!Array.isArray(fields) || fields.length === 0 || !fields.every((field) => field === 'all' || (REVIEW_FIELDS as readonly string[]).includes(field))) {
          problems.push(`${where}: fields must list ${REVIEW_FIELDS.join(', ')} or "all"`);
        }
        if (!DATE.test(String(permission.granted_on))) problems.push(`${where}: granted_on must be YYYY-MM-DD`);
        if (permission.basis === 'owner') {
          if (permission.granted_by !== 'owner') problems.push(`${where}: an owner grant has granted_by "owner"`);
        } else if (permission.basis === 'endorsement') {
          if (!nonEmpty(permission.endorsement_id)) problems.push(`${where}: an endorsement grant names its endorsement_id`);
        } else problems.push(`${where}: basis must be "owner" or "endorsement"`);
      });
    reviewers.set(match[1], profile);
  }

  // Endorsements: endorsements/<id>.json
  const endorsements = new Map<string, Record<string, unknown>>();
  for (const [file, endorsement] of parsed) {
    const match = /^endorsements\/([^/]+)\.json$/.exec(file);
    if (!match) continue;
    problems.push(...unknownKeys(endorsement, ['format', 'id', 'endorser', 'endorsee', 'field', 'statement', 'endorsed_on'], file));
    if (endorsement.format !== ENDORSEMENT_FORMAT) problems.push(`${file}: format must be "${ENDORSEMENT_FORMAT}"`);
    if (endorsement.id !== match[1]) problems.push(`${file}: id must equal the file name`);
    if (endorsement.endorser === endorsement.endorsee) problems.push(`${file}: a reviewer cannot endorse themselves`);
    if (!nonEmpty(endorsement.statement)) problems.push(`${file}: statement is required`);
    if (!DATE.test(String(endorsement.endorsed_on))) problems.push(`${file}: endorsed_on must be YYYY-MM-DD`);
    if (!reviewers.has(String(endorsement.endorsee))) problems.push(`${file}: endorsee ${String(endorsement.endorsee)} has no reviewer profile`);
    if (!holds(reviewers, String(endorsement.endorser), 'endorse', String(endorsement.field), String(endorsement.endorsed_on))) {
      problems.push(`${file}: ${String(endorsement.endorser)} did not hold "endorse" for ${String(endorsement.field)} on ${String(endorsement.endorsed_on)}`);
    }
    endorsements.set(match[1], endorsement);
  }
  for (const [handle, profile] of reviewers) {
    for (const permission of (profile.permissions as Permission[] | undefined) ?? []) {
      if (permission.basis !== 'endorsement') continue;
      const endorsement = endorsements.get(String(permission.endorsement_id));
      if (!endorsement) problems.push(`reviewers/${handle}.json: endorsement ${String(permission.endorsement_id)} does not exist`);
      else if (endorsement.endorsee !== handle || endorsement.endorser !== permission.granted_by) {
        problems.push(`reviewers/${handle}.json: endorsement ${String(permission.endorsement_id)} is not from ${permission.granted_by} to ${handle}`);
      } else if (!permission.fields.every((field) => field === endorsement.field)) {
        problems.push(`reviewers/${handle}.json: an endorsement grants only its own field (${String(endorsement.field)})`);
      }
    }
  }

  // Reviews: entries/<handle>/<id>.json
  const reviews = new Map<string, { file: string; review: Record<string, unknown> }>();
  for (const [file, review] of parsed) {
    const match = /^entries\/([^/]+)\/([^/]+)\.json$/.exec(file);
    if (!match) {
      if (!/^(reviewers|endorsements)\//.test(file) && !file.startsWith('ai/')) problems.push(`${file}: not in reviewers/, endorsements/ or entries/<handle>/`);
      continue;
    }
    const [, handle, id] = match;
    problems.push(...unknownKeys(review, ['format', 'id', 'reviewer', 'claim', 'stance', 'note', 'language', 'tradition_context', 'citations', 'ai_assistance', 'supersedes', 'submitted'], file));
    if (review.format !== REVIEW_FORMAT) problems.push(`${file}: format must be "${REVIEW_FORMAT}"`);
    if (review.id !== id || !REVIEW_ID.test(id)) problems.push(`${file}: id must equal the file name and look like rv-YYYY-MM-DD-<handle>-NNN`);
    if (review.reviewer !== handle) problems.push(`${file}: reviewer must equal the directory name`);
    if (!DATE.test(String(review.submitted))) problems.push(`${file}: submitted must be YYYY-MM-DD`);
    const claim = review.claim as Record<string, unknown> | undefined;
    const kind = claim?.kind;
    if (!claim || !isClaimKind(kind)) problems.push(`${file}: claim.kind must be a claim kind`);
    else {
      const keyProblem = typeof claim.key === 'string' ? claimKeyProblem(kind, claim.key) : 'claim.key is required';
      if (keyProblem) problems.push(`${file}: ${keyProblem}`);
      if (typeof claim.content_sha256 !== 'string' || !SHA256_PATTERN.test(claim.content_sha256)) {
        problems.push(`${file}: claim.content_sha256 must be the 64-hex hash shown with the claim`);
      }
      if (!holds(reviewers, handle, 'review', FIELD_FOR_CLAIM[kind], String(review.submitted))) {
        problems.push(`${file}: ${handle} did not hold "review" for ${FIELD_FOR_CLAIM[kind]} on ${String(review.submitted)}`);
      }
    }
    const stance = String(review.stance);
    if (!(STANCES as readonly string[]).includes(stance)) problems.push(`${file}: stance must be one of ${STANCES.join(', ')}`);
    if (!nonEmpty(review.note)) problems.push(`${file}: note is required`);
    if (!nonEmpty(review.language) || !/^[a-z]{2,3}(-[A-Za-z0-9]+)*$/.test(String(review.language))) problems.push(`${file}: language must be a language tag such as en or ar`);
    if (review.tradition_context != null && !(TRADITIONS as readonly string[]).includes(String(review.tradition_context))) {
      problems.push(`${file}: tradition_context must be Ibadi, Imami, Sunni, Zaydi or null`);
    }
    const citations = Array.isArray(review.citations) ? review.citations : null;
    if (!citations) problems.push(`${file}: citations must be a list`);
    else {
      if (stance !== 'cannot_decide' && citations.length === 0) problems.push(`${file}: a stance of ${stance} needs at least one citation`);
      citations.forEach((citation, index) => {
        for (const problem of citationProblems(citation, 'review')) problems.push(`${file}: citations[${index}]: ${problem}`);
      });
    }
    if (review.ai_assistance != null) {
      const assistance = review.ai_assistance as Record<string, unknown>;
      if (!modelIds.has(String(assistance.model))) problems.push(`${file}: ai_assistance.model must be a model registry id`);
      if (!['drafting', 'translation', 'search'].includes(String(assistance.role))) problems.push(`${file}: ai_assistance.role must be drafting, translation or search`);
    }
    if (reviews.has(id)) problems.push(`${file}: review id ${id} is used twice`);
    reviews.set(id, { file, review });
  }

  // Supersession: same reviewer, same claim, linear, and one live review per reviewer and claim.
  const supersededBy = new Map<string, string>();
  for (const [id, { file, review }] of reviews) {
    if (review.supersedes == null) continue;
    const earlier = reviews.get(String(review.supersedes));
    if (!earlier) problems.push(`${file}: supersedes ${String(review.supersedes)}, which does not exist`);
    else {
      if (earlier.review.reviewer !== review.reviewer) problems.push(`${file}: may supersede only the same reviewer's review`);
      if ((earlier.review.claim as Record<string, unknown>)?.key !== (review.claim as Record<string, unknown>)?.key) problems.push(`${file}: supersedes a review of a different claim`);
      if (String(earlier.review.submitted) > String(review.submitted)) problems.push(`${file}: supersedes a later review`);
    }
    if (supersededBy.has(String(review.supersedes))) problems.push(`${file}: ${String(review.supersedes)} is already superseded by ${supersededBy.get(String(review.supersedes))}`);
    supersededBy.set(String(review.supersedes), id);
  }
  const liveByReviewerClaim = new Map<string, string>();
  for (const [id, { file, review }] of reviews) {
    if (supersededBy.has(id)) continue;
    const key = `${String(review.reviewer)}\u001f${String((review.claim as Record<string, unknown>)?.key)}`;
    const other = liveByReviewerClaim.get(key);
    if (other) problems.push(`${file}: ${String(review.reviewer)} already has live review ${other} of this claim; supersede it instead`);
    liveByReviewerClaim.set(key, id);
  }
  return problems;
}

/** Read every file under a reviews/ directory (skipping tools/, ai/ and README files) into the map the validator takes. */
export function readReviewTree(root: string): Map<string, string> {
  const files = new Map<string, string>();
  const walk = (directory: string) => {
    for (const name of readdirSync(directory)) {
      const full = path.join(directory, name);
      const relative = path.relative(root, full).replace(/\\/g, '/');
      if (/^(tools|ai)(\/|$)/.test(relative)) continue;
      if (statSync(full).isDirectory()) walk(full);
      else if (name.endsWith('.json')) files.set(relative, readFileSync(full, 'utf8'));
    }
  };
  if (existsSync(root)) walk(root);
  return files;
}

export function modelRegistryIds(repositoryRoot: string): Set<string> {
  const registry = JSON.parse(readFileSync(path.join(repositoryRoot, 'datasets', 'hadith-data', 'model_registry.json'), 'utf8')) as {
    entries: { id: string; model_id: string | null }[];
  };
  return new Set(registry.entries.flatMap((entry) => [entry.id, entry.model_id].filter((value): value is string => !!value)));
}

if (require.main === module) {
  const repositoryRoot = path.resolve(__dirname, '..', '..');
  const root = path.resolve(process.argv[2] ?? path.join(repositoryRoot, 'reviews'));
  const files = readReviewTree(root);
  const problems = validateReviewFiles(files, modelRegistryIds(repositoryRoot));
  for (const problem of problems) console.error(`FAIL ${problem}`);
  console.log(problems.length === 0 ? `ok   ${files.size} review files valid` : `${problems.length} problems`);
  process.exitCode = problems.length === 0 ? 0 : 1;
}
