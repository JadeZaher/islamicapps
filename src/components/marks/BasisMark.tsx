/** Identity-basis markers: a circle that fills as the basis firms up; kunya-only is a bar because it is a label, not a rung. See DESIGN.md §Basis labels. */
import type { IdentityBasis } from '@/db/queries/contracts';
import { MarkSvg, type MarkProps } from './MarkSvg';

/** Same wording as BASIS_LABEL in src/app/hadith/[id]/components/IsnadChain.tsx; the application pass keeps one copy. */
export const IDENTITY_BASIS_LABEL: Record<IdentityBasis, string> = {
  reviewer_decision: 'verified by a reviewer',
  source_index_confirmed_by_text: "machine-reviewed: matches the source's index and the text",
  source_index: 'source index',
  name_exact: 'matched by name',
  name_spelling_fold: 'matched by name',
  name_kunya_only: 'matched by kunya only',
};

function Shape({ basis }: { basis: IdentityBasis }) {
  switch (basis) {
    case 'reviewer_decision':
      return <circle cx="5" cy="5" r="4.5" fill="currentColor" />;
    case 'source_index_confirmed_by_text':
      return (
        <>
          <circle cx="5" cy="5" r="4" stroke="currentColor" strokeWidth="1" />
          <circle cx="5" cy="5" r="2" fill="currentColor" />
        </>
      );
    case 'source_index':
      return <circle cx="5" cy="5" r="4" stroke="currentColor" strokeWidth="1" />;
    case 'name_exact':
    case 'name_spelling_fold':
      return <circle cx="5" cy="5" r="4" stroke="currentColor" strokeWidth="1" strokeDasharray="1.8 1.35" />;
    case 'name_kunya_only':
      return <rect x="1" y="4.25" width="8" height="1.5" fill="currentColor" shapeRendering="crispEdges" />;
  }
}

export function BasisMark({ basis, title, size = 10, ...props }: MarkProps & { basis: IdentityBasis }) {
  return (
    <MarkSvg viewBox="0 0 10 10" title={title ?? IDENTITY_BASIS_LABEL[basis]} size={size} {...props}>
      <g shapeRendering="geometricPrecision">
        <Shape basis={basis} />
      </g>
    </MarkSvg>
  );
}
