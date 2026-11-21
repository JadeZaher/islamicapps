/** Shared frame for every mark: flat, currentColor, titled for assistive technology unless decorative. See DESIGN.md §Marks. */
import { useId } from 'react';

export interface MarkProps {
  /** Accessible name; each mark supplies a default. */
  title?: string;
  /** Hide from assistive technology when visible text beside the mark already says the same thing. */
  decorative?: boolean;
  /** Rendered size in CSS px (square). */
  size?: number;
  className?: string;
}

interface MarkSvgProps extends MarkProps {
  viewBox: string;
  title: string;
  /** Height in CSS px when the mark is not square; defaults to `size`. */
  height?: number;
  children: React.ReactNode;
}

export function MarkSvg({ viewBox, title, decorative = false, size = 12, height, className, children }: MarkSvgProps) {
  const titleId = useId();
  const accessibility = decorative
    ? ({ 'aria-hidden': true } as const)
    : ({ role: 'img', 'aria-labelledby': titleId } as const);
  return (
    <svg
      viewBox={viewBox}
      width={size}
      height={height ?? size}
      className={className}
      fill="none"
      focusable="false"
      shapeRendering="crispEdges"
      {...accessibility}
    >
      {!decorative && <title id={titleId}>{title}</title>}
      {children}
    </svg>
  );
}
