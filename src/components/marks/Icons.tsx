/** Interface icons on a 16-unit grid: 1.5 stroke, square caps, mitred joins, no fills. See DESIGN.md §Icons. */
import { MarkSvg, type MarkProps } from './MarkSvg';

const STROKE = { stroke: 'currentColor', strokeWidth: 1.5, strokeLinecap: 'square', strokeLinejoin: 'miter' } as const;

function Icon({ title, size = 16, d, ...props }: MarkProps & { title: string; d: string }) {
  return (
    <MarkSvg viewBox="0 0 16 16" title={title} size={size} {...props}>
      <g shapeRendering="geometricPrecision">
        <path d={d} {...STROKE} />
      </g>
    </MarkSvg>
  );
}

const ARROW_PATHS = {
  left: 'M13.5 8H3M7 4L3 8l4 4',
  right: 'M2.5 8H13M9 4l4 4-4 4',
  up: 'M8 13.5V3M4 7l4-4 4 4',
  down: 'M8 2.5V13M4 9l4 4 4-4',
} as const;

/** Physical direction; for "back"/"next" in RTL text, swap left and right at the call site. */
export function ArrowIcon({ direction, title, ...props }: MarkProps & { direction: keyof typeof ARROW_PATHS }) {
  return <Icon d={ARROW_PATHS[direction]} title={title ?? `arrow ${direction}`} {...props} />;
}

export function SearchIcon({ title = 'search', ...props }: MarkProps) {
  return <Icon d="M7 2.5a4.5 4.5 0 1 0 0 9 4.5 4.5 0 0 0 0-9zM10.5 10.5L14 14" title={title} {...props} />;
}

export function ExternalIcon({ title = 'opens another site', ...props }: MarkProps) {
  return <Icon d="M9 2.5h4.5V7M13.5 2.5L7.5 8.5M11 9.5v4H2.5V5h4" title={title} {...props} />;
}

export function CopyIcon({ title = 'copy', ...props }: MarkProps) {
  return <Icon d="M5.5 5.5h8v8h-8zM10.5 5.5v-3h-8v8h3" title={title} {...props} />;
}

export function CheckIcon({ title = 'done', ...props }: MarkProps) {
  return <Icon d="M2.5 8.5l3.5 3.5 7.5-8" title={title} {...props} />;
}

export function CloseIcon({ title = 'close', ...props }: MarkProps) {
  return <Icon d="M3 3l10 10M13 3L3 13" title={title} {...props} />;
}

export function ChevronIcon({ title = 'expand', open = false, ...props }: MarkProps & { open?: boolean }) {
  return <Icon d={open ? 'M3.5 10l4.5-4.5 4.5 4.5' : 'M3.5 6l4.5 4.5 4.5-4.5'} title={title} {...props} />;
}

export function MenuIcon({ title = 'menu', ...props }: MarkProps) {
  return <Icon d="M2 4h12M2 8h12M2 12h12" title={title} {...props} />;
}
