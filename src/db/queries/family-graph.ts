/**
 * Combined transmission graph of a report family: pure, deterministic, safe for client components.
 * Merge rule, layout and the shared-only view: src/db/queries/AGENTS.md §Report families.
 */
import type { ChainNode, FamilyTelling, HadithTraditionCode } from './contracts';

export type FamilyGraphNodeKind = 'identity' | 'mention' | 'work';

export interface FamilyGraphNode {
  key: string;
  kind: FamilyGraphNodeKind;
  /** The name as written (first occurrence for an identity node). */
  label_ar: string | null;
  /** The identity's English name, or the work's title. */
  label_en: string | null;
  narrator_id: string | null;
  /** Every chain passing through the node; more than one only for an identity or a work node. */
  chain_ids: string[];
  traditions: HadithTraditionCode[];
  /** Work nodes: how many tellings of the family the work holds. */
  tellings: number;
  layer: number;
  order: number;
  x: number;
  y: number;
}

export interface FamilyGraphEdge {
  key: string;
  source: string;
  target: string;
  tradition: HadithTraditionCode;
  chain_ids: string[];
  /** Shared-only view: the most names any of these chains has between the two ends (left out of the drawing). */
  folded: number;
}

export interface FamilyGraphChain {
  chain_id: string;
  hadith_id: string;
  tradition: HadithTraditionCode;
  source_work: string;
  /** Node keys from the top (the report's originator) down to the work. */
  path: string[];
}

export interface FamilyGraph {
  nodes: FamilyGraphNode[];
  edges: FamilyGraphEdge[];
  chains: FamilyGraphChain[];
  /** Identity nodes that more than one chain passes through. */
  convergences: number;
  /** Shared-only view: chains with no narrator in common with another chain (drawn only as their work). */
  chainsWithoutSharedNarrator: number;
  layers: number;
}

export const LAYER_HEIGHT = 96;
export const COLUMN_WIDTH = 168;

/**
 * Merge key of a written name. Only a standing identity (`is_link`, the chain_mentions.narrator_id the pipeline or a
 * reviewer set) merges, and only within one tradition (owner, 2026-11-21: identities are never merged across traditions
 * automatically; since 0010 one external record can stand in two traditions). Every other name stays one node per
 * mention, even when the text is identical.
 */
export function mergeKey(node: ChainNode, tradition?: HadithTraditionCode): string {
  return node.is_link && node.narrator_id ? `narrator:${tradition ?? ''}:${node.narrator_id}` : `mention:${node.node_id}`;
}

interface Draft {
  key: string;
  kind: FamilyGraphNodeKind;
  label_ar: string | null;
  label_en: string | null;
  narrator_id: string | null;
  chain_ids: Set<string>;
  traditions: Set<HadithTraditionCode>;
  tellings: Set<string>;
}

function chainsOf(telling: FamilyTelling): ChainNode[][] {
  const grouped = new Map<string, ChainNode[]>();
  for (const node of telling.chain.nodes) grouped.set(node.chain_id, [...(grouped.get(node.chain_id) ?? []), node]);
  return [...grouped.values()]
    .map((nodes) => [...nodes].sort((left, right) => right.position - left.position)) // top (originator) first
    .sort((left, right) => left[0].branch - right[0].branch);
}

/**
 * Builds the merged graph. Works are pooled, one node each, on the bottom layer. `sharedOnly` keeps only identities
 * that several chains pass through: the convergence view that stays readable for dozens of chains. Names it leaves
 * out are counted on the edge (`folded`), and every name stays in the ordered lists.
 */
export function buildFamilyGraph(tellings: FamilyTelling[], options: { sharedOnly?: boolean } = {}): FamilyGraph {
  const drafts = new Map<string, Draft>();
  const chains: FamilyGraphChain[] = [];
  const folds = new Map<string, number>(); // `${chain}|${from}|${to}` -> names left out between the two
  const touch = (key: string, init: Omit<Draft, 'chain_ids' | 'traditions' | 'tellings'>, chainId: string | null, telling: FamilyTelling) => {
    const draft = drafts.get(key) ?? { ...init, chain_ids: new Set<string>(), traditions: new Set<HadithTraditionCode>(), tellings: new Set<string>() };
    if (chainId) draft.chain_ids.add(chainId);
    draft.traditions.add(telling.tradition);
    draft.tellings.add(telling.hadith_id);
    drafts.set(key, draft);
  };

  // Which identities several chains pass through (the shared-only view keeps just these).
  const chainsPerIdentity = new Map<string, Set<string>>();
  for (const telling of tellings) {
    for (const chain of chainsOf(telling)) {
      for (const node of chain) {
        const key = mergeKey(node, telling.tradition);
        if (key.startsWith('narrator:')) chainsPerIdentity.set(key, (chainsPerIdentity.get(key) ?? new Set()).add(node.chain_id));
      }
    }
  }
  const shared = (key: string) => (chainsPerIdentity.get(key)?.size ?? 0) > 1;

  let chainsWithoutSharedNarrator = 0;
  for (const telling of tellings) {
    const workKey = `work:${telling.collection_id}`;
    const workInit = { key: workKey, kind: 'work' as const, label_ar: null, label_en: telling.source_work, narrator_id: null };
    touch(workKey, workInit, null, telling); // a telling with no extracted chain still shows its work
    for (const chain of chainsOf(telling)) {
      const chainId = chain[0].chain_id;
      const path: string[] = [];
      let skipped = 0;
      for (const node of chain) {
        const key = mergeKey(node, telling.tradition);
        if (options.sharedOnly && !shared(key)) {
          skipped++;
          continue;
        }
        if (path.length) folds.set(`${chainId}|${path[path.length - 1]}|${key}`, skipped);
        skipped = 0;
        touch(key, { key, kind: node.is_link ? 'identity' : 'mention', label_ar: node.surface_ar, label_en: node.name_en, narrator_id: node.narrator_id }, chainId, telling);
        path.push(key);
      }
      if (options.sharedOnly && path.length === 0) chainsWithoutSharedNarrator++;
      if (path.length) folds.set(`${chainId}|${path[path.length - 1]}|${workKey}`, skipped);
      touch(workKey, workInit, chainId, telling);
      path.push(workKey);
      chains.push({ chain_id: chainId, hadith_id: telling.hadith_id, tradition: telling.tradition, source_work: telling.source_work, path });
    }
  }

  // Edges: one per (teacher, student, tradition), listing the chains that use it.
  const edgeMap = new Map<string, FamilyGraphEdge>();
  for (const chain of chains) {
    for (let index = 0; index + 1 < chain.path.length; index++) {
      const source = chain.path[index];
      const target = chain.path[index + 1];
      if (source === target) continue;
      const key = `${source}->${target}#${chain.tradition}`;
      const edge = edgeMap.get(key) ?? { key, source, target, tradition: chain.tradition, chain_ids: [], folded: 0 };
      if (!edge.chain_ids.includes(chain.chain_id)) edge.chain_ids.push(chain.chain_id);
      edge.folded = Math.max(edge.folded, folds.get(`${chain.chain_id}|${source}|${target}`) ?? 0);
      edgeMap.set(key, edge);
    }
  }
  const edges = [...edgeMap.values()].sort((left, right) => (left.key < right.key ? -1 : left.key > right.key ? 1 : 0));

  const layerOf = assignLayers([...drafts.keys()], edges, chains);
  const orderOf = orderWithinLayers(layerOf, edges, chains);
  const layerWidths = new Map<number, number>();
  for (const [key, layer] of layerOf) layerWidths.set(layer, Math.max(layerWidths.get(layer) ?? 0, (orderOf.get(key) ?? 0) + 1));

  const nodes: FamilyGraphNode[] = [...drafts.values()]
    .map((draft) => {
      const layer = layerOf.get(draft.key) ?? 0;
      const order = orderOf.get(draft.key) ?? 0;
      const width = layerWidths.get(layer) ?? 1;
      return {
        key: draft.key,
        kind: draft.kind,
        label_ar: draft.label_ar,
        label_en: draft.label_en,
        narrator_id: draft.narrator_id,
        chain_ids: [...draft.chain_ids].sort(),
        traditions: [...draft.traditions].sort(),
        tellings: draft.kind === 'work' ? draft.tellings.size : 0,
        layer,
        order,
        x: (order - (width - 1) / 2) * COLUMN_WIDTH,
        y: layer * LAYER_HEIGHT,
      };
    })
    .sort((left, right) => left.layer - right.layer || left.order - right.order);

  return {
    nodes,
    edges,
    chains,
    convergences: nodes.filter((node) => node.kind === 'identity' && node.chain_ids.length > 1).length,
    chainsWithoutSharedNarrator,
    layers: Math.max(0, ...nodes.map((node) => node.layer)) + 1,
  };
}

/**
 * Longest-path layering from the top (Kahn's algorithm): a node sits one layer below its lowest teacher, so every edge
 * points down. Work nodes are pinned to the bottom layer. Nodes on a cycle (a narrator merged at two depths) take the
 * layer after their deepest placed teacher.
 */
function assignLayers(keys: string[], edges: FamilyGraphEdge[], chains: FamilyGraphChain[]): Map<string, number> {
  const incoming = new Map<string, number>(keys.map((key) => [key, 0]));
  const outgoing = new Map<string, string[]>();
  const pairs = new Set<string>();
  for (const edge of edges) {
    const pair = `${edge.source}->${edge.target}`;
    if (pairs.has(pair)) continue;
    pairs.add(pair);
    incoming.set(edge.target, (incoming.get(edge.target) ?? 0) + 1);
    outgoing.set(edge.source, [...(outgoing.get(edge.source) ?? []), edge.target]);
  }
  const layer = new Map<string, number>();
  const queue = keys.filter((key) => (incoming.get(key) ?? 0) === 0).sort();
  for (const key of queue) layer.set(key, 0);
  for (let head = 0; head < queue.length; head++) {
    const key = queue[head];
    for (const next of outgoing.get(key) ?? []) {
      layer.set(next, Math.max(layer.get(next) ?? 0, (layer.get(key) ?? 0) + 1));
      const remaining = (incoming.get(next) ?? 0) - 1;
      incoming.set(next, remaining);
      if (remaining === 0) queue.push(next);
    }
  }
  // Cycle members: place along their chains, after the deepest node already placed above them.
  for (const chain of chains) {
    chain.path.forEach((key, index) => {
      if (layer.has(key)) return;
      const above = index > 0 ? (layer.get(chain.path[index - 1]) ?? index - 1) : -1;
      layer.set(key, above + 1);
    });
  }
  for (const key of keys) if (!layer.has(key)) layer.set(key, 0);
  const bottom = Math.max(0, ...[...layer.entries()].filter(([key]) => !key.startsWith('work:')).map(([, value]) => value)) + 1;
  for (const key of keys) if (key.startsWith('work:')) layer.set(key, bottom);
  return layer;
}

/** Barycentre ordering (Sugiyama): seeded by chain order, then four sweeps; ties broken by key so output is stable. */
function orderWithinLayers(layerOf: Map<string, number>, edges: FamilyGraphEdge[], chains: FamilyGraphChain[]): Map<string, number> {
  const layers = new Map<number, string[]>();
  const firstSeen = new Map<string, number>();
  chains.forEach((chain, chainIndex) => chain.path.forEach((key) => { if (!firstSeen.has(key)) firstSeen.set(key, chainIndex); }));
  for (const [key, layer] of layerOf) layers.set(layer, [...(layers.get(layer) ?? []), key]);
  const order = new Map<string, number>();
  const tieBreak = (left: string, right: string) => (left < right ? -1 : left > right ? 1 : 0);
  for (const keys of layers.values()) {
    keys.sort((left, right) => (firstSeen.get(left) ?? 1e9) - (firstSeen.get(right) ?? 1e9) || tieBreak(left, right));
    keys.forEach((key, index) => order.set(key, index));
  }
  const above = new Map<string, string[]>();
  const below = new Map<string, string[]>();
  for (const edge of edges) {
    above.set(edge.target, [...(above.get(edge.target) ?? []), edge.source]);
    below.set(edge.source, [...(below.get(edge.source) ?? []), edge.target]);
  }
  const layerNumbers = [...layers.keys()].sort((left, right) => left - right);
  for (let sweep = 0; sweep < 4; sweep++) {
    const downward = sweep % 2 === 0;
    for (const layer of downward ? layerNumbers : [...layerNumbers].reverse()) {
      const keys = layers.get(layer)!;
      const neighbours = downward ? above : below;
      const centre = new Map(
        keys.map((key) => {
          const linked = neighbours.get(key) ?? [];
          return [key, linked.length ? linked.reduce((sum, other) => sum + (order.get(other) ?? 0), 0) / linked.length : (order.get(key) ?? 0)];
        }),
      );
      keys.sort((left, right) => centre.get(left)! - centre.get(right)! || (order.get(left) ?? 0) - (order.get(right) ?? 0) || tieBreak(left, right));
      keys.forEach((key, index) => order.set(key, index));
    }
  }
  return order;
}

export interface FamilySummary {
  tellings: number;
  works: number;
  traditions: HadithTraditionCode[];
  chains: number;
  names: number;
  /** Names with a standing identity (machine-reviewed source-and-text match, or a reviewer's decision). */
  identified: number;
  /** Names shown as written that carry at least one suggested match. */
  suggested: number;
}

/** Counts for the summary line above a family. */
export function familySummary(tellings: FamilyTelling[]): FamilySummary {
  const chains = new Set<string>();
  let names = 0;
  let identified = 0;
  let suggested = 0;
  for (const telling of tellings) {
    for (const node of telling.chain.nodes) {
      chains.add(node.chain_id);
      names += 1;
      if (node.is_link) identified += 1;
      else if (node.candidates.length > 0) suggested += 1;
    }
  }
  return {
    tellings: tellings.length,
    works: new Set(tellings.map((telling) => telling.collection_id)).size,
    traditions: [...new Set(tellings.map((telling) => telling.tradition))].sort(),
    chains: chains.size,
    names,
    identified,
    suggested,
  };
}
