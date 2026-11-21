/** The four tradition marks: one framed square module, divided four ways. Alphabetical, equal weight, none a default. See DESIGN.md §Tradition marks. */
import { MarkSvg, type MarkProps } from './MarkSvg';

export type HadithTradition = 'Ibadi' | 'Imami' | 'Sunni' | 'Zaydi';

export const HADITH_TRADITIONS: readonly HadithTradition[] = ['Ibadi', 'Imami', 'Sunni', 'Zaydi'];

/** SVG stroke-dasharray per tradition, for lines that must carry the tradition in black and white (timeline lanes, legends). */
export const TRADITION_DASH: Record<HadithTradition, string> = {
  Ibadi: '6 2',
  Imami: '1.5 2',
  Sunni: '6 2 1.5 2',
  Zaydi: '3 3',
};

/** Fill of each module on a 12-unit grid; the 1-unit frame is shared. */
function Division({ tradition }: { tradition: HadithTradition }) {
  switch (tradition) {
    case 'Ibadi':
      return <rect x="0" y="6" width="12" height="6" fill="currentColor" />;
    case 'Imami':
      return <rect x="0" y="0" width="6" height="12" fill="currentColor" />;
    case 'Sunni':
      return <path d="M0 0V12H12Z" fill="currentColor" shapeRendering="geometricPrecision" />;
    case 'Zaydi':
      return <rect x="3" y="3" width="6" height="6" fill="currentColor" />;
  }
}

export function TraditionMark({ tradition, title, ...props }: MarkProps & { tradition: HadithTradition }) {
  return (
    <MarkSvg viewBox="0 0 12 12" title={title ?? `${tradition} tradition`} {...props}>
      <rect x="0.5" y="0.5" width="11" height="11" stroke="currentColor" strokeWidth="1" />
      <Division tradition={tradition} />
    </MarkSvg>
  );
}

/** A short line sample in the tradition's dash pattern, for legends. */
export function TraditionLine({ tradition, title, size = 24, ...props }: MarkProps & { tradition: HadithTradition }) {
  return (
    <MarkSvg viewBox="0 0 24 4" title={title ?? `${tradition} chain line`} size={size} height={size / 6} {...props}>
      <line x1="0" y1="2" x2="24" y2="2" stroke="currentColor" strokeWidth="1.5" strokeDasharray={TRADITION_DASH[tradition]} />
    </MarkSvg>
  );
}
