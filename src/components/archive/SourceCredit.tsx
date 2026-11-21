import Link from 'next/link';
import { sourceByCode, sourceRecordHref, type SourceCode } from '@/lib/sources/registry';
import type { SourceReference } from '@/lib/sources/report-credit';

interface SourceCreditProps {
  code: SourceCode;
  /** What the credited material is, e.g. "Text", "English", "Grading", "Identity". */
  role?: string;
  /** Work and author, translator, grader, etc. */
  detail?: string | null;
  /** This item at the provider, when the register asks for a link to it. */
  external?: string | null;
  className?: string;
}

/**
 * The one short source reference: role, code and source name linking to its record on /sources, the licence, and
 * an optional detail. Full required wording lives on the record. Shared by every surface that shows borrowed material.
 * Layout: DESIGN.md §Source short references.
 */
export function SourceCredit({ code, role, detail, external, className }: SourceCreditProps) {
  const record = sourceByCode(code);
  return (
    <p data-source-ref={code} className={`type-small text-ink-muted [overflow-wrap:anywhere] ${className ?? ''}`}>
      {role && <span className="text-ink">{`${role}: `}</span>}
      <Link href={sourceRecordHref(code)} className="archive-link text-ink-muted">
        <span className="archive-code">{code}</span> {record.name}
      </Link>
      {detail && <span> · {detail}</span>}
      <span> · </span>
      {record.licence.url ? (
        <a href={record.licence.url} className="archive-link text-ink-muted" rel="license noopener" target="_blank">
          {record.licence.name}
        </a>
      ) : (
        <span>{record.licence.name}</span>
      )}
      {external && (
        <>
          <span> · </span>
          <a href={external} className="archive-link text-ink-muted" rel="noopener" target="_blank">
            View at source
          </a>
        </>
      )}
    </p>
  );
}

/**
 * The inline form of the same reference: the source code alone, linking to its record (name as its accessible label).
 * For a line that credits one item among many (a chain name); the chain's full `SourceCredit` lines sit beside it.
 */
export function SourceCodeLink({ code, className }: { code: SourceCode; className?: string }) {
  const record = sourceByCode(code);
  return (
    <Link
      href={sourceRecordHref(code)}
      data-source-ref={code}
      aria-label={`Source: ${record.name}`}
      title={record.name}
      className={`archive-link archive-code text-ink-muted ${className ?? ''}`}
    >
      {code}
    </Link>
  );
}

/** A report reference (from reportSourceReferences) as a SourceCredit. */
export function ReportSourceCredit({ reference }: { reference: SourceReference }) {
  return <SourceCredit code={reference.code} role={reference.role} detail={reference.detail} external={reference.external} />;
}
