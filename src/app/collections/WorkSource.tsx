import { SourceCredit } from '@/components/archive/SourceCredit';
import type { WorkHeader } from '@/db/queries/browse';
import { sourceForDatabaseSlug, WORK_CREDITS } from '@/lib/sources/registry';

/** The text-source reference for a browse page that shows a work's text. */
export function WorkSource({ work }: { work: WorkHeader }) {
  const record = sourceForDatabaseSlug(work.sourceSlug);
  if (!record) return <p className="type-small text-danger">No source record is registered for this work.</p>;
  const author = WORK_CREDITS[work.sourceWorkId]?.author;
  return <SourceCredit code={record.code} role="Text" detail={author ? `${work.name}, ${author}` : work.name} />;
}
