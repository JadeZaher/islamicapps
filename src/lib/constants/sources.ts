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

  // ─── Shia Collections ───────────────────────────────────────────────────────
  kafi: {
    canonical: 'Al-Kafi',
    arabic: 'الكافي',
    displayLabel: 'Al-Kafi',
    compiler: 'Muhammad ibn Ya\'qub al-Kulayni',
  },
  faqih: {
    canonical: 'Man La Yahduruhu al-Faqih',
    arabic: 'من لا يحضره الفقيه',
    displayLabel: 'Man La Yahduruhu al-Faqih',
    compiler: 'Muhammad ibn Ali ibn Babawayh al-Saduq',
  },
  nahj_balagha: {
    canonical: 'Nahj al-Balagha',
    arabic: 'نهج البلاغة',
    displayLabel: 'Nahj al-Balagha',
    compiler: 'Al-Sharif al-Radi',
  },
  amali_saduq: {
    canonical: 'Al-Amali (Saduq)',
    arabic: 'الأمالي',
    displayLabel: 'Al-Amali (Saduq)',
    compiler: 'Muhammad ibn Ali ibn Babawayh al-Saduq',
  },
  amali_mufid: {
    canonical: 'Al-Amali (Mufid)',
    arabic: 'الأمالي',
    displayLabel: 'Al-Amali (Mufid)',
    compiler: 'Muhammad ibn Muhammad al-Mufid',
  },
  khisal: {
    canonical: 'Al-Khisal',
    arabic: 'الخصال',
    displayLabel: 'Al-Khisal',
    compiler: 'Muhammad ibn Ali ibn Babawayh al-Saduq',
  },
  ghayba_tusi: {
    canonical: 'Kitab al-Ghayba (Tusi)',
    arabic: 'كتاب الغيبة',
    displayLabel: 'Kitab al-Ghayba (Tusi)',
    compiler: 'Muhammad ibn al-Hasan al-Tusi',
  },
  ghayba_numani: {
    canonical: 'Kitab al-Ghayba (Nu\'mani)',
    arabic: 'كتاب الغيبة',
    displayLabel: 'Kitab al-Ghayba (Nu\'mani)',
    compiler: 'Muhammad ibn Ibrahim al-Nu\'mani',
  },
  thawab_amal: {
    canonical: 'Thawab al-A\'mal',
    arabic: 'ثواب الأعمال',
    displayLabel: 'Thawab al-A\'mal',
    compiler: 'Muhammad ibn Ali ibn Babawayh al-Saduq',
  },
  uyun_rida: {
    canonical: '\'Uyun Akhbar al-Rida',
    arabic: 'عيون أخبار الرضا',
    displayLabel: '\'Uyun Akhbar al-Rida',
    compiler: 'Muhammad ibn Ali ibn Babawayh al-Saduq',
  },
  maani_akhbar: {
    canonical: 'Ma\'ani al-Akhbar',
    arabic: 'معاني الأخبار',
    displayLabel: 'Ma\'ani al-Akhbar',
    compiler: 'Muhammad ibn Ali ibn Babawayh al-Saduq',
  },
  kamil_ziyarat: {
    canonical: 'Kamil al-Ziyarat',
    arabic: 'كامل الزيارات',
    displayLabel: 'Kamil al-Ziyarat',
    compiler: 'Ja\'far ibn Muhammad al-Qummi',
  },
  kamal_din: {
    canonical: 'Kamal al-Din',
    arabic: 'كمال الدين وتمام النعمة',
    displayLabel: 'Kamal al-Din',
    compiler: 'Muhammad ibn Ali ibn Babawayh al-Saduq',
  },
  tawhid_saduq: {
    canonical: 'Al-Tawhid (Saduq)',
    arabic: 'التوحيد',
    displayLabel: 'Al-Tawhid',
    compiler: 'Muhammad ibn Ali ibn Babawayh al-Saduq',
  },
  mujam_mutabara: {
    canonical: 'Mu\'jam al-Ahadith al-Mu\'tabara',
    arabic: 'معجم الأحاديث المعتبرة',
    displayLabel: 'Mu\'jam al-Ahadith al-Mu\'tabara',
    compiler: 'Muhammad Asif al-Muhsini',
  },
  zuhd_ahwazi: {
    canonical: 'Kitab al-Zuhd',
    arabic: 'كتاب الزهد',
    displayLabel: 'Kitab al-Zuhd',
    compiler: 'Husayn ibn Sa\'id al-Ahwazi',
  },
  duafa_ghadairi: {
    canonical: 'Kitab al-Du\'afa',
    arabic: 'كتاب الضعفاء',
    displayLabel: 'Kitab al-Du\'afa',
    compiler: 'Ahmad ibn al-Husayn al-Ghadairi',
  },
  mumin_ahwazi: {
    canonical: 'Kitab al-Mu\'min',
    arabic: 'كتاب المؤمن',
    displayLabel: 'Kitab al-Mu\'min',
    compiler: 'Husayn ibn Sa\'id al-Ahwazi',
  },
  sifat_shia: {
    canonical: 'Sifat al-Shi\'a',
    arabic: 'صفات الشيعة',
    displayLabel: 'Sifat al-Shi\'a',
    compiler: 'Muhammad ibn Ali ibn Babawayh al-Saduq',
  },
  fadail_shia: {
    canonical: 'Fada\'il al-Shi\'a',
    arabic: 'فضائل الشيعة',
    displayLabel: 'Fada\'il al-Shi\'a',
    compiler: 'Muhammad ibn Ali ibn Babawayh al-Saduq',
  },
  huquq_abidin: {
    canonical: 'Risalat al-Huquq',
    arabic: 'رسالة الحقوق',
    displayLabel: 'Risalat al-Huquq',
    compiler: 'Ali ibn al-Husayn Zayn al-Abidin',
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
