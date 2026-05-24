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
  /** Islamic tradition: Sunni, Imami, Zaydi, Ibadi */
  tradition: 'Sunni' | 'Imami' | 'Zaydi' | 'Ibadi';
  /** Geographic/intellectual school of the compiler */
  school?: string;
}

/** Slug-keyed map of all hadith collections */
export const CANONICAL_SOURCES: Record<string, SourceEntry> = {
  bukhari: {
    canonical: 'Sahih Bukhari',
    arabic: 'صحيح البخاري',
    displayLabel: 'Sahih Bukhari',
    compiler: 'Muhammad ibn Ismail al-Bukhari',
    tradition: 'Sunni',
    school: 'Bukhara',
  },
  muslim: {
    canonical: 'Sahih Muslim',
    arabic: 'صحيح مسلم',
    displayLabel: 'Sahih Muslim',
    compiler: 'Muslim ibn al-Hajjaj',
    tradition: 'Sunni',
    school: 'Nishapur',
  },
  abudawud: {
    canonical: "Sunan Abi Da'ud",
    arabic: 'سنن أبي داود',
    displayLabel: 'Sunan Abu Dawud',
    compiler: "Sulaiman ibn al-Ash'ath as-Sijistani",
    tradition: 'Sunni',
    school: 'Sijistan',
  },
  tirmidhi: {
    canonical: "Jami' al-Tirmidhi",
    arabic: 'جامع الترمذي',
    displayLabel: 'Jami at-Tirmidhi',
    compiler: 'Muhammad ibn Isa at-Tirmidhi',
    tradition: 'Sunni',
    school: 'Tirmidh',
  },
  nasai: {
    canonical: "Sunan an-Nasa'i",
    arabic: 'سنن النسائي',
    displayLabel: 'Sunan an-Nasai',
    compiler: "Ahmad ibn Shuaib an-Nasa'i",
    tradition: 'Sunni',
    school: 'Nasa',
  },
  ibnmajah: {
    canonical: 'Sunan Ibn Majah',
    arabic: 'سنن ابن ماجه',
    displayLabel: 'Sunan Ibn Majah',
    compiler: 'Muhammad ibn Yazid Ibn Majah',
    tradition: 'Sunni',
    school: 'Qazvin',
  },
  ahmad: {
    canonical: 'Musnad Ahmad',
    arabic: 'مسند أحمد',
    displayLabel: 'Musnad Ahmad',
    compiler: 'Ahmad ibn Hanbal',
    tradition: 'Sunni',
    school: 'Baghdad',
  },
  musnad_rabi: {
    canonical: 'al-Jami al-Sahih (Musnad al-Rabi ibn Habib)',
    arabic: 'الجامع الصحيح مسند الإمام الربيع بن حبيب',
    displayLabel: 'Musnad al-Rabi',
    compiler: "al-Rabi ibn Habib al-Azdi",
    tradition: 'Ibadi',
    school: 'Basra',
  },
  muwatta: {
    canonical: "Muwatta' Malik",
    arabic: 'موطأ مالك',
    displayLabel: 'Muwatta Malik',
    compiler: 'Malik ibn Anas',
    tradition: 'Sunni',
    school: 'Medina',
  },
  darimi: {
    canonical: 'Sunan al-Darimi',
    arabic: 'سنن الدارمي',
    displayLabel: 'Sunan al-Darimi',
    compiler: 'Abdullah ibn Abd al-Rahman al-Darimi',
    tradition: 'Sunni',
    school: 'Samarqand',
  },
  shafii: {
    canonical: "Musnad al-Shafi'i",
    arabic: 'مسند الشافعي',
    displayLabel: "Musnad al-Shafi'i",
    compiler: "Muhammad ibn Idris al-Shafi'i",
    tradition: 'Sunni',
    school: 'Mecca/Egypt',
  },

  // ─── Imami (Twelver Shia) Collections ───────────────────────────────────────
  kafi: {
    canonical: 'Al-Kafi',
    arabic: 'الكافي',
    displayLabel: 'Al-Kafi',
    compiler: 'Muhammad ibn Ya\'qub al-Kulayni',
    tradition: 'Imami',
    school: 'Baghdad/Qum',
  },
  faqih: {
    canonical: 'Man La Yahduruhu al-Faqih',
    arabic: 'من لا يحضره الفقيه',
    displayLabel: 'Man La Yahduruhu al-Faqih',
    compiler: 'Muhammad ibn Ali ibn Babawayh al-Saduq',
    tradition: 'Imami',
    school: 'Qum',
  },
  nahj_balagha: {
    canonical: 'Nahj al-Balagha',
    arabic: 'نهج البلاغة',
    displayLabel: 'Nahj al-Balagha',
    compiler: 'Al-Sharif al-Radi',
    tradition: 'Imami',
    school: 'Baghdad',
  },
  amali_saduq: {
    canonical: 'Al-Amali (Saduq)',
    arabic: 'الأمالي',
    displayLabel: 'Al-Amali (Saduq)',
    compiler: 'Muhammad ibn Ali ibn Babawayh al-Saduq',
    tradition: 'Imami',
  },
  amali_mufid: {
    canonical: 'Al-Amali (Mufid)',
    arabic: 'الأمالي',
    displayLabel: 'Al-Amali (Mufid)',
    compiler: 'Muhammad ibn Muhammad al-Mufid',
    tradition: 'Imami',
  },
  khisal: {
    canonical: 'Al-Khisal',
    arabic: 'الخصال',
    displayLabel: 'Al-Khisal',
    compiler: 'Muhammad ibn Ali ibn Babawayh al-Saduq',
    tradition: 'Imami',
  },
  ghayba_tusi: {
    canonical: 'Kitab al-Ghayba (Tusi)',
    arabic: 'كتاب الغيبة',
    displayLabel: 'Kitab al-Ghayba (Tusi)',
    compiler: 'Muhammad ibn al-Hasan al-Tusi',
    tradition: 'Imami',
  },
  ghayba_numani: {
    canonical: 'Kitab al-Ghayba (Nu\'mani)',
    arabic: 'كتاب الغيبة',
    displayLabel: 'Kitab al-Ghayba (Nu\'mani)',
    compiler: 'Muhammad ibn Ibrahim al-Nu\'mani',
    tradition: 'Imami',
  },
  thawab_amal: {
    canonical: 'Thawab al-A\'mal',
    arabic: 'ثواب الأعمال',
    displayLabel: 'Thawab al-A\'mal',
    compiler: 'Muhammad ibn Ali ibn Babawayh al-Saduq',
    tradition: 'Imami',
  },
  uyun_rida: {
    canonical: '\'Uyun Akhbar al-Rida',
    arabic: 'عيون أخبار الرضا',
    displayLabel: '\'Uyun Akhbar al-Rida',
    compiler: 'Muhammad ibn Ali ibn Babawayh al-Saduq',
    tradition: 'Imami',
  },
  maani_akhbar: {
    canonical: 'Ma\'ani al-Akhbar',
    arabic: 'معاني الأخبار',
    displayLabel: 'Ma\'ani al-Akhbar',
    compiler: 'Muhammad ibn Ali ibn Babawayh al-Saduq',
    tradition: 'Imami',
  },
  kamil_ziyarat: {
    canonical: 'Kamil al-Ziyarat',
    arabic: 'كامل الزيارات',
    displayLabel: 'Kamil al-Ziyarat',
    compiler: 'Ja\'far ibn Muhammad al-Qummi',
    tradition: 'Imami',
  },
  kamal_din: {
    canonical: 'Kamal al-Din',
    arabic: 'كمال الدين وتمام النعمة',
    displayLabel: 'Kamal al-Din',
    compiler: 'Muhammad ibn Ali ibn Babawayh al-Saduq',
    tradition: 'Imami',
  },
  tawhid_saduq: {
    canonical: 'Al-Tawhid (Saduq)',
    arabic: 'التوحيد',
    displayLabel: 'Al-Tawhid',
    compiler: 'Muhammad ibn Ali ibn Babawayh al-Saduq',
    tradition: 'Imami',
  },
  mujam_mutabara: {
    canonical: 'Mu\'jam al-Ahadith al-Mu\'tabara',
    arabic: 'معجم الأحاديث المعتبرة',
    displayLabel: 'Mu\'jam al-Ahadith al-Mu\'tabara',
    compiler: 'Muhammad Asif al-Muhsini',
    tradition: 'Imami',
  },
  zuhd_ahwazi: {
    canonical: 'Kitab al-Zuhd',
    arabic: 'كتاب الزهد',
    displayLabel: 'Kitab al-Zuhd',
    compiler: 'Husayn ibn Sa\'id al-Ahwazi',
    tradition: 'Imami',
  },
  duafa_ghadairi: {
    canonical: 'Kitab al-Du\'afa',
    arabic: 'كتاب الضعفاء',
    displayLabel: 'Kitab al-Du\'afa',
    compiler: 'Ahmad ibn al-Husayn al-Ghadairi',
    tradition: 'Imami',
  },
  mumin_ahwazi: {
    canonical: 'Kitab al-Mu\'min',
    arabic: 'كتاب المؤمن',
    displayLabel: 'Kitab al-Mu\'min',
    compiler: 'Husayn ibn Sa\'id al-Ahwazi',
    tradition: 'Imami',
  },
  sifat_shia: {
    canonical: 'Sifat al-Shi\'a',
    arabic: 'صفات الشيعة',
    displayLabel: 'Sifat al-Shi\'a',
    compiler: 'Muhammad ibn Ali ibn Babawayh al-Saduq',
    tradition: 'Imami',
  },
  fadail_shia: {
    canonical: 'Fada\'il al-Shi\'a',
    arabic: 'فضائل الشيعة',
    displayLabel: 'Fada\'il al-Shi\'a',
    compiler: 'Muhammad ibn Ali ibn Babawayh al-Saduq',
    tradition: 'Imami',
  },
  huquq_abidin: {
    canonical: 'Risalat al-Huquq',
    arabic: 'رسالة الحقوق',
    displayLabel: 'Risalat al-Huquq',
    compiler: 'Ali ibn al-Husayn Zayn al-Abidin',
    tradition: 'Imami',
  },

  // ─── Zaydi Collections ─────────────────────────────────────────────────────
  musnad_zayd: {
    canonical: 'Musnad al-Imam Zayd ibn Ali',
    arabic: 'مسند الإمام زيد بن علي',
    displayLabel: 'Musnad Zayd ibn Ali',
    compiler: 'Abd al-Aziz ibn Ishaq al-Baghdadi',
    tradition: 'Zaydi',
    school: 'Baghdad/Kufa',
  },
  sahifat_rida: {
    canonical: 'Sahifat al-Imam Ali al-Rida',
    arabic: 'صحيفة الإمام علي الرضا',
    displayLabel: 'Sahifat al-Rida',
    compiler: 'Abd al-Wasit ibn Yahya al-Wasiti (arranger)',
    tradition: 'Zaydi',
    school: 'Medina/Khorasan',
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
