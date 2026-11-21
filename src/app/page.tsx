import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { HADITH_TRADITIONS, SearchIcon, TraditionMark } from '@/components/marks';
import { HADITH_TRADITION_OPTIONS } from '@/lib/constants/traditions';

// Alphabetical: no tradition is listed as the default (DESIGN.md §Principles).
const TRADITION_LINKS = HADITH_TRADITION_OPTIONS.filter((option) => option.value).sort((a, b) => a.value.localeCompare(b.value));

function TraditionMarkFor({ tradition }: { tradition: string }) {
  const known = HADITH_TRADITIONS.find((name) => name === tradition);
  return known ? <TraditionMark tradition={known} decorative /> : null;
}

/** Home (DESIGN.md: the one page with display type). Flush left on the 12-column grid; search is the primary action. */
export default function HomePage() {
  return (
    <main className="wrap pb-12 pt-16 lg:pt-24">
      <div className="max-w-[var(--measure-wide)]">
        <h1 className="type-display text-ink max-sm:text-[2.25rem] max-sm:leading-[2.5rem]">Shura wa Istehsan</h1>
        <p className="mt-3 type-reading text-ink-muted">
          Hadith and narrators across the Sunni, Imami, Zaydi and Ibadi traditions.
        </p>

        <form action="/hadith" role="search" className="mt-12 flex max-w-[var(--measure-reading)] gap-2">
          <div className="relative w-full">
            <SearchIcon decorative className="pointer-events-none absolute start-3 top-1/2 -translate-y-1/2 text-ink-muted" />
            <input
              type="search"
              name="q"
              dir="auto"
              aria-label="Search hadith"
              placeholder="Chapter, topic or text"
              className="h-11 w-full border border-control bg-surface ps-10 pe-3 text-base text-ink placeholder:text-ink-muted focus-visible:border-focus focus-visible:outline-offset-0"
            />
          </div>
          <Button type="submit" size="lg">
            Search
          </Button>
        </form>
      </div>

      <nav aria-labelledby="browse-by-tradition" className="mt-24 border-t border-rule-strong pt-3">
        <h2 id="browse-by-tradition" className="type-label">
          Browse by tradition
        </h2>
        <ul className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
          {TRADITION_LINKS.map((option) => (
            <li key={option.value} className="border-b border-rule">
              <Link
                href={`/hadith?tradition=${encodeURIComponent(option.value)}`}
                className="flex min-h-12 items-center gap-3 py-3 pe-4 font-medium text-ink no-underline hover:[&>span]:decoration-accent"
              >
                <TraditionMarkFor tradition={option.value} />
                <span className="underline decoration-rule decoration-1 underline-offset-[0.2em] transition-colors duration-[var(--motion-fast)]">
                  {option.value}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </main>
  );
}
