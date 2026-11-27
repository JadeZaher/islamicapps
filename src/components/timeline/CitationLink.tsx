import Link from 'next/link';
import type { TimelineCitation, TimelineTemporalAssertion } from '@/db/queries/timeline-contracts';
import { formatRange } from '@/db/queries/timeline-rules';
import { ArabicText } from '@/components/ArabicText';
import styles from './timeline.module.css';

function isHttpUrl(url: string | null | undefined): url is string {
  return typeof url === 'string' && /^https?:\/\//i.test(url.trim());
}

export function formatCitationLabel(citation: TimelineCitation): string {
  const workParts = [citation.author, citation.work_title || citation.work_title_ar].filter(Boolean);
  const locParts = [
    citation.volume ? `vol. ${citation.volume}` : null,
    citation.page ? `p. ${citation.page}` : null,
    citation.locator,
  ].filter(Boolean);
  const head = workParts.join(', ');
  const tail = locParts.join(', ');
  if (head && tail) return `${head} (${tail})`;
  return head || tail || 'Source';
}

export function CitationLink({ citation }: { citation?: TimelineCitation | null }) {
  if (!citation) return null;
  const label = formatCitationLabel(citation);
  const isCandidate = citation.review_state === 'candidate_only';
  const link = isHttpUrl(citation.url) ? (
    <a href={citation.url.trim()} target="_blank" rel="noopener noreferrer" className={styles.citationLink}>
      {label}
    </a>
  ) : (
    <Link href="/sources" className={styles.citationLink}>
      {label}
    </Link>
  );
  return (
    <span className={styles.citationWrap}>
      {link}
      {isCandidate && <span className={styles.candidateTag}>candidate</span>}
    </span>
  );
}

export function TemporalAssertionsList({ assertions }: { assertions?: TimelineTemporalAssertion[] }) {
  if (!assertions || assertions.length === 0) return null;
  return (
    <ul className={styles.assertionList}>
      {assertions.map((assertion) => {
        const range =
          assertion.year_min !== null
            ? formatRange({ min: assertion.year_min, max: assertion.year_max ?? assertion.year_min })
            : null;
        return (
          <li key={assertion.id} className={styles.assertionItem}>
            {range && <span className={styles.assertionYear}>{range}</span>}
            {assertion.statement_en ? (
              <span>{assertion.statement_en}</span>
            ) : assertion.stated_ar ? (
              <ArabicText>{assertion.stated_ar}</ArabicText>
            ) : (
              <span>{assertion.predicate}</span>
            )}
            {assertion.review_state === 'candidate_only' && <span className={styles.candidateTag}>candidate</span>}
            {assertion.citation && (
              <>
                {' · '}
                <CitationLink citation={assertion.citation} />
              </>
            )}
          </li>
        );
      })}
    </ul>
  );
}
