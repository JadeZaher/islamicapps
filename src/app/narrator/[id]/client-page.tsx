'use client';

import { hadithPath } from '@/lib/hadith-address';
import type { ReactNode } from 'react';
import Link from 'next/link';
import { CommentarySection } from '@/components/CommentarySection';
import { TraditionBadge, ParallelTypeBadge, IsraIliyyatBadge } from '@/components/TraditionBadge';
import { ConsensusBadge } from '@/components/ConsensusBadge';
import { ArabicText } from '@/components/ArabicText';
import { EmptyState } from '@/components/EmptyState';
import { BilingualTitle, NarratorName } from '@/components/NarratorName';
import type { NarratorVerdict } from '@/db/queries/contracts';
import { VerdictsByTradition } from './components/VerdictsByTradition';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';

function SectionHeading({ children }: { children: React.ReactNode }) {
    return <h2 className="section-rule type-label mb-4">{children}</h2>;
}

export interface NarratorClientPageProps {
    /** Server-rendered life-and-times section (dates, generation, places, eras, events); replaces the old Life block. */
    lifeAndTimes?: ReactNode;
    /** Published verdicts; shown grouped by tradition above the tabs. */
    verdicts?: NarratorVerdict[];
    narratorDetails: {
        id: string;
        name_english: string;
        name_arabic: string;
        reliability?: 'THIQA' | 'SADUQ' | 'DAIF' | 'MAJHUL' | 'KADHAB';
        tabaqah: string;
        birth_year_hijri?: number;
        birth_year_gregorian?: number;
        birth_date_source_text?: string;
        birth_date_provenance?: string;
        birth_date_review_status?: string;
        death_year_hijri?: number;
        death_year_gregorian?: number;
        death_date_source_text?: string;
        death_date_provenance?: string;
        death_date_review_status?: string;
        bio?: string;
        biographical_narrative?: string;
        geographic_region?: string;
        // ─── v2 / Phase-0 narrator-enrichment fields ─────────────────────────
        /** True for the Prophet ﷺ; suppresses jarḥ/taʿdīl rendering by design. */
        is_prophet?: boolean;
        /** True for Companions (ṣaḥāba). */
        is_companion?: boolean;
        /** Cleaned canonical Arabic name (alongside legacy name_arabic). */
        name_arabic_clean?: string;
        /** Cleaned canonical English transliteration. */
        name_english_clean?: string;
        kunya?: string;
        nasab?: string;
        nisba?: string;
        /** AH death year (v2 schema). */
        death_date_hijri?: number;
        /** CE death year (v2 schema). */
        death_date_gregorian?: number;
        /** 2-3 sentence English synopsis. */
        bio_summary?: string;
        /** Concatenated tawthīq quotes (Arabic with English glosses in parens). */
        bio_tadil?: string;
        /** Concatenated tajrīḥ quotes — usually empty for Companions / major Tābiʿīn. */
        bio_jarh?: string;
        /** Single classical verdict label: thiqa | ṣadūq | ḍaʿīf | … | not_applicable. */
        reliability_consensus?: string;
        /** True when critics conflicted — drives a "contested" badge. */
        reliability_disagreement?: boolean;
        /** How many distinct critics contributed quotes. */
        critic_quote_count?: number;
        /** Provenance of bio fields: 'manual_phase_0' | 'taqrib_v1' | … */
        bio_provenance?: string;
        other_hadiths?: Array<{
            id: string;
            title: string;
            primary_topic?: string;
            display_grade?: string;
        }>;
    };
    narratorNetwork?: {
        teachers?: Array<{
            id: string;
            name_english: string;
            name_arabic: string;
            relationship: string;
        }>;
        students?: Array<{
            id: string;
            name_english: string;
            name_arabic: string;
            relationship: string;
        }>;
    };
    commentaries?: Array<{
        id: string;
        author: string;
        text: string;
        source_work: string;
        reference?: string;
        type: 'HADITH_COMMENTARY' | 'NARRATOR_BIOGRAPHY' | 'CHAIN_ANALYSIS' | 'OTHER';
    }>;
    traditionConnections?: {
        traditions: Array<{ id: string; name: string; name_arabic?: string; description?: string }>;
        hadiths_with_parallels: Array<{
            hadith: { id: string; title: string; display_grade?: string };
            parallel: { id: string; parallel_type: string; isra_iliyyat_status: string };
            tradition: { id: string; name: string };
            source_text: { title: string; canonical_reference?: string };
        }>;
    };
}

const HADITH_QUERY_LIMIT = 100;

const TAB_TRIGGER_CLASS =
    'flex-none rounded-none border-0 border-b-2 border-transparent bg-transparent px-1 pb-3 pt-1 text-sm font-medium text-ink-muted ' +
    'hover:text-ink data-[state=active]:border-ink data-[state=active]:bg-transparent data-[state=active]:text-ink ';

const LINK_ROW_CLASS =
    '-mx-3 block px-3 py-2.5 transition-colors hover:bg-sunken ';

/** Narrator tabs. Every section renders only what the record holds; unknowns say "Unknown". See src/components/AGENTS.md §Narrator detail. */
export default function NarratorClientPage({
    narratorDetails,
    verdicts = [],
    lifeAndTimes,
    narratorNetwork,
    commentaries = [],
    traditionConnections,
}: NarratorClientPageProps) {
    const teachers = narratorNetwork?.teachers ?? [];
    const students = narratorNetwork?.students ?? [];
    const hasNetwork = teachers.length > 0 || students.length > 0;
    const otherHadiths = narratorDetails.other_hadiths ?? [];
    // The upstream query is LIMIT 100: a full page means "at least 100", not exactly 100.
    const hadithCountLabel = otherHadiths.length >= HADITH_QUERY_LIMIT ? `${HADITH_QUERY_LIMIT}+` : String(otherHadiths.length);
    const hasTraditions = Boolean(traditionConnections && traditionConnections.traditions.length > 0);

    const summary = narratorDetails.bio_summary || narratorDetails.biographical_narrative || narratorDetails.bio;
    const hasAssessment = !narratorDetails.is_prophet &&
        Boolean(narratorDetails.reliability_consensus || narratorDetails.bio_tadil || narratorDetails.bio_jarh);
    const hasOtherTabs = hasNetwork || otherHadiths.length > 0 || commentaries.length > 0 || hasTraditions;
    const isSparse = !summary && !hasAssessment && !hasNetwork && otherHadiths.length === 0;

    return (
        <>
        <VerdictsByTradition verdicts={verdicts} />
        <Tabs defaultValue="biography" className="w-full">
            {/* A tab bar with one tab is noise: show it only when there is somewhere else to go. */}
            <div className={hasOtherTabs ? 'mb-8 overflow-x-auto border-b border-rule [scrollbar-width:none]' : 'sr-only'}>
                <TabsList className="h-auto w-max min-w-full justify-start gap-6 rounded-none bg-transparent p-0">
                    <TabsTrigger value="biography" className={TAB_TRIGGER_CLASS}>Biography</TabsTrigger>
                    {hasNetwork && <TabsTrigger value="network" className={TAB_TRIGGER_CLASS}>Teachers and students</TabsTrigger>}
                    {otherHadiths.length > 0 && <TabsTrigger value="hadiths" className={TAB_TRIGGER_CLASS}>Hadith ({hadithCountLabel})</TabsTrigger>}
                    {commentaries.length > 0 && <TabsTrigger value="commentaries" className={TAB_TRIGGER_CLASS}>Commentary</TabsTrigger>}
                    {hasTraditions && <TabsTrigger value="traditions" className={TAB_TRIGGER_CLASS}>Other traditions</TabsTrigger>}
                </TabsList>
            </div>

            <TabsContent value="biography" className="max-w-[var(--measure-wide)] space-y-10">
                {summary && (
                    <section>
                        <SectionHeading>Summary</SectionHeading>
                        <p className="whitespace-pre-line leading-relaxed text-ink" dir="auto">{summary}</p>
                        {!narratorDetails.bio_summary && narratorDetails.bio && narratorDetails.biographical_narrative &&
                            narratorDetails.bio !== narratorDetails.biographical_narrative && (
                            <p className="mt-4 whitespace-pre-line leading-relaxed text-ink" dir="auto">{narratorDetails.bio}</p>
                        )}
                    </section>
                )}

                {narratorDetails.is_prophet && (
                    <p className="border-s-2 border-rule ps-4 text-sm leading-relaxed text-ink-muted">
                        The Prophet is the source of the corpus and is not assessed within narrator criticism (jarḥ wa taʿdīl).
                    </p>
                )}

                {hasAssessment && (
                    <section>
                        <SectionHeading>Jarḥ wa taʿdīl · assessments</SectionHeading>
                        {(narratorDetails.reliability_consensus || narratorDetails.reliability_disagreement || narratorDetails.is_companion) && (
                            <div className="mb-2 flex flex-wrap items-center gap-2">
                                <ConsensusBadge verdict={narratorDetails.reliability_consensus} />
                                {narratorDetails.reliability_disagreement && (
                                    <span className="type-label">critics disagree</span>
                                )}
                                {narratorDetails.is_companion && (
                                    <span className="type-label">ṣaḥābī</span>
                                )}
                            </div>
                        )}
                        {narratorDetails.reliability_consensus && (
                            <p className="mb-4 text-xs text-ink-muted">
                                Hand-entered summary label. The tradition and critic it belongs to are not yet recorded.
                            </p>
                        )}
                        {narratorDetails.is_companion && (
                            <p className="mb-6 text-sm leading-relaxed text-ink-muted">
                                In Sunni rijāl literature Companions are not individually assessed (ʿadālat al-ṣaḥāba).
                                Assessments from other traditions are listed where recorded.
                            </p>
                        )}
                        {narratorDetails.bio_tadil && (
                            <div className="mb-6">
                                <h3 className="mb-2 text-sm font-medium text-ink">Taʿdīl · statements of trust</h3>
                                <p className="whitespace-pre-line leading-loose text-ink" dir="auto">{narratorDetails.bio_tadil}</p>
                            </div>
                        )}
                        {narratorDetails.bio_jarh && (
                            <div className="mb-6">
                                <h3 className="mb-2 text-sm font-medium text-ink">Jarḥ · statements of criticism</h3>
                                <p className="whitespace-pre-line leading-loose text-ink" dir="auto">{narratorDetails.bio_jarh}</p>
                            </div>
                        )}
                        {narratorDetails.bio_provenance && (
                            <p className="text-xs text-ink-muted">
                                {narratorDetails.bio_provenance === 'manual_phase_0'
                                    ? 'Uncited manual entry: edition, volume and page are pending.'
                                    : `Provenance: ${narratorDetails.bio_provenance}`}
                                {typeof narratorDetails.critic_quote_count === 'number' && narratorDetails.critic_quote_count > 0 &&
                                    ` · ${narratorDetails.critic_quote_count} critic${narratorDetails.critic_quote_count === 1 ? '' : 's'} quoted`}
                            </p>
                        )}
                    </section>
                )}

                {lifeAndTimes}

                {isSparse && (
                    <EmptyState
                        title="Little is recorded about this narrator yet"
                        description="No biography, assessments, teachers, students or hadith are linked to this record."
                    />
                )}
            </TabsContent>

            {hasNetwork && (
                <TabsContent value="network" className="grid grid-cols-1 gap-10 md:grid-cols-2">
                    {[
                        { title: 'Teachers', people: teachers },
                        { title: 'Students', people: students },
                    ].map(({ title, people }) => (
                        <section key={title}>
                            <SectionHeading>{title} ({people.length})</SectionHeading>
                            {people.length === 0 ? (
                                <p className="text-sm text-ink-muted">None recorded.</p>
                            ) : (
                                <ul className="divide-y divide-rule">
                                    {people.map((person) => (
                                        <li key={person.id}>
                                            <Link href={`/narrator/${encodeURIComponent(person.id)}`} className={LINK_ROW_CLASS}>
                                                <NarratorName
                                                    english={person.name_english}
                                                    arabic={person.name_arabic}
                                                    latinClassName="text-sm font-medium text-ink"
                                                    arabicClassName="text-lg leading-relaxed text-ink-muted"
                                                />
                                            </Link>
                                        </li>
                                    ))}
                                </ul>
                            )}
                        </section>
                    ))}
                </TabsContent>
            )}

            {otherHadiths.length > 0 && (
                <TabsContent value="hadiths">
                    <ul className="divide-y divide-rule">
                        {otherHadiths.map((hadith) => (
                            <li key={hadith.id}>
                                <Link href={hadithPath(hadith.id)} className={LINK_ROW_CLASS}>
                                    <span className="block font-medium text-ink">
                                        {hadith.title ? <BilingualTitle text={hadith.title} /> : 'Untitled hadith'}
                                    </span>
                                    {hadith.primary_topic && hadith.primary_topic !== hadith.title && (
                                        <span className="mt-0.5 block text-sm text-ink-muted">{hadith.primary_topic}</span>
                                    )}
                                </Link>
                            </li>
                        ))}
                    </ul>
                </TabsContent>
            )}

            {commentaries.length > 0 && (
                <TabsContent value="commentaries">
                    <CommentarySection commentaries={commentaries} narratorId={narratorDetails.id} />
                </TabsContent>
            )}

            {hasTraditions && traditionConnections && (
                <TabsContent value="traditions" className="space-y-10">
                    <section>
                        <SectionHeading>Linked traditions</SectionHeading>
                        <ul className="space-y-4">
                            {traditionConnections.traditions.map((tradition) => (
                                <li key={tradition.id}>
                                    <TraditionBadge tradition={tradition.name} size="md" />
                                    {tradition.name_arabic && (
                                        <ArabicText as="p" className="mt-1 text-ink-muted">{tradition.name_arabic}</ArabicText>
                                    )}
                                    {tradition.description && <p className="mt-1 text-sm text-ink-muted">{tradition.description}</p>}
                                </li>
                            ))}
                        </ul>
                    </section>
                    {traditionConnections.hadiths_with_parallels.length > 0 && (
                        <section>
                            <SectionHeading>Hadith in these chains with recorded parallels</SectionHeading>
                            <ul className="divide-y divide-rule">
                                {traditionConnections.hadiths_with_parallels.map((item) => (
                                    <li key={`${item.hadith.id}:${item.parallel.id}`}>
                                        <Link href={hadithPath(item.hadith.id)} className={LINK_ROW_CLASS}>
                                            <span className="block font-medium text-ink">{item.hadith.title}</span>
                                            <span className="mt-2 flex flex-wrap gap-2">
                                                <TraditionBadge tradition={item.tradition.name} />
                                                <ParallelTypeBadge type={item.parallel.parallel_type} />
                                                <IsraIliyyatBadge status={item.parallel.isra_iliyyat_status} />
                                            </span>
                                            <span className="mt-1.5 block text-xs text-ink-muted">
                                                {item.source_text.title}
                                                {item.source_text.canonical_reference && ` · ${item.source_text.canonical_reference}`}
                                            </span>
                                        </Link>
                                    </li>
                                ))}
                            </ul>
                        </section>
                    )}
                </TabsContent>
            )}
        </Tabs>
        </>
    );
}
