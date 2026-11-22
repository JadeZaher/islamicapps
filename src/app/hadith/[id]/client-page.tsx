'use client';

import Link from 'next/link';

import { ArabicText } from '@/components/ArabicText';
import { ReportEnglish } from '@/components/archive/ReportEnglish';
import { CrossCulturalParallelCard } from '@/components/CrossCulturalParallelCard';
import { BilingualTitle } from '@/components/NarratorName';
import { TraditionBadge } from '@/components/TraditionBadge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { IsnadChain } from './components/IsnadChain';
import { GradingPanel } from './components/GradingPanel';
import { Assessments } from './components/Assessments';
import { ReportFamilySection } from './components/family/ReportFamilySection';
import { SourceNotes } from './components/SourceNotes';
import { ownMatn } from './matn';
import { reportNumber, reportPart, reportReference } from '@/lib/citation/reference';
import { hadithPath } from '@/lib/hadith-address';
import type { HadithClientPageProps } from './types';

/** Section heading used for every block on the page: a 12px uppercase label (DESIGN.md §Report reading column). */
function SectionHeading({ id, children }: { id: string; children: React.ReactNode }) {
    return (
        <h2 id={id} className="type-label mb-4">
            {children}
        </h2>
    );
}

/** A section opened by a 1px ink rule above its label. */
const SECTION = 'section-rule mt-12';

/**
 * Hadith reading page (DESIGN.md §Report reading column): page header, then from 1024px an 8-column reading column
 * (text, then isnad) beside a 4-column facts margin; wide sections span all 12. English is secondary.
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
    // OpenITI works: the Arabic chain span as written, only where the split is confident (a low-confidence report keeps
    // its whole text below, once); it replaces the stored sanad line, which would show the chain twice.
    const chainSpan = hadith.split_confidence === 'high' && arabicMatn ? hadith.sanad_ar?.trim() || null : null;
    const sourceSanadText = hasArabicMatn && !chainSpan ? writtenSanad : null;
    const hasChain = (chain?.nodes.length ?? 0) > 0;
    const continuation = hadith.chain_continues_from ?? null;
    const sourceNotes = hadith.source_notes ?? [];
    const showChain = Boolean(sourceSanadText?.trim()) || hasChain || Boolean(chainSpan) || Boolean(continuation);

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
    const part = reportPart(hadith.id);
    const reference = [hadith.source, number && part ? `${number}, part ${part}` : number].filter(Boolean).join(' ');
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
        <main className="wrap pb-12">
            <header className="page-header !pt-4">
                <h1 className="type-h1 text-ink">{heading}</h1>
                {(hadith.tradition || (chapter && chapter !== heading) || hadith.display_grade || hadith.transmission_type) && (
                    <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 type-small text-ink-muted">
                        {hadith.tradition && <TraditionBadge tradition={hadith.tradition} />}
                        {chapter && chapter !== heading && (
                            <>
                                {hadith.tradition && <span aria-hidden="true">·</span>}
                                <BilingualTitle text={chapter} />
                            </>
                        )}
                        {hadith.display_grade || hadith.transmission_type ? (
                            <>
                                <span aria-hidden="true">·</span>
                                <GradingPanel displayGrade={hadith.display_grade} transmissionType={hadith.transmission_type} />
                            </>
                        ) : null}
                    </div>
                )}
                {showTopic && <p className="mt-1 type-small text-ink-muted">{topic}</p>}
            </header>

            <div className="grid grid-cols-1 gap-x-6 lg:grid-cols-12">
                <div className="min-w-0 lg:col-span-8">
                    {(arabicText || englishText) && (
                        <section aria-labelledby="matn-heading" className="mt-8 max-w-[var(--measure-reading)]">
                            <SectionHeading id="matn-heading">{isSegmented ? 'Matn · report text' : 'Text as in the source'}</SectionHeading>
                            {arabicText && (
                                <ArabicText as="p" variant="reading" className="whitespace-pre-line text-ink">
                                    {arabicText}
                                </ArabicText>
                            )}
                            <ReportEnglish
                                text={englishText}
                                attribution={hadith.english_attribution}
                                note={segmentationDiffers ? ' · includes the chain' : undefined}
                                className={arabicText ? 'mt-6' : ''}
                            />
                        </section>
                    )}

                    {showChain && (
                        <section aria-labelledby="isnad-heading" className={`${SECTION} max-w-[var(--measure-reading)]`}>
                            <SectionHeading id="isnad-heading">Isnad · chain of transmission</SectionHeading>
                            {chainSpan && (
                                <ArabicText as="p" variant="reading" className="mb-4 whitespace-pre-line text-ink">
                                    {chainSpan}
                                </ArabicText>
                            )}
                            {continuation && (
                                <p className="mb-4 type-small text-ink-muted">
                                    <Link href={hadithPath(continuation.id)} className="link-row">
                                        {`Chain continues from ${reportReference({ id: continuation.id, hadithNo: continuation.hadith_no, url: null, volume: null, pageRef: null, bookNumber: null })}`}
                                    </Link>
                                </p>
                            )}
                            <IsnadChain chain={chain} sourceSanadText={sourceSanadText} />
                        </section>
                    )}

                    {sourceNotes.length > 0 && (
                        <section aria-labelledby="notes-heading" className={`${SECTION} max-w-[var(--measure-reading)]`}>
                            <SectionHeading id="notes-heading">Notes in the source edition</SectionHeading>
                            <SourceNotes notes={sourceNotes} />
                        </section>
                    )}
                </div>

                {referenceRows.length > 0 && (
                    <aside aria-label="About this report" className="pt-8 lg:col-span-4 lg:col-start-9">
                        <dl className="grid grid-cols-[7rem_minmax(0,1fr)] gap-x-4 gap-y-2 type-small max-lg:border-t max-lg:border-rule-strong max-lg:pt-3">
                            {referenceRows.map(([label, value]) => (
                                <div key={label} className="contents">
                                    <dt className="text-ink-muted">{label}</dt>
                                    <dd className="min-w-0 text-ink [overflow-wrap:anywhere]">{value}</dd>
                                </div>
                            ))}
                        </dl>
                    </aside>
                )}

                <div className="min-w-0 lg:col-span-12">
                    {/* The chain on a time axis: recorded lifespans or generations, eras, and gaps between consecutive narrators. */}
                    {timeline && <div className={SECTION}>{timeline}</div>}

                    {family && (
                        <section aria-labelledby="family-heading" className={SECTION}>
                            <SectionHeading id="family-heading">Tellings of this report</SectionHeading>
                            <ReportFamilySection family={family} hadithId={hadith.id} />
                        </section>
                    )}

                    {hadith.assessments && hadith.assessments.length > 0 && (
                        <section aria-labelledby="assessments-heading" className={`${SECTION} max-w-[var(--measure-wide)]`}>
                            <SectionHeading id="assessments-heading">Assessments by tradition</SectionHeading>
                            <Assessments groups={hadith.assessments} hadithId={hadith.id} />
                        </section>
                    )}

                    {realVariations.length > 0 && (
                        <section aria-labelledby="variants-heading" className={`${SECTION} max-w-[var(--measure-wide)]`}>
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
                                    <TabsContent key={index} value={index.toString()} className="max-w-[var(--measure-reading)] space-y-6">
                                        {variation.text_arabic && (
                                            <ArabicText as="p" variant="reading" className="text-ink">{variation.text_arabic}</ArabicText>
                                        )}
                                        {variation.text_english && (
                                            <p className="type-reading text-ink">{variation.text_english}</p>
                                        )}
                                    </TabsContent>
                                ))}
                            </Tabs>
                        </section>
                    )}

                    {parallels.length > 0 && (
                        <section aria-labelledby="parallels-heading" className={`${SECTION} max-w-[var(--measure-wide)]`}>
                            <div className="mb-4 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-2">
                                <SectionHeading id="parallels-heading">Parallels in other traditions ({parallels.length})</SectionHeading>
                                <Link href="/comparative" className="link-row type-small text-ink-muted">
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
                </div>
            </div>
        </main>
    );
}
