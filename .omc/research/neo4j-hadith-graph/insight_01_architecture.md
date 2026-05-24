# Insight 01 — Recommended Architecture (Emergent Synthesis)

**Role:** Emergent-Insight Agent 1 (Recommended Architecture)
**Inputs:** all 8 personas + crucible_01 (convergence/tension) + crucible_02 (evidence/feasibility audit)
**Date:** 2026-05-16
**Status of this doc:** decisive recommendation for THIS brownfield repo, with the Contrarian's flip-conditions preserved verbatim as a standing exit.

---

## 0. The one-paragraph answer

Keep Neo4j — it is **already wired, the bug is small, and the high-value contributions need GDS + a vector index** — but treat the engine as *one physical mapping of an engine-agnostic logical model that must be designed first*. The Contrarian is **right about ordering and wrong about discarding what already exists**: the lowest-regret path is not "rip out Neo4j for Postgres/AGE," it is "fix the live UUID idempotency bug, reify the chain + tradition-scoped assessment in an engine-neutral model, gate every analytic on confidence, and defer disambiguation/analytics-as-results to research-grade." The schema mandates (C1–C8) are unanimous and engine-independent; the engine choice is the *only* place real disagreement lives, and the conditions that flip it are explicit in §1.

---

## 1. ENGINE DECISION — resolved, with the Contrarian confronted head-on

### 1.1 The decision

**Recommendation: stay on Neo4j (LPG) for THIS project, now.** Not because the Contrarian is wrong on the merits — the Contrarian's GIGO/ordering argument is the single most important methodological finding in the corpus and is *adopted in full* (see §1.4) — but because the Contrarian's *engine* conclusion was reached without the brownfield fact that decides it.

### 1.2 The decision criteria (explicit, not vibes)

The engine question is a function of five variables. The crucible's T1 table is the spine; this resolves each cell against the *audited* repo reality (crucible_02 §2):

| Criterion | Postgres+AGE / networkx (Contrarian) | RDF/OWL+SPARQL (SemanticHadith path) | **Neo4j (LPG) — chosen** |
|---|---|---|---|
| **Sunk asset** | Discards working `neo4j.ts`/`neo4j-helpers.ts`/`schema.ts`/6 importers/`link-sanad-chains.ts` | Discards same + rewrites as triples | **Reuses all of it**; one bug to fix, not a rewrite |
| **Workload** | Recursive CTE fine for 4–8-deep chains; networkx holds graph in RAM | SPARQL property-path is the regretted path (Historical §3: SemanticHadith *retreated* to materialized edges) | **GDS ArticleRank/Leiden/node2vec + vector index are native**; the two highest-value contributions (cross-tradition matn-reuse, GDS-vs-rijāl validation) need exactly this |
| **Scale** | ~79k hadith / low-100k edges — small; Contrarian correct it doesn't *force* a graph DB | small — doesn't force RDF either | small — doesn't force Neo4j either, but doesn't penalize it; load is sub-minute |
| **Interop / standards** | none gained | **wins decisively** — dereferenceable URIs, `owl:sameAs`, SPARQL federation, DB-layer ontology constraints | LPG cannot mint URIs or federate — the genuine, unrecovered loss (mitigation: n10s/RDF export at §3.5) |
| **Ops burden** | one datastore (Postgres already present) — Contrarian's strongest pragmatic point | new triplestore = new ops | second datastore — real cost, but **already paid** (Neo4j is running) |

Net: four of five criteria favor reuse-Neo4j *for this repo*; the one Neo4j loses (interop/standards) is real and is handled by an RDF *export* path, not an engine switch. On a greenfield repo with no Neo4j and a stated LOD goal, the Contrarian's RDF conclusion would win. This is brownfield with Neo4j already wired — that single fact moves the decision.

### 1.3 Conditions that FLIP the choice (the Contrarian's standing exit — do not bury this)

The crucible's "preserved dissent" is honored as a *contractual trigger*, not a footnote. Flip the engine if **any** of these become true:

- **FLIP → RDF/OWL+SPARQL** if LOD interoperability / federation with SemanticHadith–OpenITI–Wikidata becomes a *stated deliverable goal*, OR DB-layer ontological constraint enforcement (a narrator cannot transmit from someone who died before their birth) becomes a hard requirement rather than an application-layer check. (Contrarian 02a, verbatim: an LPG "cannot mint dereferenceable URIs, cannot be `owl:sameAs`-linked, cannot be SPARQL-federated… building an island next to an emerging archipelago.")
- **FLIP → Postgres edge table + recursive CTE / Apache AGE / networkx** if the deliverable is *ratified as research-dataset-only* with **no interactive product**, AND the team wants to "prove you need Neo4j" before carrying its ops cost, AND no repeated heavy GDS/embedding workload materializes. (Contrarian 02b/02d, verbatim: "Neo4j's value proposition… is a *product* argument, not a *research* argument.") Note: this flip is *cheaper than it looks* because the §2 logical model is engine-agnostic — the same node/edge CSVs load into AGE or a Postgres edge table unchanged.
- **HARD STOP regardless of engine** (the Contrarian's deepest point, 02c, adopted as a release gate, not an engine question): analytics that depend on centrality/common-link are "dangerous as an analytical engine" until entity resolution + Sunni-story-chain parsing + uncertainty propagation are done. This gate (§1.4) binds Neo4j, AGE, RDF, and networkx identically.

### 1.4 The Contrarian's ordering critique — adopted in full, independent of engine

The Contrarian's framing ("the brief front-loads tooling and back-loads data/semantics — that ordering is the core mistake") is **accepted**. The resolution is the dependency chain D0→D8 from crucible_01 §3: engine choice (D0) is *ratified, not assumed*; engine-agnostic schema (D1) is designed before any irreversible investment; entity-resolution authority file (D2) gates every analytic (D7) and all grading-support (D8). Choosing Neo4j does **not** soften this — it is the load-bearing concession to 02 and 08.

---

## 2. THE ENGINE-AGNOSTIC LOGICAL DATA MODEL (designed first)

This is the contract. It holds whether the physical store is Neo4j, Apache AGE, a Postgres edge table, or RDF. Every entity below is justified by ≥3-persona convergence (crucible_01 §1).

### 2.1 Entities

| Logical entity | Definition | Identity key (stable, regen-proof) | Why (convergence) |
|---|---|---|---|
| **Hadith** | One narration instance (matn + bibliographic locus) in one collection | `biz_key = "{source}|{hadith_no}"` (generalize existing `_sunni_key`) | C7 durable skeleton; Systems §3 |
| **Chain (reified Isnad)** | One transmission path for one hadith; a hadith has 1..N | `chain_id = "{hadith_biz_key}#{chain_index}"` | **C2** (6/8 personas); MIS/PROV/GEDCOM-Union |
| **Narrator** | A resolved physical person; tradition-NEUTRAL; carries NO grade/reliability scalar | `RAWI:{scholar_indx}` if resolved into all_rawis; else `EXT:{uuid5(NAMESPACE, normalized_ar_name)}` | **C1+C5+C8**; Systems §3, Neg-Space g |
| **NameMention** | A raw, *unresolved* surface string exactly as it appears in a sanad; participates in the chain *before/without* resolution | `mention_id = "{chain_id}@{position}"` | **C5**; GEDCOM-X Persona vs Subject (Analogical B.2) |
| **Authority (terminus)** | The terminal speaker the report stops at (Prophet ﷺ / named Imam / Companion / Successor / Ahl al-Bayt / unknown). One shared Prophet node across all traditions | `authority_id` (slug) | Journalistic 3.1; maps `classify_attribution.py` `attributed_to` |
| **Assessment** | One grader's verdict on one hadith *within one tradition's scheme*. Never collapsed; absence is representable | `assessment_id = "{hadith_biz_key}#{grade_source}#{grade_scheme}"` | **C1** (7/8 personas — the strongest finding in the corpus) |
| **Grade** | Controlled-vocabulary value node, tradition-scoped, with cross-scheme `ALIGNS_WITH` (approximate) | `grade_uri = "hadith:grade/{scheme}/{label}"` | Analogical D.2 (Hetionet/Mondo) |
| **Collection / Chapter / Tradition** | Bibliographic + tradition scaffold; `tradition` source-of-truth on Collection | natural keys | C7; T2 resolution |
| **DatasetVersion** | One regeneration snapshot (sha256, git_commit, row_count, generated_at) | `version` | **C8**; Systems §4, Neg-Space g |

### 2.2 Logical relationships & where properties live (the load-bearing choices)

- `Hadith —HAS_CHAIN→ Chain` (1..N: multi-isnad is **C3**, first-class, never flattened).
- `Chain —HAS_LINK{position}→ (Narrator | NameMention)` — ordered membership; `position` derived from the *parsed chain index*, never CSV row order (Systems §2c idempotency gotcha).
- `Narrator —NARRATED_FROM{chain_id, position, sigha, edge_confidence, tradition, extraction_method}→ Narrator` — the **fast shortcut edge kept alongside the reified Chain** (PROV sanctions the redundancy; C2). Multigraph: keyed by `(from, to, chain_id)`, never deduped to a node-pair (Analogical E.2). `NameMention` may stand in until resolved.
- `Hadith —ATTRIBUTED_TO{narration_level}→ Authority` — `narration_level` (marfu/imam/mawquf/maqtu/unknown) on the edge; canonical terminus on the node. Direct map of `classify_attribution.py`'s person+level design.
- `Hadith —GRADED_AS→ Assessment —UNDER_SCHEME→ Tradition`; `Assessment —HAS_GRADE→ Grade`. A Sunni *sahih* and a Zaydi verdict are **physically distinct nodes** — cannot collide.
- `NameMention —RESOLVES_TO{confidence, method, asserted_by}→ Narrator` — confidence-qualified, competing resolutions allowed, mention never destroyed (C5).
- `Narrator —IDENTIFIED_WITH{asserted_by, confidence, evidence}→ Narrator` — cross-tradition same-person, **explicit + human-confirmed, NEVER a silent merge** (**C4**, 5/8 personas). Tradition-partitioned identity is preserved; phantom-bridge GIGO (R3) is structurally impossible.
- `Hadith —LOADED_FROM→ DatasetVersion`; tombstone (`retired_at`) never hard-delete (project memory directive + Neg-Space g).

### 2.3 Per-edge provenance & confidence (C6, non-negotiable)

Every `NARRATED_FROM`, `GRADED_AS`, `RESOLVES_TO` carries `source_collection`, `extraction_method ∈ {regex, story_unstructured, manual}`, and (where applicable) `edge_confidence`. Legacy per-hadith `Hadith.sanad_confidence` is kept **immutable** (no-delete); per-edge/per-chain confidence are *added* derived rollups (T3 resolution — not a contradiction once sequenced; per-edge derivation depends on D2 entity resolution).

---

## 3. NEO4J PHYSICAL MAPPING (concrete DDL)

### 3.1 Constraints (run once, before any load — backs MERGE with O(1) index)

```cypher
// Business-key uniqueness (the regen-proof MERGE anchors)
CREATE CONSTRAINT hadith_bizkey   IF NOT EXISTS FOR (h:Hadith)     REQUIRE h.biz_key      IS UNIQUE;
CREATE CONSTRAINT hadith_id       IF NOT EXISTS FOR (h:Hadith)     REQUIRE h.id           IS UNIQUE;
CREATE CONSTRAINT narrator_key    IF NOT EXISTS FOR (n:Narrator)   REQUIRE n.narrator_key IS UNIQUE;
CREATE CONSTRAINT narrator_id     IF NOT EXISTS FOR (n:Narrator)   REQUIRE n.id           IS UNIQUE;
CREATE CONSTRAINT scholar_indx_u  IF NOT EXISTS FOR (n:Narrator)   REQUIRE n.scholar_indx IS UNIQUE;  // already in schema.ts
CREATE CONSTRAINT chain_id        IF NOT EXISTS FOR (c:Chain)      REQUIRE c.chain_id     IS UNIQUE;
CREATE CONSTRAINT mention_id      IF NOT EXISTS FOR (m:NameMention)REQUIRE m.mention_id   IS UNIQUE;
CREATE CONSTRAINT authority_id    IF NOT EXISTS FOR (a:Authority)  REQUIRE a.authority_id IS UNIQUE;
CREATE CONSTRAINT assessment_key  IF NOT EXISTS FOR (s:Assessment) REQUIRE s.assessment_id IS NODE KEY;
CREATE CONSTRAINT grade_uri       IF NOT EXISTS FOR (g:Grade)      REQUIRE g.grade_uri    IS UNIQUE;
CREATE CONSTRAINT collection_id   IF NOT EXISTS FOR (c:Collection) REQUIRE c.collection_id IS UNIQUE;
CREATE CONSTRAINT tradition_id    IF NOT EXISTS FOR (t:Tradition)  REQUIRE t.tradition_id IS UNIQUE;
CREATE CONSTRAINT dsv_version     IF NOT EXISTS FOR (d:DatasetVersion) REQUIRE d.version  IS UNIQUE;
```

### 3.2 Indexes (lookup + relationship-property for confidence-gated GDS projection)

```cypher
CREATE INDEX hadith_attr   IF NOT EXISTS FOR (h:Hadith)   ON (h.narration_level, h.attributed_to);
CREATE INDEX coll_trad     IF NOT EXISTS FOR (c:Collection) ON (c.tradition);
CREATE INDEX asm_scheme    IF NOT EXISTS FOR (s:Assessment) ON (s.grade_scheme, s.grade);
CREATE INDEX narrator_name IF NOT EXISTS FOR (n:Narrator)  ON (n.name_arabic);
CREATE INDEX rel_conf      IF NOT EXISTS FOR ()-[r:NARRATED_FROM]-() ON (r.edge_confidence);
CREATE INDEX rel_chain     IF NOT EXISTS FOR ()-[r:NARRATED_FROM]-() ON (r.chain_id, r.position);
```

### 3.3 Labels & relationship types (physical names)

`:Hadith :Chain :Narrator :NameMention :Authority :Assessment :Grade :Collection :Chapter :Tradition :DatasetVersion`
Rels: `HAS_CHAIN, HAS_LINK{position}, NARRATED_FROM{chain_id,position,sigha,edge_confidence,tradition,extraction_method,source_collection}, ATTRIBUTED_TO{narration_level}, GRADED_AS, UNDER_SCHEME, HAS_GRADE, ALIGNS_WITH{equivalence}, RESOLVES_TO{confidence,method,asserted_by}, IDENTIFIED_WITH{asserted_by,confidence,evidence}, IN_COLLECTION, IN_SECTION, OF_TRADITION, LOADED_FROM`.

> Migration note: existing `schema.ts` already constrains `Narrator.scholar_indx`, `Chain.id`, `Hadith.id` and indexes `Hadith.dataset_row_id`. The reified `Authority`/`Assessment`/`NameMention` labels are **additive**; the existing `link-sanad-chains.ts` `Hadith→MatnVariation→Chain→Narrator` pattern is compatible (MatnVariation can host the BGE-M3 `matn_cluster_id` later). Drop the `Narrator.reliability` index — it encodes the unified-narrator fallacy (R1).

### 3.4 Idempotent narrator upsert — the fix for the LIVE bug

The audited live bug (`src/scripts/import-datasets.ts:373`): `MERGE (n:Narrator {id:$id})` where `id = uuidv4()` minted per run (line 311), `scholar_indx` set `ON CREATE` only → **every re-run duplicates every narrator**. The helpers in `neo4j-helpers.ts` are not on this path. Replacement:

```cypher
UNWIND $rows AS row
MERGE (n:Narrator {narrator_key: row.narrator_key})   // "RAWI:"+scholar_indx | "EXT:"+uuid5
  ON CREATE SET n.id = randomUUID(), n.created_at = datetime(),
                n.scholar_indx = row.scholar_indx, n.name_arabic = row.name_ar
  ON MATCH  SET n.updated_at = datetime()
  SET n.name_english = row.name_en, n.tabaqah = row.tabaqah,
      n.death_year_hijri = row.death_year_hijri, n.birth_year_hijri = row.birth_year_hijri
```

i.e. wire `import-datasets.ts` through `mergeNodeByKey({label:'Narrator', keyProp:'narrator_key', ...})` instead of inline UUID MERGE. Re-runs become no-ops. **This is the S–M, highest-ROI first deliverable** (crucible_02 §4).

---

## 4. HOW EXISTING REPO ASSETS SLOT IN

| Repo asset (verified on disk) | Role in this architecture | Reliability tier |
|---|---|---|
| `datasets/narrator-data/all_rawis.csv` (24,326 rows; `scholar_indx`, `teachers_inds`, `students_inds`) | **The narrator authority / controlled vocabulary.** `narrator_key = "RAWI:"+scholar_indx` is the stable, editorial, regen-proof primary key (Systems §3, C8). `teachers_inds`/`students_inds` seed `NARRATED_FROM` edges and graph-structural blocking for disambiguation (Archaeological c). Sunni-leaning — does NOT cover Imami/Zaydi/Ibadi; absence must be representable (C1). | **reliable-now** as key mechanism; **needs-validation** as coverage % (do NOT promise 94%) |
| Live UUID bug `import-datasets.ts:311,373` | Fixed by §3.4 — MERGE on `narrator_key`, route through `neo4j-helpers.ts`. | **reliable-now** (mechanical) |
| `datasets/classify_attribution.py` (`narration_level` + `attributed_to`, deterministic, conservative `unknown`) | Directly populates `Hadith —ATTRIBUTED_TO{narration_level}→ Authority`. The person+level design *is* the logical model — zero impedance mismatch. | **reliable-now** (structure); attribution accuracy = needs-validation |
| `datasets/hadith-data/sunni_isnad.jsonl` (34,440 rows; ordered `sanad[]`, per-hadith `sanad_confidence ∈ {0,2,…}`, noisy tokens like `"ه سمع علقمة بن وقاص الليثي"`) | Source for `Chain` + `HAS_LINK` + `NARRATED_FROM`; noisy tokens become `:NameMention` (C5) that still participate, kept out of `:Narrator`. `sanad_confidence` stays as immutable `Hadith.sanad_confidence`. | **reliable-now** as navigational structure; **research-grade** as analytical input until D2/D3 done |
| `_sunni_key="{source}|{hadith_no}"` (regen_unified_csvs.py:77-84) | Generalize to `Hadith.biz_key` for ALL traditions (OpenITI: `{source}|{kitab}.{bab}.{hadith}`). | **reliable-now** |
| `neo4j-helpers.ts` (`mergeNodeByKey`, `mergeEdge`, `buildPipelineKey`) | The correct idempotency primitive — currently *aspirational scaffolding* not on the live path. Make it the single load path. | **reliable-now** once wired |
| `link-sanad-chains.ts` (`Hadith→MatnVariation→Chain→Narrator`, fuzzy `normalizeAr`) | The chain-linker; extend its fuzzy match into the two-stage retrieve→rerank (lexicon 94% / hard ~6%). | exact-lookup **reliable-now**; rerank **research-grade** |
| per-collection `PROVENANCE.json` + `schema.ts` `SCHEMA_VERSION` | Extend into the in-graph `:DatasetVersion` node + sidecar manifest + `old_id→new_id` crosswalk. | **reliable-now** |

---

## 5. RELIABILITY TIERS — every component explicitly marked

**RELIABLE-NOW (build the MVP from these — honest because it is structure + provenance + idempotency, asserts no accuracy it cannot back):**
1. Fix the live UUID idempotency bug → MERGE on `RAWI:scholar_indx`/`EXT:uuid5` via `neo4j-helpers.ts` (§3.4).
2. Engine-agnostic logical model §2 → Neo4j DDL §3.1–§3.3 (reified Chain + Authority + tradition-scoped Assessment + NameMention).
3. `all_rawis.csv` as narrator authority; `classify_attribution.py` → `ATTRIBUTED_TO`; generalized `biz_key`.
4. Per-edge provenance + `extraction_method` + immutable legacy `sanad_confidence`; `:DatasetVersion` + crosswalk + tombstone.
5. WCC / shortest-path **structural** continuity *flagging* (a flag, never a munqaṭiʿ verdict).
6. Re-count and pin the real row total (~78.9k on disk — all personas cited a stale 69,368; crucible_02 §0).

**NEEDS-VALIDATION (build, but ship only confidence-stratified + ablation-tested, never as point-value results):**
- Exact-lookup entity resolution (mechanism sound; coverage % unproven on this data — do not promise 94%).
- GDS ArticleRank / Betweenness / Leiden — production *algorithms*, but interpretation corrupted by non-random root-concentrated missingness (R2); reliable only stratified by `sanad_confidence` + ablation, framed "centrality ≠ thiqa".
- Temporal/contemporaneity plausibility pass (depends on death-year/tabaqa metadata capture, R5).

**RESEARCH-GRADE (defer; defensible research contributions but unvalidated on THIS multi-tradition data; several are GIGO or epistemically dangerous if shipped as fact):**
- Two-stage retrieve→rerank disambiguation (AraBERT). Real-text Sunni ceiling ≈ 83 F1; Shia/Zaydi/Ibadi + transliterated chains = **unmeasured**.
- Cross-tradition matn-reuse map (BGE-M3 + Neo4j vector index) — the genuinely novel flagship; candidate-surfacing only, conservative thresholds, human-in-loop.
- GDS-centrality-vs-rijāl validation per tradition (the highest-value publishable experiment — Futurist).
- Link prediction (= "fabricating a ṭarīq" — investigate-only or skip), GraphRAG assistant, tradition-aware automated grading dashboard.
- **Cross-tradition unified narrator node = category error, NOT a deferred feature** — permanently a constraint (C4): tradition-partitioned identity + curated, human-confirmed `IDENTIFIED_WITH` only.

**CROSS-CUTTING RELEASE GATE (binds every engine):** no centrality/community/grading output ships as a result until D2 (entity resolution) + D3 (Sunni-story-chain parsing) are done and D4 uncertainty is propagated. Until then the graph is a sound *finding aid*, not an *analytical engine* — exactly the Contrarian's adopted conclusion.

---

## 6. Decisive questions still owned by the project lead (from crucible_01 §5)

This architecture *presumes* the answers most consistent with brownfield reality but cannot make them: Q1 (research vs product — ratifies/revises the Neo4j premise), Q3 (cross-tradition policy — assumed: partitioned + human-confirmed `IDENTIFIED_WITH`), Q4 (grades only with full provenance + restricted-edition exclusion), Q5 (whether the team has review discipline to ship the matn-reuse/validation work safely). The engine recommendation in §1 is robust to Q1=product and Q1=research-with-GDS; it flips only under the explicit §1.3 conditions.
