# 03 - Actual v2 graph data model (as written by the regen pipeline)

Date: 2026-11-21
Intent: reconstruct the real Neo4j v2 model from loader code so a Postgres/Drizzle schema can reproduce it faithfully. Read-only investigation. All paths relative to repo root `c:/Users/atooz/Programming/experiments/islamicapps`.

Primary sources:
- `src/scripts/lib/regen/batch-loaders.ts` (BL) - the fullregen write path (Hadith, Source, Chain, INCLUDES, NARRATED_FROM, Assessment, NameMention)
- `src/scripts/lib/regen/load-narrators.ts` (LN), `dataset-version.ts` (DV), `tombstone.ts`, `temporal-plausibility.ts`, `load-chain.ts` (buildTier1Resolution), `mode-fullregen.ts` (MF), `mode-test.ts` (guardrails)
- `src/lib/db/schema.ts` (constraints + indexes), `src/lib/db/AGENTS.md`, `src/scripts/lib/regen/AGENTS.md`
- seeds: `seed-narrator-bios-phase0.ts`, `seed-historical-data.ts`, `seed-taxonomy.ts`; constants: `src/lib/constants/{sources,traditions,grade-taxonomy}.ts`

NOTE: row-level loaders (`load-hadith.ts`, `load-chain.ts` row path, `assessment.ts loadAssessment`) are the LEGACY path (positional `dataset_row_id` / `pipeline_key` identity). `mode-fullregen.ts` uses only `batch-loaders.ts` (MF:1655-1664). Treat BL as the authoritative model.

---------------------------------------------------------------------------
## 1. Short answers to the specific questions

**What does :Assessment attach to?**
- The fullregen loader attaches it to **:Hadith only**: `MATCH (target:Hadith { record_id: row.target_key })` (BL:588), `MERGE (target)-[ha:HAS_ASSESSMENT]->(a)` (BL:605), `MERGE (a)-[us:UNDER_SCHEME]->(rt)` (BL:607).
- The type signature allows **Hadith OR Narrator** (`assessment.ts:46-50`, `targetLabel: 'Hadith'|'Narrator'`), and the one-shot legacy migration `migrateScalarAssessments()` (assessment.ts:184-302, called from MF) writes Narrator-targeted Assessments (`pipeline_key = 'scholar_indx:<n>::unspecified_legacy'`, `tradition='unspecified_legacy'`, `grade_scheme='unspecified'`, `migrated_from='Narrator.reliability'`; assessment.ts:205-217) and Hadith-targeted ones (`<keyProp>:<val>::<tradition>_legacy`, `migrated_from='Hadith.grade'`; 262-274). Those legacy Narrator assessments get NO `UNDER_SCHEME` edge and are not tradition-scoped.
- Design target: `(:Hadith|:Narrator)-[:HAS_ASSESSMENT]->(:Assessment)-[:UNDER_SCHEME]->(:ReligiousTradition)` (assessment.ts:16). In v2 data as regenerated, narrator-level grades are NOT materialized as Assessments; the raw rawi CSV `grade` is stashed as `Narrator._raw_grade` breadcrumb (LN:11, 28-31, TODO LN:13-14 to fan it out later). Phase-0 `reliability_consensus` lives directly on Narrator (see 3.2).
- So for the new store: model Assessment as a polymorphic target (hadith_id nullable XOR narrator_id nullable, or two tables), tradition-scoped, but only the hadith side is populated by the current pipeline.

**How is tradition scoping represented?**
- Closed vocabulary of 4: `Sunni | Imami | Zaydi | Ibadi` (`io.ts:56`, `constants/traditions.ts:2`). Canonicalization map in `io.ts:161+` (e.g. "shia imami", "twelver" -> Imami; "shia zaydi" -> Zaydi). Read-side aliases in `traditions.ts:4-9` (Imami aliases: 'Shia Imami','Shia'; Zaydi: 'Shia Zaydi').
- Three simultaneous representations of the same fact:
  1. Scalar `Hadith.tradition` (string) and `Source.tradition` (string) - BL:176, 236.
  2. Edge `(:Hadith)-[:FROM_TRADITION]->(:ReligiousTradition {name})` - BL:311. Also `(:CrossCulturalParallel)-[:FROM_TRADITION]->(:ReligiousTradition)` (comparative/neo4j-commit.ts:203).
  3. `Assessment.tradition` scalar + `(:Assessment)-[:UNDER_SCHEME]->(:ReligiousTradition)` (BL:594-607). Plus `Assessment.grade_scheme` enum: `sunni_7tier | imami_4tier | zaydi_3tier | ibadi_2tier | unspecified` (assessment.ts:44, 72-77).
- Grades are tradition-scoped by construction: Assessment key includes tradition (see 2.8). Every hadith gets exactly one Assessment per tradition (4 rows/hadith, BL:569-581), real ones where a grade exists, `no_extant_evaluation` placeholder otherwise -> this is the 88% placeholder share.
- ReligiousTradition is ALSO used for comparative religions (Islam, Judaism, Christianity, Zoroastrianism - seed-taxonomy.ts:45-74). The 4 hadith traditions are MERGEd by `name` (MF:172, assessment.ts:85-93). Names for the hadith set are exactly 'Sunni','Imami','Zaydi','Ibadi'; the taxonomy seed's school names 'Shia Imami'/'Shia Zaydi' are a different node type (SchoolOfThought).
- SchoolOfThought pseudo-traditions are DEPRECATED: FR-1.8 migration (MF:150-205) writes `FROM_TRADITION` for every `IN_SCHOOL` edge to a pseudo school named in {Sunni,Imami,Zaydi,Ibadi} then tombstones those 4 SchoolOfThought nodes. NOTE name mismatch: seed-taxonomy seeds 'Shia Imami'/'Shia Zaydi' while migration only matches 'Imami'/'Zaydi' (so 'Shia Imami' school is not tombstoned by it). Old `IN_SCHOOL` edges are kept; `graph-actions.ts:1068` still reads `(h)-[:IN_SCHOOL]->(sch:SchoolOfThought)`.
- Source-tradition rule: a Source name appears under exactly ONE tradition (AGENTS.md regen line 11; BL:142-147 throws on conflict).

**How are multi-branch chains and positions stored?**
- Source: CSV column `chain_indx` parsed to `number[][]` - outer = isnad branches (one per tahwil `h` split), inner = scholar_indx ints in order (`io.ts:93-101`). Flat legacy `"1,2,3"` -> `[[1,2,3]]`.
- One `:Chain` node per branch. Key: `pipeline_key = "<record_id>::record_id::<chain_index>"` (BL:375-379 via `buildPipelineKey(...parts).join('::')`, neo4j-helpers.ts:198). `chain_index` = branch ordinal, 0-based (load-chain.ts:274).
- `(:Hadith)-[:HAS_CHAIN]->(:Chain)` one per branch (BL:450).
- `(:Chain)-[:INCLUDES {position}]->(:Narrator)` where `position` is **0-based position WITHIN the branch**, not global (load-chain.ts:238-240, 257). Relationship identity is `MERGE (ch)-[r:INCLUDES { position: e.position }]->(n)` (BL:462): i.e. unique on (chain, position, narrator); the same narrator at two positions of one chain yields two edges.
- Unresolved ids: if a `chain_indx` id is not in rawis, no INCLUDES is written; instead a NameMention with `surface_form='[chain_indx:<idx>]'` is drafted (load-chain.ts:252-261).
- Chain-level props: `chain_index, confidence (= resolved[0].confidence or 0), extraction_method, source=dvId` (BL:426-439). Method values: `chain_indx_join` (tier 1) or entity-resolution tiers (`regex_sanad`, `lexicon_blocked`, `rerank`, ... via `ErTier`).
- Readers must group by `chain_id` before ordering (src/app/actions/AGENTS.md "Hadith chain reads"); a legacy fallback graph exists (`HAS_VARIATION -> MatnVariation -[:TRANSMITTED_VIA]-> Chain`, graph-actions.ts:268, 379-380) which is read-only compat and NOT written by regen.
- Narrator-to-narrator shortcut `NARRATED_FROM` is derived from consecutive resolved positions only if `teacher.position === student.position + 1` (BL:403-407), direction **student -> teacher**. Deduped per (student,teacher) across the buffer keeping highest confidence (BL:414-416). It is chain-agnostic (global, not scoped to a chain/hadith).

**What is :NameMention vs :Narrator?**
- `:Narrator` = canonical identity from the rawi vocabulary (`all_rawis.csv`), stable key `scholar_indx` (int, from the CSV; constraint `narrator_scholar_indx_unique`, schema.ts:62). ~24,326 rows.
- `:NameMention` = a **per-occurrence, per-chain-position surface string that was NOT resolved to a Narrator** (or is awaiting human resolution). FR-1.4 "NameMention nodes for every unresolved narrator link" (name-mention.ts:26). Key `pipeline_key = "<chainKey>::pos<position>"` (BL:647; name-mention.ts:115). Properties: `id, surface_form, normalized_form (= norm(surface), Arabic diacritic/alef/ya normalization port of Python _norm; name-mention.ts:69-78), position, source(dvId), created_at, updated_at`. Edge: `(:Chain)-[:INCLUDES_MENTION {position, confidence(=0.0), extraction_method('regex_sanad' in batch path), source}]->(:NameMention)` (BL:677-681). It is NOT linked directly to :Hadith or :Narrator at load time.
- Link to Narrator exists only after human review: `(:NameMention)-[:RESOLVES_TO {confidence, extraction_method:'rerank', reviewed_by, reviewed_at, quarantined, created_at}]->(:Narrator)` written by `src/scripts/ingest-er-approved.ts:169-194` from `datasets/hadith-data/er-staging.jsonl`. G-5: no auto SAME_AS/RESOLVES_TO. (`SAME_AS` has no writer in src except guard; edge counts only checked informationally, mode-test.ts:126-145.)
- LATENT BUG to fix in new store: ingest-er matches `m.source_row_id = $rid` (ingest-er-approved.ts:175) and `m.normalized_form`, but the loader never writes `source_row_id` on NameMention (BL:660-681 sets id, surface_form, normalized_form, position, source only). HITL edges can therefore never be created against loader-produced mentions. New schema should key a mention by (chain_id, position) and let ER staging reference mention id / (record_id, chain_index, position).

**What is :DatasetVersion?**
- Provenance/lifecycle node, one per input content hash (constraint `content_hash` unique, schema.ts:110). Not transaction isolation (AGENTS.md regen:35). Properties (DV:460-476, 506-552): `id (uuid), content_hash (sha256 of logical decompressed CSV bytes, unique), release_class ('release'|'non_release'), load_purpose ('release_fullregen'|'dev_fullregen'|'legacy_diff'), release_eligible (bool), non_release (bool), non_release_reason ('' -> null | 'dev_allow_incomplete_data' | 'legacy_diff_mode'), active (bool), load_status ('loading'|'complete'|'non_release_loading'|'non_release_loaded'), expected_record_count, measured_unknown_fraction, attribution_disclaimer (G-3 text), version_label (default 'regen-YYYY-MM-DD'), _per_tradition (JSON string), subcount_sunni/imami/zaydi/ibadi (flattened ints, DV:374-380), created_at, updated_at, completed_at, non_release_loaded_at`.
- Invariants: class/purpose/reason immutable per hash (DV:89-150, 416); release-class only can be activated (`activateDatasetVersion` DV:506-526 sets `active = (id = target.id)` over all versions in one statement, `load_status='complete'`); non-release may never activate (DV:340-342, 540). Exactly one active version expected (mode-test.ts:169-186).
- Edges pointing at it: `(:Hadith)-[:INGESTED_IN {source,confidence,extraction_method}]->(:DatasetVersion)` (BL:309). And almost every node/edge carries `source = <DatasetVersion.id>` as a scalar string (Chain.source, Narrator.source, NameMention.source, Assessment.source, all rel `.source`) - i.e. a soft FK, not an edge. `FROM_SOURCE`, `FROM_TRADITION`, `HAS_CHAIN`, `HAS_ASSESSMENT`, `UNDER_SCHEME`, `INCLUDES`, `NARRATED_FROM`, `INCLUDES_MENTION` all store `.source = dvId`.
- Sibling coordination node: `:FullregenLease {name UNIQUE, owner_token, heartbeat_at, expires_at...}` singleton writer lock (DV:180-310). Infra-only; replace with `pg_advisory_lock`/lease row. Production fullregen requires an EMPTY target apart from the lease (MF:1033-1034, 1057-1064) -> a clean/blue-green load, so new store can simply load into a fresh schema and swap.
- Note `Hadith.created/updated`: because the Hadith MERGE uses `ON MATCH SET` that overwrites every field (BL:261-291), the latest load wins; `source` on Hadith nodes is NOT the dvId (it is the work name, see 2.2).

**Tombstone / soft-delete conventions**
- `src/scripts/lib/regen/tombstone.ts:35-71`: never DETACH DELETE. Set `n.tombstoned = true, n.superseded_by = <DatasetVersion.id>, n.tombstoned_at = datetime()`. Read filter `NOT n.tombstoned = true` (`excludeTombstoned()`, :80). Applies to any label (`tombstone(nodeId...)` generic MATCH (n {id}) ; `tombstoneByKey(label,keyProp,keyValue,dvId)`).
- Actual uses: the 4 pseudo SchoolOfThought nodes (MF:196-202); guardrail/readers filter Narrator/Hadith with `NOT n.tombstoned = true` (mode-test.ts:50, 71, 192, 210; assessment.ts:198, 251).
- Scalar-removal convention (not tombstone): `migrateScalarAssessments` does `REMOVE n.reliability` / `REMOVE h.grade` after migrating (assessment.ts:226-229, 286-289); node kept.
- Exceptions to no-delete: fullregen wipes `INCLUDES`, `NARRATED_FROM`, `INCLUDES_MENTION` relationship types in 50k chunks before reload (MF:1593-1623) (they are derived data); `deleteCommentary` DETACH DELETEs (graph-actions.ts:772). Owner memory rule (feedback_no_delete_backup): never delete data files, back up/move; purge DB only when asked.
- Postgres mapping suggestion: `tombstoned_at timestamptz NULL`, `superseded_by_dataset_version_id uuid NULL` on the tombstonable tables; partial indexes `WHERE tombstoned_at IS NULL`.

**Phase-0 narrator bio fields** (`seed-narrator-bios-phase0.ts`, header 16-36, write 614-636). 21 anchor narrators (the Prophet scholar_indx=1 + ~20 most-cited supernodes), `MATCH (n:Narrator {scholar_indx})` then SET (never creates narrators). All SET unconditionally except death dates:
| Neo4j prop (n.*) | type | note |
|---|---|---|
| is_prophet | bool | true only for scholar_indx 1; bio_* omitted for him; opts out of jarh wa ta'dil |
| is_companion | bool | sahabi flag (Sunni 'adalat al-sahaba) |
| tabaqah | enum text | PROPHET \| SAHABA \| TABIUN \| ATBA_TABIUN \| ATBA_ATBA (overwrites base CSV tabaqah text!) |
| name_english_clean | text | param `name_english_clean`; stored beside, not over, `name_english` |
| name_arabic_clean | text | likewise |
| kunya, nasab, nisba | text null | agnomen / patronymic / affiliation |
| death_date_hijri | int | `coalesce(existing, new)` - fill-if-missing |
| death_date_gregorian | int | `coalesce(existing, new)` |
| geographic_region | text null | OVERWRITES existing |
| bio_summary | text | 2-3 sentence English |
| bio_tadil | text null | NB: Cypher prop is ASCII `bio_tadil` (source field `bio_taʿdīl`) |
| bio_jarh | text null | ASCII `bio_jarh` |
| reliability_consensus | enum text | thiqa \| thiqa_thabt \| ṣadūq \| lā_baʾsa_bihi \| majhūl \| ḍaʿīf \| matrūk \| kadhāb \| mukhtalaf_fīhi \| not_applicable (script header omits lā_baʾsa_bihi) |
| reliability_disagreement | bool | critics conflicted |
| critic_quote_count | int | distinct critics quoted |
| bio_provenance | text | literal 'manual_phase_0' so phases 1-3 skip |
| bio_updated_at | datetime | |
Conflict with G-1: `reliability_consensus` is a scalar verdict on :Narrator. mode-test G-1 only checks `n.reliability` and `n.grade` (mode-test.ts:44-64), so it passes, but spirit of G-1 says verdicts live on tradition-scoped Assessment. Flag for the schema designer: model as narrator_bio table + Sunni-tradition (or `unspecified`) Assessment rows, keeping `bio_provenance`. Also `Narrator.tabaqah` from CSV is free text (raw), whereas phase 0 forces the 5-value enum - a Postgres column should be text with an optional `tabaqah_class` enum.

---------------------------------------------------------------------------
## 2. Node labels written by the regeneration pipeline

Keys in bold. "W" = writing script. dvId = DatasetVersion.id uuid. Neo4j `id` = random uuid created at first MERGE (create-only; surrogate, not stable across full regens).

### 2.1 :Narrator  (W: `load-narrators.ts bulkLoadNarrators`, LN:131-198; enriched by seed-narrator-bios-phase0; read by temporal-plausibility)
- **Stable key: `scholar_indx` (int)**, unique constraint (schema.ts:62), never MERGE on uuid (FR-0.1; mode-test G-2).
- Surrogate: `id` uuid unique (schema.ts:60).
- Base props from `RawiRecord` (io.ts:117-141): `name` (required; Arabic canonical rawi name; on match replaced only if nonblank), `name_english`, `name_arabic`, `_raw_grade` (CSV `grade` breadcrumb, never a verdict), `bio` (text), `birth_date_hijri` int, `birth_date_hijri_raw` text, `birth_date_gregorian` int, `birth_date_gregorian_raw`, `birth_date_source_text`, `birth_place`, `death_date_hijri` int, `death_date_hijri_raw`, `death_date_gregorian` int, `death_date_gregorian_raw`, `death_date_source_text`, `death_place`, `death_reason`, `geographic_region`, `tabaqah` (free text), plus `source` (dvId), `created_at`, `updated_at`.
- `RawiRecord.teachers_inds` / `students_inds` (number[]) exist in the CSV type (io.ts:137-138) but are NOT written by the loader (NARRATED_FROM is derived from chains only).
- Sparse/fill-if-missing rule: optional props only set when present and not in {'', na, n/a, null, none, nan, unknown, -} (LN:27, 112-119); on existing node each optional prop is `CASE WHEN null/blank THEN new ELSE old` (LN:53-64). Base import never replaces a nonblank biography/name/place/date (AGENTS.md regen:39). Canonical year ints accept only exact safe-integer tokens; ranges stay in `*_raw` (AGENTS.md:41). Preflight rejects death<birth and AH/CE pairs >3y from conversion.
- Phase-0 props: see section 1. Legacy props removed/forbidden: `reliability`, `grade` (G-1).
- Indexes (schema.ts:148-154): reliability, tabaqah, name_english, name_arabic, geographic_region, birth_date_hijri, death_date_hijri. NOTE: `birth_year_hijri`/`death_year_hijri` are read-API aliases only (AGENTS.md:41).
- Target model additions (db/AGENTS.md, UNIMPLEMENTED): `:Person` (id unique), `:Narrator`/`:Author` person subtypes, `HAS_BIO_ASSERTION`.

### 2.2 :Hadith  (W: `batch-loaders.ts loadHadithsBatch`, BL:225-291; also mode-enrich adds enrichment fields)
- **Stable key: `record_id` (string, unique, nonblank, trimmed)** (schema.ts:63; BL:227). Surrogate `id` uuid unique. `pipeline_key = "<source>::<hadith_no>"` create-only (buildPipelineKey) - legacy key. `dataset_row_id` (int, positional CSV `id`; compat metadata only; its uniqueness constraint `hadith_dataset_row_id_unique` is retained on populated graphs until all have record_id, schema.ts:130-143; "do not use as migration contract").
- Props (all overwritten on match, BL:261-291): `source` (canonical work name string), `source_work_id`, `source_display_label`, `tradition`, `hadith_id` (source-specific original id), `hadith_no`, `volume`, `chapter`, `chapter_no`, `category`, `text_ar`, `text_en`, `source_record_id`, `provenance_source`, `translation_status`, `translation_source`, `translation_model`, `translation_review_status`, `matn_ar`, `matn_en`, `sanad` (free-text sanad string), `sanad_confidence`, `school`, `chain_type`, `attributed_to`, `narration_level`, `url`, `page_ref`, `created_at`, `updated_at`. All string-typed in the CSV reader except `dataset_row_id`.
- Enrichment: `mode-enrich.ts:68-88` sets any `h[field]` only when empty plus `<field>_source`, `<field>_enriched_at`, `<field>_extraction_method='enrich-jsonl'` (dynamic columns - in Postgres use an `hadith_enrichment(hadith_id, field, value, source, enriched_at, method)` EAV table).
- NOT written by fullregen (legacy/dead in v2): `display_grade`, `transmission_type` (still indexed schema.ts:155-156), `grade`, `reliability`. G-1 forbids scalar grades on Hadith. `grade_value, grade_tradition, grade_source, gradings_full` are consumed only to build Assessments (BL:529-566), never stored on Hadith.
- Release gate on the row (regen AGENTS.md:5-9): unique record_id; nonblank source_record_id, provenance_source, text_ar, text_en; `translation_status == 'complete'` (vocab: complete, missing, model_refusal_or_error, same_as_arabic, copied_input, arabic_leakage, wrong_language, no_english_text, placeholder, suspiciously_short); `translation_review_status` in {human_verified, source_verified}; if translation source/provenance mentions ai/automated/generated/gpt/llm/machine/model/openai/anthropic/claude/gemma/pipeline then `translation_model` must be namespaced `a/b` or `a:b`; every row has >=1 chain branch whose ids exist in rawis; supported tradition + nonblank source; a source maps to one tradition; schema-v2 curation_manifest.json with gates.
- Indexes: display_grade, transmission_type, source, source_work_id, hadith_no, dataset_row_id (schema.ts:155-160).

### 2.3 :Source  (W: loadHadithsBatch step 1, BL:173-185; seed in sources.ts registry)
- **Key: `name` (unique, schema.ts:84)** = canonical work name, e.g. 'Sahih Bukhari', 'Al-Kafi'. Surrogate `id` unique.
- Props: `tradition`, `source_work_id` (null if blank), `source_display_label` (null if blank), `compiler_name` (from `CANONICAL_SOURCES[*].compiler`, else null), `created_at`, `updated_at`. Index `source_work_id`.
- Registry `src/lib/constants/sources.ts`: `SourceEntry {canonical, arabic, displayLabel, aliases?, compiler, tradition, school?}` slug-keyed; ~35 entries (6 Sunni canon + Ahmad + Muwatta + Darimi + Shafi'i musnad; Ibadi Musnad al-Rabi; ~24 Imami works; Zaydi Musnad Zayd; Imami Sahifat al-Rida). Aliases are READ-compat only; shared labels 'Al-Amali' / 'Kitab al-Ghayba' are intentionally unresolved (constants/AGENTS.md). Unregistered work/compiler identities BLOCK release (AGENTS.md:11).
- Edge: `(:Hadith)-[:FROM_SOURCE {source:dvId, confidence:1.0, extraction_method:'unified_csv'}]->(:Source)` (BL:307-308).

### 2.4 :Chain  (W: loadChainsBatch, BL:425-441)
- **Key: `pipeline_key` = `<record_id>::record_id::<chain_index>`** (unique, schema.ts:67). Surrogate `id` uuid.
- Props: `chain_index` int, `source` (dvId), `confidence` float, `extraction_method` string, `created_at`, `updated_at`.
- Edges: `HAS_CHAIN` (in), `INCLUDES` (out to Narrator), `INCLUDES_MENTION` (out to NameMention).
- Cardinality: ~99,283 hadiths -> chains ~ hadiths + extra tahwil branches; ~160k INCLUDES inclusions per the brief.

### 2.4b :ReligiousTradition  (W: `migrateSchoolOfThought` MF:172; `loadAssessment` mergeReligiousTradition assessment.ts:85; seed-taxonomy.ts; comparative/neo4j-commit.ts:69)
- **Key: `name` (unique)**; `id` uuid. Props from taxonomy seed: `name_arabic, description, geographic_origin`.
- 8 values in practice: Sunni, Imami, Zaydi, Ibadi (hadith scope; pre-merged before batch edges, BL:23-24, MF) + Islam, Judaism, Christianity, Zoroastrianism (comparative parents; plus others created ad hoc by comparative commit via `tradition_name`). Used as FK target for Hadith, Assessment, CrossCulturalParallel, SourceText.

### 2.5 :NameMention - see section 1. Key `pipeline_key = "<chain.pipeline_key>::pos<position>"` (unique). Index surface_form, normalized_form, position.

### 2.6 :DatasetVersion - see section 1. Key `content_hash` unique + `id` unique; indexes content_hash, created_at.

### 2.7 :FullregenLease (infra) - see section 1.

### 2.8 :Assessment  (W: loadAssessmentsBatch BL:586-611)
- **Key: `pipeline_key`**: `record_id:<record_id>::<tradition>::<scholar-or-'unspecified'>` for gradings_full entries (BL:533), `record_id:<record_id>::<tradition>` for the primary grade_value and for placeholders (BL:555, 571). Legacy keys: `dataset_row_id:<n>::<tradition>`, `scholar_indx:<n>::unspecified_legacy`, `<keyProp>:<val>::<tradition>_legacy`. Surrogate `id`.
- Props: `grade` (raw string - Arabic or Latin or 'no_extant_evaluation'; NOT normalized to GradeCanonical in the loader), `grade_source` (scholar name for gradings_full; CSV `grade_source` or 'hadith_csv' for primary; 'system_placeholder' for placeholders; 'legacy_scalar_migration' for migration), `grade_scheme` (enum above), `tradition`, `source` (dvId), `migrated_from` (legacy only), `created_at`, `updated_at`.
- gradings_full format: `<scholar>: <grade> (<citation>) | ...` split on ' | ', first ':' splits scholar, trailing balanced parens = citation (assessment.ts:326-395). **The citation is parsed but DROPPED by the batch loader** (BL:534-542 stores no citation; the row-level `loadGradingsFull` instead concatenated it into grade_source as "scholar (citation)", assessment.ts:433-435). New schema should keep a `citation` column.
- Quirk: the key `...::<tradition>::<scholar>` means two entries from the same scholar in one tradition collapse into one Assessment (last write wins).
- Edges: `HAS_ASSESSMENT {source,confidence:1.0,extraction_method:'assessment_matrix'}` from Hadith; `UNDER_SCHEME {same props}` to ReligiousTradition.
- Indexes: grade, grade_source, grade_scheme. Constraint on `pipeline_key` and `id` (schema.ts:107-108).
- Note on the 399k count: 99,283 x 4 traditions = 397,132 matrix rows + legacy/narrator migration rows ~ matches ~399k; 88% placeholders.
- Grade vocabularies: `src/lib/constants/grade-taxonomy.ts` provides `GradeCanonical` = sahih | hasan | muwaththaq | da_if | majhul | mursal | mawdu | mu_tabar | mukhtalaf | ungraded, `mapToCanonical(display_grade)` (exact-map then first-match contains rules) and `cleanGradeDetail()`. It is NOT applied by the regen loader to `Assessment.grade` - so a `grade_canonical` column derived at load/ETL time is a net-new, low-risk improvement for the new schema. `grade-taxonomy.ts` describes the two-tier design: `grade_canonical` (bucket) + `grade_detail` (cleaned text).

### 2.9 Nodes NOT written by regen but present in schema/app (carry forward or drop deliberately)
- `:HistoricalEvent` (W: seed-historical-data.ts:943-964; also `createHistoricalEvent` action). **Key `id = stableSeedId('historical-event', title, year_hijri)`** = `historical-event:<sha256(ns|normalized parts)[:24]>` (lines 27-33). Props: `title, title_arabic, description, year_hijri, year_gregorian, start_year_hijri (= year_hijri), start_year_gregorian, end_year_hijri, end_year_gregorian, category (PROPHETIC_ERA|RASHIDUN|UMAYYAD|ABBASID|SCHOLARLY|MILITARY|POLITICAL|SOCIAL), significance, location_name, verification_status ('unverified_seed'), publication_ready (false), created_at, updated_at`. Seed may refresh content ONLY while `verification_status='unverified_seed' AND publication_ready=false` (FOREACH-guarded, 947-964). Read gate for public timeline: `publication_ready=true` AND `verification_status IN (human_verified, source_verified)` AND nonblank `citation_source` AND (`citation_locator` OR `citation_url`) (db/AGENTS.md:7). `citation_*` columns exist only as interim embedded props. Indexes: year_hijri, start_year_hijri, end_year_hijri, category.
- `:Location` (seed-historical-data.ts:906-916): key `id = stableSeedId('location', name)`; props `name, name_arabic, latitude, longitude, modern_country, region, description, verification_status='unverified_seed'`. Edge `(:HistoricalEvent)-[:OCCURRED_AT]->(:Location)`.
- `(:Narrator)-[:INVOLVED_IN {role}]->(:HistoricalEvent)` (graph-actions.ts:623; role default 'Participant'). Narrator-event contextual overlap is computed at READ time via year intervals (never persisted; db/AGENTS.md:30).
- `:Epoch` (start_year_hijri, end_year_hijri) - only constraints/indexes exist, no writer.
- `:SchoolOfThought` (seed-taxonomy.ts): key `name` unique + `id`; props `name_arabic, category (SUNNI_THEOLOGICAL|SHIA_THEOLOGICAL|IBADI_THEOLOGICAL|SUNNI_MADHHAB|SHIA_MADHHAB), founder, founded_century_hijri, description`. Edges `WITHIN_RELIGION -> ReligiousTradition{Islam}`, `PART_OF -> SchoolOfThought` (madhhab -> theological school: Hanafi/Maliki/Shafi'i/Hanbali -> Sunni; Ja'fari -> Shia Imami). 9 schools seeded + Sunni/Ibadi/Shia Imami/Shia Zaydi.
- `:CrossCulturalParallel` (W: src/lib/comparative/neo4j-commit.ts:145-165, human/agent-reviewed): key `pipeline_key = "<hadith.id uuid>::<TRADITION_UPPER>::<source_reference>"`; props `parallel_type, isra_iliyyat_status, confidence_level, hadith_excerpt_en, source_text_original, source_text_en, scholarly_analysis`. Edges `(:Hadith)-[:HAS_PARALLEL]->(p)`, `(p)-[:PARALLELS]->(:SourceText)`, `(p)-[:FROM_TRADITION]->(:ReligiousTradition)`, `(p)-[:TAGGED_WITH]->(:MotifTag)`. NB: the key embeds the Hadith surrogate **uuid**, which changes on a clean fullregen - parallels must be re-keyed by `record_id` or they orphan. This is a MIGRATION RISK for the clean-target load.
- `:SourceText` (key `canonical_reference` per merge; constraint on `id`): `id, title, tradition_name, description`; edge `BELONGS_TO -> ReligiousTradition`.
- `:MotifTag` (key `name` unique): `id, category (inferMotifCategory)`.
- `:Commentary` (W: graph-actions.ts createCommentary 661-709, CREATE not MERGE; pipeline_key unique constraint exists but unused here): props `id, source_work, author, text, text_arabic, type, reference, created_at`; edges `(c)-[:COMMENTS_ON]->(:Hadith)` (by Hadith.id uuid!), `(c)-[:DISCUSSES]->(:Narrator)` (by Narrator.id uuid!). Same uuid-surrogate risk as parallels.
- `:Practice`, `:Scholar`, `:ScholarVerdict`, `:MatnVariation`, `:Person`, `:BibliographicWork`, `:Edition`, `:Citation`, `:BiographicalAssertion`, `:TemporalAssertion`: schema.ts constraints only (59-111); no writers in the current regen. `:MatnVariation` + `HAS_VARIATION`/`TRANSMITTED_VIA`/`HEARD_FROM` is the legacy v1 chain graph, read-only fallback.

---------------------------------------------------------------------------
## 3. Relationships (endpoints and properties)

All regen-written relationships carry provenance `source = dvId` (string), and (G-2/G-4) `confidence` + `extraction_method`.

| Type | From -> To | Properties | Writer | Identity |
|---|---|---|---|---|
| FROM_SOURCE | Hadith -> Source | source, confidence=1.0, extraction_method='unified_csv' | BL:307 | one per hadith |
| INGESTED_IN | Hadith -> DatasetVersion | same | BL:309 | one per hadith per version |
| FROM_TRADITION | Hadith -> ReligiousTradition (also CrossCulturalParallel -> RT; legacy migrated edges with `migrated_from='IN_SCHOOL'`, `created_at`) | source, confidence, extraction_method | BL:311, MF:188 | one per hadith |
| HAS_CHAIN | Hadith -> Chain | source, confidence=1.0, extraction_method=method | BL:450 | one per branch |
| INCLUDES | Chain -> Narrator | **position** (0-based in branch; part of MERGE identity), confidence (per narrator), extraction_method, source | BL:462 | (chain, position, narrator) |
| INCLUDES_MENTION | Chain -> NameMention | position, confidence (0.0), extraction_method ('regex_sanad'), source | BL:677 | (chain, mention) |
| NARRATED_FROM | Narrator(student) -> Narrator(teacher) | confidence (max over occurrences of min(student,teacher conf)), extraction_method, source, updated_at, and G-6 `temporal_plausibility ('plausible'\|'impossible'\|'unknown')`, `temporal_reason`, `temporal_assessed_at`, `temporal_dvId` | BL:475-480, temporal-plausibility.ts:170-177 | (student, teacher) global, NOT per chain |
| HAS_ASSESSMENT | Hadith (or Narrator in legacy migration) -> Assessment | source, confidence=1.0, extraction_method='assessment_matrix' | BL:605, assessment.ts:217 | |
| UNDER_SCHEME | Assessment -> ReligiousTradition | same | BL:607 | |
| RESOLVES_TO | NameMention -> Narrator | confidence, extraction_method='rerank', reviewed_by, reviewed_at, quarantined, created_at | ingest-er-approved.ts:177 (HITL only) | |
| SAME_AS | (none written) | reviewed_by required (G-5) | - | |
| IN_SCHOOL | Hadith/Narrator -> SchoolOfThought | legacy, superseded by FROM_TRADITION | old importer | |
| WITHIN_RELIGION / PART_OF | SchoolOfThought -> ReligiousTradition / SchoolOfThought | none | seed-taxonomy | |
| OCCURRED_AT | HistoricalEvent -> Location | none | seed-historical | |
| INVOLVED_IN | Narrator -> HistoricalEvent | role | graph-actions:623 | |
| HAS_PARALLEL / PARALLELS / TAGGED_WITH / BELONGS_TO | see 2.9 | none | comparative commit | |
| COMMENTS_ON / DISCUSSES | Commentary -> Hadith / Narrator | none | graph-actions | |

NARRATED_FROM temporal rules (temporal-plausibility.ts:63-105): `impossible` if student_birth > teacher_death OR teacher_birth > student_death (i.e. NON-OVERLAP of lifetimes); `plausible` only when all four bounds known and overlapping; else `unknown`. Never infer impossibility from a large death-year gap alone (AGENTS.md:43). Annotated in bounded UNWIND batches of 1,000 (`TEMPORAL_WRITE_BATCH_SIZE`). Hijri integers used (death_date_hijri/birth_date_hijri). Because NARRATED_FROM is student->teacher and global, in SQL it is a derived table `narrator_transmission(student_id, teacher_id, ...)` = `SELECT DISTINCT` of consecutive INCLUDES positions across chains; best kept as a MATERIALIZED VIEW or table rebuilt by the loader (the loader already wipes+rebuilds it, MF:1621-1623). ~80k rows.

Supernode caution (supernode-detect.ts, BL header 8-14): a few narrators (Abu Hurayra, Anas, Prophet scholar_indx=1...) appear in tens of thousands of chains; with relational tables this is only an index-selectivity concern, not a write-lock problem.

---------------------------------------------------------------------------
## 4. Stable keys summary (what a relational PK / natural key must preserve)

| Entity | Natural key | Surrogate |
|---|---|---|
| Narrator | scholar_indx int | id uuid |
| Hadith | record_id text | id uuid; dataset_row_id int (compat only); pipeline_key = source::hadith_no |
| Source | name (canonical work) | id uuid; source_work_id |
| Chain | (record_id, chain_index) i.e. pipeline_key | id uuid |
| ChainNarrator (INCLUDES) | (chain, position) -> narrator | - |
| NameMention | (chain, position) | id uuid |
| Assessment | (hadith_or_narrator, tradition, scholar/grade_source) | id uuid |
| ReligiousTradition | name | id |
| DatasetVersion | content_hash | id uuid |
| HistoricalEvent / Location | deterministic `stableSeedId` sha256 prefix | = id |
| CrossCulturalParallel | pipeline_key (embeds hadith uuid - re-key by record_id) | id |
| Commentary | id uuid only (links by hadith/narrator uuid - re-key) | id |

Important: every `id` uuid is minted with `randomUUID()` at first MERGE and is not stable across a clean-target regen. All user-curated content (Commentary, CrossCulturalParallel, HITL RESOLVES_TO, Narrator phase-0 bios, enrichment, graph `HistoricalEvent` reviews) must be re-attached via natural keys (record_id / scholar_indx), not via the old uuids.

---------------------------------------------------------------------------
## 5. Guardrails a new store must still honor

Defined in `mode-test.ts` (read-only checks) and file headers; "spec" = track `neo4j_isnad_graph_regen_20260516`.
- **G-1 (ABSOLUTE)**: no scalar `reliability`/`grade` verdict on Narrator or Hadith; all verdicts on tradition-scoped Assessment (assessment.ts:13-16; BL:29; LN:9-11; check mode-test.ts:44-64). Raw rawi grade only as `_raw_grade` breadcrumb. Gap: phase-0 `reliability_consensus` currently violates the spirit.
- **G-2**: Narrator identity keyed on stable `scholar_indx`, never uuid (mode-test.ts:66-85, FR-0.1); also "every edge carries confidence + extraction_method + source" (BL:30; MF:254 GIGO report prints confidence strata per rel type).
- **G-3**: active DatasetVersion has `attribution_disclaimer`; disclaimer text: "kathrat al-riwaya describes transmission volume only; it is not a judgment of narrator reliability or hadith authenticity." (regen-isnad-graph.ts:41-42; MF:1850-1855 run-report literal `DISCLAIMER (spec §5 G-3)`: reliability scores reflect frequency of transmission, not 'adala/dabt, not authoritative rulings). Must remain surfaced in UI/exports.
- **G-4**: all NARRATED_FROM edges have confidence + extraction_method + source (mode-test.ts:106-124).
- **G-5**: no auto-written SAME_AS / RESOLVES_TO; only human-approved ER rows (ingest-er-approved.ts invariants 1-5); `quarantined` flag for unmeasured strata (NFR-3).
- **G-6**: every NARRATED_FROM edge has a `temporal_plausibility` flag after a full regen; failure to annotate blocks activation (MF:1786-1793; mode-test.ts:147-167).
- **Section 9b checks** (mode-test.ts:169-245): exactly one active DatasetVersion; live Hadith >= 50,000; live Narrator > 0; every live Hadith has an INGESTED_IN edge; per-tradition coverage (hadith/chain/no_extant counts, chain hit rate).
- **NFR-2 / no-delete**: tombstone not DETACH DELETE (tombstone.ts:13-21); owner memory `feedback_no_delete_backup`.
- **Release gates** (regen AGENTS.md lines 5-19, 29-35): curated gate and manifest before first DB connection; clean-target/blue-green full regen only; singleton lease; DatasetVersion activated only after counts verified (hadiths, chains, narrators) and temporal annotation succeeded (MF:260-295, 1769-1820); non-release loads can never activate; idempotent MERGE writes keyed on record_id; Railway project ACK `RAILWAY_FULLREGEN_PROJECT_ACK=43973172-fd19-4c41-8097-369cf805cbe6` (project id is a safety guard to be re-pointed for the Postgres target).
- **Evidence/publication gates** (db/AGENTS.md): historical events/locations default `unverified_seed`, `publication_ready=false`, stay hidden from public reads until cited; competing biographical claims must not be overwritten (fill-if-missing only; reviewed-assertion resolver is future work); canonical lifetime ints only from exact safe-integer tokens, ranges kept in `*_raw`.
- **Corpus identity** (constants/AGENTS.md): a shared source label is never silently assigned to a compiler; tradition aliases accepted on read but URLs/DB converge on Sunni/Imami/Zaydi/Ibadi.
- **Arabic normalization parity**: TS `norm()` must stay byte-equivalent to Python `classify_attribution._norm`; JS `\b` is ASCII-only, use `(?![ء-ي])` (name-mention.ts:13-20; memory js-python-word-boundary-arabic).
- **Chain reads**: group by chain_id before ordering; never flatten tahwil branches (actions/AGENTS.md).

---------------------------------------------------------------------------
## 6. Observations useful for the Postgres/Drizzle schema design

1. The app genuinely needs only these fixed-depth joins: Hadith -> Chain -> (position-ordered) Narrator; Hadith -> Source/Tradition; Hadith -> Assessment(by tradition); Narrator <-> Narrator (1 hop, both directions) and Narrator -> Chain -> Hadith (reverse). All are plain FK joins; `narrator_transmission` (student, teacher) is the only derived edge table.
2. Tables recommended by the model: `dataset_version`, `religious_tradition`, `source`, `narrator`, `narrator_bio` (phase-0 + future assertions), `hadith`, `chain`, `chain_narrator(chain_id, position, narrator_id, confidence, method)` PK (chain_id, position), `name_mention` + `mention_resolution`, `narrator_transmission`, `assessment` (polymorphic target + citation), `hadith_enrichment`, plus carried-over `historical_event`, `location`, `school_of_thought`, `cross_cultural_parallel`, `source_text`, `motif_tag`, `commentary`.
3. Provenance: replace per-row `source` string with a real FK `dataset_version_id` on Hadith/Chain/Assessment/Narrator rows, and keep `confidence`, `extraction_method` columns on chain_narrator, narrator_transmission, chain, mention_resolution (G-2/G-4).
4. Clean-target fullregen semantics map well to "load into a new schema/dataset_version, verify counts, flip `active`" - one active row enforced by a partial unique index `WHERE active`.
5. Placeholder economics: 88% of assessments are `no_extant_evaluation`. In relational form store only real assessments and synthesize the placeholder at read time via a LEFT JOIN against the 4 traditions (saves ~350k rows) - but the guard "coverage must be explicit" (assessment.ts:28-29) means the read API must still emit explicit placeholders.
6. Vector table (new): keyed by `hadith_id` (record_id FK) with model/version columns; must exclude tombstoned and non-active dataset versions.
7. Known defects discovered while reading: (a) ingest-er `source_row_id` property never written (section 1); (b) `gradings_full` citation dropped in batch path; (c) Assessment key collision for same scholar twice in one tradition; (d) `schema.ts` indexes `Hadith.display_grade`/`transmission_type` that fullregen never populates; (e) Phase-0 `tabaqah` enum overwrites free-text CSV `tabaqah`; (f) seed-taxonomy 'Shia Imami'/'Shia Zaydi' vs migration names 'Imami'/'Zaydi' mismatch; (g) uuid-based links for Commentary/CrossCulturalParallel break on clean regen; (h) `schema.ts` `clearDatabase()` is entirely commented out.
