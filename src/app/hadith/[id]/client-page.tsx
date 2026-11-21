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

export function HadithClientPage({
    hadith,
    nodes,
    edges,
    chainHealthScore,
    parallels = [],
    tracesToProphet = false,
}: HadithClientPageProps) {
    const gradeColor = GRADE_COLORS[hadith.display_grade as string] || 'bg-gray-500/20 text-gray-400 border-gray-500/30';

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
    const linkedNodes = nodes.filter((node) => Boolean(node.name_arabic?.trim() || node.name_english?.trim()));
    const linkedNarratorCount = new Set(linkedNodes.map((node) => node.id)).size;
    const branchCount = new Set(linkedNodes.map((node) => node.chain_id || 'linked-chain')).size;
    const linkedSummary = linkedNarratorCount > 0
        ? `${linkedNarratorCount} linked narrator ${linkedNarratorCount === 1 ? 'identity' : 'identities'}${branchCount > 1 ? ` across ${branchCount} isnad branches` : ''}`
        : 'identities unresolved';

    return (
        <div className="min-h-screen bg-slate-950 text-white">
            {/* ── Header ── */}
            <header className="border-b border-slate-800/60 bg-slate-950/80 backdrop-blur-sm sticky top-0 z-10">
                <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4 px-6 py-4">
                    <div>
                        <h1 className="text-2xl font-bold">
                            {hadith.title || <span className="text-slate-400 italic">Untitled</span>}
                        </h1>
                        <p className="text-sm text-slate-400 mt-0.5">
                            {hadith.primary_topic || <span className="text-slate-400 italic">No topic</span>}
                        </p>
                    </div>
                    <div className="flex items-center gap-2">
                        {tracesToProphet && (
                            <Badge className="bg-amber-500/20 text-amber-400 border-amber-500/30">
                                Marfu&apos;
                            </Badge>
                        )}
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
                        {sourceSanadText
                            ? `Source sanad shown verbatim · ${linkedSummary}`
                            : linkedNarratorCount > 0
                                ? linkedSummary
                                : 'Transmission chain'}
                    </p>
                </div>
                <IsnadChain
                    nodes={nodes}
                    edges={edges}
                    hadithTextArabic={hadithTextArabic}
                    hadithTextEnglish={hadithTextEnglish}
                    hadithTextLabel={hadithTextLabel}
                    sourceSanadText={sourceSanadText}
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

                    {/* Sanad (isnad text) + Matn from v2 :Hadith node — direct render */}
                    {(sourceSanadText || hadithTextArabic || hadithTextEnglish) && (
                        <Card className="bg-slate-900/50 border-slate-800 p-6 md:col-span-2">
                            <h2 className="text-lg font-semibold mb-4 text-white">Text and source record</h2>
                            <div className="space-y-5">
                                {sourceSanadText && (
                                    <div>
                                        <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-2">
                                            Source sanad (verbatim)
                                        </h3>
                                        <p
                                            className="text-base leading-loose font-[var(--font-amiri)] text-amber-100"
                                            dir="auto"
                                        >
                                            {sourceSanadText}
                                        </p>
                                    </div>
                                )}
                                {hadithTextArabic && (
                                    <div>
                                        <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-2">
                                            {hasArabicMatn ? 'Matn — Arabic' : 'Source text — Arabic (unsegmented)'}
                                        </h3>
                                        <p
                                            className="text-lg leading-loose font-[var(--font-amiri)] text-amber-50"
                                            dir="rtl"
                                            lang="ar"
                                        >
                                            {hadithTextArabic}
                                        </p>
                                    </div>
                                )}
                                {hadithTextEnglish && (
                                    <div>
                                        <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-2">
                                            {hasEnglishMatn ? 'Matn — English' : 'Source text — English (unsegmented)'}
                                        </h3>
                                        <p className="text-base leading-relaxed text-slate-200">
                                            {hadithTextEnglish}
                                        </p>
                                    </div>
                                )}
                                {/* Metadata strip */}
                                <div className="pt-3 border-t border-slate-800/60 flex flex-wrap gap-x-6 gap-y-1 text-xs text-slate-400">
                                    {hadith.source && <span><span className="text-slate-500">Source:</span> {hadith.source}</span>}
                                    {hadith.hadith_no && <span><span className="text-slate-500">No:</span> {hadith.hadith_no}</span>}
                                    {hadith.volume && <span><span className="text-slate-500">Volume:</span> {hadith.volume}</span>}
                                    {hadith.chapter && <span><span className="text-slate-500">Chapter:</span> {hadith.chapter}</span>}
                                    {hadith.tradition && <span><span className="text-slate-500">Tradition:</span> {displayHadithTradition(hadith.tradition)}</span>}
                                    {hadith.chain_type && <span><span className="text-slate-500">Chain type:</span> {hadith.chain_type}</span>}
                                    {hadith.attributed_to && <span><span className="text-slate-500">Attributed to:</span> {hadith.attributed_to}</span>}
                                </div>
                            </div>
                        </Card>
                    )}

                    {/* Legacy MatnVariation tabs — only when real :MatnVariation nodes exist
                        (synthesized single-variation from getHadithById is filtered out via source check). */}
                    {hadith.variations && hadith.variations.length > 0 && hadith.variations.some((v) => v.source !== 'hadith_node') && (
                        <Card className="bg-slate-900/50 border-slate-800 p-6 md:col-span-2">
                            <h2 className="text-lg font-semibold mb-4 text-white">Text Variations (Matn)</h2>
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
                                    parallel={p}
                                    tradition={p.tradition}
                                    sourceText={p.source_text}
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
