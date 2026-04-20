'use client';

import { useState } from 'react';
import Link from 'next/link';
import { TabaqahTimeline } from '@/components/TabaqahTimeline';
import { HistoricalTimeline } from '@/components/HistoricalTimeline';
import { CommentarySection } from '@/components/CommentarySection';
import { TraditionBadge, ParallelTypeBadge, IsraIliyyatBadge } from '@/components/TraditionBadge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface NarratorClientPageProps {
    narratorDetails: {
        id: string;
        name_english: string;
        name_arabic: string;
        reliability: 'THIQA' | 'SADUQ' | 'DAIF' | 'MAJHUL' | 'KADHAB';
        tabaqah: string;
        birth_year_hijri?: number;
        birth_year_gregorian?: number;
        death_year_hijri?: number;
        death_year_gregorian?: number;
        bio?: string;
        biographical_narrative?: string;
        geographic_region?: string;
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
    historicalEvents?: Array<{
        id: string;
        title: string;
        description: string;
        year_hijri: number;
        year_gregorian: number;
        category: 'POLITICAL' | 'SCIENTIFIC' | 'CULTURAL' | 'RELIGIOUS' | 'OTHER';
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

export default function NarratorClientPage({
    narratorDetails,
    narratorNetwork,
    commentaries = [],
    historicalEvents = [],
    traditionConnections,
}: NarratorClientPageProps) {
    const [selectedEvent, setSelectedEvent] = useState<string | null>(null);

    return (
        <Tabs defaultValue="biography" className="w-full">
            <div className="mb-8 bg-white/5 backdrop-blur-lg rounded-2xl p-6 border border-white/10 overflow-x-auto">
                <TabsList className="w-full justify-start gap-2 bg-transparent h-auto p-0">
                    <TabsTrigger
                        value="biography"
                        className="data-[state=active]:bg-cyan-700 data-[state=active]:text-white text-white/70 px-4 py-2 rounded-lg border border-white/20 data-[state=active]:border-cyan-600"
                    >
                        Biography
                    </TabsTrigger>
                    <TabsTrigger
                        value="timeline"
                        className="data-[state=active]:bg-cyan-700 data-[state=active]:text-white text-white/70 px-4 py-2 rounded-lg border border-white/20 data-[state=active]:border-cyan-600"
                    >
                        Historical Timeline
                    </TabsTrigger>
                    <TabsTrigger
                        value="network"
                        className="data-[state=active]:bg-cyan-700 data-[state=active]:text-white text-white/70 px-4 py-2 rounded-lg border border-white/20 data-[state=active]:border-cyan-600"
                    >
                        Teacher-Student Network
                    </TabsTrigger>
                    <TabsTrigger
                        value="hadiths"
                        className="data-[state=active]:bg-cyan-700 data-[state=active]:text-white text-white/70 px-4 py-2 rounded-lg border border-white/20 data-[state=active]:border-cyan-600"
                    >
                        Hadiths
                    </TabsTrigger>
                    <TabsTrigger
                        value="commentaries"
                        className="data-[state=active]:bg-cyan-700 data-[state=active]:text-white text-white/70 px-4 py-2 rounded-lg border border-white/20 data-[state=active]:border-cyan-600"
                    >
                        Commentaries
                    </TabsTrigger>
                    {traditionConnections && traditionConnections.traditions.length > 0 && (
                        <TabsTrigger
                            value="traditions"
                            className="data-[state=active]:bg-amber-600 data-[state=active]:text-white text-white/70 px-4 py-2 rounded-lg border border-white/20 data-[state=active]:border-amber-500"
                        >
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
                                {narratorDetails.biographical_narrative && (
                                    <div>
                                        <h3 className="text-lg font-semibold text-cyan-300 mb-3">
                                            Biographical Narrative
                                        </h3>
                                        <p className="text-white/80 leading-relaxed">
                                            {narratorDetails.biographical_narrative}
                                        </p>
                                    </div>
                                )}

                                {narratorDetails.bio && (
                                    <div>
                                        <h3 className="text-lg font-semibold text-cyan-300 mb-3">
                                            Summary
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
                                        {narratorDetails.birth_year_hijri && (
                                            <p>
                                                <span className="font-semibold">Born:</span> {narratorDetails.birth_year_hijri} AH
                                                {narratorDetails.birth_year_gregorian && (
                                                    <span> ({narratorDetails.birth_year_gregorian} CE)</span>
                                                )}
                                            </p>
                                        )}
                                        {narratorDetails.death_year_hijri && (
                                            <p>
                                                <span className="font-semibold">Died:</span> {narratorDetails.death_year_hijri} AH
                                                {narratorDetails.death_year_gregorian && (
                                                    <span> ({narratorDetails.death_year_gregorian} CE)</span>
                                                )}
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
                                <TabaqahTimeline currentTabaqah={narratorDetails.tabaqah as any} />
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
                        {historicalEvents && historicalEvents.length > 0 ? (
                            <HistoricalTimeline
                                events={historicalEvents}
                                narratorBirthYear={narratorDetails.birth_year_hijri}
                                narratorDeathYear={narratorDetails.death_year_hijri}
                                onEventSelect={setSelectedEvent}
                                selectedEventId={selectedEvent}
                            />
                        ) : (
                            <div className="text-center py-12">
                                <p className="text-white/60">No historical events available for this period.</p>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </TabsContent>

            {/* Teacher-Student Network Tab */}
            <TabsContent value="network">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    {/* Teachers */}
                    {narratorNetwork?.teachers && narratorNetwork.teachers.length > 0 && (
                        <Card className="bg-white/5 border-white/10">
                            <CardHeader>
                                <CardTitle className="text-white">Teachers</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="space-y-4">
                                    {narratorNetwork.teachers.map((teacher) => (
                                        <Link
                                            key={teacher.id}
                                            href={`/narrator/${teacher.id}`}
                                            className="block p-4 bg-white/5 hover:bg-white/10 border border-white/10 hover:border-cyan-500/50
                                                rounded-lg transition-all group"
                                        >
                                            <h4 className="font-semibold text-white group-hover:text-cyan-300 transition-colors">
                                                {teacher.name_english}
                                            </h4>
                                            <p className="text-sm text-cyan-200/80 font-arabic mt-1">
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
                    {narratorNetwork?.students && narratorNetwork.students.length > 0 && (
                        <Card className="bg-white/5 border-white/10">
                            <CardHeader>
                                <CardTitle className="text-white">Students</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="space-y-4">
                                    {narratorNetwork.students.map((student) => (
                                        <Link
                                            key={student.id}
                                            href={`/narrator/${student.id}`}
                                            className="block p-4 bg-white/5 hover:bg-white/10 border border-white/10 hover:border-cyan-500/50
                                                rounded-lg transition-all group"
                                        >
                                            <h4 className="font-semibold text-white group-hover:text-cyan-300 transition-colors">
                                                {student.name_english}
                                            </h4>
                                            <p className="text-sm text-cyan-200/80 font-arabic mt-1">
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

                    {!narratorNetwork?.teachers && !narratorNetwork?.students && (
                        <div className="col-span-2 text-center py-12">
                            <p className="text-white/60">No network information available for this narrator.</p>
                        </div>
                    )}
                </div>
            </TabsContent>

            {/* Hadiths Tab */}
            <TabsContent value="hadiths">
                <Card className="bg-white/5 border-white/10">
                    <CardHeader>
                        <CardTitle className="text-white">
                            Hadiths Narrated
                            {narratorDetails.other_hadiths && ` (${narratorDetails.other_hadiths.length})`}
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
                                                <p className="text-slate-400 font-arabic mt-1 text-sm">{t.name_arabic}</p>
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
