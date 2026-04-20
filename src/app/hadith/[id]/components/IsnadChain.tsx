'use client';

import { useMemo } from 'react';
import Link from 'next/link';

interface ChainNode {
    id: string;
    name_arabic: string;
    name_english: string;
    reliability: string;
    tabaqah?: string;
    death_year_hijri?: number;
    is_prophet?: boolean;
}

interface ChainEdge {
    source: string;
    target: string;
    status: string;
}

interface IsnadChainProps {
    nodes: ChainNode[];
    edges: ChainEdge[];
    hadithTextArabic?: string | null;
    hadithTextEnglish?: string | null;
    chainTextArabic?: string | null;
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

export function IsnadChain({ nodes, edges, hadithTextArabic, hadithTextEnglish, chainTextArabic }: IsnadChainProps) {
    const chain = useMemo(() => buildOrderedChain(nodes, edges), [nodes, edges]);

    if (chain.length === 0 && !hadithTextArabic && !hadithTextEnglish && !chainTextArabic) {
        return (
            <div className="flex items-center justify-center py-20 text-slate-400 text-sm">
                No isnad chain data available for this hadith.
            </div>
        );
    }

    return (
        <div className="w-full py-10 px-4">
            <div className="flex flex-col items-center max-w-2xl mx-auto">
                {/* Raw chain text fallback when no graph narrator nodes exist */}
                {chain.length === 0 && chainTextArabic && (
                    <div className="w-full max-w-lg mb-4">
                        <div className="rounded-xl border border-cyan-500/30 bg-slate-900/60 overflow-hidden">
                            <div className="px-3 py-1.5 bg-cyan-500/10 border-b border-cyan-500/20">
                                <span className="text-[10px] font-semibold text-cyan-400 uppercase tracking-wider">
                                    Chain of Transmission (Isnad)
                                </span>
                            </div>
                            <div className="px-5 py-4">
                                <p className="text-base leading-loose text-cyan-100/80 font-[var(--font-amiri)]" dir="rtl">
                                    {chainTextArabic}
                                </p>
                            </div>
                        </div>
                        {/* Arrow to matn */}
                        {(hadithTextArabic || hadithTextEnglish) && (
                            <div className="flex flex-col items-center py-1">
                                <div className="w-px h-6 bg-slate-600" />
                                <svg width="12" height="8" viewBox="0 0 12 8" className="text-slate-400 -mt-px">
                                    <path d="M1 1l5 5.5L11 1" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
                                </svg>
                            </div>
                        )}
                    </div>
                )}

                {/* Chain nodes */}
                {chain.map((narrator, i) => {
                    const rel = RELIABILITY_STYLE[narrator.reliability] || RELIABILITY_STYLE.MAJHUL;
                    const dot = RELIABILITY_DOT[narrator.reliability] || 'bg-slate-400';
                    const isProphet = narrator.is_prophet || narrator.tabaqah === 'PROPHET';

                    return (
                        <div key={narrator.id} className="flex flex-col items-center w-full">
                            {/* Narrator card */}
                            <Link
                                href={`/narrator/${narrator.id}`}
                                target="_blank"
                                className={`
                                    group relative w-full max-w-lg rounded-xl border
                                    transition-all duration-200
                                    hover:scale-[1.02] hover:shadow-lg hover:shadow-slate-900/50
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
                                            {narrator.name_arabic}
                                        </p>
                                        <p className="text-sm text-slate-400 mt-0.5">
                                            {narrator.name_english}
                                            {narrator.death_year_hijri && (
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
                            {(i < chain.length - 1 || hadithTextArabic || hadithTextEnglish) && (
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

                {/* Hadith text node */}
                {(hadithTextArabic || hadithTextEnglish) && (
                    <div className="w-full max-w-lg rounded-xl border border-amber-500/30 bg-slate-900/60 overflow-hidden">
                        <div className="px-3 py-1.5 bg-amber-500/10 border-b border-amber-500/20">
                            <span className="text-[10px] font-semibold text-amber-400 uppercase tracking-wider">
                                Hadith Text (Matn)
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
