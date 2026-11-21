/**
 * Ready-to-mount server component for the report page: every chain of a report (and optionally its related
 * reports) on one Hijri axis, with eras, events, chronological notes and the place trail.
 *
 * Props contract:
 *   hadithId          the report's stable id (`hadith:k6:10008`), i.e. what the page already resolved from its address.
 *   relatedHadithIds  optional ids of other reports of the same family (e.g. the report-family statement's tellings),
 *                     aligned on the same axis; MAX_FAMILY_REPORTS (12) ids are read in total, the page's own first.
 *   visibility        optional; the page's `requestVisibility()` result. Resolved here when omitted.
 * Public visibility shows only published, cited data (often nothing yet); curator visibility under private preview
 * shows lexicon dates, seed eras and events, each labelled. Renders nothing on a failed read.
 * See src/components/AGENTS.md §Time and place.
 */
import { getChainFamilyTimeline } from '@/db/queries/timeline';
import type { ReadVisibility } from '@/db/queries/visibility';
import { requestVisibility } from '@/lib/auth/visibility';
import { ChainTimeline } from './ChainTimeline';

export interface ChainFamilyTimelineSectionProps {
  hadithId: string;
  relatedHadithIds?: string[];
  visibility?: ReadVisibility;
}

export async function ChainFamilyTimelineSection({ hadithId, relatedHadithIds = [], visibility }: ChainFamilyTimelineSectionProps) {
  const ids = [hadithId, ...relatedHadithIds.filter((id) => id !== hadithId)];
  const family = await getChainFamilyTimeline(ids, visibility ?? (await requestVisibility())).catch((error: unknown) => {
    console.error('Chain timeline failed:', error);
    return null;
  });
  if (!family) return null;
  return <ChainTimeline family={family} headingId={`chain-timeline-${hadithId.replace(/[^a-zA-Z0-9_-]/g, '-')}`} />;
}
