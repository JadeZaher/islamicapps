export const dynamic = 'force-dynamic';

import { getPublishedCommentariesForNarrator } from '@/db/queries/commentary';
import { getTraditionConnectionsForNarrator } from '@/db/queries/comparative';
import type { NarratorDetail } from '@/db/queries/contracts';
import { getNarratorTimeline } from '@/db/queries/timeline';
import { requestVisibility } from '@/lib/auth/visibility';
import { NarratorTimeline } from '@/components/timeline/NarratorTimeline';
import { getNarratorNetwork } from '@/db/queries/narrator';
import type { Metadata } from 'next';
import { loadNarrator } from './data';
import { NarratorName } from '@/components/NarratorName';
import { LexiconRecord } from './components/LexiconRecord';
import { notFound } from 'next/navigation';
import NarratorClientPage, { type NarratorClientPageProps } from './client-page';

interface PageProps {
    params: Promise<{
        id: string;
    }>;
}

/**
 * Adapts the public narrator contract to the client's keys. Only published bios and verdicts reach this adapter; the
 * lexicon's dates and places render separately in LexiconRecord with their label, and no single cross-tradition verdict
 * is synthesized.
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
    const [network, commentaryRows, timelineResult, connections] = await Promise.allSettled([
        getNarratorNetwork(id),
        getPublishedCommentariesForNarrator(id),
        // Curator visibility (private preview) shows the labelled lexicon and seed data; public shows only cited data.
        requestVisibility().then((visibility) => getNarratorTimeline(id, visibility)),
        getTraditionConnectionsForNarrator(id),
    ]);
    const settled = <T,>(result: PromiseSettledResult<T>): T | undefined => {
        if (result.status === 'fulfilled') return result.value;
        console.error('Narrator section failed:', result.reason);
        return undefined;
    };

    return (
        <main className="wrap pb-12">
            <header className="page-header mb-8">
                <h1>
                    <NarratorName
                        english={narrator.name_english}
                        arabic={narrator.name_arabic}
                        latinClassName="type-h1"
                        arabicClassName="mt-1 w-fit text-[length:var(--text-arabic-display)] leading-[var(--leading-arabic-display)] font-normal text-ink"
                    />
                </h1>
            </header>

            {narrator.lexicon && <LexiconRecord lexicon={narrator.lexicon} />}

            <NarratorClientPage
                narratorDetails={toNarratorDetails(narrator)}
                verdicts={narrator.verdicts}
                lifeAndTimes={(() => {
                    const timeline = settled(timelineResult);
                    return timeline ? <NarratorTimeline timeline={timeline} /> : null;
                })()}
                narratorNetwork={settled(network) as NarratorClientPageProps['narratorNetwork']}
                commentaries={(settled(commentaryRows) ?? []) as unknown as NarratorClientPageProps['commentaries']}
                traditionConnections={
                    (settled(connections) ?? { traditions: [], hadiths_with_parallels: [] }) as unknown as NarratorClientPageProps['traditionConnections']
                }
            />
        </main>
    );
}
