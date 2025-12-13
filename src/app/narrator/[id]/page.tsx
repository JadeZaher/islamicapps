import { getNarratorDetails } from '@/app/actions/graph-actions';
import { ReliabilityBadge } from '@/components/ReliabilityBadge';
import { TabaqahTimeline } from '@/components/TabaqahTimeline';
import Link from 'next/link';

interface PageProps {
    params: {
        id: string;
    };
}

export default async function NarratorPage({ params }: PageProps) {
    const { id } = params;
    const narratorDetails = await getNarratorDetails(id);

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

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    {/* Biography Section */}
                    <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-8 border border-white/10">
                        <h2 className="text-2xl font-bold text-white mb-6">Biography</h2>
                        <div className="prose prose-invert max-w-none">
                            <p className="text-white/80 leading-relaxed">{narratorDetails.bio}</p>
                        </div>
                    </div>

                    {/* Generation Timeline */}
                    <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-8 border border-white/10">
                        <TabaqahTimeline currentTabaqah={narratorDetails.tabaqah} />
                    </div>
                </div>

                {/* Hadiths Narrated Section */}
                {narratorDetails.other_hadiths && narratorDetails.other_hadiths.length > 0 && (
                    <div className="mt-8 bg-white/5 backdrop-blur-lg rounded-2xl p-8 border border-white/10">
                        <h2 className="text-2xl font-bold text-white mb-6">
                            Hadiths Narrated ({narratorDetails.other_hadiths.length})
                        </h2>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {narratorDetails.other_hadiths.map((hadith: any) => (
                                <Link
                                    key={hadith.id}
                                    href={`/hadith/${hadith.id}`}
                                    className="block p-6 bg-white/5 hover:bg-white/10 border border-white/10 hover:border-purple-500/50 
                                        rounded-xl transition-all duration-300 group"
                                >
                                    <h3 className="text-lg font-semibold text-white group-hover:text-purple-300 transition-colors mb-2">
                                        {hadith.title}
                                    </h3>
                                    <p className="text-sm text-white/60 mb-3">{hadith.primary_topic}</p>
                                    {hadith.display_grade && (
                                        <div className="inline-block px-3 py-1 rounded-md bg-purple-500/20 border border-purple-500/30">
                                            <span className="text-xs text-purple-200">{hadith.display_grade}</span>
                                        </div>
                                    )}
                                </Link>
                            ))}
                        </div>
                    </div>
                )}

                {/* Empty State for No Hadiths */}
                {(!narratorDetails.other_hadiths || narratorDetails.other_hadiths.length === 0) && (
                    <div className="mt-8 bg-white/5 backdrop-blur-lg rounded-2xl p-12 border border-white/10 text-center">
                        <div className="text-4xl mb-4">📚</div>
                        <h3 className="text-xl font-semibold text-white/80 mb-2">No Hadiths Found</h3>
                        <p className="text-white/60">
                            This narrator is not currently linked to any hadiths in our database.
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
}
