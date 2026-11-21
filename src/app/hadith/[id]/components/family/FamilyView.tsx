'use client';

import Link from 'next/link';

import { ArabicText } from '@/components/ArabicText';
import type { ReportFamily } from '@/db/queries/contracts';
import { hadithPath } from '@/lib/hadith-address';
import { AllChains } from './AllChains';
import styles from './family.module.css';
import { FamilySummaryLine } from './FamilySummaryLine';
import { tellingReference } from './labels';
import { TextCredit } from './SourceCredits';
import { TellingsList, tellingText } from './TellingsList';
import { TransmissionDiagram } from './TransmissionDiagram';

interface FamilyViewProps {
  family: ReportFamily;
  /** Public pages, or the curator preview in /admin (each pair then links to its review screen). */
  mode: 'public' | 'curator';
  /** `div` inside a layout that already has a main landmark (the admin preview). */
  container?: 'main' | 'div';
  /** Server-rendered chain timeline of the family (history lane), shown after the diagram. */
  timeline?: React.ReactNode;
}

/**
 * The full family page: summary, the report, its tellings, the combined diagram and every chain as lists.
 * See src/app/hadith/[id]/AGENTS.md §Report family.
 */
export function FamilyView({ family, mode, container: Container = 'main', timeline = null }: FamilyViewProps) {
  const focal = family.tellings.find((telling) => telling.is_focal)!;
  const { text, isMatn } = tellingText(focal);
  const listsId = 'all-chains';
  const reviewHrefBase = mode === 'curator' ? '/admin/correspondences/review' : undefined;
  const backHref = hadithPath(focal.hadith_id);
  return (
    <Container className={`${styles.family} wrap pb-12`}>
      <header className="page-header !pt-4">
        <p className="type-small">
          <Link href={backHref} className={styles.link}>{tellingReference(focal)}</Link>
        </p>
        <h1 className="type-h1 mt-3">Tellings and chains</h1>
        <div className="mt-3 max-w-[var(--measure-wide)]">
          <FamilySummaryLine family={family} />
          <p className={`mt-2 type-small ${styles.muted}`}>
            Correspondences are found by shared wording and are evidence, not rulings: they say nothing about which telling
            is earlier or more authentic. Each chain stays with the tradition and work it comes from.{' '}
            <Link href="/glossary#report-correspondence" className={styles.link}>How tellings are matched</Link>
          </p>
        </div>
      </header>

      {text && (
        <section className={styles.section} aria-labelledby="focal-heading">
          <h2 id="focal-heading" className={styles.label}>This report</h2>
          <ArabicText as="p" variant="reading" className="max-w-[var(--measure-reading)] whitespace-pre-line text-ink">{text}</ArabicText>
          <p className={styles.meta}>{isMatn ? 'Report text, chain omitted' : 'Text as in the source, chain included'}</p>
          <TextCredit hadithId={focal.hadith_id} className="mt-2" />
        </section>
      )}

      <section className={styles.section} aria-labelledby="tellings-heading">
        <h2 id="tellings-heading" className={styles.label}>Tellings of this report</h2>
        <div className="max-w-[var(--measure-wide)]">
          <TellingsList tellings={family.tellings} mode={mode} reviewHrefBase={reviewHrefBase} />
        </div>
      </section>

      <section className={styles.section} aria-labelledby="diagram-heading">
        <h2 id="diagram-heading" className={styles.label}>Combined transmission diagram</h2>
        <TransmissionDiagram tellings={family.tellings} listsId={listsId} />
      </section>

      {timeline && <div className={styles.section}>{timeline}</div>}

      <section id={listsId} className={styles.section} aria-labelledby="chains-heading">
        <h2 id="chains-heading" className={styles.label}>All chains</h2>
        <p className={`mb-6 max-w-[var(--measure-reading)] type-small ${styles.muted}`}>
          Every chain of every telling, in order from the compiler&apos;s informant to the earliest narrator, with each
          name as written. This is the same content as the diagram above.
        </p>
        <div className="max-w-[var(--measure-reading)]">
          <AllChains tellings={family.tellings} />
        </div>
      </section>
    </Container>
  );
}
