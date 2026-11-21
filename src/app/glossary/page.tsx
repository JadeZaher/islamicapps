import type { Metadata } from 'next';
import Link from 'next/link';
import { ArabicText } from '@/components/ArabicText';
import { EmptyState } from '@/components/EmptyState';
import { Button } from '@/components/ui/button';
import {
  GLOSSARY_ENTRIES,
  GLOSSARY_SECTIONS,
  TRANSLITERATION_NOTE,
  getGlossaryEntry,
  matchesGlossaryQuery,
  type GlossaryEntry,
} from '@/lib/glossary/terms';

export const metadata: Metadata = {
  title: 'Glossary',
  description: 'Definitions of the terms used across the archive, its traditions and its data.',
};

interface PageProps {
  searchParams: Promise<{ q?: string | string[] }>;
}

/** Server-rendered glossary; the filter is a plain GET form, so the page reads and filters without JavaScript. */
export default async function GlossaryPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const q = (Array.isArray(params.q) ? params.q[0] : params.q)?.trim() ?? '';
  const entries = q ? GLOSSARY_ENTRIES.filter((entry) => matchesGlossaryQuery(entry, q)) : GLOSSARY_ENTRIES;
  const sections = GLOSSARY_SECTIONS.map((section) => ({
    ...section,
    entries: entries.filter((entry) => entry.section === section.id),
  })).filter((section) => section.entries.length > 0);

  return (
    <main className="wrap pb-12 text-ink">
      <h1 className="page-header type-h1">Glossary</h1>

      <form action="/glossary" role="search" className="mt-8 flex max-w-[var(--measure-reading)] gap-2">
        <input
          type="search"
          name="q"
          defaultValue={q}
          aria-label="Filter terms"
          placeholder="Filter terms, in English, transliteration or Arabic"
          dir="auto"
          className="h-10 w-full border border-control bg-surface px-3 text-base text-ink placeholder:text-ink-muted focus-visible:border-focus focus-visible:outline-offset-0"
        />
        <Button type="submit">
          Filter
        </Button>
      </form>

      {q && (
        <p className="mt-4 text-sm text-ink-muted" aria-live="polite">
          {entries.length} {entries.length === 1 ? 'term' : 'terms'} matching “{q}” ·{' '}
          <Link href="/glossary" className="link-row text-ink">
            Show all
          </Link>
        </p>
      )}

      {sections.length === 0 ? (
        <EmptyState
          className="mt-6"
          title="No terms found"
          description="Try another spelling, the Arabic, or an English word."
          action={
            <Button asChild variant="outline" size="sm">
              <Link href="/glossary">Show all terms</Link>
            </Button>
          }
        />
      ) : (
        <>
          <nav aria-label="Glossary sections" className="mt-6">
            <ul className="flex flex-wrap gap-x-5 gap-y-1 type-small">
              {sections.map((section) => (
                <li key={section.id}>
                  <a
                    href={`#section-${section.id}`}
                    className="link-row inline-block py-2 text-ink-muted hover:text-ink"
                  >
                    {section.title}
                  </a>
                </li>
              ))}
            </ul>
          </nav>

          {sections.map((section) => (
            <section key={section.id} aria-labelledby={`section-${section.id}`} className="section-rule mt-12 max-w-[var(--measure-reading)]">
              <h2
                id={`section-${section.id}`}
                className="type-label scroll-mt-6"
              >
                {section.title}
              </h2>
              <div className="mt-2">
                {section.entries.map((entry) => (
                  <GlossaryEntryArticle key={entry.slug} entry={entry} />
                ))}
              </div>
            </section>
          ))}
        </>
      )}

      <p className="mt-12 max-w-[var(--measure-reading)] border-t border-rule pt-4 type-small text-ink-muted">{TRANSLITERATION_NOTE}</p>
    </main>
  );
}

/** One term: heading with its anchor id, the plain definition, then the archive and cross-tradition notes. */
function GlossaryEntryArticle({ entry }: { entry: GlossaryEntry }) {
  const related = (entry.related ?? []).flatMap((slug) => {
    const target = getGlossaryEntry(slug);
    return target ? [target] : [];
  });

  return (
    <article
      id={entry.slug}
      aria-labelledby={`${entry.slug}-term`}
      className="scroll-mt-6 border-t border-rule py-5 first:border-t-0 target:bg-accent-wash target:shadow-[inset_2px_0_0_var(--color-accent)] target:px-3"
    >
      <h3 id={`${entry.slug}-term`} className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="type-h3 text-ink">{entry.term}</span>
        {entry.english && <span className="text-sm text-ink-muted">{entry.english}</span>}
        {entry.arabic && <ArabicText variant="inline" className="text-ink">{entry.arabic}</ArabicText>}
      </h3>
      <p className="mt-2 text-ink">{entry.definition}</p>
      {entry.inArchive && (
        <p className="mt-2 text-sm text-ink-muted">
          <span className="font-medium text-ink">In this archive. </span>
          {entry.inArchive}
        </p>
      )}
      {entry.acrossTraditions && (
        <p className="mt-2 text-sm text-ink-muted">
          <span className="font-medium text-ink">Across traditions. </span>
          {entry.acrossTraditions}
        </p>
      )}
      {related.length > 0 && (
        <p className="mt-2 text-sm text-ink-muted">
          Related:{' '}
          {related.map((target, index) => (
            <span key={target.slug}>
              {index > 0 && ', '}
              <a
                href={`/glossary#${target.slug}`}
                className="link-row text-ink"
              >
                {target.term}
              </a>
            </span>
          ))}
        </p>
      )}
    </article>
  );
}
