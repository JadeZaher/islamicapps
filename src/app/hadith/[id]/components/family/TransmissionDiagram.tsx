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
  dimmed: boolean;
}

/** Flat geometry: a filled square for a standing identity (larger where chains converge), a hollow circle for a name
 * as written, a rule under a work. */
const NarratorNode = memo(function NarratorNode({ data }: NodeProps<Node<NarratorData>>) {
  const node = data.graphNode;
  const converging = node.kind === 'identity' && node.chain_ids.length > 1;
  const markerSize = converging ? 12 : 8;
  return (
    <div
      style={{ width: COLUMN_WIDTH - 24, opacity: data.dimmed ? 'var(--family-dim)' : 1 }}
      className="flex flex-col items-center text-center"
      title={[node.label_ar, node.label_en, node.chain_ids.length > 1 ? `${node.chain_ids.length} chains pass through` : null].filter(Boolean).join(' · ')}
    >
      <Handle type="target" position={Position.Top} style={{ opacity: 0, top: 0 }} isConnectable={false} />
      {node.kind === 'work' ? (
        <span aria-hidden="true" style={{ display: 'block', width: 40, height: 2, background: 'var(--family-ink)' }} />
      ) : (
        <svg aria-hidden="true" width={markerSize} height={markerSize} viewBox={`0 0 ${markerSize} ${markerSize}`}>
          {node.kind === 'identity' ? (
            <rect width={markerSize} height={markerSize} fill={converging ? 'var(--family-accent)' : 'var(--family-ink)'} />
          ) : (
            <circle cx={markerSize / 2} cy={markerSize / 2} r={markerSize / 2 - 1} fill="var(--family-paper)" stroke="var(--family-ink)" strokeWidth="1" />
          )}
        </svg>
      )}
      <div className="mt-1 leading-tight">
        {node.kind === 'work' ? (
          <span style={{ fontSize: 11, color: 'var(--family-ink)' }}>
            {node.label_en}
            {node.tellings > 1 && <span style={{ color: 'var(--family-ink-tertiary)' }}> · {node.tellings}</span>}
          </span>
        ) : (
          <ArabicText style={{ fontSize: 14, lineHeight: 1.5, color: 'var(--family-ink)' }} className="line-clamp-2">
            {node.label_ar}
          </ArabicText>
        )}
        {converging && <div style={{ fontSize: 10, color: 'var(--family-ink-tertiary)' }}>{node.chain_ids.length} chains</div>}
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
        data: { graphNode: node, dimmed: litChains !== null && !node.chain_ids.some((id) => litChains.has(id)) },
        draggable: false,
        selectable: false,
        connectable: false,
      })),
    [graph, litChains],
  );
  const edges: Edge[] = useMemo(
    () =>
      graph.edges.map((edge) => {
        const lit = litChains === null || edge.chain_ids.some((id) => litChains.has(id));
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
            stroke: 'var(--family-ink)',
            strokeWidth: edge.chain_ids.length > 1 ? 1.75 : 1,
            strokeDasharray: TRADITION_DASH[edge.tradition].dash,
            strokeLinecap: 'round',
            opacity: lit ? 0.9 : 'var(--family-dim)',
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
          colorMode="dark"
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
          <svg aria-hidden="true" width="10" height="10" className="mr-1 inline align-middle"><rect width="10" height="10" fill="var(--family-ink)" /></svg>
          Identified narrator, drawn once
        </span>
        <span>
          <svg aria-hidden="true" width="10" height="10" className="mr-1 inline align-middle"><rect width="10" height="10" fill="var(--family-accent)" /></svg>
          Several chains pass through ({graph.convergences})
        </span>
        <span>
          <svg aria-hidden="true" width="10" height="10" className="mr-1 inline align-middle"><circle cx="5" cy="5" r="4" fill="none" stroke="var(--family-ink)" /></svg>
          Name as written, one per chain
        </span>
        {traditions.map((tradition) => (
          <span key={tradition}>
            <TraditionMark tradition={tradition} />
            {tradition} ({TRADITION_DASH[tradition].name})
          </span>
        ))}
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
