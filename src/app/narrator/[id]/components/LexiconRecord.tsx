import Link from 'next/link';
import type { NarratorLexicon } from '@/db/queries/contracts';
import { SourceCredit } from '@/components/archive/SourceCredit';

/** "40 BH / 582 CE", "18 AH / 639 CE"; null when neither year is recorded. */
function lexiconDate(hijri: number | null, gregorian: number | null): string | null {
  const parts = [
    hijri === null ? null : hijri < 0 ? `${-hijri} BH` : `${hijri} AH`,
    gregorian === null ? null : `${gregorian} CE`,
  ].filter(Boolean);
  return parts.length > 0 ? parts.join(' / ') : null;
}

/** "entry 10" from the lexicon locator `all_rawis.csv#scholar_indx=10`. */
function lexiconEntry(locator: string | null): string | null {
  const match = locator?.match(/scholar_indx=(\d+)/);
  return match ? `entry ${match[1]}` : null;
}

/**
 * The narrator lexicon's dates and places on a public narrator page, labelled as an uncited lexicon claim with its
 * source reference (owner decision 2026-11-21). See src/db/queries/AGENTS.md §Lexicon on public narrator pages.
 */
export function LexiconRecord({ lexicon }: { lexicon: NarratorLexicon }) {
  const deathHeld = lexicon.held_back.find((item) => item.field === 'death_year');
  const rows: Array<[string, string]> = [
    ['Born', [lexiconDate(lexicon.birth_year_hijri, lexicon.birth_year_gregorian), lexicon.birth_place].filter(Boolean).join(', ')],
    ['Died', [lexiconDate(lexicon.death_year_hijri, lexicon.death_year_gregorian), lexicon.death_place].filter(Boolean).join(', ')],
    ['Region', lexicon.geographic_region ?? ''],
  ].filter((row): row is [string, string] => row[1] !== '');
  if (rows.length === 0 && !deathHeld) return null;

  return (
    <section aria-labelledby="lexicon-heading" className="mb-12 max-w-[var(--measure-wide)]" data-lexicon-record>
      <h2 id="lexicon-heading" className="type-label mb-1">
        Dates and places
      </h2>
      <p className="mb-3 type-small text-ink-muted">
        <Link href="/glossary#rijal" className="link-term">
          Narrator lexicon, not yet cited
        </Link>
      </p>
      {rows.length > 0 && (
        <dl className="grid grid-cols-[7rem_minmax(0,1fr)] gap-x-4 gap-y-2 type-small">
          {rows.map(([label, value]) => (
            <div key={label} className="contents">
              <dt className="text-ink-muted">{label}</dt>
              <dd className="text-ink tabular-nums">{value}</dd>
            </div>
          ))}
        </dl>
      )}
      {deathHeld && (
        <p className="mt-2 type-small text-ink-muted" data-held-back="death_year">
          Death year held back until reviewed: {deathHeld.reason}
          {deathHeld.taqrib_entry ? ` (Taqrib entry ${deathHeld.taqrib_entry})` : ''}.
        </p>
      )}
      <div className="mt-3 space-y-1">
        <SourceCredit code="MSD" role="Lexicon" detail={lexiconEntry(lexicon.source_locator)} />
        {deathHeld && <SourceCredit code="RIJ" role="Compared with" detail="Ibn Hajar, Taqrib al-Tahdhib" />}
      </div>
    </section>
  );
}
