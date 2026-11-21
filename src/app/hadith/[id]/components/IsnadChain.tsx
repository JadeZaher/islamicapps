'use client';

import { useMemo } from 'react';
import Link from 'next/link';

import { ArabicText } from '@/components/ArabicText';
import { narratorNameParts } from '@/components/NarratorName';

interface ChainNode {
    id: string;
    name_arabic?: string | null;
    name_english?: string | null;
    tabaqah?: string;
    is_prophet?: boolean;
    /** Position as recorded on the chain inclusion, when the graph has it. */
    chain_position?: number | null;
    chain_id?: string | null;
    chain_index?: number | null;
    chain_schema?: 'v2' | 'legacy';
    /** False for a mention not resolved to a narrator; absent on legacy rows, which are all resolved. */
    is_link?: boolean;
}

interface ChainEdge {
    source: string;
    target: string;
    chain_id?: string | null;
}

interface IsnadChainProps {
    nodes: ChainNode[];
    edges: ChainEdge[];
    sourceSanadText?: string | null;
}

const ROW_CLASS = '-mx-2 flex flex-col gap-x-6 rounded-md px-2 py-1.5 sm:flex-row sm:items-baseline sm:justify-between';

/** Orders one branch: recorded INCLUDES positions first, otherwise a walk along NARRATED_FROM edges. */
function buildOrderedChain(nodes: ChainNode[], edges: ChainEdge[]): ChainNode[] {
    if (nodes.length === 0) return [];
    if (nodes.every((node) => Number.isFinite(node.chain_position))) {
        return [...nodes].sort((a, b) => (a.chain_position ?? 0) - (b.chain_position ?? 0));
    }
    if (edges.length === 0) return nodes;

    // Edges run student -> teacher; start from the narrator nobody narrates from.
    const teacherOf = new Map<string, string>();
    for (const edge of edges) teacherOf.set(edge.source, edge.target);
    const targets = new Set(edges.map((edge) => edge.target));
    const start = nodes.find((node) => !targets.has(node.id) && teacherOf.has(node.id))
        ?? nodes.find((node) => teacherOf.has(node.id))
        ?? nodes[0];

    const chain: ChainNode[] = [];
    const visited = new Set<string>();
    let current: ChainNode | undefined = start;
    while (current && !visited.has(current.id)) {
        visited.add(current.id);
        chain.push(current);
        const nextId = teacherOf.get(current.id);
        current = nextId ? nodes.find((node) => node.id === nextId) : undefined;
    }
    for (const node of nodes) if (!visited.has(node.id)) chain.push(node);
    return chain;
}

function hasNarratorName(node: ChainNode): boolean {
    return Boolean(node.name_arabic?.trim() || node.name_english?.trim());
}

/** Groups by chain id first so taḥwīl branches are never flattened into one isnad (see src/app/actions/AGENTS.md). */
function buildChainBranches(nodes: ChainNode[], edges: ChainEdge[]) {
    const grouped = new Map<string, { chainIndex: number | null; nodes: ChainNode[]; edges: ChainEdge[] }>();
    for (const node of nodes) {
        const chainId = node.chain_id || 'linked-chain';
        const branch = grouped.get(chainId) ?? { chainIndex: node.chain_index ?? null, nodes: [], edges: [] };
        branch.nodes.push(node);
        grouped.set(chainId, branch);
    }
    for (const edge of edges) grouped.get(edge.chain_id || 'linked-chain')?.edges.push(edge);
    return [...grouped.entries()]
        .map(([id, branch]) => ({
            id,
            chainIndex: branch.chainIndex,
            nodes: buildOrderedChain(branch.nodes, branch.edges).filter(hasNarratorName),
            ordered: branch.nodes.every((node) => Number.isFinite(node.chain_position)) ||
                (branch.nodes.every((node) => node.chain_schema !== 'legacy') && branch.edges.length > 0),
        }))
        .filter((branch) => branch.nodes.length > 0)
        .sort((a, b) => (a.chainIndex ?? Number.MAX_SAFE_INTEGER) - (b.chainIndex ?? Number.MAX_SAFE_INTEGER) || a.id.localeCompare(b.id));
}

/** The written sanad, then the identified narrators of each branch as a linked rail. No verdicts: those live, attributed, on narrator pages. */
export function IsnadChain({ nodes, edges, sourceSanadText }: IsnadChainProps) {
    const branches = useMemo(() => buildChainBranches(nodes, edges), [nodes, edges]);
    const sourceSanad = sourceSanadText?.trim() || null;

    if (branches.length === 0 && !sourceSanad) return null;

    return (
        <div className="space-y-8">
            {sourceSanad && (
                <ArabicText as="p" className="whitespace-pre-line text-xl text-slate-300">
                    {sourceSanad}
                </ArabicText>
            )}

            {branches.map((branch, branchIndex) => {
                const List = branch.ordered ? 'ol' : 'ul';
                const label = branches.length > 1 ? `Branch ${branchIndex + 1}` : 'Narrators';
                return (
                    <div key={branch.id}>
                        {(branches.length > 1 || !branch.ordered || sourceSanad) && (
                            <p className="mb-3 text-sm text-slate-400">
                                {label}
                                {!branch.ordered && <span className="text-slate-500"> · order not recorded</span>}
                            </p>
                        )}
                        <List
                            aria-label={branches.length > 1 ? `Chain branch ${branchIndex + 1}` : 'Narrators in this chain'}
                            className={branch.ordered ? 'relative ms-1.5 border-s border-slate-700' : 'space-y-1'}
                        >
                            {branch.nodes.map((narrator, index) => {
                                const isProphet = narrator.is_prophet || narrator.tabaqah === 'PROPHET';
                                const { latin, arabic } = narratorNameParts(narrator.name_english, narrator.name_arabic);
                                return (
                                    <li key={`${branch.id}:${narrator.id}:${narrator.chain_position ?? index}`} className={branch.ordered ? 'relative ps-5' : ''}>
                                        {branch.ordered && (
                                            <span
                                                aria-hidden="true"
                                                className={`absolute -start-[5px] top-1/2 size-2.5 -translate-y-1/2 rounded-full border-2 border-slate-950 ${isProphet ? 'bg-amber-400' : 'bg-slate-500'}`}
                                            />
                                        )}
                                        {narrator.is_link === false ? (
                                            // Unidentified mention: the name as written, never a link to an identity we do not have.
                                            <div className={`${ROW_CLASS} text-slate-500`}>
                                                <span className="text-sm">Not yet identified</span>
                                                {arabic && (
                                                    <ArabicText className="order-first text-lg leading-relaxed text-slate-300 sm:order-none">{arabic}</ArabicText>
                                                )}
                                            </div>
                                        ) : (
                                            <Link
                                                href={`/narrator/${encodeURIComponent(narrator.id)}`}
                                                className={`group ${ROW_CLASS} outline-none transition-colors hover:bg-slate-900 focus-visible:ring-2 focus-visible:ring-emerald-400`}
                                            >
                                                {latin && <span className="text-sm text-slate-400 group-hover:text-slate-200">{latin}</span>}
                                                {/* Arabic leads on phones; on wider screens it sits at the right edge, where Arabic reads from. */}
                                                {arabic && (
                                                    <ArabicText className="order-first text-lg leading-relaxed text-slate-100 sm:order-none">{arabic}</ArabicText>
                                                )}
                                            </Link>
                                        )}
                                    </li>
                                );
                            })}
                        </List>
                    </div>
                );
            })}
        </div>
    );
}
