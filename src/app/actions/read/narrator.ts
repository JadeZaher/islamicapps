'use server';
/** Narrator name typeahead: a plain array of at most 20 (section 9.1). */
import { z } from 'zod';
import type { NarratorListItem } from '@/db/queries/contracts';
import { searchNarratorsTypeahead as searchNarratorsByName } from '@/db/queries/narrator';

export async function searchNarratorsTypeahead(term: unknown): Promise<NarratorListItem[]> {
  return searchNarratorsByName(z.string().max(100).parse(term ?? ''));
}
