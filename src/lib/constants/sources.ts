/**
 * Canonical source name registry.
 * All import scripts and UI components MUST reference these names.
 */

export interface SourceEntry {
  /** Canonical DB name — used in Neo4j Source.name and Hadith.source */
  canonical: string;
  /** Arabic name */
  arabic: string;
  /** Human-friendly display label for UI */
  displayLabel: string;
  /** Compiler/author */
  compiler: string;
}

/** Slug-keyed map of all hadith collections */
export const CANONICAL_SOURCES: Record<string, SourceEntry> = {
  bukhari: {
    canonical: 'Sahih Bukhari',
    arabic: 'صحيح البخاري',
    displayLabel: 'Sahih Bukhari',
    compiler: 'Muhammad ibn Ismail al-Bukhari',
  },
  muslim: {
    canonical: 'Sahih Muslim',
    arabic: 'صحيح مسلم',
    displayLabel: 'Sahih Muslim',
    compiler: 'Muslim ibn al-Hajjaj',
  },
  abudawud: {
    canonical: "Sunan Abi Da'ud",
    arabic: 'سنن أبي داود',
    displayLabel: 'Sunan Abu Dawud',
    compiler: "Sulaiman ibn al-Ash'ath as-Sijistani",
  },
  tirmidhi: {
    canonical: "Jami' al-Tirmidhi",
    arabic: 'جامع الترمذي',
    displayLabel: 'Jami at-Tirmidhi',
    compiler: 'Muhammad ibn Isa at-Tirmidhi',
  },
  nasai: {
    canonical: "Sunan an-Nasa'i",
    arabic: 'سنن النسائي',
    displayLabel: 'Sunan an-Nasai',
    compiler: "Ahmad ibn Shuaib an-Nasa'i",
  },
  ibnmajah: {
    canonical: 'Sunan Ibn Majah',
    arabic: 'سنن ابن ماجه',
    displayLabel: 'Sunan Ibn Majah',
    compiler: 'Muhammad ibn Yazid Ibn Majah',
  },
  ahmad: {
    canonical: 'Musnad Ahmad',
    arabic: 'مسند أحمد',
    displayLabel: 'Musnad Ahmad',
    compiler: 'Ahmad ibn Hanbal',
  },
  musnad_rabi: {
    canonical: "al-Jami' al-Sahih -- Musnad al-Imam al-Rabi' b. Habib",
    arabic: 'الجامع الصحيح — مسند الإمام الربيع بن حبيب',
    displayLabel: 'Musnad al-Rabi',
    compiler: "al-Rabi' b. Habib b. 'Amr al-Farahidi al-Azdi",
  },
  muwatta: {
    canonical: "Muwatta' Malik",
    arabic: 'موطأ مالك',
    displayLabel: 'Muwatta Malik',
    compiler: 'Malik ibn Anas',
  },
  darimi: {
    canonical: 'Sunan al-Darimi',
    arabic: 'سنن الدارمي',
    displayLabel: 'Sunan al-Darimi',
    compiler: 'Abdullah ibn Abd al-Rahman al-Darimi',
  },
  shafii: {
    canonical: "Musnad al-Shafi'i",
    arabic: 'مسند الشافعي',
    displayLabel: "Musnad al-Shafi'i",
    compiler: "Muhammad ibn Idris al-Shafi'i",
  },
};

/** Get canonical DB name from slug */
export function getCanonicalName(slug: string): string {
  const entry = CANONICAL_SOURCES[slug];
  if (!entry) throw new Error(`Unknown source slug: ${slug}`);
  return entry.canonical;
}

/** Get all source filter options for UI dropdowns */
export function getSourceFilterOptions(): Array<{ label: string; value: string }> {
  return [
    { label: 'All Sources', value: '' },
    ...Object.values(CANONICAL_SOURCES).map((s) => ({
      label: s.displayLabel,
      value: s.canonical,
    })),
  ];
}
