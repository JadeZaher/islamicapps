# Strategic Report — Regenerating the Hadith Dataset into a Neo4j Isnad/Narrator Graph

*Deep-research synthesis (8 personas → 2 Crucible → 4 emergent insights → this capstone).
Source docs: `.omc/research/neo4j-hadith-graph/01..08`, `crucible_01/02`, `insight_01..04`.*

## 0. Authoritative ground-truth corrections (verified directly in-repo, not from agents)

The research agents repeatedly tripped on two facts; these are the verified truths the track must use:

1. **Canonical record count = 69,368** (Sunni 34,441 + Imami 33,225 + Ibadi 1,004 + Zaydi 698),
   measured with a real CSV parser (`csv.DictReader`). The "78,951/78,952" figure several
   agents cited is a `wc -l` artifact — Arabic `text_ar` contains embedded newlines (the
   dataset README already warns about this). **Validation gates MUST count CSV records, never
   `wc -l`.**
2. **`all_rawis.csv` lives at `datasets/narrator-data/all_rawis.csv`** (not `hadith-data/`),
   **24,326 rows**, and is far richer than "an authority list": `scholar_indx` (1 = Prophet ﷺ),
   bilingual `name`, `grade`, full genealogy, **`death_date_hijri`/`death_date_gregorian`**,
   and `teachers_inds`/`students_inds` adjacency id-lists. It is simultaneously the controlled
   vocabulary, a prebuilt teacher/student graph, and the temporal authority for contemporaneity
   checks.
3. **`chain_indx` is already populated**: Sunni 34,318/34,441 (99.6%), Imami 27,863/33,225
   (84%), Ibadi/Zaydi 0%. For ~62k of 69k rows the narrator chain is **already mapped to
   `scholar_indx`** — entity resolution for the bulk is a JOIN + audit, not ML.

Net effect: this is **brownfield and far more tractable than the literature implies**. The
ML-heavy entity-resolution narrative applies only to Ibadi+Zaydi (1,702 rows) and the
Imami 16% gap.

## 1. The decision (Contrarian resolved)

**Stay on Neo4j** — but adopt the Contrarian's *ordering* critique as a binding release gate:
data quality and tradition semantics are fixed BEFORE any analytic is exposed. Rationale:
the repo is already wired to Neo4j (`src/lib/db/schema.ts`, `src/scripts/import-datasets.ts`,
`link-sanad-chains.ts`, importers) and the highest-value outputs (GDS-vs-rijāl validation,
cross-tradition matn-reuse) want native GDS + vector index. RDF/LOD interoperability is met
by an **export**, not an engine switch. The logical model is kept **engine-agnostic** so the
Contrarian's flip is cheap if it's ever ratified research-only. Flip conditions (preserved):
→ RDF if LOD federation becomes a stated goal; → Postgres-AGE/networkx if declared
research-only with no product surface.

## 2. Convergent schema (7–8 personas independently)

- **Identity ≠ Assessment** (7/8). Never a scalar `grade`/`reliability` on Narrator/Hadith.
  Verdicts are reified, tradition-scoped `:Assessment {grade, grade_source, grade_scheme}`
  `-[:UNDER_SCHEME]->(:Tradition)`. A Sunni *ṣaḥīḥ* and a Zaydī verdict are *physically
  incapable* of overwriting each other; absence is explicit (`no_extant_evaluation`), so
  Zaydī/Ibāḍī never silently inherit a Sunnī grade.
- **Reify the isnad as a `:Chain` node** (6/8) with a fast shortcut `NARRATED_FROM` edge
  retained for SNA (two-layer model: raw bipartite + materialized weighted projection).
- **Multi-isnad first-class** (5/8); **NameMention (surface form) vs resolved Narrator**
  (5/8); **cross-tradition links are explicit, reviewed, reversible `:SAME_AS`, never silent
  merges** (5/8).
- **Per-edge `confidence` + `extraction_method` + provenance**; weak edges are *excluded by
  GDS projection predicates, never deleted* (tombstone rule, matches the standing
  no-delete directive). `:DatasetVersion` node + content-hash so regen is reproducible and
  node IDs do not churn.

## 3. Two live bugs (fix-first, Phase 0)

Verified in `src/scripts/import-datasets.ts`:
1. **Narrator duplication**: narrators are `MERGE`d on a fresh `uuidv4()` per run → every
   re-run duplicates every narrator. Fix: `MERGE` on `RAWI:scholar_indx` (or the
   `source|hadith_no` business key for hadith), via the existing `neo4j-helpers.ts`
   conventions that the live importer currently bypasses.
2. **Unified-narrator fallacy in production**: importer stores `n.reliability` as a node
   scalar — the #1 ranked risk, shipping today. Remove; replace with reified Assessment.

## 4. Entity resolution — tiered, mostly a join

1. **`chain_indx` join** (Sunni 99.6%, Imami 84%) → direct `scholar_indx` edges. Audit-only.
2. **Exact/blocked lexicon lookup** against `all_rawis.csv` for the rest, reusing
   `classify_attribution._norm` for Arabic normalization.
3. **Ambiguous collision core** (kunya like "Abū Jaʿfar" = al-Kulaynī vs al-Bāqir vs
   al-Jawād): graph-prior retrieve → BERT cross-encoder rerank → confidence, using the
   existing `narration_level`/`attributed_to` outputs and `all_rawis` nasab/tabaqa/dates as
   free features. **Mandatory human-in-the-loop** for the ambiguous core and **every**
   cross-tradition `:SAME_AS`.
4. **Honest ceilings**: ~83 F1 on real Sunni text without `chain_indx`; Imami-gap,
   transliterated, and cross-tradition are **unmeasured** — must be measured, not assumed.
   AR-Sanad / al-Khūʾī are *supplementary* key spaces, never identity keys.

## 5. Phased roadmap (stop-the-line gates)

- **Phase 0 — Fix-first**: the two live bugs; pin canonical count = 69,368 via a
  `:DatasetVersion` node (CSV-record count, not `wc -l`); generalize the stable business
  key; measure the *real* unknown-attribution fraction (the "~12%" is unverified).
- **Phase 1 — Honest foundation**: load the reified engine-agnostic schema (Chain /
  Authority-terminus / tradition-scoped Assessment) with per-edge confidence + provenance.
  **No analytics.** Exit gate G1: record-count parity (=69,368), zero dangling edges,
  100% constraint coverage, confidence distribution reported.
- **Phase 2 — Entity resolution**: the tiered pipeline above; exit gate = ambiguous-core
  HITL queue drained or quarantined; no cross-tradition `:SAME_AS` unreviewed.
- **Phase 3 — Confidence-gated analytics (decision-support only)**: GDS
  ArticleRank/Betweenness (≈ *madār*), Leiden (transmission schools), WCC + shortest-path
  (*munqaṭiʿ* flags) — every projection carries a confidence/level predicate; metrics
  segregated to `:GraphMetric` nodes, never rijāl-named, never on Assessment; rijāl-Spearman
  validation required before any UI exposure.
- **Phase 4 — Frontier (optional, labeled EXPERIMENTAL)**: cross-tradition matn-reuse
  (BGE-M3), link-prediction (`hypothesis_for_takhrij` only — never asserts a *ṭarīq*),
  GraphRAG.

## 6. Six enforceable guardrails (each with an acceptance test)

1. Identity≠Assessment — schema constraint; test: a scalar grade on Narrator/Hadith returns 0.
2. Confidence-stratified analytics — CI linter rejects a GDS projection without a confidence
   predicate; a GIGO report (strata + ablation Spearman + dataset version) gates metric display.
3. Non-authority framing — metrics on `:GraphMetric` only; serializer refuses emission without
   the "kathrat al-riwāya, not ʿadāla/ḍabṭ" disclaimer; no global authenticity score.
4. Provenance & copyright — every grade/edge carries source+edition; `:Source.license_status`
   blocks redistribution of restricted critical-edition apparatus.
5. Cross-tradition safety — `:SAME_AS` explicit, human-confirmed, reversible, audited;
   split-vs-confirmed projection switch.
6. Temporal plausibility — contemporaneity pass using `all_rawis` death dates flags
   `impossible`/`unknown` transmission edges as a continuity validator (excluded, not deleted).

## 7. Coordination with existing Conductor tracks

Existing tracks already cover adjacent scope: `narrator_enrichment_20260425`,
`scholarly_metadata_layer_20260425`, `gds_setup_analytics_20260425`,
`grade_normalization_20260425`, `vector_embedding_pipeline_20260425`,
`fix_hadith_data_integrity_20260418`. The new track must be the **Neo4j regeneration /
ingestion pipeline** (Phases 0–2): it owns the fix-first bugs, the reified idempotent schema,
and `chain_indx`-driven narrator edges, then **hands off** to `gds_setup_analytics` (Phase 3
analytics) and consumes `narrator_enrichment`/`grade_normalization` outputs rather than
re-deriving them. Explicit dependency edges, not duplication.

## 8. Honest reliability ledger

- **Reliable now**: reified schema; idempotent load on stable keys; `chain_indx` join for
  Sunni/Imami; temporal-plausibility flags from `all_rawis` dates; ArticleRank/Leiden/WCC
  as *decision-support* with confidence gating.
- **Needs validation**: ambiguous-core ER (~83 F1 Sunni; Imami/cross-tradition unmeasured);
  GDS-vs-rijāl correlation.
- **Research-grade (defer / label experimental)**: cross-tradition matn-reuse, link
  prediction, GraphRAG, any automated grading.

**Bottom line**: the graph is honest as a *finding aid* from Phase 1, and becomes an
*analytical engine* only after entity resolution + validation gates. No GIGO analytic ever
ships as a result, and no algorithmic output is ever presented as a *ḥukm*.
