import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { Breadcrumbs } from '@/components/archive/Breadcrumbs';
import { Pager, ReportList } from '@/components/archive/ReportList';
import { BilingualTitle } from '@/components/NarratorName';
import { getBookOutline, listReportsInOrder } from '@/db/queries/browse';
import { requestVisibility } from '@/lib/auth/visibility';
import { ChapterList } from '../../ChapterList';
import { pageParam, routeParam } from '../../structure';
import { WorkSource } from '../../WorkSource';

export const dynamic = 'force-dynamic';

interface PageProps {
  params: Promise<{ work: string; book: string }>;
  searchParams: Promise<{ page?: string; view?: string }>;
}

const number = (value: number) => value.toLocaleString('en');

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { work, book } = await params;
  const outline = await getBookOutline(routeParam(work), routeParam(book), await requestVisibility()).catch(() => null);
  return { title: outline ? `${outline.work.name}, ${outline.book.label}` : 'Book not found' };
}

/** A book: its chapters with counts, or (no chapters, or `?view=all`) every report in it in source order. */
export default async function BookPage({ params, searchParams }: PageProps) {
  const { work: rawWork, book: rawBook } = await params;
  const query = await searchParams;
  const slug = routeParam(rawWork);
  const bookNumber = routeParam(rawBook);
  const visibility = await requestVisibility();
  const outline = await getBookOutline(slug, bookNumber, visibility);
  if (!outline) notFound();
  const { work, book, chapters } = outline;
  const workPath = `/collections/${encodeURIComponent(work.slug)}`;
  const bookPath = `${workPath}/${encodeURIComponent(book.number)}`;
  const listAll = chapters.length === 0 || query.view === 'all';
  const reports = listAll ? await listReportsInOrder({ workSlug: slug, bookNumber }, { page: pageParam(query.page) }, visibility) : null;

  return (
    <main className="archive archive-column py-[var(--archive-space-5)]">
      <Breadcrumbs
        items={[
          { label: 'Collections', href: '/collections' },
          { label: work.tradition, href: `/collections#${work.tradition.toLowerCase()}` },
          { label: work.name, href: workPath },
          { label: book.label },
        ]}
      />
      <h1 className="mt-[var(--archive-space-3)] type-h1">
        {book.title ? <BilingualTitle text={book.title} /> : `${work.name}, ${book.label}`}
      </h1>
      <p className="mt-[var(--archive-space-2)] text-sm text-[color:var(--archive-muted)]">
        {book.title && `${book.label} · `}
        {number(book.reportCount)} reports
        {chapters.length > 0 && ` · ${number(chapters.length)} chapters`}
      </p>
      <div className="mt-[var(--archive-space-2)]">
        <WorkSource work={work} />
      </div>
      {chapters.length === 0 && (
        <p className="archive-rule mt-[var(--archive-space-3)] pt-[var(--archive-space-3)] text-sm">
          Our copy records no chapters in this book. Reports are listed in source order.
        </p>
      )}
      {chapters.length > 0 && (
        <p className="mt-[var(--archive-space-3)] text-sm">
          {listAll ? (
            <Link href={bookPath} className="archive-link">
              Show chapters
            </Link>
          ) : (
            <Link href={`${bookPath}?view=all`} className="archive-link">
              Read the whole book in order
            </Link>
          )}
          {outline.reportsWithoutChapter > 0 && ` · ${number(outline.reportsWithoutChapter)} reports in this book have no chapter`}
        </p>
      )}

      <div className="mt-[var(--archive-space-4)]">
        {reports ? (
          <>
            <ReportList items={reports.items} />
            <Pager basePath={bookPath} page={reports.page} totalPages={reports.totalPages} extra={query.view === 'all' ? { view: 'all' } : {}} />
          </>
        ) : (
          <ChapterList chapters={chapters} basePath={bookPath} />
        )}
      </div>
    </main>
  );
}
