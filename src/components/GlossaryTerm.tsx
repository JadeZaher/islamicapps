import { useId, type ReactNode } from 'react';
import Link from 'next/link';
import { getGlossaryEntry, glossaryHref } from '@/lib/glossary/terms';
import { cn } from '@/lib/utils';

interface GlossaryTermProps {
  /** Glossary slug, e.g. "kunya". */
  slug: string;
  /** Visible text; defaults to the glossary term. */
  children?: ReactNode;
  className?: string;
}

/**
 * A term linked to its glossary entry. The one-sentence definition is the link's accessible description
 * (aria-describedby) and its title, so keyboard and screen-reader users get it without hovering.
 * Use from server components: importing it into a client component ships the whole glossary to the browser.
 */
export function GlossaryTerm({ slug, children, className }: GlossaryTermProps) {
  const descriptionId = useId();
  const entry = getGlossaryEntry(slug);
  if (!entry) return <>{children ?? slug}</>;

  return (
    <>
      <Link
        href={glossaryHref(entry.slug)}
        title={entry.definition}
        aria-describedby={descriptionId}
        className={cn(
          'link-term',
          className,
        )}
      >
        {children ?? entry.term}
      </Link>
      <span id={descriptionId} hidden>
        {entry.definition}
      </span>
    </>
  );
}
