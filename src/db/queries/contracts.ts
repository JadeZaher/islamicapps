/** Read contracts the query layer returns (section 9.4). Types only, safe to import from client components. */
import type { SourceReference } from '@/lib/sources/report-credit';
import type { HadithTraditionCode, Paginated } from './sql-helpers';

export type { HadithTraditionCode, Paginated };

/** One grade attributed to a grader within a tradition. `collection_label` rows never appear. */
export interface HadithAssessment {
  tradition: HadithTraditionCode;
  kind: 'cited_ruling' | 'compiler_criterion' | 'compiler_statement';
  grade_raw: string;
  grade_canonical: string | null;
  grader: string | null;
  citation_raw: string | null;
}

/** One group per tradition; an empty `assessments` list means "no assessment recorded". */
export interface HadithAssessmentGroup {
  tradition: HadithTraditionCode;
  assessments: HadithAssessment[];
}

/** A hadith in a list or search result; aliases mirror the keys the UI reads (rule 3). */
export interface HadithListItem {
  id: string;
  record_id: string;
  title: string | null;
  primary_topic: string | null;
  chapter: string | null;
  chapter_no: string | null;
  category: string | null;
  volume: string | null;
  hadith_no: string | null;
  source: string;
  source_display_label: string | null;
  collection_id: string;
  tradition: HadithTraditionCode;
  text_ar: string | null;
  text_arabic: string | null;
  matn_ar: string | null;
  text_en: string | null;
  text_english: string | null;
  /** Reviewer mode only: the state of the English shown; public lists only ever show reviewed English. */
  english_state: string | null;
  source_text_status: string;
  chain_status: string;
  grading_status: string;
}

export interface HadithVariation {
  id: string;
  text_arabic: string | null;
  text_english: string | null;
  source: 'hadith_node';
}

/** How a report's English was obtained, its label and its credit (owner decision 2026-11-21). */
export interface EnglishAttribution {
  state: string;
  source: string | null;
  translator: string | null;
  model: string | null;
  /** "Source-provided English, not reviewed here" or "Unreviewed machine translation (<model> | model not recorded)". */
  label: string;
  reference: SourceReference | null;
}

/** Hadith detail; `assessments` replaces display_grade / auto_calculated_grade / transmission_type. */
export interface HadithDetail extends HadithListItem {
  sanad: string | null;
  isnad_arabic: string | null;
  chain_text_arabic: string | null;
  sanad_confidence: string | null;
  matn_en: string | null;
  narration_level: string | null;
  chain_type: string | null;
  school: string | null;
  attributed_to: string | null;
  url: string | null;
  page_ref: string | null;
  arabic_sha256: string;
  english_attribution: EnglishAttribution | null;
  variations: HadithVariation[];
  assessments: HadithAssessmentGroup[];
}

/** Where an identity candidate comes from (owner decisions 2026-11-21; src/db/AGENTS.md §Identity candidates). */
export type IdentityBasis =
  | 'reviewer_decision'
  | 'source_index_confirmed_by_text'
  | 'source_index'
  | 'name_exact'
  | 'name_spelling_fold'
  | 'name_kunya_only'
  | 'source_hadith_kg_confirmed_by_text'
  | 'source_hadith_kg'
  | 'source_riwayat_confirmed_by_text'
  | 'source_riwayat'
  | 'imam_kunya_convention'
  | 'imam_kunya_candidate';

/** Narrator record authority: the lexicon, an external dataset's own record, or the Imam register (0010). */
export type NarratorAuthority = 'rawi' | 'imami_rijal' | 'hadith_kg' | 'riwayat' | 'imam_register';

/** How a chain name's Latin form was obtained (never an identification; src/db/AGENTS.md §Latin names). */
export type NameLatinBasis = 'provider_english' | 'identity_name' | 'transliteration_vocalized' | 'transliteration_table';

/** One identity a source or matcher gives a mention; several may disagree and all are shown. */
export interface ChainMentionCandidate {
  narrator_id: string;
  name_ar: string | null;
  name_en: string | null;
  basis: IdentityBasis;
  /** External claims: the report it was read from, and who asserted the id (Riwayat's origin or `dataset_index`). */
  source_ref?: string | null;
  origin?: string | null;
  /** Can carry the machine-reviewed tier by itself (not Riwayat's automatic linker, not a label-like record). */
  tier_basis?: boolean;
  authority?: NarratorAuthority;
  /** The target record's placeholder reason: a label, never a contest. */
  placeholder?: string | null;
  /** The target is a label-like external record (the source's id names a label as written, not a person). */
  label_reason?: string | null;
  /** Comparison key across registries (lexicon link candidates); records with one key name one person. */
  person_key?: string;
}

/** `differ`: the candidates name more than one narrator. */
export type MentionIdentity = 'unidentified' | 'agreed' | 'differ';

/** A chain position, keyed by mention ID (section 9.4). Narrator fields are set only when `is_link`. */
export interface ChainNode {
  node_id: string;
  chain_id: string;
  branch: number;
  position: number;
  surface_ar: string;
  narrator_id: string | null;
  name_ar: string | null;
  name_en: string | null;
  resolution: string;
  link_kind: string;
  /** Verified link: a confirmed source index nobody contests, or a reviewer decision. */
  is_link: boolean;
  /** Published verdict in the hadith's tradition, or null. */
  verdict: string | null;
  /** Every candidate with its basis, strongest basis first; verified or not. */
  candidates: ChainMentionCandidate[];
  identity: MentionIdentity;
  /** The name as written in Latin letters and how it was obtained; null when no source or rule gives one. */
  name_latin?: string | null;
  name_latin_basis?: NameLatinBasis | null;
  name_latin_narrator_id?: string | null;
  /** What set the standing identity (e.g. `two_sources_agree`, `imam_kunya_convention`); null when none. */
  standing_basis?: string | null;
}

export interface ChainEdge {
  source: string;
  target: string;
  chain_id: string;
}

export interface ChainGraph {
  hadith_id: string;
  tradition: HadithTraditionCode | null;
  /** The source work (collection) the chain comes from; each sanad stays within its tradition and work. */
  source_work: string | null;
  chain_schema: 'v2';
  nodes: ChainNode[];
  edges: ChainEdge[];
}

/** A narrator verdict, tradition-scoped; public pages see `published` only. */
export interface NarratorVerdict {
  id: string;
  tradition: HadithTraditionCode | null;
  verdict: string;
  kind: string;
  status: string;
  critic: string | null;
  quote_ar: string | null;
  quote_en: string | null;
}

export interface NarratorListItem {
  id: string;
  name: string;
  name_english: string;
  name_arabic: string;
  tabaqah: string | null;
  geographic_region: string | null;
  verdicts: NarratorVerdict[];
}

export interface NarratorBio {
  status: string;
  is_prophet: boolean;
  tabaqah: string | null;
  name_english_clean: string | null;
  name_arabic_clean: string | null;
  kunya: string | null;
  nasab: string | null;
  nisba: string | null;
  geographic_region: string | null;
  death_year_hijri: number | null;
  death_year_gregorian: number | null;
  bio_summary: string | null;
}

/**
 * What the narrator lexicon (MSD) says: a lexicon claim, never a cited fact. Public pages show the dates and places
 * labelled "narrator lexicon, not yet cited" (owner, 2026-11-21); `held_back` names fields withheld there because a
 * rijal work disagrees (src/db/queries/AGENTS.md §Lexicon on public narrator pages). `bio` is reviewer-only.
 */
export interface NarratorLexicon {
  review_state: string;
  birth_year_hijri: number | null;
  death_year_hijri: number | null;
  birth_year_gregorian: number | null;
  death_year_gregorian: number | null;
  birth_place: string | null;
  death_place: string | null;
  geographic_region: string | null;
  bio: string | null;
  /** Where in the lexicon the row comes from, e.g. `all_rawis.csv#scholar_indx=10`. */
  source_locator: string | null;
  held_back: Array<{ field: 'death_year'; reason: string; taqrib_entry: string | null }>;
}

export interface NarratorHadithSummary {
  id: string;
  title: string | null;
  primary_topic: string | null;
  source: string;
  hadith_no: string | null;
  tradition: HadithTraditionCode;
  assessments: HadithAssessmentGroup[];
}

export interface NarratorLocation {
  id: string;
  name: string;
  name_arabic: string | null;
  relation: 'born' | 'died' | 'resided';
}

export interface NarratorDetail {
  id: string;
  name: string;
  name_english: string;
  name_arabic: string;
  /** Which registry the record belongs to: the lexicon, an external dataset, or the Imam register. */
  authority: NarratorAuthority;
  verdicts: NarratorVerdict[];
  /** Published bio on public pages; any live bio in reviewer mode. */
  bio: NarratorBio | null;
  /** Dates and places on public pages (held-back fields removed); everything in reviewer mode; null when no row. */
  lexicon: NarratorLexicon | null;
  hadiths: Paginated<NarratorHadithSummary>;
  locations: NarratorLocation[];
}

export interface NetworkPeer {
  id: string;
  name_english: string;
  name_arabic: string;
  relationship: 'teacher' | 'student';
  hadith_count: number;
  temporal_plausibility: string;
}

export interface NarratorNetwork {
  teachers: NetworkPeer[];
  students: NetworkPeer[];
  teacher_total: number;
  student_total: number;
  attribution_disclaimer: string | null;
  network_refreshed_at: string | null;
}

export interface HistoricalEventRecord {
  id: string;
  title: string;
  title_arabic: string | null;
  description: string | null;
  significance: string | null;
  start_year_hijri: number | null;
  end_year_hijri: number | null;
  start_year_gregorian: number | null;
  end_year_gregorian: number | null;
  /** Legacy aliases of the start years. */
  year_hijri: number | null;
  year_gregorian: number | null;
  category: string | null;
  location_name: string | null;
  verification_status: string;
  publication_ready: boolean;
  citation_source: string | null;
  citation_locator: string | null;
  citation_url: string | null;
  citation_retrieved_at: string | null;
}

export interface LocationRecord {
  id: string;
  name: string;
  name_arabic: string | null;
  modern_country: string | null;
  region: string | null;
  description: string | null;
  latitude: number | null;
  longitude: number | null;
  verification_status: string;
}

export interface CommentaryRecord {
  id: string;
  type: string | null;
  text: string;
  text_arabic: string | null;
  author: string | null;
  source_work: string | null;
  reference: string | null;
  citation_id: string | null;
  status: string;
  created_at: string | null;
  created_by: string;
  hadith: { id: string; title: string | null; source: string; hadith_no: string | null } | null;
  narrator: { id: string; name_english: string; name_arabic: string } | null;
}

export interface ReligiousTraditionRecord {
  id: string;
  name: string;
  name_arabic: string | null;
  description: string | null;
  geographic_origin: string | null;
  geographic_heartlands: string[];
  source_count: number;
  narrator_count: number;
}

export interface SourceTextRecord {
  id: string;
  title: string;
  title_original: string | null;
  author: string | null;
  approximate_date_ce: string | null;
  description: string | null;
  canonical_reference: string | null;
  religious_tradition_id: string;
  tradition_name: string;
  tradition: { id: string; name: string } | null;
}

export interface MotifTagRecord {
  id: string;
  name: string;
  category: string;
  description: string | null;
}

export interface ParallelRecord {
  id: string;
  parallel_type: string;
  isra_iliyyat_status: string;
  confidence_level: string;
  hadith_excerpt_en: string | null;
  source_text_original: string | null;
  source_text_en: string | null;
  scholarly_analysis: string | null;
  origin: string;
  status: string;
  created_at: string | null;
  hadith: { id: string; title: string | null; primary_topic: string | null; chapter: string | null; category: string | null };
  source_text: { id: string; title: string; canonical_reference: string | null; tradition_name: string };
  tradition: { id: string; name: string };
  motif_tags: MotifTagRecord[];
}

export interface ComparativeStat {
  tradition: string;
  type: string;
  count: number;
}

export interface TraditionConnections {
  traditions: Array<{ id: string; name: string; name_arabic: string | null; description: string | null }>;
  hadiths_with_parallels: Array<{
    hadith: { id: string; title: string | null };
    parallel: { id: string; parallel_type: string; isra_iliyyat_status: string };
    tradition: { id: string; name: string };
    source_text: { title: string; canonical_reference: string | null };
  }>;
}

/** How a telling corresponds to the report it was found from (report-correspondence job). */
export type CorrespondenceClass = 'same_wording' | 'same_report_variant_wording' | 'partial_overlap';
export type CorrespondenceDecision = 'confirmed' | 'rejected' | 'uncertain';
export type CorrespondenceReviewedRelation =
  | CorrespondenceClass
  | 'same_ruling_different_attribution'
  | 'shared_formula_only'
  | 'shared_quran_quotation';

/** The evidence linking a telling to the report: machine scores, and a reviewer decision when there is one. */
export interface TellingCorrespondence {
  /** Null only for a pair a reviewer confirmed with no machine candidate. */
  relation_class: CorrespondenceClass | null;
  jaccard: number | null;
  containment: number | null;
  scope: 'same_work' | 'cross_work_same_tradition' | 'cross_tradition' | null;
  decision: CorrespondenceDecision | null;
  reviewed_relation: CorrespondenceReviewedRelation | null;
  /** A reviewer confirmed the pair (hash-bound, live decision). Otherwise the pair is machine-found and unreviewed. */
  confirmed: boolean;
}

/** One telling of a report in the family: its text, reference and every chain it carries. */
export interface FamilyTelling {
  hadith_id: string;
  record_id: string;
  is_focal: boolean;
  tradition: HadithTraditionCode;
  collection_id: string;
  source_work: string;
  source_work_id: string;
  /** The stored number as loaded; display goes through `reportNumber` (Thaqalayn's stored number is the chapter). */
  hadith_no: string | null;
  /** False where the work's numbering is not citable (UNCITABLE_NUMBERING_WORKS): show the stable id instead. */
  numbering_citable: boolean;
  volume: string | null;
  url: string | null;
  page_ref: string | null;
  chapter: string | null;
  text_ar: string | null;
  matn_ar: string | null;
  sanad: string | null;
  /** Public English of this telling, labelled and credited like the report page; null when none is public. */
  english: TellingEnglish | null;
  correspondence: TellingCorrespondence | null;
  chain: ChainGraph;
}

/** A telling's English and its attribution (through src/lib/sources/report-credit.ts). */
export interface TellingEnglish {
  text: string;
  attribution: EnglishAttribution;
}

/** A report and every telling the archive links to it, capped; `capped` says some were left out. */
export interface ReportFamily {
  hadith_id: string;
  tellings: FamilyTelling[];
  /** Corresponding reports shown by the display rule, before the cap. */
  correspondences_total: number;
  capped: boolean;
  cap: number;
}
