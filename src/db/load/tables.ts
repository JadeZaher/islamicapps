/** Load contract: the pipeline tables a bundle projection fills, in merge (foreign-key) order. See src/db/load/AGENTS.md. */

/** One pipeline table the loader merges from `canonical/<table>.csv`. */
export interface PipelineTableSpec {
  /** Table name, also the CSV file stem. */
  name: string;
  /** Primary-key columns (the merge conflict target). */
  key: string[];
  /** Live columns the loader writes itself, never present in the CSV. */
  loaderDerived: string[];
  /** CSV columns written on insert only and then owned by the derived-column step (section 4.1). */
  derivedFromStaging: string[];
}

/** Bookkeeping columns on every pipeline table (section 5.1); written only by the merge. */
export const PIPELINE_BOOKKEEPING_COLUMNS = [
  'first_seen_dataset_version_id',
  'changed_in_dataset_version_id',
  'updated_at',
  'retired_at',
  'retired_in_dataset_version_id',
] as const;

/** Dependency order of section 4.3 step 6: evidence before collections and assessments. */
export const PIPELINE_TABLES: PipelineTableSpec[] = [
  { name: 'traditions', key: ['id'], loaderDerived: [], derivedFromStaging: [] },
  { name: 'sources', key: ['id'], loaderDerived: [], derivedFromStaging: [] },
  { name: 'narrators', key: ['id'], loaderDerived: ['name_en_folded'], derivedFromStaging: [] },
  // External narrators' own records, crosswalk ids and lexicon link candidates (0010; src/db/AGENTS.md §External identity).
  { name: 'narrator_source_profiles', key: ['narrator_id'], loaderDerived: [], derivedFromStaging: [] },
  { name: 'narrator_external_ids', key: ['id'], loaderDerived: [], derivedFromStaging: [] },
  { name: 'narrator_link_candidates', key: ['id'], loaderDerived: [], derivedFromStaging: [] },
  { name: 'bibliographic_works', key: ['id'], loaderDerived: [], derivedFromStaging: [] },
  { name: 'editions', key: ['id'], loaderDerived: [], derivedFromStaging: [] },
  { name: 'citations', key: ['id'], loaderDerived: [], derivedFromStaging: [] },
  { name: 'collections', key: ['id'], loaderDerived: [], derivedFromStaging: [] },
  { name: 'books', key: ['id'], loaderDerived: [], derivedFromStaging: [] },
  { name: 'chapters', key: ['id'], loaderDerived: [], derivedFromStaging: [] },
  {
    name: 'hadiths',
    key: ['id'],
    loaderDerived: ['source_text_status', 'chain_status', 'grading_status'],
    derivedFromStaging: [],
  },
  { name: 'translations', key: ['id'], loaderDerived: [], derivedFromStaging: [] },
  { name: 'narrator_lexicon_profiles', key: ['narrator_id'], loaderDerived: [], derivedFromStaging: [] },
  { name: 'narrator_aliases', key: ['id'], loaderDerived: [], derivedFromStaging: [] },
  { name: 'narrator_teachers', key: ['student_id', 'teacher_id'], loaderDerived: [], derivedFromStaging: [] },
  { name: 'chains', key: ['id'], loaderDerived: ['verified_link_count'], derivedFromStaging: [] },
  {
    name: 'chain_mentions',
    key: ['id'],
    loaderDerived: ['decision_id'],
    derivedFromStaging: ['link_kind', 'resolution', 'resolution_basis', 'narrator_id', 'confidence', 'extraction_method'],
  },
  // After chain_mentions and narrators: every candidate references both (src/db/AGENTS.md §Identity candidates).
  { name: 'chain_mention_candidates', key: ['id'], loaderDerived: [], derivedFromStaging: [] },
  { name: 'hadith_assessments', key: ['id'], loaderDerived: [], derivedFromStaging: [] },
  // Report correspondences (src/db/AGENTS.md §Report correspondences): pipeline candidates bound to both Arabic hashes.
  { name: 'report_correspondence_candidates', key: ['id'], loaderDerived: [], derivedFromStaging: [] },
  { name: 'report_correspondence_cluster_members', key: ['method_version', 'hadith_id'], loaderDerived: [], derivedFromStaging: [] },
];

/** Bare SQL identifier check: every name interpolated into SQL comes from this file or the catalog. */
export function quoteIdentifier(name: string): string {
  if (!/^[a-z_][a-z0-9_]*$/.test(name)) throw new Error(`unsafe SQL identifier: ${name}`);
  return `"${name}"`;
}
