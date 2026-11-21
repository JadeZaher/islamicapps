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
    <main className="mx-auto max-w-3xl px-6 py-10 text-slate-100">
      <h1 className="text-3xl font-semibold">Glossary</h1>

      <form action="/glossary" role="search" className="mt-6 flex gap-2">
        <input
          type="search"
          name="q"
          defaultValue={q}
          aria-label="Filter terms"
          placeholder="Filter terms, in English, transliteration or Arabic"
          className="h-10 w-full rounded-md border border-slate-700 bg-slate-900 px-3 text-sm text-slate-100 placeholder:text-slate-500 outline-none focus-visible:border-emerald-500 focus-visible:ring-2 focus-visible:ring-emerald-500/40"
        />
        <Button type="submit" className="h-10 bg-emerald-600 text-white hover:bg-emerald-500">
          Filter
        </Button>
      </form>

      {q && (
        <p className="mt-4 text-sm text-slate-400" aria-live="polite">
          {entries.length} {entries.length === 1 ? 'term' : 'terms'} matching “{q}” ·{' '}
          <Link href="/glossary" className="text-slate-300 underline underline-offset-2 hover:text-white">
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
            <ul className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
              {sections.map((section) => (
                <li key={section.id}>
                  <a
                    href={`#section-${section.id}`}
                    className="rounded-sm text-slate-400 outline-none hover:text-slate-100 focus-visible:ring-2 focus-visible:ring-emerald-400"
                  >
                    {section.title}
                  </a>
                </li>
              ))}
            </ul>
          </nav>

          {sections.map((section) => (
            <section key={section.id} aria-labelledby={`section-${section.id}`} className="mt-10">
              <h2
                id={`section-${section.id}`}
                className="scroll-mt-6 text-xs font-semibold uppercase tracking-wider text-slate-500"
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

      <p className="mt-12 border-t border-slate-800 pt-4 text-xs leading-relaxed text-slate-500">{TRANSLITERATION_NOTE}</p>
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
      className="-mx-3 scroll-mt-6 rounded-md border-t border-slate-800 px-3 py-5 target:bg-slate-900"
    >
      <h3 id={`${entry.slug}-term`} className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="text-lg font-medium text-slate-100">{entry.term}</span>
        {entry.english && <span className="text-sm text-slate-400">{entry.english}</span>}
        {entry.arabic && <ArabicText className="text-xl text-slate-300">{entry.arabic}</ArabicText>}
      </h3>
      <p className="mt-1 text-slate-200">{entry.definition}</p>
      {entry.inArchive && (
        <p className="mt-2 text-sm text-slate-400">
          <span className="font-medium text-slate-300">In this archive. </span>
          {entry.inArchive}
        </p>
      )}
      {entry.acrossTraditions && (
        <p className="mt-2 text-sm text-slate-400">
          <span className="font-medium text-slate-300">Across traditions. </span>
          {entry.acrossTraditions}
        </p>
      )}
      {related.length > 0 && (
        <p className="mt-2 text-sm text-slate-500">
          Related:{' '}
          {related.map((target, index) => (
            <span key={target.slug}>
              {index > 0 && ', '}
              <a
                href={`/glossary#${target.slug}`}
                className="rounded-sm text-slate-300 underline decoration-slate-600 underline-offset-2 outline-none hover:text-white focus-visible:ring-2 focus-visible:ring-emerald-400"
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
