/** Short source references for one report (text and English), built from its work's database source. */
import { sourceByCode, sourceForDatabaseSlug, sourceRecordHref, WORK_CREDITS, type SourceCode } from './registry';

export interface SourceReference {
  role: 'Text' | 'English';
  code: SourceCode;
  name: string;
  /** Link to the source's record on /sources. */
  href: string;
  licence: { name: string; url: string | null };
  /** Work and author, or translator. */
  detail: string | null;
  /** This report at the provider, where the register asks for a link to it. */
  external: string | null;
}

export interface ReportCreditInput {
  sourceSlug: string;
  sourceWorkId: string;
  workName: string;
  /** Provider URL recorded for the report. */
  url: string | null;
  /** The work's own number for the report. */
  number: string | null;
  english: { state: string | null; translator: string | null; model: string | null } | null;
}

/** thaqalayn.net now redirects to thaqalayn.com (rights register, source 4): link the current host. */
export function thaqalaynLink(url: string | null): string | null {
  if (!url) return null;
  try {
    const parsed = new URL(url);
    if (parsed.hostname === 'thaqalayn.net' || parsed.hostname === 'www.thaqalayn.net') parsed.hostname = 'thaqalayn.com';
    return parsed.hostname === 'thaqalayn.com' ? parsed.toString() : null;
  } catch {
    return null;
  }
}

/** sunnah.com per-hadith link; Muslim's numbering is not verified against sunnah.com, so it links the collection. */
function sunnahLink(collection: string | undefined, number: string | null): string | null {
  if (!collection) return null;
  if (collection === 'muslim' || !number) return `https://sunnah.com/${collection}`;
  return `https://sunnah.com/${collection}:${number}`;
}

function reference(role: SourceReference['role'], code: SourceCode, detail: string | null, external: string | null): SourceReference {
  const record = sourceByCode(code);
  return { role, code, name: record.name, href: sourceRecordHref(code), licence: record.licence, detail, external };
}

export type EnglishInput = NonNullable<ReportCreditInput['english']>;

/** True for machine English: its state says so, or a model is recorded. */
export function isMachineEnglish(english: EnglishInput): boolean {
  return english.state === 'machine_unreviewed' || Boolean(english.model);
}

/** Machine English label (owner, 2026-11-22); its model is named in the credit line (`englishReference`). */
export const MACHINE_ENGLISH_LABEL =
  'Unreviewed machine translation. May contain errors that change the meaning; the Arabic is authoritative.';

/** The label shown above English text: machine, or source-provided, or reviewed. */
export function englishLabel(english: EnglishInput): string {
  if (isMachineEnglish(english)) return MACHINE_ENGLISH_LABEL;
  if (english.state === 'human_verified' || english.state === 'source_verified') return 'English translation, reviewed';
  return 'Source-provided English, not reviewed here';
}

/** The English reference for a report: our own layer for machine English, else the text source with its translator. */
export function englishReference(input: Pick<ReportCreditInput, 'sourceSlug' | 'sourceWorkId' | 'english'>): SourceReference | null {
  const record = sourceForDatabaseSlug(input.sourceSlug);
  if (!record || !input.english) return null;
  if (isMachineEnglish(input.english)) {
    return reference('English', 'SWI', `Machine translation (${input.english.model ?? 'model not recorded'}), not reviewed`, null);
  }
  const translator = input.english.translator ?? WORK_CREDITS[input.sourceWorkId]?.translator ?? 'translator not recorded in our copy';
  return reference('English', record.code, `Translation: ${translator}`, null);
}

/** Text and (when shown) English references for a report; empty only for an unregistered source. */
export function reportSourceReferences(input: ReportCreditInput): SourceReference[] {
  const record = sourceForDatabaseSlug(input.sourceSlug);
  if (!record) return [];
  const credit = WORK_CREDITS[input.sourceWorkId];
  const external =
    record.code === 'THQ' ? thaqalaynLink(input.url) : record.code === 'SUN' ? sunnahLink(credit?.sunnahCollection, input.number) : null;
  const work = credit ? `${input.workName}, ${credit.author}` : input.workName;
  const references = [reference('Text', record.code, credit?.openitiUri ? `${work} (OpenITI ${credit.openitiUri})` : work, external)];
  const english = englishReference(input);
  if (english) references.push(english);
  return references;
}

/** One plain-text line per reference, for the copyable citation. */
export function referencesText(references: SourceReference[], origin: string): string {
  return references
    .map((item) => `${item.role}: ${item.name} [${item.code}]${item.detail ? `, ${item.detail}` : ''}; ${item.licence.name}; ${origin}${item.href}`)
    .join('\n');
}
