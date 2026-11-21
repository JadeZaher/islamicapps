/** Display guard for a stored matn (review 2026-11-21). See src/app/hadith/[id]/AGENTS.md §Matn. */

/** Arabic base letters only (U+0621..U+064A), as matn_isolation.arabic_letters compares them. */
function arabicLetters(text: string): string {
  return text.replace(/[^ء-ي]/g, '');
}

/**
 * The matn when it is this report's own: its letters occur inside the report's text, and it is not a leading slice of
 * a longer text (that is where the chain sits). Otherwise null, and the page shows the full text with the chain once.
 */
export function ownMatn(matn: string | null | undefined, text: string | null | undefined): string | null {
  if (!matn?.trim()) return null;
  if (!text?.trim()) return null;
  const matnLetters = arabicLetters(matn);
  const textLetters = arabicLetters(text);
  if (!matnLetters || !textLetters.includes(matnLetters)) return null;
  if (textLetters.length > matnLetters.length && textLetters.startsWith(matnLetters.slice(0, 30))) return null;
  return matn;
}
