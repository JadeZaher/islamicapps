export const dynamic = 'force-dynamic';

import {
    getEnhancedNarratorDetails,
    getNarratorNetwork,
    getCommentariesForNarrator,
    getHistoricalEventsForNarrator,
} from '@/app/actions/graph-actions';
import { getTraditionConnectionsForNarrator } from '@/app/actions/comparative-actions';
import { ConsensusBadge } from '@/components/ConsensusBadge';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import NarratorClientPage, { type NarratorClientPageProps } from './client-page';

interface PageProps {
    params: Promise<{
        id: string;
    }>;
}

export default async function NarratorPage({ params }: PageProps) {
    const { id } = await params;

    const narratorDetails = await getEnhancedNarratorDetails(id);
    if (!narratorDetails) notFound();

    // Secondary sections degrade independently: one failing query must not blank the page.
    const [network, commentaryRows, eventRows, connections] = await Promise.allSettled([
        getNarratorNetwork(id),
        getCommentariesForNarrator(id),
        getHistoricalEventsForNarrator(id),
        getTraditionConnectionsForNarrator(id),
    ]);
    const settled = <T,>(result: PromiseSettledResult<T>): T | undefined => {
        if (result.status === 'fulfilled') return result.value;
        console.error('Narrator section failed:', result.reason);
        return undefined;
    };

    return (
        <div className="min-h-screen bg-slate-950 py-12 px-4">
            <div className="max-w-6xl mx-auto">
                {/* Header */}
                <div className="mb-8">
                    <Link
                        href="/"
                        className="inline-flex items-center gap-2 text-cyan-300 hover:text-cyan-200 transition-colors mb-4"
                    >
                        <span>←</span> Back to Home
                    </Link>
                    <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-8 border border-white/10">
                        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-6">
                            <div>
                                <h1 className="text-4xl font-bold text-white mb-3">
                                    {narratorDetails.name_english}
                                </h1>
                                <p className="text-2xl text-cyan-200/90 font-arabic mb-4">
                                    {narratorDetails.name_arabic}
                                </p>
                                <div className="flex flex-wrap gap-3">
                                    {narratorDetails.reliability && (
                                        <ConsensusBadge verdict={narratorDetails.reliability_consensus ?? narratorDetails.reliability} />
                                    )}
                                    <div className="px-4 py-2 rounded-lg bg-cyan-500/15 border border-cyan-500/25">
                                        <span className="text-sm text-cyan-200">
                                            {narratorDetails.tabaqah}
                                        </span>
                                    </div>
                                    {narratorDetails.geographic_region && (
                                        <div className="px-4 py-2 rounded-lg bg-blue-500/20 border border-blue-500/30">
                                            <span className="text-sm text-blue-200">
                                                📍 {narratorDetails.geographic_region}
                                            </span>
                                        </div>
                                    )}
                                </div>
                            </div>
                            {narratorDetails.death_year_hijri && (
                                <div className="flex flex-col items-end">
                                    <span className="text-sm text-white/60 mb-1">Died</span>
                                    <span className="text-3xl font-bold text-cyan-300">
                                        {narratorDetails.death_year_hijri} AH
                                    </span>
                                    {narratorDetails.birth_year_hijri && (
                                        <span className="text-sm text-white/60 mt-2">
                                            Born {narratorDetails.birth_year_hijri} AH
                                        </span>
                                    )}
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Client-side tabbed content */}
                <NarratorClientPage
                    narratorDetails={narratorDetails}
                    narratorNetwork={settled(network) as NarratorClientPageProps['narratorNetwork']}
                    commentaries={(settled(commentaryRows) ?? []) as NarratorClientPageProps['commentaries']}
                    historicalEvents={(settled(eventRows) ?? []) as NarratorClientPageProps['historicalEvents']}
                    traditionConnections={(settled(connections) ?? { traditions: [], hadiths_with_parallels: [] }) as NarratorClientPageProps['traditionConnections']}
                />
            </div>
        </div>
    );
}
