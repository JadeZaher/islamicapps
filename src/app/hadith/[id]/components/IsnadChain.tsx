'use client';

import { useMemo } from 'react';
import Link from 'next/link';

import { ArabicText } from '@/components/ArabicText';
import { narratorNameParts } from '@/components/NarratorName';
import { TraditionBadge } from '@/components/TraditionBadge';
import { BasisMark, IDENTITY_BASIS_LABEL, NarratorNode, type NarratorNodeKind } from '@/components/marks';
import type { ChainGraph, ChainMentionCandidate, ChainNode, IdentityBasis } from '@/db/queries/contracts';
import { IdentityCredit } from './family/SourceCredits';

/** Basis wording is IDENTITY_BASIS_LABEL (src/components/marks/BasisMark.tsx), one copy; owner decisions 2026-11-21, src/db/AGENTS.md §Identity candidates. */
const BASIS_LABEL: Record<IdentityBasis, string> = IDENTITY_BASIS_LABEL;

interface IdentityGroup {
    narratorId: string;
    latin: string;
    arabic: string;
    labels: string[];
    /** Every basis that names this narrator, strongest first: each is credited to its source. */
    bases: IdentityBasis[];
    /** Every candidate for this narrator is a kunya-only match: a label, never a contest. */
    kunyaOnly: boolean;
}

/** One group per narrator, in the order the query ranked the candidates (strongest basis first). */
function groupByNarrator(candidates: ChainMentionCandidate[]): IdentityGroup[] {
    const groups = new Map<string, IdentityGroup>();
    for (const candidate of candidates) {
        const group = groups.get(candidate.narrator_id) ?? {
            narratorId: candidate.narrator_id,
            ...narratorNameParts(candidate.name_en, candidate.name_ar),
            labels: [],
            bases: [],
            kunyaOnly: true,
        };
        const label = BASIS_LABEL[candidate.basis];
        if (label && !group.labels.includes(label)) group.labels.push(label);
        if (!group.bases.includes(candidate.basis)) group.bases.push(candidate.basis);
        if (candidate.basis !== 'name_kunya_only') group.kunyaOnly = false;
        groups.set(candidate.narrator_id, group);
    }
    return [...groups.values()];
}

/** Basis lines (DESIGN.md §Identity basis labels): mark, then wording; one line per distinct wording. */
function BasisLines({ bases }: { bases: IdentityBasis[] }) {
    const seen = new Set<string>();
    const lines = bases.filter((basis) => {
        const label = BASIS_LABEL[basis];
        if (!label || seen.has(label)) return false;
        seen.add(label);
        return true;
    });
    return (
        <>
            {lines.map((basis) => (
                <p key={basis} className="relative mt-1 ps-[1.125rem] text-ink-muted">
                    <BasisMark basis={basis} decorative className="absolute start-0 top-[0.3125rem]" />
                    {BASIS_LABEL[basis]}
                </p>
            ))}
        </>
    );
}

function IdentityLink({ group }: { group: IdentityGroup }) {
    return (
        <div>
            <span className="inline-flex flex-wrap items-baseline gap-x-2">
                <Link href={`/narrator/${encodeURIComponent(group.narratorId)}`} className="link-row font-semibold text-ink">
                    {group.latin || <ArabicText>{group.arabic || group.narratorId}</ArabicText>}
                </Link>
                {group.latin && group.arabic && (
                    <bdi lang="ar" dir="rtl" className="font-arabic text-[1.0625rem] text-ink-muted">
                        {group.arabic}
                    </bdi>
                )}
            </span>
            <BasisLines bases={group.bases} />
            <IdentityCredit bases={group.bases} className="mt-1 !text-xs !leading-4" />
        </div>
    );
}

/**
 * Who a written name is: nothing, one identity (however many sources agree), or every identity when they differ.
 * A kunya-only match beside another identity is a secondary note, never "sources differ" (owner decision 2026-11-21).
 */
function MentionIdentityCell({ node }: { node: ChainNode }) {
    const groups = groupByNarrator(node.candidates);
    const contesting = groups.filter((group) => !group.kunyaOnly);
    const notes = contesting.length > 0 ? groups.filter((group) => group.kunyaOnly) : [];
    const primary = contesting.length > 0 ? contesting : groups;
    if (primary.length === 0) return <p className="pt-1.5 type-small text-ink-muted">Not yet identified</p>;
    return (
        <div className="space-y-2 pt-1.5 type-small">
            {primary.length === 1 ? (
                <IdentityLink group={primary[0]} />
            ) : (
                <>
                    <p className="text-ink-muted">Sources differ on who this is</p>
                    <div className="space-y-3">
                        {primary.map((group) => (
                            <IdentityLink key={group.narratorId} group={group} />
                        ))}
                    </div>
                </>
            )}
            {notes.length > 0 && (
                <p className="text-ink-muted">
                    Also{' '}
                    {notes.map((group, index) => (
                        <span key={group.narratorId}>
                            {index > 0 && ', '}
                            <Link href={`/narrator/${encodeURIComponent(group.narratorId)}`} className="link-row">
                                {group.latin || (group.arabic ? <ArabicText>{group.arabic}</ArabicText> : group.narratorId)}
                            </Link>
                        </span>
                    ))}{' '}
                    · matched by kunya only
                </p>
            )}
            {notes.length > 0 && (
                <IdentityCredit bases={['name_kunya_only']} className="!text-xs !leading-4" />
            )}
        </div>
    );
}

/** The rail mark of a position (DESIGN.md §Isnad list): outline when unidentified, two bars when sources differ. */
function nodeKind(node: ChainNode): NarratorNodeKind {
    const groups = groupByNarrator(node.candidates);
    if (groups.length === 0) return 'unidentified';
    return groups.filter((group) => !group.kunyaOnly).length > 1 ? 'contested' : 'identified';
}

interface IsnadChainProps {
    chain: ChainGraph | null;
    sourceSanadText?: string | null;
    /** Names the chain for assistive technology when several reports' chains share a page ("Sahih Muslim 5036"). */
    chainLabel?: string;
}

/**
 * The written sanad, then each branch name by name as written, with every identity proposed for it and where
 * each comes from. No verdicts here: those live, attributed, on narrator pages.
 */
export function IsnadChain({ chain, sourceSanadText, chainLabel }: IsnadChainProps) {
    const branches = useMemo(() => {
        const grouped = new Map<string, ChainNode[]>();
        for (const node of chain?.nodes ?? []) grouped.set(node.chain_id, [...(grouped.get(node.chain_id) ?? []), node]);
        return [...grouped.entries()]
            .map(([id, nodes]) => ({ id, nodes: [...nodes].sort((a, b) => a.position - b.position) }))
            .sort((a, b) => a.nodes[0].branch - b.nodes[0].branch);
    }, [chain]);
    const sourceSanad = sourceSanadText?.trim() || null;

    if (branches.length === 0 && !sourceSanad) return null;

    return (
        <div className="space-y-8">
            {(chain?.tradition || chain?.source_work) && (
                <p className="flex flex-wrap items-center gap-2 type-small text-ink-muted">
                    {chain.tradition && <TraditionBadge tradition={chain.tradition} size="sm" />}
                    {chain.tradition && chain.source_work && <span aria-hidden="true">·</span>}
                    {chain.source_work && <span>{chain.source_work}</span>}
                </p>
            )}

            {sourceSanad && (
                <ArabicText as="p" variant="reading" className="whitespace-pre-line text-ink-muted">
                    {sourceSanad}
                </ArabicText>
            )}

            {branches.map((branch, branchIndex) => (
                <div key={branch.id}>
                    {(branches.length > 1 || sourceSanad) && (
                        <p className="mb-2 type-h3 text-ink">{branches.length > 1 ? `Branch ${branchIndex + 1}` : 'Narrators'}</p>
                    )}
                    <ol
                        aria-label={[
                            chainLabel,
                            branches.length > 1 ? `chain branch ${branchIndex + 1}` : 'narrators in this chain',
                        ].filter(Boolean).join(', ').replace(/^./, (first) => first.toUpperCase())}
                    >
                        {branch.nodes.map((node, nodeIndex) => (
                            <li key={node.node_id} className="group/position grid grid-cols-[1.5rem_0.75rem_minmax(0,1fr)] items-start gap-x-3">
                                <span aria-hidden="true" className="text-end text-xs leading-8 tabular-nums text-ink-muted">
                                    {nodeIndex + 1}
                                </span>
                                {/* Rail: a faint hairline through the node marks; the order itself is the ordered list. */}
                                <span
                                    aria-hidden="true"
                                    className="relative self-stretch before:absolute before:inset-y-0 before:start-[calc(50%-0.5px)] before:w-px before:bg-ink-faint group-first/position:before:top-4 group-last/position:before:bottom-auto group-last/position:before:h-4"
                                >
                                    <NarratorNode
                                        kind={nodeKind(node)}
                                        decorative
                                        size={12}
                                        className="relative mx-auto mt-[calc(1rem-6px)] text-ink"
                                    />
                                </span>
                                <div className="grid grid-cols-1 border-b border-rule pb-3 group-last/position:border-b-0 sm:grid-cols-[minmax(9rem,2fr)_minmax(0,3fr)] sm:gap-x-6">
                                    <ArabicText as="p" variant="inline" className="text-ink">
                                        {node.surface_ar}
                                    </ArabicText>
                                    <MentionIdentityCell node={node} />
                                </div>
                            </li>
                        ))}
                    </ol>
                </div>
            ))}
        </div>
    );
}
