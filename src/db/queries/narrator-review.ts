/** Reviewer-mode narrator reads: every live verdict and bio, base chain tables, the lexicon. Curator callers only. */
import 'server-only';
import type { NarratorDetail, NarratorListItem, Paginated } from './contracts';
import { getNarratorDetail, listNarrators, type NarratorFilters } from './narrator';
import type { PageRequest } from './sql-helpers';

export async function listNarratorsForReview(
  term: string | undefined,
  filters: NarratorFilters = {},
  request?: PageRequest,
): Promise<Paginated<NarratorListItem>> {
  return listNarrators(term, filters, request, 'review');
}

export async function getNarratorForReview(narratorId: string): Promise<NarratorDetail | null> {
  return getNarratorDetail(narratorId, 'review');
}
