'use client';

import { useMemo } from 'react';
import Link from 'next/link';

import { ArabicText } from '@/components/ArabicText';
import { narratorNameParts } from '@/components/NarratorName';
import { TraditionBadge } from '@/components/TraditionBadge';
import type { ChainGraph, ChainMentionCandidate, ChainNode, IdentityBasis } from '@/db/queries/contracts';
import { IdentityCredit } from './family/SourceCredits';

/**
 * Plain labels for where an identity comes from (owner decisions 2026-11-21; see src/db/AGENTS.md §Identity candidates).
 * "Verified" is reserved for a reviewer's decision; the automatic top tier is machine review.
 */
const BASIS_LABEL: Record<IdentityBasis, string> = {
    reviewer_decision: 'verified by a reviewer',
    source_index_confirmed_by_text: "machine-reviewed: matches the source's index and the text",
    source_index: 'source index',
    name_exact: 'matched by name',
    name_spelling_fold: 'matched by name',
    name_kunya_only: 'matched by kunya only',
};

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

function IdentityLink({ group }: { group: IdentityGroup }) {
    return (
        <div>
        <span className="inline-flex flex-wrap items-baseline gap-x-2">
            <Link
                href={`/narrator/${encodeURIComponent(group.narratorId)}`}
                className="rounded-sm text-sm text-slate-200 underline-offset-4 outline-none hover:underline focus-visible:ring-2 focus-visible:ring-emerald-400"
            >
                {group.latin || <ArabicText>{group.arabic || group.narratorId}</ArabicText>}
            </Link>
            <span className="text-xs text-slate-500">{group.labels.join(' · ')}</span>
        </span>
        <IdentityCredit bases={group.bases} className="!text-xs" />
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
    if (primary.length === 0) return <span className="text-sm text-slate-500">Not yet identified</span>;
    return (
        <div className="space-y-1">
            {primary.length === 1 ? (
                <IdentityLink group={primary[0]} />
            ) : (
                <>
                    <p className="text-xs text-slate-500">Sources differ on who this is</p>
                    <div className="flex flex-wrap gap-x-5 gap-y-1">
                        {primary.map((group) => (
                            <IdentityLink key={group.narratorId} group={group} />
                        ))}
                    </div>
                </>
            )}
            {notes.length > 0 && (
                <p className="text-xs text-slate-500">
                    Also{' '}
                    {notes.map((group, index) => (
                        <span key={group.narratorId}>
                            {index > 0 && ', '}
                            <Link href={`/narrator/${encodeURIComponent(group.narratorId)}`} className="underline-offset-4 hover:underline">
                                {group.latin || (group.arabic ? <ArabicText>{group.arabic}</ArabicText> : group.narratorId)}
                            </Link>
                        </span>
                    ))}{' '}
                    · matched by kunya only
                </p>
            )}
            {notes.length > 0 && (
                <IdentityCredit bases={['name_kunya_only']} className="!text-xs" />
            )}
        </div>
    );
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
                <p className="flex flex-wrap items-center gap-2 text-sm text-slate-400">
                    {chain.tradition && <TraditionBadge tradition={chain.tradition} size="sm" />}
                    {chain.source_work && <span>{chain.source_work}</span>}
                </p>
            )}

            {sourceSanad && (
                <ArabicText as="p" className="whitespace-pre-line text-xl text-slate-300">
                    {sourceSanad}
                </ArabicText>
            )}

            {branches.map((branch, branchIndex) => (
                <div key={branch.id}>
                    {(branches.length > 1 || sourceSanad) && (
                        <p className="mb-3 text-sm text-slate-400">{branches.length > 1 ? `Branch ${branchIndex + 1}` : 'Narrators'}</p>
                    )}
                    <ol
                        aria-label={[
                            chainLabel,
                            branches.length > 1 ? `chain branch ${branchIndex + 1}` : 'narrators in this chain',
                        ].filter(Boolean).join(', ').replace(/^./, (first) => first.toUpperCase())}
                        className="relative ms-1.5 border-s border-slate-700"
                    >
                        {branch.nodes.map((node) => (
                            <li key={node.node_id} className="relative ps-5">
                                <span
                                    aria-hidden="true"
                                    className="absolute -start-[5px] top-3.5 size-2.5 rounded-full border-2 border-slate-950 bg-slate-500"
                                />
                                <div className="-mx-2 flex flex-col gap-x-6 gap-y-1 rounded-md px-2 py-1.5 sm:flex-row sm:items-baseline sm:justify-between">
                                    {/* Arabic as written leads on phones; on wider screens it sits at the right edge, where Arabic reads from. */}
                                    <ArabicText className="order-first text-lg leading-relaxed text-slate-100 sm:order-last">
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
