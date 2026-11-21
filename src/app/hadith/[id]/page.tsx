export const dynamic = 'force-dynamic';

import { notFound } from 'next/navigation';
import type { Metadata } from 'next';
import { getPublicParallelsForHadith } from '@/db/queries/comparative';
import type { HadithDetail } from '@/db/queries/contracts';
import { getChainGraph } from '@/db/queries/isnad';
import { requestVisibility } from '@/lib/auth/visibility';
import { hadithPath } from '@/lib/hadith-address';
import { siteOrigin } from '@/lib/site-url';
import { ChainFamilyTimelineSection } from '@/components/timeline/ChainFamilyTimelineSection';
import { HadithClientPage } from './client-page';
import { loadFamily, loadHadith } from './data';
import type { HadithNode, ParallelRecord } from './types';

interface PageProps {
    params: Promise<{
        id: string;
    }>;
}

/** Adapts the section 9.4 detail contract to the client's HadithNode keys. No grade is defaulted. */
function toHadithNode(hadith: HadithDetail): HadithNode {
    return {
        ...hadith,
        display_grade: null,
        auto_calculated_grade: null,
        transmission_type: null,
        hadith_id: hadith.record_id,
        variations: hadith.variations,
        assessments: hadith.assessments,
    };
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
    const { id } = await params;
    const hadith = await loadHadith(id).catch(() => null);
    if (!hadith) return { title: 'Hadith not found' };
    const reference = [hadith.source, hadith.hadith_no].filter(Boolean).join(' ');
    // The canonical address is built from SITE_URL (never a request header in production): src/lib/site-origin.ts.
    return {
        title: hadith.title?.trim() || reference || 'Hadith',
        alternates: { canonical: `${await siteOrigin()}${hadithPath(hadith.id)}` },
    };
}

export default async function HadithPage({ params }: PageProps) {
    const rawId = (await params).id;
    const id = decodeURIComponent(rawId);
    const visibility = await requestVisibility();

    const [hadith, graph, parallels, family] = await Promise.all([
        loadHadith(rawId),
        getChainGraph(id, visibility).catch((err) => {
            console.error('Error fetching chain graph:', err);
            return null;
        }),
        getPublicParallelsForHadith(id).catch(() => []),
        loadFamily(rawId).catch((err) => {
            console.error('Error fetching report family:', err);
            return null;
        }),
    ]);

    if (!hadith) notFound();

    return (
        <HadithClientPage
            hadith={toHadithNode(hadith)}
            chain={graph}
            parallels={parallels as unknown as ParallelRecord[]}
            family={family}
            timeline={
                <ChainFamilyTimelineSection
                    hadithId={id}
                    relatedHadithIds={(family?.tellings ?? []).filter((telling) => !telling.is_focal).map((telling) => telling.hadith_id)}
                    visibility={visibility}
                />
            }
        />
    );
}
