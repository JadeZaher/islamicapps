/**
 * The glossary: the single source of term definitions for the app, docs/glossary.md and the data pipeline.
 * See src/lib/glossary/AGENTS.md for the writing rules, the transliteration scheme and how the doc is generated.
 */

export type GlossarySectionId =
  | 'traditions'
  | 'names'
  | 'transmission'
  | 'narrator-criticism'
  | 'report-grading'
  | 'works'
  | 'comparative'
  | 'archive';

export interface GlossarySection {
  id: GlossarySectionId;
  title: string;
}

/** A Postgres enum value this entry explains, written `<enum_name>.<value>` (see src/db/schema/enums.ts). */
export type EnumValueReference = `${string}.${string}`;

export interface GlossaryEntry {
  /** Stable anchor id: `/glossary#<slug>`. Lowercase ASCII words joined by hyphens. */
  slug: string;
  section: GlossarySectionId;
  /** The term in the archive's transliteration (or plain English for archive terms). */
  term: string;
  /** Short English rendering, when the term itself is not English. */
  english?: string;
  arabic?: string;
  /** One plain sentence a non-specialist can follow. */
  definition: string;
  /** How the app uses or displays it. */
  inArchive?: string;
  /** Where usage differs between traditions or critics. */
  acrossTraditions?: string;
  related?: readonly string[];
  /** Other spellings readers may type into the filter. */
  aliases?: readonly string[];
  /** Database enum values this entry explains. */
  enumValues?: readonly EnumValueReference[];
  /** A specific doubt for the owner to check; listed in docs/glossary.md, never shown on the public page. */
  ownerReview?: string;
}

export const GLOSSARY_SECTIONS: readonly GlossarySection[] = [
  { id: 'traditions', title: 'Traditions' },
  { id: 'names', title: 'Names' },
  { id: 'transmission', title: 'Transmission' },
  { id: 'narrator-criticism', title: 'Narrator criticism' },
  { id: 'report-grading', title: 'Report grading' },
  { id: 'works', title: 'Works and genres' },
  { id: 'comparative', title: 'Comparative study and history' },
  { id: 'archive', title: 'Archive terms' },
];

export const TRANSLITERATION_NOTE =
  'Arabic terms are written in a simple scheme: no long-vowel or dot marks; ʿ for ʿayn and ʾ for hamza (not written at the start of a word); ' +
  'th, dh, kh, sh and gh for single Arabic letters; doubled letters written twice; the article always as al-; ta marbuta as -a. ' +
  'Words already common in English (hadith, isnad, Sunni, Imami, Zaydi, Ibadi) keep their usual spelling.';

export const GLOSSARY_ENTRIES: readonly GlossaryEntry[] = [
  // ── Traditions (alphabetical, so no tradition is listed as the default) ─────────────────────────
  {
    slug: 'ibadi',
    section: 'traditions',
    term: 'Ibadi',
    arabic: 'الإباضية',
    definition:
      'A Muslim tradition that traces its origins to scholars of early Basra and is found today mainly in Oman and parts of North Africa.',
    inArchive:
      'Its reports here come from al-Jamiʿ al-Sahih, the Musnad of al-Rabiʿ ibn Habib. The archive holds no per-report gradings for Ibadi works.',
    related: ['ibadi-report-acceptance', 'jami', 'sahih-collection'],
    enumValues: ['hadith_tradition.Ibadi'],
    ownerReview: 'Check the one-line description of the tradition and its present-day regions.',
  },
  {
    slug: 'imami',
    section: 'traditions',
    term: 'Imami',
    english: 'Twelver Shiʿi',
    arabic: 'الإمامية',
    definition:
      'The Shiʿi tradition that recognises twelve Imams from the Prophet’s family and transmits their sayings as hadith alongside the Prophet’s.',
    inArchive:
      'Imami reports come chiefly from the Four Books and related works. Their gradings are rulings by named later scholars, such as al-Majlisi, each with a citation.',
    related: ['four-books', 'imami-grading', 'imam-report'],
    aliases: ['Twelver', 'Shia', 'Ithna ʿAshari'],
    enumValues: ['hadith_tradition.Imami'],
  },
  {
    slug: 'sunni',
    section: 'traditions',
    term: 'Sunni',
    arabic: 'أهل السنة والجماعة',
    definition:
      'The tradition of Ahl al-Sunna wa al-Jamaʿa, the largest body of Muslims, whose best-known hadith collections are the Six Books.',
    inArchive:
      'Gradings shown are statements by a named compiler or critic. The archive does not compute a grade of its own.',
    related: ['six-books', 'sunni-grading'],
    aliases: ['Ahl al-Sunna'],
    enumValues: ['hadith_tradition.Sunni'],
  },
  {
    slug: 'zaydi',
    section: 'traditions',
    term: 'Zaydi',
    arabic: 'الزيدية',
    definition: 'The Shiʿi tradition named after Zayd ibn ʿAli ibn al-Husayn, historically centred in Yemen.',
    inArchive:
      'Its reports here come from Musnad al-Imam Zayd ibn ʿAli. The archive holds no per-report gradings for Zaydi works.',
    related: ['zaydi-report-acceptance', 'musnad', 'amali'],
    enumValues: ['hadith_tradition.Zaydi'],
    ownerReview: 'Check the one-line description, and whether other Zaydi works (such as amali collections) should be named.',
  },

  // ── Names ───────────────────────────────────────────────────────────────────────────────────────
  {
    slug: 'ism',
    section: 'names',
    term: 'ism',
    english: 'given name',
    arabic: 'اسم',
    definition: 'A person’s own given name, such as Muhammad, ʿAli or ʿAʾisha.',
    inArchive: 'A given name on its own is shared by many narrators, so the archive never identifies a person from it alone.',
    related: ['kunya', 'nasab', 'nisba', 'laqab', 'single-name-mention'],
  },
  {
    slug: 'kunya',
    section: 'names',
    term: 'kunya',
    english: 'teknonym',
    arabic: 'كنية',
    definition:
      'A name of the form “father of” (Abu) or “mother of” (Umm) followed by another name, such as Abu Hurayra or Umm Salama, used as a respectful way of naming someone.',
    inArchive:
      'Many narrators share the same kunya. A chain that names someone only by kunya is never treated as identified by itself; an automatic match on a kunya alone is labelled “matched by kunya only”.',
    acrossTraditions:
      'In Imami chains, Abu ʿAbd Allah and Abu Jaʿfar usually refer to particular Imams (Jaʿfar al-Sadiq and Muhammad al-Baqir), while in other chains the same kunyas refer to many different people. Context, not the kunya, settles who is meant.',
    related: ['single-name-mention', 'matched-by-kunya-only', 'ism', 'mushtarak'],
    aliases: ['kunyah', 'Abu', 'Umm'],
  },
  {
    slug: 'nasab',
    section: 'names',
    term: 'nasab',
    english: 'lineage',
    arabic: 'نسب',
    definition: 'The chain of “son of” (ibn) or “daughter of” (bint) that names a person’s father and earlier ancestors.',
    inArchive:
      'A name with a nasab is more specific than a single name, which is why the archive’s narrator matching allows some spelling folds only for names that carry one.',
    related: ['ism', 'kunya', 'single-name-mention'],
    aliases: ['ibn', 'bint', 'lineage'],
  },
  {
    slug: 'nisba',
    section: 'names',
    term: 'nisba',
    english: 'relational name',
    arabic: 'نسبة',
    definition:
      'A name ending in -i that ties a person to a place, tribe, trade or school, such as al-Kufi (of Kufa) or al-Zuhri (of the Zuhra clan).',
    inArchive: 'A nisba alone, like a single name, can point to more than one narrator.',
    related: ['ism', 'laqab', 'mushtarak'],
  },
  {
    slug: 'laqab',
    section: 'names',
    term: 'laqab',
    english: 'epithet',
    arabic: 'لقب',
    definition: 'A descriptive title or nickname, such as al-Sadiq (the truthful) or al-Aʿmash (the bleary-eyed).',
    inArchive: 'Identity decisions based only on a laqab require a citation before a curator may record them.',
    related: ['ism', 'kunya', 'nisba'],
  },
  {
    slug: 'single-name-mention',
    section: 'names',
    term: 'Kunya-only and single-name mentions',
    definition:
      'A place in a chain where a narrator is named only by a kunya, a single given name or a single epithet, which many different people share.',
    inArchive:
      'Such a mention does not identify a person. The archive shows it as written and leaves it unidentified unless a curator records a cited decision; lexicon entries that are only a kunya or a single word are never used as match targets.',
    acrossTraditions:
      'Critics in every tradition resolve such names from context: who the narrator heard from, who heard from him, and his generation.',
    related: ['kunya', 'ism', 'mushtarak', 'not-yet-identified', 'placeholder-entry'],
  },
  {
    slug: 'mushtarak',
    section: 'names',
    term: 'mushtarak',
    english: 'shared name',
    arabic: 'المشترك',
    definition:
      'A name borne by two or more narrators; telling them apart (tamyiz al-mushtarakat) is a recognised branch of narrator study.',
    inArchive:
      'Because the same name can mean different people depending on teacher and student, identity decisions are recorded for a name in its context, not for the name everywhere.',
    related: ['single-name-mention', 'review-unit', 'identity-decision'],
    aliases: ['tamyiz al-mushtarakat'],
  },

  // ── Transmission ────────────────────────────────────────────────────────────────────────────────
  {
    slug: 'hadith',
    section: 'transmission',
    term: 'hadith',
    arabic: 'حديث',
    definition:
      'A report of what the Prophet said, did or approved, carried by a chain of named narrators; the word is also used for the whole body of such reports.',
    acrossTraditions:
      'Sunni, Zaydi and Ibadi usage centres on reports from the Prophet. Imami usage also includes the sayings of the twelve Imams (and of Fatima), regarded in that tradition as authoritative teachers.',
    related: ['khabar', 'athar', 'isnad', 'matn', 'imam-report'],
    aliases: ['hadeeth', 'ahadith'],
    ownerReview:
      'Check whether the Zaydi and Ibadi notes need more: the weight Zaydis give to reports from ʿAli and the Prophet’s family, and the Ibadi inclusion of reports from Jabir ibn Zayd.',
  },
  {
    slug: 'khabar',
    section: 'transmission',
    term: 'khabar',
    english: 'report',
    arabic: 'خبر',
    definition:
      'A report; some scholars use it as another word for hadith, while others reserve it for reports about people other than the Prophet.',
    acrossTraditions: 'Imami writing commonly uses khabar (plural akhbar) for reports from the Prophet and the Imams.',
    related: ['hadith', 'athar', 'riwaya'],
    aliases: ['akhbar'],
    ownerReview: 'Confirm the Imami usage note, and whether Zaydi or Ibadi usage differs.',
  },
  {
    slug: 'athar',
    section: 'transmission',
    term: 'athar',
    english: 'report, trace',
    arabic: 'أثر',
    definition:
      'A transmitted report; many scholars use it especially for sayings of Companions and Followers, while others apply it to any report, including the Prophet’s.',
    related: ['hadith', 'khabar', 'mawquf', 'maqtu'],
    aliases: ['athar', 'aathaar'],
  },
  {
    slug: 'riwaya',
    section: 'transmission',
    term: 'riwaya',
    english: 'transmission',
    arabic: 'رواية',
    definition: 'The act of passing on a report, or one particular transmitted version of it.',
    inArchive: 'Different versions of a report kept in the archive are shown under “Variant texts”.',
    related: ['rawi', 'hadith', 'isnad'],
    aliases: ['riwayah', 'narration'],
  },
  {
    slug: 'isnad',
    section: 'transmission',
    term: 'isnad',
    english: 'chain of transmission',
    arabic: 'إسناد',
    definition:
      'The list of narrators through whom a report reached the compiler, each said to have received it from the next; sanad is usually used as a synonym.',
    inArchive:
      'The isnad is always shown as written in the Arabic source. Narrators are linked to their profiles only where the identification meets the archive’s rules; every other name stays plain text.',
    related: ['matn', 'rawi', 'chain-status', 'mention', 'tahwil'],
    aliases: ['sanad', 'chain', 'asanid'],
  },
  {
    slug: 'matn',
    section: 'transmission',
    term: 'matn',
    english: 'report text',
    arabic: 'متن',
    definition: 'The content of a report itself, the words that follow the chain of narrators.',
    inArchive: 'Shown as “Matn · report text” when the source text can be split from its chain, otherwise as “Text as in the source”.',
    related: ['isnad', 'hadith'],
  },
  {
    slug: 'rawi',
    section: 'transmission',
    term: 'rawi',
    english: 'narrator',
    arabic: 'راوٍ',
    definition: 'A person who passes on a report they received; one link in an isnad.',
    inArchive: 'Narrator pages collect what the archive knows about one person, with each claim attributed to its source.',
    related: ['isnad', 'tabaqa', 'jarh-wa-tadil'],
    aliases: ['narrator', 'ruwat'],
    enumValues: ['narrator_authority.rawi'],
  },
  {
    slug: 'tabaqa',
    section: 'transmission',
    term: 'tabaqa',
    english: 'generation',
    arabic: 'طبقة',
    definition:
      'A generation or layer of narrators who lived and transmitted at about the same time, used to check that a student could have heard from a teacher.',
    inArchive:
      'Narrator pages show the generation on a short scale: the Prophet, Companions, Followers, Followers of the Followers, and later scholars. It is highlighted only when it is recorded.',
    acrossTraditions:
      'Critics divide generations differently: some use broad layers like these, others finer divisions (Ibn Hajar uses twelve). Imami narrator works often group narrators by the Imam they transmitted from instead.',
    related: ['sahabi', 'tabii', 'atba-al-tabiin'],
    aliases: ['tabaqah', 'tabaqat', 'generation'],
    enumValues: ['tabaqah_class.ATBA_ATBA', 'tabaqah_class.LATER_SCHOLAR'],
  },
  {
    slug: 'sahabi',
    section: 'transmission',
    term: 'sahabi',
    english: 'Companion',
    arabic: 'صحابي',
    definition: 'A person who met the Prophet as a believer; the Companions (sahaba) are the first generation of narrators.',
    acrossTraditions:
      'Traditions differ on how Companions are assessed as narrators: Sunni scholarship holds them collectively upright, while Imami scholarship, among others, assesses them individually. Imami works also speak of the “companions” (ashab) of each Imam.',
    related: ['tabaqa', 'tabii', 'adalat-al-sahaba'],
    aliases: ['Companion', 'sahaba', 'ashab'],
    enumValues: ['tabaqah_class.SAHABA'],
  },
  {
    slug: 'tabii',
    section: 'transmission',
    term: 'tabiʿi',
    english: 'Follower',
    arabic: 'تابعي',
    definition: 'A person of the generation after the Companions who met and learned from at least one Companion.',
    related: ['tabaqa', 'sahabi', 'atba-al-tabiin', 'maqtu'],
    aliases: ['Follower', 'Successor', 'tabiun', 'tabiʿun'],
    enumValues: ['tabaqah_class.TABIUN'],
  },
  {
    slug: 'atba-al-tabiin',
    section: 'transmission',
    term: 'atbaʿ al-tabiʿin',
    english: 'Followers of the Followers',
    arabic: 'أتباع التابعين',
    definition: 'The generation that learned from the Followers, the third generation of narrators.',
    related: ['tabaqa', 'tabii'],
    aliases: ['Successors of the Successors', 'tabi al-tabiin'],
    enumValues: ['tabaqah_class.ATBA_TABIUN'],
  },
  {
    slug: 'imam-report',
    section: 'transmission',
    term: 'Report from an Imam',
    definition: 'A report whose chain ends at one of the Imams rather than at the Prophet.',
    inArchive: 'Recorded as the narration level “imam”.',
    acrossTraditions:
      'In Imami usage such a report is a hadith in the full sense. Sunni terminology classifies a saying by the speaker’s generation, so the same words would be mawquf (from ʿAli, a Companion) or maqtuʿ (from a later Imam).',
    related: ['hadith', 'marfu', 'mawquf', 'maqtu', 'imami'],
    enumValues: ['narration_level.imam'],
    ownerReview: 'Confirm whether the data’s narration level “imam” is also used for reports ending at Zaydi imams.',
  },
  {
    slug: 'mudmar',
    section: 'transmission',
    term: 'mudmar',
    english: 'with the source unnamed',
    arabic: 'مضمر',
    definition:
      'A report in which the narrator refers to the Imam he asked only by a pronoun, such as “I asked him”, without naming him.',
    inArchive: 'The term appears in Imami gradings carried by the data.',
    acrossTraditions:
      'An Imami term. Imami scholars discuss when such a report can be relied on, for example when the narrator is known to have put questions only to an Imam.',
    related: ['mursal', 'imam-report', 'imami-grading'],
    ownerReview:
      'The grade mapping in src/lib/constants/grade-taxonomy.ts groups مضمر with mursal. Confirm whether that grouping is acceptable or should be kept separate.',
  },
  {
    slug: 'haddathana',
    section: 'transmission',
    term: 'haddathana',
    english: '“he narrated to us”',
    arabic: 'حدّثنا',
    definition: 'A transmission formula stating that the teacher narrated the report to the speaker, ordinarily meaning it was heard directly.',
    acrossTraditions:
      'The same formulas appear in chains of all four traditions. Conventions for reading them were set by critics and are not identical between them.',
    related: ['akhbarana', 'samitu', 'an', 'qala'],
    aliases: ['haddathani', 'hadathana'],
  },
  {
    slug: 'akhbarana',
    section: 'transmission',
    term: 'akhbarana',
    english: '“he informed us”',
    arabic: 'أخبرنا',
    definition: 'A transmission formula stating that the teacher informed the speaker of the report.',
    acrossTraditions:
      'Usage differs: some critics treat it as equivalent to haddathana, while others reserve it for a text read aloud to the teacher and confirmed by him.',
    related: ['haddathana', 'samitu', 'an'],
    aliases: ['akhbarani'],
    ownerReview: 'Check the summary of the difference in usage, and whether any tradition-specific note should be added.',
  },
  {
    slug: 'an',
    section: 'transmission',
    term: 'ʿan',
    english: '“from”',
    arabic: 'عن',
    definition:
      'A formula saying only that the report came “from” a narrator, without stating how it was received; a chain linked this way is called muʿanʿan.',
    acrossTraditions:
      'Critics differ on when ʿan counts as direct transmission: some require that the two narrators are known to have met, others accept that they lived at the same time. For a narrator known for tadlis it is not taken as proof of hearing.',
    related: ['tadlis', 'samitu', 'haddathana', 'qala'],
    aliases: ['anana', 'ʿanʿana', 'muʿanʿan', 'muanan'],
  },
  {
    slug: 'samitu',
    section: 'transmission',
    term: 'samiʿtu',
    english: '“I heard”',
    arabic: 'سمعت',
    definition: 'A formula in which the narrator states that he heard the report directly from the person named.',
    inArchive: 'The formula records the narrator’s claim; it does not by itself verify who the person named is.',
    related: ['haddathana', 'an'],
    aliases: ['samitu', 'samaʿ'],
  },
  {
    slug: 'qala',
    section: 'transmission',
    term: 'qala',
    english: '“he said”',
    arabic: 'قال',
    definition:
      'A formula attributing words to a narrator without stating how they were received; like ʿan, it does not on its own show direct hearing.',
    related: ['an', 'muallaq', 'compiler-statement'],
  },
  {
    slug: 'tahwil',
    section: 'transmission',
    term: 'tahwil',
    english: 'switch of chain',
    arabic: 'تحويل (ح)',
    definition:
      'A switch from one chain to another partway through an isnad, marked by the letter ح, so that two or more chains share their later part.',
    inArchive:
      'The archive follows each branch at a ح and joins branches only where the Arabic shows where they meet; where it cannot tell, the branches stay separate rather than being guessed together.',
    related: ['isnad', 'mutaba'],
    aliases: ['tahweel', 'ha'],
  },
  {
    slug: 'mutaba',
    section: 'transmission',
    term: 'mutabaʿa',
    english: 'corroborating transmission',
    arabic: 'متابعة',
    definition:
      'A second transmission of the same report through another narrator who shares a teacher, or a teacher higher up, with the first.',
    acrossTraditions:
      'Some critics separate mutabaʿa from shahid by whether the same Companion is involved, others by whether the wording or only the meaning agrees.',
    related: ['shahid', 'gharib'],
    aliases: ['mutabaa', 'mutabaʿat'],
    ownerReview: 'Confirm whether the Imami, Zaydi or Ibadi literature uses these two terms differently from the description given.',
  },
  {
    slug: 'shahid',
    section: 'transmission',
    term: 'shahid',
    english: 'supporting report',
    arabic: 'شاهد',
    definition: 'A separate report, usually from a different Companion, that supports the meaning of another report.',
    related: ['mutaba', 'gharib'],
    aliases: ['shawahid'],
  },
  {
    slug: 'mursal',
    section: 'transmission',
    term: 'mursal',
    english: 'with a link omitted',
    arabic: 'مرسل',
    definition: 'A report whose chain leaves out a narrator, classically a Follower quoting the Prophet without naming the Companion.',
    inArchive: 'Appears both as a description of a chain and as a grade in Imami gradings.',
    acrossTraditions:
      'In Imami usage the term is broader: any report whose chain drops a narrator or names one only vaguely (“from a man”). Whether mursal reports can be accepted is disputed within each tradition, and some scholars accept those of particular narrators.',
    related: ['munqati', 'mudal', 'muallaq', 'mubham', 'imami-grading'],
    aliases: ['marasil'],
    enumValues: ['grade_canonical.mursal'],
    ownerReview: 'Check the summary of the Imami sense and of the dispute over acceptance.',
  },
  {
    slug: 'munqati',
    section: 'transmission',
    term: 'munqatiʿ',
    english: 'broken',
    arabic: 'منقطع',
    definition: 'A report whose chain is broken by one or more missing narrators; some critics use it for any break, others only for a single missing link.',
    related: ['mursal', 'mudal', 'muallaq'],
    aliases: ['munqati'],
  },
  {
    slug: 'mudal',
    section: 'transmission',
    term: 'muʿdal',
    english: 'doubly broken',
    arabic: 'معضل',
    definition: 'A report whose chain is missing two or more narrators in succession.',
    related: ['munqati', 'mursal'],
    aliases: ['mudal'],
  },
  {
    slug: 'muallaq',
    section: 'transmission',
    term: 'muʿallaq',
    english: 'suspended',
    arabic: 'معلق',
    definition:
      'A report whose chain is cut at the compiler’s end, with one or more of the compiler’s own authorities left out; al-Bukhari’s Sahih contains many.',
    related: ['munqati', 'qala'],
    aliases: ['muallaq', 'taʿliq'],
  },
  {
    slug: 'mubham',
    section: 'transmission',
    term: 'mubham',
    english: 'unnamed narrator',
    arabic: 'مبهم',
    definition: 'A narrator referred to without a name, such as “a man” or “a shaykh”.',
    inArchive: 'Recorded as an anonymous link: it is part of the chain, but it never identifies a person.',
    related: ['collective-mention', 'mursal', 'majhul'],
    aliases: ['anonymous', 'rajul'],
    enumValues: ['link_kind.anonymous', 'surface_decision_kind.anonymous'],
  },
  {
    slug: 'marfu',
    section: 'transmission',
    term: 'marfuʿ',
    english: 'raised (to the Prophet)',
    arabic: 'مرفوع',
    definition: 'A report attributed to the Prophet himself, whatever the state of its chain.',
    inArchive: 'Recorded as the narration level “marfu”.',
    acrossTraditions:
      'In some Imami grading notes, marfuʿ instead describes a chain in which a narrator “raised” the report to the Imam with the intermediate narrators left out.',
    related: ['mawquf', 'maqtu', 'imam-report', 'mursal'],
    aliases: ['marfu'],
    enumValues: ['narration_level.marfu'],
    ownerReview:
      'Confirm the Imami sense. The grade mapping in src/lib/constants/grade-taxonomy.ts maps مرفوع to mursal, which fits only that Imami sense.',
  },
  {
    slug: 'mawquf',
    section: 'transmission',
    term: 'mawquf',
    english: 'stopped (at a Companion)',
    arabic: 'موقوف',
    definition: 'A report whose chain stops at a Companion, giving the Companion’s own words or deeds rather than the Prophet’s.',
    inArchive: 'Recorded as the narration level “mawquf”.',
    acrossTraditions: 'Imami works on hadith terms define it relative to the Prophet or an Imam: a report that stops at someone other than them.',
    related: ['marfu', 'maqtu', 'athar'],
    enumValues: ['narration_level.mawquf'],
    ownerReview: 'Confirm the Imami definition.',
  },
  {
    slug: 'maqtu',
    section: 'transmission',
    term: 'maqtuʿ',
    english: 'ending at a Follower',
    arabic: 'مقطوع',
    definition: 'A report whose chain stops at a Follower or someone later, giving that person’s own words.',
    inArchive: 'Recorded as the narration level “maqtu”. Not to be confused with munqatiʿ, which describes a broken chain.',
    related: ['mawquf', 'marfu', 'munqati'],
    aliases: ['maqtu'],
    enumValues: ['narration_level.maqtu'],
    ownerReview: 'Confirm whether Imami usage differs.',
  },
  {
    slug: 'mutawatir',
    section: 'transmission',
    term: 'mutawatir',
    english: 'mass-transmitted',
    arabic: 'متواتر',
    definition: 'A report carried by so many independent narrators at every stage that their agreement on a falsehood is considered impossible.',
    acrossTraditions:
      'All four traditions use the distinction, but scholars differ on how many narrators are needed and on which reports qualify.',
    related: ['ahad'],
    aliases: ['tawatur'],
  },
  {
    slug: 'ahad',
    section: 'transmission',
    term: 'ahad',
    english: 'solitary reports',
    arabic: 'آحاد',
    definition: 'A report that does not reach the level of mutawatir; most reports are ahad.',
    acrossTraditions:
      'Traditions and schools within them differ on what weight an ahad report carries in belief and in law.',
    related: ['mutawatir', 'gharib'],
    aliases: ['khabar al-wahid', 'ahaad'],
  },
  {
    slug: 'illa',
    section: 'transmission',
    term: 'ʿilla',
    english: 'hidden defect',
    arabic: 'علة',
    definition: 'A hidden flaw in a report that looks sound on the surface, such as an unnoticed break or a misattribution, found by comparing its transmissions.',
    related: ['sahih', 'tadlis'],
    aliases: ['illa', 'muʿallal', 'ilal'],
  },
  {
    slug: 'tadlis',
    section: 'transmission',
    term: 'tadlis',
    english: 'concealment',
    arabic: 'تدليس',
    definition:
      'Transmitting in a way that hides a gap or a weak narrator, for example using ʿan for something not heard directly; a narrator who does this is a mudallis.',
    related: ['an', 'illa'],
    aliases: ['mudallis'],
  },

  // ── Narrator criticism ──────────────────────────────────────────────────────────────────────────
  {
    slug: 'jarh-wa-tadil',
    section: 'narrator-criticism',
    term: 'al-jarh wa al-taʿdil',
    english: 'criticism and praise',
    arabic: 'الجرح والتعديل',
    definition: 'The assessment of narrators, recording critics’ judgements that weaken (jarh) or support (taʿdil) a narrator’s reliability.',
    inArchive:
      'Each verdict is meant to be shown with its critic and tradition. Terms and their weight differ between critics and between traditions, so the archive does not convert one critic’s word into another’s.',
    related: ['adala', 'dabt', 'thiqa', 'daif', 'narrator-verdict', 'rijal'],
    aliases: ['jarh', 'tadil', 'taʿdil'],
    enumValues: ['narrator_assessment_kind.critic_ruling'],
  },
  {
    slug: 'adala',
    section: 'narrator-criticism',
    term: 'ʿadala',
    english: 'probity',
    arabic: 'عدالة',
    definition: 'A narrator’s religious and moral integrity, one of the two qualities critics require before trusting a report.',
    acrossTraditions:
      'What ʿadala requires differs: in the Imami scheme a fully sound (sahih) chain needs narrators who are Imami as well as upright, while Sunni critics do not make school membership a condition in the same way.',
    related: ['dabt', 'jarh-wa-tadil', 'adalat-al-sahaba'],
    aliases: ['adala', 'adl', 'ʿadl'],
  },
  {
    slug: 'dabt',
    section: 'narrator-criticism',
    term: 'dabt',
    english: 'accuracy',
    arabic: 'ضبط',
    definition: 'A narrator’s precision in preserving a report, from memory or in writing, the second quality critics require.',
    related: ['adala', 'thiqa', 'saduq'],
    aliases: ['dabit'],
  },
  {
    slug: 'thiqa',
    section: 'narrator-criticism',
    term: 'thiqa',
    english: 'trustworthy',
    arabic: 'ثقة',
    definition:
      'A narrator judged both upright and accurate; “thiqa thabt” (ثقة ثبت) adds that he is especially firm and precise.',
    acrossTraditions:
      'Used by critics of every tradition, but a critic’s thiqa vouches for a narrator by that critic’s own standards, which differ.',
    related: ['saduq', 'la-basa-bihi', 'jarh-wa-tadil'],
    aliases: ['thiqah', 'thabt', 'thiqa thabt'],
    enumValues: ['narrator_verdict.thiqa', 'narrator_verdict.thiqa_thabt'],
  },
  {
    slug: 'saduq',
    section: 'narrator-criticism',
    term: 'saduq',
    english: 'truthful',
    arabic: 'صدوق',
    definition: 'A narrator judged honest, with accuracy a little below that of a thiqa.',
    acrossTraditions: 'Its exact rank differs between critics, as with most grading words.',
    related: ['thiqa', 'la-basa-bihi', 'hasan'],
    aliases: ['sadooq'],
    enumValues: ['narrator_verdict.saduq'],
  },
  {
    slug: 'la-basa-bihi',
    section: 'narrator-criticism',
    term: 'la baʾsa bihi',
    english: '“no harm in him”',
    arabic: 'لا بأس به',
    definition: 'A mild positive verdict: the narrator is acceptable.',
    acrossTraditions:
      'Its weight depends on the critic; by a widely cited report, Yahya ibn Maʿin used it as close to thiqa.',
    related: ['saduq', 'thiqa'],
    aliases: ['la basa bihi', 'laa baʾs'],
    enumValues: ['narrator_verdict.la_basa_bihi'],
  },
  {
    slug: 'majhul',
    section: 'narrator-criticism',
    term: 'majhul',
    english: 'unknown',
    arabic: 'مجهول',
    definition:
      'A narrator whose identity or reliability is not established in the critics’ sources; for a report, a chain that contains such a narrator.',
    inArchive: 'Appears both as a narrator verdict and as a grade in Imami gradings. It records missing knowledge, not a finding of unreliability.',
    acrossTraditions:
      'Sunni critics distinguish a narrator unknown in person from one unknown in reliability. Imami critics use majhul for a narrator described as unknown, and some separate this from a narrator not mentioned at all (muhmal).',
    related: ['mubham', 'daif', 'imami-grading', 'jarh-wa-tadil'],
    aliases: ['majhool', 'jahala', 'muhmal'],
    enumValues: ['narrator_verdict.majhul', 'grade_canonical.majhul'],
    ownerReview: 'Confirm the Imami distinction between majhul and muhmal.',
  },
  {
    slug: 'matruk',
    section: 'narrator-criticism',
    term: 'matruk',
    english: 'abandoned',
    arabic: 'متروك',
    definition: 'A narrator so seriously criticised that his reports are set aside entirely, not used even as support.',
    related: ['daif', 'kadhdhab'],
    aliases: ['matrook'],
    enumValues: ['narrator_verdict.matruk'],
  },
  {
    slug: 'kadhdhab',
    section: 'narrator-criticism',
    term: 'kadhdhab',
    english: 'liar',
    arabic: 'كذّاب',
    definition: 'The gravest verdict: a narrator accused of lying in his reports.',
    related: ['matruk', 'mawdu'],
    aliases: ['kadhab', 'kadhdhaab', 'liar'],
    enumValues: ['narrator_verdict.kadhab'],
  },
  {
    slug: 'mukhtalaf-fihi',
    section: 'narrator-criticism',
    term: 'mukhtalaf fihi',
    english: 'disputed',
    arabic: 'مختلف فيه',
    definition: 'Said of a narrator, or a grading, on which critics disagree.',
    inArchive: 'The archive keeps disagreeing verdicts side by side rather than choosing one.',
    related: ['jarh-wa-tadil', 'narrator-verdict'],
    aliases: ['mukhtalaf'],
    enumValues: ['narrator_verdict.mukhtalaf_fihi', 'grade_canonical.mukhtalaf'],
  },
  {
    slug: 'adalat-al-sahaba',
    section: 'narrator-criticism',
    term: 'ʿadalat al-sahaba',
    english: 'probity of the Companions',
    arabic: 'عدالة الصحابة',
    definition: 'The position that every Companion is upright as a narrator and need not be individually assessed.',
    inArchive:
      'Where the data records no verdict for a Companion because of this position, it stores “not applicable”, and the narrator page currently displays this label.',
    acrossTraditions:
      'A Sunni position. Imami scholarship assesses Companions individually, and Zaydi and Ibadi scholarship also hold their own views; the archive does not rule between them.',
    related: ['sahabi', 'adala', 'narrator-verdict'],
    enumValues: ['narrator_verdict.not_applicable'],
    ownerReview:
      'The narrator page (ConsensusBadge) shows “ʿadalat al-sahaba” for every “not applicable” verdict regardless of tradition. Confirm the wording and how Zaydi and Ibadi positions should be summarised.',
  },

  // ── Report grading ──────────────────────────────────────────────────────────────────────────────
  {
    slug: 'sunni-grading',
    section: 'report-grading',
    term: 'Sunni grading',
    definition:
      'Sunni critics grade a report mainly as sahih, hasan or daʿif, and a fabricated report as mawduʿ, judging the continuity of the chain, the narrators, and the absence of hidden defects.',
    inArchive:
      'Sunni grades here are statements by a named compiler, such as al-Tirmidhi’s remarks after each report, or a compiler’s stated criterion; they are never computed.',
    acrossTraditions: 'Individual critics often disagree about the same report.',
    related: ['sahih', 'hasan', 'daif', 'mawdu', 'hasan-sahih', 'compiler-statement'],
  },
  {
    slug: 'imami-grading',
    section: 'report-grading',
    term: 'Imami grading',
    definition:
      'The Imami four-part scheme grades a chain as sahih, hasan, muwaththaq or daʿif according to the school and standing of its narrators.',
    inArchive:
      'Imami grades here are rulings by named scholars, mostly al-Majlisi, with Behbudi, Mohseni and al-Najafi, each with a citation; entries such as “not included” or “silent” are not shown as grades.',
    acrossTraditions:
      'The scheme was formalised by Imami scholars in the 7th/13th century. Many Imami scholars, earlier and later, also accept a report on other evidence, so a chain grade is not the only measure.',
    related: ['sahih', 'hasan', 'muwaththaq', 'daif', 'daif-ala-al-mashhur', 'mutabar', 'majhul', 'mursal'],
  },
  {
    slug: 'sahih',
    section: 'report-grading',
    term: 'sahih',
    english: 'sound',
    arabic: 'صحيح',
    definition: 'The highest grade: a report whose chain and narrators meet the grader’s full standard.',
    acrossTraditions:
      'Sunni: an unbroken chain of upright, accurate narrators, free of irregularity and hidden defect. Imami: an unbroken chain to the Imam or Prophet of narrators who are Imami and declared upright. The same word therefore names different tests.',
    related: ['hasan', 'sahih-collection', 'kal-sahih', 'sunni-grading', 'imami-grading'],
    aliases: ['saheeh', 'authentic', 'sound'],
    enumValues: ['grade_canonical.sahih'],
  },
  {
    slug: 'hasan',
    section: 'report-grading',
    term: 'hasan',
    english: 'good',
    arabic: 'حسن',
    definition: 'An acceptable grade below sahih.',
    acrossTraditions:
      'Sunni: the narrators are upright but somewhat less accurate. Imami: the narrators are Imami and at least one is praised without being explicitly declared trustworthy.',
    related: ['sahih', 'hasan-sahih', 'hasan-gharib', 'saduq'],
    aliases: ['hassan', 'good'],
    enumValues: ['grade_canonical.hasan'],
  },
  {
    slug: 'muwaththaq',
    section: 'report-grading',
    term: 'muwaththaq',
    english: 'reliable',
    arabic: 'موثق',
    definition:
      'An Imami grade for a chain that includes a narrator from outside the Imami school who is declared trustworthy.',
    related: ['imami-grading', 'sahih', 'thiqa'],
    aliases: ['muwathaq', 'qawi'],
    enumValues: ['grade_canonical.muwaththaq'],
  },
  {
    slug: 'daif',
    section: 'report-grading',
    term: 'daʿif',
    english: 'weak',
    arabic: 'ضعيف',
    definition:
      'Weak: said of a report whose chain or narrators fall short of the grader’s standard, or of a narrator whose reliability critics doubt.',
    inArchive: 'A weak grade is a judgement on the chain as assessed by that grader. It is not a statement that the content is false.',
    acrossTraditions:
      'Sunni and Imami critics both use it, under their own standards; whether and how weak reports may be used differs between scholars.',
    related: ['daif-ala-al-mashhur', 'matruk', 'mawdu', 'sahih'],
    aliases: ['daif', 'da_if', 'dhaif', 'weak'],
    enumValues: ['grade_canonical.da_if', 'narrator_verdict.daif'],
  },
  {
    slug: 'mawdu',
    section: 'report-grading',
    term: 'mawduʿ',
    english: 'fabricated',
    arabic: 'موضوع',
    definition: 'A report judged to be invented and falsely attributed.',
    related: ['kadhdhab', 'daif'],
    aliases: ['mawdu', 'mawdoo', 'fabricated'],
    enumValues: ['grade_canonical.mawdu'],
  },
  {
    slug: 'hasan-sahih',
    section: 'report-grading',
    term: 'hasan sahih',
    arabic: 'حسن صحيح',
    definition: 'A compound grade used by al-Tirmidhi after many reports in his Jamiʿ.',
    inArchive: 'Shown as al-Tirmidhi’s own statement, in his words.',
    acrossTraditions:
      'Scholars differ on what he meant: among the explanations are that the report has two chains, one of each grade, or that critics hesitated between the two grades.',
    related: ['hasan-gharib', 'gharib', 'compiler-statement', 'sunni-grading'],
  },
  {
    slug: 'hasan-gharib',
    section: 'report-grading',
    term: 'hasan gharib',
    arabic: 'حسن غريب',
    definition:
      'A compound grade used by al-Tirmidhi for a report he considers hasan that is known through a single line of transmission; he also writes hasan sahih gharib.',
    inArchive: 'Shown as al-Tirmidhi’s own statement, in his words.',
    related: ['hasan-sahih', 'gharib', 'compiler-statement'],
  },
  {
    slug: 'gharib',
    section: 'report-grading',
    term: 'gharib',
    english: 'singular',
    arabic: 'غريب',
    definition:
      'A report transmitted by only one narrator at some point in its chain; it describes how the report travelled, not by itself its strength.',
    related: ['ahad', 'hasan-gharib', 'mutaba'],
    aliases: ['ghareeb', 'fard'],
  },
  {
    slug: 'daif-ala-al-mashhur',
    section: 'report-grading',
    term: 'daʿif ʿala al-mashhur',
    english: 'weak on the prevailing view',
    arabic: 'ضعيف على المشهور',
    definition:
      'An Imami grading phrase meaning the chain is weak according to the prevailing view of one of its narrators, signalling that other scholars judge him better.',
    inArchive: 'It appears in al-Majlisi’s gradings in the data and is kept in his words.',
    related: ['daif', 'imami-grading', 'mutabar'],
    ownerReview:
      'Confirm the reading. The grade mapping also turns “ضعيف على المشهور معتبر عند ي” into muʿtabar; check that this is the intended reading.',
  },
  {
    slug: 'mutabar',
    section: 'report-grading',
    term: 'muʿtabar',
    english: 'considered reliable',
    arabic: 'معتبر',
    definition: 'A grading word for a report that a scholar considers reliable enough to act on, whatever its formal chain grade.',
    inArchive: 'Appears in Imami gradings in the data and is kept in the grader’s words.',
    related: ['imami-grading', 'daif-ala-al-mashhur'],
    aliases: ['mutabar', 'muʿtabar', 'mu_tabar'],
    enumValues: ['grade_canonical.mu_tabar'],
    ownerReview: 'Confirm what al-Majlisi and the other graders in the data mean by معتبر.',
  },
  {
    slug: 'kal-sahih',
    section: 'report-grading',
    term: 'ka-al-sahih',
    english: 'like sahih',
    arabic: 'كالصحيح',
    definition:
      'A qualifier in Imami gradings, as in “hasan ka-al-sahih”, meaning the grader treats the report as close to sahih while giving it a lower formal grade.',
    inArchive: 'Kept in the grader’s words.',
    related: ['sahih', 'hasan', 'imami-grading'],
    aliases: ['kal-sahih', 'kalsahih'],
    ownerReview:
      'src/lib/constants/grade-taxonomy.ts maps every “… كالصحيح” to the canonical bucket sahih, which states more than the grader did. Confirm the reading and whether the mapping should change.',
  },
  {
    slug: 'thabit',
    section: 'report-grading',
    term: 'thabit',
    english: 'established',
    arabic: 'ثابت',
    definition: 'A word meaning “established”, which some critics use for an accepted report.',
    inArchive:
      'One upstream dataset puts ثابت on every one of its rows, including whole collections, so it carries no information about any single report. The archive keeps it as a collection label and never shows it as a grade.',
    related: ['collection-label'],
  },
  {
    slug: 'ibadi-report-acceptance',
    section: 'report-grading',
    term: 'Ibadi acceptance of reports',
    definition:
      'Ibadi scholars treat the Musnad of al-Rabiʿ ibn Habib, transmitted through Abu ʿUbayda and Jabir ibn Zayd, as their most authoritative collection, and weigh other reports by their chains and by agreement with the Qurʾan.',
    inArchive: 'The archive holds no per-report gradings for Ibadi works. A report with none shows “No assessment recorded”.',
    related: ['ibadi', 'jami', 'no-assessment-recorded'],
    ownerReview:
      'Describe Ibadi criteria for accepting reports correctly, in that tradition’s own terms; this entry is written cautiously and may be incomplete.',
  },
  {
    slug: 'zaydi-report-acceptance',
    section: 'report-grading',
    term: 'Zaydi acceptance of reports',
    definition:
      'Zaydi scholars give particular weight to reports transmitted through the Prophet’s family, use reports from other collections as well, and assess them by criteria set out in their own works on legal theory.',
    inArchive: 'The archive holds no per-report gradings for Zaydi works. A report with none shows “No assessment recorded”.',
    related: ['zaydi', 'musnad', 'no-assessment-recorded'],
    ownerReview:
      'Describe Zaydi criteria for accepting reports correctly, in that tradition’s own terms; this entry is written cautiously and may be incomplete.',
  },

  // ── Works and genres ────────────────────────────────────────────────────────────────────────────
  {
    slug: 'sahih-collection',
    section: 'works',
    term: 'sahih (collection)',
    arabic: 'صحيح',
    definition: 'A collection whose compiler set out to include only reports meeting his own standard of soundness, such as the Sahihs of al-Bukhari and Muslim.',
    inArchive:
      'A compiler’s criterion applies to his collection as a whole and is shown as such, not as a grade on each report.',
    acrossTraditions:
      'The title records the compiler’s aim; other traditions, and some critics within the same tradition, do not accept every report in it. The Ibadi al-Jamiʿ al-Sahih also bears the title.',
    related: ['compiler-criterion', 'six-books', 'jami'],
  },
  {
    slug: 'sunan',
    section: 'works',
    term: 'sunan',
    arabic: 'سنن',
    definition: 'A collection arranged by legal topic, such as purification and prayer, like the Sunan of Abu Dawud or al-Nasaʾi.',
    related: ['six-books', 'jami', 'musnad'],
  },
  {
    slug: 'musnad',
    section: 'works',
    term: 'musnad',
    arabic: 'مسند',
    definition:
      'A collection arranged by the Companion or authority who narrates each report, like the Musnad of Ahmad ibn Hanbal; the word is also used in some titles for a collection with chains.',
    inArchive: 'Musnad al-Imam Zayd ibn ʿAli and the Musnad of al-Rabiʿ ibn Habib use the word in their titles but are arranged by topic.',
    related: ['sunan', 'jami', 'zaydi', 'ibadi'],
    aliases: ['masanid'],
  },
  {
    slug: 'muwatta',
    section: 'works',
    term: 'muwattaʾ',
    english: 'the smoothed path',
    arabic: 'موطأ',
    definition:
      'A collection combining reports with legal opinions and local practice, best known through Malik ibn Anas’s Muwattaʾ.',
    related: ['sunan', 'six-books'],
    aliases: ['muwatta', 'muwatta malik'],
  },
  {
    slug: 'jami',
    section: 'works',
    term: 'jamiʿ',
    english: 'comprehensive collection',
    arabic: 'جامع',
    definition: 'A collection covering every subject, from belief and law to manners and history, such as the Jamiʿ of al-Tirmidhi.',
    related: ['sunan', 'sahih-collection', 'ibadi'],
    aliases: ['jami', 'jamiʿ'],
  },
  {
    slug: 'amali',
    section: 'works',
    term: 'amali',
    english: 'dictations',
    arabic: 'أمالي',
    definition: 'A work recording reports a scholar dictated to students in sessions, often arranged by session rather than topic.',
    inArchive:
      'Several works share the title al-Amali (for example those of al-Saduq, al-Mufid and al-Tusi), so the archive identifies the work by its compiler, not by the title.',
    acrossTraditions: 'The genre is found in Imami, Zaydi and Sunni literature.',
    related: ['source-work', 'zaydi', 'imami'],
    aliases: ['amaali', 'al-amali'],
  },
  {
    slug: 'six-books',
    section: 'works',
    term: 'al-kutub al-sitta',
    english: 'the Six Books',
    arabic: 'الكتب الستة',
    definition:
      'The six Sunni collections most widely relied on: the Sahihs of al-Bukhari and Muslim, and the Sunan of Abu Dawud, al-Tirmidhi, al-Nasaʾi and Ibn Maja.',
    acrossTraditions: 'Some Sunni scholars list Malik’s Muwattaʾ or al-Darimi’s Sunan in place of Ibn Maja.',
    related: ['sunni', 'sahih-collection', 'sunan', 'four-books'],
    aliases: ['six books', 'kutub sitta'],
  },
  {
    slug: 'four-books',
    section: 'works',
    term: 'al-kutub al-arbaʿa',
    english: 'the Four Books',
    arabic: 'الكتب الأربعة',
    definition:
      'The four principal Imami collections: al-Kafi of al-Kulayni, Man la yahduruhu al-faqih of al-Saduq, and Tahdhib al-ahkam and al-Istibsar of al-Tusi.',
    acrossTraditions: 'Imami scholars hold different views on whether every report in them is reliable.',
    related: ['imami', 'imami-grading', 'six-books'],
    aliases: ['four books', 'kutub arbaa'],
  },
  {
    slug: 'rijal',
    section: 'works',
    term: 'rijal',
    english: 'narrator studies',
    arabic: 'رجال',
    definition:
      'The study of narrators’ lives and reliability (ʿilm al-rijal), and the books that record it, giving each narrator’s name, teachers, students, dates and critics’ verdicts.',
    inArchive:
      'Narrator data comes partly from a narrator lexicon (the Muslim Scholars Database). Its dates and places are shown on narrator pages labelled “narrator lexicon, not yet cited”; a death year that Ibn Hajar’s Taqrib contradicts is held back until reviewed, and its prose biographies stay hidden.',
    acrossTraditions:
      'Each tradition has its own rijal works, such as those of al-Najashi and al-Tusi for Imami narrators and those of Ibn Abi Hatim and Ibn Hajar for Sunni narrators.',
    related: ['jarh-wa-tadil', 'rawi', 'narrator-verdict'],
    aliases: ['ilm al-rijal', 'rijal works', 'biographical dictionary'],
    enumValues: ['narrator_authority.imami_rijal'],
  },
  {
    slug: 'sharh',
    section: 'works',
    term: 'sharh',
    english: 'commentary',
    arabic: 'شرح',
    definition: 'A commentary that explains a collection report by report, covering language, chains, rulings and disputes.',
    inArchive: 'Commentary shown in the archive is attributed to its author and source.',
    related: ['sahih-collection', 'citation'],
    aliases: ['shuruh', 'commentary'],
  },

  // ── Comparative study and history ───────────────────────────────────────────────────────────────
  {
    slug: 'israiliyyat',
    section: 'comparative',
    term: 'Israʾiliyyat',
    arabic: 'الإسرائيليات',
    definition:
      'Reports and stories that entered Muslim literature from Jewish and Christian sources, especially about earlier prophets, creation and the end of time.',
    inArchive:
      'The comparative pages classify such material as muwafiq, mukhalif or maskut ʿanhu; “Not classified” means no classification has been recorded.',
    acrossTraditions:
      'The three-part classification is set out by Sunni exegetes such as Ibn Kathir; scholars of every tradition have debated how far such material may be used.',
    related: ['muwafiq', 'mukhalif', 'maskut-anhu', 'parallel'],
    aliases: ['israiliyat', 'israʾiliyyat'],
    enumValues: ['isra_iliyyat_status.NONE'],
    ownerReview: 'Confirm the attribution of the three-part classification and whether a tradition-specific note is needed for Imami, Zaydi or Ibadi treatments.',
  },
  {
    slug: 'muwafiq',
    section: 'comparative',
    term: 'muwafiq',
    english: 'consistent',
    arabic: 'موافق',
    definition: 'Earlier-scripture material whose content agrees with what Islamic sources affirm.',
    related: ['israiliyyat', 'mukhalif', 'maskut-anhu'],
    enumValues: ['isra_iliyyat_status.MUWAFIQ'],
  },
  {
    slug: 'mukhalif',
    section: 'comparative',
    term: 'mukhalif',
    english: 'contrary',
    arabic: 'مخالف',
    definition: 'Earlier-scripture material whose content contradicts what Islamic sources affirm.',
    related: ['israiliyyat', 'muwafiq', 'maskut-anhu'],
    enumValues: ['isra_iliyyat_status.MUKHALIF'],
  },
  {
    slug: 'maskut-anhu',
    section: 'comparative',
    term: 'maskut ʿanhu',
    english: 'left unaddressed',
    arabic: 'مسكوت عنه',
    definition: 'Earlier-scripture material that Islamic sources neither confirm nor deny, so it is neither affirmed nor rejected.',
    related: ['israiliyyat', 'muwafiq', 'mukhalif'],
    aliases: ['maskut anhu'],
    enumValues: ['isra_iliyyat_status.MASKUT_ANHU'],
  },
  {
    slug: 'parallel',
    section: 'comparative',
    term: 'Parallel',
    definition: 'A recorded resemblance between a hadith and a passage in another religious tradition’s literature.',
    inArchive:
      'Each parallel has a type: condemnation (the hadith rejects the other text), cultural crossover (shared surroundings), shared source, direct borrowing, apologetic (answering the other tradition), or disputed. A recorded parallel is a reading for discussion, not a finding about origin.',
    related: ['israiliyyat', 'confidence', 'machine-proposed'],
    aliases: ['cross-cultural parallel', 'parallels'],
    enumValues: [
      'parallel_type.CONDEMNATION',
      'parallel_type.CULTURAL_BLEED',
      'parallel_type.SHARED_SOURCE',
      'parallel_type.DIRECT_BORROWING',
      'parallel_type.APOLOGETIC',
      'parallel_type.DISPUTED',
    ],
    ownerReview: 'The one-line glosses of the six parallel types are inferred from their labels; confirm them.',
  },
  {
    slug: 'confidence',
    section: 'comparative',
    term: 'Confidence',
    definition: 'How strongly the person who recorded a parallel judges the resemblance: high, medium or low.',
    inArchive: 'It describes the recorded comparison only; it is not a grade of the hadith.',
    related: ['parallel'],
    enumValues: ['confidence_level.HIGH', 'confidence_level.MEDIUM', 'confidence_level.LOW'],
  },
  {
    slug: 'madhhab',
    section: 'comparative',
    term: 'madhhab',
    english: 'school',
    arabic: 'مذهب',
    definition: 'A school of thought, either of law (such as the Hanafi or Jaʿfari schools) or of theology.',
    inArchive: 'Schools are grouped as Sunni or Shiʿi legal schools and Sunni, Shiʿi or Ibadi theological schools.',
    related: ['sunni', 'imami', 'zaydi', 'ibadi'],
    aliases: ['madhahib', 'school of thought'],
    enumValues: [
      'school_category.SUNNI_THEOLOGICAL',
      'school_category.SHIA_THEOLOGICAL',
      'school_category.IBADI_THEOLOGICAL',
      'school_category.SUNNI_MADHHAB',
      'school_category.SHIA_MADHHAB',
    ],
    ownerReview:
      'The school categories have no Ibadi legal or separate Zaydi entries, and group Imami and Zaydi together as Shiʿi. Confirm whether that is acceptable.',
  },
  {
    slug: 'rashidun',
    section: 'comparative',
    term: 'Rashidun',
    english: 'the first four caliphs',
    arabic: 'الراشدون',
    definition: 'The period of the first four caliphs after the Prophet, Abu Bakr, ʿUmar, ʿUthman and ʿAli (11–40 AH).',
    inArchive: 'Used as a period label on historical events.',
    acrossTraditions:
      'The name, “rightly guided”, is Sunni usage; Imami, Zaydi and Ibadi historians assess these caliphates differently, and the archive uses the label only to name the period.',
    related: ['umayyad', 'hijri'],
    aliases: ['rashidun caliphate', 'rightly guided'],
    enumValues: ['event_category.RASHIDUN'],
    ownerReview: 'The period label carries a Sunni name. Confirm the wording, or choose a neutral label such as “early caliphate”.',
  },
  {
    slug: 'umayyad',
    section: 'comparative',
    term: 'Umayyad',
    arabic: 'الأمويون',
    definition: 'The dynasty that ruled the caliphate from Damascus from 41 to 132 AH (661–750 CE).',
    inArchive: 'Used as a period label on historical events.',
    related: ['rashidun', 'abbasid', 'hijri'],
    aliases: ['umayyads', 'banu umayya'],
    enumValues: ['event_category.UMAYYAD'],
  },
  {
    slug: 'abbasid',
    section: 'comparative',
    term: 'Abbasid',
    arabic: 'العباسيون',
    definition: 'The dynasty that ruled the caliphate, mostly from Baghdad, from 132 AH (750 CE), the period in which the major hadith collections were compiled.',
    inArchive: 'Used as a period label on historical events.',
    related: ['umayyad', 'hijri'],
    aliases: ['abbasids'],
    enumValues: ['event_category.ABBASID'],
  },
  {
    slug: 'hijri',
    section: 'comparative',
    term: 'hijri',
    english: 'AH',
    arabic: 'هجري',
    definition: 'The Islamic lunar calendar, counted from the Prophet’s emigration to Medina in 622 CE; dates in it are marked AH.',
    inArchive: 'Narrator life dates are hijri years, often uncertain, so they may be shown as ranges.',
    related: ['tabaqa'],
    aliases: ['AH', 'hijra'],
    enumValues: ['calendar.hijri'],
  },

  {
    slug: 'era',
    section: 'comparative',
    term: 'Era',
    definition: 'A named stretch of years, such as a caliphate or the lifetimes of the Imams, used to place a narrator’s life in its time.',
    inArchive:
      'Eras have neutral descriptive names; a tradition’s own name for a period is listed beside it with who uses it. A disputed start or end is kept as a range of years. Eras loaded from the seed are unverified until a curator cites them.',
    acrossTraditions:
      'Traditions divide and name the past differently: Sunni writers speak of the rightly guided caliphs, Imami writers of the presence and the occultation of the Imams, Zaydi and Ibadi writers of their own imamates. The archive shows each tradition’s periods in its own reckoning and makes none the default.',
    related: ['hijri', 'ghayba', 'chronological-gap'],
    aliases: ['epoch', 'period', 'ʿasr'],
  },
  {
    slug: 'ghayba',
    section: 'comparative',
    term: 'ghayba',
    english: 'occultation',
    arabic: 'غيبة',
    definition: 'In Imami belief, the hiddenness of the twelfth Imam, divided into a Lesser Occultation (260–329 AH) with four successive deputies and a Greater Occultation from 329 AH.',
    inArchive: 'Shown as eras in Imami reckoning.',
    related: ['era', 'imami'],
    aliases: ['occultation', 'ghaybah', 'lesser occultation', 'greater occultation'],
  },

  // ── Archive terms ───────────────────────────────────────────────────────────────────────────────
  {
    slug: 'chronological-gap',
    section: 'archive',
    term: 'Chronological note',
    definition: 'A note that two consecutive narrators in a chain, as their dates or generations are recorded, do not seem to have overlapped.',
    inArchive:
      'Shown when one narrator’s earliest recorded birth is after the other’s latest recorded death, or when their recorded generations are more than one step apart. Each note names where each date comes from. It is information about the records, which may themselves be wrong or may name the wrong person, and never a ruling on the chain.',
    related: ['tabaqa', 'era', 'basis', 'munqati'],
    aliases: ['gap', 'chronological gap', 'lifespans do not overlap'],
  },
  {
    slug: 'unverified-seed',
    section: 'archive',
    term: 'Seed, unverified',
    definition: 'A starting record (an event, place or era) entered before any curator review, with no citation yet.',
    inArchive:
      'Seed records are labelled “seed, unverified” and are never public. Once a curator edits or reviews one, later reloads of the seed leave it alone.',
    related: ['unreviewed', 'citation', 'era'],
    aliases: ['seed', 'seed data'],
  },
  {
    slug: 'source-work',
    section: 'archive',
    term: 'Source work',
    definition: 'The book a report is taken from, identified by its compiler and title, such as al-Kulayni’s al-Kafi.',
    inArchive:
      'Where one title names several works (al-Amali, Kitab al-Ghayba), the archive keeps them apart by compiler and never guesses which one a bare title means.',
    related: ['edition', 'citation', 'amali'],
    aliases: ['work', 'collection', 'source'],
  },
  {
    slug: 'edition',
    section: 'archive',
    term: 'Edition',
    definition: 'A particular printing or digital text of a source work, whose volume and page numbers a citation refers to.',
    related: ['source-work', 'citation'],
  },
  {
    slug: 'citation',
    section: 'archive',
    term: 'Citation',
    definition: 'A pointer to the exact place, by work, edition, volume and page, that supports a claim shown in the archive.',
    inArchive: 'Verdicts, biographies, dates and identity decisions without a citation are not published.',
    related: ['edition', 'source-work', 'published'],
  },
  {
    slug: 'locator-bound',
    section: 'archive',
    term: 'Traced to source page',
    definition: 'Said of an Arabic text that is tied to a specific record and page or address in its source.',
    inArchive: 'It shows the text can be checked against its source; it is not a review of the text.',
    related: ['citation', 'source-work'],
    aliases: ['locator bound', 'present_locator_bound'],
    enumValues: ['source_text_status.present_locator_bound'],
  },
  {
    slug: 'mention',
    section: 'archive',
    term: 'Mention',
    definition: 'One name exactly as written at one position in one chain.',
    inArchive:
      'Every mention is kept as written. A mention may later be linked to a person, recorded as a relation, a group or an unnamed narrator, or marked as not a narrator at all when the text-reading picked up a word that is not a name.',
    related: ['isnad', 'basis', 'identity-decision', 'not-yet-identified'],
    aliases: ['surface'],
    enumValues: [
      'link_kind.person',
      'link_kind.not_a_narrator',
      'surface_decision_kind.not_a_narrator',
      'decision_scope.mention',
    ],
  },
  {
    slug: 'basis',
    section: 'archive',
    term: 'Basis',
    definition: 'The reason the archive gives for connecting a name in a chain to a particular narrator.',
    inArchive:
      'The labels are: verified by a reviewer; machine-reviewed (matches the source’s index and the text); source index; matched by name; matched by kunya only; and not yet identified. When candidates disagree, all of them are kept. A kunya-only match is shown as a note beside other candidates and never counts as a disagreement.',
    related: [
      'confirmed-by-source-and-text',
      'identity-decision',
      'source-index',
      'matched-by-name',
      'matched-by-kunya-only',
      'not-yet-identified',
    ],
  },
  {
    slug: 'confirmed-by-source-and-text',
    section: 'archive',
    term: 'Machine-reviewed',
    english: 'matches the source’s index and the text',
    definition:
      'A machine check found that the source’s own narrator index names this person at this position and that the name written in the Arabic agrees with it.',
    inArchive:
      'The archive’s top automatic tier, shown as “machine-reviewed”, never as verified: a sample found about one in twenty of these wrong where two people share a name. It rests on one of: the six-books source index, hadith-kg’s index, or Thaqalayn’s annotation carried by the Riwayat corpus, each confirmed by the Arabic; two independent sources agreeing; or an Imam’s conventional kunya in an Imami chain. Riwayat’s own automatic links never count. It stands only when no other source names someone else (a kunya-only match does not count against it). Teacher-to-student links built from it are machine-reviewed too. Only a reviewer’s decision is called verified.',
    related: ['basis', 'source-index', 'two-sources-agree', 'imam-kunya', 'identity-decision'],
    aliases: ['confirmed by source and text', 'machine review', 'AI review'],
    enumValues: [
      'mention_candidate_basis.source_index_confirmed_by_text',
      'mention_candidate_basis.source_hadith_kg_confirmed_by_text',
      'mention_candidate_basis.source_riwayat_confirmed_by_text',
    ],
  },
  {
    slug: 'two-sources-agree',
    section: 'archive',
    term: 'Two sources agree',
    definition:
      'Two independent compilations name the same person at the same place in the chain: the six-books source index and hadith-kg.',
    inArchive:
      'Counts toward the machine-reviewed tier under its own label (owner, 2026-11-21). The two records are taken as one person only through a machine-proposed link between them, which is shown as a candidate. The Riwayat corpus’s ids for Sunni chains are hadith-kg’s own, so Riwayat agreeing with hadith-kg is not a second source.',
    related: ['confirmed-by-source-and-text', 'external-source-record'],
    aliases: ['independent agreement'],
  },
  {
    slug: 'imam-kunya',
    section: 'archive',
    term: 'Imam’s conventional kunya',
    english: 'e.g. Abu ʿAbd Allah (ʿa) for al-Sadiq',
    definition:
      'In Imami chains the Imams are often named by kunya alone, followed by the honorific: Abu ʿAbd Allah (ʿa) is Jaʿfar al-Sadiq, Abu Ibrahim (ʿa) is Musa al-Kazim.',
    inArchive:
      'In an Imami chain, a kunya with the honorific identifies the Imam and counts toward the machine-reviewed tier (owner, 2026-11-21). A kunya several Imams share (Abu Jaʿfar, Abu al-Hasan, Abu Muhammad) is decided only when a word after it names one Imam (al-Rida, al-Thani); otherwise every Imam who shares it is shown as an undecided candidate. The rule is a reviewable file, never applied outside Imami chains.',
    related: ['kunya', 'matched-by-kunya-only', 'confirmed-by-source-and-text'],
    aliases: ['Abu Abd Allah', 'Abu Jafar', 'Abu al-Hasan', 'kunya of the Imam'],
    enumValues: [
      'mention_candidate_basis.imam_kunya_convention',
      'mention_candidate_basis.imam_kunya_candidate',
      'narrator_authority.imam_register',
    ],
  },
  {
    slug: 'opening-isnad',
    section: 'archive',
    term: 'Named in the opening isnad',
    english: 'e.g. «عن أبيه عن جده» in Musnad Zayd',
    definition:
      'A work often writes its full chain once, in its first report, and later writes only «from his father, from his grandfather». The first report says who they are.',
    inArchive:
      'In Musnad Zayd only, a chain of exactly the shape «Zayd b. ʿAli, from his father, from his grandfather, from ʿAli» is read through the work’s own report No. 1, which names ʿAli b. al-Husayn and al-Husayn b. ʿAli. The words stay as written; the identity names that report as its basis and counts toward the machine-reviewed tier. Any other shape gets nothing. The rule is a reviewable file.',
    related: ['imam-kunya', 'confirmed-by-source-and-text'],
    aliases: ['abihi', 'jaddihi', 'his father, his grandfather'],
    enumValues: ['mention_candidate_basis.named_in_opening_isnad'],
  },
  {
    slug: 'edition-identification',
    section: 'archive',
    term: 'Named by a printed edition',
    english: 'e.g. «عمر، هو ابن عبد الواحد الدمشقي»',
    definition:
      'An editor of a printed edition sometimes says in a note who a short name in the chain is. The note is cited with its book, volume and page.',
    inArchive:
      'Five Sunni chain positions carry such an identification, found by the chain audit and cited to the edition; it counts toward the machine-reviewed tier and stands over the source index it corrects. It is never called verified: a reviewer has not confirmed it. Other proposals of the audit stay as notes for review.',
    related: ['source-index', 'confirmed-by-source-and-text'],
    aliases: ['editor’s note', 'tahqiq'],
    enumValues: ['mention_candidate_basis.edition_identification'],
  },
  {
    slug: 'external-source-record',
    section: 'archive',
    term: 'External source record',
    definition:
      'A narrator as another open dataset describes it, under that dataset’s own id: hadith-kg (narrator ids for the Sunni and some Ibadi and Zaydi chains) or the Riwayat corpus (Sunni and Shiʿi chains).',
    inArchive:
      'Such a record has its own narrator page, credited to its dataset, listing what the dataset records (never its grading words) and every chain it is named in. Its claims at a chain position are shown with their source: an id confirmed by the Arabic, or only aligned. A record is never merged with a lexicon entry automatically; a proposed link is shown as a candidate.',
    related: ['source-index', 'label-id', 'riwayat-automatic-link', 'two-sources-agree'],
    aliases: ['hadith-kg', 'Riwayat', 'external narrator'],
    enumValues: [
      'narrator_authority.hadith_kg',
      'narrator_authority.riwayat',
      'mention_candidate_basis.source_hadith_kg',
      'mention_candidate_basis.source_riwayat',
    ],
  },
  {
    slug: 'riwayat-automatic-link',
    section: 'archive',
    term: 'Riwayat automatic link',
    definition:
      'An identification the Riwayat corpus made with its own matching software, rather than taking it from Thaqalayn’s or hadith-kg’s annotation.',
    inArchive:
      'Shown, labelled as such, and never counted toward the machine-reviewed tier: a sample read one in eight wrong, against none of 52 taken from Thaqalayn’s annotation.',
    related: ['external-source-record', 'confirmed-by-source-and-text'],
  },
  {
    slug: 'label-id',
    section: 'archive',
    term: 'Label id',
    definition:
      'A source id that names a name as it is written in chains rather than an established person: a name several men share, one word, a kunya alone, or a group.',
    inArchive:
      'Its narrator page says so plainly, and its claims never carry the machine-reviewed tier, because matching the text cannot tell which man a shared label means.',
    related: ['external-source-record', 'mushtarak', 'single-name-mention'],
    aliases: ['label-like', 'shared label'],
  },
  {
    slug: 'latin-name',
    section: 'archive',
    term: 'Name in Latin letters',
    definition:
      'Every name in a chain is shown with a Latin form beside the Arabic, so a reader without Arabic can follow the chain. It renders the name as written; it does not say who the person is.',
    inArchive:
      'Taken, in order, from the source’s own English for that name (Thaqalayn’s English chains), the English name of the record the name is identified with, a transliteration of the vowelled Arabic, or a transliteration assembled only from common name parts whose reading is fixed. Where none applies the name is shown in Arabic alone rather than guessed. Each form shows how it was obtained and its source.',
    related: ['mention', 'not-yet-identified', 'external-source-record'],
    aliases: ['transliteration', 'Latin name', 'English name'],
    enumValues: [
      'name_latin_basis.provider_english',
      'name_latin_basis.identity_name',
      'name_latin_basis.transliteration_vocalized',
      'name_latin_basis.transliteration_table',
    ],
  },
  {
    slug: 'source-index',
    section: 'archive',
    term: 'Source index',
    definition: 'An identification taken from the source’s own list of narrator IDs for a report, without confirmation from the Arabic text.',
    inArchive: 'A source index is the source’s claim, not the archive’s; it is shown as such and is neither machine-reviewed nor verified.',
    related: ['basis', 'confirmed-by-source-and-text', 'candidate'],
    enumValues: ['mention_candidate_basis.source_index', 'mention_resolution.source_index', 'resolution_basis.source_index'],
  },
  {
    slug: 'matched-by-name',
    section: 'archive',
    term: 'Matched by name',
    definition:
      'The name as written matches exactly one entry in the narrator lexicon, either letter for letter or after fixed spelling rules.',
    inArchive: 'The match says the spelling agrees; it does not say a scholar has confirmed the person.',
    related: ['basis', 'matched-by-kunya-only', 'mushtarak'],
    enumValues: [
      'mention_candidate_basis.name_exact',
      'mention_candidate_basis.name_spelling_fold',
      'mention_resolution.exact_registry',
      'resolution_basis.mention_exact',
      'resolution_basis.report_atomic',
    ],
  },
  {
    slug: 'matched-by-kunya-only',
    section: 'archive',
    term: 'Matched by kunya only',
    definition: 'The only match is on a kunya, which many narrators share, so the identification is uncertain.',
    inArchive:
      'Shown as a labelled note beside any other match, never as a disagreement, and ignored when deciding which identity stands and in every analysis, including the teacher-to-student network.',
    related: ['kunya', 'single-name-mention', 'basis'],
    enumValues: ['mention_candidate_basis.name_kunya_only'],
    ownerReview:
      'The runbook records this treatment of kunya-only matches as a reading of your answer that is still to be confirmed.',
  },
  {
    slug: 'not-yet-identified',
    section: 'archive',
    term: 'Not yet identified',
    definition: 'No identification of this name meets the archive’s rules, so it is shown as written, without a link.',
    inArchive:
      'Not identified is not the same as unknown to scholarship. A curator may also record that the evidence cannot decide between candidates.',
    related: ['mention', 'basis', 'single-name-mention', 'review-unit'],
    aliases: ['unidentified', 'unresolved'],
    enumValues: [
      'mention_resolution.unresolved',
      'mention_resolution.undecidable',
      'surface_decision_kind.undecidable',
    ],
  },
  {
    slug: 'identity-decision',
    section: 'archive',
    term: 'Identity decision',
    english: 'verified by a reviewer',
    definition: 'A curator’s recorded judgement of who a name in a chain refers to, in a given context, with the reviewer named.',
    inArchive:
      'A decision applies to every mention of the same name with the same teacher (and, where needed, the same student) in the same work. Decisions about kunya-only, epithet-only or cross-tradition names need a citation.',
    related: ['review-unit', 'basis', 'curator', 'mushtarak'],
    aliases: ['curator decision', 'reviewer decision', 'verified by a reviewer'],
    enumValues: [
      'mention_candidate_basis.reviewer_decision',
      'mention_resolution.human_verified',
      'resolution_basis.human_decision',
      'surface_decision_kind.same_as',
    ],
  },
  {
    slug: 'derived-relation',
    section: 'archive',
    term: 'Derived relation',
    definition: 'A name given only by relation to the previous narrator, such as “his father” (abihi) or “his grandfather” (jaddihi).',
    inArchive: 'It can be identified only once the narrator it depends on is identified.',
    related: ['mention', 'identity-decision', 'nasab'],
    aliases: ['abihi', 'jaddihi'],
    enumValues: [
      'link_kind.derived_relation',
      'mention_resolution.derived_relation_verified',
      'surface_decision_kind.derived_relation',
    ],
  },
  {
    slug: 'collective-mention',
    section: 'archive',
    term: 'Collective mention',
    definition: 'A link that names a group rather than a person, such as “a number of our companions” (ʿidda min ashabina).',
    inArchive: 'It is part of the chain but never resolves to one narrator.',
    acrossTraditions:
      'Where a compiler states who such a group means, as al-Kulayni does for some of his, that statement is a cited claim within that tradition.',
    related: ['mubham', 'mention'],
    aliases: ['idda', 'baʿd ashabina', 'collective'],
    enumValues: ['link_kind.collective', 'surface_decision_kind.collective'],
  },
  {
    slug: 'placeholder-entry',
    section: 'archive',
    term: 'Placeholder entry',
    definition: 'A narrator-lexicon entry that cannot name one person, because it is only a single word, only a kunya, has no Arabic name, or is marked as an unidentified shaykh.',
    inArchive:
      'Placeholder entries are never used as match targets; they remain for review. An external source’s record of the same kind (a kunya alone, a relation, a group, or a hadith-kg stub) is shown when the source names it, as a label that never contests another identity.',
    related: ['single-name-mention', 'matched-by-name', 'label-id'],
    enumValues: [
      'narrator_placeholder_reason.unidentified_shaykh_marker',
      'narrator_placeholder_reason.no_arabic_name',
      'narrator_placeholder_reason.bare_single_token_name',
      'narrator_placeholder_reason.kunya_only_name',
      'narrator_placeholder_reason.relational_name',
      'narrator_placeholder_reason.collective_or_anonymous_name',
      'narrator_placeholder_reason.hadith_kg_stub_narrator',
    ],
  },
  {
    slug: 'review-unit',
    section: 'archive',
    term: 'Review unit',
    definition: 'A group of mentions that one identity decision can settle together: the same name, with the same teacher (and where needed the same student), in the same work.',
    inArchive: 'Curators review units in order of how many reports one decision would complete.',
    related: ['identity-decision', 'candidate', 'mushtarak'],
    enumValues: ['decision_scope.teacher_context', 'decision_scope.teacher_and_student_context'],
  },
  {
    slug: 'candidate',
    section: 'archive',
    term: 'Candidate',
    definition: 'A machine-produced suggestion, of an identity, a translation or a grading, kept for review and never shown to readers as fact.',
    related: ['machine-proposed', 'unreviewed', 'review-unit'],
    aliases: ['candidates'],
    enumValues: ['evidence_review_state.candidate_only'],
  },
  {
    slug: 'report-correspondence',
    section: 'archive',
    term: 'Telling (corresponding report)',
    definition:
      'Another report, in this or another work or tradition, whose wording overlaps this one closely enough that it may be the same report told again.',
    inArchive:
      'Found by a machine comparison of the report texts with the chains removed (shared five-letter sequences), then shown as machine-found and unreviewed unless a reviewer confirmed it. A reader sees same wording, variant wording at 40 percent shared wording or more, and a shared passage covering 70 percent or more of the shorter text; a reviewer’s confirmation shows a pair at any score and a rejection hides it. It is evidence that two reports correspond, not a ruling that they are one hadith, and it says nothing about which telling is earlier or more authentic. Each telling keeps its own chains, tradition and work.',
    related: ['same-wording', 'variant-wording', 'shared-passage', 'correspondence-decision', 'matn', 'isnad'],
    aliases: ['telling', 'tellings', 'variant', 'parallel report', 'textual overlap', 'shawahid'],
    enumValues: [
      'report_correspondence_basis.textual_overlap',
    ],
  },
  {
    slug: 'same-wording',
    section: 'archive',
    term: 'Same wording',
    definition: 'Two report texts that are nearly identical letter for letter, once the chains are set aside.',
    inArchive: 'At least 80 percent of their letter sequences are shared.',
    related: ['report-correspondence', 'variant-wording'],
    enumValues: ['report_correspondence_class.same_wording', 'report_correspondence_reviewed_relation.same_wording'],
  },
  {
    slug: 'variant-wording',
    section: 'archive',
    term: 'Variant wording',
    definition: 'Two texts that tell what appears to be the same report with differences of wording, order or length.',
    inArchive: 'Shown to readers from 40 percent shared wording; lower scores are kept for reviewers.',
    related: ['report-correspondence', 'same-wording', 'shared-passage'],
    enumValues: [
      'report_correspondence_class.same_report_variant_wording',
      'report_correspondence_reviewed_relation.same_report_variant_wording',
    ],
  },
  {
    slug: 'shared-passage',
    section: 'archive',
    term: 'Shares a passage',
    definition: 'One text contains a passage of the other, for example a saying quoted inside a longer report.',
    inArchive: 'Shown to readers when the passage covers 70 percent or more of the shorter text.',
    related: ['report-correspondence', 'variant-wording'],
    aliases: ['partial overlap'],
    enumValues: ['report_correspondence_class.partial_overlap', 'report_correspondence_reviewed_relation.partial_overlap'],
  },
  {
    slug: 'correspondence-decision',
    section: 'archive',
    term: 'Correspondence decision',
    definition: 'A reviewer’s judgement on a machine-found pair of reports: confirmed, rejected, or uncertain.',
    inArchive:
      'A decision is tied to the exact Arabic the reviewer read; if either text changes, the pair goes back for review. Earlier decisions are kept, never deleted.',
    related: ['report-correspondence', 'curator', 'human-verified'],
    enumValues: [
      'report_correspondence_decision.confirmed',
      'report_correspondence_decision.rejected',
      'report_correspondence_decision.uncertain',
    ],
  },
  {
    slug: 'shared-formula-only',
    section: 'archive',
    term: 'Shared formula, verse or ruling',
    definition:
      'A reviewer’s reading that two texts overlap only in a common formula (such as the shahada), a Quran verse, or the same ruling attributed to a different speaker, so they are not one report.',
    inArchive: 'Recorded with a rejection or an uncertain decision, never with a confirmation.',
    related: ['correspondence-decision', 'report-correspondence'],
    enumValues: [
      'report_correspondence_reviewed_relation.shared_formula_only',
      'report_correspondence_reviewed_relation.shared_quran_quotation',
      'report_correspondence_reviewed_relation.same_ruling_different_attribution',
    ],
  },
  {
    slug: 'chain-status',
    section: 'archive',
    term: 'Chain status',
    definition: 'How much of a report’s chain the archive has identified.',
    inArchive:
      'Complete: every name has an identity (machine-reviewed or verified by a reviewer). Partial: some do. Unresolved: none are yet. No chain in source: the work gives none (for example the sermons of Nahj al-Balagha). Not extracted: the chain could not be read from the text. In every case the chain is shown as written.',
    related: ['isnad', 'mention', 'basis'],
    enumValues: [
      'chain_status.complete',
      'chain_status.partial',
      'chain_status.unresolved',
      'chain_status.absent_in_source',
      'chain_status.extraction_failed',
    ],
  },
  {
    slug: 'assessment',
    section: 'archive',
    term: 'Assessment',
    definition: 'A grade for a report, attributed to a named scholar within one tradition and kept in that scholar’s words.',
    inArchive:
      'Hadith pages list assessments by tradition. There is no single computed grade for a hadith, and different traditions’ assessments are never combined.',
    related: ['compiler-statement', 'compiler-criterion', 'no-assessment-recorded', 'sunni-grading', 'imami-grading'],
    aliases: ['grade', 'grading', 'cited ruling'],
    enumValues: ['grading_status.cited_assessments', 'assessment_kind.cited_ruling'],
  },
  {
    slug: 'compiler-statement',
    section: 'archive',
    term: 'Compiler’s statement',
    definition: 'A grade the compiler wrote into the work beside a report, such as al-Tirmidhi’s remark after it.',
    inArchive: 'Quoted from the Arabic text where it appears.',
    related: ['assessment', 'hasan-sahih', 'compiler-criterion'],
    enumValues: ['assessment_kind.compiler_statement'],
  },
  {
    slug: 'compiler-criterion',
    section: 'archive',
    term: 'Compiler’s criterion',
    definition: 'The standard a compiler set for the whole collection, such as the conditions of the two Sahihs, rather than a ruling on one report.',
    inArchive: 'Shown as the collection’s criterion, not as a grade of the individual report.',
    related: ['sahih-collection', 'assessment', 'compiler-statement'],
    enumValues: ['grading_status.compiler_criterion', 'assessment_kind.compiler_criterion'],
  },
  {
    slug: 'collection-label',
    section: 'archive',
    term: 'Collection label',
    definition: 'A label an upstream dataset applied to every row of a collection, which says nothing about any one report.',
    inArchive: 'Kept for the record and never shown as a grade.',
    related: ['thabit', 'assessment'],
    enumValues: ['assessment_kind.collection_label'],
  },
  {
    slug: 'source-grade',
    section: 'archive',
    term: 'Source grade',
    definition: 'A grade recorded in the source the report was taken from, shown as that source gives it.',
    related: ['assessment', 'source-work'],
  },
  {
    slug: 'no-assessment-recorded',
    section: 'archive',
    term: 'No assessment recorded',
    definition: 'The archive holds no grade for this report in this tradition.',
    inArchive: 'This says nothing about the report’s strength: it may never have been graded, or a grading may exist that the archive does not yet hold.',
    related: ['assessment', 'ibadi-report-acceptance', 'zaydi-report-acceptance'],
    aliases: ['ungraded', 'none recorded'],
    enumValues: ['grading_status.none_recorded', 'grade_canonical.ungraded'],
  },
  {
    slug: 'narrator-verdict',
    section: 'archive',
    term: 'Narrator verdict',
    definition: 'A summary judgement on a narrator’s reliability, such as thiqa or daʿif.',
    inArchive:
      'A verdict belongs to a critic and a tradition. For the verdicts currently shown, the critic and tradition are not yet recorded, and the narrator page says so.',
    related: ['jarh-wa-tadil', 'thiqa', 'daif', 'mukhtalaf-fihi'],
    aliases: ['reliability', 'verdict'],
    enumValues: ['narrator_assessment_kind.consensus_summary'],
  },
  {
    slug: 'dataset-version',
    section: 'archive',
    term: 'Dataset version',
    definition: 'One numbered load of the archive’s data, recorded with its inputs so any figure can be traced to the load it came from.',
    inArchive: 'A release version has passed the release checks; any other version is shown publicly only as a preview.',
    related: ['preview', 'retired'],
    aliases: ['release', 'load'],
    enumValues: ['release_class.release'],
  },
  {
    slug: 'preview',
    section: 'archive',
    term: 'Preview',
    definition: 'Data from a dataset version that has not passed the release checks, shown publicly only because the owner has recorded approval to do so.',
    inArchive:
      'While the preview notice is shown, identities, gradings and translations may be incomplete or unverified, and may change with the next load. A preview is not a reviewed release.',
    related: ['dataset-version', 'unreviewed', 'publication-status'],
    aliases: ['preview data', 'non-release'],
    enumValues: ['release_class.non_release'],
    ownerReview: 'Confirm that this wording matches the preview notice and your approval.',
  },
  {
    slug: 'rights-status',
    section: 'archive',
    term: 'Rights status',
    definition: 'Whether the archive has permission to publish a source work’s text: cleared, pending or restricted.',
    inArchive: 'Only cleared works publish text or English. A work with no recorded status counts as pending.',
    related: ['source-work', 'publication-status'],
    aliases: ['rights', 'licence'],
    enumValues: ['rights_status.cleared', 'rights_status.pending', 'rights_status.restricted'],
  },
  {
    slug: 'publication-status',
    section: 'archive',
    term: 'Publication status',
    definition: 'Where a curated item stands on its way to readers: proposed, verified, then published, or retired.',
    inArchive: 'A row is public when every claim it displays is verified; completeness is tracked, not required.',
    related: ['proposed', 'published', 'retired', 'unreviewed'],
  },
  {
    slug: 'unreviewed',
    section: 'archive',
    term: 'Unreviewed',
    definition: 'Not yet checked by a person against its source.',
    inArchive:
      'Unreviewed material, including lexicon biographies, seed historical events and English of unknown origin, is kept for curators and labelled wherever it appears.',
    related: ['machine-proposed', 'candidate', 'proposed', 'human-verified'],
    aliases: ['unverified', 'lexicon unverified', 'unknown provenance'],
    enumValues: [
      'evidence_review_state.lexicon_unverified',
      'event_verification.unverified',
      'event_verification.unverified_seed',
      'translation_state.unknown_provenance',
    ],
  },
  {
    slug: 'machine-proposed',
    section: 'archive',
    term: 'Machine-proposed',
    definition: 'Produced by software, such as a translation model or an automated comparison, and not yet reviewed by a person.',
    inArchive:
      'Always labelled. A machine translation is shown only for works whose recorded English policy allows it, as “Unreviewed machine translation” with the model that produced it, or “model not recorded”. No identity, grade, date or translation is asserted by a machine.',
    related: ['candidate', 'unreviewed', 'parallel'],
    aliases: ['machine translation', 'ai'],
    enumValues: [
      'translation_state.machine_unreviewed',
      'record_origin.ai_research',
      'english_policy.source_provided_and_machine_allowed',
    ],
  },
  {
    slug: 'proposed',
    section: 'archive',
    term: 'Proposed',
    definition: 'Entered by a curator or a tool and awaiting review before it can be published.',
    related: ['publication-status', 'published', 'unreviewed'],
    enumValues: ['curation_status.proposed'],
  },
  {
    slug: 'source-provided',
    section: 'archive',
    term: 'Source provided',
    definition: 'Supplied with the source data, such as an English translation from the provider, but not yet checked by the archive.',
    inArchive:
      'Source-provided English is shown only for works whose recorded English policy allows it, labelled “Source-provided English, not reviewed here” and credited to its source and translator.',
    related: ['source-verified', 'human-verified', 'unreviewed'],
    enumValues: [
      'translation_state.source_provided',
      'evidence_review_state.source_provided',
      'english_policy.source_provided_allowed',
      'english_policy.reviewed_only',
    ],
  },
  {
    slug: 'source-verified',
    section: 'archive',
    term: 'Source verified',
    definition: 'Checked against a published source, such as a printed translation or edition, and found to match it.',
    related: ['human-verified', 'source-provided', 'citation'],
    enumValues: ['translation_state.source_verified', 'evidence_review_state.source_verified', 'event_verification.source_verified'],
  },
  {
    slug: 'human-verified',
    section: 'archive',
    term: 'Human verified',
    definition: 'Reviewed and accepted by a named person.',
    related: ['source-verified', 'curator', 'identity-decision'],
    aliases: ['reviewed', 'verified'],
    enumValues: [
      'translation_state.human_verified',
      'evidence_review_state.human_verified',
      'event_verification.human_verified',
      'curation_status.verified',
    ],
  },
  {
    slug: 'published',
    section: 'archive',
    term: 'Published',
    definition: 'Reviewed, cited where required, and visible to readers.',
    related: ['publication-status', 'proposed', 'retired', 'citation'],
    enumValues: ['curation_status.published'],
  },
  {
    slug: 'retired',
    section: 'archive',
    term: 'Retired',
    definition: 'Withdrawn from display but kept, with who retired it and when; nothing in the archive is deleted.',
    inArchive: 'A corrected decision or record replaces the old one, which stays in the history.',
    related: ['publication-status', 'published', 'dataset-version'],
    aliases: ['retire', 'withdrawn'],
  },
  {
    slug: 'curator',
    section: 'archive',
    term: 'Curator',
    definition: 'A named, invited person who may record decisions and publish material; every change they make is logged under their name.',
    related: ['contributor', 'identity-decision', 'human-verified'],
    aliases: ['reviewer', 'editor'],
  },
  {
    slug: 'contributor',
    section: 'archive',
    term: 'Contributor',
    definition: 'A person who submits material, such as commentary, a translation or a correction, for curators to review.',
    inArchive: 'Planned: the contribution system is designed but not yet built.',
    related: ['curator', 'endorsement'],
  },
  {
    slug: 'endorsement',
    section: 'archive',
    term: 'Endorsement (ijaza)',
    arabic: 'إجازة',
    definition:
      'In the archive, a record that one contributor vouches for another’s expertise in a field, named after the ijaza, the classical licence by which a teacher authorised a student to transmit.',
    inArchive: 'Planned with the contribution system.',
    related: ['contributor', 'curator'],
    aliases: ['ijaza', 'ijazah'],
    ownerReview:
      'A classical ijaza licenses transmission; the planned endorsement vouches for expertise. Confirm you want the word ijaza used for it.',
  },
];

const ENTRIES_BY_SLUG: ReadonlyMap<string, GlossaryEntry> = new Map(GLOSSARY_ENTRIES.map((entry) => [entry.slug, entry]));

/** Lookup by slug; undefined when the slug is unknown. */
export function getGlossaryEntry(slug: string): GlossaryEntry | undefined {
  return ENTRIES_BY_SLUG.get(slug);
}

/** Path to a term's anchor on the glossary page. */
export function glossaryHref(slug: string): string {
  return `/glossary#${slug}`;
}

/** Lowercase, strip Arabic vowel marks and the ʿ/ʾ/' marks so "daif" finds "daʿif" and "ضعيف" finds "ضَعِيف". */
export function normalizeGlossaryText(text: string): string {
  return text
    .normalize('NFKD')
    .replace(/[̀-ًͯ-ٰٟـ]/g, '')
    .replace(/[ʿʾ'’‘`]/g, '')
    .toLowerCase();
}

/** True when the filter text appears in the entry's term, English, Arabic, aliases or definition. */
export function matchesGlossaryQuery(entry: GlossaryEntry, query: string): boolean {
  const needle = normalizeGlossaryText(query.trim());
  if (!needle) return true;
  const haystack = [entry.term, entry.english, entry.arabic, entry.definition, ...(entry.aliases ?? [])]
    .filter(Boolean)
    .join(' \u0000 ');
  return normalizeGlossaryText(haystack).includes(needle);
}
