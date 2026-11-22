/** Reader wording for the chain structure gate (0017; src/db/AGENTS.md §Chain structure gate). */
import type { ChainNode } from '@/db/queries/contracts';

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
