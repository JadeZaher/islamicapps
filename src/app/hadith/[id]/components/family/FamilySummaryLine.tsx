import type { ReportFamily } from '@/db/queries/contracts';
import { familySummary } from '@/db/queries/family-graph';
import styles from './family.module.css';

function plural(count: number, one: string, many: string) {
  return `${count.toLocaleString('en')} ${count === 1 ? one : many}`;
}

/** One honest sentence: how many tellings, works, traditions and chains, and how many names carry an identity. */
export function FamilySummaryLine({ family }: { family: ReportFamily }) {
  const summary = familySummary(family.tellings);
  const others = summary.tellings - 1;
  return (
    <p className={styles.summary}>
      {others === 0 ? (
        <>No other telling of this report has been found. </>
      ) : (
        <>
          <strong>{plural(summary.tellings, 'telling', 'tellings')}</strong> in {plural(summary.works, 'work', 'works')} across{' '}
          {plural(summary.traditions.length, 'tradition', 'traditions')} ({summary.traditions.join(', ')}).{' '}
        </>
      )}
      <strong>{plural(summary.chains, 'chain', 'chains')}</strong>
      {summary.names > 0 && (
        <>
          {' '}
          naming {plural(summary.names, 'narrator', 'narrators')}: {summary.identified.toLocaleString('en')} identified,{' '}
          {(summary.names - summary.identified).toLocaleString('en')} shown as written
          {summary.suggested > 0 && <> ({summary.suggested.toLocaleString('en')} with a suggested match)</>}
        </>
      )}
      .
      {family.capped && (
        <>
          {' '}
          Showing the {family.cap} closest of {family.correspondences_total.toLocaleString('en')} corresponding reports.
        </>
      )}
    </p>
  );
}
