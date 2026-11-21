export const dynamic = 'force-dynamic';

import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { ChainFamilyTimelineSection } from '@/components/timeline/ChainFamilyTimelineSection';
import { requestVisibility } from '@/lib/auth/visibility';
import { FamilyView } from '../components/family/FamilyView';
import { loadFamily } from '../data';
import { tellingReference } from '../components/family/labels';

interface PageProps {
    params: Promise<{ id: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
    const family = await loadFamily((await params).id).catch(() => null);
    const focal = family?.tellings.find((telling) => telling.is_focal);
    return { title: focal ? `Tellings and chains · ${tellingReference(focal)}` : 'Tellings and chains' };
}

/** Every telling of a public report and every chain each carries (the layout has already 404ed unknown reports). */
export default async function ReportChainsPage({ params }: PageProps) {
    const family = await loadFamily((await params).id);
    if (!family) notFound();
    const visibility = await requestVisibility();
    const others = family.tellings.filter((telling) => !telling.is_focal).map((telling) => telling.hadith_id);
    return (
        <FamilyView
            family={family}
            mode="public"
            timeline={<ChainFamilyTimelineSection hadithId={family.hadith_id} relatedHadithIds={others} visibility={visibility} />}
        />
    );
}
