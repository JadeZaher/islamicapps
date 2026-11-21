export const dynamic = 'force-dynamic';

import { notFound } from 'next/navigation';
import type { Metadata } from 'next';
import { getPublicParallelsForHadith } from '@/db/queries/comparative';
import type { ChainGraph, HadithDetail } from '@/db/queries/contracts';
import { getChainGraph } from '@/db/queries/isnad';
import { HadithClientPage } from './client-page';
import { loadHadith } from './data';
import type { GraphEdge, GraphNode, HadithNode, ParallelRecord } from './types';

interface PageProps {
    params: Promise<{
        id: string;
    }>;
}

/** Adapts the section 9.4 detail contract to the client's HadithNode keys. No grade is defaulted. */
function toHadithNode(hadith: HadithDetail): HadithNode {
    return {
        ...hadith,
        display_grade: null,
        auto_calculated_grade: null,
        transmission_type: null,
        hadith_id: hadith.record_id,
        variations: hadith.variations,
        assessments: hadith.assessments,
    };
}

/**
 * Adapts mention-keyed chain nodes to the client's GraphNode keys. Every position is kept, so the isnad reads
 * as written; an unidentified position shows its surface and carries no narrator identity.
 */
function toGraph(graph: ChainGraph): { nodes: GraphNode[]; edges: GraphEdge[] } {
    const clientId = new Map(graph.nodes.map((node) => [node.node_id, node.is_link && node.narrator_id ? node.narrator_id : node.node_id]));
    const nodes: GraphNode[] = graph.nodes.map((node) => ({
        ...node,
        id: clientId.get(node.node_id)!,
        name_arabic: node.is_link ? node.name_ar ?? node.surface_ar : node.surface_ar,
        name_english: node.is_link ? node.name_en ?? undefined : undefined,
        chain_id: node.chain_id,
        chain_index: node.branch,
        position: node.position,
        chain_position: node.position,
        chain_schema: 'v2',
    }));
    const edges: GraphEdge[] = graph.edges.map((edge) => ({
        source: clientId.get(edge.source)!,
        target: clientId.get(edge.target)!,
        chain_id: edge.chain_id,
        chain_schema: 'v2',
    }));
    return { nodes, edges };
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
    const { id } = await params;
    const hadith = await loadHadith(id).catch(() => null);
    if (!hadith) return { title: 'Hadith not found' };
    const reference = [hadith.source, hadith.hadith_no].filter(Boolean).join(' ');
    return { title: hadith.title?.trim() || reference || 'Hadith' };
}

export default async function HadithPage({ params }: PageProps) {
    const rawId = (await params).id;
    const id = decodeURIComponent(rawId);

    const [hadith, graph, parallels] = await Promise.all([
        loadHadith(rawId),
        getChainGraph(id).catch((err) => {
            console.error('Error fetching chain graph:', err);
            return null;
        }),
        getPublicParallelsForHadith(id).catch(() => []),
    ]);

    if (!hadith) notFound();
    const { nodes, edges } = graph ? toGraph(graph) : { nodes: [], edges: [] };

    return (
        <HadithClientPage
            hadith={toHadithNode(hadith)}
            nodes={nodes}
            edges={edges}
            parallels={parallels as unknown as ParallelRecord[]}
        />
    );
}
