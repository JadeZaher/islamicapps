import Link from 'next/link';
import type { ReactNode } from 'react';
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

/** The lexicon's generation classes in plain words. */
const GENERATION_CLASS: Record<string, string> = {
  'Comp.(RA)': 'Companion',
  "Follower(Tabi')": 'Follower (tābiʿī)',
  "Succ. (Taba' Tabi')": 'Follower of the Followers',
  "Prophet's Relative": "Relative of the Prophet",
  'Rasool Allah': 'The Prophet',
};

/** "Comp.(RA) [1st Generation]" -> "Companion, 1st generation"; other bracketed notes are not a generation. */
export function generationLabel(raw: string | null): string | null {
  if (!raw) return null;
  const base = raw.replace(/\s*\[[^\]]*\]/g, '').trim();
  const ordinal = raw.match(/\[\s*(\d+(?:st|nd|rd|th))\s+generation\s*\]/i);
  const label = [GENERATION_CLASS[base] ?? (base || null), ordinal ? `${ordinal[1]} generation` : null].filter(Boolean);
  return label.length > 0 ? label.join(', ') : null;
}

/** "Zaynab bint Maz'un [124] , Umm Walad(Fakhihah)" -> names, each with its lexicon entry when the source gives one. */
export function lexiconPeople(value: string): Array<{ name: string; entry: string | null }> {
  return value
    .split(/\s*,\s*|\s+\/\s+/)
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => {
      const match = part.match(/^(.*?)\s*\[(\d+)\]$/);
      return match ? { name: match[1], entry: match[2] } : { name: part, entry: null };
    });
}

function People({ value }: { value: string }) {
  const people = lexiconPeople(value);
  return (
    <>
      {people.map((person, index) => (
        <span key={`${person.name}:${index}`}>
          {index > 0 && ', '}
          {person.entry ? (
            <Link href={`/narrator/${encodeURIComponent(`narrator:rawi:${person.entry}`)}`} className="link-row">
              {person.name}
            </Link>
          ) : (
            person.name
          )}
        </span>
      ))}
    </>
  );
}

/** Label and value of every field the lexicon records for this narrator, in reading order. */
function lexiconRows(lexicon: NarratorLexicon): Array<[string, ReactNode]> {
  const fields = lexicon.source_fields;
  const death = [
    lexiconDate(lexicon.death_year_hijri, lexicon.death_year_gregorian),
    lexicon.death_place,
  ].filter(Boolean).join(', ');
  const rows: Array<[string, ReactNode]> = [
    ['Generation', generationLabel(lexicon.generation)],
    ['Born', [lexiconDate(lexicon.birth_year_hijri, lexicon.birth_year_gregorian), lexicon.birth_place].filter(Boolean).join(', ')],
    ['Died', death && lexicon.death_reason ? `${death} (${lexicon.death_reason.toLowerCase()})` : death],
    ['Region', lexicon.geographic_region],
    ['Lived in', fields.places_of_stay],
    ['Parents', fields.parents && <People value={fields.parents} />],
    ['Spouses', fields.spouse && <People value={fields.spouse} />],
    ['Siblings', fields.siblings && <People value={fields.siblings} />],
    ['Children', fields.children && <People value={fields.children} />],
    ['Known for', fields.tags],
    ['Fields', fields.area_of_interest],
  ];
  return rows.filter((row) => Boolean(row[1]));
}

/** True when the lexicon has something to show (a field, or a held-back death year to explain). */
export function hasLexiconRecord(lexicon: NarratorLexicon | null): lexicon is NarratorLexicon {
  return Boolean(lexicon) && (lexiconRows(lexicon as NarratorLexicon).length > 0 || (lexicon as NarratorLexicon).held_back.length > 0);
}

/**
 * The narrator lexicon's own record, shown as the biography until a reviewed one exists: generation, dates, places,
 * family and tags, labelled as an uncited lexicon claim credited to MSD. See src/db/queries/AGENTS.md §Lexicon on
 * public narrator pages.
 */
export function LexiconRecord({ lexicon }: { lexicon: NarratorLexicon }) {
  const deathHeld = lexicon.held_back.find((item) => item.field === 'death_year');
  const rows = lexiconRows(lexicon);
  if (rows.length === 0 && !deathHeld) return null;

  return (
    <section aria-labelledby="lexicon-heading" className="max-w-[var(--measure-wide)]" data-lexicon-record>
      <h2 id="lexicon-heading" className="section-rule type-label mb-1">
        The lexicon&apos;s record
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
