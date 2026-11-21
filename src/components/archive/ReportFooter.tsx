import Link from 'next/link';
import { citationText } from '@/lib/citation/cite';
import { hadithPath } from '@/lib/hadith-address';
import { reportSourceReferences } from '@/lib/sources/report-credit';
import { siteOrigin } from '@/lib/site-url';
import { CopyText } from './CopyText';
import { DatasetVersionLine } from './DatasetVersionLine';
import { ArrowMark } from './Marks';
import { loadDatasetVersion, loadReportContext } from './report-data';
import { ReportSourceCredit } from './SourceCredit';

/** Below a report: previous/next in its work, source references, the citation block and the dataset version. */
export async function ReportFooter({ id }: { id: string }) {
  const [context, version, origin] = await Promise.all([loadReportContext(id), loadDatasetVersion(), siteOrigin()]);
  if (!context) return null;
  const references = reportSourceReferences({
    sourceSlug: context.work.sourceSlug,
    sourceWorkId: context.work.sourceWorkId,
    workName: context.work.name,
    // A provider URL shared by several reports cannot identify this one (see src/components/AGENTS.md §Archive surfaces).
    url: context.urlUnique ? context.url : null,
    number: context.number,
    english: context.english,
  });
  const citation = citationText({
    workName: context.work.name,
    reference: context.reference,
    version: version ? { label: version.label, shortId: version.shortId } : null,
    address: `${origin}${hadithPath(context.id)}`,
    origin,
    accessed: new Date().toISOString().slice(0, 10),
    references,
  });

  return (
    <div className="archive archive-column mt-12 pb-8">
      <nav
        aria-label={`Reports in ${context.work.name}`}
        className="archive-rule grid grid-cols-2 gap-4 py-4 type-small"
      >
        <div>
          {context.previous && (
            <Link href={hadithPath(context.previous.id)} rel="prev" className="group flex flex-col gap-1 no-underline">
              <span className="archive-label flex items-center gap-2">
                <ArrowMark direction="left" /> Previous
              </span>
              <span className="underline decoration-rule decoration-1 underline-offset-[0.2em] group-hover:decoration-accent">{context.previous.reference}</span>
            </Link>
          )}
        </div>
        <div className="text-end">
          {context.next && (
            <Link href={hadithPath(context.next.id)} rel="next" className="group flex flex-col items-end gap-1 no-underline">
              <span className="archive-label flex items-center gap-2">
                Next <ArrowMark direction="right" />
              </span>
              <span className="underline decoration-rule decoration-1 underline-offset-[0.2em] group-hover:decoration-accent">{context.next.reference}</span>
            </Link>
          )}
        </div>
        <p className="col-span-2 type-small text-ink-muted">
          Report {context.position.toLocaleString('en')} of {context.total.toLocaleString('en')} in {context.work.name}, in source order.
        </p>
      </nav>

      <section aria-labelledby="report-sources" className="archive-rule py-4">
        <h2 id="report-sources" className="archive-label mb-2">
          Sources
        </h2>
        {references.length > 0 ? (
          references.map((reference) => <ReportSourceCredit key={reference.role} reference={reference} />)
        ) : (
          <p className="type-small text-danger">No source record is registered for this work.</p>
        )}
      </section>

      <section aria-labelledby="report-cite" className="archive-rule py-4">
        <h2 id="report-cite" className="archive-label mb-2">
          Cite this report
        </h2>
        <CopyText label="Citation" text={citation} />
      </section>

      <DatasetVersionLine className="archive-rule pt-4" />
    </div>
  );
}
