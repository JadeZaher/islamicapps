import { GRADE_LABELS, mapToCanonical, type GradeCanonical } from '@/lib/constants/grade-taxonomy';

export { ConsensusBadge as VerdictBadge } from '@/components/ConsensusBadge';
export { TraditionBadge } from '@/components/TraditionBadge';

const GRADE_CLASSES: Record<GradeCanonical, string> = {
  sahih: 'bg-emerald-500/20 text-emerald-200 border-emerald-500/40',
  hasan: 'bg-lime-500/15 text-lime-200 border-lime-500/30',
  muwaththaq: 'bg-sky-500/15 text-sky-200 border-sky-500/30',
  mu_tabar: 'bg-sky-500/15 text-sky-200 border-sky-500/30',
  mukhtalaf: 'bg-amber-500/15 text-amber-200 border-amber-500/30',
  da_if: 'bg-orange-500/20 text-orange-200 border-orange-500/40',
  mursal: 'bg-orange-500/20 text-orange-200 border-orange-500/40',
  majhul: 'bg-slate-500/20 text-slate-200 border-slate-500/30',
  mawdu: 'bg-red-600/25 text-red-200 border-red-600/50',
  ungraded: '',
};

/** Hadith grade badge. Renders nothing when there is no grade: absence is not a verdict. */
export function GradeBadge({ grade }: { grade?: string | null }) {
  if (!grade) return null;
  const canonical = mapToCanonical(grade);
  if (canonical === 'ungraded') return null;
  return (
    <span className={`inline-block whitespace-nowrap rounded border px-2.5 py-1 text-xs font-semibold ${GRADE_CLASSES[canonical]}`}>
      {GRADE_LABELS[canonical]}
    </span>
  );
}
