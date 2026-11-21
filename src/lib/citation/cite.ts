/** The plain-text "Cite this report" block. Pure: the caller supplies the address, version and access date. */
import { referencesText, type SourceReference } from '@/lib/sources/report-credit';

export const ARCHIVE_NAME = 'Shura wa Istehsan';

export interface CitationInput {
  workName: string;
  reference: string;
  version: { label: string | null; shortId: string } | null;
  /** Absolute page address. */
  address: string;
  origin: string;
  /** ISO date (YYYY-MM-DD) the page was rendered for the reader. */
  accessed: string;
  references: SourceReference[];
}

export function versionText(version: CitationInput['version']): string {
  if (!version) return 'dataset version unknown';
  return version.label ? `dataset version "${version.label}" (${version.shortId})` : `dataset version ${version.shortId}`;
}

export function citationText(input: CitationInput): string {
  const head = `${input.workName}, ${input.reference}. ${ARCHIVE_NAME}, hadith archive, ${versionText(input.version)}. ${input.address}. Accessed ${input.accessed}.`;
  const credits = referencesText(input.references, input.origin);
  return credits ? `${head}\n${credits}` : head;
}
