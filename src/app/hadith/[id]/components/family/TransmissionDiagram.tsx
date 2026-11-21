'use client';

import { memo, useMemo, useState } from 'react';
import {
  Handle,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { ArabicText } from '@/components/ArabicText';
import { NarratorNode as NodeMark, NarratorNodeShape, type NarratorNodeKind } from '@/components/marks';
import type { FamilyTelling, HadithTraditionCode } from '@/db/queries/contracts';
import { buildFamilyGraph, COLUMN_WIDTH, LAYER_HEIGHT, type FamilyGraphNode } from '@/db/queries/family-graph';
import styles from './family.module.css';
import { tellingReference, TRADITION_DASH, TRADITION_ORDER } from './labels';
import { TraditionMark } from './TellingsList';

/** Above this many chains the diagram opens on shared narrators only (the convergence view). */
const SHARED_ONLY_FROM_CHAINS = 12;
/** The opening view never shrinks names below this zoom; Fit still shows the whole graph. */
const READABLE_ZOOM = 0.55;

type Highlight = { kind: 'tradition'; value: HadithTraditionCode } | { kind: 'chain'; value: string } | { kind: 'node'; value: string } | null;

interface NarratorData extends Record<string, unknown> {
  graphNode: FamilyGraphNode;
  /** On a highlighted chain, or the clicked node: drawn on an accent-wash square with an accent frame. */
  selected: boolean;
}

/** Node shapes of DESIGN.md §Transmission graph: identified = filled square, shared by several chains = framed. */
function nodeKind(node: FamilyGraphNode): NarratorNodeKind {
  if (node.kind !== 'identity') return 'unidentified';
  return node.chain_ids.length > 1 ? 'shared' : 'identified';
}

/** Flat geometry: squares for names (filled when identified, framed where chains converge), an ink rule under a work.
 * Selection is an accent-wash square with a 2px accent frame; nothing fades, glows or scales. */
const NarratorNode = memo(function NarratorNode({ data }: NodeProps<Node<NarratorData>>) {
  const node = data.graphNode;
  const converging = node.kind === 'identity' && node.chain_ids.length > 1;
  return (
    <div
      style={{ width: COLUMN_WIDTH - 24 }}
      className="flex flex-col items-center text-center"
      title={[node.label_ar, node.label_en, node.chain_ids.length > 1 ? `${node.chain_ids.length} chains pass through` : null].filter(Boolean).join(' · ')}
    >
      <Handle type="target" position={Position.Top} style={{ opacity: 0, top: 0 }} isConnectable={false} />
      {node.kind === 'work' ? (
        <span aria-hidden="true" style={{ display: 'block', width: 40, height: 2, background: data.selected ? 'var(--family-accent)' : 'var(--family-ink)' }} />
      ) : (
        <svg aria-hidden="true" width={20} height={20} viewBox="0 0 20 20" style={{ color: 'var(--family-ink)', overflow: 'visible' }}>
          <NarratorNodeShape kind={nodeKind(node)} x={10} y={10} selected={data.selected} />
        </svg>
      )}
      <div className="mt-1 leading-tight">
        {node.kind === 'work' ? (
          <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.02em', color: 'var(--family-ink)' }}>
            {node.label_en}
            {node.tellings > 1 && <span style={{ color: 'var(--family-ink-tertiary)' }}> · {node.tellings}</span>}
          </span>
        ) : (
          <ArabicText style={{ fontSize: 15, lineHeight: 1.6, color: 'var(--family-ink)' }} className="line-clamp-2">
            {node.label_ar}
          </ArabicText>
        )}
        {converging && <div style={{ fontSize: 11, color: 'var(--family-ink-tertiary)' }}>{node.chain_ids.length} chains</div>}
      </div>
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0, bottom: 0 }} isConnectable={false} />
    </div>
  );
});

const NODE_TYPES = { narrator: NarratorNode };

function ZoomControls() {
  const flow = useReactFlow();
  return (
    <>
      <button type="button" className={styles.button} onClick={() => flow.zoomIn()} aria-label="Zoom in">+</button>
      <button type="button" className={styles.button} onClick={() => flow.zoomOut()} aria-label="Zoom out">−</button>
      <button type="button" className={styles.button} onClick={() => flow.fitView({ padding: 0.1, minZoom: 0.05 })}>Fit</button>
    </>
  );
}

interface TransmissionDiagramProps {
  tellings: FamilyTelling[];
  /** Id of the "All chains" section, the accessible equivalent of this diagram. */
  listsId: string;
}

/**
 * One graph of every chain in the family, originator at the top, works at the bottom. Names merge only on a standing
 * identity (src/db/queries/family-graph.ts). Visual only: the ordered lists under "All chains" carry the same content.
 */
function Diagram({ tellings, listsId }: TransmissionDiagramProps) {
  const chainCount = useMemo(() => new Set(tellings.flatMap((telling) => telling.chain.nodes.map((node) => node.chain_id))).size, [tellings]);
  const [sharedOnly, setSharedOnly] = useState(chainCount > SHARED_ONLY_FROM_CHAINS);
  const [highlight, setHighlight] = useState<Highlight>(null);
  const graph = useMemo(() => buildFamilyGraph(tellings, { sharedOnly }), [tellings, sharedOnly]);
  const traditions = TRADITION_ORDER.filter((tradition) => graph.chains.some((chain) => chain.tradition === tradition));
  const referenceOf = useMemo(() => new Map(tellings.map((telling) => [telling.hadith_id, tellingReference(telling)])), [tellings]);

  const litChains = useMemo(() => {
    if (!highlight) return null;
    if (highlight.kind === 'chain') return new Set([highlight.value]);
    if (highlight.kind === 'tradition') return new Set(graph.chains.filter((chain) => chain.tradition === highlight.value).map((chain) => chain.chain_id));
    return new Set(graph.nodes.find((node) => node.key === highlight.value)?.chain_ids ?? []);
  }, [highlight, graph]);

  const nodes: Node<NarratorData>[] = useMemo(
    () =>
      graph.nodes.map((node) => ({
        id: node.key,
        type: 'narrator',
        position: { x: node.x, y: node.y },
        data: {
          graphNode: node,
          selected: highlight?.kind === 'node' ? highlight.value === node.key : litChains !== null && node.chain_ids.some((id) => litChains.has(id)),
        },
        draggable: false,
        selectable: false,
        connectable: false,
      })),
    [graph, litChains, highlight],
  );
  const edges: Edge[] = useMemo(
    () =>
      graph.edges.map((edge) => {
        // Selected chains draw in 2px accent; every other edge stays a faint hairline in its tradition's pattern.
        const lit = litChains !== null && edge.chain_ids.some((id) => litChains.has(id));
        return {
          id: edge.key,
          source: edge.source,
          target: edge.target,
          type: 'straight',
          selectable: false,
          focusable: false,
          ...(edge.folded > 0
            ? {
                label: `+${edge.folded}`,
                labelStyle: { fill: 'var(--family-ink-tertiary)', fontSize: 10 },
                labelBgStyle: { fill: 'var(--family-paper)' },
                labelBgPadding: [2, 1] as [number, number],
              }
            : {}),
          style: {
            stroke: lit ? 'var(--family-accent)' : 'var(--family-faint)',
            strokeWidth: lit ? 2 : edge.chain_ids.length > 1 ? 1.75 : 1,
            strokeDasharray: lit ? undefined : TRADITION_DASH[edge.tradition].dash,
            strokeLinecap: 'butt',
          },
        };
      }),
    [graph, litChains],
  );

  const toggle = (next: NonNullable<Highlight>) =>
    setHighlight((current) => (current && current.kind === next.kind && current.value === next.value ? null : next));

  return (
    <figure aria-labelledby="diagram-caption">
      <div className={styles.controls}>
        {traditions.map((tradition) => (
          <button
            key={tradition}
            type="button"
            className={styles.button}
            aria-pressed={highlight?.kind === 'tradition' && highlight.value === tradition}
            onClick={() => toggle({ kind: 'tradition', value: tradition })}
          >
            <TraditionMark tradition={tradition} />
            {tradition}
          </button>
        ))}
        <label className="sr-only" htmlFor="diagram-chain">Highlight one chain</label>
        <select
          id="diagram-chain"
          className={styles.select}
          value={highlight?.kind === 'chain' ? highlight.value : ''}
          onChange={(event) => setHighlight(event.target.value ? { kind: 'chain', value: event.target.value } : null)}
        >
          <option value="">Highlight one chain…</option>
          {graph.chains.map((chain, index) => (
            <option key={chain.chain_id} value={chain.chain_id}>
              {referenceOf.get(chain.hadith_id)} · chain {index + 1}
            </option>
          ))}
        </select>
        <button type="button" className={styles.button} aria-pressed={sharedOnly} onClick={() => setSharedOnly((value) => !value)}>
          Shared narrators only
        </button>
        {highlight && (
          <button type="button" className={styles.button} onClick={() => setHighlight(null)}>Clear</button>
        )}
        <ZoomControls />
      </div>
      {/* Visual only; the ordered lists under "All chains" are the accessible equivalent. */}
      <div className={styles.canvas} style={{ height: `min(78vh, ${Math.max(320, graph.layers * LAYER_HEIGHT + 120)}px)` }} aria-hidden="true">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={NODE_TYPES}
          fitView
          fitViewOptions={{ padding: 0.1, minZoom: READABLE_ZOOM }}
          minZoom={0.05}
          maxZoom={2}
          // Fixed so server and client agree; the tokens (light-dark) carry the theme, and only <html> classes force one.
          colorMode="light"
          nodesDraggable={false}
          nodesConnectable={false}
          nodesFocusable={false}
          edgesFocusable={false}
          elementsSelectable={false}
          disableKeyboardA11y
          onNodeClick={(_, node) => toggle({ kind: 'node', value: node.id })}
          onPaneClick={() => setHighlight(null)}
          proOptions={{ hideAttribution: true }}
          style={{ background: 'var(--family-paper)' }}
        />
      </div>
      <figcaption id="diagram-caption" className={styles.legend}>
        <span>
          <NodeMark kind="identified" decorative />
          Identified narrator, drawn once
        </span>
        <span>
          <NodeMark kind="shared" decorative />
          Several chains pass through ({graph.convergences})
        </span>
        <span>
          <NodeMark kind="unidentified" decorative />
          Name as written, one per chain
        </span>
        {traditions.map((tradition) => (
          <span key={tradition}>
            <svg aria-hidden="true" width="24" height="8" viewBox="0 0 24 8">
              <line x1="0" y1="4" x2="24" y2="4" stroke="currentColor" strokeWidth="1.5" strokeDasharray={TRADITION_DASH[tradition].dash} />
            </svg>
            <TraditionMark tradition={tradition} />
            {tradition} ({TRADITION_DASH[tradition].name})
          </span>
        ))}
        {highlight && (
          <span>
            <svg aria-hidden="true" width="24" height="8" viewBox="0 0 24 8">
              <line x1="0" y1="4" x2="24" y2="4" stroke="var(--family-accent)" strokeWidth="2" />
            </svg>
            Highlighted chains
          </span>
        )}
        {sharedOnly && (
          <span>
            Names only one chain passes through are left out and counted on the line (+N)
            {graph.chainsWithoutSharedNarrator > 0 && <>; {graph.chainsWithoutSharedNarrator} chains share no narrator with another and show only their work</>}.
          </span>
        )}
        <span>
          Names merge only on an identity the archive holds, never on matching text.{' '}
          <a href={`#${listsId}`} className={styles.link}>Read every chain as an ordered list</a>
        </span>
      </figcaption>
    </figure>
  );
}

export function TransmissionDiagram(props: TransmissionDiagramProps) {
  return (
    <ReactFlowProvider>
      <Diagram {...props} />
    </ReactFlowProvider>
  );
}
