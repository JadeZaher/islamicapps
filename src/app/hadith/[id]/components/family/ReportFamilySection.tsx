'use client';

import Link from 'next/link';

import type { ReportFamily } from '@/db/queries/contracts';
import { hadithPath } from '@/lib/hadith-address';
import styles from './family.module.css';
import { FamilySummaryLine } from './FamilySummaryLine';
import { TellingsList } from './TellingsList';

/** Hadith-page section: the summary line and the tellings, with the full chains view one link away. */
export function ReportFamilySection({ family, hadithId }: { family: ReportFamily; hadithId: string }) {
  const href = `${hadithPath(hadithId)}/chains`;
  const hasOthers = family.tellings.length > 1;
  return (
    <div className={`${styles.family} max-w-[var(--measure-wide)]`}>
      <FamilySummaryLine family={family} />
      {hasOthers && (
        <div className="mt-6">
          <TellingsList tellings={family.tellings} mode="public" />
        </div>
      )}
      <p className="mt-6 type-small">
        <Link href={href} className={styles.link}>
          {hasOthers ? 'Every chain of every telling, with the combined diagram' : 'This report’s chains on one page'}
        </Link>
      </p>
    </div>
  );
}
