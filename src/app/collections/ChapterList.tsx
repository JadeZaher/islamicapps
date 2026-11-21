import Link from 'next/link';
import { BilingualTitle } from '@/components/NarratorName';
import type { ChapterSummary } from '@/db/queries/browse';

const number = (value: number) => value.toLocaleString('en');

/** A book's chapters in source order, grouped under their kitab heading when the source names one. */
export function ChapterList({ chapters, basePath }: { chapters: ChapterSummary[]; basePath: string }) {
  const groups: Array<{ category: string | null; chapters: ChapterSummary[] }> = [];
  for (const chapter of chapters) {
    const last = groups[groups.length - 1];
    if (last && last.category === chapter.category) last.chapters.push(chapter);
    else groups.push({ category: chapter.category, chapters: [chapter] });
  }
  return (
    <div className="grid gap-[var(--archive-space-4)]">
      {groups.map((group, index) => (
        <section key={`${index}:${group.category ?? ''}`} aria-label={group.category ?? 'Chapters'}>
          {group.category && (
            <h3 className="mb-[var(--archive-space-2)] text-sm font-semibold">
              <BilingualTitle text={group.category} />
            </h3>
          )}
          <ol className="archive-rule">
            {group.chapters.map((chapter) => (
              <li key={chapter.key} className="border-b border-[color:var(--archive-rule)]">
                <Link
                  href={`${basePath}/${encodeURIComponent(chapter.key)}`}
                  className="archive-focus grid grid-cols-[4rem_1fr_auto] items-baseline gap-[var(--archive-space-3)] py-[var(--archive-space-2)] hover:text-[color:var(--archive-accent)]"
                >
                  <span className="text-sm tabular-nums text-[color:var(--archive-muted)]">{chapter.number ?? '—'}</span>
                  <span className="min-w-0">{chapter.name ? <BilingualTitle text={chapter.name} /> : 'Untitled chapter'}</span>
                  <span className="text-sm tabular-nums text-[color:var(--archive-muted)]">{number(chapter.reportCount)}</span>
                </Link>
              </li>
            ))}
          </ol>
        </section>
      ))}
    </div>
  );
}
