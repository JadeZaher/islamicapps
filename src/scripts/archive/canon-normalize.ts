/**
 * canon-normalize.ts
 *
 * TypeScript port of the Python `normalize_arabic` function from
 * datasets/05_hadith_cleansing_pipeline_pure_canon_authentica.py (lines 159-167).
 *
 * IMPORTANT: Any changes to this function MUST be kept in sync with the Python source.
 * The Python implementation is authoritative for the Arabic normalization pipeline;
 * this file exists to share the same normalization logic in the TypeScript import scripts.
 *
 * Original Python:
 * ```python
 * def normalize_arabic(text):
 *     if not isinstance(text, str):
 *         return ""
 *     text = re.sub(r"[\u064B-\u0652]", "", text)   # remove harakat (Arabic diacritics)
 *     text = re.sub(r"[^\u0621-\u064A\s]", " ", text)  # keep only Arabic letters + whitespace
 *     text = re.sub(r"[أإآ]", "ا", text)  # normalize alif variants
 *     text = " ".join(text.split())  # collapse whitespace
 *     return text.strip()
 * ```
 *
 * Example:
 * ```ts
 * normalizeArabic("إِنَّ الله رَحِيمٌ") // => "ان الله رحيم"
 * ```
 */

/**
 * Normalize Arabic text by removing diacritics, stripping non-Arabic characters,
 * normalizing alif variants to bare alif, and collapsing whitespace.
 *
 * Port of the Python `normalize_arabic` function. Keep in sync with:
 * datasets/05_hadith_cleansing_pipeline_pure_canon_authentica.py lines 159-167
 */
export function normalizeArabic(text: string): string {
    if (typeof text !== 'string') return '';

    // Remove harakat (Arabic diacritics): U+064B (fathatan) through U+0652 (sukun)
    text = text.replace(/[\u064B-\u0652]/g, '');

    // Keep only Arabic letters (U+0621–U+064A) and whitespace; replace everything else with space
    text = text.replace(/[^\u0621-\u064A\s]/g, ' ');

    // Normalize alif variants (أ إ آ) to bare alif (ا)
    text = text.replace(/[\u0623\u0625\u0622]/g, '\u0627');

    // Collapse multiple whitespace characters into a single space
    text = text.split(/\s+/).filter(Boolean).join(' ');

    return text.trim();
}

/**
 * Return the first `len` characters of the normalized Arabic text.
 * Useful as a quick matn-match fingerprint key for approximate deduplication.
 *
 * @param text   Raw Arabic text to normalize and truncate.
 * @param len    Maximum length of the fingerprint (default: 60).
 */
export function fingerprintArabic(text: string, len = 60): string {
    return normalizeArabic(text).slice(0, len);
}
