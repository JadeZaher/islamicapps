export const dynamic = 'force-dynamic';

import { notFound } from 'next/navigation';
import { getReportFamilyForReview } from '@/db/queries/correspondence-review';
import { FamilyView } from '@/app/hadith/[id]/components/family/FamilyView';

interface PageProps {
  params: Promise<{ id: string }>;
}

/**
 * Curator preview of a family: the public view's components over every live report, published or not, with a review
 * link on each pair. Reachable only with a curator session (src/proxy.ts gates /admin/**).
 */
export default async function CuratorFamilyPage({ params }: PageProps) {
  const id = decodeURIComponent((await params).id);
  const family = await getReportFamilyForReview(id);
  if (!family) notFound();
  return (
    <div>
      <p className="border-b border-rule pb-3 text-sm text-ink-muted">
        Curator preview: includes reports not yet published.
      </p>
      <FamilyView family={family} mode="curator" container="div" />
    </div>
  );
}
