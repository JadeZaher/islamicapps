# Specification: Neo4j Isnad/Narrator Graph Regeneration Pipeline (Phases 0–2)

**Track ID:** `neo4j_isnad_graph_regen_20260516`
**Type:** Feature
**Priority:** P0 (upstream blocker for the analytics/enrichment track family)
**Created:** 2026-05-16
**Authoritative source:** `.omc/research/neo4j-hadith-graph/STRATEGIC_REPORT.md` (Sections 0–8 binding)

---

## 1. Overview

Regenerate the unified hadith dataset into the existing Neo4j layer as an
**idempotent, provenance-tracked, reified isnad/narrator graph**. This track owns
the *fix-first* corrections, the engine-agnostic reified schema, and the
`chain_indx`-driven tiered narrator entity resolution. It is the upstream
ingestion pipeline that the GDS-analytics, narrator-enrichment,
grade-normalization, embedding, and scholarly-metadata tracks all consume — it
does **not** duplicate them.

Scope is **Phases 0–2 only**. Phases 3 (analytics) and 4 (frontier) are out of
scope and explicitly belong to downstream tracks.

The bottom line from the reliability ledger governs every acceptance criterion:
the graph is honest as a *finding aid* from Phase 1, becomes an *analytical
engine* only after entity resolution + validation gates, **no GIGO analytic
ever ships as a result**, and **no algorithmic output is ever presented as a
ḥukm**.

## 2. Background

Two live bugs are shipping today in `src/scripts/import-datasets.ts`:

1. **Narrator duplication.** Narrators are `MERGE`'d on a fresh `uuidv4()`
   generated per run (`import-datasets.ts:312`, `:373`). Every re-run duplicates
   every narrator. The repo already has the correct idempotency convention in
   `src/lib/db/neo4j-helpers.ts` (`mergeNodeByKey` → MERGE on business key with
   `ON CREATE`/`ON MATCH` sentinel), which the live importer bypasses.
2. **Unified-narrator fallacy.** The importer writes a scalar
   `n.reliability` node property (`import-datasets.ts:378`, derived from
   `mapGradeToTabaqah`). This collapses tradition-specific assessment onto a
   single Narrator node — a Sunnī *ṣaḥīḥ* and a Zaydī verdict can silently
   overwrite each other. It is the #1 ranked risk and is in production.

Ground-truth corrections (verified in-repo, not from agents — these MUST NOT be
re-introduced by any sub-analysis):

- **Canonical record count = 69,368 CSV records** = Sunni 34,441 + Imami 33,225
  + Ibadi 1,004 + Zaydi 698, measured with a real CSV parser (`csv.DictReader`
  semantics). `wc -l` on the file yields ~78,952 because Arabic `text_ar`
  contains embedded newlines. **Validation gates MUST count CSV records, never
  lines.**
- **`datasets/hadith-data/all_hadiths_unified.csv`** has `chain_indx` already
  populated: Sunni 34,318/34,441 (99.6%), Imami 27,863/33,225 (84%), Ibadi/Zaydi
  0%. For ~62k of 69k rows narrator edges are a JOIN to `scholar_indx`, not ML.
- **`datasets/narrator-data/all_rawis.csv`** (24,326 rows): `scholar_indx`
  (1 = Prophet ﷺ), bilingual `name`, `grade`, full genealogy, `death_date_hijri`
  / `death_date_gregorian`, and `teachers_inds`/`students_inds` adjacency lists.
  It is simultaneously the controlled vocabulary, a prebuilt teacher/student
  graph, and the temporal authority enabling the contemporaneity guardrail.
- `datasets/classify_attribution.py` provides reusable Arabic normalization
  (`_norm`) and the `attributed_to`/`narration_level` rule-based outputs that
  Phase 2 must reuse for the regex-sanad path (Ibadi/Zaydi 1,702 rows + the
  Imami 16% `chain_indx` gap).

Net effect: this is brownfield and far more tractable than the literature
implies. The ML-heavy ER narrative applies only to the ambiguous collision core.

## 3. Functional Requirements

### Phase 0 — Fix-first

**FR-0.1 — New idempotent regeneration script.**
Create `src/scripts/regen-isnad-graph.ts` following the `import-datasets.ts`
structure, but using `src/lib/db/neo4j-helpers.ts` (`mergeNodeByKey`,
`mergeEdge`, `buildPipelineKey`) for all node/edge writes. `import-datasets.ts`
is left in place but marked deprecated in a header comment and in
`tech-stack.md`. A new `npm run` command (e.g. `db:regen`) is added to
`package.json`. Acceptance: priority **P0**.

- Acceptance criteria:
  - Running the script twice consecutively produces **identical node and
    relationship counts** on the second run (idempotent).
  - Narrators are MERGE'd on the stable business key `scholar_indx` (the
    `narrator_scholar_indx_unique` constraint already exists in `schema.ts`),
    never on a freshly generated UUID.
  - Hadiths are MERGE'd on a stable composite business key
    `buildPipelineKey(source, hadith_no)` (or `dataset_row_id` when present),
    not a per-run UUID.
  - No scalar `reliability` (or any assessment scalar) is written to any
    `:Narrator` or `:Hadith` node.

**FR-0.2 — `:DatasetVersion` provenance node.**
Each regen run creates/merges a `:DatasetVersion` node pinning the canonical
record count and a content hash of the input CSVs.

- Acceptance criteria:
  - `:DatasetVersion` node has `expected_record_count = 69368`, per-tradition
    sub-counts, `content_hash` (sha256 of the unified + rawis CSVs), and
    `created_at`.
  - The count is computed by a **CSV-record parser** (multiline-quoted-field
    aware — the existing `readCSV` in `import-datasets.ts` already handles
    embedded newlines; reuse that logic), never `wc -l` / line splitting.
  - All ingested `:Hadith` nodes carry an `INGESTED_IN` edge to the active
    `:DatasetVersion`.

**FR-0.3 — Measure the real unknown-attribution fraction.**
Run `classify_attribution.classify` (or a TS port faithful to its `_norm` +
marker logic) across the unified CSV and record the real `narration_level`
distribution, including the true `unknown` fraction (the "~12%" figure is
unverified and must be measured, not assumed).

- Acceptance criteria:
  - A machine-readable distribution report is produced
    (`attributed_to` × `narration_level` × tradition counts).
  - The measured `unknown` fraction is recorded as a property on
    `:DatasetVersion` and printed in the run summary.

### Phase 1 — Reified engine-agnostic schema

**FR-1.1 — Reified `:Chain` with retained fast shortcut.**
The isnad is reified as a `:Chain` node. A fast `NARRATED_FROM` shortcut edge
between consecutive resolved narrators is retained for SNA (two-layer model:
raw reified chain + materialized shortcut). The existing `INCLUDES`
(Chain→Narrator) and `TRANSMITTED_VIA` (MatnVariation→Chain) edges from the
current importer are preserved and made idempotent.

- Acceptance criteria:
  - Every hadith with a non-empty isnad has exactly one `:Chain` per distinct
    isnad (multi-isnad is first-class: a hadith with N distinct chains has N
    `:Chain` nodes, not one merged chain).
  - `:Chain` carries `position`-ordered membership so chain order is
    recoverable.
  - `NARRATED_FROM` edges exist between consecutive *resolved* narrators only;
    unresolved links use `NameMention` (FR-1.3).

**FR-1.2 — Tradition-scoped reified `:Assessment`.**
Verdicts/grades are reified as `:Assessment {grade, grade_source,
grade_scheme}` linked `-[:UNDER_SCHEME]->(:ReligiousTradition)`. Absence is
explicit (`no_extant_evaluation`), never an inherited default.

- Acceptance criteria:
  - A Sunnī *ṣaḥīḥ* `:Assessment` and a Zaydī `:Assessment` on the same hadith
    are distinct nodes scoped to distinct traditions; neither can overwrite the
    other.
  - A hadith with no extant evaluation in a tradition has an explicit
    `no_extant_evaluation` `:Assessment` for that tradition (or a documented
    absence representation) — Zaydī/Ibāḍī never silently inherit a Sunnī grade.
  - This track only *creates the structure and migrates existing scalar grade
    data into it*; populating scholarly verdicts is delegated to
    `scholarly_metadata_layer_20260425` (dependency edge, not duplication).

**FR-1.3 — NameMention vs resolved Narrator.**
A surface form occurring in an isnad that is not (yet) resolved to a
`scholar_indx` narrator is a `:NameMention {surface_form, normalized_form,
position}` node, distinct from a resolved `:Narrator`. Resolution attaches a
`:RESOLVES_TO` edge (created in Phase 2).

- Acceptance criteria:
  - No isnad link silently drops because its narrator is unresolved; it becomes
    a `:NameMention` with provenance.
  - `:NameMention.normalized_form` is produced by the shared `_norm` Arabic
    normalization (faithful to `classify_attribution._norm`).

**FR-1.4 — Per-edge confidence + extraction_method + provenance; tombstone.**
Every narrator/isnad edge carries `confidence` (0–1), `extraction_method`
(`chain_indx_join` | `lexicon_exact` | `lexicon_blocked` | `rerank` |
`regex_sanad`), and `source` provenance (dataset version + row). Weak edges are
**excluded by projection predicates, never deleted** (tombstone rule; honors
the standing no-delete directive).

- Acceptance criteria:
  - 100% of narrator/isnad edges have non-null `confidence`,
    `extraction_method`, and `source`.
  - A confidence distribution histogram is produced per `extraction_method` and
    per tradition.
  - "Removing" a weak edge sets a `tombstoned = true` property; the edge is
    retained in the store and excluded by query/projection predicates.

### Phase 2 — Tiered entity resolution

**FR-2.1 — Tier 1: `chain_indx` join.**
For rows with populated `chain_indx`, create direct resolved-narrator edges to
the matching `scholar_indx` in `all_rawis.csv`. Audit-only (no ML).

- Acceptance criteria:
  - ≥99% of Sunni `chain_indx`-populated rows and ≥84% of Imami rows resolve
    via direct join (matching the verified `chain_indx` coverage).
  - Every Tier-1 edge has `extraction_method = 'chain_indx_join'` and
    `confidence = 1.0` (deterministic join).
  - An audit report flags `chain_indx` values with no `scholar_indx` match in
    `all_rawis.csv`.

**FR-2.2 — Tier 2: exact / blocked lexicon lookup.**
For rows without `chain_indx` (Ibadi/Zaydi 1,702 + Imami 16% gap), resolve via
exact and blocked lexicon lookup against `all_rawis.csv`, reusing the shared
`_norm` normalization, plus the `attributed_to`/`narration_level` outputs from
`classify_attribution`.

- Acceptance criteria:
  - Exact matches get `extraction_method = 'lexicon_exact'`, `confidence ≥ 0.9`.
  - Blocked (normalized-key candidate) matches get `lexicon_blocked` with
    measured/justified confidence.
  - Rows that fall through to the regex-sanad path are tagged
    `extraction_method = 'regex_sanad'` with the `classify_attribution`
    terminus recorded.

**FR-2.3 — Tier 3: ambiguous collision core with mandatory HITL.**
Kunya collisions (e.g. "Abū Jaʿfar" = al-Kulaynī vs al-Bāqir vs al-Jawād) are
resolved by graph-prior retrieve → rerank → confidence, using `all_rawis`
nasab/tabaqa/dates as free features. Every ambiguous-core resolution **and
every cross-tradition `:SAME_AS`** requires human confirmation.

- Acceptance criteria:
  - Ambiguous candidates are written to a reviewable JSON staging file
    (candidate surface form + ranked options + features + confidence), mirroring
    the existing `comparative_ingestion` staging pattern.
  - An idempotent "ingest approved" script commits only human-approved
    resolutions as `:RESOLVES_TO` edges with `extraction_method = 'rerank'` and
    `reviewed_by` / `reviewed_at` provenance.
  - No ambiguous-core edge is auto-committed without an approval record.
  - Phase 2 exit requires the HITL queue **drained or quarantined** (see
    NFR-3 ER exit posture).

**FR-2.4 — Cross-tradition `:SAME_AS` (reviewed-only, reversible).**
Cross-tradition narrator identity links are explicit, human-confirmed,
reversible, audited `:SAME_AS` edges — never silent merges.

- Acceptance criteria:
  - `:SAME_AS` edges only exist with `reviewed_by`, `reviewed_at`,
    `confidence`, and a `reversible = true` semantic (a split-vs-confirmed
    projection switch is documented).
  - A test asserts zero `:SAME_AS` edges without a review record.

## 4. Non-Functional Requirements

**NFR-1 — Idempotency & reproducibility.** Re-running the full pipeline on the
same `:DatasetVersion` yields byte-stable node IDs and identical counts. Node
IDs do not churn across runs.

**NFR-2 — No-delete / tombstone.** Honors the standing no-delete directive
(MEMORY: `feedback_no_delete_backup.md`). Nothing is `DETACH DELETE`'d; weak or
superseded data is tombstoned and excluded by predicate.

**NFR-3 — ER exit posture (no-GIGO).** Ambiguous-core resolutions for
**unmeasured strata** (Imami-gap, cross-tradition, transliterated) are written
with low confidence + a `quarantined = true` flag and are excluded from all
downstream projections until separately measured. Phase 2 exits when the HITL
queue is drained **or** quarantined. No unmeasured resolution is presented as
authoritative.

**NFR-4 — Engine-agnostic logical model.** The reified schema (Chain /
NameMention / tradition-scoped Assessment / typed provenance edges) is kept
logically engine-agnostic so an RDF/Postgres-AGE flip stays cheap. An RDF
export is the interoperability path, not an engine switch.

**NFR-5 — Performance.** Full regen of 69,368 hadith records + 24,326 narrators
completes in a single batched run; writes use `runWrite`'s `executeWrite`
(retry-safe) and batched transactions per the existing importer's batching
shape.

**NFR-6 — TypeScript strict + parameterized queries.** All Cypher uses
parameterized inputs (workflow.md). Scripts live in `src/scripts/`, schema
changes in `src/lib/db/schema.ts` applied via `npm run db:init`. Per
workflow.md: **no formal TDD**; targeted tests only for the
data-transformation / ingestion / ER logic.

## 5. Six Enforceable Guardrails (each an acceptance criterion with a test)

| # | Guardrail | Concrete test |
|---|-----------|---------------|
| **G-1** | **Identity ≠ Assessment** | Cypher assertion test: `MATCH (n) WHERE (n:Narrator OR n:Hadith) AND (n.reliability IS NOT NULL OR n.grade IS NOT NULL) RETURN count(n)` **must return 0**. Run in CI/verification after every regen. |
| **G-2** | **Confidence-stratified analytics** | Test: every narrator/isnad edge has a non-null `confidence` + `extraction_method`; a GIGO report (confidence strata + dataset version + per-method counts) is generated and required to exist before any downstream metric display. A linter check rejects a projection query lacking a confidence predicate. |
| **G-3** | **Non-authority framing** | Test: no `:Narrator`/`:Hadith` carries a global authenticity/authority scalar; any metric node must be a separate `:GraphMetric` (created downstream, not here) and the regen serializer/report emits the "kathrat al-riwāya, not ʿadāla/ḍabṭ" disclaimer string. Assert the disclaimer is present in the run report. |
| **G-4** | **Provenance & copyright** | Test: 100% of narrator/isnad/assessment edges carry `source` (dataset version + row). `:Source` license status is checked; a test asserts no edge lacks provenance and that restricted-edition apparatus is not redistributed (license_status gate). |
| **G-5** | **Cross-tradition safety** | Test: `MATCH ()-[r:SAME_AS]->() WHERE r.reviewed_by IS NULL RETURN count(r)` **must return 0**. Plus a test that a `:SAME_AS` is reversible (split projection switch documented + exercised). |
| **G-6** | **Temporal plausibility** | Test: a contemporaneity pass using `all_rawis` `death_date_hijri` flags transmission edges where teacher death precedes student floruit as `temporal_plausibility = 'impossible'` (or `'unknown'` when dates missing). Assert flagged edges are tombstoned/excluded, **not deleted**, and a count is reported. |

## 6. User Stories

**US-1 — Reproducible regeneration**
As a data engineer, I want to re-run the ingestion pipeline safely, so that the
graph stays correct without duplicating every narrator on each run.
- Given a populated graph from a prior run
- When I run `npm run db:regen` again on the same dataset version
- Then node and relationship counts are identical and no duplicates appear.

**US-2 — Tradition-faithful grading structure**
As an Islamic studies researcher, I want Sunnī and Zaydī assessments kept
physically separate, so that one tradition's verdict never silently overwrites
another's.
- Given a hadith assessed in two traditions
- When I query its assessments
- Then I get two distinct tradition-scoped `:Assessment` nodes, and a tradition
  with no extant evaluation shows an explicit `no_extant_evaluation`.

**US-3 — Honest finding aid**
As a serious student, I want the graph to be honest about what is a
deterministic join vs an unmeasured guess, so that I never mistake an
algorithmic output for a scholarly ḥukm.
- Given a resolved narrator edge
- When I inspect it
- Then it carries `confidence`, `extraction_method`, and provenance, and
  unmeasured ambiguous-core resolutions are quarantined and excluded from
  downstream analytics.

**US-4 — Auditable entity resolution**
As a domain-expert reviewer, I want ambiguous kunya collisions queued for human
confirmation, so that "Abū Jaʿfar" is never auto-assigned to the wrong identity.
- Given an ambiguous surface form
- When the ER pipeline runs
- Then it produces a reviewable staging entry with ranked candidates and
  features, and only my approval commits a `:RESOLVES_TO` edge.

## 7. Technical Considerations / Decisions Made

These defaults were chosen from the strategic report + repo conventions
(interactive confirmation was unavailable in the planning context; the
orchestrator may override — see Open Questions):

- **D-1 (pipeline location):** New script `src/scripts/regen-isnad-graph.ts`;
  `import-datasets.ts` deprecated in place (reversible, preserves the reference
  pattern workflow.md points to).
- **D-2 (canonical source):** `datasets/hadith-data/all_hadiths_unified.csv` is
  the single canonical input; the 69,368 gate counts CSV records from it **and**
  asserts the four per-tradition sub-counts.
- **D-3 (HITL surface):** JSON staging file + idempotent "ingest approved"
  script, mirroring the existing `comparative_ingestion` pattern. No web/admin
  UI in this track.
- **D-4 (sequencing):** This track is upstream of all five adjacent tracks.
- **D-5 (ER exit):** Quarantine unmeasured strata (NFR-3) — satisfies "no GIGO
  ships" without stalling on unmeasurable labeled sets.
- **D-6:** Reuse `import-datasets.ts`'s multiline-aware `readCSV` for
  CSV-record counting; port `classify_attribution._norm` faithfully (do not
  re-implement Arabic normalization differently).

## 8. Explicit Dependency Edges (no duplication)

This track is the **upstream reified-ingestion pipeline**. It produces the
clean reified graph + resolved narrator identities; the following existing
tracks **consume** its output and must not be duplicated here:

| Downstream track | Relationship | Boundary |
|---|---|---|
| `gds_setup_analytics_20260425` | **DEPENDS ON** this track | Phase 3 analytics belong there; this track ships **no analytics**. |
| `narrator_enrichment_20260425` | **DEPENDS ON** this track, then runs (parallel-able post-handoff) | Enriches resolved `:Narrator` nodes. Its current "P0 blocks gds" note should be reframed: it blocks gds **but itself depends on regen first** — regen produces the resolved identities it enriches. Recommended new ordering: `regen → narrator_enrichment → gds`. |
| `grade_normalization_20260425` | **DEPENDS ON** this track | Consumes the reified `:Assessment` structure; this track creates the structure + migrates existing scalar grades, it does not normalize the ~200 grade strings. |
| `vector_embedding_pipeline_20260425` | **DEPENDS ON** this track | Embeds the clean resolved graph. |
| `scholarly_metadata_layer_20260425` | **DEPENDS ON** this track | Populates `:Assessment`/`:ScholarVerdict` into the reified structure this track creates. |
| `fix_hadith_data_integrity_20260418` | **PRECEDES** this track (complete) | Canonical source registry / `dataset_row_id` backfill is reused, not redone. |
| `translate_classical_collections_20260418` | **PRODUCES INPUT** to this track's enrich mode | When that track completes, its output `classical_collections_translated.jsonl` is consumed via `npm run db:regen -- --mode=enrich --field=text_english --source=<that file>`. No code change required when it lands — the enrich mode is field-agnostic. Its own deferred status does NOT block this track's `--fullregen` (FR-0.9 includes classical collections with whatever Arabic + partial English exists today; the translation gap is filled later via enrich). |

## 9. Honest Reliability Ledger

| Tier | Status | Notes |
|---|---|---|
| Reified schema + idempotent load on stable keys | **Reliable now** | Phase 0–1. |
| `chain_indx` join (Sunni 99.6% / Imami 84%) | **Reliable now** | Deterministic join, `confidence = 1.0`. |
| Temporal-plausibility flags from `all_rawis` dates | **Reliable now** | Continuity validator (excluded, not deleted). |
| Ambiguous-core ER (kunya collisions) | **Needs validation** | ~83 F1 on Sunni without `chain_indx`; **Imami-gap, transliterated, cross-tradition UNMEASURED** — quarantined, not shipped. |
| GDS-vs-rijāl correlation | **Needs validation** | Downstream (`gds_setup_analytics`), out of scope here. |
| Cross-tradition matn-reuse, link prediction, GraphRAG, automated grading | **Research-grade — defer / label EXPERIMENTAL** | Out of scope (Phase 4). |

**Bottom line:** the graph is honest as a *finding aid* from Phase 1, and
becomes an *analytical engine* only after entity resolution + validation gates.
No GIGO analytic ever ships as a result. No algorithmic output is ever
presented as a *ḥukm*. AR-Sanad / al-Khūʾī are *supplementary* key spaces,
never identity keys.

## 9b. Live-DB gap audit (verified 2026-05-20, drives the test-load contract)

A read-only audit of the live Neo4j (`src/scripts/_audit_gaps.ts`, throwaway —
remove after this track lands) surfaced concrete gaps the regen must address or
explicitly preserve. The test-load (`--mode=test`) presence check has an
acceptance criterion for each:

| Gap | Live count | Disposition |
|---|---|---|
| `SchoolOfThought` mislabel: 4 "tradition" pseudo-schools (Sunni / "Shia Imami" / Ibadi / "Shia Zaydi") used as schools | 4 with 98,029 hadith | **Phase 1 schema cleanup** (FR-1.8 below): retire these from `SchoolOfThought`; school is a fiqh madhhab, tradition is the existing `:ReligiousTradition` |
| `SchoolOfThought` real madhhabs (Hanafi/Maliki/Shafi'i/Hanbali/Ja'fari) with **0 hadith** | 5 unused | **Out of scope for assignment** (madhhab assignment requires scholarly source; defer to `scholarly_metadata_layer`). This track just ensures they survive a fullregen unwiped. |
| Tradition string drift: DB has `"Shia Imami"`/`"Shia Zaydi"`; unified CSV has `"Imami"`/`"Zaydi"` | drift on 100% of those rows | **Phase 0 task 0.7 (NEW)**: canonicalize tradition strings on load to match unified CSV vocabulary; emit a migration count |
| Hadiths with `text_arabic` length <30 (broken/garbled) | **2,254** | **Test-load flag** (`broken_text_ar`): exit non-zero unless `--allow-known-gaps`; record a remediation list per source |
| Hadiths with empty `text_arabic` | 9 | **Test-load fail** (no opt-out — these are unusable) |
| Hadiths missing `text_english` | 381 (all Sunni) | **Test-load warn** (handed off to translate track) |
| Hadiths with English leak/refusal contamination | **0** ✅ | Parser fix held |
| Hadiths with no chain (matn-only) | 36,152 (37%) | **Test-load classify**: legitimate (Imami back-referenced, Sahifat al-Rida, fiqh-only) vs bug-affected (legacy uuid Sunni without extraction). Threshold: legitimate is acceptable; bug-affected is a Phase-2 ER prerequisite. |
| Legacy uuid-keyed Sunni hadiths (the bug damage) | 34,442 | **Fullregen replaces** them with biz-key-keyed nodes; diff mode quarantines them under `legacy_uuid_keyed=true` |
| Narrators with NULL `tradition` | 10,278 (42%) | **Test-load warn**; tradition derived from chain context where possible; the rest handed to `narrator_enrichment` (dependency edge, not duplication) |
| Zero `:Narrator` tagged Imami despite 33,225 Imami hadith | n/a | Same — `narrator_enrichment` |
| `Source.tradition` NULL on all 33 sources | 33 | **Phase 0 task 0.8 (NEW)**: populate Source.tradition from the canonical source registry (`src/lib/constants/sources.ts`) on load |
| Hadiths NOT linked to a `:DatasetVersion` (legacy) | **97,581 of 99,029 (98%)** | Phase 0 task 0.4 backfill: every hadith touched by regen gets `INGESTED_IN` to the new `:DatasetVersion`; legacy untouched rows are tombstoned-by-omission in `--fullregen` mode |
| `DatasetVersion.measured_unknown_fraction = NULL` on all 5 prior regens | 5/5 | **Phase 0 task 0.5 audit/fix**: the property was never written; correct that and backfill the active `:DatasetVersion` |

### **Scope decision (resolved 2026-05-20) — `--fullregen` includes the classical collections**

The live DB has 99,029 hadiths; unified CSV has 69,368. The +29,661 are the
classical collections — **Musnad Ahmad (23,529) + Sunan al-Darimi (2,478) +
Musnad al-Shafi'i (2,054) + Muwatta' Malik (1,856)**. Per user direction, the
fullregen will **include** these. That requires expanding the unified CSV
*before* the Neo4j load: classical collections become rows in
`all_hadiths_unified.csv` and flow through the same reified pipeline as the
other five traditions.

**FR-0.9 (NEW, Phase 0 prerequisite) — Expand unified CSV with classical collections, including sanad + narrator extraction.**
Extend `datasets/hadith-data/regen_unified_csvs.py` to ingest the four classical
collections from their source data (`datasets/.../pure_canon.jsonl` per the
existing `import_classical_collections_20260418` track spec), producing
~99,285 total rows in `all_hadiths_unified.csv`. **Sanad and narrator data
must be carried through** — text alone is not acceptable (per user direction):

  1. Run `extract_isnad_sunni.py` (the existing Sunni Arabic isnad extractor)
     across Ahmad / Darimi / Muwatta classical text; produces `sanad`
     (ordered name array) per hadith with `sanad_confidence`.
  2. **Resolve names to `chain_indx`** by exact + blocked lookup against
     `datasets/narrator-data/all_rawis.csv` (24,326 narrators, the existing
     controlled vocabulary), reusing the same Tier-1/2 logic that Phase 2 of
     this track applies to the rest of the corpus.
  3. Unresolved names become `:NameMention` nodes at load time (per FR-1.3) —
     never silently dropped.
  4. Emit a **classical-narrator coverage report**: count of distinct
     surface-form names from classical collections that found a
     `scholar_indx` in `all_rawis.csv` vs unresolved. If coverage is low (the
     24,326-row authority file is Kutub al-Sittah-centric and Ahmad in
     particular introduces many additional narrators), the unresolved set
     becomes input to `narrator_enrichment_20260425` (dependency edge, not
     duplication here).
  5. Shafi'i is matn-only by source (no isnad — documented in
     `shafii-research.md`); the test load treats this as an allowed per-source
     exception (`{source: 'Musnad al-Shafi'i', isnad_optional: true}`), it is
     NOT a missing-isnad failure.

- Acceptance:
  - Unified CSV record count rises from 69,368 to the measured total (~99,285;
    pinned to `:DatasetVersion.expected_record_count`).
  - All four classical sources appear with `tradition='Sunni'` and the existing
    canonical names from `src/lib/constants/sources.ts`.
  - `sanad` is populated for Ahmad / Darimi / Muwatta rows where extraction
    succeeds (target: same ≥55% Sunni baseline `extract_isnad_sunni.py`
    achieves on Kutub al-Sittah; Shafi'i exempt).
  - `chain_indx` is populated for resolved narrators; the unresolved-narrator
    set is written to `datasets/.../classical_narrator_gap.csv` for handoff to
    `narrator_enrichment`.
  - Classical-narrator coverage report is emitted by `regen_unified_csvs.py`
    and surfaced in the regen run summary.
  - The Shafi'i exception is the only per-source isnad-optional allow-list
    entry on the test-load presence checker.
  - English-translation coverage gap (classical is ~3.6% translated per
    `translate_classical_collections_20260418`) is a test-load `warn`, not
    fail.

Once FR-0.9 lands, the +29k discrepancy is closed and `--fullregen` is
unambiguous: wipe everything covered by the (now-expanded) unified CSV and
reload from it. No classical collections survive outside the unified pipeline,
and their sanad + narrator data flows through the same reified schema +
controlled-vocabulary resolution as the rest of the corpus.

## 9c. Unified runner — one script, three modes (refines FR-0.1)

The Phase 0 scaffold (`src/scripts/regen-isnad-graph.ts`, `npm run db:regen`)
absorbs all per-tradition importers and exposes three modes via a single
entry point. This is the **single test load that verifies metadata + isnad +
narrator presence is correct end-to-end**.

```
npm run db:regen -- --mode=test                # dry-run + presence/integrity checks, no writes
npm run db:regen -- --mode=fullregen           # tombstone old → load unified CSV from scratch
npm run db:regen -- --mode=fullregen --wipe-all  # also wipes preserved classical collections
npm run db:regen -- --mode=diff                # for each row, compare → only write deltas
```

**Common to all modes:**
- Batched (`BATCH_SIZE` env, default 500)
- Parallel (Neo4j-driver concurrent transactions with bounded `CONCURRENCY` env, default 4)
- Structured JSONL log to `logs/regen-<mode>-<datasetVersionId>.jsonl` +
  human-readable progress line every batch
- Idempotent on stable business keys (FR-0.1)
- Honors no-delete: `--fullregen` tombstones via `tombstoned=true` +
  `superseded_by=<DatasetVersion.id>`, never `DETACH DELETE`

**`--mode=test` (the single test load — required acceptance test):**
Asserts every gap row in §9b and emits a per-tradition coverage report:
- CSV-record parity = **69,368** (per-tradition sub-counts match)
- Every required column populated per the tradition-aware coverage rules
- All 6 guardrails (G-1..G-6) green
- Isnad presence: every Hadith has either a `chain_indx`-derived edge set or a
  queued `:NameMention` (no silent drops)
- No `broken_text_ar` (text_arabic <30) above the documented threshold
- No legacy uuid-keyed hadith outside the explicit quarantine set
- Source.tradition populated on every Source
- SchoolOfThought contains only real madhhabs (no tradition pseudo-schools)
- Tradition strings match unified vocabulary (no "Shia Imami" drift)
- Exit code 0 only if all assertions pass (or `--allow-known-gaps` is set and
  the gaps match the documented allow-list)

**Additional functional requirements:**

**FR-1.8 — SchoolOfThought / Tradition disambiguation.** Retire (tombstone, not
delete) the 4 tradition-pseudo-schools from `:SchoolOfThought`; move the
hadith→school edges to `(:Hadith)-[:FROM_TRADITION]->(:ReligiousTradition)`
which already exists at 4 nodes. The 5 real madhhab `:SchoolOfThought` nodes
(Hanafi/Maliki/Shafi'i/Hanbali/Ja'fari) remain present but unassigned in this
track (assignment is `scholarly_metadata_layer`).
- Acceptance: `MATCH (s:SchoolOfThought) WHERE s.name IN ['Sunni','Shia Imami','Ibadi','Shia Zaydi'] AND NOT s.tombstoned RETURN count(s)` = 0.

**FR-1.9 — Tradition string canonicalization on load.** Normalize tradition
strings to the unified-CSV vocabulary: `"Shia Imami" → "Imami"`,
`"Shia Zaydi" → "Zaydi"`. Emit a migration count.
- Acceptance: no `:Hadith` or `:Narrator` has `tradition` matching the legacy
  set after a fullregen.

**FR-1.10 — Source.tradition population.** On every load, set
`Source.tradition` from the canonical source registry
(`src/lib/constants/sources.ts`).
- Acceptance: `MATCH (s:Source) WHERE s.tradition IS NULL RETURN count(s)` = 0
  after a successful run.

**FR-1.11 — Append / enrich mode (`--mode=enrich`).**
A fourth mode for the unified runner that **fills missing values only** —
specifically built so the classical-collections translation track can land
its output incrementally without disturbing other graph data, and so any
future "we got better data for field X" workflow uses the same plumbing.

```
npm run db:regen -- --mode=enrich --field=text_english \
    --source=datasets/hadith-data/classical_collections_translated.jsonl
```

Semantics:
- Generic on field + source. `--field` names the Hadith property to fill;
  `--source` is a JSONL with one record per hadith keyed by the same
  business key the regen uses (`dataset_row_id` else
  `source|hadith_no`), carrying the new field value.
- **Only writes where the target field is empty or missing** on the
  Hadith node. Never overwrites a non-empty value (use `--mode=diff` for
  that). Idempotent: re-running over the same source after success is a
  no-op.
- Every enrich write stamps provenance on the Hadith node:
  `text_english_source = <source-file-path-or-uri>`,
  `text_english_enriched_at = <ISO ts>`,
  `text_english_extraction_method = 'enrich-jsonl'`. (Field-name-prefixed
  so multiple fields can be enriched independently.)
- Producer track for the first use:
  `translate_classical_collections_20260418` (already planned). Its
  documented final output `classical_collections_translated.jsonl` IS the
  expected `--source` for `--field=text_english`. **No spec change to that
  track is required** — this regen track adopts its existing output
  contract.
- Per-source structured log: `logs/regen-enrich-<field>-<dvId>.jsonl` with
  `added` / `skipped_already_filled` / `missing_in_db` / `missing_in_source`
  / `error` counts plus per-row entries.

- Acceptance:
  - A re-run of `--mode=enrich --field=text_english --source=<same file>`
    after a successful first run reports 0 writes (idempotent).
  - For a Hadith with an already-populated `text_english`, the value is
    NOT overwritten and the row is logged `skipped_already_filled`.
  - For a key present in the source JSONL but absent from the DB, the row
    is logged `missing_in_db` (not silently dropped — caller may want to
    audit).
  - Provenance properties (`<field>_source`, `<field>_enriched_at`,
    `<field>_extraction_method`) are set on every enrich-written value.
  - The mode is field-agnostic: `--field=death_year_hijri` etc. is
    supported with the same semantics (no field-specific code branches).

## 9d. Script archive & cleanup (no auto-delete — list for confirmation)

The repo accumulated 32 TS scripts that touched Neo4j ingestion. This track
consolidates ingestion into `regen-isnad-graph.ts` and proposes the following
dispositions. Per `feedback_no_delete_backup.md`, **archive (`git mv` to
`src/scripts/archive/`) — never `rm`**. Each move accompanies a one-line
deprecation note in the archived file's header.

| Action | Files | Reason |
|---|---|---|
| **Keep (active in package.json)** | `init-db.ts`, `regen-isnad-graph.ts`, `remediate-legacy-scalar-assessment.ts`, `seed-historical-data.ts`, `find-parallels.ts`, `ingest-approved-parallels.ts`, `link-sanad-chains.ts`, `backup-db.ts` | Required by current `db:*` commands or live workflows |
| **Replaced by unified `db:regen`** | `import-datasets.ts`, `import-classical-collections.ts`, `import-musnad.ts`, `import-pure-canon.ts`, `import-shia-collections.ts`, `import-zaydi-collections.ts`, `reimport-zaydi.ts`, `apply-schema.ts` | Subsumed; `db:import`/`db:import:clear` removed from package.json |
| **One-off migration (work done)** | `backfill-tradition.ts`, `tag-ibadi.ts`, `migrate-tradition-to-edges.ts`, `migrate-shia-to-imami.ts`, `migrate-source-names.ts`, `rename-anthology-sources.ts`, `fix-name-arabic.ts` | Archive with date-of-last-run note |
| **Move to owning track** | `clean-hadith-text.ts` → `text_cleanup_embedding_prep`; `normalize-grades.ts` → `grade_normalization`; `enrich-narrators-deep.ts`, `enrich-narrators-from-csv.ts` → `narrator_enrichment` | Not Neo4j ingestion concerns |
| **Keep as diagnostics; fold into `db:regen --mode=test`** | `check-traditions.ts`, `verify-db.ts`, `verify-migration.ts`, `diagnose-db.ts`, `data-readiness-audit.ts` | Their checks become acceptance assertions in `--mode=test` |
| **Throwaway (delete after this track)** | `_audit_gaps.ts` | One-shot live-DB audit for this spec; not in package.json |

Implementation as a Phase 1 task (1.8) so it is reversible if any script turns
out to still be needed.

## 10. Out of Scope

- **Phase 3 — Confidence-gated analytics** (GDS ArticleRank/Betweenness/Leiden/
  WCC, `:GraphMetric` nodes, rijāl-Spearman validation) → `gds_setup_analytics_20260425`.
- **Phase 4 — Frontier** (cross-tradition matn-reuse via BGE-M3, link
  prediction, GraphRAG) → defer, label EXPERIMENTAL.
- Narrator biographical enrichment (name_arabic/death_year/region backfill) →
  `narrator_enrichment_20260425`.
- Grade-string normalization (~200 display_grade strings → canonical taxonomy)
  → `grade_normalization_20260425`.
- Embedding generation / semantic search → `vector_embedding_pipeline_20260425`.
- Scholar/ScholarVerdict/Commentary population → `scholarly_metadata_layer_20260425`.
- Any web/admin UI (HITL is JSON-staging + script only).
- RDF/Postgres-AGE engine switch (logical model kept agnostic; flip is a future
  research-only decision, not this track).

## 11. Open Questions (for orchestrator confirmation — defaults applied)

1. **OQ-1 (D-1):** New script + deprecate `import-datasets.ts` (chosen) vs.
   modify in place vs. new script + repoint `npm run db:import`. Default: new
   script, deprecate old.
2. **OQ-2 (D-3):** HITL surface — JSON staging + script (chosen) vs. add a thin
   `/admin` review page vs. add an interactive CLI reviewer. Default: JSON
   staging + ingest script (matches `comparative_ingestion` precedent).
3. **OQ-3 (sequencing):** Confirm reframing `narrator_enrichment_20260425`'s
   "P0 blocks gds" note to `regen → narrator_enrichment → gds`. Default:
   recommend the reframe in `tracks.md`; do not silently edit the other track.
4. **OQ-4 (NFR-3):** Quarantine unmeasured strata (chosen) vs. block Phase 2
   exit until every stratum has a measured F1. Default: quarantine.
5. **OQ-5:** Confirm the Hadith business key precedence:
   `dataset_row_id` when present, else `buildPipelineKey(source, hadith_no)`.

## 12. Acceptance Gate Summary

| Gate | When | Pass condition |
|---|---|---|
| **Phase 0 exit** | After fix-first | Double-run idempotency (identical counts); zero UUID-keyed narrator/hadith MERGEs; `:DatasetVersion` with 69,368 + per-tradition sub-counts + content hash; measured `unknown` fraction recorded. |
| **G1 — Phase 1 exit (STOP-THE-LINE)** | After reified load, before Phase 2 | (a) CSV-**record** parity = **69,368** (and four per-tradition sub-counts); (b) **zero dangling edges**; (c) **100% constraint coverage** (all schema constraints present, applied via `npm run db:init`); (d) per-edge confidence distribution reported; (e) **no analytics shipped**. |
| **Phase 2 exit (STOP-THE-LINE)** | After tiered ER | Tier-1 join coverage meets the verified `chain_indx` percentages; HITL queue **drained or quarantined**; **zero unreviewed `:SAME_AS`**; G-1..G-6 all green; reliability-ledger statuses reported honestly. |
