'use client';

import { useMemo } from 'react';
import Link from 'next/link';

interface ChainNode {
    id: string;
    name_arabic?: string | null;
    name_english?: string | null;
    reliability?: string | null;
    tabaqah?: string;
    death_year_hijri?: number;
    is_prophet?: boolean;
    /** Position as recorded on the chain inclusion, when the graph has it. */
    chain_position?: number | null;
    chain_id?: string | null;
    chain_index?: number | null;
    chain_schema?: 'v2' | 'legacy';
}

interface ChainEdge {
    source: string;
    target: string;
    status?: string | null;
    chain_id?: string | null;
}

interface IsnadChainProps {
    nodes: ChainNode[];
    edges: ChainEdge[];
    sourceSanadText?: string | null;
}

const RELIABILITY_STYLE: Record<string, { bg: string; text: string; border: string; label: string }> = {
    THIQA: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/30', label: 'Trustworthy' },
    SADUQ: { bg: 'bg-yellow-500/10', text: 'text-yellow-400', border: 'border-yellow-500/30', label: 'Truthful' },
    DAIF: { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/30', label: 'Weak' },
    KADHAB: { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/30', label: 'Fabricator' },
    MAJHUL: { bg: 'bg-slate-500/10', text: 'text-slate-400', border: 'border-slate-500/30', label: 'Unknown' },
};

const RELIABILITY_DOT: Record<string, string> = {
    THIQA: 'bg-emerald-400',
    SADUQ: 'bg-yellow-400',
    DAIF: 'bg-red-400',
    KADHAB: 'bg-red-400',
    MAJHUL: 'bg-slate-400',
};

function buildOrderedChain(nodes: ChainNode[], edges: ChainEdge[]): ChainNode[] {
    if (nodes.length === 0) return [];

    // Prefer source-backed inclusion positions to inferred edge traversal.
    if (nodes.every((node) => Number.isFinite(node.chain_position))) {
        return [...nodes].sort((a, b) => (a.chain_position ?? 0) - (b.chain_position ?? 0));
    }
    if (edges.length === 0) return nodes;

    // HEARD_FROM: source (student) → target (teacher)
    // We want to display: student → teacher → ... → Prophet
    const adj = new Map<string, string>();
    for (const e of edges) {
        adj.set(e.source, e.target);
    }

    // Find leaf node: appears as source but not as target (latest narrator)
    const targetSet = new Set(edges.map((e) => e.target));
    const starts = nodes.filter((n) => !targetSet.has(n.id) && adj.has(n.id));

    // If no clear start, try any node that has an outgoing edge
    const start = starts[0] || nodes.find((n) => adj.has(n.id)) || nodes[0];

    const chain: ChainNode[] = [];
    const visited = new Set<string>();
    let current: ChainNode | undefined = start;

    while (current && !visited.has(current.id)) {
        visited.add(current.id);
        chain.push(current);
        const nextId = adj.get(current.id);
        current = nextId ? nodes.find((n) => n.id === nextId) : undefined;
    }

    // Add any nodes not in the chain (disconnected)
    for (const n of nodes) {
        if (!visited.has(n.id)) chain.push(n);
    }

    return chain;
}

function hasNarratorIdentity(node: ChainNode): boolean {
    return Boolean(node.name_arabic?.trim() || node.name_english?.trim());
}

function buildChainBranches(nodes: ChainNode[], edges: ChainEdge[]) {
    const grouped = new Map<string, { chainIndex: number | null; nodes: ChainNode[]; edges: ChainEdge[] }>();
    for (const node of nodes) {
        const chainId = node.chain_id || 'linked-chain';
        const branch = grouped.get(chainId) ?? { chainIndex: node.chain_index ?? null, nodes: [], edges: [] };
        branch.nodes.push(node);
        grouped.set(chainId, branch);
    }
    for (const edge of edges) {
        const chainId = edge.chain_id || 'linked-chain';
        const branch = grouped.get(chainId);
        if (branch) branch.edges.push(edge);
    }
    return [...grouped.entries()]
        .map(([id, branch]) => ({
            id,
            chainIndex: branch.chainIndex,
            nodes: buildOrderedChain(branch.nodes, branch.edges).filter(hasNarratorIdentity),
            ordered: branch.nodes.every((node) => Number.isFinite(node.chain_position)) ||
                (branch.nodes.every((node) => node.chain_schema !== 'legacy') && branch.edges.length > 0),
        }))
        .filter((branch) => branch.nodes.length > 0)
        .sort((a, b) => (a.chainIndex ?? Number.MAX_SAFE_INTEGER) - (b.chainIndex ?? Number.MAX_SAFE_INTEGER) || a.id.localeCompare(b.id));
}

export function IsnadChain({ nodes, edges, sourceSanadText }: IsnadChainProps) {
    const branches = useMemo(() => buildChainBranches(nodes, edges), [nodes, edges]);
    const sourceSanad = sourceSanadText?.trim() || null;

    if (branches.length === 0 && !sourceSanad) return null;

    return (
        <div className="w-full py-8 px-4">
            <div className="flex flex-col items-center max-w-2xl mx-auto">
                {sourceSanad && (
                    <section className="w-full mb-6" aria-label="Source sanad">
                        <h2 className="mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-300">
                            Sanad
                        </h2>
                        <p
                            className="rounded-lg border border-slate-700/60 bg-slate-900/60 px-5 py-4 text-lg font-arabic text-amber-50/90"
                            dir="rtl"
                            lang="ar"
                        >
                            {sourceSanad}
                        </p>
                    </section>
                )}

                {branches.map((branch, branchIndex) => (
                    <section
                        key={branch.id}
                        className="mb-6 w-full max-w-lg"
                        aria-label={branches.length > 1 ? `Chain ${branchIndex + 1}` : 'Narrator chain'}
                    >
                        {(branches.length > 1 || !branch.ordered) && (
                            <h3 className="mb-3 text-xs font-semibold uppercase tracking-[0.14em] text-slate-300">
                                {branches.length > 1 ? `Chain ${branchIndex + 1}` : 'Narrators'}
                                {!branch.ordered && <span className="ml-2 normal-case tracking-normal text-slate-400">order not recorded</span>}
                            </h3>
                        )}
                        {branch.nodes.map((narrator, i) => {
                            // Only render a verdict the data actually carries.
                            const rel = narrator.reliability ? RELIABILITY_STYLE[narrator.reliability] : undefined;
                            const dot = narrator.reliability ? RELIABILITY_DOT[narrator.reliability] : undefined;
                            const isProphet = narrator.is_prophet || narrator.tabaqah === 'PROPHET';
                            const narratorName = narrator.name_english || narrator.name_arabic || 'narrator';

                            return (
                                <div key={`${branch.id}:${narrator.id}:${narrator.chain_position ?? i}`} className="flex flex-col items-center w-full">
                                    <Link
                                        href={`/narrator/${narrator.id}`}
                                        aria-label={`Open narrator profile for ${narratorName}`}
                                        className={`relative w-full rounded-md border px-5 py-4 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950 ${isProphet
                                            ? 'border-amber-500/40 bg-amber-500/5 hover:border-amber-400/60'
                                            : 'border-slate-700/50 bg-slate-900/40 hover:border-slate-600/70'
                                        }`}
                                    >
                                        {isProphet && (
                                            <div className="absolute -top-2.5 left-4 bg-amber-500/20 border border-amber-500/30 rounded-full px-3 py-0.5 text-[10px] font-semibold text-amber-400 uppercase tracking-wider">
                                                Prophet
                                            </div>
                                        )}
                                        <div className="flex items-center justify-between gap-4">
                                            <div className="flex-1 min-w-0">
                                                {narrator.name_arabic && (
                                                    <p className="text-lg font-semibold text-slate-100 font-arabic" dir="rtl" lang="ar">
                                                        {narrator.name_arabic}
                                                    </p>
                                                )}
                                                {narrator.name_english && (
                                                    <p className="text-sm text-slate-400 mt-0.5">{narrator.name_english}</p>
                                                )}
                                                {narrator.death_year_hijri != null && (
                                                    <p className="text-xs text-slate-400 mt-0.5">d. {narrator.death_year_hijri} AH</p>
                                                )}
                                            </div>
                                            {rel && dot && (
                                                <div className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium border ${rel.bg} ${rel.text} ${rel.border} shrink-0`}>
                                                    <span className={`w-1.5 h-1.5 rounded-full ${dot}`} aria-hidden="true" />
                                                    {rel.label}
                                                </div>
                                            )}
                                        </div>
                                    </Link>

                                    {branch.ordered && i < branch.nodes.length - 1 && (
                                        <div className="flex flex-col items-center py-1" aria-hidden="true">
                                            <div className="w-px h-6 bg-slate-600" />
                                            <svg width="12" height="8" viewBox="0 0 12 8" className="text-slate-400 -mt-px">
                                                <path d="M1 1l5 5.5L11 1" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
                                            </svg>
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </section>
                ))}
            </div>
        </div>
    );
}
