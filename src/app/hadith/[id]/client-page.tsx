'use client';

import Link from 'next/link';

import { ArabicText } from '@/components/ArabicText';
import { CrossCulturalParallelCard } from '@/components/CrossCulturalParallelCard';
import { BilingualTitle } from '@/components/NarratorName';
import { TraditionBadge } from '@/components/TraditionBadge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { IsnadChain } from './components/IsnadChain';
import { GradingPanel } from './components/GradingPanel';
import { Assessments } from './components/Assessments';
import { ReportFamilySection } from './components/family/ReportFamilySection';
import { ownMatn } from './matn';
import { reportNumber, reportReference } from '@/lib/citation/reference';
import type { HadithClientPageProps } from './types';

/** Section heading used for every block on the page: one size, one weight. */
function SectionHeading({ id, children }: { id: string; children: React.ReactNode }) {
    return (
        <h2 id={id} className="mb-4 text-xs font-semibold uppercase tracking-[0.14em] text-slate-400">
            {children}
        </h2>
    );
}

/**
 * Hadith reading page: one column, isnad before matn as in the sources, English secondary.
 * Computed signals (chain score, inferred marfūʿ) are deliberately not rendered; see src/components/AGENTS.md §Hadith detail.
 */
export function HadithClientPage({ hadith, chain, parallels = [], family = null, timeline = null }: HadithClientPageProps) {
    // Prefer the v2 fields; legacy aliases remain a fallback for the live graph.
    const fullArabic = hadith.text_ar ?? hadith.text_arabic ?? hadith.variations?.[0]?.text_arabic ?? null;
    // A stored matn is shown only when it is this report's own (another report's matn was once attached upstream).
    const arabicMatn = ownMatn(hadith.matn_ar, fullArabic);
    const hasArabicMatn = Boolean(arabicMatn);
    const hasEnglishMatn = Boolean(hadith.matn_en?.trim());
    const arabicText = arabicMatn ?? fullArabic;
    const englishText = hasEnglishMatn ? hadith.matn_en : hadith.text_en ?? hadith.text_english ?? hadith.variations?.[0]?.text_english ?? null;
    // When only one side is segmented, say so: the English may carry the chain the Arabic omits.
    const segmentationDiffers = Boolean(arabicText && englishText) && hasArabicMatn !== hasEnglishMatn;
    const isSegmented = hasArabicMatn || hasEnglishMatn;

    // The written sanad is shown above the matn only when the Arabic below is the matn alone; otherwise the full text
    // below already carries the chain, and it is shown once.
    const writtenSanad = hadith.sanad ?? hadith.isnad_arabic ?? hadith.chain_text_arabic ?? null;
    const sourceSanadText = hasArabicMatn ? writtenSanad : null;
    const hasChain = (chain?.nodes.length ?? 0) > 0;
    const showChain = Boolean(sourceSanadText?.trim()) || hasChain;

    // Thaqalayn's stored hadith_no is the chapter number: the report's own number comes from the provider URL.
    const referenceFields = {
        id: hadith.id,
        hadithNo: hadith.hadith_no,
        url: hadith.url ?? null,
        volume: hadith.volume ?? null,
        pageRef: hadith.page_ref ?? null,
        bookNumber: null,
    };
    const number = reportNumber(referenceFields);
    const reference = [hadith.source, number].filter(Boolean).join(' ');
    const heading = reference || hadith.title?.trim() || 'Hadith';
    const chapter = hadith.chapter?.trim() || hadith.title?.trim() || '';
    const topic = hadith.primary_topic?.trim();
    const showTopic = Boolean(topic) && topic !== chapter;

    const realVariations = (hadith.variations ?? []).filter((variation) => variation.source !== 'hadith_node');

    const referenceRows: Array<[string, React.ReactNode]> = [
        ['Source', hadith.source],
        ['Reference', reportReference(referenceFields)],
        ['Volume', hadith.volume],
        ['Chain type', hadith.chain_type],
        ['Attributed to', hadith.attributed_to],
    ].filter((row): row is [string, string] => Boolean(row[1]));

    return (
        <main className="mx-auto max-w-3xl px-6 pb-20 pt-10 text-slate-100">
            <header className="border-b border-slate-800 pb-6">
                <div className="flex flex-wrap items-center gap-2 text-sm text-slate-400">
                    {hadith.tradition && <TraditionBadge tradition={hadith.tradition} />}
                    {hadith.display_grade || hadith.transmission_type ? (
                        <GradingPanel displayGrade={hadith.display_grade} transmissionType={hadith.transmission_type} />
                    ) : null}
                </div>
                <h1 className="mt-3 text-3xl font-semibold">{heading}</h1>
                {chapter && chapter !== heading && (
                    <p className="mt-2 text-base text-slate-300">
                        <BilingualTitle text={chapter} />
                    </p>
                )}
                {showTopic && <p className="mt-1 text-sm text-slate-400">{topic}</p>}
            </header>

            {showChain && (
                <section aria-labelledby="isnad-heading" className="border-b border-slate-800 py-8">
                    <SectionHeading id="isnad-heading">Isnad · chain of transmission</SectionHeading>
                    <IsnadChain chain={chain} sourceSanadText={sourceSanadText} />
                </section>
            )}

            {/* The chain on a time axis: recorded lifespans or generations, eras, and gaps between consecutive narrators. */}
            {timeline}

            {(arabicText || englishText) && (
                <section aria-labelledby="matn-heading" className="py-8">
                    <SectionHeading id="matn-heading">{isSegmented ? 'Matn · report text' : 'Text as in the source'}</SectionHeading>
                    {arabicText && (
                        <ArabicText as="p" className="whitespace-pre-line text-2xl leading-[2.1] text-slate-50">
                            {arabicText}
                        </ArabicText>
                    )}
                    {englishText && (
                        <div className={arabicText ? 'mt-8 border-t border-slate-800/70 pt-6' : ''}>
                            <p className="mb-2 text-xs text-slate-500">
                                English translation, not yet reviewed
                                {segmentationDiffers && ' · includes the chain'}
                            </p>
                            <p className="whitespace-pre-line text-base leading-relaxed text-slate-300">{englishText}</p>
                        </div>
                    )}
                </section>
            )}

            {family && (
                <section aria-labelledby="family-heading" className="border-t border-slate-800 py-8">
                    <SectionHeading id="family-heading">Tellings of this report</SectionHeading>
                    <ReportFamilySection family={family} hadithId={hadith.id} />
                </section>
            )}

            {hadith.assessments && hadith.assessments.length > 0 && (
                <section aria-labelledby="assessments-heading" className="border-t border-slate-800 py-8">
                    <SectionHeading id="assessments-heading">Assessments by tradition</SectionHeading>
                    <Assessments groups={hadith.assessments} hadithId={hadith.id} />
                </section>
            )}

            {realVariations.length > 0 && (
                <section aria-labelledby="variants-heading" className="border-t border-slate-800 py-8">
                    <SectionHeading id="variants-heading">Variant texts</SectionHeading>
                    <Tabs defaultValue="0" className="w-full">
                        <TabsList className="mb-4">
                            {realVariations.map((variation, index) => (
                                <TabsTrigger key={index} value={index.toString()}>
                                    {variation.source_book || `Variant ${index + 1}`}
                                </TabsTrigger>
                            ))}
                        </TabsList>
                        {realVariations.map((variation, index) => (
                            <TabsContent key={index} value={index.toString()} className="space-y-6">
                                {variation.text_arabic && (
                                    <ArabicText as="p" className="text-xl text-slate-100">{variation.text_arabic}</ArabicText>
                                )}
                                {variation.text_english && (
                                    <p className="text-base leading-relaxed text-slate-300">{variation.text_english}</p>
                                )}
                            </TabsContent>
                        ))}
                    </Tabs>
                </section>
            )}

            {parallels.length > 0 && (
                <section aria-labelledby="parallels-heading" className="border-t border-slate-800 py-8">
                    <div className="mb-4 flex items-baseline justify-between">
                        <SectionHeading id="parallels-heading">Parallels in other traditions ({parallels.length})</SectionHeading>
                        <Link href="/comparative" className="text-sm text-slate-400 underline-offset-4 hover:text-slate-100 hover:underline">
                            All comparative studies
                        </Link>
                    </div>
                    <div className="space-y-4">
                        {parallels.map((parallel) => (
                            <CrossCulturalParallelCard
                                key={parallel.id}
                                parallel={parallel}
                                tradition={parallel.tradition}
                                sourceText={parallel.source_text}
                                motifTags={parallel.motif_tags}
                            />
                        ))}
                    </div>
                </section>
            )}

            {referenceRows.length > 0 && (
                <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-1.5 border-t border-slate-800 pt-6 text-sm">
                    {referenceRows.map(([label, value]) => (
                        <div key={label} className="contents">
                            <dt className="text-slate-500">{label}</dt>
                            <dd className="text-slate-300">{value}</dd>
                        </div>
                    ))}
                </dl>
            )}
        </main>
    );
}
