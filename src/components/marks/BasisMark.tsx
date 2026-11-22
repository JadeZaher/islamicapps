/** Identity-basis markers: a circle that fills as the basis firms up; label bases are a bar because they are labels, not rungs. See DESIGN.md §Basis labels. */
import type { ChainMentionCandidate, HadithTraditionCode, IdentityBasis, NameLatinBasis } from '@/db/queries/contracts';
import { MarkSvg, type MarkProps } from './MarkSvg';

/** Default wording per basis (the one copy; `candidateBasisLabel` refines it with the claim's origin). */
export const IDENTITY_BASIS_LABEL: Record<IdentityBasis, string> = {
  reviewer_decision: 'verified by a reviewer',
  source_index_confirmed_by_text: 'six-books source index, matches the text',
  source_index: 'six-books source index',
  name_exact: 'matched by name',
  name_spelling_fold: 'matched by name',
  name_kunya_only: 'matched by kunya only',
  source_hadith_kg_confirmed_by_text: 'hadith-kg index, matches the text',
  source_hadith_kg: 'hadith-kg index',
  source_riwayat_confirmed_by_text: 'Riwayat corpus, matches the text',
  source_riwayat: 'Riwayat corpus',
  imam_kunya_convention: "the Imam's conventional kunya with the honorific",
  imam_kunya_candidate: 'a kunya several Imams share; not decided',
  named_in_opening_isnad: "named by the work's own opening isnad (report No. 1)",
  edition_identification: "named by a printed edition's note on this report",
};

/** What set a standing (machine-reviewed) identity, from `chain_mentions.extraction_method`. */
export const STANDING_BASIS_LABEL: Record<string, string> = {
  source_index_confirmed_by_text: "machine-reviewed: the source's index and the text agree",
  two_sources_agree: 'machine-reviewed: two sources agree',
  source_hadith_kg_confirmed_by_text: "machine-reviewed: hadith-kg's index and the text agree",
  source_riwayat_confirmed_by_text: 'machine-reviewed: the annotation and the text agree',
  imam_kunya_convention: "machine-reviewed: the Imam's kunya in Imami usage",
  named_in_opening_isnad: "machine-reviewed: the work's opening isnad names him",
  edition_identification: "machine-reviewed: a printed edition's note names him",
};

/** Riwayat's id origin in words: Thaqalayn's annotation in Imami chains, hadith-kg's elsewhere (reconciled/README.md). */
function riwayatOrigin(origin: string | null | undefined, tradition: HadithTraditionCode | null): string {
  if (origin === 'riwayat_automatic_linking') return "Riwayat's automatic link, not counted";
  if (origin === 'riwayat_manual_gold') return "Riwayat, checked by its authors";
  return tradition === 'Imami' ? "Thaqalayn's annotation via Riwayat" : "hadith-kg's annotation via Riwayat";
}

/** The basis line under one candidate: the default wording, refined by who asserted an external id. */
export function candidateBasisLabel(candidate: ChainMentionCandidate, tradition: HadithTraditionCode | null): string {
  if (candidate.basis === 'source_riwayat' || candidate.basis === 'source_riwayat_confirmed_by_text') {
    const origin = riwayatOrigin(candidate.origin, tradition);
    const confirmed = candidate.basis === 'source_riwayat_confirmed_by_text' ? ', matches the text' : '';
    const label = candidate.label_reason ? '; the id names a label, not a person' : '';
    return `${origin}${confirmed}${label}`;
  }
  return IDENTITY_BASIS_LABEL[candidate.basis] ?? candidate.basis;
}

/** The mark a candidate is drawn with: a Riwayat automatic link or a label record never shows a firmer mark than a ring. */
export function candidateMarkBasis(candidate: ChainMentionCandidate): IdentityBasis {
  if (candidate.basis === 'source_riwayat_confirmed_by_text' && !candidate.tier_basis) return 'source_riwayat';
  return candidate.basis;
}

function Shape({ basis }: { basis: IdentityBasis }) {
  switch (basis) {
    case 'reviewer_decision':
      return <circle cx="5" cy="5" r="4.5" fill="currentColor" />;
    case 'source_index_confirmed_by_text':
    case 'source_hadith_kg_confirmed_by_text':
    case 'source_riwayat_confirmed_by_text':
    case 'imam_kunya_convention':
    case 'named_in_opening_isnad':
    case 'edition_identification':
      return (
        <>
          <circle cx="5" cy="5" r="4" stroke="currentColor" strokeWidth="1" />
          <circle cx="5" cy="5" r="2" fill="currentColor" />
        </>
      );
    case 'source_index':
    case 'source_hadith_kg':
    case 'source_riwayat':
      return <circle cx="5" cy="5" r="4" stroke="currentColor" strokeWidth="1" />;
    case 'name_exact':
    case 'name_spelling_fold':
      return <circle cx="5" cy="5" r="4" stroke="currentColor" strokeWidth="1" strokeDasharray="1.8 1.35" />;
    case 'name_kunya_only':
    case 'imam_kunya_candidate':
      return <rect x="1" y="4.25" width="8" height="1.5" fill="currentColor" shapeRendering="crispEdges" />;
  }
}

export function BasisMark({ basis, title, size = 10, ...props }: MarkProps & { basis: IdentityBasis }) {
  return (
    <MarkSvg viewBox="0 0 10 10" title={title ?? IDENTITY_BASIS_LABEL[basis]} size={size} {...props}>
      <g shapeRendering="geometricPrecision">
        <Shape basis={basis} />
      </g>
    </MarkSvg>
  );
}

/** How a chain name's Latin form was obtained (DESIGN.md §Latin names). Never an identification. */
export const NAME_LATIN_BASIS_LABEL: Record<NameLatinBasis, string> = {
  provider_english: "the source's English",
  identity_name: 'name of the identified record',
  transliteration_vocalized: 'transliterated from the vowelled text',
  transliteration_table: 'transliterated from common name parts',
};

/**
 * Latin-name basis mark: horizontal rules, solid when a source wrote the Latin form, one rule for a transliteration
 * read from the vowel marks, a dashed rule for one assembled from the name-parts table. Square, flat, single colour.
 */
export function NameBasisMark({ basis, title, size = 10, ...props }: MarkProps & { basis: NameLatinBasis }) {
  return (
    <MarkSvg viewBox="0 0 10 10" title={title ?? NAME_LATIN_BASIS_LABEL[basis]} size={size} {...props}>
      <g shapeRendering="crispEdges" fill="currentColor">
        {basis === 'provider_english' && (
          <>
            <rect x="1" y="2.5" width="8" height="1.5" />
            <rect x="1" y="6" width="8" height="1.5" />
          </>
        )}
        {basis === 'identity_name' && (
          <>
            <rect x="1" y="2.5" width="8" height="1.5" />
            <rect x="1" y="6" width="3" height="1.5" />
          </>
        )}
        {basis === 'transliteration_vocalized' && <rect x="1" y="4.25" width="8" height="1.5" />}
        {basis === 'transliteration_table' && (
          <>
            <rect x="1" y="4.25" width="2" height="1.5" />
            <rect x="4" y="4.25" width="2" height="1.5" />
            <rect x="7" y="4.25" width="2" height="1.5" />
          </>
        )}
      </g>
    </MarkSvg>
  );
}
