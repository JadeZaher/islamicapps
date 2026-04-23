export const dynamic = 'force-dynamic';

import { getHadithById, getFullChainGraph } from '@/app/actions/graph-actions';
import { getParallelsForHadith } from '@/app/actions/comparative-actions';
import { HadithClientPage } from './client-page';

interface PageProps {
    params: Promise<{
        id: string;
    }>;
}

export default async function HadithPage({ params }: PageProps) {
    try {
        const { id } = await params;

        // Fetch hadith and graph data with error handling
        const [hadith, graphData, parallels] = await Promise.all([
            getHadithById(id).catch(err => {
                console.error('Error fetching hadith:', err);
                return null;
            }),
            getFullChainGraph(id).catch(err => {
                console.error('Error fetching graph data:', err);
                return { nodes: [], edges: [] };
            }),
            getParallelsForHadith(id).catch(() => []),
        ]);

        // Create a default hadith object with null values if not found
        const hadithData = hadith || {
            id,
            title: null,
            primary_topic: null,
            display_grade: null,
            auto_calculated_grade: null,
            transmission_type: null,
            variations: [],
        };

        // Calculate chain health score (percentage of THIQA narrators)
        const thiqaNarrators = graphData.nodes?.filter((n: any) => n.reliability === 'THIQA').length || 0;
        const totalNarrators = graphData.nodes?.length || 0;
        const chainHealthScore = totalNarrators > 0
            ? Math.round((thiqaNarrators / totalNarrators) * 100)
            : 0;

        return (
            <HadithClientPage
                hadith={hadithData}
                nodes={graphData.nodes || []}
                edges={graphData.edges || []}
                chainHealthScore={chainHealthScore}
                parallels={parallels}
            />
        );
    } catch (error) {
        console.error('Unexpected error in HadithPage:', error);
        return (
            <div className="min-h-screen bg-slate-950 flex items-center justify-center p-8">
                <div className="max-w-2xl w-full bg-white/10 backdrop-blur-lg rounded-2xl p-8 border border-white/20 text-center">
                    <div className="text-6xl mb-4">⚠️</div>
                    <h1 className="text-3xl font-bold text-white mb-4">Error Loading Hadith</h1>
                    <p className="text-white/80 mb-6">
                        An unexpected error occurred while loading this hadith.
                    </p>
                    <p className="text-white/60 mb-8 font-mono text-sm">
                        {error instanceof Error ? error.message : 'Unknown error'}
                    </p>
                    <a
                        href="/"
                        className="inline-block px-6 py-3 bg-cyan-700 hover:bg-cyan-800 text-white rounded-lg transition-colors"
                    >
                        Return Home
                    </a>
                </div>
            </div>
        );
    }
}
