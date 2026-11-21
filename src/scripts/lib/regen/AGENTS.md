# Regeneration loader invariants

## Curated release gate

`mode-fullregen.ts` scans the complete logical CSV before its first database connection. A production load requires a unique nonblank `record_id`, nonblank `source_record_id`, `provenance_source`, `text_ar`, and `text_en`, `translation_status=complete`, and at least one normalized `chain_indx` branch whose narrator IDs all exist in the rawi vocabulary for every row. The recognized status vocabulary is `complete`, `missing`, `model_refusal_or_error`, `same_as_arabic`, `copied_input`, `arabic_leakage`, `wrong_language`, `no_english_text`, `placeholder`, and `suspiciously_short`; only `complete` is publishable. Content QA NFKC-normalizes copied text, rejects the candidate-pipeline placeholder vocabulary, any Arabic-script leakage, and output whose letters are not at least 80% Latin. Short English is suspicious only when paired with unusually long Arabic, so genuine short reports such as “Eat.” remain valid.

Translation provenance also requires meaningful `source_record_id`, `provenance_source`, `translation_source`, and `translation_review_status` values. Normalized placeholders including `unknown`, `<missing>`, `N/A`, `none`, `null`, `-`, `TBA`, and `TBD` do not satisfy the gate; source-owned IDs must contain a letter or digit, while provenance locators require at least two. Strict release accepts only `human_verified` or `source_verified`; `source_verified` means source attribution and publication/rights eligibility have both been completed. `source_provided`, `source_status_unknown`, and machine/unreviewed states remain non-release.

If either translation provenance field contains a case-insensitive token `ai`, `automated`, `generated`, `gpt`, `llm`, `machine`, `model`, `openai`, `anthropic`, `claude`, `gemma`, or `pipeline`, `translation_model` must be a namespaced identifier with at least two nonempty components separated by `/` or `:`. Current valid forms include `google/gemma-4-e4b` and `manual:claude-opus-4.7`; generic values such as `OpenAI`, `model`, `x`, and placeholder tokens fail closed.

Every row must name a supported tradition and a nonblank source. A source may appear under exactly one tradition, and registered sources must agree with the canonical registry. Unregistered work/compiler identities block production release because display-label collapse can erase provenance. A disposable development override may retain their explicitly validated row tradition; no loader silently defaults them to Sunni.

Production also requires schema-v2 `curation_manifest.json`. The loader independently requires every named and required `full_load_gates` entry to pass, exact zero-valued integer release blockers, record/stable-ID/tradition counts equal to the streamed preflight, physical and logical CSV/GZIP hash binding, and fresh hashes for every declared input including rawis, source registry, and Imami work registry. It then streams a read-only, content-addressed temporary snapshot to require each Imami `provider_book_id` or non-provider provenance to map to exactly one registered `source_work_id` and canonical source. The same snapshot is used for every load read and rehashed before database acquisition and finalization, so replacement of the canonical CSV cannot change the loaded bytes. `ready_for_full_load=true` alone has no authority. This handoff completes before the first database connection.

`--dev-allow-incomplete-data` is only for a disposable direct `bolt://` loopback Neo4j test database; `neo4j://` and `neo4j+s://` routing schemes are refused even with a loopback bootstrap host. `RUN_LIVE_NEO4J_TESTS=1` must opt in, `NEO4J_URL` must exactly equal `NEO4J_TEST_URI`, application credentials must equal the dedicated test credentials, and both `NEO4J_TEST_TARGET_MARKER=DISPOSABLE_TEST_ONLY` and `NEO4J_TEST_DISPOSABLE_ACK=I_ACKNOWLEDGE_THIS_IS_A_DISPOSABLE_NEO4J_TEST_DATABASE` are mandatory. Production, Railway, other remote runtimes, and non-loopback targets are hard-refused. The override permits incomplete text and derives a deterministic `legacy:*` identity for an old schema without `record_id`; duplicate effective identities still fail because merging two records into one node is never safe. Do not use the legacy identity as a migration contract.

Production full regeneration is clean-target/blue-green only. After the curation handoff, a uniqueness-backed singleton `FullregenLease` is reserved before the clean-target read; its heartbeat spans all phases, database ownership/expiry is synchronously rechecked before each write phase and batch, and a `finally` release runs on success or failure. Expired leases are never stolen: a crashed owner blocks future regeneration until an audited manual cleanup. The owned coordination node is the sole clean-target exclusion. Any other existing node or relationship stops the run. Build and verify a fresh target, then switch traffic; a failed target is discarded and recreated. The disposable development override may mutate a non-empty local test graph only with a loud warning and must never be published. Its DatasetVersion is permanently inactive and machine-marked `release_eligible=false`, `non_release=true`, and `load_status=non_release_loaded`; activation refuses such nodes.

Every release fullregen targeting Railway requires `RAILWAY_FULLREGEN_PROJECT_ACK=43973172-fd19-4c41-8097-369cf805cbe6` before the first database connection. In a Railway runtime, `RAILWAY_PROJECT_ID` must also equal that exact project; a missing or different runtime project ID fails even when the acknowledgement is present. A URL-only Railway proxy cannot independently prove project identity, so the loader emits that limitation and proceeds only with the exact acknowledgement. The development override is never allowed on Railway, even with the acknowledgement. The cost guard never bypasses curation, lease, or clean-target safeguards. Non-Railway release targets are unchanged.

## Streaming and memory

CSV, gzip CSV, and JSONL inputs are consumed as streams. The CSV state machine retains one logical record so quoted multiline Arabic and translations remain intact. Gzip inputs are decompressed in the pipeline and are not expanded to a sibling file. SHA-256 is computed over logical decompressed bytes, making the content hash independent of storage compression.

`all_rawis.csv` is intentionally retained as a small in-memory lookup for entity resolution, but parsing and narrator batching do not create second whole-file arrays. Hadith buffers are bounded by both row count and UTF-8 payload size. Exact/blocked name indexes are cached once per rawi map, and final temporal annotations use bounded UNWIND batches rather than per-edge transactions.

## Identity and retry safety

Hadith nodes merge on `record_id`; `dataset_row_id` is positional compatibility metadata. Chain, assessment, and name-mention keys derive from `record_id` and stable chain position. Relationship writes use `MERGE`, including `INCLUDES.position`, so driver-level transaction retries and whole-process resumes are idempotent.

Schema initialization retains the positional Hadith uniqueness constraint on a populated graph until every Hadith has a nonblank canonical unique `record_id`. An empty clean target may retire it immediately; merely creating the new uniqueness constraint is insufficient because Neo4j uniqueness permits null properties.

A buffer spans several transactions. The orchestrator therefore never retries or splits the whole buffer after a later phase fails: it logs the affected stable IDs and stops. A fresh invocation can safely resume through idempotent merges. `batch-loaders-fresh.ts` is a compatibility alias and must not reintroduce blind `CREATE` writes.

Full loads create or reuse a `DatasetVersion` with `load_status=loading`. This is provenance metadata, not transaction isolation; the `FullregenLease` supplies cross-process writer exclusion. A content hash has one immutable lifecycle class (`release` or `non_release`) and one immutable `load_purpose` (`release_fullregen`, `dev_fullregen`, or `legacy_diff`). Non-release purposes are bound to their immutable reasons: `dev_fullregen` to `dev_allow_incomplete_data`, and `legacy_diff` to `legacy_diff_mode`. Before any matched-node update, class, purpose, and reason markers are checked for consistency and must equal the request; release, development-fullregen, and legacy-diff runs cannot reuse or reclassify one another. Finalization also requires the expected purpose. Hadith, Chain, and Narrator counts are verified against the preflight inputs before temporal annotation, the version is activated only after required phases succeed, and a failed release target is discarded rather than resumed in place.

## Narrator metadata sequencing

The base rawi import establishes narrator identity and only applies optional properties that are present and nonblank. On an existing narrator, every optional property is fill-if-missing: the base CSV must not replace any nonblank biography, Arabic/English name, place, tabaqah, raw date token, source text, or canonical date already present in Neo4j. Replacing competing scalar claims requires a future reviewed assertion resolver, never a base regeneration.

Canonical narrator lifetime properties accept only exact safe integer tokens; ranges and qualified canonical tokens are retained in `*_raw`/source-text properties and are not truncated with `parseInt`. A numeric Hijri token may still acquire a negative sign from explicit `BH` source context. Before any writes, narrator preflight rejects death-before-birth and AH/CE pairs more than three years from the standard approximate conversion. Read APIs may expose `birth_year_hijri` / `death_year_hijri` aliases for UI compatibility, but historical-event range queries use the canonical values and return no contextual lifetime events when both bounds are unknown.

Temporal plausibility compares narrator lifetime intervals. It flags only non-overlap as impossible, treats incomplete bounds as unknown, and never interprets a large teacher/student death-year gap by itself as proof. Relationship reads and writes are both paged in bounded batches.

`mode-diff.ts` and the row-level loaders still use legacy positional identity. Diff mode calls the same direct-loopback disposable-target assertion before file or database work, records its DatasetVersion as inactive `non_release_loaded`, and never deactivates release versions; clean-target full regeneration is the sole production path until those modules migrate to durable `record_id` keys.

## Focused verification

Run the DB-free contract test with:

```powershell
npx tsx src/scripts/__tests__/regen-full-load-hardening.test.ts
```

Then include TypeScript and lint in the repository's single integrated final verification sweep.
