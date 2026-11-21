/**
 * Source credits for the report family and chain surfaces, through the shared `SourceCredit` (one short reference: code
 * and name linking to the source record). Each renders a block `<p>`, so place it beside, never inside, a paragraph.
 */
import { SourceCredit } from '@/components/archive/SourceCredit';
import type { IdentityBasis } from '@/db/queries/contracts';
import { sourceCodeForHadithId, sourceForGrading, sourceForIdentityBasis, type SourceCode } from '@/lib/sources/registry';

/** The text source of a report (telling, or the chain extracted from its text). */
export function TextCredit({ hadithId, role = 'Text', className }: { hadithId: string; role?: string; className?: string }) {
  const code = sourceCodeForHadithId(hadithId);
  return code ? <SourceCredit code={code} role={role} className={className} /> : null;
}

/** The datasets behind one identity claim: one credit per distinct source among its bases (K6 index, lexicon, review). */
export function IdentityCredit({ bases, className }: { bases: IdentityBasis[]; className?: string }) {
  const codes = [...new Set(bases.map((basis) => sourceForIdentityBasis(basis)))] as SourceCode[];
  return (
    <>
      {codes.map((code) => (
        <SourceCredit key={code} code={code} role="Identity" className={className} />
      ))}
    </>
  );
}

/** The source of the gradings shipped with a report's text (Thaqalayn records the Imami graders). */
export function GradingCredit({ hadithId, className }: { hadithId: string; className?: string }) {
  const text = sourceCodeForHadithId(hadithId);
  return text ? <SourceCredit code={sourceForGrading(text)} role="Grading" className={className} /> : null;
}
