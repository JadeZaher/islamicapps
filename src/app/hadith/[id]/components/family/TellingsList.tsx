'use client';

import { useState } from 'react';
import Link from 'next/link';

import { ArabicText } from '@/components/ArabicText';
import { BilingualTitle } from '@/components/NarratorName';
import { TraditionMark as TraditionModule } from '@/components/marks';
import type { FamilyTelling, HadithTraditionCode } from '@/db/queries/contracts';
import { hadithPath } from '@/lib/hadith-address';
import { ownMatn } from '../../matn';
import styles from './family.module.css';
import { correspondenceLabel, groupTellings, tellingReference, withinWorkReference } from './labels';
import { TextCredit } from './SourceCredits';

/** The text a telling is compared on: its own matn when stored, else the full text as in the source. */
export function tellingText(telling: FamilyTelling): { text: string | null; isMatn: boolean } {
  const matn = ownMatn(telling.matn_ar, telling.text_ar);
  return matn ? { text: matn, isMatn: true } : { text: telling.text_ar, isMatn: false };
}

/** The tradition's module (DESIGN.md §Tradition marks); decorative, because the name always follows it. */
export function TraditionMark({ tradition }: { tradition: HadithTraditionCode }) {
  return <TraditionModule tradition={tradition} decorative className={styles.mark} />;
}

/** Where a telling links: its public page, or the curator preview of its family. */
export function tellingHref(hadithId: string, mode: 'public' | 'curator'): string {
  return mode === 'public' ? hadithPath(hadithId) : `/admin/correspondences/family/${encodeURIComponent(hadithId)}`;
}

function TellingRow({ telling, mode, reviewHrefBase, focalId, clampLines }: {
  telling: FamilyTelling;
  mode: 'public' | 'curator';
  reviewHrefBase?: string;
  focalId: string;
  clampLines: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const { text, isMatn } = tellingText(telling);
  const label = telling.correspondence ? correspondenceLabel(telling.correspondence) : null;
  const textId = `telling-text-${telling.hadith_id.replace(/[^a-zA-Z0-9_-]/g, '-')}`;
  return (
    <li>
      <div className={styles.rowHead}>
        <p>
          {/* The work is the heading above; the row names the report within it. */}
          <Link href={tellingHref(telling.hadith_id, mode)} className={styles.link} aria-label={tellingReference(telling)}>
            {withinWorkReference(telling)}
          </Link>
        </p>
        {label && (
          <p className="type-small">
            <span>{label.kind}</span>
            <span className={styles.muted}> · {label.status}</span>
            {label.measure && <span className={styles.muted}> · {label.measure}</span>}
            {reviewHrefBase && (
              <>
                <span className={styles.muted}> · </span>
                <Link
                  href={`${reviewHrefBase}?a=${encodeURIComponent(focalId)}&b=${encodeURIComponent(telling.hadith_id)}`}
                  className={styles.link}
                >
                  Review
                </Link>
              </>
            )}
          </p>
        )}
      </div>
      <TextCredit hadithId={telling.hadith_id} className="mt-1 !text-xs !leading-4" />
      {telling.chapter && (
        <p className={`mt-1 type-small ${styles.muted}`}>
          <BilingualTitle text={telling.chapter} />
        </p>
      )}
      {text && (
        <div className="mt-2">
          <ArabicText
            as="p"
            id={textId}
            className={`whitespace-pre-line ${styles.arabic} ${clampLines && !expanded ? styles.clamped : ''}`}
          >
            {text}
          </ArabicText>
          <div className={styles.meta}>
            <span>{isMatn ? 'Report text, chain omitted' : 'Text as in the source, chain included'}</span>
            {clampLines && (
              <button
                type="button"
                aria-expanded={expanded}
                aria-controls={textId}
                onClick={() => setExpanded((value) => !value)}
                className={styles.textButton}
              >
                {expanded ? 'Show less' : 'Show full text'}
              </button>
            )}
          </div>
        </div>
      )}
    </li>
  );
}

interface TellingsListProps {
  tellings: FamilyTelling[];
  /** Link target for each telling: its public page, or the curator preview in /admin. */
  mode: 'public' | 'curator';
  /** Curator mode: link each pair to its review screen. */
  reviewHrefBase?: string;
  clampLines?: boolean;
}

/** Every other telling, grouped by tradition and then by work, each with its text and how it corresponds. */
export function TellingsList({ tellings, mode, reviewHrefBase, clampLines = true }: TellingsListProps) {
  const focalId = tellings.find((telling) => telling.is_focal)?.hadith_id ?? '';
  const groups = groupTellings(tellings);
  if (groups.length === 0) {
    return <p className={styles.secondary}>No other telling of this report has been found in the archive.</p>;
  }
  return (
    <div className="space-y-8">
      {groups.map((group) => {
        const count = group.works.reduce((sum, work) => sum + work.tellings.length, 0);
        return (
          <section key={group.tradition} aria-labelledby={`tellings-${group.tradition}`}>
            <h3 id={`tellings-${group.tradition}`} className={styles.groupHeading}>
              <span>
                <TraditionMark tradition={group.tradition} />
                {group.tradition}
              </span>
              <span className={styles.muted}>
                {count} {count === 1 ? 'telling' : 'tellings'}
              </span>
            </h3>
            {group.works.map((work) => (
              <div key={work.work}>
                <h4 className={styles.workHeading}>{work.work}</h4>
                <ul className={styles.rows}>
                  {work.tellings.map((telling) => (
                    <TellingRow
                      key={telling.hadith_id}
                      telling={telling}
                      mode={mode}
                      reviewHrefBase={reviewHrefBase}
                      focalId={focalId}
                      clampLines={clampLines}
                    />
                  ))}
                </ul>
              </div>
            ))}
          </section>
        );
      })}
    </div>
  );
}
