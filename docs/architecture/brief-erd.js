/*
 * Diagram data for brief-schema.html and brief.html. Plain data, no logic.
 *
 * Source of truth: the Drizzle schema in src/db/schema/*.ts (built objects) and docs/architecture/data-architecture.md
 * (designed objects). To update after a schema change: edit the matching entry below (entity block, relationship line,
 * and the purpose in `tables`). The pages count tables and views from this file; nothing else needs a number changed.
 *
 * Shape:
 *   window.ERD          built domains:   { id, name, owner, blurb, tables: [{ name, kind, purpose }], mermaid }
 *   window.ERD_PLANNED  planned domains: the same, plus `basis` (where the design lives). Planned tables are never counted
 *                       as built.
 *   kind  = "table" | "view" | "materialized view"          owner = "pipeline" | "curation" | "operations" | "derived"
 *
 * Mermaid rules the renderer relies on: lowercase snake_case entity names; attribute lines are `type name` with an optional
 * PK, FK or UK; at most 8 attributes per entity; relationship labels are a single word. Entities named only in a
 * relationship line (for example hadiths inside the Isnad diagram) are drawn as empty boxes by Mermaid, which is intended.
 */
window.ERD = [
  {
    id: "corpus",
    name: "Corpus",
    owner: "pipeline",
    blurb: "The hadith corpus itself: the four traditions, source works, browsing structure, Arabic reports and their English translations, with a per-work publication gate.",
    tables: [
      { name: "traditions", kind: "table", purpose: "The closed set of four hadith traditions (Ibadi, Imami, Sunni, Zaydi) and their grading schemes." },
      { name: "sources", kind: "table", purpose: "The upstream provider a row came from." },
      { name: "collections", kind: "table", purpose: "One row per source work (34 today), tied to its tradition and provider." },
      { name: "collection_rights", kind: "table", purpose: "The owner's per-work publication and English-text decision. A reload never touches it, and it is empty until the owner records decisions." },
      { name: "books", kind: "table", purpose: "Book-level browsing structure inside a collection." },
      { name: "chapters", kind: "table", purpose: "Chapter-level browsing structure inside a collection." },
      { name: "hadiths", kind: "table", purpose: "One row per report: Arabic stored byte for byte with its hash, plus status facets for source text, chain and grading that default to the worst state." },
      { name: "translations", kind: "table", purpose: "The English the source provided, bound by hash to the Arabic it renders, with a provenance state." }
    ],
    mermaid: `erDiagram
  traditions {
    text id PK
    text code UK
    text name_arabic
    text normalized_name
    text grade_scheme
  }
  sources {
    text id PK
    text slug UK
    text name
    text release_state
  }
  collections {
    text id PK
    text source_work_id UK
    text slug UK
    text name
    int sort_key UK
    text tradition_id FK
    text source_id FK
    text bibliographic_work_id FK
  }
  collection_rights {
    text collection_id PK
    text rights_status
    text english_policy
    text rights_note
    text citation
  }
  books {
    text id PK
    text collection_id FK
    text number
    text name
    text volume
  }
  chapters {
    text id PK
    text collection_id FK
    text book_id FK
    text number
    text name
  }
  hadiths {
    text id PK
    text record_id UK
    text collection_id FK
    text tradition_id FK
    text book_id FK
    text chapter_id FK
    text text_ar
    text arabic_sha256
  }
  translations {
    text id PK
    text hadith_id FK
    text language
    text text
    text state
    text quality_status
    text arabic_sha256
  }
  traditions ||--o{ collections : holds
  sources ||--o{ collections : supplies
  collections ||--o| collection_rights : gated
  collections ||--o{ books : contains
  collections ||--o{ chapters : contains
  books ||--o{ chapters : groups
  collections ||--o{ hadiths : contains
  traditions ||--o{ hadiths : classifies
  books ||--o{ hadiths : places
  chapters ||--o{ hadiths : places
  hadiths ||--o{ translations : has
`
  },
  {
    id: "narrators",
    name: "Narrators",
    owner: "pipeline",
    blurb: "Narrator identity from the lexicon: names, the lexicon's own unverified biography, name variants and declared teacher links. Never a verdict.",
    tables: [
      { name: "narrators", kind: "table", purpose: "Identity only; never a verdict, grade or reliability column. A placeholder reason marks lexicon rows that cannot name one person, which are never a match target." },
      { name: "narrator_lexicon_profiles", kind: "table", purpose: "Everything the lexicon claims about a narrator (dates, places, biography), kept as an unverified lexicon claim." },
      { name: "narrator_aliases", kind: "table", purpose: "Name surfaces a narrator is known by, for matching." },
      { name: "narrator_teachers", kind: "table", purpose: "Teacher and student links declared by the lexicon; used only to rank candidates, never as transmission evidence." }
    ],
    mermaid: `erDiagram
  narrators {
    text id PK
    text authority
    text authority_key
    int scholar_indx UK
    text name
    text name_ar
    text name_en
    text placeholder_reason
  }
  narrator_lexicon_profiles {
    text narrator_id PK
    text bundle_id UK
    text bio
    int birth_year_hijri
    int death_year_hijri
    text geographic_region
    text review_state
    text source_status
  }
  narrator_aliases {
    text id PK
    text narrator_id FK
    text surface
    text normalized_surface
    text alias_kind
  }
  narrator_teachers {
    text student_id PK
    text teacher_id FK
    int evidence_count
    bool reciprocal
    text review_state
  }
  narrators ||--o| narrator_lexicon_profiles : profiled
  narrators ||--o{ narrator_aliases : named
  narrators ||--o{ narrator_teachers : studies
  narrators ||--o{ narrator_teachers : teaches
`
  },
  {
    id: "isnad",
    name: "Isnad",
    owner: "pipeline",
    blurb: "Chains of transmission as written, every identity candidate for each name with its basis, the human decisions that settle a name, and the views derived from verified links only.",
    tables: [
      { name: "chains", kind: "table", purpose: "One row per branch (tahwil) of a report." },
      { name: "chain_mentions", kind: "table", purpose: "The name as written at one position of one branch. It carries a narrator only when the identity is verified." },
      { name: "chain_mention_candidates", kind: "table", purpose: "Every automatic identity candidate for a name, each with its basis (exact name, spelling fold, kunya only, the source's own index, or that index confirmed by the Arabic). Disagreeing candidates are all kept." },
      { name: "chain_absence_dispositions", kind: "table", purpose: "Records that a report, or a whole work, has no chain by nature (curation)." },
      { name: "narrator_surface_decisions", kind: "table", purpose: "A reviewer's identity decision for a name in a context, replayed onto every matching mention after a load (curation)." },
      { name: "narrator_lifespans", kind: "view", purpose: "Birth and death ranges per narrator, never collapsing competing claims." },
      { name: "narrator_transmissions", kind: "materialized view", purpose: "Who narrated from whom, from consecutive verified links only." }
    ],
    mermaid: `erDiagram
  chains {
    text id PK
    text hadith_id FK
    int branch
    int length
    bool resolved
    int verified_link_count
    text extraction_method
    real confidence
  }
  chain_mentions {
    text id PK
    text chain_id FK
    int position
    text surface_ar
    text link_kind
    text resolution
    text narrator_id FK
    text decision_id FK
  }
  chain_mention_candidates {
    text id PK
    text mention_id FK
    text hadith_id FK
    text narrator_id FK
    text basis
    text detail
    int source_position
  }
  chain_absence_dispositions {
    text id PK
    text collection_id FK
    text hadith_id FK
    text reason
    text citation_id FK
  }
  narrator_surface_decisions {
    text id PK
    text scope
    text unit_id
    text decision_kind
    text target_narrator_id FK
    text citation_id FK
    text reviewer
    timestamptz reviewed_at
  }
  narrator_lifespans {
    text narrator_id
    int birth_min
    int birth_max
    int death_min
    int death_max
    int claim_count
    bool disputed
    text basis
  }
  narrator_transmissions {
    text student_id
    text teacher_id
    int hadith_count
    int occurrence_count
    real confidence
    text temporal_plausibility
    text temporal_reason
  }
  hadiths ||--o{ chains : has
  chains ||--o{ chain_mentions : lists
  hadiths ||--o{ chain_mentions : contains
  narrators |o--o{ chain_mentions : verifies
  narrator_surface_decisions |o--o{ chain_mentions : decides
  chain_mentions ||--o{ chain_mention_candidates : proposes
  narrators ||--o{ chain_mention_candidates : names
  narrators |o--o{ narrator_surface_decisions : targets
  collections ||--o{ narrator_surface_decisions : scopes
  collections |o--o{ chain_absence_dispositions : excuses
  hadiths |o--o{ chain_absence_dispositions : excuses
  citations |o--o{ chain_absence_dispositions : cites
  citations |o--o{ narrator_surface_decisions : cites
  chain_mentions }o--o{ narrator_transmissions : derives
  narrators ||--o{ narrator_transmissions : links
  narrators ||--o| narrator_lifespans : spans
  narrator_lifespans |o--o{ narrator_transmissions : bounds
`
  },
  {
    id: "assessments",
    name: "Assessments and biography",
    owner: "curation",
    blurb: "Tradition-scoped grades on reports, verdicts on narrators and curated biographies. A grade is always attributed to a grader within a tradition.",
    tables: [
      { name: "hadith_assessments", kind: "table", purpose: "Pipeline-owned, tradition-scoped, multi-valued grades on a report, each with its grader and citation. A collection label is stored as a label, never as a grade." },
      { name: "narrator_assessments", kind: "table", purpose: "Curation-owned verdicts on a narrator by a named critic, always scoped to a tradition before publication." },
      { name: "narrator_bios", kind: "table", purpose: "Curated biography fields, one row per narrator; publication needs a citation." }
    ],
    mermaid: `erDiagram
  hadith_assessments {
    text id PK
    text hadith_id FK
    text tradition_id FK
    text kind
    text grader
    text grade_raw
    text grade_canonical
    text citation_id FK
  }
  narrator_assessments {
    text id PK
    text narrator_id FK
    text tradition_id FK
    text kind
    text verdict
    text critic
    text citation_id FK
    text status
  }
  narrator_bios {
    text narrator_id PK
    bool is_prophet
    text tabaqah_class
    text kunya
    int death_year_hijri
    text bio_summary
    text citation_id FK
    text status
  }
  hadiths ||--o{ hadith_assessments : graded
  traditions ||--o{ hadith_assessments : scopes
  citations |o--o{ hadith_assessments : cites
  narrators ||--o{ narrator_assessments : judged
  traditions |o--o{ narrator_assessments : scopes
  citations |o--o{ narrator_assessments : cites
  narrators ||--o| narrator_bios : described
  citations |o--o{ narrator_bios : cites
`
  },
  {
    id: "evidence",
    name: "Evidence and citations",
    owner: "pipeline",
    blurb: "The works, editions and page-level citations that claims rest on. Competing dated claims about narrators and events are designed but not built yet (see the planned tables).",
    tables: [
      { name: "bibliographic_works", kind: "table", purpose: "The works cited as evidence, with author and OpenITI reference." },
      { name: "editions", kind: "table", purpose: "Specific editions of a work with publisher, locator scheme and rights status." },
      { name: "citations", kind: "table", purpose: "A cited volume, page or locator in an edition. It counts as a citation only when live and reviewed." }
    ],
    mermaid: `erDiagram
  bibliographic_works {
    text id PK
    text title
    text author
    text author_narrator_id FK
    text tradition_id FK
    int author_death_year_hijri
    text openiti_uri
  }
  editions {
    text id PK
    text work_id FK
    text editor
    text publisher
    text year
    text locator_scheme
    text rights_status
  }
  citations {
    text id PK
    text work_id FK
    text edition_id FK
    text volume
    text page
    text locator
    text review_state
  }
  bibliographic_works ||--o{ editions : published
  bibliographic_works ||--o{ citations : cited
  editions |o--o{ citations : located
  narrators |o--o{ bibliographic_works : wrote
  traditions |o--o{ bibliographic_works : belongs
  bibliographic_works |o--o{ collections : describes
`
  },
  {
    id: "history",
    name: "History",
    owner: "curation",
    blurb: "Places and historical events, and their links to narrators, so a narrator's life can be set against the events of their time. Today only a small uncited seed exists.",
    tables: [
      { name: "locations", kind: "table", purpose: "Places with coordinates and a verification status." },
      { name: "historical_events", kind: "table", purpose: "Events with Hijri and Gregorian years and a publish gate (verified, cited, marked ready), enforced by a database constraint." },
      { name: "narrator_events", kind: "table", purpose: "Link between a narrator and an event with a role." },
      { name: "narrator_locations", kind: "table", purpose: "Link between a narrator and a place as born, died or resided." }
    ],
    mermaid: `erDiagram
  locations {
    text id PK
    text name
    text modern_country
    double latitude
    double longitude
    text verification_status
    text origin
  }
  historical_events {
    text id PK
    text title
    int start_year_hijri
    int end_year_hijri
    text category
    text location_id FK
    bool publication_ready
    text citation_id FK
  }
  narrator_events {
    int id PK
    text narrator_id FK
    text event_id FK
    text role
  }
  narrator_locations {
    int id PK
    text narrator_id FK
    text location_id FK
    text relation
  }
  locations |o--o{ historical_events : hosts
  narrators ||--o{ narrator_events : joins
  historical_events ||--o{ narrator_events : involves
  narrators ||--o{ narrator_locations : tied
  locations ||--o{ narrator_locations : places
  citations |o--o{ historical_events : cites
`
  },
  {
    id: "commentary",
    name: "Commentary",
    owner: "curation",
    blurb: "Scholarly commentary attached to reports and narrators, with a publish status. Public pages show published commentary only.",
    tables: [
      { name: "commentaries", kind: "table", purpose: "Commentary text with author, source work, citation and a proposed, verified or published status." },
      { name: "commentary_hadiths", kind: "table", purpose: "Link from a commentary to a report, bound to the hash of the Arabic it was written against." },
      { name: "commentary_narrators", kind: "table", purpose: "Link from a commentary to a narrator." }
    ],
    mermaid: `erDiagram
  commentaries {
    text id PK
    text type
    text text
    text author
    text source_work
    text citation_id FK
    text status
    text origin
  }
  commentary_hadiths {
    int id PK
    text commentary_id FK
    text hadith_id FK
    text bound_arabic_sha256
  }
  commentary_narrators {
    int id PK
    text commentary_id FK
    text narrator_id FK
  }
  commentaries ||--o{ commentary_hadiths : annotates
  hadiths ||--o{ commentary_hadiths : discussed
  commentaries ||--o{ commentary_narrators : mentions
  narrators ||--o{ commentary_narrators : discussed
  citations |o--o{ commentaries : cites
`
  },
  {
    id: "comparative",
    name: "Comparative study",
    owner: "curation",
    blurb: "Comparison of reports with other religious traditions: faiths, schools, source texts, parallels and motif tags. New parallels start as proposed.",
    tables: [
      { name: "religious_traditions", kind: "table", purpose: "The open set of faiths used for comparison, distinct from the four hadith traditions." },
      { name: "schools_of_thought", kind: "table", purpose: "Seeded taxonomy of theological schools and madhhabs." },
      { name: "source_texts", kind: "table", purpose: "Texts from other traditions that a report may parallel." },
      { name: "cross_parallels", kind: "table", purpose: "A claimed parallel between a report and a source text, bound to the report's Arabic hash, with a review status and the classical Isra'iliyyat classification." },
      { name: "motif_tags", kind: "table", purpose: "Thematic tags such as eschatology or creation." },
      { name: "hadith_motif_tags", kind: "table", purpose: "Link between a report and a motif tag." },
      { name: "parallel_motif_tags", kind: "table", purpose: "Link between a parallel and a motif tag." },
      { name: "narrator_religious_traditions", kind: "table", purpose: "Link between a narrator and a religious tradition." },
      { name: "location_religious_traditions", kind: "table", purpose: "Link between a place and a religious tradition." }
    ],
    mermaid: `erDiagram
  religious_traditions {
    text id PK
    text name
    text name_arabic
    text research_faith_code UK
  }
  schools_of_thought {
    text id PK
    text name
    text category
    text parent_school_id FK
    text religious_tradition_id FK
    text tradition_id FK
  }
  source_texts {
    text id PK
    text religious_tradition_id FK
    text title
    text author
    text canonical_reference UK
  }
  cross_parallels {
    text id PK
    text hadith_id FK
    text source_text_id FK
    text religious_tradition_id FK
    text parallel_type
    text isra_iliyyat_status
    text status
    text source_translation_id FK
  }
  motif_tags {
    text id PK
    text name
    text category
    text origin
  }
  hadith_motif_tags {
    int id PK
    text hadith_id FK
    text motif_tag_id FK
  }
  parallel_motif_tags {
    int id PK
    text parallel_id FK
    text motif_tag_id FK
  }
  narrator_religious_traditions {
    int id PK
    text narrator_id FK
    text religious_tradition_id FK
  }
  location_religious_traditions {
    int id PK
    text location_id FK
    text religious_tradition_id FK
  }
  religious_traditions ||--o{ schools_of_thought : groups
  schools_of_thought |o--o{ schools_of_thought : parents
  traditions |o--o{ schools_of_thought : aligns
  religious_traditions ||--o{ source_texts : owns
  hadiths ||--o{ cross_parallels : parallels
  source_texts ||--o{ cross_parallels : cited
  religious_traditions ||--o{ cross_parallels : compares
  translations |o--o{ cross_parallels : read
  hadiths ||--o{ hadith_motif_tags : tagged
  motif_tags ||--o{ hadith_motif_tags : tags
  cross_parallels ||--o{ parallel_motif_tags : tagged
  motif_tags ||--o{ parallel_motif_tags : tags
  narrators ||--o{ narrator_religious_traditions : belongs
  religious_traditions ||--o{ narrator_religious_traditions : includes
  locations ||--o{ location_religious_traditions : hosts
  religious_traditions ||--o{ location_religious_traditions : includes
`
  },
  {
    id: "operations",
    name: "Operations",
    owner: "operations",
    blurb: "The record of every data load and the append-only audit trail of every curated change. Every pipeline table points back to the loads that created, changed or retired its rows.",
    tables: [
      { name: "dataset_versions", kind: "table", purpose: "One row per load: input hashes, counts, release class, the current-version flag, and the owner's recorded preview approval (all three approval fields or none)." },
      { name: "curation_audit", kind: "table", purpose: "Append-only record of every curated write: who, what, before and after, written in the same transaction as the change." }
    ],
    mermaid: `erDiagram
  dataset_versions {
    text id PK
    text bundle_version
    text release_class
    text load_status
    bool is_current
    text public_override_by
    timestamptz started_at
    timestamptz completed_at
  }
  curation_audit {
    int id PK
    timestamptz occurred_at
    text actor
    text action
    text entity_type
    text entity_id
    jsonb before
    jsonb after
  }
  dataset_versions ||--o{ hadiths : loads
  dataset_versions ||--o{ chain_mentions : loads
  dataset_versions ||--o{ chain_mention_candidates : loads
  dataset_versions ||--o{ translations : loads
`
  },
  {
    id: "public-views",
    name: "Public views",
    owner: "derived",
    blurb: "What a public page may read. Pages never read the base tables for public content, so the rights, review and publish gates live in these views.",
    tables: [
      { name: "public_hadiths", kind: "view", purpose: "Reports of a live collection whose rights are cleared (or under the recorded preview approval) in a complete load." },
      { name: "public_translations", kind: "view", purpose: "Reviewed, hash-bound English on public reports. Machine candidates are never in it." },
      { name: "public_chain_links", kind: "view", purpose: "Every name of a public chain as written; the narrator is filled in only where the link is verified." },
      { name: "public_chain_mention_candidates", kind: "view", purpose: "Every identity candidate of a public name with its basis, and whether that basis is one that may verify." },
      { name: "published_historical_events", kind: "view", purpose: "Events that pass the publish gate, with start and end years for timeline overlap." }
    ],
    mermaid: `erDiagram
  public_hadiths {
    text id PK
    text record_id
    text collection_id
    text tradition_id
    text text_ar
    text arabic_sha256
    text chain_status
    text grading_status
  }
  public_translations {
    text id PK
    text hadith_id
    text language
    text text
    text state
    text arabic_sha256
  }
  public_chain_links {
    text id PK
    text chain_id
    text hadith_id
    int position
    text surface_ar
    bool is_link
    text narrator_id
    real confidence
  }
  public_chain_mention_candidates {
    text mention_id
    text chain_id
    text hadith_id
    text narrator_id
    text basis
    bool verified_basis
  }
  published_historical_events {
    text id PK
    text title
    int event_start
    int event_end
    bool publication_ready
  }
  hadiths ||--o| public_hadiths : gated
  translations ||--o| public_translations : gated
  chain_mentions ||--o| public_chain_links : exposes
  chain_mention_candidates ||--o| public_chain_mention_candidates : exposes
  historical_events ||--o| published_historical_events : gated
  public_hadiths ||--o{ public_chain_links : shows
  public_hadiths ||--o{ public_translations : shows
`
  }
];

window.ERD_PLANNED = [
  {
    id: "planned-candidates",
    name: "Candidate streams and vectors",
    owner: "planned",
    basis: "Designed in data-architecture.md section 5.14; each table is created with the feature that first writes it.",
    blurb: "Machine output kept apart from reviewed data, and derived embeddings. Nothing here is built yet.",
    tables: [
      { name: "translation_candidates", kind: "table", purpose: "Machine or unknown-provenance English rows, read only in reviewer mode, bound by hash to the Arabic." },
      { name: "resolution_review_units", kind: "table", purpose: "The ranked review queue of unidentified names, with the evidence for each." },
      { name: "hadith_embeddings", kind: "table", purpose: "Derived meaning-vectors per report, model and input kind, for finding similar reports." }
    ],
    mermaid: `erDiagram
  translation_candidates {
    text id PK
    text hadith_id FK
    text candidate_source
    text state
    text arabic_sha256
    text dataset_version_id FK
  }
  resolution_review_units {
    text unit_id PK
    text scope
    text surface_normalized
    int occurrences
    int rows_unblocked
    jsonb candidates
    text dataset_version_id FK
  }
  hadith_embeddings {
    text hadith_id PK
    text model
    text input_kind
    text tradition_id FK
    bool is_public
    halfvec embedding
    text dataset_version_id FK
  }
  hadiths ||--o{ translation_candidates : proposes
  dataset_versions ||--o{ translation_candidates : loaded
  collections ||--o{ resolution_review_units : queues
  traditions ||--o{ resolution_review_units : classifies
  dataset_versions ||--o{ resolution_review_units : loaded
  hadiths ||--o{ hadith_embeddings : embedded
  traditions ||--o{ hadith_embeddings : filters
  dataset_versions ||--o{ hadith_embeddings : loaded
`
  },
  {
    id: "planned-claims",
    name: "Cited claims and cross-authority identity",
    owner: "planned",
    basis: "Designed in data-architecture.md section 5.14; created with their first writer.",
    blurb: "Competing, cited claims about narrators, events and periods; named eras; and human-confirmed identity between narrators from different authorities. Nothing here is built yet.",
    tables: [
      { name: "biographical_assertions", kind: "table", purpose: "Cited, competing claims about a narrator's dates, places and generation, kept as separate rows." },
      { name: "temporal_assertions", kind: "table", purpose: "Cited dating claims about an event, epoch or collection." },
      { name: "epochs", kind: "table", purpose: "Named historical periods with an overview; the missing era layer of the historical context." },
      { name: "narrator_same_as", kind: "table", purpose: "Human-confirmed identity between narrators from different key spaces, for example a future Imami authority." }
    ],
    mermaid: `erDiagram
  biographical_assertions {
    text id PK
    text narrator_id FK
    text predicate
    int year_min
    int year_max
    text citation_id FK
    text supersedes_assertion_id FK
    text review_state
  }
  temporal_assertions {
    text id PK
    text event_id
    text epoch_id
    text collection_id FK
    text predicate
    int year_min
    text citation_id FK
    text review_state
  }
  epochs {
    text id PK
    text name
    int start_year_hijri
    int end_year_hijri
    bool publication_ready
    text citation_id FK
  }
  narrator_same_as {
    text id PK
    text narrator_id_a FK
    text narrator_id_b FK
    text citation_id FK
    text reviewer
  }
  narrators ||--o{ biographical_assertions : claimed
  citations ||--o{ biographical_assertions : supports
  biographical_assertions |o--o{ biographical_assertions : supersedes
  collections |o--o{ temporal_assertions : dated
  citations ||--o{ temporal_assertions : supports
  temporal_assertions |o--o{ temporal_assertions : supersedes
  citations |o--o{ epochs : cites
  narrators ||--o{ narrator_same_as : matches
  citations |o--o{ narrator_same_as : cites
`
  },
  {
    id: "correspondence",
    name: "Report correspondence",
    owner: "planned",
    basis: "Proposed in datasets/hadith-data/diagnostics/report-correspondence/README.md; not yet in the design document.",
    blurb: "Links between tellings of the same report across works and traditions, at the level of the report. Each telling keeps its own chain, tradition and source. Machine-found pairs and human decisions are separate tables.",
    tables: [
      { name: "report_correspondence_candidates", kind: "table", purpose: "Machine-found pairs of reports with the same or overlapping wording, with scores and a cluster; reviewer mode only." },
      { name: "report_correspondence_cluster_members", kind: "table", purpose: "Which reports belong to which cluster of tellings, per method version." },
      { name: "report_correspondence_decisions", kind: "table", purpose: "A reviewer's confirmed, rejected or uncertain decision on a pair, bound to the hash of both Arabic texts so a changed text is re-queued." }
    ],
    mermaid: `erDiagram
  report_correspondence_candidates {
    text id PK
    text hadith_id_a FK
    text hadith_id_b FK
    text relation_class
    real jaccard
    text cluster_id
    text basis
    text method_version
  }
  report_correspondence_cluster_members {
    text method_version PK
    text hadith_id FK
    text cluster_id
    text star_centre
  }
  report_correspondence_decisions {
    text id PK
    text hadith_id_a FK
    text hadith_id_b FK
    text decision
    text reviewed_relation
    text citation_id FK
    text decided_by
    timestamptz decided_at
  }
  hadiths ||--o{ report_correspondence_candidates : first
  hadiths ||--o{ report_correspondence_candidates : second
  hadiths ||--o{ report_correspondence_cluster_members : member
  hadiths ||--o{ report_correspondence_decisions : decided
  report_correspondence_cluster_members }o--o{ report_correspondence_candidates : groups
  citations |o--o{ report_correspondence_decisions : cites
  dataset_versions ||--o{ report_correspondence_candidates : loaded
`
  },
  {
    id: "contribution",
    name: "Contribution",
    owner: "planned",
    basis: "Open Scholarly Contribution System plan (March 2026); data-architecture.md section 5.15. Columns are a proposal.",
    blurb: "Contributor accounts, endorsements, submissions, peer review and bulk collection uploads. They replace the small fixed list of named curators that access control starts with.",
    tables: [
      { name: "contributors", kind: "table", purpose: "A person's scholarly profile: name, institution, areas of expertise, and role (reader, contributor, reviewer, editor, admin)." },
      { name: "contributor_endorsements", kind: "table", purpose: "One scholar vouching for another in a named field. The chain of endorsements is public. The name \"ijaza\" for this is an open question (see the Contribution system section)." },
      { name: "submissions", kind: "table", purpose: "One proposed contribution: its type, what it is about, its content, and its status from draft to published or rejected." },
      { name: "submission_reviews", kind: "table", purpose: "A reviewer's verdict and notes on a submission." },
      { name: "submission_comments", kind: "table", purpose: "The discussion between reviewer and contributor." },
      { name: "collection_imports", kind: "table", purpose: "A bulk upload: file hash, validation report, and the dataset version it became." }
    ],
    mermaid: `erDiagram
  contributors {
    uuid id PK
    text display_name
    text email UK
    text role
    text institution
    timestamptz retired_at
  }
  contributor_endorsements {
    uuid id PK
    uuid endorser_id FK
    uuid contributor_id FK
    text field
    timestamptz endorsed_at
  }
  submissions {
    uuid id PK
    uuid contributor_id FK
    text kind
    text status
    text target_type
    text target_id
    jsonb content
    uuid supersedes_id FK
  }
  submission_reviews {
    uuid id PK
    uuid submission_id FK
    uuid reviewer_id FK
    text verdict
    timestamptz reviewed_at
  }
  submission_comments {
    uuid id PK
    uuid submission_id FK
    uuid author_id FK
    uuid parent_id FK
    text body
  }
  collection_imports {
    uuid id PK
    uuid submission_id FK
    text file_sha256
    jsonb validation_report
    text dataset_version_id FK
  }
  contributors ||--o{ contributor_endorsements : endorses
  contributors ||--o{ submissions : submits
  submissions ||--o{ submission_reviews : receives
  contributors ||--o{ submission_reviews : writes
  submissions ||--o{ submission_comments : discussed
  submissions ||--o| collection_imports : uploads
  submissions ||--o{ submissions : supersedes
  collection_imports }o--|| dataset_versions : becomes
  submissions }o--o{ citations : cites
  contributors ||--o{ curation_audit : acts
`
  }
];
