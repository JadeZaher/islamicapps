/** How a report is numbered and referred to, per provider. See src/lib/AGENTS.md §Report numbering. */

export type IdNamespace = 'k6' | 'thaqalayn' | 'pure-canon' | 'openiti' | 'other';

export interface ReferenceFields {
  id: string;
  hadithNo: string | null;
  url: string | null;
  volume: string | null;
  pageRef: string | null;
  bookNumber: string | null;
}

export function idNamespace(id: string): IdNamespace {
  const namespace = id.split(':')[1];
  return namespace === 'k6' || namespace === 'thaqalayn' || namespace === 'pure-canon' || namespace === 'openiti'
    ? namespace
    : 'other';
}

/** Thaqalayn's own path `/hadith/<book>/<category>/<chapter>/<hadith>`; the loaded `hadith_no` is the chapter. */
const THAQALAYN_PATH = /\/hadith\/(\d+)\/(\d+)\/(\d+)\/(\d+)\/?$/;

export function thaqalaynLocator(url: string | null): { category: string; chapter: string; hadith: string } | null {
  const match = url ? THAQALAYN_PATH.exec(url) : null;
  return match ? { category: match[2], chapter: match[3], hadith: match[4] } : null;
}

/** `V01P059` -> `vol. 1, p. 59`; anything else is returned unchanged. */
export function pageLabel(pageRef: string | null): string | null {
  if (!pageRef) return null;
  const match = /^V0*(\d+)P0*(\d+)$/.exec(pageRef.trim());
  return match ? `vol. ${match[1]}, p. ${match[2]}` : pageRef.trim();
}

function positiveNumber(value: string | null): string | null {
  const trimmed = value?.trim() ?? '';
  return /^\d+$/.test(trimmed) && Number(trimmed) > 0 ? String(Number(trimmed)) : null;
}

/** The work's own number for the report, or null when this copy records none. */
export function reportNumber(fields: ReferenceFields): string | null {
  if (idNamespace(fields.id) === 'thaqalayn') return thaqalaynLocator(fields.url)?.hadith ?? null;
  return positiveNumber(fields.hadithNo);
}

/** The part of a report the parser split off a numbered one (`...rida_0004#2|4|V01P442` is part 2 of No. 4); null for the first. */
export function reportPart(id: string): number | null {
  const match = /#(\d+)(?:\||$)/.exec(id);
  return match ? Number(match[1]) : null;
}

/** The local part of the stable ID (`k6:10008` -> `10008`), used when a report has no number. */
function recordKey(id: string): string {
  return id.split(':').slice(2).join(':');
}

/** A human reference within the work, e.g. "Book 14, Hadith 2880" or "Volume 5, Book 2, Chapter 41, Hadith 1". */
export function reportReference(fields: ReferenceFields): string {
  const number = reportNumber(fields);
  switch (idNamespace(fields.id)) {
    case 'k6': {
      const book = fields.bookNumber ? `Book ${fields.bookNumber}, ` : '';
      return number ? `${book}Hadith ${number}` : `${book}unnumbered (record ${recordKey(fields.id)})`;
    }
    case 'thaqalayn': {
      const locator = thaqalaynLocator(fields.url);
      // Thaqalayn books are its provider files, one per volume: the book number is the volume when none is recorded.
      const volumeNumber = fields.volume ?? fields.bookNumber;
      const volume = volumeNumber ? `Volume ${volumeNumber}, ` : '';
      return locator
        ? `${volume}Book ${locator.category}, Chapter ${locator.chapter}, Hadith ${locator.hadith}`
        : `${volume}record ${recordKey(fields.id)}`;
    }
    case 'openiti': {
      const page = pageLabel(fields.pageRef);
      const part = reportPart(fields.id);
      const base = number ? `No. ${number}${part ? `, part ${part}` : ''}` : `Record ${recordKey(fields.id)}`;
      return page ? `${base} (${page})` : base;
    }
    default:
      return number ? `No. ${number}` : `Record ${recordKey(fields.id)} (no number in this copy)`;
  }
}

/** Heading for a book row: K6 kitabs are numbered books, Thaqalayn and OpenITI books are volumes. */
export function bookHeading(namespace: IdNamespace, book: { number: string; name: string | null; volume: string | null }): {
  label: string;
  title: string | null;
} {
  if (namespace === 'k6') return { label: `Book ${book.number}`, title: book.name };
  return { label: `Volume ${book.volume ?? book.number}`, title: null };
}
