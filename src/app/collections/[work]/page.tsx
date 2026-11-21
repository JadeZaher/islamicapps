import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { Breadcrumbs } from '@/components/archive/Breadcrumbs';
import { Pager, ReportList } from '@/components/archive/ReportList';
import { BilingualTitle } from '@/components/NarratorName';
import { getBookOutline, getWorkOutline, listReportsInOrder } from '@/db/queries/browse';
import { requestVisibility } from '@/lib/auth/visibility';
import { ChapterList } from '../ChapterList';
import { pageParam, routeParam, structureNote } from '../structure';
import { WorkSource } from '../WorkSource';

export const dynamic = 'force-dynamic';

interface PageProps {
  params: Promise<{ work: string }>;
  searchParams: Promise<{ page?: string }>;
}

const number = (value: number) => value.toLocaleString('en');

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const outline = await getWorkOutline(routeParam((await params).work), await requestVisibility()).catch(() => null);
  return { title: outline?.work.name ?? 'Work not found' };
}

/** A work: its books (volumes) with counts; a single book's chapters inline; or its reports when it has no books. */
export default async function WorkPage({ params, searchParams }: PageProps) {
  const slug = routeParam((await params).work);
  const page = pageParam((await searchParams).page);
  const visibility = await requestVisibility();
  const outline = await getWorkOutline(slug, visibility);
  if (!outline) notFound();
  const { work, structure, books } = outline;
  const basePath = `/collections/${encodeURIComponent(work.slug)}`;
  const note = structureNote(structure);
  const singleBook = books.length === 1 && books[0].chapterCount > 0 ? await getBookOutline(slug, books[0].number, visibility) : null;
  const reports = books.length === 0 ? await listReportsInOrder({ workSlug: slug }, { page }, visibility) : null;

  return (
    <main className="archive archive-column py-[var(--archive-space-5)]">
      <Breadcrumbs
        items={[
          { label: 'Collections', href: '/collections' },
          { label: work.tradition, href: `/collections#${work.tradition.toLowerCase()}` },
          { label: work.name },
        ]}
      />
      <h1 className="mt-[var(--archive-space-3)] text-3xl font-semibold tracking-tight">{work.name}</h1>
      <p className="mt-[var(--archive-space-2)] text-sm text-[color:var(--archive-muted)]">
        {number(structure.reports)} reports
        {books.length > 1 && ` · ${number(books.length)} ${structure.namespace === 'k6' ? 'books' : 'volumes'}`}
        {structure.withChapter > 0 && ` · ${number(books.reduce((sum, book) => sum + book.chapterCount, 0))} chapters`}
      </p>
      <div className="mt-[var(--archive-space-2)]">
        <WorkSource work={work} />
      </div>
      {note && <p className="archive-rule mt-[var(--archive-space-3)] pt-[var(--archive-space-3)] text-sm">{note}</p>}

      <div className="mt-[var(--archive-space-4)]">
        {singleBook ? (
          <ChapterList chapters={singleBook.chapters} basePath={`${basePath}/${encodeURIComponent(singleBook.book.number)}`} />
        ) : books.length > 0 ? (
          <ol className="archive-rule">
            {books.map((book) => (
              <li key={book.number} className="border-b border-[color:var(--archive-rule)]">
                <Link
                  href={`${basePath}/${encodeURIComponent(book.number)}`}
                  className="archive-focus grid grid-cols-[6rem_1fr_auto] items-baseline gap-[var(--archive-space-3)] py-[var(--archive-space-2)] hover:text-[color:var(--archive-accent)]"
                >
                  <span className="text-sm text-[color:var(--archive-muted)]">{book.label}</span>
                  <span className="min-w-0">{book.title ? <BilingualTitle text={book.title} /> : null}</span>
                  <span className="text-sm tabular-nums text-[color:var(--archive-muted)]">
                    {number(book.reportCount)}
                    {book.chapterCount > 0 && ` · ${number(book.chapterCount)} ch.`}
                  </span>
                </Link>
              </li>
            ))}
          </ol>
        ) : reports ? (
          <>
            <ReportList items={reports.items} />
            <Pager basePath={basePath} page={reports.page} totalPages={reports.totalPages} />
          </>
        ) : null}
      </div>
    </main>
  );
}
