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
    hadithTextArabic?: string | null;
    hadithTextEnglish?: string | null;
    hadithTextLabel?: string;
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

export function IsnadChain({ nodes, edges, hadithTextArabic, hadithTextEnglish, hadithTextLabel = 'Hadith text', sourceSanadText }: IsnadChainProps) {
    const branches = useMemo(() => buildChainBranches(nodes, edges), [nodes, edges]);
    const resolvedChain = branches.flatMap((branch) => branch.nodes);
    const sourceSanad = sourceSanadText?.trim() || null;

    if (resolvedChain.length === 0 && !hadithTextArabic && !hadithTextEnglish && !sourceSanad) {
        return (
            <div className="flex items-center justify-center py-20 text-center text-slate-400 text-sm" role="status">
                No source sanad text or linked narrator identities are available for this hadith.
            </div>
        );
    }

    return (
        <div className="w-full py-10 px-4">
            <div className="flex flex-col items-center max-w-2xl mx-auto">
                {/* Source wording stays visible even when only part of it links to narrator records. */}
                {sourceSanad && (
                    <section className="w-full max-w-2xl mb-6" aria-labelledby="source-sanad-heading">
                        <div className="overflow-hidden rounded-lg border border-cyan-400/30 bg-slate-900/60">
                            <div className="flex items-center justify-between gap-3 border-b border-cyan-400/20 bg-cyan-400/10 px-4 py-2">
                                <h2 id="source-sanad-heading" className="text-[11px] font-semibold uppercase tracking-[0.16em] text-cyan-200">
                                    Source sanad
                                </h2>
                                <span className="text-[10px] text-cyan-100/70">Verbatim source wording</span>
                            </div>
                            <div className="px-5 py-4">
                                <p className="text-base leading-loose text-cyan-50/90 font-[var(--font-amiri)]" dir="auto">
                                    {sourceSanad}
                                </p>
                            </div>
                        </div>
                        <p className="mt-2 text-xs leading-relaxed text-slate-400" role="status">
                            {resolvedChain.length > 0
                                ? 'Linked narrator records below are shown only where the source chain was resolved.'
                                : 'No narrator identities are linked to this source chain yet.'}
                        </p>
                    </section>
                )}

                {/* Chain nodes */}
                {resolvedChain.length > 0 && (
                    <div className="mb-3 w-full max-w-lg border-b border-slate-800 pb-2">
                        <h2 className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-300">
                            Linked narrator identities
                        </h2>
                    </div>
                )}
                {branches.map((branch, branchIndex) => (
                    <section key={branch.id} className="mb-6 w-full max-w-lg border-l-2 border-cyan-400/40 pl-4" aria-labelledby={`chain-${branchIndex}`}>
                        <div className="mb-3 flex items-center justify-between gap-3">
                            <h3 id={`chain-${branchIndex}`} className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-200">
                                {branch.ordered
                                    ? (branches.length > 1 ? `Isnad branch ${branchIndex + 1}` : 'Narrator chain')
                                    : (branches.length > 1 ? `Linked identities · branch ${branchIndex + 1}` : 'Linked narrator identities · order unresolved')}
                            </h3>
                            <span className="text-xs tabular-nums text-slate-400">{branch.nodes.length} linked</span>
                        </div>
                        {branch.nodes.map((narrator, i) => {
                    const reliability = narrator.reliability ?? 'MAJHUL';
                    const rel = RELIABILITY_STYLE[reliability] || RELIABILITY_STYLE.MAJHUL;
                    const dot = RELIABILITY_DOT[reliability] || 'bg-slate-400';
                    const isProphet = narrator.is_prophet || narrator.tabaqah === 'PROPHET';
                    const narratorName = narrator.name_english || narrator.name_arabic || 'linked narrator';

                    return (
                        <div key={`${branch.id}:${narrator.id}:${narrator.chain_position ?? i}`} className="flex flex-col items-center w-full">
                            {/* Narrator card */}
                            <Link
                                href={`/narrator/${narrator.id}`}
                                aria-label={`Open narrator profile for ${narratorName}`}
                                className={`
                                    group relative w-full max-w-lg rounded-md border
                                    transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950
                                    hover:shadow-lg hover:shadow-slate-900/50
                                    ${isProphet
                                        ? 'border-amber-500/40 bg-amber-500/5 hover:border-amber-400/60'
                                        : 'border-slate-700/50 bg-slate-900/40 hover:border-slate-600/70'
                                    }
                                    px-5 py-4 cursor-pointer
                                `}
                            >
                                {/* Prophet indicator */}
                                {isProphet && (
                                    <div className="absolute -top-2.5 left-1/2 -translate-x-1/2 bg-amber-500/20 border border-amber-500/30 rounded-full px-3 py-0.5 text-[10px] font-semibold text-amber-400 uppercase tracking-wider">
                                        Prophet
                                    </div>
                                )}

                                <div className="flex items-center justify-between gap-4">
                                    {/* Names */}
                                    <div className="flex-1 min-w-0">
                                        <p className="text-lg font-semibold text-slate-100 font-[var(--font-amiri)] leading-relaxed" dir="rtl">
                                            {narrator.name_arabic || '—'}
                                        </p>
                                        <p className="text-sm text-slate-400 mt-0.5">
                                            {narrator.name_english || 'English name not recorded'}
                                            {narrator.death_year_hijri != null && (
                                                <span className="text-slate-400 ml-2">
                                                    d. {narrator.death_year_hijri} AH
                                                </span>
                                            )}
                                        </p>
                                    </div>

                                    {/* Reliability badge */}
                                    <div className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium border ${rel.bg} ${rel.text} ${rel.border} shrink-0`}>
                                        <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />
                                        {rel.label}
                                    </div>
                                </div>

                                {/* Hover arrow */}
                                <div className="absolute right-3 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity text-slate-400">
                                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M6 3l5 5-5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
                                </div>
                            </Link>

                            {/* Arrow connector */}
                            {branch.ordered && i < branch.nodes.length - 1 && (
                                <div className="flex flex-col items-center py-1">
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

                {/* Hadith text node */}
                {(hadithTextArabic || hadithTextEnglish) && (
                    <div className="w-full max-w-lg rounded-xl border border-amber-500/30 bg-slate-900/60 overflow-hidden">
                        <div className="px-3 py-1.5 bg-amber-500/10 border-b border-amber-500/20">
                            <span className="text-[10px] font-semibold text-amber-400 uppercase tracking-wider">
                                {hadithTextLabel}
                            </span>
                        </div>
                        <div className="px-5 py-4 space-y-3">
                            {hadithTextArabic && (
                                <p className="text-base leading-loose text-amber-100/90 font-[var(--font-amiri)]" dir="rtl">
                                    {hadithTextArabic}
                                </p>
                            )}
                            {hadithTextArabic && hadithTextEnglish && (
                                <div className="border-t border-slate-700/50" />
                            )}
                            {hadithTextEnglish && (
                                <p className="text-sm leading-relaxed text-slate-300">
                                    {hadithTextEnglish}
                                </p>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
