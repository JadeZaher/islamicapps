/** Read visibility: the one switch between public views and curator preview reads. See AGENTS.md §Visibility. */
import 'server-only';
import { sql } from 'drizzle-orm';
import type { VerdictMode } from './assessment';
import type { HadithRelations } from './hadith';

declare const verifiedCuratorSession: unique symbol;

/** Only `src/lib/auth/visibility.ts` mints this, after verifying a curator session under PRIVATE_PREVIEW. */
export type CuratorVisibility = 'curator' & { readonly [verifiedCuratorSession]: true };

/** What a page may read: published rows only, or every live row for a verified curator. */
export type ReadVisibility = 'public' | CuratorVisibility;

export const PUBLIC_VISIBILITY: ReadVisibility = 'public';

export function isCuratorVisibility(visibility: ReadVisibility): visibility is CuratorVisibility {
  return visibility === 'curator';
}

const PUBLIC_HADITH_RELATIONS: HadithRelations = {
  hadiths: sql`public_hadiths`,
  translations: sql`public_translations`,
  liveHadith: sql`true`,
  liveTranslation: sql`true`,
};

/** Live base tables: unpublished and rights-pending rows included (curator preview only). */
const CURATOR_HADITH_RELATIONS: HadithRelations = {
  hadiths: sql`hadiths`,
  translations: sql`translations`,
  liveHadith: sql`h.retired_at is null`,
  liveTranslation: sql`x.retired_at is null`,
};

/** Hadith and translation relations for a visibility. Every visibility-aware hadith read goes through this. */
export function hadithRelationsFor(visibility: ReadVisibility): HadithRelations {
  return isCuratorVisibility(visibility) ? CURATOR_HADITH_RELATIONS : PUBLIC_HADITH_RELATIONS;
}

/** Verdict/bio mode for a visibility: curators see unpublished verdicts and the lexicon. */
export function verdictModeFor(visibility: ReadVisibility): VerdictMode {
  return isCuratorVisibility(visibility) ? 'review' : 'public';
}
