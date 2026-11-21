/** The product mark: the four tradition modules in one 2x2 square, none first. See DESIGN.md §Site header. */
import { MarkSvg, type MarkProps } from './MarkSvg';

export function ProductMark({ title = 'Shura wa Istehsan', size = 16, ...props }: MarkProps) {
  return (
    <MarkSvg viewBox="0 0 16 16" title={title} size={size} {...props}>
      <g stroke="currentColor" strokeWidth="1">
        <rect x="0.5" y="0.5" width="6" height="6" />
        <rect x="9.5" y="0.5" width="6" height="6" />
        <rect x="0.5" y="9.5" width="6" height="6" />
        <rect x="9.5" y="9.5" width="6" height="6" />
      </g>
      <g fill="currentColor">
        {/* Ibadi: lower half; Imami: left half; Sunni: lower-left diagonal; Zaydi: centre square. */}
        <rect x="0" y="3.5" width="7" height="3.5" />
        <rect x="9" y="0" width="3.5" height="7" />
        <path d="M0 9V16H7Z" shapeRendering="geometricPrecision" />
        <rect x="11" y="11" width="3" height="3" />
      </g>
    </MarkSvg>
  );
}
