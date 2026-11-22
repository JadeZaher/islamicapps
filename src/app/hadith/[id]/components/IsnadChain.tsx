'use client';

import { useMemo } from 'react';
import Link from 'next/link';
import { WithheldIdentity } from '@/components/archive/WithheldIdentity';

import { ArabicText } from '@/components/ArabicText';
import { SourceCodeLink } from '@/components/archive/SourceCredit';
import { narratorNameParts } from '@/components/NarratorName';
import { TraditionBadge } from '@/components/TraditionBadge';
import {
    BasisMark,
    NameBasisMark,
    NAME_LATIN_BASIS_LABEL,
    NarratorNode,
    STANDING_BASIS_LABEL,
    candidateBasisLabel,
    candidateMarkBasis,
    type NarratorNodeKind,
} from '@/components/marks';
import type { ChainGraph, ChainMentionCandidate, ChainNode, HadithTraditionCode } from '@/db/queries/contracts';
import { groupCandidates, type IdentityGroup, type IdentityRecord } from '@/db/queries/identity-groups';
import { sourceForLatinName, sourcesForIdentityClaim } from '@/lib/sources/registry';
import { ChainSourceCredits } from './family/SourceCredits';
import { structureNote } from './chain-structure';

/** Which registry a record belongs to, in words, for a second record of the same person. */
const RECORD_SOURCE: Record<string, string> = {
    rawi: 'narrator lexicon',
    hadith_kg: 'hadith-kg',
    riwayat: 'Riwayat',
    imam_register: 'Imam register',
    imami_rijal: 'Imami rijal',
};

function narratorHref(narratorId: string): string {
    return `/narrator/${encodeURIComponent(narratorId)}`;
}

/** One basis line (DESIGN.md §Identity basis labels): mark, wording, inline source codes. */
function BasisLine({ candidate, tradition }: { candidate: ChainMentionCandidate; tradition: HadithTraditionCode | null }) {
    return (
        <p className="relative mt-1 ps-[1.125rem] text-ink-muted">
            <BasisMark basis={candidateMarkBasis(candidate)} decorative className="absolute start-0 top-[0.3125rem]" />
            {candidateBasisLabel(candidate, tradition)}
            {candidate.detail && (
                <>
                    {': '}
                    <bdi>{candidate.detail}</bdi>
                </>
            )}
            {sourcesForIdentityClaim(candidate.basis, candidate.origin, tradition).map((code) => (
                <span key={code}>
                    {' · '}
                    <SourceCodeLink code={code} />
                </span>
            ))}
        </p>
    );
}

/** Basis lines of one record, one per distinct wording. */
function BasisLines({ record, tradition }: { record: IdentityRecord; tradition: HadithTraditionCode | null }) {
    const seen = new Set<string>();
    const lines = record.candidates.filter((candidate) => {
        const label = candidateBasisLabel(candidate, tradition);
        if (seen.has(label)) return false;
        seen.add(label);
        return true;
    });
    return (
        <>
            {lines.map((candidate) => (
                <BasisLine key={`${candidate.basis}:${candidate.origin ?? ''}`} candidate={candidate} tradition={tradition} />
            ))}
        </>
    );
}

function RecordName({ record }: { record: IdentityRecord }) {
    const { latin, arabic } = narratorNameParts(record.candidate.name_en, record.candidate.name_ar);
    return (
        <span className="inline-flex flex-wrap items-baseline gap-x-2">
            <Link href={narratorHref(record.narratorId)} className="link-row font-semibold text-ink">
                {latin || <ArabicText>{arabic || record.narratorId}</ArabicText>}
            </Link>
            {latin && arabic && (
                <bdi lang="ar" dir="rtl" className="font-arabic text-[1.0625rem] text-ink-muted">
                    {arabic}
                </bdi>
            )}
        </span>
    );
}

/** One person: the first record as the identity, the other records of the same person as "also" links. */
function IdentityGroupView({ group, tradition }: { group: IdentityGroup; tradition: HadithTraditionCode | null }) {
    const [first, ...others] = group.records;
    return (
        <div>
            <RecordName record={first} />
            <BasisLines record={first} tradition={tradition} />
            {others.map((record) => (
                <div key={record.narratorId} className="mt-1.5">
                    <p className="text-ink-muted">
                        Same person in {RECORD_SOURCE[record.candidate.authority ?? ''] ?? 'another source'}:{' '}
                        <Link href={narratorHref(record.narratorId)} className="link-row">
                            {narratorNameParts(record.candidate.name_en, record.candidate.name_ar).latin || (
                                <ArabicText>{record.candidate.name_ar ?? record.narratorId}</ArabicText>
                            )}
                        </Link>
                    </p>
                    <BasisLines record={record} tradition={tradition} />
                </div>
            ))}
        </div>
    );
}

/**
 * Who a written name is: nothing, one person (however many sources agree), or every person when they differ. A standing
 * identity comes first with what made it machine-reviewed; labels (kunya-only, a shared Imam kunya) are secondary notes
 * and never a disagreement (owner decisions 2026-11-21).
 */
function MentionIdentityCell({ node, tradition }: { node: ChainNode; tradition: HadithTraditionCode | null }) {
    const groups = groupCandidates(node.candidates);
    if (groups.length === 0) return <p className="pt-1.5 type-small text-ink-muted">Not yet identified</p>;
    const standing = node.is_link ? groups.find((group) => group.records.some((record) => record.narratorId === node.narrator_id)) : undefined;
    const persons = groups.filter((group) => !group.labelOnly && group !== standing);
    const labels = groups.filter((group) => group.labelOnly && group !== standing);
    const ordered = standing ? [standing, ...persons] : persons;
    return (
        <div className="space-y-2 pt-1.5 type-small">
            {standing && node.standing_basis && (
                <p className="relative ps-[1.125rem] text-ink" data-standing-basis={node.standing_basis}>
                    <BasisMark basis="source_index_confirmed_by_text" decorative className="absolute start-0 top-[0.3125rem]" />
                    {STANDING_BASIS_LABEL[node.standing_basis] ?? 'machine-reviewed'}
                </p>
            )}
            {node.identity === 'differ' && <p className="text-ink-muted">Sources differ on who this is</p>}
            {node.identity_withheld_reason && <WithheldIdentity reason={node.identity_withheld_reason} />}
            <div className="space-y-3">
                {ordered.map((group) => (
                    <IdentityGroupView key={group.personKey} group={group} tradition={tradition} />
                ))}
            </div>
            {labels.map((group) => (
                <div key={group.personKey} className="text-ink-muted">
                    <p>
                        {ordered.length > 0 ? 'Also ' : ''}
                        {group.records.map((record, index) => (
                            <span key={record.narratorId}>
                                {index > 0 && ', '}
                                <Link href={narratorHref(record.narratorId)} className="link-row">
                                    {narratorNameParts(record.candidate.name_en, record.candidate.name_ar).latin || (
                                        <ArabicText>{record.candidate.name_ar ?? record.narratorId}</ArabicText>
                                    )}
                                </Link>
                            </span>
                        ))}
                    </p>
                    {group.records.map((record) => (
                        <BasisLines key={record.narratorId} record={record} tradition={tradition} />
                    ))}
                </div>
            ))}
        </div>
    );
}

/** What a position is when it is not a name written here: repeated from an earlier report, or a gap the text marks. */
export function positionNote(node: Pick<ChainNode, 'inherited_from_mention_id' | 'link_kind'>): string | null {
    if (node.link_kind === 'anonymous') return 'Unnamed transmitter: the text names no one here';
    if (node.link_kind === 'not_a_narrator') return "Refers back to the previous report's chain; not a narrator";
    if (node.inherited_from_mention_id) return "From the earlier report's chain";
    return null;
}

/** Why a chain does not start with the compiler's own shaykh (0015), in plain words. */
export const CHAIN_SUSPENSION_LABEL: Record<string, string> = {
    back_reference: 'Chain relies on the previous report',
    mid_chain_start: 'Chain starts mid-way and relies on an earlier report',
    route_given_elsewhere: "The compiler gives his route to the first narrator elsewhere in the book",
};

/** The name as written: Arabic in the Arabic face at the end, its Latin form at the start with how it was obtained. */
function WrittenName({ node }: { node: ChainNode }) {
    const note = positionNote(node);
    return (
        <div className="min-w-0">
            <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                <ArabicText as="p" variant="inline" className="order-2 ms-auto text-ink">
                    {node.surface_ar}
                </ArabicText>
                {node.name_latin && (
                    <p className="order-1 type-small text-ink" lang="en" data-name-latin={node.name_latin_basis ?? ''}>
                        {node.name_latin}
                    </p>
                )}
            </div>
            {node.name_latin && node.name_latin_basis && (
                <p className="relative mt-0.5 ps-[1.125rem] text-xs leading-4 text-ink-muted">
                    <NameBasisMark basis={node.name_latin_basis} decorative className="absolute start-0 top-[0.1875rem]" />
                    {NAME_LATIN_BASIS_LABEL[node.name_latin_basis]}
                    {' · '}
                    <SourceCodeLink code={sourceForLatinName(node.name_latin_basis, node.name_latin_narrator_id)} />
                </p>
            )}
            {note && (
                <p className="mt-0.5 text-xs leading-4 text-ink-muted" data-position-note>
                    {note}
                </p>
            )}
        </div>
    );
}

/** The rail mark of a position (DESIGN.md §Isnad list): outline when unidentified, two bars when sources differ or the dates do. */
function nodeKind(node: ChainNode): NarratorNodeKind {
    if (node.candidates.length === 0) return 'unidentified';
    return node.identity === 'differ' || node.identity_withheld_reason ? 'contested' : 'identified';
}

interface IsnadChainProps {
    chain: ChainGraph | null;
    sourceSanadText?: string | null;
    /** Names the chain for assistive technology when several reports' chains share a page ("Sahih Muslim 5036"). */
    chainLabel?: string;
}

/**
 * The written sanad, then each branch name by name as written, with its Latin form, every identity proposed for it and
 * where each comes from. No verdicts here: those live, attributed, on narrator pages.
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
    const tradition = chain?.tradition ?? null;

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
                    {branch.nodes[0].chain_missing_link_after != null && (
                        <p className="mb-2 type-small text-ink-muted" data-chain-missing-link>
                            A link is missing after name {branch.nodes[0].chain_missing_link_after + 1}: the next name lived too
                            early to be heard directly
                        </p>
                    )}
                    {structureNote(branch.nodes[0]) && (
                        <p className="mb-2 type-small text-ink-muted" data-chain-structure="uncertain">
                            {structureNote(branch.nodes[0])}
                        </p>
                    )}
                    {branch.nodes[0].chain_suspension && (
                        <p className="mb-2 type-small text-ink-muted" data-chain-suspension={branch.nodes[0].chain_suspension}>
                            {CHAIN_SUSPENSION_LABEL[branch.nodes[0].chain_suspension] ?? 'Chain relies on another report'}
                        </p>
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
                                <div className="grid grid-cols-1 gap-y-1 border-b border-rule pb-3 group-last/position:border-b-0 sm:grid-cols-[minmax(10rem,5fr)_minmax(0,6fr)] sm:gap-x-6">
                                    <WrittenName node={node} />
                                    <MentionIdentityCell node={node} tradition={tradition} />
                                </div>
                            </li>
                        ))}
                    </ol>
                </div>
            ))}
            <ChainSourceCredits chain={chain} />
        </div>
    );
}
