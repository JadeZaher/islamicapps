import type { EnglishAttribution } from '@/db/queries/contracts';
import { ReportSourceCredit } from './SourceCredit';
import type { SourceCode } from '@/lib/sources/registry';

/** The line shown where a report has no public English (owner, 2026-11-21): said once, never a silent gap. */
export const NO_ENGLISH = 'No English available yet';

/**
 * A report's English beneath its Arabic: the label from `englishLabel` ("Source-provided English, not reviewed here"),
 * the text, and the credit from `englishReference` (source and translator). Without English, the one line `NO_ENGLISH`.
 * Reading size on the report page, body size in the tellings list. DESIGN.md §Report reading column.
 */
export function ReportEnglish({
  text,
  attribution,
  note,
  size = 'reading',
  clamped = false,
  className,
}: {
  text: string | null | undefined;
  attribution: EnglishAttribution | null | undefined;
  /** Appended to the label, e.g. " · includes the chain". */
  note?: string;
  size?: 'reading' | 'body';
  /** Cut to four lines (the tellings list's collapsed rows); the full text is one click away. */
  clamped?: boolean;
  className?: string;
}) {
  if (!text?.trim() || !attribution) {
    return (
      <p className={`type-small text-ink-muted ${className ?? ''}`} data-english="none">
        {NO_ENGLISH}
      </p>
    );
  }
  return (
    <div className={className} data-english={attribution.state}>
      <p className="mb-1 type-small text-ink-muted" data-english-label>
        {attribution.label}
        {note}
      </p>
      <p
        lang="en"
        className={`whitespace-pre-line text-ink ${size === 'reading' ? 'type-reading' : 'text-base leading-6'} ${clamped ? 'line-clamp-4' : ''}`}
      >
        {text}
      </p>
      {attribution.reference && <ReportSourceCredit reference={attribution.reference} />}
    </div>
  );
}

/**
 * The one-line form for report lists: label and source code under the English excerpt. The row is one link, so the code
 * is text here; the list's footnote credits each source with its link (`ReportList`).
 */
export function ListEnglishLabel({ label, code }: { label: string; code: SourceCode | null }) {
  return (
    <span className="mt-0.5 block text-xs leading-4 text-ink-muted" data-english-label>
      {label}
      {code && <> · <span className="archive-code" data-source-ref={code}>{code}</span></>}
    </span>
  );
}
