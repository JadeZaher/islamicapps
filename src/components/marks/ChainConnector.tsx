/** Vertical connector between two positions of an isnad list: a hairline, dashed where the chain as written has no named link. See DESIGN.md §Isnad list. */
import { TRADITION_DASH, type HadithTradition } from './TraditionMark';

export type ChainConnectorVariant = 'continuous' | 'gap';

/** Decorative: the order is carried by the ordered list it sits in. Stretches to its container's height. */
export function ChainConnector({
  variant = 'continuous',
  tradition,
  emphasis = false,
  className,
}: {
  variant?: ChainConnectorVariant;
  /** Draw in the tradition's dash pattern (only where several traditions share one plot). */
  tradition?: HadithTradition;
  /** 2px instead of 1px: the selected chain. */
  emphasis?: boolean;
  className?: string;
}) {
  const dash = variant === 'gap' ? '2 3' : tradition ? TRADITION_DASH[tradition] : undefined;
  return (
    <svg viewBox="0 0 12 10" preserveAspectRatio="none" width="12" height="100%" className={className} aria-hidden="true" focusable="false">
      <line
        x1="6" y1="0" x2="6" y2="10"
        stroke="currentColor"
        strokeWidth={emphasis ? 2 : 1}
        strokeDasharray={dash}
        vectorEffect="non-scaling-stroke"
        shapeRendering="crispEdges"
      />
    </svg>
  );
}
