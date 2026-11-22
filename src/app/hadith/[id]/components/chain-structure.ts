/** Reader wording for the chain structure gate (0017), model readings (0019) and the compiler head (0019; src/db/AGENTS.md). */
import type { ChainCompiler, ChainDisposition, ChainFixLabel, ChainNode, ChainVariantRemark } from '@/db/queries/contracts';

/** Why a chain's structure is uncertain (0017; codes from `pg_export/chain_structure.py`), in plain words. */
export const CHAIN_STRUCTURE_REASON_LABEL: Record<string, string> = {
  duplicated_link: 'one person seems to be stored as two neighbouring names',
  joined_names: 'one position holds two names joined by «و»',
  ghayr_wahid_half: 'half of «غير واحد» is stored as a name',
  short_beside_long: 'this route is much shorter than another route of the report',
  repeated_name: 'the same name stands twice in the chain',
  text_between_links: 'the text names more between two stored names than the chain holds',
  text_names_more_after: 'the text names a further transmitter after the last stored name',
  not_a_name: 'a stored name contains words that are not a name',
  unaccounted_route_marker: 'the text marks more routes («ح», «جميعا», «كلهم») than were stored',
  crossed_routes: "two of al-Kulayni's routes appear joined in one chain",
  many_routes: 'the report has three or more routes, which the rules read wrong too often',
  sibling_skips_link: 'two routes of this report differ by one name in the middle, so one of them lost or added a name',
  work_not_checked: 'chains in this work were read wrong too often to rely on',
};

/** The plain line under an uncertain chain: shown as stored, kept out of teacher and student lists, and why. */
export function structureNote(node: Pick<ChainNode, 'chain_structure_status' | 'chain_structure_reasons'>): string | null {
  if (node.chain_structure_status !== 'uncertain') return null;
  const reasons = (node.chain_structure_reasons ?? []).map((code) => CHAIN_STRUCTURE_REASON_LABEL[code] ?? code);
  return [
    "The reading of this chain's routes has not been checked; it is not used for teacher and student lists.",
    reasons.length > 0 ? `Why: ${reasons.join('; ')}.` : null,
  ].filter(Boolean).join(' ');
}

const day = (value: string) => value.slice(0, 10);

/**
 * The line under a chain a model reader read (docs/review/chain-fix-pipeline.md §States). "Verified" only names a person:
 * a reading awaiting final review never says it.
 */
export function chainFixNote(fix: ChainFixLabel | null | undefined, status: ChainNode['chain_structure_status']): string | null {
  if (!fix) return null;
  const models = [...new Set(fix.models)].join(', ');
  if (status === 'verified_by_reviewer' && fix.human_confirmations.length > 0) {
    return fix.human_confirmations.map((confirmation) => `Verified by ${confirmation.reviewer}, ${day(confirmation.reviewed_at)}`).join('; ');
  }
  if (fix.effect === 'annotate') return `A model reader read the same routes (${models}, ${day(fix.decided_at)})`;
  return `Read by model (${models}), ${day(fix.decided_at)}; awaiting final review`;
}

/** The line for a report whose applied model reading found no isnad in the text (0021): instead of stored junk names. */
export function noChainNote(disposition: ChainDisposition | null | undefined): string | null {
  if (!disposition) return null;
  const models = [...new Set(disposition.models)].join(', ');
  const review = disposition.awaiting_final_review ? '; awaiting final review' : '';
  return `No chain is written in this report (read by model (${models}), ${day(disposition.decided_at)}${review}).`;
}

/** The plain label of the compiler heading a chain: derived from the work, never written in the text. */
export function compilerNote(compiler: ChainCompiler): string {
  return compiler.link === 'direct'
    ? 'Compiler of the work; not written in the text'
    : 'Compiler of the work; not written in the text, and this chain does not start from his own teacher, so no teacher link is drawn';
}

/** The variant remarks of the model reading a report's chains share (one fix per report), or none. */
export function variantRemarksOf(nodes: Pick<ChainNode, 'chain_fix'>[]): ChainVariantRemark[] {
  return nodes.find((node) => node.chain_fix?.variant_remarks?.length)?.chain_fix?.variant_remarks ?? [];
}

/** The lead of a variant remark's line; the Arabic sentence and the names follow it (never drawn as a chain, never a route). */
export const VARIANT_REMARK_LEAD = 'The report mentions another version:';

/** The names a remark lists, in the order the sentence gives them; alternatives of one level joined by «/». */
export function variantRemarkNames(remark: ChainVariantRemark): string {
  return remark.surfaces.map((level) => level.join(' / ')).join('، ');
}

/** A remark only one of the two readers noted is said so: a weaker claim than one both made. */
export function variantRemarkCaveat(remark: ChainVariantRemark): string | null {
  return remark.passes.length < 2 ? 'noted by one of the two readers' : null;
}
