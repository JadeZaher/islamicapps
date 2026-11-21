import { hadithPath } from '@/lib/hadith-address';
import { siteOrigin } from '@/lib/site-url';
import { Breadcrumbs, type Crumb } from './Breadcrumbs';
import { loadReportContext } from './report-data';
import './archive.css';

/** Tradition > work > book > chapter trail above a report, plus its canonical address. */
export async function ReportTrail({ id }: { id: string }) {
  const [context, origin] = await Promise.all([loadReportContext(id), siteOrigin()]);
  if (!context) return null;
  const work = `/collections/${encodeURIComponent(context.work.slug)}`;
  const items: Crumb[] = [
    { label: 'Collections', href: '/collections' },
    { label: context.tradition, href: `/collections#${context.tradition.toLowerCase()}` },
    { label: context.work.name, href: work },
  ];
  if (context.book) items.push({ label: context.book.label, href: `${work}/${encodeURIComponent(context.book.number)}` });
  if (context.book && context.chapter) {
    items.push({
      label: context.chapter.number ? `Chapter ${context.chapter.number}` : 'Chapter',
      href: `${work}/${encodeURIComponent(context.book.number)}/${encodeURIComponent(context.chapter.key)}`,
    });
  }
  items.push({ label: context.reference });
  return (
    <div className="archive archive-column pt-[var(--archive-space-4)]">
      <link rel="canonical" href={`${origin}${hadithPath(context.id)}`} />
      <Breadcrumbs items={items} />
    </div>
  );
}
