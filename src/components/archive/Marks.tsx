/** Archive call sites of the design-system marks (src/components/marks/); decorative because a word always sits beside them. */
import { ArrowIcon, NarratorNode } from '@/components/marks';

export { ArrowIcon, NarratorNode };

export function ArrowMark({ direction, className }: { direction: 'left' | 'right'; className?: string }) {
  return <ArrowIcon direction={direction} decorative className={className} />;
}

export function SquareMark({ className }: { className?: string }) {
  return <NarratorNode kind="identified" decorative size={10} className={className} />;
}
