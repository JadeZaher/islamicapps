/** Flat geometric marks (Swiss direction): line arrows and a square bullet, drawn in currentColor. */

export function ArrowMark({ direction, className }: { direction: 'left' | 'right'; className?: string }) {
  const path = direction === 'left' ? 'M14 8H2M6 4L2 8l4 4' : 'M2 8h12M10 4l4 4-4 4';
  return (
    <svg aria-hidden="true" viewBox="0 0 16 16" width="16" height="16" className={className} fill="none" stroke="currentColor" strokeWidth="1.25">
      <path d={path} />
    </svg>
  );
}

export function SquareMark({ className }: { className?: string }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 8 8" width="8" height="8" className={className}>
      <rect width="8" height="8" fill="currentColor" />
    </svg>
  );
}
