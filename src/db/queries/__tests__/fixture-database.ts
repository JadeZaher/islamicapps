/**
 * Deterministic fixture database for the query-layer flow tests. See src/db/queries/AGENTS.md §Tests.
 *
 * Builds the real migrations into a private schema (`query_fixture` by default) of the development database,
 * loads real rows copied from the 2026-11-21 bundle (fixtures/corpus.json), and points DATABASE_URL at that
 * schema through the `search_path` startup parameter, so the app's own client and views run unchanged.
 * Refuses to run against the production database.
 */
import { createHash } from 'node:crypto';
import { readFileSync, readdirSync } from 'node:fs';
import path from 'node:path';
import { config as loadEnvironment } from 'dotenv';
import postgres, { type Sql } from 'postgres';
import { norm } from '../../../lib/attribution/classify-attribution';
import { connectionOptions } from '../../connection-options';

export const FIXTURE_VERSION_ID = 'dv:query-fixture';
export const FIXTURE_ACTOR = 'system:query-fixture';

type FixtureRow = Record<string, string | null>;
interface Corpus {
  collections: FixtureRow[];
  hadiths: FixtureRow[];
  chapters: FixtureRow[];
  books: FixtureRow[];
  translations: FixtureRow[];
  chains: FixtureRow[];
  mentions: FixtureRow[];
  links: Array<{ chain_id: string; position: number; narrator_id: string }>;
  narrators: FixtureRow[];
  lexicon_profiles: Array<Record<string, string | number>>;
  hadith_assessments: FixtureRow[];
  narrator_assessments: FixtureRow[];
}

/** Real identity candidates copied from the 2026-11-21 projection (fixtures/identity-candidates.json). */
export interface IdentityFixture {
  generated_from: { projection_content_sha256: string; projection_version: string };
  /** One extra Sahih Muslim report (k6:10008) whose chain has every identity case. */
  extra: { hadiths: FixtureRow[]; chains: FixtureRow[]; mentions: FixtureRow[] };
  narrators: Array<{ id: string; scholar_indx: string; name: string; name_ar: string | null; name_en: string | null; placeholder_reason: string | null }>;
  /** Mentions whose narrator_id the loader verified (uncontested confirmed source index). */
  verified: Array<{ mention_id: string; narrator_id: string }>;
  candidates: Array<{ mention_id: string; hadith_id: string; narrator_id: string; basis: string; detail: string | null; source_position: number | null }>;
}

export interface FixtureDatabase {
  schema: string;
  /** DATABASE_URL with the fixture search_path; the app client reads it. */
  url: string;
  /** A direct client on the fixture schema, for assertions on stored rows. */
  sql: Sql;
  corpus: Corpus;
  identity: IdentityFixture;
  close(): Promise<void>;
}

const REPOSITORY_ROOT = path.resolve(__dirname, '../../../..');

/** Opens the fixture URL, refusing production and anything but the development database. */
function fixtureUrl(schema: string): string {
  loadEnvironment({ path: path.join(REPOSITORY_ROOT, '.env.local'), quiet: true });
  const base = process.env.TEST_DATABASE_URL || process.env.DATABASE_URL;
  if (!base) throw new Error('Set DATABASE_URL (development) or TEST_DATABASE_URL to run the query flow tests.');
  if (process.env.DATABASE_URL_PRODUCTION && base === process.env.DATABASE_URL_PRODUCTION) {
    throw new Error('Refusing to build the fixture in the production database.');
  }
  const url = new URL(base);
  if (url.pathname.replace('/', '') === 'railway') throw new Error('Refusing to build the fixture in the production database.');
  if (!/^[a-z_][a-z0-9_]*$/.test(schema)) throw new Error('Fixture schema name must be a plain identifier.');
  url.searchParams.set('search_path', `${schema},public`);
  return url.toString();
}

/** The migration stream rewritten into `schema` (extensions stay in public; 0000 is skipped). */
function migrationStatements(schema: string): string[] {
  const directory = path.join(REPOSITORY_ROOT, 'drizzle/core');
  return readdirSync(directory)
    .filter((file) => /^\d{4}_.*\.sql$/.test(file) && !file.startsWith('0000_'))
    .sort()
    .flatMap((file) =>
      readFileSync(path.join(directory, file), 'utf8')
        .replaceAll('"public".', `"${schema}".`)
        .replaceAll('SET search_path = public, pg_temp', `SET search_path = ${schema}, public, pg_temp`)
        .split('--> statement-breakpoint'),
    )
    .map((statement) => statement.trim())
    .filter((statement) => statement.length > 0);
}

function trimmed(value: string | null | undefined): string | null {
  const text = (value ?? '').trim();
  return text === '' ? null : text;
}

/** Splits a lexicon `name` ("Imam Maalik مالك بن أنس") at its first Arabic letter. */
function splitNarratorName(name: string): { english: string | null; arabic: string | null } {
  const index = name.search(/[؀-ۿ]/);
  if (index < 0) return { english: trimmed(name), arabic: null };
  return { english: trimmed(name.slice(0, index)), arabic: trimmed(name.slice(index)) };
}

const TRADITIONS = [
  { id: 'tradition:sunni', code: 'Sunni', scheme: 'sunni_7tier' },
  { id: 'tradition:imami', code: 'Imami', scheme: 'imami_4tier' },
  { id: 'tradition:zaydi', code: 'Zaydi', scheme: 'zaydi_3tier' },
  { id: 'tradition:ibadi', code: 'Ibadi', scheme: 'ibadi_2tier' },
] as const;

/** Rights per work: every fixture work is cleared; provider English is allowed for Bukhari and al-Kafi only. */
const ENGLISH_POLICY: Record<string, 'reviewed_only' | 'source_provided_allowed'> = {
  'sunni:bukhari': 'source_provided_allowed',
  'imami:al-kafi': 'source_provided_allowed',
};

async function loadRows(sql: Sql, baseCorpus: Corpus, identity: IdentityFixture): Promise<void> {
  const corpus: Corpus = {
    ...baseCorpus,
    hadiths: [...baseCorpus.hadiths, ...identity.extra.hadiths],
    chains: [...baseCorpus.chains, ...identity.extra.chains],
    mentions: [...baseCorpus.mentions, ...identity.extra.mentions],
  };
  const pipeline = { first_seen_dataset_version_id: FIXTURE_VERSION_ID, changed_in_dataset_version_id: FIXTURE_VERSION_ID };
  const curated = { created_by: FIXTURE_ACTOR, updated_by: FIXTURE_ACTOR };

  await sql`insert into dataset_versions ${sql({
    id: FIXTURE_VERSION_ID,
    source_bundle_sha256: 'fixture',
    input_dataset_sha256: 'fixture',
    rawis_sha256: 'fixture',
    legacy_master_sha256: 'fixture',
    extractor_version: 'fixture',
    extractor_sha256: 'fixture',
    bundle_version: '2026-11-21',
    bundle_schema_version: 1,
    source_release_state: 'test_fixture',
    release_class: 'release',
    load_purpose: 'query-layer flow tests',
    load_status: 'complete',
    is_current: true,
    attribution_disclaimer: 'Test fixture: attributions are as recorded by the source datasets.',
    loaded_by: FIXTURE_ACTOR,
  })}`;

  await sql`insert into traditions ${sql(
    TRADITIONS.map((tradition) => ({
      id: tradition.id,
      code: tradition.code,
      normalized_name: tradition.code.toLowerCase(),
      grade_scheme: tradition.scheme,
      ...pipeline,
    })),
  )}`;

  const sourceIds = [...new Set(corpus.collections.map((collection) => collection.source_id!))];
  await sql`insert into sources ${sql(
    sourceIds.map((id) => ({ id, slug: id.replace('source:', ''), name: id.replace('source:', ''), release_state: 'unreviewed_local_snapshot', ...pipeline })),
  )}`;

  const traditionId = (code: string | null) => TRADITIONS.find((tradition) => tradition.code === code)!.id;
  type FixtureCollection = { id: string; source_work_id: string; slug: string; name: string; tradition: string; source_id: string; sortKey: number };
  const collectionByWork = new Map<string, FixtureCollection>(
    corpus.collections.map((collection, index) => [
      collection.source_work_id!,
      { ...(collection as unknown as Omit<FixtureCollection, 'sortKey'>), sortKey: index + 1 },
    ]),
  );
  await sql`insert into collections ${sql(
    [...collectionByWork.values()].map((collection) => ({
      id: collection.id,
      source_work_id: collection.source_work_id,
      slug: collection.slug,
      name: collection.name,
      sort_key: collection.sortKey,
      tradition_id: traditionId(collection.tradition),
      source_id: collection.source_id,
      registry_version: 'fixture',
      ...pipeline,
    })),
  )}`;
  await sql`insert into collection_rights ${sql(
    [...collectionByWork.values()].map((collection) => ({
      collection_id: collection.id,
      rights_status: 'cleared',
      english_policy: ENGLISH_POLICY[collection.source_work_id!] ?? 'reviewed_only',
      ...curated,
    })),
  )}`;

  await sql`insert into books ${sql(
    corpus.books.map((book) => ({ id: book.id, collection_id: book.collection_id, number: trimmed(book.number), name: trimmed(book.name), ...pipeline })),
  )}`;
  await sql`insert into chapters ${sql(
    corpus.chapters.map((chapter) => ({
      id: chapter.id,
      collection_id: chapter.collection_id,
      book_id: chapter.book_id,
      number: trimmed(chapter.number),
      name: trimmed(chapter.name),
      ...pipeline,
    })),
  )}`;
  await sql`update chapters set name_folded = lower(unaccent(name))`;

  const chapterNames = new Map(corpus.chapters.map((chapter) => [chapter.id!, chapter.name]));
  const bookNames = new Map(corpus.books.map((book) => [book.id!, book.name]));
  await sql`insert into hadiths ${sql(
    corpus.hadiths.map((hadith) => {
      const collection = collectionByWork.get(hadith.source_work_id!)!;
      return {
        id: hadith.id,
        record_id: hadith.record_id,
        source_record_id: trimmed(hadith.source_record_id),
        collection_id: collection.id,
        collection_sort_key: collection.sortKey,
        source_display_label: collection.name,
        tradition_id: traditionId(hadith.tradition),
        book_id: hadith.book_id,
        chapter_id: hadith.chapter_id,
        // Chapter title as the browse structure names it: the chapter, else the book.
        chapter_title: trimmed(chapterNames.get(hadith.chapter_id ?? '') ?? bookNames.get(hadith.book_id ?? '') ?? null),
        hadith_no: trimmed(hadith.hadith_no),
        text_ar: hadith.text_ar,
        text_ar_normalized: norm(hadith.text_ar),
        arabic_sha256: hadith.arabic_sha256,
        sanad: trimmed(hadith.sanad),
        matn_ar: trimmed(hadith.matn_ar),
        url: trimmed(hadith.url),
        page_ref: trimmed(hadith.page_ref),
        provenance_source: hadith.provenance,
        translation_disposition: trimmed(hadith.translation_disposition),
        ...pipeline,
      };
    }),
  )}`;
  await sql`update hadiths set chapter_title_folded = lower(unaccent(chapter_title)), category_folded = lower(unaccent(category))`;

  await sql`insert into translations ${sql(
    corpus.translations.map((translation) => ({
      id: translation.id,
      hadith_id: `hadith:${translation.id!.slice('translation:'.length, -':en'.length)}`,
      language: 'en',
      text: translation.text!.replace(/\s+/g, ' ').trim(),
      // Provider English without row-by-row review (question 5): public only where the work's policy allows it.
      state: 'source_provided',
      quality_status: translation.status,
      review_state_raw: translation.review_state,
      source: translation.source,
      source_record_id: translation.source_record_id,
      arabic_sha256: translation.arabic_sha256,
      provenance_source: translation.provenance_source,
      ...pipeline,
    })),
  )}`;

  await sql`insert into narrators ${sql(
    corpus.narrators.map((narrator) => {
      const name = splitNarratorName(narrator.name!);
      return {
        id: narrator.id,
        authority: 'rawi',
        authority_key: narrator.scholar_indx,
        scholar_indx: Number(narrator.scholar_indx),
        name: narrator.name,
        name_en: name.english,
        name_ar: name.arabic,
        name_ar_normalized: name.arabic ? norm(name.arabic) : null,
        ...pipeline,
      };
    }),
  )}`;
  const corpusNarrators = new Set(corpus.narrators.map((narrator) => narrator.id));
  const extraNarrators = identity.narrators.filter((narrator) => !corpusNarrators.has(narrator.id));
  if (extraNarrators.length > 0) {
    await sql`insert into narrators ${sql(
      extraNarrators.map((narrator) => ({
        id: narrator.id,
        authority: 'rawi',
        authority_key: narrator.scholar_indx,
        scholar_indx: Number(narrator.scholar_indx),
        name: narrator.name,
        name_en: narrator.name_en,
        name_ar: narrator.name_ar,
        name_ar_normalized: narrator.name_ar ? norm(narrator.name_ar) : null,
        ...pipeline,
      })),
    )}`;
  }
  for (const narrator of identity.narrators.filter((row) => row.placeholder_reason)) {
    await sql`update narrators set placeholder_reason = ${narrator.placeholder_reason} where id = ${narrator.id}`;
  }
  await sql`update narrators set name_en_folded = lower(unaccent(name_en))`;

  await sql`insert into narrator_lexicon_profiles ${sql(
    corpus.lexicon_profiles.map((profile) => ({
      narrator_id: profile.narrator_id,
      bundle_id: profile.bundle_id,
      raw_profile_sha256: profile.raw_profile_sha256,
      lexicon_grade_label: profile.grade,
      birth_year_hijri: profile.birth_year_hijri,
      death_year_hijri: profile.death_year_hijri,
      birth_place: profile.birth_place,
      death_place: profile.death_place,
      review_state: 'lexicon_unverified',
      source_status: 'source_status_unknown',
      source_locator: profile.source_locator,
      ...pipeline,
    })),
  )}`;

  await sql`insert into chains ${sql(
    corpus.chains.map((chain) => ({
      id: chain.id,
      hadith_id: chain.hadith_id,
      branch: Number(chain.branch),
      length: Number(chain.length),
      resolved: chain.resolved === 'true',
      extraction_method: chain.extraction_method,
      sanad_confidence: chain.sanad_confidence,
      ...pipeline,
    })),
  )}`;

  // Verified identity exactly as the loader writes it (src/db/AGENTS.md §Identity candidates): only an uncontested
  // confirmed source index. The bundle's name links in corpus.links are candidates now, not links.
  const verified = new Map(identity.verified.map((row) => [row.mention_id, row.narrator_id]));
  await sql`insert into chain_mentions ${sql(
    corpus.mentions.map((mention) => {
      const narratorId = verified.get(mention.id!) ?? null;
      return {
        id: mention.id,
        chain_id: mention.chain_id,
        hadith_id: mention.hadith_id,
        position: Number(mention.position),
        surface_ar: mention.surface,
        surface_normalized: mention.normalized_surface,
        review_unit_id: `unit:${mention.normalized_surface}`,
        review_unit_fine_id: `unit-fine:${mention.chain_id}:${mention.position}`,
        link_kind: narratorId ? 'person' : 'unclassified',
        resolution: narratorId ? 'source_index' : 'unresolved',
        resolution_basis: narratorId ? 'source_index' : null,
        narrator_id: narratorId,
        confidence: narratorId ? 1 : null,
        extraction_method: narratorId ? 'source_index_confirmed_by_text' : null,
        ...pipeline,
      };
    }),
  )}`;
  await sql`insert into chain_mention_candidates ${sql(
    identity.candidates.map((candidate) => ({
      id: `candidate:${candidate.mention_id.replace(/^mention:/, '')}:${candidate.basis}:${candidate.narrator_id.replace(/^narrator:/, '')}`,
      mention_id: candidate.mention_id,
      hadith_id: candidate.hadith_id,
      narrator_id: candidate.narrator_id,
      basis: candidate.basis,
      detail: candidate.detail,
      source_position: candidate.source_position,
      ...pipeline,
    })),
  )}`;

  const traditionOf = new Map(corpus.hadiths.map((hadith) => [hadith.id!, hadith.tradition]));
  await sql`insert into hadith_assessments ${sql(
    corpus.hadith_assessments.map((assessment, index) => ({
      id: `assessment:fixture:${index}`,
      hadith_id: assessment.hadith_id,
      tradition_id: traditionId(assessment.tradition ?? traditionOf.get(assessment.hadith_id!) ?? null),
      grade_scheme: 'imami_4tier',
      ordinal: 0,
      kind: assessment.kind,
      grader: assessment.grader,
      grade_raw: assessment.grade_raw,
      grade_canonical: assessment.grade_canonical,
      citation_raw: assessment.citation_raw,
      source_field: 'gradings_full',
      review_state: 'source_provided',
      ...pipeline,
    })),
  )}`;

  await sql`insert into bibliographic_works ${sql({
    id: 'work:taqrib-al-tahdhib',
    title: 'Taqrīb al-Tahdhīb',
    title_ar: 'تقريب التهذيب',
    author: 'Ibn Ḥajar al-ʿAsqalānī',
    ...pipeline,
  })}`;
  await sql`insert into citations ${sql({
    id: 'citation:fixture:taqrib-malik',
    work_id: 'work:taqrib-al-tahdhib',
    quote_ar: 'رأس المتقنين وكبير المتثبتين',
    review_state: 'human_verified',
    ...pipeline,
  })}`;
  await sql`insert into narrator_assessments ${sql(
    corpus.narrator_assessments.map((assessment, index) => ({
      id: `verdict:fixture:${index}`,
      narrator_id: assessment.narrator_id,
      tradition_id: assessment.tradition ? traditionId(assessment.tradition) : null,
      kind: assessment.kind,
      verdict: assessment.verdict,
      critic: assessment.critic,
      quote_ar: assessment.quote_ar,
      provenance: assessment.provenance,
      citation_id: assessment.status === 'published' ? 'citation:fixture:taqrib-malik' : null,
      status: assessment.status,
      ...curated,
    })),
  )}`;

  await sql`select refresh_publication_facets(array(select id from hadiths))`;
  await sql`refresh materialized view narrator_transmissions`;
}

/** Drops and rebuilds the fixture schema, then points DATABASE_URL at it. */
export async function prepareFixtureDatabase(schema = process.env.QUERY_FIXTURE_SCHEMA || 'query_fixture'): Promise<FixtureDatabase> {
  const url = fixtureUrl(schema);
  const corpus = JSON.parse(readFileSync(path.join(__dirname, 'fixtures/corpus.json'), 'utf8')) as Corpus;
  const identity = JSON.parse(readFileSync(path.join(__dirname, 'fixtures/identity-candidates.json'), 'utf8')) as IdentityFixture;
  const sql = postgres(url, { ...connectionOptions(url, 1), onnotice: () => {} });
  await sql.unsafe(`drop schema if exists ${schema} cascade`);
  await sql.unsafe(`create schema ${schema}`);
  for (const statement of migrationStatements(schema)) await sql.unsafe(statement);
  await loadRows(sql, corpus, identity);
  process.env.DATABASE_URL = url;
  return {
    schema,
    url,
    sql,
    corpus,
    identity,
    close: () => sql.end({ timeout: 5 }),
  };
}

/** sha256 of a string, hex; mirrors the Arabic round-trip binding. */
export function sha256(text: string): string {
  return createHash('sha256').update(text, 'utf8').digest('hex');
}
