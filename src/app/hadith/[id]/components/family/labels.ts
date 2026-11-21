/** Reader-facing wording for correspondences and traditions in the family view. Neutral: evidence, not rulings. */
import type { FamilyTelling, HadithTraditionCode, TellingCorrespondence } from '@/db/queries/contracts';
import { reportReference } from '@/lib/citation/reference';

export const CORRESPONDENCE_LABEL: Record<string, string> = {
  same_wording: 'Same wording',
  same_report_variant_wording: 'Variant wording',
  partial_overlap: 'Shares a passage',
};

/** "Same wording", and how sure the archive is: a reviewer's confirmation, or a machine match nobody has reviewed. */
export function correspondenceLabel(correspondence: TellingCorrespondence): { kind: string; status: string; measure: string | null } {
  const relation = correspondence.reviewed_relation ?? correspondence.relation_class;
  const kind = (relation && CORRESPONDENCE_LABEL[relation]) || 'Corresponding report';
  const status = correspondence.confirmed
    ? 'confirmed by a reviewer'
    : correspondence.decision === 'uncertain'
      ? 'machine-found; a reviewer was unsure'
      : 'machine-found, unreviewed';
  let measure: string | null = null;
  if (correspondence.relation_class === 'partial_overlap' && correspondence.containment !== null) {
    measure = `${Math.round(correspondence.containment * 100)}% of the shorter text`;
  } else if (correspondence.jaccard !== null) {
    measure = `${Math.round(correspondence.jaccard * 100)}% shared wording`;
  }
  return { kind, status, measure };
}

/** Alphabetical, so no tradition is listed as the default (src/lib/glossary/AGENTS.md). */
export const TRADITION_ORDER: HadithTraditionCode[] = ['Ibadi', 'Imami', 'Sunni', 'Zaydi'];

/**
 * Line pattern per tradition, drawn in ink only (Swiss, legible in black and white): the pattern, not a hue, tells the
 * traditions apart, and the same pattern marks the tradition in every list heading.
 */
export const TRADITION_DASH: Record<HadithTraditionCode, { dash: string | undefined; name: string }> = {
  Ibadi: { dash: '1 4', name: 'dotted line' },
  Imami: { dash: '7 4', name: 'dashed line' },
  Sunni: { dash: undefined, name: 'solid line' },
  Zaydi: { dash: '9 3 1 3', name: 'dash-dot line' },
};

type ReferenceTelling = Pick<FamilyTelling, 'hadith_id' | 'source_work' | 'hadith_no' | 'numbering_citable' | 'record_id' | 'volume' | 'url' | 'page_ref'>;

/** The reference within its work ("Hadith 5036", "Volume 2, Book 2, Chapter 41, Hadith 5"), through the shared helper;
 * the stable record id where the work's numbering is not citable. */
export function withinWorkReference(telling: ReferenceTelling): string {
  if (!telling.numbering_citable) return `Record ${telling.record_id}`;
  return reportReference({
    id: telling.hadith_id,
    hadithNo: telling.hadith_no,
    url: telling.url,
    volume: telling.volume,
    pageRef: telling.page_ref,
    bookNumber: null,
  });
}

/** "Sahih Muslim, Hadith 5036". */
export function tellingReference(telling: ReferenceTelling): string {
  return `${telling.source_work}, ${withinWorkReference(telling)}`;
}

/** Tellings grouped by tradition (alphabetical), then by work, the report itself excluded. */
export function groupTellings(tellings: FamilyTelling[]): Array<{ tradition: HadithTraditionCode; works: Array<{ work: string; tellings: FamilyTelling[] }> }> {
  const others = tellings.filter((telling) => !telling.is_focal);
  return TRADITION_ORDER.map((tradition) => {
    const inTradition = others.filter((telling) => telling.tradition === tradition);
    const works = [...new Set(inTradition.map((telling) => telling.source_work))]
      .sort((left, right) => left.localeCompare(right))
      .map((work) => ({ work, tellings: inTradition.filter((telling) => telling.source_work === work) }));
    return { tradition, works };
  }).filter((group) => group.works.length > 0);
}
