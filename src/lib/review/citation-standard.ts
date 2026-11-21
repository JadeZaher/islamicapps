/**
 * The archive's one citation standard as a checkable record (docs/review/citations.md is its prose form).
 * Pure; used by the claims validator, the human-review validator and, later, the loader.
 */
import { SOURCES, type SourceCode } from '../sources/registry';
import { SHA256_PATTERN, type ClaimKind } from './claim-key';

export const CITATION_FORMAT = 'shura-citation/1';
export const TRADITIONS = ['Ibadi', 'Imami', 'Sunni', 'Zaydi'] as const;
/** The label a claim carries when it has no acceptable citation. */
export const NOT_YET_CITED_LABEL = 'not yet cited';

export type Locator =
  | { kind: 'print'; volume?: string; page?: string; entry?: string; number?: string }
  | { kind: 'web'; url: string; retrieved: string }
  | { kind: 'dataset'; dataset: string; version: string; record_id: string }
  | { kind: 'quran'; sura: number; aya_from: number; aya_to: number };

export interface Citation {
  work: { author: string; title: string; tradition: (typeof TRADITIONS)[number] | 'none' };
  /** The edition or digital source exactly as its header or metadata names it. */
  edition: string;
  locator: Locator;
  /** The verbatim passage relied on, in the original language; `span` when it is part of a stored text. */
  passage: { text: string; language: string; span?: { field: string; start: number; end: number } };
  /** Short reference and licence from src/lib/sources/registry.ts. */
  source: { code: SourceCode; licence: string };
  /** SHA-256 of the text the citation was checked against. */
  checked_against_sha256: string;
}

/** Locator kinds that can cite each kind of claim. A dataset record alone does not cite a biographical value. */
export const ACCEPTED_LOCATORS: Readonly<Record<ClaimKind | 'review' | 'post', readonly Locator['kind'][]>> = {
  identity: ['print', 'dataset'],
  correspondence: ['dataset', 'print', 'web'],
  translation: ['dataset', 'print', 'web'],
  grading: ['print', 'dataset'],
  narrator_verdict: ['print'],
  biography: ['print'],
  rijal_link: ['print'],
  history: ['print'],
  quran_citation: ['quran'],
  numbering: ['dataset', 'web', 'print'],
  review: ['print', 'web', 'dataset', 'quran'],
  post: ['print', 'web', 'dataset', 'quran'],
};

/** Minimum number of citations per claim kind (a correspondence cites both texts). */
export const MINIMUM_CITATIONS: Partial<Record<ClaimKind, number>> = { correspondence: 2 };

/** Phrases that mark an unacceptable citation: a model's own knowledge or a reference to no particular work. */
const UNACCEPTABLE_WORK = /\b(general reference|reference works|common knowledge|well[- ]known|various sources|model knowledge|own knowledge|ai knowledge|internet|wikipedia)\b/i;
const ARABIC_LETTER = /[ء-ي]/;
const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;
const nonEmpty = (value: unknown): value is string => typeof value === 'string' && value.trim().length > 0;

const LICENCE_BY_CODE = new Map(SOURCES.map((source) => [source.code, source.licence.name]));

/** Every way a citation falls short of the standard for a claim kind; empty when it passes. */
export function citationProblems(raw: unknown, kind: ClaimKind | 'review' | 'post'): string[] {
  const problems: string[] = [];
  if (!raw || typeof raw !== 'object') return ['citation is not an object'];
  const citation = raw as Partial<Citation> & Record<string, unknown>;
  const work = citation.work as Partial<Citation['work']> | undefined;
  if (!work || !nonEmpty(work.title)) problems.push('work.title is required');
  if (!work || !nonEmpty(work.author)) problems.push('work.author is required (write "anonymous" or the compiling body when there is none)');
  if (!work || !([...TRADITIONS, 'none'] as string[]).includes(String(work.tradition))) problems.push('work.tradition must be Ibadi, Imami, Sunni, Zaydi or none');
  if (work && (UNACCEPTABLE_WORK.test(String(work.title)) || UNACCEPTABLE_WORK.test(String(work.author)))) {
    problems.push('a general reference or a model’s own knowledge is not a citation');
  }
  if (!nonEmpty(citation.edition)) problems.push('edition is required, exactly as the source’s header or metadata names it');

  const locator = citation.locator as Partial<Locator> | undefined;
  if (!locator || typeof locator !== 'object') problems.push('locator is required');
  else {
    const accepted = ACCEPTED_LOCATORS[kind];
    if (!accepted.includes(locator.kind as Locator['kind'])) problems.push(`a ${String(locator.kind)} locator does not cite a ${kind} claim (accepted: ${accepted.join(', ')})`);
    if (locator.kind === 'print') {
      const print = locator as Extract<Locator, { kind: 'print' }>;
      if (!nonEmpty(print.page) && !nonEmpty(print.entry) && !nonEmpty(print.number)) problems.push('a print locator needs a page, entry or number (a bare title or volume is not a locator)');
    } else if (locator.kind === 'web') {
      const web = locator as Extract<Locator, { kind: 'web' }>;
      if (!nonEmpty(web.url) || !/^https:\/\//.test(web.url)) problems.push('a web locator needs an https URL');
      if (!nonEmpty(web.retrieved) || !ISO_DATE.test(web.retrieved)) problems.push('a web locator needs its retrieval date (YYYY-MM-DD)');
    } else if (locator.kind === 'dataset') {
      const dataset = locator as Extract<Locator, { kind: 'dataset' }>;
      if (!nonEmpty(dataset.dataset)) problems.push('a dataset locator needs the dataset name');
      if (!nonEmpty(dataset.version)) problems.push('a dataset locator needs the dataset version');
      if (!nonEmpty(dataset.record_id)) problems.push('a dataset locator needs a record id');
    } else if (locator.kind === 'quran') {
      const quran = locator as Extract<Locator, { kind: 'quran' }>;
      if (!Number.isInteger(quran.sura) || quran.sura < 1 || quran.sura > 114) problems.push('sura must be 1 to 114');
      if (!Number.isInteger(quran.aya_from) || !Number.isInteger(quran.aya_to) || quran.aya_from < 1 || quran.aya_to < quran.aya_from) problems.push('aya_from and aya_to must be a valid range');
    } else problems.push(`unknown locator kind ${JSON.stringify(locator.kind)}`);
  }

  const passage = citation.passage as Partial<Citation['passage']> | undefined;
  if (!passage || !nonEmpty(passage.text)) problems.push('the verbatim passage relied on is required');
  else {
    if (!nonEmpty(passage.language)) problems.push('passage.language is required');
    if (passage.language === 'ar' && !ARABIC_LETTER.test(passage.text)) problems.push('an Arabic passage must contain Arabic letters');
    if (passage.span !== undefined) {
      const span = passage.span;
      if (!nonEmpty(span.field) || !Number.isInteger(span.start) || !Number.isInteger(span.end) || span.start < 0 || span.end <= span.start) {
        problems.push('passage.span needs a field and 0 <= start < end');
      } else if (span.end - span.start !== [...passage.text].length) {
        problems.push('passage.span length does not match the passage (spans count code points)');
      }
    } else if (kind === 'quran_citation') problems.push('a Qur’an citation needs the span of the quotation in the report text');
  }

  const source = citation.source as Partial<Citation['source']> | undefined;
  const licence = source ? LICENCE_BY_CODE.get(source.code as SourceCode) : undefined;
  if (!source || licence === undefined) problems.push('source.code must be a code in the source registry');
  else if (source.licence !== licence) problems.push(`source.licence must be the registry’s "${licence}"`);

  if (!nonEmpty(citation.checked_against_sha256) || !SHA256_PATTERN.test(citation.checked_against_sha256)) {
    problems.push('checked_against_sha256 must be the SHA-256 of the text the citation was checked against');
  }
  return problems;
}
