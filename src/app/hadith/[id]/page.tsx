export const dynamic = 'force-dynamic';

import { getHadithById, getFullChainGraph } from '@/app/actions/graph-actions';
import { getParallelsForHadith } from '@/app/actions/comparative-actions';
import { HadithClientPage } from './client-page';
import type { HadithNode } from './types';

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

        // Create a default hadith object with null values if not found.
        // Shape matches HadithNode (see ./types.ts) so the typed prop fits.
        const hadithData: HadithNode = (hadith as HadithNode | null) ?? {
            id,
            title: null,
            primary_topic: null,
            display_grade: null,
            auto_calculated_grade: null,
            transmission_type: null,
            text_english: null,
            text_arabic: null,
            isnad_arabic: null,
            chain_text_arabic: null,
            chapter: null,
            hadith_no: null,
            source: null,
            variations: [],
            // v2 canonical fields — all optional/null when hadith not found
            text_en: null,
            text_ar: null,
            matn_ar: null,
            matn_en: null,
            sanad: null,
            category: null,
        };

        // Calculate chain health score (percentage of THIQA narrators).
        // v1 narrators had `.reliability` directly; v2 narrators do not (G-1
        // moved verdicts onto :Assessment nodes). For v2 nodes the score will
        // be 0 here — TODO: re-derive from :HAS_ASSESSMENT.
        const nodes = graphData.nodes || [];
        const thiqaNarrators = nodes.filter((n) => (n as { reliability?: string }).reliability === 'THIQA').length;
        const totalNarrators = nodes.length;
        const chainHealthScore = totalNarrators > 0
            ? Math.round((thiqaNarrators / totalNarrators) * 100)
            : 0;

        // Check if chain traces back to the Prophet (via Sahabi or Prophet node)
        const hasSahabi = nodes.some((n) => (n as { tabaqah?: string }).tabaqah === 'SAHABA');
        const hasProphet = nodes.some((n) => {
            const x = n as { is_prophet?: boolean; tabaqah?: string };
            return x.is_prophet === true || x.tabaqah === 'PROPHET';
        });
        const chainTextMentionsProphet = Boolean(
            hadithData.chain_text_arabic?.includes('رسول الله') ||
            hadithData.chain_text_arabic?.includes('النبي') ||
            hadithData.isnad_arabic?.includes('رسول الله') ||
            hadithData.isnad_arabic?.includes('النبي') ||
            hadithData.sanad?.includes('رسول الله') ||
            hadithData.sanad?.includes('النبي')
        );
        const tracesToProphet = hasProphet || hasSahabi || chainTextMentionsProphet;

        return (
            <HadithClientPage
                hadith={hadithData}
                nodes={nodes}
                edges={graphData.edges || []}
                chainHealthScore={chainHealthScore}
                parallels={parallels}
                tracesToProphet={tracesToProphet}
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
