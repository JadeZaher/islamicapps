window.ERD = [
  {
    name: "Corpus",
    owner: "pipeline",
    blurb: "The hadith corpus itself: traditions, source works, browsing structure, Arabic reports and their English translations.",
    tables: [
      { name: "traditions", purpose: "The closed set of four hadith traditions and their grading schemes.", ships: "launch" },
      { name: "sources", purpose: "The upstream provider a row came from.", ships: "launch" },
      { name: "collections", purpose: "One row per source work (34 today); the Neo4j Source node.", ships: "launch" },
      { name: "collection_rights", purpose: "The owner's per-work publication and English-policy decision; a reload never touches it.", ships: "launch" },
      { name: "books", purpose: "Book-level browsing structure inside a collection.", ships: "launch" },
      { name: "chapters", purpose: "Chapter-level browsing structure inside a collection.", ships: "launch" },
      { name: "hadiths", purpose: "One row per report, with Arabic stored byte for byte and derived status facets.", ships: "launch" },
      { name: "translations", purpose: "Canonical English translations bound by hash to the Arabic they rendered.", ships: "launch" },
      { name: "translation_candidates", purpose: "Machine or unknown-provenance English rows, read only in reviewer mode.", ships: "later" }
    ],
    mermaid: `erDiagram
  traditions {
    text id PK
    text code UK
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
    text name
    int sort_key UK
    text tradition_id FK
    text source_id FK
  }
  collection_rights {
    text collection_id PK
    text rights_status
    text english_policy
    text citation
  }
  books {
    text id PK
    text collection_id FK
    text number
    text name
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
    text arabic_sha256
  }
  translation_candidates {
    text id PK
    text hadith_id FK
    text candidate_source
    text state
    text arabic_sha256
    text dataset_version_id FK
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
  hadiths ||--o{ translation_candidates : proposes
  dataset_versions ||--o{ translation_candidates : loaded
`
  },
  {
    name: "Narrators",
    owner: "pipeline",
    blurb: "Narrator identity from the lexicon: names, lexicon-claimed biography, name variants and declared teacher links, with no verdicts.",
    tables: [
      { name: "narrators", purpose: "Identity only; never a verdict, grade or reliability column.", ships: "launch" },
      { name: "narrator_lexicon_profiles", purpose: "Everything the lexicon claims about a narrator, kept as unverified lexicon claim.", ships: "launch" },
      { name: "narrator_aliases", purpose: "Canonical names now and registry segments later, for matching surfaces.", ships: "launch" },
      { name: "narrator_teachers", purpose: "Teacher and student links declared by the lexicon, used for candidate ranking.", ships: "launch" }
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
  }
  narrator_lexicon_profiles {
    text narrator_id PK
    text bundle_id UK
    text raw_profile_sha256
    text bio
    int birth_year_hijri
    int death_year_hijri
    text review_state
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
    name: "Isnad",
    owner: "pipeline",
    blurb: "Chains of transmission as written, the human decisions that resolve each name to a narrator, and the views derived from verified links.",
    tables: [
      { name: "chains", purpose: "One row per branch (tahwil) of a report.", ships: "launch" },
      { name: "chain_mentions", purpose: "The name as written at one position of one branch, with its resolution state.", ships: "launch" },
      { name: "chain_absence_dispositions", purpose: "Records that a report or whole work has no isnad by nature (curation).", ships: "launch" },
      { name: "narrator_surface_decisions", purpose: "A human identity decision replayed onto every matching mention (curation).", ships: "launch" },
      { name: "resolution_review_units", purpose: "The ranked offline review queue of unresolved surfaces (candidate stream).", ships: "later" },
      { name: "narrator_transmissions", purpose: "Materialized view of who narrated from whom, from consecutive verified links only.", ships: "launch" },
      { name: "narrator_lifespans", purpose: "View of birth and death ranges per narrator, never collapsing competing claims.", ships: "launch" }
    ],
    mermaid: `erDiagram
  chains {
    text id PK
    text hadith_id FK
    int branch
    int length
    bool resolved
    int verified_link_count
  }
  chain_mentions {
    text id PK
    text chain_id FK
    text hadith_id FK
    int position
    text surface_ar
    text resolution
    text narrator_id FK
    text decision_id FK
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
  narrator_transmissions {
    text student_id FK
    text teacher_id FK
    int hadith_count
    int occurrence_count
    text temporal_plausibility
  }
  narrator_lifespans {
    text narrator_id FK
    int birth_min
    int birth_max
    int death_min
    int death_max
    bool disputed
    text basis
  }
  hadiths ||--o{ chains : has
  chains ||--o{ chain_mentions : lists
  hadiths ||--o{ chain_mentions : contains
  narrators |o--o{ chain_mentions : resolves
  narrator_surface_decisions |o--o{ chain_mentions : decides
  narrators |o--o{ narrator_surface_decisions : targets
  collections ||--o{ narrator_surface_decisions : scopes
  collections |o--o{ chain_absence_dispositions : excuses
  hadiths |o--o{ chain_absence_dispositions : excuses
  citations |o--o{ chain_absence_dispositions : cites
  citations |o--o{ narrator_surface_decisions : cites
  collections ||--o{ resolution_review_units : queues
  traditions ||--o{ resolution_review_units : classifies
  dataset_versions ||--o{ resolution_review_units : loaded
  chain_mentions }o--o{ narrator_transmissions : derives
  narrators ||--o{ narrator_transmissions : links
  narrators ||--o| narrator_lifespans : spans
  narrator_lifespans |o--o{ narrator_transmissions : bounds
`
  },
  {
    name: "Assessments and biography",
    owner: "curation",
    blurb: "Tradition-scoped grades on hadiths, verdicts on narrators, curated biographies and cross-authority identity links.",
    tables: [
      { name: "hadith_assessments", purpose: "Pipeline-owned, tradition-scoped, multi-valued and cited grades on a hadith.", ships: "launch" },
      { name: "narrator_assessments", purpose: "Curation-owned verdicts on a narrator, always scoped to a tradition.", ships: "launch" },
      { name: "narrator_bios", purpose: "Curated biography fields, one row per narrator.", ships: "launch" },
      { name: "narrator_same_as", purpose: "Human-confirmed identity between narrators across key spaces.", ships: "later" }
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
    text citation_id FK
    text status
  }
  narrator_bios {
    text narrator_id PK
    bool is_prophet
    text tabaqah_class
    text bio_summary
    text citation_id FK
    text status
  }
  narrator_same_as {
    text id PK
    text narrator_id_a FK
    text narrator_id_b FK
    text citation_id FK
    text reviewer
  }
  hadiths ||--o{ hadith_assessments : graded
  traditions ||--o{ hadith_assessments : scopes
  citations |o--o{ hadith_assessments : cites
  narrators ||--o{ narrator_assessments : judged
  traditions |o--o{ narrator_assessments : scopes
  citations |o--o{ narrator_assessments : cites
  narrators ||--o| narrator_bios : described
  citations |o--o{ narrator_bios : cites
  narrators ||--o{ narrator_same_as : matches
  citations |o--o{ narrator_same_as : cites
`
  },
  {
    name: "Evidence and citations",
    owner: "pipeline",
    blurb: "Cited works, editions and citations, plus competing dated claims about narrators, events, epochs and collections.",
    tables: [
      { name: "bibliographic_works", purpose: "The works cited as evidence, with author and OpenITI reference.", ships: "launch" },
      { name: "editions", purpose: "Specific editions of a work with publisher, locator scheme and rights status.", ships: "launch" },
      { name: "citations", purpose: "A cited volume, page or locator in an edition; public rows need a reviewed live citation.", ships: "launch" },
      { name: "biographical_assertions", purpose: "Cited, competing claims about a narrator's dates, places and generation.", ships: "later" },
      { name: "temporal_assertions", purpose: "Cited dating claims about an event, epoch or collection.", ships: "later" }
    ],
    mermaid: `erDiagram
  bibliographic_works {
    text id PK
    text title
    text author
    text author_narrator_id FK
    text tradition_id FK
    int author_death_year_hijri
  }
  editions {
    text id PK
    text work_id FK
    text editor
    text publisher
    text year
    text rights_status
  }
  citations {
    text id PK
    text work_id FK
    text edition_id FK
    text volume
    text page
    text review_state
  }
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
  bibliographic_works ||--o{ editions : published
  bibliographic_works ||--o{ citations : cited
  editions |o--o{ citations : located
  narrators |o--o{ bibliographic_works : wrote
  traditions |o--o{ bibliographic_works : belongs
  narrators ||--o{ biographical_assertions : claimed
  citations ||--o{ biographical_assertions : supports
  biographical_assertions |o--o{ biographical_assertions : supersedes
  collections |o--o{ temporal_assertions : dated
  citations ||--o{ temporal_assertions : supports
  temporal_assertions |o--o{ temporal_assertions : supersedes
`
  },
  {
    name: "History",
    owner: "curation",
    blurb: "Locations, historical events and epochs, their links to narrators, and the publish-gated events view.",
    tables: [
      { name: "locations", purpose: "Places with coordinates and verification status.", ships: "launch" },
      { name: "historical_events", purpose: "Events with hijri and gregorian years, a publish gate and an embedded citation.", ships: "launch" },
      { name: "epochs", purpose: "Named historical periods with an overview.", ships: "later" },
      { name: "narrator_events", purpose: "Link between a narrator and an event with a role.", ships: "launch" },
      { name: "narrator_locations", purpose: "Link between a narrator and a place as born, died or resided.", ships: "launch" },
      { name: "published_historical_events", purpose: "View of events that pass the publish gate, with start and end years for timeline overlap.", ships: "launch" }
    ],
    mermaid: `erDiagram
  locations {
    text id PK
    text name
    text modern_country
    double latitude
    double longitude
    text verification_status
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
  epochs {
    text id PK
    text name
    int start_year_hijri
    int end_year_hijri
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
  published_historical_events {
    text id FK
    text title
    int event_start
    int event_end
  }
  locations |o--o{ historical_events : hosts
  narrators ||--o{ narrator_events : joins
  historical_events ||--o{ narrator_events : involves
  narrators ||--o{ narrator_locations : tied
  locations ||--o{ narrator_locations : places
  historical_events ||--o| published_historical_events : gates
  citations |o--o{ historical_events : cites
  citations |o--o{ epochs : cites
`
  },
  {
    name: "Commentary",
    owner: "curation",
    blurb: "Scholarly commentary attached to hadiths and narrators, with a publish status.",
    tables: [
      { name: "commentaries", purpose: "Commentary text with author, source, citation and publish status.", ships: "launch" },
      { name: "commentary_hadiths", purpose: "Link from a commentary to a hadith, bound to that hadith's Arabic hash.", ships: "launch" },
      { name: "commentary_narrators", purpose: "Link from a commentary to a narrator.", ships: "launch" }
    ],
    mermaid: `erDiagram
  commentaries {
    text id PK
    text type
    text text
    text author
    text citation_id FK
    text status
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
    name: "Comparative study",
    owner: "curation",
    blurb: "Comparison of hadiths with other religious traditions: faiths, schools, source texts, parallels and motif tags.",
    tables: [
      { name: "religious_traditions", purpose: "The open set of faiths used for comparison, distinct from the four hadith traditions.", ships: "launch" },
      { name: "schools_of_thought", purpose: "Seeded taxonomy of theological schools and madhhabs.", ships: "launch" },
      { name: "source_texts", purpose: "Texts from other traditions that a hadith may parallel.", ships: "launch" },
      { name: "cross_parallels", purpose: "A claimed parallel between a hadith and a source text, with a review status.", ships: "launch" },
      { name: "motif_tags", purpose: "Thematic tags such as eschatology or creation.", ships: "launch" },
      { name: "hadith_motif_tags", purpose: "Link between a hadith and a motif tag.", ships: "launch" },
      { name: "parallel_motif_tags", purpose: "Link between a parallel and a motif tag.", ships: "launch" },
      { name: "narrator_religious_traditions", purpose: "Link between a narrator and a religious tradition.", ships: "launch" },
      { name: "location_religious_traditions", purpose: "Link between a location and a religious tradition.", ships: "launch" }
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
    name: "Operations and vectors",
    owner: "operations",
    blurb: "Load records, the curation audit trail and the derived hadith embeddings.",
    tables: [
      { name: "dataset_versions", purpose: "One row per load, with hashes, counts, release class and the current-version flag.", ships: "launch" },
      { name: "curation_audit", purpose: "Append-only record of every curated change, written in the same transaction.", ships: "launch" },
      { name: "hadith_embeddings", purpose: "Derived halfvec embeddings per hadith, model and input kind.", ships: "later" }
    ],
    mermaid: `erDiagram
  dataset_versions {
    text id PK
    text bundle_version
    text release_class
    text load_status
    bool is_current
    timestamptz started_at
  }
  curation_audit {
    int id PK
    timestamptz occurred_at
    text actor
    text action
    text entity_type
    text entity_id
    jsonb after
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
  hadiths ||--o{ hadith_embeddings : embedded
  traditions ||--o{ hadith_embeddings : filters
  dataset_versions ||--o{ hadith_embeddings : loaded
`
  }
];
