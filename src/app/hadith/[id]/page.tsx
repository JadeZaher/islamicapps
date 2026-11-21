export const dynamic = 'force-dynamic';

import { notFound } from 'next/navigation';
import { getHadithById, getFullChainGraph } from '@/app/actions/graph-actions';
import { getParallelsForHadith } from '@/app/actions/comparative-actions';
import type { Metadata } from 'next';
import { HadithClientPage } from './client-page';
import type { HadithNode, ParallelRecord } from './types';

interface PageProps {
    params: Promise<{
        id: string;
    }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
    const { id } = await params;
    const hadith = (await getHadithById(id).catch(() => null)) as HadithNode | null;
    if (!hadith) return { title: 'Hadith not found' };
    const reference = [hadith.source, hadith.hadith_no].filter(Boolean).join(' ');
    return { title: hadith.title?.trim() || reference || 'Hadith' };
}

export default async function HadithPage({ params }: PageProps) {
    const { id } = await params;

    const [hadithRow, graphData, parallels] = await Promise.all([
        getHadithById(id),
        getFullChainGraph(id).catch((err) => {
            console.error('Error fetching graph data:', err);
            return { nodes: [], edges: [] };
        }),
        getParallelsForHadith(id).catch(() => []),
    ]);

    if (!hadithRow) notFound();
    const hadithData = hadithRow as unknown as HadithNode;

    // Chain health = % of narrators graded THIQA; null (unknown) when no narrator carries a verdict.
    const nodes = graphData.nodes || [];
    const gradedNarrators = nodes.filter((n) => Boolean((n as { reliability?: string }).reliability));
    const thiqaNarrators = gradedNarrators.filter((n) => (n as { reliability?: string }).reliability === 'THIQA').length;
    const chainHealthScore: number | null = gradedNarrators.length > 0
        ? Math.round((thiqaNarrators / nodes.length) * 100)
        : null;

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
            parallels={parallels as ParallelRecord[]}
            tracesToProphet={tracesToProphet}
        />
    );
}
