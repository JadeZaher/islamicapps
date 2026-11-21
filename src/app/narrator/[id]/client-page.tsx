'use client';

import { useState } from 'react';
import Link from 'next/link';
import { TabaqahTimeline } from '@/components/TabaqahTimeline';
import { HistoricalTimeline, type HistoricalTimelineEvent } from '@/components/HistoricalTimeline';
import { CommentarySection } from '@/components/CommentarySection';
import { TraditionBadge, ParallelTypeBadge, IsraIliyyatBadge } from '@/components/TraditionBadge';
import { ConsensusBadge } from '@/components/ConsensusBadge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

function DateEvidence({
    sourceText,
    provenance,
    reviewStatus,
}: {
    sourceText?: string;
    provenance?: string;
    reviewStatus?: string;
}) {
    const reviewed = (
        reviewStatus === 'human_verified' || reviewStatus === 'source_verified'
    ) && Boolean(provenance);
    return (
        <p className="mt-1 text-xs text-white/50">
            {reviewed ? 'Reviewed date provenance' : 'Legacy/unverified date evidence'}:{' '}
            {provenance ? `Source/provenance: ${provenance}` : 'no structured source retained'}
            {sourceText && ` · Source text: ${sourceText}`}
            {!reviewed && ' — not a structured reviewed citation'}
        </p>
    );
}

export interface NarratorClientPageProps {
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
    historicalEvents?: HistoricalTimelineEvent[];
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
    'flex-none rounded-none border-0 border-b-2 border-transparent bg-transparent px-1 pb-3 pt-1 text-sm font-medium text-white/60 shadow-none ' +
    'hover:text-white data-[state=active]:border-cyan-400 data-[state=active]:bg-transparent data-[state=active]:text-white data-[state=active]:shadow-none';

export default function NarratorClientPage({
    narratorDetails,
    narratorNetwork,
    commentaries = [],
    historicalEvents = [],
    traditionConnections,
}: NarratorClientPageProps) {
    const [selectedEvent, setSelectedEvent] = useState<string | null>(null);

    const teachers = narratorNetwork?.teachers ?? [];
    const students = narratorNetwork?.students ?? [];
    const hasNetwork = teachers.length > 0 || students.length > 0;
    const hasTimeline = historicalEvents.length > 0;
    const hadithCount = narratorDetails.other_hadiths?.length ?? 0;
    const hasHadiths = hadithCount > 0;
    // The upstream query is LIMIT 100: a full page means "at least 100", not exactly 100.
    const hadithCountLabel = hadithCount >= HADITH_QUERY_LIMIT ? `${HADITH_QUERY_LIMIT}+` : String(hadithCount);

    // v2 rows carry death_date_*; v1 rows carry death_year_*. Unknown stays undefined.
    const deathYearHijri = narratorDetails.death_year_hijri ?? narratorDetails.death_date_hijri;
    const deathYearGregorian = narratorDetails.death_year_gregorian ?? narratorDetails.death_date_gregorian;

    return (
        <Tabs defaultValue="biography" className="w-full">
            <div className="mb-8 overflow-x-auto border-b border-white/10 [scrollbar-width:none]">
                <TabsList className="h-auto w-max min-w-full justify-start gap-6 rounded-none bg-transparent p-0">
                    <TabsTrigger value="biography" className={TAB_TRIGGER_CLASS}>
                        Biography
                    </TabsTrigger>
                    {hasTimeline && (
                        <TabsTrigger value="timeline" className={TAB_TRIGGER_CLASS}>
                            Historical Timeline
                        </TabsTrigger>
                    )}
                    {hasNetwork && (
                        <TabsTrigger value="network" className={TAB_TRIGGER_CLASS}>
                            Teachers and Students
                        </TabsTrigger>
                    )}
                    {hasHadiths && (
                        <TabsTrigger value="hadiths" className={TAB_TRIGGER_CLASS}>
                            Hadiths
                        </TabsTrigger>
                    )}
                    {commentaries.length > 0 && (
                        <TabsTrigger value="commentaries" className={TAB_TRIGGER_CLASS}>
                            Commentaries
                        </TabsTrigger>
                    )}
                    {traditionConnections && traditionConnections.traditions.length > 0 && (
                        <TabsTrigger value="traditions" className={TAB_TRIGGER_CLASS}>
                            Tradition Connections ({traditionConnections.traditions.length})
                        </TabsTrigger>
                    )}
                </TabsList>
            </div>

            {/* Biography Tab */}
            <TabsContent value="biography">
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    {/* Main Biography */}
                    <div className="lg:col-span-2">
                        <Card className="bg-white/5 border-white/10">
                            <CardHeader>
                                <CardTitle className="text-white">Biography</CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-6">
                                {/* ─── Phase-0 enriched bio_summary ─── */}
                                {narratorDetails.bio_summary && (
                                    <div>
                                        <h3 className="text-lg font-semibold text-cyan-300 mb-3">
                                            Summary
                                        </h3>
                                        <p className="text-white/85 leading-relaxed whitespace-pre-line">
                                            {narratorDetails.bio_summary}
                                        </p>
                                    </div>
                                )}

                                {/* ─── Classical verdict: jarḥ wa taʿdīl ─── */}
                                {narratorDetails.is_prophet ? (
                                    <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4">
                                        <h3 className="text-base font-semibold text-amber-300 mb-2">
                                            Not subject to jarḥ wa taʿdīl
                                        </h3>
                                        <p className="text-white/75 text-sm leading-relaxed">
                                            As the source of the ḥadīth corpus, the Prophet ﷺ is not classified
                                            within the classical narrator-criticism framework. Biographical fields
                                            here document basic identity only.
                                        </p>
                                    </div>
                                ) : (narratorDetails.reliability_consensus || narratorDetails.bio_tadil || narratorDetails.bio_jarh) && (
                                    <div className="pt-2 border-t border-white/10">
                                        <div className="flex items-baseline justify-between mb-3">
                                            <h3 className="text-lg font-semibold text-cyan-300">
                                                Classical Verdict — Jarḥ wa Taʿdīl
                                            </h3>
                                            <div className="flex items-center gap-2">
                                                {narratorDetails.reliability_consensus && (
                                                    <ConsensusBadge verdict={narratorDetails.reliability_consensus} />
                                                )}
                                                {narratorDetails.reliability_disagreement && (
                                                    <span className="text-xs px-2 py-0.5 rounded bg-rose-500/15 text-rose-200 border border-rose-500/30">
                                                        contested
                                                    </span>
                                                )}
                                                {narratorDetails.is_companion && (
                                                    <span className="text-xs px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-200 border border-emerald-500/30">
                                                        ṣaḥābī
                                                    </span>
                                                )}
                                            </div>
                                        </div>

                                        {narratorDetails.is_companion && (
                                            <p className="text-xs text-white/55 mb-3 italic">
                                                Sunni rijāl literature does not subject Companions to individual taʿdīl/jarḥ
                                                under the doctrine of <span className="not-italic">ʿadālat al-ṣaḥāba</span>.
                                                Where critique exists in Imami or other traditions, it is noted below.
                                            </p>
                                        )}

                                        {narratorDetails.bio_tadil && (
                                            <div className="mb-4">
                                                <h4 className="text-sm font-semibold text-emerald-300 mb-2 uppercase tracking-wide">
                                                    Taʿdīl — testimonies of trust
                                                </h4>
                                                <p className="text-white/85 leading-loose" dir="auto">
                                                    {narratorDetails.bio_tadil}
                                                </p>
                                            </div>
                                        )}

                                        {narratorDetails.bio_jarh && (
                                            <div className="mb-2">
                                                <h4 className="text-sm font-semibold text-rose-300 mb-2 uppercase tracking-wide">
                                                    Jarḥ — testimonies of criticism
                                                </h4>
                                                <p className="text-white/85 leading-loose" dir="auto">
                                                    {narratorDetails.bio_jarh}
                                                </p>
                                            </div>
                                        )}

                                        {narratorDetails.bio_provenance && (
                                            <p className="text-xs text-white/40 mt-3 italic">
                                                Provenance status: {narratorDetails.bio_provenance === 'manual_phase_0'
                                                    ? 'uncited legacy manual seed; edition, volume, and page evidence is pending'
                                                    : narratorDetails.bio_provenance}
                                                {typeof narratorDetails.critic_quote_count === 'number' && narratorDetails.critic_quote_count > 0 && (
                                                    ` · ${narratorDetails.critic_quote_count} critic${narratorDetails.critic_quote_count === 1 ? '' : 's'}`
                                                )}
                                            </p>
                                        )}
                                    </div>
                                )}

                                {/* Legacy fields (only render if no Phase-0 bio_summary already covered them) */}
                                {narratorDetails.biographical_narrative && !narratorDetails.bio_summary && (
                                    <div>
                                        <h3 className="text-lg font-semibold text-cyan-300 mb-3">
                                            Biographical Narrative
                                        </h3>
                                        <p className="text-white/80 leading-relaxed">
                                            {narratorDetails.biographical_narrative}
                                        </p>
                                    </div>
                                )}

                                {narratorDetails.bio && !narratorDetails.bio_summary && (
                                    <div>
                                        <h3 className="text-lg font-semibold text-cyan-300 mb-3">
                                            Summary (legacy)
                                        </h3>
                                        <p className="text-white/80 leading-relaxed">
                                            {narratorDetails.bio}
                                        </p>
                                    </div>
                                )}

                                {/* Geographic Information */}
                                {narratorDetails.geographic_region && (
                                    <div className="pt-4 border-t border-white/10">
                                        <h3 className="text-lg font-semibold text-cyan-300 mb-3">
                                            Geographic Information
                                        </h3>
                                        <p className="text-white/80">
                                            <span className="font-semibold">Region:</span> {narratorDetails.geographic_region}
                                        </p>
                                    </div>
                                )}

                                {/* Life Dates */}
                                <div className="pt-4 border-t border-white/10">
                                    <h3 className="text-lg font-semibold text-cyan-300 mb-3">
                                        Life Timeline
                                    </h3>
                                    <div className="space-y-2 text-white/80">
                                        {(narratorDetails.birth_year_hijri !== undefined
                                            || narratorDetails.birth_year_gregorian !== undefined) ? (
                                            <div>
                                                <p>
                                                    <span className="font-semibold">Born:</span>
                                                    {narratorDetails.birth_year_hijri !== undefined ? (
                                                        <>
                                                            {' '}{narratorDetails.birth_year_hijri} AH
                                                            {narratorDetails.birth_year_gregorian !== undefined
                                                                && ` (${narratorDetails.birth_year_gregorian} CE)`}
                                                        </>
                                                    ) : (
                                                        <> {narratorDetails.birth_year_gregorian} CE</>
                                                    )}
                                                </p>
                                                <DateEvidence
                                                    sourceText={narratorDetails.birth_date_source_text}
                                                    provenance={narratorDetails.birth_date_provenance}
                                                    reviewStatus={narratorDetails.birth_date_review_status}
                                                />
                                            </div>
                                        ) : (
                                            <p>
                                                <span className="font-semibold">Born:</span>{' '}
                                                <span className="text-white/50">unknown</span>
                                            </p>
                                        )}
                                        {(deathYearHijri !== undefined || deathYearGregorian !== undefined) ? (
                                            <div>
                                                <p>
                                                    <span className="font-semibold">Died:</span>
                                                    {deathYearHijri !== undefined ? (
                                                        <>
                                                            {' '}{deathYearHijri} AH
                                                            {deathYearGregorian !== undefined
                                                                && ` (${deathYearGregorian} CE)`}
                                                        </>
                                                    ) : (
                                                        <> {deathYearGregorian} CE</>
                                                    )}
                                                </p>
                                                <DateEvidence
                                                    sourceText={narratorDetails.death_date_source_text}
                                                    provenance={narratorDetails.death_date_provenance}
                                                    reviewStatus={narratorDetails.death_date_review_status}
                                                />
                                            </div>
                                        ) : (
                                            <p>
                                                <span className="font-semibold">Died:</span>{' '}
                                                <span className="text-white/50">unknown</span>
                                            </p>
                                        )}
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    </div>

                    {/* Generation Timeline */}
                    <div>
                        <Card className="bg-white/5 border-white/10">
                            <CardContent className="pt-6">
                                <TabaqahTimeline currentTabaqah={narratorDetails.tabaqah} />
                            </CardContent>
                        </Card>
                    </div>
                </div>
            </TabsContent>

            {/* Historical Timeline Tab */}
            <TabsContent value="timeline">
                <Card className="bg-white/5 border-white/10">
                    <CardHeader>
                        <CardTitle className="text-white">Historical Timeline</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <HistoricalTimeline
                            events={historicalEvents}
                            narratorBirthYear={narratorDetails.birth_year_hijri}
                            narratorDeathYear={deathYearHijri}
                            onEventSelect={setSelectedEvent}
                            selectedEventId={selectedEvent}
                        />
                    </CardContent>
                </Card>
            </TabsContent>

            {/* Teacher-Student Network Tab */}
            <TabsContent value="network">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    {/* Teachers */}
                    {teachers.length > 0 && (
                        <Card className="bg-white/5 border-white/10">
                            <CardHeader>
                                <CardTitle className="text-white">Teachers</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="space-y-4">
                                    {teachers.map((teacher) => (
                                        <Link
                                            key={teacher.id}
                                            href={`/narrator/${teacher.id}`}
                                            className="block p-4 bg-white/5 hover:bg-white/10 border border-white/10 hover:border-cyan-500/50
                                                rounded-lg transition-all group"
                                        >
                                            <h4 className="font-semibold text-white group-hover:text-cyan-300 transition-colors">
                                                {teacher.name_english}
                                            </h4>
                                            <p lang="ar" dir="rtl" className="text-sm text-cyan-200/80 font-arabic mt-1 text-start">
                                                {teacher.name_arabic}
                                            </p>
                                            {teacher.relationship && (
                                                <p className="text-xs text-white/60 mt-2">{teacher.relationship}</p>
                                            )}
                                        </Link>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>
                    )}

                    {/* Students */}
                    {students.length > 0 && (
                        <Card className="bg-white/5 border-white/10">
                            <CardHeader>
                                <CardTitle className="text-white">Students</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="space-y-4">
                                    {students.map((student) => (
                                        <Link
                                            key={student.id}
                                            href={`/narrator/${student.id}`}
                                            className="block p-4 bg-white/5 hover:bg-white/10 border border-white/10 hover:border-cyan-500/50
                                                rounded-lg transition-all group"
                                        >
                                            <h4 className="font-semibold text-white group-hover:text-cyan-300 transition-colors">
                                                {student.name_english}
                                            </h4>
                                            <p lang="ar" dir="rtl" className="text-sm text-cyan-200/80 font-arabic mt-1 text-start">
                                                {student.name_arabic}
                                            </p>
                                            {student.relationship && (
                                                <p className="text-xs text-white/60 mt-2">{student.relationship}</p>
                                            )}
                                        </Link>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>
                    )}

                </div>
            </TabsContent>

            {/* Hadiths Tab */}
            <TabsContent value="hadiths">
                <Card className="bg-white/5 border-white/10">
                    <CardHeader>
                        <CardTitle className="text-white">
                            Hadiths Narrated
                            {` (${hadithCountLabel})`}
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        {narratorDetails.other_hadiths && narratorDetails.other_hadiths.length > 0 ? (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {narratorDetails.other_hadiths.map((hadith) => (
                                    <Link
                                        key={hadith.id}
                                        href={`/hadith/${hadith.id}`}
                                        className="block p-6 bg-white/5 hover:bg-white/10 border border-white/10 hover:border-cyan-500/50
                                            rounded-xl transition-all duration-300 group"
                                    >
                                        <h3 className="text-lg font-semibold text-white group-hover:text-cyan-300 transition-colors mb-2">
                                            {hadith.title}
                                        </h3>
                                        {hadith.primary_topic && (
                                            <p className="text-sm text-white/60 mb-3">{hadith.primary_topic}</p>
                                        )}
                                        {hadith.display_grade && (
                                            <div className="inline-block px-3 py-1 rounded-md bg-cyan-500/15 border border-cyan-500/25">
                                                <span className="text-xs text-cyan-200">
                                                    {hadith.display_grade}
                                                </span>
                                            </div>
                                        )}
                                    </Link>
                                ))}
                            </div>
                        ) : (
                            <div className="text-center py-12">
                                <p className="text-white/60">This narrator is not currently linked to any hadiths.</p>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </TabsContent>

            {/* Commentaries Tab */}
            <TabsContent value="commentaries">
                <CommentarySection commentaries={commentaries} narratorId={narratorDetails.id} />
            </TabsContent>

            {/* Tradition Connections Tab */}
            {traditionConnections && traditionConnections.traditions.length > 0 && (
                <TabsContent value="traditions">
                    <div className="space-y-6">
                        {/* Traditions this narrator is linked to */}
                        <Card className="bg-white/5 border-white/10">
                            <CardHeader>
                                <CardTitle className="text-white">Linked Religious Traditions</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="flex flex-wrap gap-4">
                                    {traditionConnections.traditions.map((t) => (
                                        <div key={t.id} className="p-4 bg-amber-900/20 border border-amber-500/20 rounded-lg min-w-48">
                                            <TraditionBadge tradition={t.name} size="md" />
                                            {t.name_arabic && (
                                                <p lang="ar" dir="rtl" className="text-slate-400 font-arabic mt-1 text-sm text-start">{t.name_arabic}</p>
                                            )}
                                            {t.description && (
                                                <p className="text-xs text-slate-400 mt-2 leading-relaxed">{t.description}</p>
                                            )}
                                        </div>
                                    ))}
                                </div>
                                <p className="text-xs text-slate-400 mt-4">
                                    This narrator has been identified as a transmitter of narratives from the above traditions,
                                    either through conversion, scholarly contact, or regional cultural exchange.
                                </p>
                            </CardContent>
                        </Card>

                        {/* Hadiths with parallels via this narrator */}
                        {traditionConnections.hadiths_with_parallels.length > 0 && (
                            <Card className="bg-white/5 border-white/10">
                                <CardHeader>
                                    <CardTitle className="text-white">Hadiths with Cross-Cultural Parallels</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <p className="text-sm text-slate-400 mb-4">
                                        Hadiths in which this narrator appears in the chain that have documented cross-cultural parallels:
                                    </p>
                                    <div className="space-y-3">
                                        {traditionConnections.hadiths_with_parallels.map((item, i) => (
                                            <Link
                                                key={i}
                                                href={`/hadith/${item.hadith.id}`}
                                                className="block p-4 bg-white/5 hover:bg-white/10 border border-white/10 hover:border-amber-500/50 rounded-lg transition-all group"
                                            >
                                                <div className="flex items-start justify-between gap-3">
                                                    <div className="flex-1">
                                                        <h4 className="font-semibold text-white group-hover:text-amber-300 transition-colors mb-2">
                                                            {item.hadith.title}
                                                        </h4>
                                                        <div className="flex flex-wrap gap-2">
                                                            <TraditionBadge tradition={item.tradition.name} />
                                                            <ParallelTypeBadge type={item.parallel.parallel_type} />
                                                            <IsraIliyyatBadge status={item.parallel.isra_iliyyat_status} />
                                                        </div>
                                                        <p className="text-xs text-slate-400 mt-1.5">
                                                            ↔ {item.source_text.title}
                                                            {item.source_text.canonical_reference && ` · ${item.source_text.canonical_reference}`}
                                                        </p>
                                                    </div>
                                                    {item.hadith.display_grade && (
                                                        <span className="text-xs text-slate-300 bg-slate-800 px-2 py-1 rounded">
                                                            {item.hadith.display_grade}
                                                        </span>
                                                    )}
                                                </div>
                                            </Link>
                                        ))}
                                    </div>
                                </CardContent>
                            </Card>
                        )}
                    </div>
                </TabsContent>
            )}
        </Tabs>
    );
}
