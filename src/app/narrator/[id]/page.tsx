import {
    getEnhancedNarratorDetails,
    getNarratorNetwork,
    getCommentariesForNarrator,
    getHistoricalEventsForNarrator,
} from '@/app/actions/graph-actions';
import { ReliabilityBadge } from '@/components/ReliabilityBadge';
import { TabaqahTimeline } from '@/components/TabaqahTimeline';
import Link from 'next/link';
import NarratorClientPage from './client-page';

interface PageProps {
    params: {
        id: string;
    };
}

export default async function NarratorPage({ params }: PageProps) {
    const { id } = params;

    try {
        const [narratorDetails, narratorNetwork, commentaries, historicalEvents] = await Promise.all([
            getEnhancedNarratorDetails(id),
            getNarratorNetwork(id),
            getCommentariesForNarrator(id),
            getHistoricalEventsForNarrator(id),
        ]);

        if (!narratorDetails) {
            return (
                <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center p-8">
                    <div className="max-w-2xl w-full bg-white/10 backdrop-blur-lg rounded-2xl p-8 border border-white/20 text-center">
                        <div className="text-6xl mb-4">👤</div>
                        <h1 className="text-3xl font-bold text-white mb-4">Narrator Not Found</h1>
                        <p className="text-white/80 mb-8">
                            The narrator you're looking for doesn't exist in our database.
                        </p>
                        <Link
                            href="/"
                            className="inline-block px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
                        >
                            Return Home
                        </Link>
                    </div>
                </div>
            );
        }

        return (
            <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 py-12 px-4">
                <div className="max-w-6xl mx-auto">
                    {/* Header */}
                    <div className="mb-8">
                        <Link
                            href="/"
                            className="inline-flex items-center gap-2 text-purple-300 hover:text-purple-200 transition-colors mb-4"
                        >
                            <span>←</span> Back to Home
                        </Link>
                        <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-8 border border-white/10">
                            <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-6">
                                <div>
                                    <h1 className="text-4xl font-bold text-white mb-3">
                                        {narratorDetails.name_english}
                                    </h1>
                                    <p className="text-2xl text-purple-200/90 font-arabic mb-4">
                                        {narratorDetails.name_arabic}
                                    </p>
                                    <div className="flex flex-wrap gap-3">
                                        <ReliabilityBadge reliability={narratorDetails.reliability} />
                                        <div className="px-4 py-2 rounded-lg bg-purple-500/20 border border-purple-500/30">
                                            <span className="text-sm text-purple-200">
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
                                        <span className="text-3xl font-bold text-purple-300">
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
                        narratorNetwork={narratorNetwork}
                        commentaries={commentaries}
                        historicalEvents={historicalEvents}
                    />
                </div>
            </div>
        );
    } catch (error) {
        console.error('Error loading narrator details:', error);
        return (
            <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center p-8">
                <div className="max-w-2xl w-full bg-white/10 backdrop-blur-lg rounded-2xl p-8 border border-white/20 text-center">
                    <div className="text-6xl mb-4">⚠️</div>
                    <h1 className="text-3xl font-bold text-white mb-4">Error Loading Narrator</h1>
                    <p className="text-white/80 mb-8">
                        There was an error loading this narrator's information.
                    </p>
                    <Link
                        href="/"
                        className="inline-block px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
                    >
                        Return Home
                    </Link>
                </div>
            </div>
        );
    }
}
