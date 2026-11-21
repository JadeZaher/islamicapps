// Temporary preview notice: see conductor/RUNBOOK.md, Remove after the first release.
import { connection } from 'next/server';
import { getPreviewNotice } from '@/db/queries/dataset';
import { PreviewNoticeBar } from './PreviewNoticeBar';

/** Site-wide line shown while the current dataset version is a non-release version served under owner approval. */
export async function PreviewNotice() {
  await connection();
  const notice = await getPreviewNotice().catch((error: unknown) => {
    console.error('Preview notice lookup failed', error instanceof Error ? error.message : error);
    return null;
  });
  return notice ? <PreviewNoticeBar /> : null;
}
