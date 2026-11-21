/**
 * How reviews of one claim are summarised for display: counts by stance, never a score, a percentage or a ruling.
 * See src/lib/review/AGENTS.md §Summary.
 */

/** A human reviewer's stated view of a claim. Order here is display order. */
export const STANCES = ['agrees', 'qualifies', 'disagrees', 'cannot_decide'] as const;
export type Stance = (typeof STANCES)[number];

export const STANCE_LABEL: Readonly<Record<Stance, { one: string; many: string }>> = {
  agrees: { one: 'agrees', many: 'agree' },
  qualifies: { one: 'qualifies', many: 'qualify' },
  disagrees: { one: 'disagrees', many: 'disagree' },
  cannot_decide: { one: 'cannot decide', many: 'cannot decide' },
};

/** Outcome vocabulary of an AI review record (rule or specialist). */
export const AI_OUTCOMES = ['supports', 'contradicts', 'insufficient_evidence', 'contested'] as const;
export type AiOutcome = (typeof AI_OUTCOMES)[number];

export interface HumanReviewForSummary {
  id: string;
  reviewerId: string;
  stance: Stance;
  /** The content hash the reviewer read. */
  contentSha256: string;
  submittedAt: string;
  supersedesId: string | null;
  retired: boolean;
}

export interface AiReviewForSummary {
  kind: 'rule' | 'specialist';
  outcome: AiOutcome;
}

export type DisplayState = 'not_reviewed' | 'ai_reviewed' | 'reviewers_differ' | 'ai_did_not_support';

export interface ClaimSummary {
  state: DisplayState;
  /** Live, hash-current reviews, one per reviewer (the latest), in display order. */
  current: HumanReviewForSummary[];
  /** Reviews bound to an earlier text: listed, never counted. */
  stale: HumanReviewForSummary[];
  counts: Record<Stance, number>;
  label: string;
}

/**
 * Summarise one claim. Rules: one view per reviewer (a superseded or retired review is history, not a second voice);
 * a review of a different text is stale and not counted; nothing is weighted, netted or turned into a percentage.
 * A claim is "reviewers differ" whenever any current view disagrees or any AI review is contested: both views show.
 */
export function summariseClaim(
  currentContentSha256: string,
  aiReviews: readonly AiReviewForSummary[],
  humanReviews: readonly HumanReviewForSummary[],
): ClaimSummary {
  const superseded = new Set(humanReviews.map((review) => review.supersedesId).filter((id): id is string => id !== null));
  const live = humanReviews.filter((review) => !review.retired && !superseded.has(review.id));
  const latestByReviewer = new Map<string, HumanReviewForSummary>();
  for (const review of live) {
    const previous = latestByReviewer.get(review.reviewerId);
    if (!previous || review.submittedAt > previous.submittedAt) latestByReviewer.set(review.reviewerId, review);
  }
  const latest = [...latestByReviewer.values()];
  const current = latest
    .filter((review) => review.contentSha256 === currentContentSha256)
    .sort((a, b) => STANCES.indexOf(a.stance) - STANCES.indexOf(b.stance) || a.submittedAt.localeCompare(b.submittedAt));
  const stale = latest.filter((review) => review.contentSha256 !== currentContentSha256);

  const counts = Object.fromEntries(STANCES.map((stance) => [stance, 0])) as Record<Stance, number>;
  for (const review of current) counts[review.stance] += 1;

  const aiSupports = aiReviews.some((review) => review.outcome === 'supports');
  const aiContested = aiReviews.some((review) => review.outcome === 'contested');
  const aiAgainst = aiReviews.length > 0 && aiReviews.every((review) => review.outcome === 'contradicts' || review.outcome === 'insufficient_evidence');

  let state: DisplayState;
  if (counts.disagrees > 0 || aiContested) state = 'reviewers_differ';
  else if (aiSupports) state = 'ai_reviewed';
  else if (aiAgainst) state = 'ai_did_not_support';
  else state = 'not_reviewed';

  return { state, current, stale, counts, label: summaryLabel(state, aiReviews, counts, stale.length) };
}

const STATE_PREFIX: Readonly<Record<DisplayState, string>> = {
  not_reviewed: 'Not yet reviewed',
  ai_reviewed: 'AI-reviewed',
  reviewers_differ: 'Reviewers differ',
  ai_did_not_support: 'AI review did not support this',
};

/** "AI-reviewed (checked by rule) · 3 human reviews: 2 agree, 1 qualifies · 1 review of an earlier text". */
export function summaryLabel(
  state: DisplayState,
  aiReviews: readonly AiReviewForSummary[],
  counts: Readonly<Record<Stance, number>>,
  staleCount: number,
): string {
  const kinds = new Set(aiReviews.map((review) => review.kind));
  const how = [kinds.has('rule') ? 'checked by rule' : null, kinds.has('specialist') ? 'AI specialist review' : null]
    .filter(Boolean)
    .join(' and ');
  const parts = [how ? `${STATE_PREFIX[state]} (${how})` : STATE_PREFIX[state]];
  const total = STANCES.reduce((sum, stance) => sum + counts[stance], 0);
  if (total > 0) {
    const byStance = STANCES.filter((stance) => counts[stance] > 0)
      .map((stance) => `${counts[stance]} ${counts[stance] === 1 ? STANCE_LABEL[stance].one : STANCE_LABEL[stance].many}`)
      .join(', ');
    parts.push(`${total} human ${total === 1 ? 'review' : 'reviews'}: ${byStance}`);
  }
  if (staleCount > 0) parts.push(`${staleCount} ${staleCount === 1 ? 'review' : 'reviews'} of an earlier text`);
  return parts.join(' · ');
}
