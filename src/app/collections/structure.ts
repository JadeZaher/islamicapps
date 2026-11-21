/** Honest notes about what structure a copy of a work carries. See src/app/collections/AGENTS.md. */
import type { WorkStructure } from '@/db/queries/browse';

const number = (value: number) => value.toLocaleString('en');

/** A one-sentence note when the copy lacks chapters (or books), saying how reports are ordered instead; else null. */
export function structureNote(structure: WorkStructure): string | null {
  if (structure.withChapter > 0) return null;
  if (structure.withBook > 0) {
    return structure.namespace === 'k6'
      ? 'Our copy records the books of this work but not their chapters, so each book lists its reports in source order with sunnah.com’s numbering.'
      : 'Our copy records the books of this work but not their chapters, so each book lists its reports in source order.';
  }
  if (structure.withNumber === 0) {
    return 'Our copy records no books, chapters or numbers for this work. Reports are listed by record identifier, which does not follow the work’s own order.';
  }
  if (structure.distinctNumbers < structure.withNumber) {
    return `Our copy records no books or chapters for this work. Reports are listed by the number the provider gives them; numbers repeat (${number(structure.distinctNumbers)} distinct numbers across ${number(structure.reports)} reports), so reports sharing a number follow record identifier order.`;
  }
  return 'Our copy records no books or chapters for this work. Reports are listed by the provider’s numbering.';
}

/** Page number from a search param; 1 when absent or invalid. */
export function pageParam(value: string | string[] | undefined): number {
  const raw = Array.isArray(value) ? value[0] : value;
  const parsed = Math.floor(Number(raw));
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 1;
}

/** Route params arrive percent-encoded; decode once, safely. */
export function routeParam(value: string): string {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}
