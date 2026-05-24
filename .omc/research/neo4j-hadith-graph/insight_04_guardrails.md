# Emergent Insight 04 — Guardrails & Scholarly Integrity

**Agent:** Emergent-Insight 4 (Guardrails & Scholarly Integrity)
**Inputs synthesized:** 08_negative_space, 02_contrarian, 07_futurist, 05_journalistic, crucible_01_convergence, crucible_02_evidence (01/03/04/06 skimmed)
**Date:** 2026-05-16

> **Purpose.** Six non-negotiable guardrails that keep a cross-tradition isnad graph scholarly-honest rather than GIGO or sectarian. Each is a *contract*, not advice: a named failure it prevents, a concrete schema- or process-level enforcement (Cypher constraint, ingest gate, projection predicate, or review step), and an executable acceptance test that fails loudly if the guardrail is violated. The crucible established these as engine-agnostic (they hold whether the store is Neo4j, Apache AGE, or Postgres) and as the most robust finding in the corpus (C1–C8). Brownfield reality (crucible_02 §2): a Neo4j layer already exists and the live importer `import-datasets.ts:370-389` mints `uuidv4()` per run — Guardrails 1, 4, 5 are currently *violated in production* and must be fixed first.

---

## GUARDRAIL 1 — IDENTITY ≠ ASSESSMENT (schema-enforced, tradition-scoped, absence-honest)

**Failure prevented (R1, the rank-1 risk; 7 of 8 personas).** A unified `Narrator`/`Hadith` node carrying a scalar `grade`/`reliability` property silently *picks a winner* — whichever tradition's rijāl corpus was scraped first — and erases the inter-tradition disagreement that *is* the scholarly content of ʿilm al-rijāl. Zaydi/Ibadi/Rida material, which has little-to-no digitized jarḥ-wa-taʿdīl, gets the Sunni verdict by silent default. A scalar grade is also incommensurable across schemes (al-Albānī "ṣaḥīḥ" ≠ classical "ṣaḥīḥ" ≠ Imāmī "ṣaḥīḥ li-ghayrihi" ≠ Zaydī judgment).

**Concrete enforcement (schema-level).**
- `grade`, `reliability`, `tawthiq` are **forbidden as properties** on `:Narrator` and `:Hadith`. A verdict is a reified node: `(:Hadith)-[:GRADED_AS]->(:Assessment)-[:UNDER_SCHEME]->(:Tradition)` and `(:Narrator)-[:EVALUATED_BY]->(:Assessment)`.
- `:Assessment` **node-key**: `assessment_id` unique; **mandatory non-null** `grade`, `grade_source` (the critic/work, e.g. `al-Najashi`, `al-Albani`), `grade_scheme` ∈ `{sunni, imami, zaydi, ibadi, rida}`. Enforced by `CREATE CONSTRAINT … IS NODE KEY` + property-existence constraints (Neo4j Enterprise) or an ingest-time assertion (Community/AGE/Postgres).
- One narrator/hadith carries **N contradictory `:Assessment` nodes**; they cannot overwrite each other because they are physically distinct nodes filtered by `grade_scheme` at query time.
- **Absence is a first-class value, not inheritance.** Where a tradition has no extant verdict (much Zaydi/Ibadi/Rida), store an explicit `(:Assessment {grade:'none', grade_scheme:'zaydi', reason:'no_extant_evaluation_in_tradition'})` — *never* let a Sunni assessment satisfy a Zaydi query. `tradition` is a query-time projection; it is **never** a scalar on `:Narrator` (per tension T2: denormalize tradition onto Collection/Hadith/Chain/edge/Assessment, never onto the tradition-neutral person).

**Acceptance test (must pass before any analytic/UI ships).**
1. `MATCH (n:Narrator) WHERE n.grade IS NOT NULL OR n.reliability IS NOT NULL RETURN count(n)` → **must be 0**.
2. `MATCH (a:Assessment) WHERE a.grade IS NULL OR a.grade_source IS NULL OR a.grade_scheme IS NULL RETURN count(a)` → **must be 0**.
3. Seed a known cross-tradition narrator (a name reliable in Imāmī rijāl, weak in Sunni). Query under `grade_scheme:'sunni'` then `'imami'` → must return **two different verdicts**; neither query may return the other's grade.
4. Pick a Zaydi hadith with no digital verdict. Query its assessment under `grade_scheme:'zaydi'` → must return `reason:'no_extant_evaluation_in_tradition'`, **not** an empty result and **not** a Sunni grade. (Empty result = silent inheritance failure.)

---

## GUARDRAIL 2 — CONFIDENCE-STRATIFIED ANALYTICS (the GIGO gate before any metric)

**Failure prevented (R2, the single strongest objection; Contrarian 02c + Negative-Space 08b).** The missingness is **structured, not random**: the ~12% unknown attribution and the unparsed Sunni story-form chains are concentrated at the *early-generation common-link root* (muʿallaq/taʿlīq drop the Companion end). Dropping them **inflates the apparent centrality of canonical Sunni hubs** (al-Zuhrī, Nāfiʿ, the Imams) and manufactures artificially tight communities, systematically under-representing Shia/Zaydi/Ibadi structure. PageRank/Leiden return *confidently wrong* numbers with no error raised. (Note crucible_02 §0: the "69,368" and "12%" figures are themselves unverified — disk is ~78.9k rows — which *strengthens* this guardrail: the uncertainty is worse than assumed.)

**Concrete enforcement (process + projection-level).**
- **Every GDS projection MUST carry a confidence predicate and an `extraction_method` filter.** No projection without `WHERE r.edge_confidence >= $threshold` and `r.extraction_method IN $methods`. A projection Cypher lacking both is rejected in code review and by an automated linter on the projection registry.
- Low-confidence edges are **never deleted** (project no-delete directive) — they are *excluded by predicate*, so different analyses pick different thresholds and the exclusion is auditable.
- **The GIGO test, run and recorded before any metric is displayed:**
  (a) Run the metric on the high-confidence subgraph; then on the full graph; **report as a range across confidence strata, never a point value.**
  (b) **Ablation:** randomly delete an additional 5/10/20% of edges; compute Spearman ρ of top-k centrality vs. baseline. If top-k is unstable under loss comparable to the known missingness, **publish the instability instead of the ranking.**
  (c) **Exclude unparsed Sunni story-form chains from any cross-tradition centrality comparison** (never compare a regex-parsed tradition against an unparsed one — that result is a format artifact).
- A metric may be shown in dataset/UI **only if** an accompanying `gigo_report` artifact exists for it (stratum range + ablation ρ + dataset version). Missing artifact ⇒ metric is suppressed.

**Acceptance test.**
1. Projection-registry linter: every registered projection's Cypher contains an `edge_confidence` predicate and an `extraction_method` filter → CI **fails** on any that do not.
2. For each shipped metric, assert a `gigo_report` row exists with non-null `{strata_range, ablation_spearman, dataset_version}`; absence ⇒ test fails and the metric is not rendered.
3. Ablation regression: re-run the 10% edge-drop ablation; if top-20 ArticleRank Spearman ρ < a pre-registered threshold (e.g. 0.7), the build **flags the metric "unstable — do not present as result"** automatically.
4. Cross-tradition guard: any query joining centrality scores across `grade_scheme` values where one side has `extraction_method='story_unstructured'` → must raise a `format_confounded` warning, not return a silent comparison.

---

## GUARDRAIL 3 — NON-AUTHORITY FRAMING (centrality ≈ kathrat al-riwāya, never ʿadāla/ḍabṭ)

**Failure prevented (R8; Futurist 07 non-negotiable principle + Negative-Space 08f + Contrarian 02c).** Presenting a computed centrality, community, or link-prediction output as a verdict is, across five living traditions, an implicit **sectarian ḥukm made by a script** — a takfīr-adjacent claim against the disadvantaged tradition. Graph topology measures *transmission volume/pivot status* (kathrat al-riwāya, being a madār); it is **not** moral probity (ʿadāla) or precision of memory (ḍabṭ), which live in the kutub al-rijāl, not the chain. A high-ArticleRank narrator can be a prolific liar (matrūk). Link-prediction asserting a probable edge is, in hadith terms, **fabricating a ṭarīq**.

**Concrete enforcement (schema label + UI contract + process).**
- Algorithmic outputs are written to **distinctly-labeled, segregated nodes/properties**: `:GraphMetric {kind:'articlerank'|'betweenness'|'leiden'|'link_prediction', value, dataset_version, projection_id}` attached via `(:Narrator)-[:HAS_METRIC]->(:GraphMetric)`. They are **never** written onto `:Assessment` and never named with rijāl vocabulary (`thiqa`, `daʿīf`, `ṣaḥīḥ`). A constraint/lint forbids `:GraphMetric` from carrying a `grade`-named property.
- **Mandatory disclaimer binding.** Any serialization (API, UI panel, export, GraphRAG answer) that includes a `:GraphMetric` MUST co-emit the fixed string: *"Topological signal (kathrat al-riwāya / madār). Not a verdict of ʿadāla or ḍabṭ. Investigate via ʿilm al-rijāl; consult the tradition-scoped Assessment."* The serializer rejects emission of a metric without the bound disclaimer field.
- **Link-prediction is "investigate", never "exists":** `:PredictedLink {status:'hypothesis_for_takhrij'}` only; it may never be promoted to a `:Chain`/`NARRATED_FROM` edge by any automated path. Promotion requires a human-confirmed provenance record (ties to Guardrail 5's review gate).
- **No global authenticity score.** Any score is tradition-scoped, labeled with its scheme, and rendered alongside dissenting traditions' verdicts. A single composite "authenticity" field is forbidden at schema level.

**Acceptance test.**
1. `MATCH (m:GraphMetric) WHERE any(k IN keys(m) WHERE k IN ['grade','thiqa','daif','sahih','reliability','authenticity']) RETURN count(m)` → **must be 0**.
2. Serializer contract test: request any payload containing a `:GraphMetric`; assert the exact disclaimer string is present. Strip it → serializer test **must fail** (disclaimer is non-optional).
3. `MATCH (:PredictedLink)-[r:NARRATED_FROM]->() RETURN count(r)` and assert no `NARRATED_FROM`/`HAS_CHAIN` edge has provenance `derived_from:'link_prediction'` → **must be 0** (no laundered ṭarīq).
4. Schema scan: assert no node label or property anywhere named `authenticity_score`/`global_grade` → fails build if present.

---

## GUARDRAIL 4 — PROVENANCE & COPYRIGHT (every grade/edge sourced; no apparatus laundering; reproducible)

**Failure prevented (R6 + R7; Negative-Space 08c/08g, Systems via crucible).** A bare `grade="sahih"` is scholarly meaningless *and* a legal hazard: the only source of many modern grades is 20th–21st-c. copyrighted critical apparatus (al-Albānī, Shuʿayb al-Arnaʾūṭ, Dār al-Salām). Regenerating those verdicts into a redistributable dataset **launders protected critical labor** while the medieval matn/isnad is public domain. Separately, IDs derived from row-order/UUID/auto-increment **reshuffle every regeneration** ("node 4471" becomes a different person; the volatile 12% churns most), silently breaking longitudinal and external citations — this is the **current live bug** (`import-datasets.ts` mints `uuidv4()` per run; re-run duplicates every narrator).

**Concrete enforcement.**
- **No bare grade.** Ingest rejects an `:Assessment` whose `grade_source`/`work`/`edition` are absent, or sets `grade_unsourced=true` and **excludes it from all authoritative queries/UI** by predicate.
- `:Source {source_id, work, edition, year, license_status}` with `license_status ∈ {public_domain_classical, modern_critical_edition_restricted}`. `(:Assessment)-[:CITED_FROM]->(:Source)` mandatory. **Restricted-edition verdicts are not redistributed** — export stores a citation/pointer, never the verdict text. Export filter: `WHERE s.license_status <> 'modern_critical_edition_restricted'` for the grade value column.
- **Content-stable, semantically-anchored IDs.** Narrator key = `RAWI:{scholar_indx}` (the existing 24,326-row authority file) → fallback `EXT:uuid5(NAMESPACE, normalized_arabic_name + disambiguator)`. Hadith key = `{source}|{hadith_no}`. **All loads `MERGE` on the business key — never `uuidv4()`.** Fix the live importer to route through `neo4j-helpers.ts` (`mergeNodeByKey`).
- `(:DatasetVersion {version, content_hash, generated_at})`; every node carries `first_seen_version`/`last_seen_version`; an `old_id→new_id` crosswalk (`added/removed/merged/split`) is emitted per regeneration; **tombstone, never delete** (project directive). Every shipped metric is pinned to a `dataset_version`.

**Acceptance test.**
1. `MATCH (a:Assessment) WHERE NOT (a)-[:CITED_FROM]->(:Source) AND coalesce(a.grade_unsourced,false)=false RETURN count(a)` → **must be 0**.
2. Export a sample; assert no row exposes a verbatim grade whose `:Source.license_status='modern_critical_edition_restricted'` (only a citation pointer permitted) → test fails on any leak.
3. **Idempotency test (closes the live bug):** import the full dataset, snapshot `count{:Narrator}` and `count{:Hadith}`; re-run the importer unchanged; counts must be **identical** (delta = 0). Current code fails this — it is the first deliverable.
4. **Reproducibility test:** regenerate the dataset; assert a stable narrator (anchored by `scholar_indx`) retains the same node key across versions and that a crosswalk row exists for every `added/removed/merged/split`. A churned key with no crosswalk entry ⇒ fail.

---

## GUARDRAIL 5 — CROSS-TRADITION SAFETY (SAME_AS is explicit, reviewed, reversible — never a silent merge)

**Failure prevented (R3; C4, 5 personas).** Sunni and Shia ʿilm al-rijāl are **different evaluative systems with different objects** (~75% of Rijāl al-Ṭūsī concerns book-compilers, not oral transmitters; transmission networks are largely non-overlapping). A unified node or silent merge across traditions **manufactures phantom transmission bridges that never existed in history**, which then dominate betweenness/community results — GIGO that encodes a contested theological premise as fact.

**Concrete enforcement.**
- Narrator identities are **tradition-partition-able**: each `:Narrator` is tradition-neutral, but cross-tradition equivalence is *only* an explicit edge `(:Narrator)-[:SAME_AS {confidence, evidence, asserted_by, asserted_at, status}]->(:Narrator)`. **No automated process may MERGE two narrator nodes across traditions.** The importer/resolver may only *create `SAME_AS` candidates* with `status:'unconfirmed'`.
- A `SAME_AS` edge enters analytics **only when `status:'human_confirmed'`** with a non-null `asserted_by` and `evidence`. It is **reversible** (set `status:'rejected'`, tombstone — never delete the audit trail).
- GDS projections expose a **partition switch**: analytics can run under (i) split hypothesis (ignore all `SAME_AS`), (ii) confirmed-merge hypothesis (`SAME_AS{status:'human_confirmed'}` only). Reporting a metric without stating which hypothesis was used is forbidden (ties to Guardrail 2's `gigo_report`).

**Acceptance test.**
1. Run the full ingest + resolver on a fixture containing a known Sunni/Imāmī homonym pair. Assert **two distinct nodes remain** and only an `unconfirmed` `SAME_AS` candidate exists — `count` of merged single nodes must be 0.
2. `MATCH ()-[r:SAME_AS]->() WHERE r.status='human_confirmed' AND (r.asserted_by IS NULL OR r.evidence IS NULL) RETURN count(r)` → **must be 0**.
3. Run centrality under split vs confirmed-merge hypotheses on a fixture with one phantom-bridge candidate; assert the top-k changes (proving the switch is real) and that the default/unspecified call **refuses** to return without a stated hypothesis.
4. Reversibility: confirm a `SAME_AS`, then reject it; assert the audit trail (both transitions) is retained (tombstoned, not deleted).

---

## GUARDRAIL 6 — TEMPORAL PLAUSIBILITY (contemporaneity as a continuity validator + data-quality flag)

**Failure prevented (R4; Negative-Space 08e — "the cheapest high-value validation the whole field skips").** Every published computational isnad graph drops death/birth years, so it **cannot** check that a student could have met the teacher. Temporally impossible edges (a regex artifact, or a real munqaṭiʿ/mursal break) are presented with the **same analytical weight as sound ones**, and PageRank flows through historically impossible links.

**Concrete enforcement.**
- Capture (nullable, ranged) `death_year_h`, `birth_year_h`, `tabaqa`, `locations[]` on `:Narrator` with `*_uncertain` flags (R5 metadata; enables this check).
- **Automated temporal-plausibility pass** over every `NARRATED_FROM(teacher→student)`: set `temporal_plausibility ∈ {ok, suspect, impossible, unknown}` — `impossible` if `student.birth_year_h > teacher.death_year_h` (or overlap window implausibly short); `unknown` when dates missing (its **own bucket — never silently `ok`**).
- `impossible` edges are **excluded from analytics by default** (predicate, not deletion) and surfaced as **dual findings**: candidate extraction error *or* candidate inqitāʿ — both are results, not noise to hide. This is a *continuity validator and data-quality flag*, never an authenticity verdict (Guardrail 3 framing applies).

**Acceptance test.**
1. Seed an edge where `student.birth_year_h > teacher.death_year_h`; run the pass; assert that edge gets `temporal_plausibility='impossible'` and is **absent from the default GDS projection**.
2. Seed an edge with a missing date; assert `temporal_plausibility='unknown'` (not `'ok'`) — a missing-date edge classified `ok` ⇒ test fails.
3. Assert the `impossible` set is queryable as a findings report (extraction-error vs inqitāʿ candidates), i.e. excluded-but-not-deleted.
4. Regression: total edge count before/after the pass is unchanged (flag-not-delete invariant).

---

## Cross-guardrail invariants (apply to all six)

- **Never delete; tombstone + version.** Every guardrail excludes by predicate or marks status, never destroys data (project no-delete directive; reproducibility C8).
- **Engine-agnostic.** Constraints expressed as Neo4j `CONSTRAINT`/`NODE KEY` degrade to ingest-time assertions in AGE/Postgres; the contract (not the syntax) is the guardrail.
- **Descriptive, not prescriptive, everywhere.** The system reports *who said what* with provenance; it never issues a ḥukm of its own (Guardrails 1, 3).
- **Gate order is load-bearing** (crucible dependency chain D1→D8): Identity≠Assessment schema (G1) and stable IDs (G4) before any analytic; confidence-stratification (G2), non-authority framing (G3), SAME_AS discipline (G5), temporal pass (G6) before any metric or grading-support ships. Violating the order produces confidently-wrong output.
