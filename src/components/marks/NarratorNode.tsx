/** Narrator nodes for the transmission graph and its legend: squares, filled when identified. See DESIGN.md §Transmission graph. */
import { MarkSvg, type MarkProps } from './MarkSvg';

/**
 * identified: a mention linked to a narrator record. unidentified: plain-text mention (never a link).
 * shared: an identified narrator through whom two or more chains of this report pass.
 * contested: sources give different identities; both are listed, neither preferred.
 */
export type NarratorNodeKind = 'identified' | 'unidentified' | 'shared' | 'contested';

export const NARRATOR_NODE_LABEL: Record<NarratorNodeKind, string> = {
  identified: 'identified narrator',
  unidentified: 'name not identified',
  shared: 'narrator shared by several chains',
  contested: 'sources give different identities',
};

/** The node drawn inside a larger SVG, centred on (x, y). Selection is an accent wash square plus a 2px accent frame, never a shadow. */
export function NarratorNodeShape({ kind, x, y, selected = false }: { kind: NarratorNodeKind; x: number; y: number; selected?: boolean }) {
  const half = 4;
  return (
    <g shapeRendering="crispEdges">
      {selected && (
        <rect x={x - 9} y={y - 9} width={18} height={18} fill="var(--color-accent-wash)" stroke="var(--color-accent)" strokeWidth={2} />
      )}
      {kind === 'identified' && <rect x={x - half} y={y - half} width={8} height={8} fill="currentColor" />}
      {kind === 'unidentified' && (
        <rect x={x - half + 0.5} y={y - half + 0.5} width={7} height={7} fill="var(--color-paper)" stroke="currentColor" strokeWidth={1} />
      )}
      {kind === 'shared' && (
        <>
          <rect x={x - 6.5} y={y - 6.5} width={13} height={13} fill="var(--color-paper)" stroke="currentColor" strokeWidth={1} />
          <rect x={x - half} y={y - half} width={8} height={8} fill="currentColor" />
        </>
      )}
      {kind === 'contested' && (
        <>
          <rect x={x - half} y={y - half} width={3} height={8} fill="currentColor" />
          <rect x={x + 1} y={y - half} width={3} height={8} fill="currentColor" />
        </>
      )}
    </g>
  );
}

/** Stand-alone node for legends and lists. */
export function NarratorNode({ kind, title, size = 14, ...props }: MarkProps & { kind: NarratorNodeKind }) {
  return (
    <MarkSvg viewBox="0 0 14 14" title={title ?? NARRATOR_NODE_LABEL[kind]} size={size} {...props}>
      <NarratorNodeShape kind={kind} x={7} y={7} />
    </MarkSvg>
  );
}
