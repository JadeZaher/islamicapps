'use client';

import { IsnadChain } from './components/IsnadChain';
import { GradingPanel } from './components/GradingPanel';
import { CrossCulturalParallelCard } from '@/components/CrossCulturalParallelCard';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { displayHadithTradition } from '@/lib/constants/traditions';
import Link from 'next/link';
import type { HadithClientPageProps } from './types';

const GRADE_COLORS: Record<string, string> = {
    SAHIH: 'bg-green-500/20 text-green-400 border-green-500/30',
    HASAN: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    DAIF: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
    MAWDU: 'bg-red-500/20 text-red-400 border-red-500/30',
};
const NEUTRAL_GRADE = 'bg-gray-500/20 text-gray-300 border-gray-500/30';

export function HadithClientPage({
    hadith,
    nodes,
    edges,
    chainHealthScore,
    parallels = [],
    tracesToProphet = false,
}: HadithClientPageProps) {
    // Prefer the v2 fields; legacy aliases remain a fallback for the live graph.
    const hasArabicMatn = Boolean(hadith.matn_ar?.trim());
    const hasEnglishMatn = Boolean(hadith.matn_en?.trim());
    const hadithTextArabic = hasArabicMatn ? hadith.matn_ar : hadith.text_ar ?? hadith.text_arabic ?? hadith.variations?.[0]?.text_arabic ?? null;
    const hadithTextEnglish = hasEnglishMatn ? hadith.matn_en : hadith.text_en ?? hadith.text_english ?? hadith.variations?.[0]?.text_english ?? null;
    const displayedTextKinds = [
        hadithTextArabic ? hasArabicMatn : null,
        hadithTextEnglish ? hasEnglishMatn : null,
    ].filter((kind): kind is boolean => kind !== null);
    const hadithTextLabel = displayedTextKinds.every(Boolean)
        ? 'Hadith matn'
        : displayedTextKinds.some(Boolean)
            ? 'Hadith text (mixed segmentation)'
            : 'Source text (unsegmented)';
    const sourceSanadText = hadith.sanad ?? hadith.isnad_arabic ?? hadith.chain_text_arabic ?? null;
    const hasChain = nodes.some((node) => Boolean(node.name_arabic?.trim() || node.name_english?.trim()));
    const showChainSection = Boolean(sourceSanadText?.trim()) || hasChain;
    const hasGrading = Boolean(
        hadith.display_grade || hadith.auto_calculated_grade || typeof chainHealthScore === 'number',
    );
    const heading = hadith.title?.trim()
        || [hadith.source, hadith.hadith_no].filter(Boolean).join(' ')
        || 'Hadith';
    const hasMetadata = Boolean(
        hadith.source || hadith.hadith_no || hadith.volume || hadith.chapter || hadith.tradition || hadith.chain_type || hadith.attributed_to,
    );

    return (
        <div className="min-h-screen bg-slate-950 text-white">
            {/* ── Header ── */}
            <header className="border-b border-slate-800/60 bg-slate-950/80 backdrop-blur-sm sticky top-0 z-10">
                <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4 px-6 py-4">
                    <div>
                        <h1 className="text-2xl font-bold">{heading}</h1>
                        {hadith.primary_topic && (
                            <p className="text-sm text-slate-400 mt-0.5">{hadith.primary_topic}</p>
                        )}
                    </div>
                    <div className="flex items-center gap-2">
                        {tracesToProphet && (
                            <Badge className="bg-amber-500/20 text-amber-400 border-amber-500/30">
                                Marfu&apos;
                            </Badge>
                        )}
                        {hadith.display_grade && (
                            <Badge className={GRADE_COLORS[hadith.display_grade] ?? NEUTRAL_GRADE}>
                                {hadith.display_grade}
                            </Badge>
                        )}
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

            {showChainSection && (
                <section className="w-full border-b border-slate-800/40">
                    <IsnadChain nodes={nodes} edges={edges} sourceSanadText={sourceSanadText} />
                </section>
            )}

            {/* ── Details section ── */}
            <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {hasGrading && (
                        <Card className="bg-slate-900/50 border-slate-800 p-6 md:col-span-1 self-start">
                            <GradingPanel
                                autoCalculatedGrade={hadith.auto_calculated_grade}
                                displayGrade={hadith.display_grade}
                                chainHealthScore={chainHealthScore}
                            />
                        </Card>
                    )}

                    {(hadithTextArabic || hadithTextEnglish || hasMetadata) && (
                        <Card className={`bg-slate-900/50 border-slate-800 p-6 ${hasGrading ? 'md:col-span-2' : 'md:col-span-3'}`}>
                            <h2 className="text-lg font-semibold mb-4 text-white">{hadithTextLabel}</h2>
                            <div className="space-y-5">
                                {hadithTextArabic && (
                                    <p className="text-xl font-arabic text-amber-50" dir="rtl" lang="ar">
                                        {hadithTextArabic}
                                    </p>
                                )}
                                {hadithTextEnglish && (
                                    <p className="text-base leading-relaxed text-slate-200">
                                        {hadithTextEnglish}
                                    </p>
                                )}
                                {hasMetadata && (
                                    <dl className="pt-3 border-t border-slate-800/60 flex flex-wrap gap-x-6 gap-y-1 text-xs text-slate-400">
                                        {hadith.source && <div className="flex gap-1"><dt className="text-slate-500">Source:</dt><dd>{hadith.source}</dd></div>}
                                        {hadith.hadith_no && <div className="flex gap-1"><dt className="text-slate-500">No:</dt><dd>{hadith.hadith_no}</dd></div>}
                                        {hadith.volume && <div className="flex gap-1"><dt className="text-slate-500">Volume:</dt><dd>{hadith.volume}</dd></div>}
                                        {hadith.chapter && <div className="flex gap-1"><dt className="text-slate-500">Chapter:</dt><dd>{hadith.chapter}</dd></div>}
                                        {hadith.tradition && <div className="flex gap-1"><dt className="text-slate-500">Tradition:</dt><dd>{displayHadithTradition(hadith.tradition)}</dd></div>}
                                        {hadith.chain_type && <div className="flex gap-1"><dt className="text-slate-500">Chain type:</dt><dd>{hadith.chain_type}</dd></div>}
                                        {hadith.attributed_to && <div className="flex gap-1"><dt className="text-slate-500">Attributed to:</dt><dd>{hadith.attributed_to}</dd></div>}
                                    </dl>
                                )}
                            </div>
                        </Card>
                    )}

                    {/* Legacy MatnVariation tabs — only when real :MatnVariation nodes exist
                        (synthesized single-variation from getHadithById is filtered out via source check). */}
                    {hadith.variations && hadith.variations.length > 0 && hadith.variations.some((v) => v.source !== 'hadith_node') && (
                        <Card className="bg-slate-900/50 border-slate-800 p-6 md:col-span-2">
                            <h2 className="text-lg font-semibold mb-4 text-white">Variant texts</h2>
                            <Tabs defaultValue="0" className="w-full">
                                <TabsList className="mb-4">
                                    {hadith.variations.map((v, i) => (
                                        <TabsTrigger key={i} value={i.toString()}>
                                            {v.source_book}
                                        </TabsTrigger>
                                    ))}
                                </TabsList>
                                {hadith.variations.map((v, i) => (
                                    <TabsContent key={i} value={i.toString()} className="space-y-4">
                                        <div>
                                            <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-2">Arabic</h3>
                                            <p className="text-lg font-arabic text-amber-100" dir="rtl" lang="ar">{v.text_arabic}</p>
                                        </div>
                                        <div>
                                            <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-2">English</h3>
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
                            Parallels
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
                                    parallel={p}
                                    tradition={p.tradition}
                                    sourceText={p.source_text}
                                    motifTags={p.motif_tags}
                                />
                            ))}
                        </div>
                    ) : (
                        <p className="text-sm text-slate-400" role="status">No parallels recorded.</p>
                    )}
                </div>
            </div>
        </div>
    );
}
