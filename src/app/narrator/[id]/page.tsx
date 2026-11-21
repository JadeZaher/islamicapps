export const dynamic = 'force-dynamic';

import { getPublishedCommentariesForNarrator } from '@/db/queries/commentary';
import { getTraditionConnectionsForNarrator } from '@/db/queries/comparative';
import type { NarratorDetail } from '@/db/queries/contracts';
import { getHistoricalEventsForNarrator } from '@/db/queries/history';
import { getNarratorNetwork } from '@/db/queries/narrator';
import type { Metadata } from 'next';
import { loadNarrator } from './data';
import { NarratorName } from '@/components/NarratorName';
import { notFound } from 'next/navigation';
import NarratorClientPage, { type NarratorClientPageProps } from './client-page';

interface PageProps {
    params: Promise<{
        id: string;
    }>;
}

/**
 * Adapts the public narrator contract to the client's keys. Only published bios and verdicts reach this page;
 * lexicon dates and biography stay hidden (question 4), and no single cross-tradition verdict is synthesized.
 */
function toNarratorDetails(narrator: NarratorDetail): NarratorClientPageProps['narratorDetails'] {
    const bio = narrator.bio;
    return {
        id: narrator.id,
        name_english: narrator.name_english,
        name_arabic: narrator.name_arabic,
        tabaqah: bio?.tabaqah ?? '',
        is_prophet: bio?.is_prophet,
        name_english_clean: bio?.name_english_clean ?? undefined,
        name_arabic_clean: bio?.name_arabic_clean ?? undefined,
        kunya: bio?.kunya ?? undefined,
        nasab: bio?.nasab ?? undefined,
        nisba: bio?.nisba ?? undefined,
        geographic_region: bio?.geographic_region ?? undefined,
        death_year_hijri: bio?.death_year_hijri ?? undefined,
        death_year_gregorian: bio?.death_year_gregorian ?? undefined,
        death_date_hijri: bio?.death_year_hijri ?? undefined,
        death_date_gregorian: bio?.death_year_gregorian ?? undefined,
        bio_summary: bio?.bio_summary ?? undefined,
        other_hadiths: narrator.hadiths.items.map((hadith) => ({
            id: hadith.id,
            title: hadith.title ?? [hadith.source, hadith.hadith_no].filter(Boolean).join(' '),
            primary_topic: hadith.primary_topic ?? undefined,
        })),
    };
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
    const narrator = await loadNarrator((await params).id).catch(() => null);
    if (!narrator) return { title: 'Narrator not found' };
    return { title: narrator.name_english || narrator.name_arabic || 'Narrator' };
}

export default async function NarratorPage({ params }: PageProps) {
    const rawId = (await params).id;
    const id = decodeURIComponent(rawId);

    const narrator = await loadNarrator(rawId);
    if (!narrator) notFound();

    // Secondary sections degrade independently: one failing query must not blank the page.
    const [network, commentaryRows, eventRows, connections] = await Promise.allSettled([
        getNarratorNetwork(id),
        getPublishedCommentariesForNarrator(id),
        getHistoricalEventsForNarrator(id),
        getTraditionConnectionsForNarrator(id),
    ]);
    const settled = <T,>(result: PromiseSettledResult<T>): T | undefined => {
        if (result.status === 'fulfilled') return result.value;
        console.error('Narrator section failed:', result.reason);
        return undefined;
    };

    return (
        <main className="mx-auto max-w-4xl px-6 pb-20 pt-10 text-slate-100">
            <header className="mb-8">
                <h1>
                    <NarratorName
                        english={narrator.name_english}
                        arabic={narrator.name_arabic}
                        latinClassName="text-3xl font-semibold"
                        arabicClassName="mt-1 text-end text-3xl font-normal leading-relaxed text-slate-200"
                    />
                </h1>
            </header>

            <NarratorClientPage
                narratorDetails={toNarratorDetails(narrator)}
                verdicts={narrator.verdicts}
                narratorNetwork={settled(network) as NarratorClientPageProps['narratorNetwork']}
                commentaries={(settled(commentaryRows) ?? []) as unknown as NarratorClientPageProps['commentaries']}
                historicalEvents={(settled(eventRows) ?? []) as unknown as NarratorClientPageProps['historicalEvents']}
                traditionConnections={
                    (settled(connections) ?? { traditions: [], hadiths_with_parallels: [] }) as unknown as NarratorClientPageProps['traditionConnections']
                }
            />
        </main>
    );
}
