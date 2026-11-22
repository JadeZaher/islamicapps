/**
 * The one typed source registry: every source the archive draws on, its short reference code, licence and the
 * wording its licence or the rights register requires. Checked against docs/rights/rights-register.md and
 * datasets/sources/*.md by src/db/queries/__tests__/browse-flows.test.ts. See src/lib/AGENTS.md §Sources.
 */

export type SourceCode = 'THQ' | 'OITI' | 'SUN' | 'NMC' | 'MSD' | 'K6I' | 'RIJ' | 'HKG' | 'RWY' | 'SWI' | 'AMR' | 'GST';

export type Supply = 'text' | 'translation' | 'gradings' | 'narrator data' | 'rijal' | 'identity claims' | 'typeface';

export interface SourceRecord {
  code: SourceCode;
  /** Stable anchor on /sources. */
  anchor: string;
  name: string;
  supplies: Supply[];
  took: string;
  licence: { name: string; url: string | null };
  /** The wording the rights register or the source card requires, placeholders as written; null when none. */
  requiredWording: string | null;
  link: string | null;
  retrieved: string;
  /** `sources.slug` values in the database whose works come from this source. */
  databaseSourceSlugs: string[];
  /** `datasets/sources/*.md` card ids this record covers. */
  sourceCards: string[];
}

export const CC_BY_4 = 'https://creativecommons.org/licenses/by/4.0/';
export const CC_BY_NC_SA_4 = 'https://creativecommons.org/licenses/by-nc-sa/4.0/';
const OFL = 'https://openfontlicense.org/';
const OPENITI_DOI = 'https://doi.org/10.5281/zenodo.17767721';

export const SOURCES: readonly SourceRecord[] = [
  {
    code: 'THQ',
    anchor: 'thq',
    name: 'Thaqalayn (Stichting Thaqalayn)',
    supplies: ['text', 'translation', 'gradings', 'identity claims'],
    took: "Arabic and English of twenty classical Imami works and Muhsini's Mu'jam, with the gradings Thaqalayn records (al-Majlisi, al-Behbudi, Muhsini, al-Najafi), through ThaqalaynAPI. Its English chains give the Latin form of Imami narrators' names, and its narrator annotation (carried by the Riwayat corpus, re-keyed to this edition) identifies Imami narrators.",
    licence: { name: 'CC BY 4.0', url: CC_BY_4 },
    requiredWording:
      'Source: Thaqalayn (Stichting Thaqalayn) — [link to the hadith on thaqalayn.com]. Arabic text of [work] by [author]. Translation: [translator], where shown. CC BY 4.0 — https://creativecommons.org/licenses/by/4.0/. Changes: text normalized and chains of narrators extracted by Shura wa Istehsan. Thaqalayn does not endorse this site.',
    link: 'https://thaqalayn.com/',
    retrieved: '2026-04-19',
    databaseSourceSlugs: ['thaqalayn-api'],
    sourceCards: ['thaqalayn-api'],
  },
  {
    code: 'OITI',
    anchor: 'oiti',
    name: 'OpenITI: a Machine-Readable Corpus of Islamicate Texts',
    supplies: ['text'],
    took: "Arabic of Musnad al-Imam Zayd, al-Jami' al-Sahih of al-Rabi' b. Habib and the Sahifat al-Imam al-Rida, release 2025.1.9.",
    licence: { name: 'CC BY-NC-SA 4.0', url: CC_BY_NC_SA_4 },
    requiredWording:
      'Arabic text: [work], OpenITI version [URI], from OpenITI: a Machine-Readable Corpus of Islamicate Texts, release 2025.1.9, https://doi.org/10.5281/zenodo.17767721, originally from [upstream library]. Licensed CC BY-NC-SA 4.0 — https://creativecommons.org/licenses/by-nc-sa/4.0/. Changes: parsed into reports, page markers moved out of the text, Unicode normalized; English is a machine translation by Shura wa Istehsan, released under the same licence.',
    link: OPENITI_DOI,
    retrieved: '2026-05-08',
    databaseSourceSlugs: ['jami-sahih-rabi-openiti', 'musnad-zayd-openiti', 'musnad-rida-openiti'],
    sourceCards: ['openiti', 'jami-sahih-rabi-openiti', 'musnad-zayd-openiti', 'musnad-rida-openiti'],
  },
  {
    code: 'SUN',
    anchor: 'sun',
    name: 'sunnah.com (via Kaggle “fahd09/hadith-dataset”)',
    supplies: ['text', 'translation'],
    took: 'Arabic and English of the six books, with their book divisions and sunnah.com numbering.',
    licence: { name: 'Permission (owner, 2026-11-21)', url: 'https://sunnah.com/about' },
    requiredWording: 'Arabic text courtesy of sunnah.com, [link to the hadith].',
    link: 'https://sunnah.com/',
    retrieved: '2018-08-22',
    databaseSourceSlugs: ['sunnah-com'],
    sourceCards: ['sunnah-com'],
  },
  {
    code: 'NMC',
    anchor: 'nmc',
    name: 'NabiMuhammad.com, Hadith Pure Canon Authentica',
    supplies: ['text'],
    took: "Arabic of Musnad Ahmad, the Muwatta', Sunan al-Darimi and the rows labelled Musnad al-Shafi'i.",
    licence: { name: 'Permission (owner, 2026-11-21)', url: null },
    requiredWording: null,
    link: 'https://nabimuhammad.com/',
    retrieved: '2026-03-29',
    databaseSourceSlugs: ['sheikahmad-pure-canon'],
    sourceCards: ['sheikahmad-pure-canon'],
  },
  {
    code: 'MSD',
    anchor: 'msd',
    name: 'Muslim Scholars Database, Arees Institute (via Kaggle “fahd09/hadith-narrators”)',
    supplies: ['narrator data', 'identity claims'],
    took: 'The narrator lexicon: names, teacher and student links, dates and places. Its names are matched against chains to suggest identities.',
    licence: { name: 'Permission (owner, 2026-11-21)', url: 'https://muslimscholars.info/' },
    requiredWording: null,
    link: 'https://muslimscholars.info/',
    retrieved: '2026-07-20',
    databaseSourceSlugs: [],
    sourceCards: ['narrator-lexicon'],
  },
  {
    code: 'K6I',
    anchor: 'k6i',
    name: 'K6 source narrator index (Kaggle “fahd09/hadith-dataset”, chain_indx)',
    supplies: ['identity claims'],
    took: "The six-books source's own narrator index per chain position, read where the Arabic corroborates it.",
    licence: { name: 'Permission (owner, 2026-11-21)', url: null },
    requiredWording: null,
    link: 'https://www.kaggle.com/datasets/fahd09/hadith-dataset',
    retrieved: '2018-08-22',
    databaseSourceSlugs: [],
    sourceCards: [],
  },
  {
    code: 'RIJ',
    anchor: 'rij',
    name: 'OpenITI rijal texts',
    supplies: ['rijal'],
    took: "al-Najashi, Rijal; al-Tusi, Rijal and al-Fihrist; al-Kashshi via al-Tusi, Ikhtiyar Ma'rifat al-Rijal; Ibn Hajar, Taqrib al-Tahdhib; al-Mizzi, Tahdhib al-Kamal. Used to check narrator biographies.",
    licence: { name: 'CC BY-NC-SA 4.0', url: CC_BY_NC_SA_4 },
    requiredWording:
      'Narrator information derived from [work], OpenITI version [URI], release 2025.1.9, https://doi.org/10.5281/zenodo.17767721. CC BY-NC-SA 4.0. This derived material is offered under the same licence: non-commercial use only, with attribution, and adaptations must be shared alike.',
    link: OPENITI_DOI,
    retrieved: '2026-11-21',
    databaseSourceSlugs: [],
    sourceCards: [],
  },
  {
    code: 'HKG',
    anchor: 'hkg',
    name: 'hadith-kg (“al-Jami — Hadith Knowledge Graph”) by emadjumaah',
    supplies: ['identity claims'],
    took: 'Narrator identities per chain position and its narrator records (names, generation, dates, places), matched to this archive’s reports and shown as identity claims with their own narrator pages. Its grading words are not shown.',
    licence: { name: 'CC BY 4.0', url: CC_BY_4 },
    requiredWording:
      'hadith-kg — "الجامع — Hadith Knowledge Graph" by emadjumaah, https://huggingface.co/datasets/emadjumaah/hadith-kg (revision 8ae7e3d5), licensed under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). Compiled by its author from hadithdb (2017). Measurements and candidate rows derived from it by this project are unreviewed; the database itself was not changed.',
    link: 'https://huggingface.co/datasets/emadjumaah/hadith-kg',
    retrieved: '2026-11-21',
    databaseSourceSlugs: [],
    sourceCards: [],
  },
  {
    code: 'RWY',
    anchor: 'rwy',
    name: 'Riwāyāt: A Corpus of Sunni and Shīʿī Hadith Transmission (Abdullah Ansar)',
    supplies: ['identity claims'],
    took: 'Narrator identifications per chain position (its own, or carried from Thaqalayn’s and hadith-kg’s annotation), its narrator records and their crosswalk ids, shown as identity claims with their own narrator pages; its automatic links are shown and never counted.',
    licence: { name: 'CC0 1.0 (embedded texts under their own licences)', url: 'https://creativecommons.org/publicdomain/zero/1.0/' },
    requiredWording:
      'Abdullah Ansar, "Riwāyāt: A Corpus of Sunni and Shīʿī Hadith Transmission", v1, Zenodo, 2026, https://doi.org/10.5281/zenodo.23630501 (CC0 1.0). Hadith texts and annotations derive from third-party datasets under their own licences, including hadith-kg by emadjumaah (CC BY 4.0, https://huggingface.co/datasets/emadjumaah/hadith-kg) and ThaqalaynData for the Shi\'i texts.',
    link: 'https://doi.org/10.5281/zenodo.23630501',
    retrieved: '2026-11-21',
    databaseSourceSlugs: [],
    sourceCards: [],
  },
  {
    code: 'SWI',
    anchor: 'swi',
    name: 'Shura wa Istehsan (this archive)',
    supplies: ['translation', 'identity claims'],
    took: 'Our own layer: chain extraction, machine translations (labelled unreviewed), reviewer decisions, the transliteration of narrator names, the register of the Imams’ conventional kunyas, and the historical seed data, which is unverified until cited.',
    licence: { name: 'Same licence as the source material it derives from', url: null },
    requiredWording: 'Machine translation by Shura wa Istehsan ([model]), not reviewed.',
    link: null,
    retrieved: 'n/a',
    databaseSourceSlugs: [],
    sourceCards: [],
  },
  {
    code: 'AMR',
    anchor: 'amr',
    name: 'Amiri typeface (Khaled Hosny)',
    supplies: ['typeface'],
    took: 'The Arabic typeface.',
    licence: { name: 'SIL Open Font License 1.1', url: OFL },
    requiredWording: null,
    link: 'https://github.com/aliftype/amiri',
    retrieved: 'n/a',
    databaseSourceSlugs: [],
    sourceCards: [],
  },
  {
    code: 'GST',
    anchor: 'gst',
    name: 'Geist typeface (Vercel)',
    supplies: ['typeface'],
    took: 'The Latin typeface.',
    licence: { name: 'SIL Open Font License 1.1', url: OFL },
    requiredWording: null,
    link: 'https://vercel.com/font',
    retrieved: 'n/a',
    databaseSourceSlugs: [],
    sourceCards: [],
  },
];

const BY_CODE = new Map(SOURCES.map((record) => [record.code, record]));

export function sourceByCode(code: SourceCode): SourceRecord {
  return BY_CODE.get(code)!;
}

/** The record for a database `sources.slug`, or null when unregistered (a test fails on any such loaded work). */
export function sourceForDatabaseSlug(slug: string): SourceRecord | null {
  return SOURCES.find((record) => record.databaseSourceSlugs.includes(slug)) ?? null;
}

/** Link to a source's record on the reference page. */
export function sourceRecordHref(code: SourceCode): string {
  return `/sources#${sourceByCode(code).anchor}`;
}

export interface WorkCredit {
  author: string;
  /** English translator or publisher as recorded (rights register); null when not recorded. */
  translator: string | null;
  openitiUri?: string;
  upstreamLibrary?: string;
  /** sunnah.com collection key, for the per-hadith link the register asks for. */
  sunnahCollection?: string;
}

const ZAYD_URI = '0122ZaydIbnCali.Musnad.Zaydiyya0000052-ara1';

/** Per-work credits from the rights register's tables, keyed by `collections.source_work_id`. */
export const WORK_CREDITS: Readonly<Record<string, WorkCredit>> = {
  'sunni:bukhari': { author: 'al-Bukhari', translator: 'Muhammad Muhsin Khan', sunnahCollection: 'bukhari' },
  'sunni:muslim': { author: 'Muslim b. al-Hajjaj', translator: 'Abdul Hamid Siddiqui', sunnahCollection: 'muslim' },
  'sunni:abudawud': { author: 'Abu Dawud', translator: 'Ahmad Hasan', sunnahCollection: 'abudawud' },
  'sunni:tirmidhi': { author: 'al-Tirmidhi', translator: 'Darussalam (English edition)', sunnahCollection: 'tirmidhi' },
  'sunni:nasai': { author: "al-Nasa'i", translator: 'Darussalam (English edition)', sunnahCollection: 'nasai' },
  'sunni:ibnmajah': { author: 'Ibn Majah', translator: 'Darussalam (English edition)', sunnahCollection: 'ibnmajah' },
  'sunni:ahmad': { author: 'Ahmad b. Hanbal', translator: null },
  'sunni:muwatta': { author: 'Malik b. Anas', translator: null },
  'sunni:darimi': { author: 'al-Darimi', translator: null },
  'sunni:shafii': { author: "al-Shafi'i (attribution unconfirmed)", translator: null },
  'ibadi:musnad-rabi': {
    author: "al-Rabi' b. Habib",
    translator: null,
    openitiUri: '0170RabicIbnHabibAzdi.JamicSahih.ShamIbadiyya0000155-ara1',
    upstreamLibrary: 'al-Maktaba al-Shamila al-Ibadiyya',
  },
  'imami:al-kafi': { author: 'al-Kulayni', translator: 'Muhammad Sarwar' },
  'imami:man-la-yahduruhu-al-faqih': { author: 'al-Saduq', translator: 'Bab Ul Qaim Publications' },
  'imami:nahj-al-balagha': { author: 'al-Sharif al-Radi', translator: 'Sayed Ali Raza' },
  'imami:al-amali-saduq': { author: 'al-Saduq', translator: 'Bilal Muhammad' },
  'imami:al-amali-mufid': { author: 'al-Mufid', translator: 'Mulla Asgharali M M Jaffer' },
  'imami:al-khisal': { author: 'al-Saduq', translator: 'Dr. Ali Peiravi' },
  'imami:kitab-al-ghayba-tusi': { author: 'al-Tusi', translator: 'Sayyid Athar Husain S. H. Rizvi' },
  'imami:kitab-al-ghayba-numani': { author: "al-Nu'mani", translator: 'Abdullah al-Shahin' },
  'imami:thawab-al-amal': { author: 'al-Saduq', translator: 'Sayed Athar Husain Rizvi & Sayed Maqsood Athar' },
  'imami:uyun-akhbar-al-rida': { author: 'al-Saduq', translator: 'Dr. Ali Peiravi' },
  'imami:maani-al-akhbar': { author: 'al-Saduq', translator: 'Basel Kadem' },
  'imami:kamil-al-ziyarat': { author: 'Ibn Qulawayh', translator: 'Sayyid Mohsen Al-Husayni Al-Milani' },
  'imami:kamal-al-din': { author: 'al-Saduq', translator: null },
  'imami:al-tawhid-saduq': { author: 'al-Saduq', translator: 'Sayed Ali Raza Rizvi' },
  'imami:mujam-al-ahadith-al-mutabara': { author: 'Muhammad Asif Muhsini', translator: 'Ammaar Muslim' },
  'imami:kitab-al-zuhd': { author: "al-Husayn b. Sa'id al-Ahwazi", translator: 'Shaykh Tahir Ridha Jaffer' },
  'imami:kitab-al-duafa': { author: "Ibn al-Ghada'iri", translator: 'Tashayyu' },
  'imami:kitab-al-mumin': { author: "al-Husayn b. Sa'id al-Ahwazi", translator: 'Muhajir b. Ali' },
  'imami:sifat-al-shia': { author: 'al-Saduq', translator: 'Badr Shahin' },
  'imami:fadail-al-shia': { author: 'al-Saduq', translator: 'Badr Shahin' },
  'imami:risalat-al-huquq': { author: "Imam Zayn al-'Abidin (attributed)", translator: 'William C. Chittick' },
  'imami:sahifat-al-imam-ali-al-rida': {
    author: 'Imam al-Rida (attributed)',
    translator: null,
    openitiUri: ZAYD_URI,
    upstreamLibrary: 'al-Maktaba al-Shamila al-Zaydiyya',
  },
  'zaydi:musnad-zayd': {
    author: "Zayd b. 'Ali",
    translator: null,
    openitiUri: ZAYD_URI,
    upstreamLibrary: 'al-Maktaba al-Shamila al-Zaydiyya',
  },
};

/** Identity-candidate basis (chain_mention_candidates.basis, or reviewer_decision) -> the source asserting it. */
export function sourceForIdentityBasis(basis: string): SourceCode {
  if (basis === 'source_index' || basis === 'source_index_confirmed_by_text') return 'K6I';
  if (basis.startsWith('name_')) return 'MSD';
  if (basis.startsWith('source_hadith_kg')) return 'HKG';
  if (basis.startsWith('source_riwayat')) return 'RWY';
  if (basis === 'named_in_opening_isnad') return 'OITI';
  return 'SWI';
}

/**
 * Every source behind one identity claim (reconciled/README.md §e): a Riwayat id taken from an upstream annotation is
 * also credited to that annotation's author, Thaqalayn in Imami chains and hadith-kg elsewhere.
 */
export function sourcesForIdentityClaim(basis: string, origin: string | null | undefined, tradition: string | null): SourceCode[] {
  const primary = sourceForIdentityBasis(basis);
  if (primary === 'RWY' && origin === 'upstream_annotation') return ['RWY', tradition === 'Imami' ? 'THQ' : 'HKG'];
  return [primary];
}

/** The source of a chain name's Latin form: the provider's English, the identified record's register, or this archive. */
export function sourceForLatinName(basis: string, narratorId: string | null | undefined): SourceCode {
  if (basis === 'provider_english') return 'THQ';
  if (basis === 'identity_name') return narratorId?.startsWith('narrator:rawi:') ? 'MSD' : 'SWI';
  return 'SWI';
}

/** The source of a narrator record by its authority (narrators.authority). */
export function sourceForNarratorAuthority(authority: string): SourceCode {
  if (authority === 'hadith_kg') return 'HKG';
  if (authority === 'riwayat') return 'RWY';
  if (authority === 'imam_register' || authority === 'work_register') return 'SWI';
  return 'MSD';
}

/** Hadith gradings shipped with a work come from the work's text source (Thaqalayn records the Imami graders). */
export function sourceForGrading(textSource: SourceCode): SourceCode {
  return textSource;
}

/** The text source of a report from its stable ID namespace alone (k6, thaqalayn, openiti, pure-canon); null otherwise. */
export function sourceCodeForHadithId(hadithId: string): SourceCode | null {
  const namespace = hadithId.split(':')[1];
  if (namespace === 'k6') return 'SUN';
  if (namespace === 'thaqalayn') return 'THQ';
  if (namespace === 'openiti') return 'OITI';
  if (namespace === 'pure-canon') return 'NMC';
  return null;
}
