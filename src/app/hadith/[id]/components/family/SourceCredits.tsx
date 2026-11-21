/**
 * Source credits for the report family and chain surfaces, through the shared `SourceCredit` (one short reference: code
 * and name linking to the source record). Each renders a block `<p>`, so place it beside, never inside, a paragraph.
 */
import { SourceCredit } from '@/components/archive/SourceCredit';
import type { ChainGraph, IdentityBasis } from '@/db/queries/contracts';
import {
  sourceCodeForHadithId,
  sourceForGrading,
  sourceForIdentityBasis,
  sourceForLatinName,
  sourcesForIdentityClaim,
  type SourceCode,
} from '@/lib/sources/registry';

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

/**
 * Every source a chain list draws on for names and identities, each once, next to the chain (reconciled/README.md §e):
 * role "Identity" for identity claims, "Latin name" for the Latin forms. The rows carry the inline codes.
 */
export function ChainSourceCredits({ chain }: { chain: ChainGraph | null }) {
  const identity = new Set<SourceCode>();
  const latin = new Set<SourceCode>();
  for (const node of chain?.nodes ?? []) {
    for (const candidate of node.candidates) {
      for (const code of sourcesForIdentityClaim(candidate.basis, candidate.origin, chain?.tradition ?? null)) identity.add(code);
    }
    if (node.name_latin_basis) latin.add(sourceForLatinName(node.name_latin_basis, node.name_latin_narrator_id));
  }
  if (identity.size === 0 && latin.size === 0) return null;
  return (
    <div className="mt-4 space-y-0.5" data-chain-credits>
      {[...identity].sort().map((code) => (
        <SourceCredit key={`identity-${code}`} code={code} role="Identity" className="!text-xs !leading-4" />
      ))}
      {[...latin].sort().map((code) => (
        <SourceCredit key={`latin-${code}`} code={code} role="Latin name" className="!text-xs !leading-4" />
      ))}
    </div>
  );
}

/** The source of the gradings shipped with a report's text (Thaqalayn records the Imami graders). */
export function GradingCredit({ hadithId, className }: { hadithId: string; className?: string }) {
  const text = sourceCodeForHadithId(hadithId);
  return text ? <SourceCredit code={sourceForGrading(text)} role="Grading" className={className} /> : null;
}
