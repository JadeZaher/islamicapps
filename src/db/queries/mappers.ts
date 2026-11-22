/** One row mapper per entity, producing the section 9.4 contracts (section 3.2 rule 3). */
import 'server-only';
import type {
  CommentaryRecord,
  HadithAssessment,
  HadithAssessmentGroup,
  HadithListItem,
  HistoricalEventRecord,
  LocationRecord,
  MotifTagRecord,
  NarratorBio,
  NarratorListItem,
  NarratorVerdict,
  ParallelRecord,
  SourceNote,
  SourceTextRecord,
} from './contracts';
import { HADITH_TRADITION_CODES, type HadithTraditionCode, toInt, toIso } from './sql-helpers';

type Row = Record<string, unknown>;

/** Non-blank trimmed string or null. */
export function text(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  const trimmed = String(value).trim();
  return trimmed === '' ? null : trimmed;
}

/** Text kept byte for byte (Arabic and English bodies are never trimmed or folded). */
export function verbatim(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  const asString = String(value);
  return asString.trim() === '' ? null : asString;
}

function tradition(value: unknown): HadithTraditionCode {
  return value as HadithTraditionCode;
}

function arrayOf(value: unknown): Row[] {
  return Array.isArray(value) ? (value as Row[]) : [];
}

/** Hadith list row (json_build_object keys in hadith.ts / hadith-review.ts). */
export function mapHadithListItem(row: Row): HadithListItem {
  const chapter = text(row.chapter_title);
  const category = text(row.category);
  const english = verbatim(row.english_text);
  const arabic = verbatim(row.text_ar);
  return {
    id: String(row.id),
    record_id: String(row.record_id),
    title: chapter ?? category,
    primary_topic: category,
    chapter,
    chapter_no: text(row.chapter_no),
    category,
    volume: text(row.volume),
    hadith_no: text(row.hadith_no),
    source: String(row.collection_name ?? ''),
    source_display_label: text(row.source_display_label),
    collection_id: String(row.collection_id),
    tradition: tradition(row.tradition),
    text_ar: arabic,
    text_arabic: arabic,
    matn_ar: verbatim(row.matn_ar),
    text_en: english,
    text_english: english,
    english_state: text(row.english_state),
    source_text_status: String(row.source_text_status),
    chain_status: String(row.chain_status),
    grading_status: String(row.grading_status),
  };
}

/** `hadiths.source_notes` (jsonb list) as notes; an entry without text or of an unknown kind is dropped. */
export function mapSourceNotes(value: unknown): SourceNote[] {
  const kinds = ['compiler_comment', 'arranger_note', 'editor_footnote', 'note'];
  return arrayOf(value).flatMap((row) => {
    const textAr = verbatim(row.text_ar);
    return textAr && kinds.includes(String(row.kind)) ? [{ kind: row.kind as SourceNote['kind'], text_ar: textAr }] : [];
  });
}

/** Groups assessment rows into one group per tradition, in the fixed tradition order; empty groups kept. */
export function groupAssessments(value: unknown): HadithAssessmentGroup[] {
  const assessments: HadithAssessment[] = arrayOf(value).map((row) => ({
    tradition: tradition(row.tradition),
    kind: row.kind as HadithAssessment['kind'],
    grade_raw: String(row.grade_raw),
    grade_canonical: text(row.grade_canonical),
    grader: text(row.grader),
    citation_raw: text(row.citation_raw),
  }));
  return HADITH_TRADITION_CODES.map((code) => ({
    tradition: code,
    assessments: assessments.filter((assessment) => assessment.tradition === code),
  }));
}

export function mapVerdicts(value: unknown): NarratorVerdict[] {
  return arrayOf(value).map((row) => ({
    id: String(row.id),
    tradition: (row.tradition ?? null) as HadithTraditionCode | null,
    verdict: String(row.verdict),
    kind: String(row.kind),
    status: String(row.status),
    critic: text(row.critic),
    quote_ar: verbatim(row.quote_ar),
    quote_en: verbatim(row.quote_en),
  }));
}

/** Display names: English falls back to the lexicon `name`, Arabic to an empty string. */
export function narratorNames(row: Row): { name: string; name_english: string; name_arabic: string } {
  const name = String(row.name ?? '');
  return {
    name,
    name_english: text(row.name_en) ?? name,
    name_arabic: text(row.name_ar) ?? '',
  };
}

export function mapNarratorListItem(row: Row): NarratorListItem {
  return {
    id: String(row.id),
    ...narratorNames(row),
    tabaqah: text(row.tabaqah_class),
    geographic_region: text(row.geographic_region),
    verdicts: mapVerdicts(row.verdicts),
  };
}

export function mapNarratorBio(value: unknown): NarratorBio | null {
  if (!value || typeof value !== 'object') return null;
  const row = value as Row;
  return {
    status: String(row.status),
    is_prophet: row.is_prophet === true,
    tabaqah: text(row.tabaqah_class),
    name_english_clean: text(row.name_en_clean),
    name_arabic_clean: text(row.name_ar_clean),
    kunya: text(row.kunya),
    nasab: text(row.nasab),
    nisba: text(row.nisba),
    geographic_region: text(row.geographic_region),
    death_year_hijri: toInt(row.death_year_hijri),
    death_year_gregorian: toInt(row.death_year_gregorian),
    bio_summary: verbatim(row.bio_summary),
  };
}

export function mapHistoricalEvent(row: Row): HistoricalEventRecord {
  const startHijri = toInt(row.start_year_hijri);
  const startGregorian = toInt(row.start_year_gregorian);
  return {
    id: String(row.id),
    title: String(row.title),
    title_arabic: text(row.title_arabic),
    description: verbatim(row.description),
    significance: verbatim(row.significance),
    start_year_hijri: startHijri,
    end_year_hijri: toInt(row.end_year_hijri),
    start_year_gregorian: startGregorian,
    end_year_gregorian: toInt(row.end_year_gregorian),
    year_hijri: startHijri,
    year_gregorian: startGregorian,
    category: text(row.category),
    location_name: text(row.location_name),
    verification_status: String(row.verification_status),
    publication_ready: row.publication_ready === true,
    citation_source: text(row.citation_source),
    citation_locator: text(row.citation_locator),
    citation_url: text(row.citation_url),
    citation_retrieved_at: toIso(row.citation_retrieved_at),
  };
}

export function mapLocation(row: Row): LocationRecord {
  const latitude = row.latitude;
  const longitude = row.longitude;
  return {
    id: String(row.id),
    name: String(row.name),
    name_arabic: text(row.name_arabic),
    modern_country: text(row.modern_country),
    region: text(row.region),
    description: verbatim(row.description),
    // `??`, never `||`: a latitude of 0 is a real coordinate (rule 7).
    latitude: latitude === null || latitude === undefined ? null : Number(latitude),
    longitude: longitude === null || longitude === undefined ? null : Number(longitude),
    verification_status: String(row.verification_status),
  };
}

export function mapCommentary(row: Row): CommentaryRecord {
  const hadith = row.hadith as Row | null;
  const narrator = row.narrator as Row | null;
  return {
    id: String(row.id),
    type: text(row.type),
    text: String(row.text),
    text_arabic: verbatim(row.text_arabic),
    author: text(row.author),
    source_work: text(row.source_work),
    reference: text(row.reference),
    citation_id: text(row.citation_id),
    status: String(row.status),
    created_at: toIso(row.created_at),
    created_by: String(row.created_by),
    hadith: hadith
      ? {
          id: String(hadith.id),
          title: text(hadith.chapter_title) ?? text(hadith.category),
          source: String(hadith.collection_name ?? ''),
          hadith_no: text(hadith.hadith_no),
        }
      : null,
    narrator: narrator ? { id: String(narrator.id), ...narratorNames(narrator) } : null,
  };
}

export function mapMotifTag(row: Row): MotifTagRecord {
  return {
    id: String(row.id),
    name: String(row.name),
    category: String(row.category),
    description: verbatim(row.description),
  };
}

export function mapSourceText(row: Row): SourceTextRecord {
  const traditionName = String(row.tradition_name ?? '');
  return {
    id: String(row.id),
    title: String(row.title),
    title_original: text(row.title_original),
    author: text(row.author),
    approximate_date_ce: text(row.approximate_date_ce),
    description: verbatim(row.description),
    canonical_reference: text(row.canonical_reference),
    religious_tradition_id: String(row.religious_tradition_id),
    tradition_name: traditionName,
    tradition: row.religious_tradition_id ? { id: String(row.religious_tradition_id), name: traditionName } : null,
  };
}

export function mapParallel(row: Row): ParallelRecord {
  const hadith = (row.hadith ?? {}) as Row;
  const chapter = text(hadith.chapter_title);
  const category = text(hadith.category);
  return {
    id: String(row.id),
    parallel_type: String(row.parallel_type),
    isra_iliyyat_status: String(row.isra_iliyyat_status),
    confidence_level: String(row.confidence_level),
    hadith_excerpt_en: verbatim(row.hadith_excerpt_en),
    source_text_original: verbatim(row.source_text_original),
    source_text_en: verbatim(row.source_text_en),
    scholarly_analysis: verbatim(row.scholarly_analysis),
    origin: String(row.origin),
    status: String(row.status),
    created_at: toIso(row.created_at),
    hadith: { id: String(hadith.id ?? row.hadith_id), title: chapter ?? category, primary_topic: category, chapter, category },
    source_text: {
      id: String(row.source_text_id),
      title: String(row.source_text_title ?? ''),
      canonical_reference: text(row.canonical_reference),
      tradition_name: String(row.tradition_name ?? ''),
    },
    tradition: { id: String(row.religious_tradition_id), name: String(row.tradition_name ?? '') },
    motif_tags: arrayOf(row.motif_tags).map(mapMotifTag),
  };
}
