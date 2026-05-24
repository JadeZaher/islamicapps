/**
 * Two-tier hadith grading system.
 *
 * Tier 1 -- grade_canonical: broad bucket used for filtering / analytics.
 * Tier 2 -- grade_detail:    cleaned version of the original display_grade
 *           (OCR fixes, spacing normalisation, Persian-ya mapping).
 *
 * All import / normalisation scripts MUST use mapToCanonical() and
 * cleanGradeDetail() from this module.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type GradeCanonical =
  | 'sahih'       // Sound / authentic
  | 'hasan'       // Good
  | 'muwaththaq'  // Reliable (Shia: trustworthy non-Shia narrator)
  | 'da_if'       // Weak
  | 'majhul'      // Unknown narrator
  | 'mursal'      // Broken chain / missing link
  | 'mawdu'       // Fabricated / dropped
  | 'mu_tabar'    // Considered reliable (Shia)
  | 'mukhtalaf'   // Disputed
  | 'ungraded';   // No grade assigned

// ---------------------------------------------------------------------------
// Display helpers
// ---------------------------------------------------------------------------

/** Human-friendly English labels for each canonical grade */
export const GRADE_LABELS: Record<GradeCanonical, string> = {
  sahih:      'Authentic (Sahih)',
  hasan:      'Good (Hasan)',
  muwaththaq: 'Reliable (Muwaththaq)',
  da_if:      'Weak (Da\'if)',
  majhul:     'Unknown narrator (Majhul)',
  mursal:     'Broken chain (Mursal)',
  mawdu:      'Fabricated (Mawdu\')',
  mu_tabar:   'Considered reliable (Mu\'tabar)',
  mukhtalaf:  'Disputed (Mukhtalaf)',
  ungraded:   'Ungraded',
};

// ---------------------------------------------------------------------------
// Internal normalisation helpers
// ---------------------------------------------------------------------------

/** Collapse whitespace, trim, and normalise Persian ya / kaf to Arabic */
function normaliseArabic(s: string): string {
  return s
    .replace(/\s+/g, ' ')       // collapse whitespace
    .trim()
    .replace(/ی/g, 'ي')         // Persian ya  -> Arabic ya
    .replace(/ک/g, 'ك')         // Persian kaf -> Arabic kaf
    .replace(/ة\s/g, 'ة ')      // ensure ta-marbuta spacing is clean
    .replace(/\u200c/g, '')      // remove zero-width non-joiner
    .replace(/\u200d/g, '');     // remove zero-width joiner
}

// ---------------------------------------------------------------------------
// Exact-match lookup table: normalised display_grade -> GradeCanonical
// ---------------------------------------------------------------------------

const EXACT_MAP: Record<string, GradeCanonical> = {
  // Empty / null
  '':           'ungraded',
  'null':       'ungraded',

  // Sunni / Ibadi Latin
  'thabit':     'sahih',
  'sahih':      'sahih',
  'daif':       'da_if',
  'hasan':      'hasan',

  // Primary Arabic grades
  'صحيح':       'sahih',
  'حسن':        'hasan',
  'موثق':       'muwaththaq',
  'ضعيف':       'da_if',
  'مجهول':      'majhul',
  'مرسل':       'mursal',
  'معتبر':      'mu_tabar',
  'مختلف فيه':  'mukhtalaf',
  'مرفوع':      'mursal',
  'مضمر':       'mursal',

  // Compound -- exact
  'حسن كالصحيح':                    'sahih',
  'موثق كالصحيح':                   'sahih',
  'مجهول كالصحيح':                  'sahih',
  'صحيح على الظاهر':                'sahih',
  'حسن على الظاهر':                 'hasan',
  'مرسل كالموثق':                   'muwaththaq',
  'حسن او موثق':                    'hasan',
  'حسن أو موثق':                    'hasan',

  // Weak variants
  'ضعيف على المشهور':               'da_if',
  'ضعيف على الشهور':                'da_if',    // OCR variant

  // Compound with mu'tabar override
  'ضعيف على المشهور معتبر عند ي':   'mu_tabar',

  // Silent / not extracted
  'سكت عنه':    'ungraded',
  'لم يخرجه':   'ungraded',
};

// ---------------------------------------------------------------------------
// Contains-based rules (checked in priority order)
// ---------------------------------------------------------------------------

interface ContainsRule {
  pattern: string;
  canonical: GradeCanonical;
}

/**
 * Order matters: first match wins.
 * More specific patterns (e.g. معتبر) must come before broader ones.
 */
const CONTAINS_RULES: ContainsRule[] = [
  // Dropped / fabricated
  { pattern: 'ساقط',    canonical: 'mawdu' },
  { pattern: 'موضوع',   canonical: 'mawdu' },

  // "like sahih" compounds -- strongest upgrade
  { pattern: 'كالصحيح', canonical: 'sahih' },

  // mu'tabar override (before weak check)
  { pattern: 'معتبر',   canonical: 'mu_tabar' },

  // Disputed
  { pattern: 'مختلف',   canonical: 'mukhtalaf' },

  // Primary grades (order: strongest first so multi-chain picks strongest)
  { pattern: 'صحيح',    canonical: 'sahih' },
  { pattern: 'حسن',     canonical: 'hasan' },
  { pattern: 'موثق',    canonical: 'muwaththaq' },
  { pattern: 'مجهول',   canonical: 'majhul' },
  { pattern: 'مرسل',    canonical: 'mursal' },
  { pattern: 'مرفوع',   canonical: 'mursal' },
  { pattern: 'مضمر',    canonical: 'mursal' },
  { pattern: 'ضعيف',    canonical: 'da_if' },

  // Latin fallbacks
  { pattern: 'sahih',   canonical: 'sahih' },
  { pattern: 'hasan',   canonical: 'hasan' },
  { pattern: 'daif',    canonical: 'da_if' },
  { pattern: 'thabit',  canonical: 'sahih' },
];

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Map a raw display_grade (+ optional tradition) to a canonical grade bucket.
 *
 * Strategy:
 *   1. Normalise & trim input.
 *   2. Exact-match lookup.
 *   3. Contains-rule scan (first match wins).
 *   4. Fallback to 'ungraded'.
 */
export function mapToCanonical(
  displayGrade: string | null | undefined,
  _tradition?: string | null,
): GradeCanonical {
  if (displayGrade === null || displayGrade === undefined) return 'ungraded';

  const normalised = normaliseArabic(displayGrade);
  const lower = normalised.toLowerCase();

  // 1. Exact match (try normalised Arabic, then lowercased Latin)
  if (EXACT_MAP[normalised] !== undefined) return EXACT_MAP[normalised];
  if (EXACT_MAP[lower] !== undefined) return EXACT_MAP[lower];

  // 2. Contains rules
  for (const { pattern, canonical } of CONTAINS_RULES) {
    if (normalised.includes(pattern) || lower.includes(pattern.toLowerCase())) {
      return canonical;
    }
  }

  // 3. Fallback
  return 'ungraded';
}

/**
 * Clean a raw display_grade into a presentable grade_detail string.
 *
 * - Normalises Arabic script (Persian ya/kaf -> Arabic).
 * - Collapses whitespace.
 * - Fixes known OCR mis-splits (e.g. "الظاه ر" -> "الظاهر").
 * - Returns empty string for null/empty input.
 */
export function cleanGradeDetail(displayGrade: string | null | undefined): string {
  if (!displayGrade) return '';

  let cleaned = normaliseArabic(displayGrade);

  // OCR fixes: broken words
  cleaned = cleaned
    .replace(/الظاه\s+ر/g, 'الظاهر')
    .replace(/المشهو\s+ر/g, 'المشهور')
    .replace(/الصحي\s+ح/g, 'الصحيح')
    .replace(/المعتب\s+ر/g, 'المعتبر')
    .replace(/الموث\s+ق/g, 'الموثق');

  // Final whitespace pass
  cleaned = cleaned.replace(/\s+/g, ' ').trim();

  return cleaned;
}
