import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { Breadcrumbs } from '@/components/archive/Breadcrumbs';
import { Pager, ReportList } from '@/components/archive/ReportList';
import { BilingualTitle } from '@/components/NarratorName';
import { getBookOutline, listReportsInOrder } from '@/db/queries/browse';
import { requestVisibility } from '@/lib/auth/visibility';
import { pageParam, routeParam } from '../../../structure';
import { WorkSource } from '../../../WorkSource';

export const dynamic = 'force-dynamic';

interface PageProps {
  params: Promise<{ work: string; book: string; chapter: string }>;
  searchParams: Promise<{ page?: string }>;
}

const number = (value: number) => value.toLocaleString('en');

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { work, book, chapter } = await params;
  const outline = await getBookOutline(routeParam(work), routeParam(book), await requestVisibility()).catch(() => null);
  const found = outline?.chapters.find((item) => item.key === routeParam(chapter));
  return { title: found ? `${found.name ?? 'Chapter'} | ${outline?.work.name}` : 'Chapter not found' };
}

/** A chapter: its reports in source order, paged. */
export default async function ChapterPage({ params, searchParams }: PageProps) {
  const { work: rawWork, book: rawBook, chapter: rawChapter } = await params;
  const slug = routeParam(rawWork);
  const bookNumber = routeParam(rawBook);
  const chapterKey = routeParam(rawChapter);
  const visibility = await requestVisibility();
  const [outline, reports] = await Promise.all([
    getBookOutline(slug, bookNumber, visibility),
    listReportsInOrder({ workSlug: slug, bookNumber, chapterKey }, { page: pageParam((await searchParams).page) }, visibility),
  ]);
  const chapter = outline?.chapters.find((item) => item.key === chapterKey);
  if (!outline || !chapter || reports.total === 0) notFound();
  const workPath = `/collections/${encodeURIComponent(outline.work.slug)}`;
  const bookPath = `${workPath}/${encodeURIComponent(outline.book.number)}`;
  const chapterPath = `${bookPath}/${encodeURIComponent(chapter.key)}`;

  return (
    <main className="archive archive-column py-[var(--archive-space-5)]">
      <Breadcrumbs
        items={[
          { label: 'Collections', href: '/collections' },
          { label: outline.work.tradition, href: `/collections#${outline.work.tradition.toLowerCase()}` },
          { label: outline.work.name, href: workPath },
          { label: outline.book.label, href: bookPath },
          { label: chapter.number ? `Chapter ${chapter.number}` : 'Chapter' },
        ]}
      />
      {chapter.category && (
        <p className="mt-[var(--archive-space-3)] text-sm text-[color:var(--archive-muted)]">
          <BilingualTitle text={chapter.category} />
        </p>
      )}
      <h1 className="mt-[var(--archive-space-2)] text-2xl font-semibold tracking-tight">
        {chapter.name ? <BilingualTitle text={chapter.name} /> : 'Untitled chapter'}
      </h1>
      <p className="mt-[var(--archive-space-2)] text-sm text-[color:var(--archive-muted)]">{number(reports.total)} reports</p>
      <div className="mt-[var(--archive-space-2)]">
        <WorkSource work={outline.work} />
      </div>
      <div className="mt-[var(--archive-space-4)]">
        <ReportList items={reports.items} />
        <Pager basePath={chapterPath} page={reports.page} totalPages={reports.totalPages} />
      </div>
    </main>
  );
}
