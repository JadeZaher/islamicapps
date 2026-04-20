'use client';

import { IsnadChain } from './components/IsnadChain';
import { GradingPanel } from './components/GradingPanel';
import { CrossCulturalParallelCard } from '@/components/CrossCulturalParallelCard';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import Link from 'next/link';
import type { HadithClientPageProps } from './types';

const GRADE_COLORS: Record<string, string> = {
    SAHIH: 'bg-green-500/20 text-green-400 border-green-500/30',
    HASAN: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    DAIF: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
    MAWDU: 'bg-red-500/20 text-red-400 border-red-500/30',
};

export function HadithClientPage({
    hadith,
    nodes,
    edges,
    chainHealthScore,
    parallels = [],
}: HadithClientPageProps) {
    const gradeColor = GRADE_COLORS[hadith.display_grade as string] || 'bg-gray-500/20 text-gray-400 border-gray-500/30';

    const hadithTextArabic = hadith.variations?.[0]?.text_arabic ?? hadith.text_arabic ?? null;
    const hadithTextEnglish = hadith.variations?.[0]?.text_english ?? hadith.text_english ?? null;
    const chainTextArabic = hadith.isnad_arabic ?? hadith.chain_text_arabic ?? null;

    return (
        <div className="min-h-screen bg-slate-950 text-white">
            {/* ── Header ── */}
            <header className="border-b border-slate-800/60 bg-slate-950/80 backdrop-blur-sm sticky top-0 z-10">
                <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold">
                            {hadith.title || <span className="text-slate-400 italic">Untitled</span>}
                        </h1>
                        <p className="text-sm text-slate-400 mt-0.5">
                            {hadith.primary_topic || <span className="text-slate-400 italic">No topic</span>}
                        </p>
                    </div>
                    <div className="flex items-center gap-2">
                        <Badge className={gradeColor}>
                            {hadith.display_grade || 'Ungraded'}
                        </Badge>
                        {hadith.transmission_type && (
                            <Badge className={hadith.transmission_type === 'MUTAWATIR'
                                ? 'bg-amber-500/20 text-amber-400 border-amber-500/30'
                                : 'bg-blue-500/20 text-blue-400 border-blue-500/30'
                            }>
                                {hadith.transmission_type}
                            </Badge>
                        )}
                    </div>
                </div>
            </header>

            {/* ── Full-width Isnad Chain ── */}
            <section className="w-full border-b border-slate-800/40">
                <div className="max-w-7xl mx-auto px-6 pt-2 pb-2">
                    <p className="text-xs text-slate-400 uppercase tracking-widest">
                        Isnad Chain &middot; Click a narrator to view details
                    </p>
                </div>
                <IsnadChain
                    nodes={nodes as any}
                    edges={edges as any}
                    hadithTextArabic={hadithTextArabic}
                    hadithTextEnglish={hadithTextEnglish}
                    chainTextArabic={chainTextArabic}
                />
            </section>

            {/* ── Details section ── */}
            <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">
                {/* Grading row */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <Card className="bg-slate-900/50 border-slate-800 p-6 md:col-span-1">
                        <GradingPanel
                            autoCalculatedGrade={hadith.auto_calculated_grade as string}
                            displayGrade={hadith.display_grade as string}
                            transmissionType={hadith.transmission_type as string}
                            chainHealthScore={chainHealthScore}
                        />
                    </Card>

                    {/* Matn Variations */}
                    {hadith.variations && hadith.variations.length > 0 && (
                        <Card className="bg-slate-900/50 border-slate-800 p-6 md:col-span-2">
                            <h2 className="text-lg font-semibold mb-4 text-white">Text Variations (Matn)</h2>
                            <Tabs defaultValue="0" className="w-full">
                                <TabsList className="mb-4">
                                    {hadith.variations.map((v: any, i: number) => (
                                        <TabsTrigger key={i} value={i.toString()}>
                                            {v.source_book}
                                        </TabsTrigger>
                                    ))}
                                </TabsList>
                                {hadith.variations.map((v: any, i: number) => (
                                    <TabsContent key={i} value={i.toString()} className="space-y-4">
                                        <div>
                                            <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-2">Arabic</h3>
                                            <p className="text-lg leading-loose font-[var(--font-amiri)] text-amber-100" dir="rtl">{v.text_arabic}</p>
                                        </div>
                                        <div>
                                            <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-2">English Translation</h3>
                                            <p className="text-base leading-relaxed text-slate-300">{v.text_english}</p>
                                        </div>
                                    </TabsContent>
                                ))}
                            </Tabs>
                        </Card>
                    )}
                </div>

                {/* Comparative Parallels */}
                <div>
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-xl font-semibold">
                            Comparative Parallels
                            {parallels.length > 0 && (
                                <span className="ml-2 text-sm font-normal text-slate-400">({parallels.length})</span>
                            )}
                        </h2>
                        <Link href="/comparative" className="text-sm text-amber-400 hover:text-amber-300 transition-colors">
                            Browse all &rarr;
                        </Link>
                    </div>
                    {parallels.length > 0 ? (
                        <div className="space-y-4">
                            {parallels.map((p) => (
                                <CrossCulturalParallelCard
                                    key={p.id}
                                    parallel={p as any}
                                    tradition={p.tradition}
                                    sourceText={p.source_text as any}
                                    motifTags={p.motif_tags}
                                />
                            ))}
                        </div>
                    ) : (
                        <Card className="bg-slate-900/30 border-slate-800 border-dashed p-8">
                            <p className="text-center text-slate-400 text-sm">
                                No cross-cultural parallels recorded for this hadith.{' '}
                                <Link href="/admin/comparative" className="text-amber-500 hover:text-amber-400">
                                    Add one in the admin &rarr;
                                </Link>
                            </p>
                        </Card>
                    )}
                </div>
            </div>
        </div>
    );
}
