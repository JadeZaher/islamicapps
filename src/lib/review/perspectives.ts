/**
 * The perspectives matrix: rows are sources of a view (classical works, named critics, datasets, AI reviews, human
 * reviews), grouped by tradition alphabetically; columns are aspects. Pure. See docs/review/README.md §Perspectives.
 */
import type { ClaimKind } from './claim-key';

export const PERSPECTIVE_ROW_KINDS = [
  { kind: 'classical_work', label: 'A classical work (a rijal book, a commentary, a chronicle)', shownAs: 'Author, work, entry and page, with the passage' },
  { kind: 'named_critic', label: 'A critic quoted by name inside another work', shownAs: 'The critic, then the work that quotes them' },
  { kind: 'compiler', label: 'The compiler of the collection', shownAs: 'The compiler’s statement in the text' },
  { kind: 'dataset', label: 'A dataset (the narrator lexicon, hadith-kg, Riwayat)', shownAs: 'Dataset, version and record; “not yet cited” where it gives no passage' },
  { kind: 'ai_rule', label: 'An AI review by rule', shownAs: 'Checked by rule, with the procedure id' },
  { kind: 'ai_specialist', label: 'An AI specialist review', shownAs: 'AI specialist review, with model, date and reasons' },
  { kind: 'human_review', label: 'A human review', shownAs: 'The reviewer’s name, stance, note and citations' },
] as const;
export type PerspectiveRowKind = (typeof PERSPECTIVE_ROW_KINDS)[number]['kind'];

export const PERSPECTIVE_ASPECTS = {
  narrator: [
    { id: 'identity', label: 'who the person is', claimKind: 'identity' },
    { id: 'reliability', label: 'reliability verdict', claimKind: 'narrator_verdict' },
    { id: 'death_year', label: 'death year', claimKind: 'biography' },
    { id: 'birth_year', label: 'birth year', claimKind: 'biography' },
    { id: 'generation', label: 'generation (tabaqa)', claimKind: 'biography' },
    { id: 'places', label: 'places', claimKind: 'biography' },
    { id: 'teachers_students', label: 'teachers and students', claimKind: 'rijal_link' },
    { id: 'rijal_entry', label: 'rijal entry', claimKind: 'rijal_link' },
  ],
  report: [
    { id: 'grading', label: 'grading', claimKind: 'grading' },
    { id: 'tellings', label: 'tellings elsewhere', claimKind: 'correspondence' },
    { id: 'translation', label: 'English', claimKind: 'translation' },
    { id: 'quran', label: 'Qur’an citations', claimKind: 'quran_citation' },
    { id: 'numbering', label: 'number and edition', claimKind: 'numbering' },
  ],
} as const satisfies Record<string, readonly { id: string; label: string; claimKind: ClaimKind }[]>;

export const TRADITION_ORDER = ['Ibadi', 'Imami', 'Sunni', 'Zaydi'] as const;

export interface PerspectiveCell {
  /** Stable row key, e.g. `work:ibn_hajar_taqrib`, `critic:yahya-ibn-main@work:mizzi`, `human:<handle>`, `ai:<specialist>@<model>`. */
  rowKey: string;
  rowKind: PerspectiveRowKind;
  rowLabel: string;
  /** The tradition the source belongs to; null for datasets, AI and reviewers who state none. */
  tradition: (typeof TRADITION_ORDER)[number] | null;
  aspect: string;
  /** The view in the source's own words, with its claim key so a review or a thread can address the cell. */
  value: string;
  claimKey: string;
  cited: boolean;
}

export interface PerspectiveGroup {
  tradition: (typeof TRADITION_ORDER)[number] | 'No tradition stated';
  rows: { rowKey: string; rowKind: PerspectiveRowKind; rowLabel: string; cells: Record<string, PerspectiveCell[]> }[];
}

const KIND_ORDER: readonly PerspectiveRowKind[] = PERSPECTIVE_ROW_KINDS.map((row) => row.kind);

/**
 * Group cells into the matrix: traditions alphabetical (none is first by default), sources without a tradition last;
 * within a group, classical sources before datasets, AI and human reviews. A cell may hold several values (a critic
 * reported two ways); they are all kept.
 */
export function buildPerspectiveMatrix(cells: readonly PerspectiveCell[]): PerspectiveGroup[] {
  const groups: PerspectiveGroup[] = [];
  for (const tradition of [...TRADITION_ORDER, null] as const) {
    const inGroup = cells.filter((cell) => cell.tradition === tradition);
    if (inGroup.length === 0) continue;
    const rows = new Map<string, PerspectiveGroup['rows'][number]>();
    for (const cell of inGroup) {
      const row = rows.get(cell.rowKey) ?? { rowKey: cell.rowKey, rowKind: cell.rowKind, rowLabel: cell.rowLabel, cells: {} };
      (row.cells[cell.aspect] ??= []).push(cell);
      rows.set(cell.rowKey, row);
    }
    groups.push({
      tradition: tradition ?? 'No tradition stated',
      rows: [...rows.values()].sort((a, b) => KIND_ORDER.indexOf(a.rowKind) - KIND_ORDER.indexOf(b.rowKind) || a.rowLabel.localeCompare(b.rowLabel)),
    });
  }
  return groups;
}

/** The discussion anchor of one cell: subject, row and aspect (see docs/review/schema-proposal.ts, anchor kind `perspective_cell`). */
export function perspectiveCellAnchor(subjectId: string, cell: Pick<PerspectiveCell, 'rowKey' | 'aspect'>): string {
  return `perspective_cell|${subjectId}|${cell.rowKey}|${cell.aspect}`;
}
