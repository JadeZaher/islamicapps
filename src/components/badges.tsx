import { GRADE_LABELS, mapToCanonical } from '@/lib/constants/grade-taxonomy';

export { ConsensusBadge as VerdictBadge } from '@/components/ConsensusBadge';
export { TraditionBadge } from '@/components/TraditionBadge';

/** Hadith grade as a muted uppercase label (DESIGN.md §Badges: no colour per grade). Renders nothing when there is no grade: absence is not a verdict. */
export function GradeBadge({ grade }: { grade?: string | null }) {
  if (!grade) return null;
  const canonical = mapToCanonical(grade);
  if (canonical === 'ungraded') return null;
  return (
    <span className="type-label inline-block whitespace-nowrap">
      {GRADE_LABELS[canonical]}
    </span>
  );
}
