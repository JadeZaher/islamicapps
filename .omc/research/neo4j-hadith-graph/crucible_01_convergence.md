# Crucible 01 — Convergence & Tension Analysis

**Role:** Crucible Agent 1 (Convergence & Tension Analysis)
**Inputs:** 01_historical, 02_contrarian, 03_analogical, 04_systems, 05_journalistic, 06_archaeological, 07_futurist, 08_negative_space
**Date:** 2026-05-16

This document distills where the eight personas independently agree (high confidence), where they genuinely disagree (decisions the project must make), the build dependency chain, the ranked risk register, and the decisive questions the project lead must answer before building. Dissent — especially the Contrarian's — is preserved, not smoothed.

---

## 1. STRONG CONVERGENCE — claims independently reached by ≥3 personas

These are the high-confidence findings. They matter because the personas reached them from *different directions* (history of prior art, analogical porting from other KG domains, pipeline engineering, failure-mode hunting, future techniques, deep entity-resolution mechanics, practitioner how-to, contrarian skepticism). Independence of method is what makes the agreement load-bearing.

### C1. Identity ≠ Assessment: never store a scalar grade/reliability on a Narrator node. Reify the verdict, tradition-scoped. — **7 of 8 personas**

- **Negative-Space (08, gap a)**: "Never store a scalar `reliability` on a Narrator node" — names it the single most destructive error; tradition-specific taʿdīl/tajrīḥ *is* the point of rijāl science. Absence (Zaydi/Ibadi with no extant verdict) must be representable, not inherited from Sunni.
- **Contrarian (02, e)**: a unified narrator node with a single grade "reifies an identity claim that the traditions themselves reject"; Sunni and Shia *ʿilm al-rijāl* are different evaluative systems with different objects (~75% of Rijāl al-Ṭūsī concerns book-compilers, not oral transmitters).
- **Archaeological (06, d)**: "Identity resolution and assessment ingestion are separate passes… Never collapse `Assessment` nodes." Models one identity node + N tradition-tagged `:Assessment` nodes.
- **Journalistic (05, 3.4)**: "Hard rule: never put `grade` as a property on `Hadith`." One reified `Assessment` per (hadith, source, scheme); Sunni *sahih* and Zaydi verdict are physically distinct nodes, filtered by `grade_scheme`.
- **Analogical (03, D.2 / table row 5 & 7)**: grade is a controlled-vocabulary node, tradition-scoped (Hetionet/Mondo pattern); cross-tradition identity is a curated link, never a hard merge (GEDCOM GFG).
- **Futurist (07, Part C.4 + non-negotiable principle)**: the `grade` field is "ground truth and evaluation target, never a model output presented as authority"; train/interpret per tradition — a single global classifier on mixed-tradition grade is "methodologically invalid."
- **Historical (01, §8)**: durable skeleton includes a separate `Class`(grade) entity; surface-form-only identity is the recurring regret (KITAB 1,070 names → 25 individuals).

**Why independence matters:** the failure-hunter, the skeptic, the entity-resolution specialist, the practitioner, the analogy-porter, the futurist, and the historian all arrived at the *same schema mandate* from unrelated evidence bases. This is the most robust finding in the entire corpus and should be treated as a hard constraint, not a design option.

### C2. Reify the isnad/chain as a first-class node; keep a fast shortcut narrator→narrator edge alongside it (two-layer model). — **6 of 8 personas**

- **Analogical (03, executive thesis + §B.1, §C, §E)**: the single most consequential decision; every mature analogous KG (OpenAlex `Authorship`, W3C PROV `Derivation`, GEDCOM `Union`, MIS, SemanticHadith) reified the relationship. Recommends hybrid: plain `NARRATED_FROM` for algorithms + `Isnad` node for provenance — PROV explicitly sanctions the redundancy.
- **Journalistic (05, §1, §2)**: "Reject" the bare relationship; a `Chain` node sits between Hadith and ordered narrator links; single-linked `NARRATED_FROM` carries chain_id/position/term/confidence.
- **Historical (01, §2, §8)**: Van Bruggen's two-layer design (raw bipartite for fidelity + materialized weighted mono-partite for GDS) is "the key architectural takeaway"; "do not collapse to one layer."
- **Futurist (07, Part A projection)**: keeps a directed transmission graph for GDS while the underlying chain structure is preserved; aggregated/weighted projection for centrality.
- **Negative-Space (08, gap d)**: model hadith→chain as first-class multi-chain `(:Hadith)-[:HAS_CHAIN]->(:Chain)-[:LINK {order, mode, tahwil_branch}]->(:Narrator)`; "never collapse a hadith to one path."
- **Systems (04, §2c)**: idempotent isnad edges keyed by ordered position; chain links carry position derived from parsed chain index.

**Why independence matters:** the analogy-porter derived it from four unrelated external domains; the historian derived it from 2014→2026 prior-art regret; the failure-hunter derived it from multi-chain corroboration loss; the practitioner derived it from Neo4j modeling guidance. Convergent reification across these lenses is decisive.

### C3. Multi-isnad is first-class: one hadith fans out to N parallel chains; never flatten to one path. — **5 of 8 personas**

- **Historical (01, §1, §8)**: MIS's "ISNAD count" is "the single most important durable schema idea"; essential where the same matn recurs across traditions.
- **Analogical (03, §E.2)**: multigraph keyed by (hadith_id, chain_id), "never dedupe to a simple narrator-pair edge."
- **Journalistic (05, 3.5)**: solved structurally by the `Chain` node, cardinality 1→N, mark strongest `is_primary`.
- **Negative-Space (08, gap d)**: collapsing to one path "destroys corroboration (mutābaʿāt/shawāhid) analysis"; also flags taḥwīl (ح) mishandling as a silent fabrication/destruction of links.
- **Futurist (07)**: MIS multi-directed model (2,092 nodes / 77,797 edges) referenced as the corroboration-preserving precedent.

### C4. Cross-tradition same-person link must be an explicit, evidence-tagged `SAME_AS`/`IDENTIFIED_WITH` edge — NEVER a silent node merge. — **5 of 8 personas**

- **Contrarian (02, e)**: a naive merge "manufactures spurious cross-tradition paths — phantom bridges that never existed… which will then dominate betweenness/community results." Tradition-partitioned identifiers + explicit sourced links.
- **Analogical (03, §B.1, table row 7)**: GEDCOM GFG multi-graph linking — cross-tradition identity = curated `IDENTIFIED_WITH` with provenance, traditions stay distinct.
- **Archaeological (06, d/e/f)**: auto-suggest `:SAME_AS`, "never auto-merge"; require human confirm (theological/historical stakes); one identity node + N tradition-tagged assessments.
- **Negative-Space (08, gap a)**: expose ambiguous identities (`possibly_same_as`) as soft links, so analysts can run metrics under both merge and split hypotheses.
- **Journalistic (05, §2.2)**: `(:Narrator)-[:SAME_AS]->(:Narrator)` as identity-merge *candidates* (optional), not a hard merge.

### C5. The data is the bottleneck: narrator entity resolution must be a dedicated pass (canonical IDs + alias list, NOT regex/surface form); analytics are misleading until it is done and uncertainty is propagated. — **6 of 8 personas**

- **Contrarian (02, c)**: "the single strongest argument against proceeding now." GIGO is acute because missingness is *correlated with the analytical target* (muʿallaq chains drop the early/common-link root). "Ship the analytics with confidence intervals or do not ship the analytics."
- **Negative-Space (08, gap b)**: extraction error is "structurally biased, not random noise"; gate analytics on `sanad_confidence`, report metrics as ranges across confidence strata, run ablation/sensitivity.
- **Historical (01, §4, §8)**: narrator identity resolution is "the recurring failure mode in every project"; mature answer is graph topology + contextual embeddings, not rules.
- **Archaeological (06, all)**: two-stage retrieve-then-rerank; ~94% of surface forms resolve by lexicon lookup, the hard ~6% (~3,477 ambiguous forms) needs the contextual + graph-structural pass; real-text accuracy is low-to-mid 80s%, not high 90s.
- **Futurist (07, Part C.1)**: KG+Transformer 97.8% is a "ceiling-under-ideal-conditions," not the expected number on real multi-tradition noisy data.
- **Analogical (03, §B.2, table row 4)**: GEDCOM-X Persona vs Subject — never destroy the ambiguous mention; attach a confidence-qualified resolution edge; allow competing resolutions.
- *(Systems 04 implicitly concurs via the unresolved-name handling and stable-key requirement.)*

### C6. Confidence/uncertainty must be a first-class, queryable property that gates every analytic — not a cosmetic field. — **5 of 8 personas**

- **Contrarian (02, c)**: "`sanad_confidence` must gate every analytic, not be a cosmetic field."
- **Journalistic (05, 3.3, 3.7)**: confidence at every grain, finest (per-edge `edge_confidence`) is canonical; never delete weak edges — exclude them in GDS projections by predicate.
- **Negative-Space (08, gap b)**: report metrics as ranges across confidence strata; carry `extraction_method` per edge.
- **Analogical (03, §A.2, §B.2)**: `is_influential`→`sanad_confidence` as a derived weighted flag + `confidence_method`; GEDCOM-X confidence enum.
- **Futurist (07)**: carry `sanad_confidence` as a relationship property into the GDS projection; gate downstream claims.

### C7. SemanticHadith / MIS / Van Bruggen are the canonical prior art and the durable label skeleton (Hadith / Matn / Sanad / Narrator / Collection / Chapter / Grade / Topic). — **5 of 8 personas**

- **Historical (01, §3, §8)**: skeleton "unchanged 2014→2026"; "adopt this vocabulary for the Neo4j label set."
- **Analogical (03, §E.1, §E.2)**: validates the canonical node set and that sanad is a modeled object, not a derived path.
- **Journalistic (05, §1, §2)**: schema explicitly built on MIS + Van Bruggen precedent.
- **Contrarian (02, a)**: cites SemanticHadith as the closest peer — but to argue it chose RDF/OWL deliberately (see Tension T1).
- **Futurist (07)** & **Negative-Space (08)**: both anchor on MIS figures (2,092 nodes / 77,797 edges) as the reference model — Negative-Space to note it is Sunni-single-collection and structurally inadequate for multi-tradition (see Tension T4).

### C8. Stable, content-anchored node IDs are mandatory because the dataset regenerates and reassigns `id` every rebuild. — **3 of 8 personas (deep), echoed by others**

- **Systems (04, §0, §3)**: the central design tension already in the code (`regen_unified_csvs.py:77-84` reassigns `id`); recommends layered resolution → controlled-vocab key (`RAWI:scholar_indx` then `EXT:uuid5(norm_name)`) + alias table.
- **Negative-Space (08, gap g)**: node-ID churn "quietly destroys reproducibility"; content-stable semantically-anchored IDs + crosswalk + tombstone (never delete — matches project memory directive).
- **Analogical (03, §B.2)**: surface mention ≠ resolved entity; the older cluster retains the ID (entity-resolution stability pattern).
- *(Historical 01 §8 reinforces: keep real provenance per edge or analytics mislead.)*

---

## 2. PRODUCTIVE TENSIONS — genuine decisions the project must make

These are *not* reconciled here. Each is framed as a real fork with the conditions under which each side wins. The Contrarian is given full weight.

### T1. Neo4j (LPG) vs RDF/OWL+SPARQL vs Postgres/Apache-AGE/networkx — *the foundational tooling decision*

**The Contrarian's position (02), stated without softening:** The brief "front-loads the *tooling* decision and back-loads the *data and semantic* decisions. That ordering is the core mistake." Four distinct sub-arguments:

1. **Interoperability/standards (02a):** SemanticHadith — the closest peer — *deliberately* chose RDF/OWL/SPARQL to join the LOD cloud and become a standard vocabulary; OpenITI uses CTS URNs. An LPG "cannot mint dereferenceable URIs, cannot be `owl:sameAs`-linked, cannot be SPARQL-federated" — building "an island next to an emerging archipelago of standards." RDF/OWL can also *enforce* ontological constraints (a narrator cannot transmit from someone who died before their birth) that Neo4j cannot enforce at the DB layer.
2. **Scale (02b, 02d):** ~69k hadith / low-hundreds-of-thousands of edges is *small*. Recursive CTEs resolve shallow (4–8 deep) isnad chains in milliseconds; networkx holds the whole graph in RAM with the full algorithm catalog at zero ops cost. "Neo4j's value proposition… is a *product* argument, not a *research* argument — and the brief is framed as research/dataset regeneration."
3. **Operational cost (02b):** Neo4j is a second database — second backup, monitoring, access-control, and application-level joins back to the existing Postgres+pgvector stack. Apache AGE keeps one datastore (but has a governance/maturity risk: Bitnine→"SKAI Worldwide" 2025 pivot).
4. **Ordering (02c):** GIGO is acute and *root-concentrated*; analytics on regex chains with 12% unknown are "dangerous as an analytical engine" regardless of which DB.

**The schema-design personas' counter (01, 03, 05, 07):** Isnad analysis *is* multi-hop traversal + centrality + community detection — LPG's home turf. The Contrarian itself concedes (02a steelman): "Cypher pattern-matching and built-in graph algorithms… are far more direct than SPARQL property-path gymnastics." Historical (01) documents that MIS, Van Bruggen, and the Bukhari-SNA work all *chose Neo4j over RDF* precisely because RDF/OWL+SPARQL is heavy for variable-length isnad path + GDS, and SemanticHadith effectively retreated to precomputing/materializing edges (an implicit admission SPARQL inference didn't scale for exploration). Futurist (07) shows the highest-value novel contributions (cross-tradition matn-reuse, GDS-vs-rijāl validation) need GDS + a vector index — natively Neo4j.

**The decision and its conditions:**

| Choose… | When these hold |
|---|---|
| **Neo4j (LPG)** | Deliverable includes an *interactive product* with sub-second arbitrary-depth traversals for many users; OR repeated heavy GDS centrality/community/embedding work on stable data; entity resolution is solved; team accepts vendor/standard lock-in; cross-tradition modeled as explicit links not merge. |
| **RDF/OWL+SPARQL** | LOD interoperability / federation with SemanticHadith-OpenITI-Wikidata is a stated goal; the project wants DB-layer ontological constraint enforcement; longevity-as-citable-standard outweighs traversal ergonomics. |
| **Postgres edge table + recursive CTE / Apache AGE / networkx** | The deliverable is *research + a dataset* (not a product); scale stays ~70k; minimizing the second-datastore ops burden matters; you want to "prove you need Neo4j" before adopting it. |

**Crucible note — the deepest unresolved disagreement:** Five personas design *for* Neo4j on the brief's premise; the Contrarian argues the premise itself is the error and the lowest-regret path is Postgres+networkx now, Neo4j only on demonstrated product/scale need, RDF if LOD becomes a goal. **The schema-design personas largely assume Neo4j; only the Contrarian interrogates the premise. This asymmetry must not be read as consensus.** A defensible synthesis many personas would tolerate: the *schema* (reified chain, tradition-scoped assessment, explicit SAME_AS, confidence-gated edges, stable IDs) is engine-agnostic and should be designed first; the *engine* is a later, evidence-gated choice. But the project lead must consciously decide whether the brief's "regenerate into Neo4j" framing survives the Contrarian's ordering critique. (See Decisive Question Q1.)

### T2. Where does `tradition` live — denormalized for query speed, vs single source of truth for correctness?

- **Journalistic (05, 3.2)**: put `tradition` on `Collection` as source of truth *and deliberately denormalize* it onto Hadith, Chain, `NARRATED_FROM`, Assessment — GDS projections must filter by tradition without a 3-hop join.
- **Negative-Space (08, gap a)** & **Contrarian (02, e)**: tradition must be a *query-time projection / partition*, and the danger is precisely that a denormalized tradition tag on a shared narrator node silently encodes the unified-narrator fallacy.

**Decision:** Denormalization wins for *edge/analytic* properties (performance, and the edge genuinely is tradition-scoped — a chain belongs to one collection's tradition). Source-of-truth-only wins for *narrator identity* (a narrator must NOT carry a single tradition; the person is tradition-neutral, the *assessments* are tradition-scoped). The reconciliation: `tradition` denormalized onto Collection/Hadith/Chain/edge/Assessment; **never** as a scalar on `Narrator`. Both sides win if applied to different node types.

### T3. Confidence granularity: per-edge (analytically correct) vs keep existing per-hadith (data reality / no-delete directive)

- **Journalistic (05, 3.3)**: per-edge `edge_confidence` is "the analytically correct granularity"; keep all three grains, finest is canonical, never throw the existing per-hadith field away (project memory: never destroy fields).
- **Systems (04)** & data ground truth: confidence is *currently* stored per-hadith only (`sunni_isnad.jsonl` → `sanad_confidence: 0/2`); per-edge confidence does not yet exist and must be *derived* (term strength × name-resolution confidence).

**Decision:** Not a true contradiction once sequenced — keep the legacy per-hadith integer as-is (immutable, no-delete), *add* derived per-edge and per-chain rollups. The real question is whether per-edge confidence can be *defensibly derived* before entity resolution exists (it partly depends on name-resolution confidence — a dependency, see §3).

### T4. Is published prior art a usable template, or a trap?

- **Historical (01)** & **Analogical (03)**: treat MIS / SemanticHadith / Van Bruggen as the durable, reusable spine and label set.
- **Negative-Space (08, §0)**: "the literature itself omits the multi-tradition problem"; every published project is single-collection single-tradition (mostly Sunni Bukhari/Muslim). "Any methodology copied from these papers will inherit a mono-tradition data model that structurally cannot represent this dataset's core reality… treat the multi-tradition design as net-new engineering, not a port."

**Decision:** Reuse the *node/label skeleton and reification pattern* (where 01/03/05 agree) but treat *cross-tradition modeling, grading partition, and SAME_AS* as net-new (08's mandate). The two reconcile if "reuse" is scoped to the mono-tradition core and "net-new" to the cross-tradition layer — but the project must consciously refuse to inherit the single-grade, single-tradition assumptions baked into the cited datasets.

### T5. Cross-tradition matn-reuse & automated grading — flagship contribution vs epistemic hazard

- **Futurist (07)**: the never-published cross-tradition matn-reuse map (BGE-M3 + vector index) and GDS-centrality-vs-rijāl validation are "the highest-value novel contribution available."
- **Negative-Space (08, f)** & **Contrarian (02, c)**: an algorithmic grade across five living traditions is "implicitly a sectarian verdict… a takfir-adjacent claim made by a script"; building automated common-link analytics on noisy regex chains "compounds a contested method with corrupted inputs."
- **Futurist (07) itself** concedes the guardrail: GDS is "decision-support, not a *muḥaddith*"; grade is "never a model output presented as authority"; matn-reuse hits are "candidates for scholarly takhrīj, not established ṭuruq."

**Decision:** The contribution and the hazard are reconcilable *only* under strict framing discipline: descriptive not prescriptive, tradition-scoped, citation-grounded, human-in-the-loop, no global authenticity score, conservative thresholds, methodology+limitations shipped with the data and UI. The fork is whether the project has the discipline and review process to ship it that way — if not, Negative-Space/Contrarian win and the analytics should not ship.

---

## 3. DEPENDENCY CHAIN — what must be true/done before what

The personas (esp. Systems 04, Archaeological 06, Negative-Space 08, Contrarian 02) imply a strict ordering. Violating it produces confidently-wrong output.

```
[D0] DECIDE THE ENGINE & PREMISE (Q1)  ── must precede irreversible schema/ops investment
        │   (Contrarian: this ordering itself is contested; resolve before building)
        ▼
[D1] ENGINE-AGNOSTIC SCHEMA DESIGN
     • reified Chain/Isnad node + shortcut edge (C2)
     • tradition-scoped Assessment, NEVER scalar grade on Narrator (C1)
     • explicit SAME_AS, never merge (C4)
     • absence-representable verdicts (Zaydi/Ibadi NULL+reason) (C1)
        ▼
[D2] STABLE ID / ENTITY-RESOLUTION AUTHORITY FILE         ← gates everything analytic
     • controlled-vocab key: RAWI:scholar_indx → EXT:uuid5(norm_name) (Systems 04 §3)
     • alias / merge_history table (Systems 04, Neg-Space 08g, Analogical 03 B.2)
     • two-stage retrieve→rerank resolution; ~94% lexicon, ~6% hard core (Archaeological 06)
        ▼
[D3] STRUCTURE THE INPUT BEFORE LOADING
     • parse Sunni story-form chains; resolve taḥwīl (ح) branches (Neg-Space 08d)
     • quantify the 12% unknown; carry extraction_method per edge (Neg-Space 08b, Contrarian 02c)
     • death-year / tabaqa / geography metadata captured (Neg-Space 08d) ── enables [D6]
        ▼
[D4] DERIVE CONFIDENCE AT FINEST DEFENSIBLE GRAIN
     • per-edge edge_confidence = term-strength × name-resolution-confidence
       (note: depends on [D2] — cannot fully derive before resolution) (Journalistic 05 3.3)
     • keep legacy per-hadith sanad_confidence immutable (no-delete directive)
        ▼
[D5] IDEMPOTENT GRAPH LOAD (provenance-stamped, tombstone-not-delete)
     • MERGE on stable business keys; DatasetVersion node + crosswalk (Systems 04 §2,4,5)
     • validation gate BEFORE load; Cypher assertions AFTER (Systems 04 §6)
        ▼
[D6] TEMPORAL / CONTEMPORANEITY PLAUSIBILITY PASS          ← depends on [D3] dates
     • flag student.birth > teacher.death as impossible; exclude from analytics (Neg-Space 08e)
        ▼
[D7] CONFIDENCE-GATED GDS ANALYTICS (ranges, not point values)
     • run on high-confidence subgraph first; ablation/sensitivity (Neg-Space 08b, Contrarian 02c)
     • ArticleRank/Leiden/Betweenness as SCREENING, tradition-aware (Futurist 07)
        ▼
[D8] GRADING-SUPPORT / CROSS-TRADITION MATN-REUSE          ← LAST, never before [D2]–[D7]
     • descriptive, tradition-scoped, cited, human-in-loop, no global score
     • validate GDS centrality vs rijāl per tradition (Futurist 07 highest-value experiment)
```

**Critical chain insight (convergent across 02, 06, 08):** D2 (entity-resolution authority file) is the gate. Every analytic (D7) and all grading-support (D8) is "confidently wrong" until D2 + D3 are done and D4 uncertainty is propagated. The Contrarian's core recommendation *is* this dependency chain: data/semantics before tooling/analytics.

---

## 4. RISK REGISTER — ranked, with the concrete mitigation each persona proposed

Ranked by GIGO/harm leverage (Negative-Space's priority ranking, cross-checked against Contrarian severity weighting).

| # | Risk | Who flagged | Concrete schema/process mitigation (as proposed) |
|---|---|---|---|
| **R1** | **Unified-narrator fallacy** — one node + one scalar grade silently picks a tradition's winner and erases the disagreement that *is* the scholarly content; Zaydi/Ibadi flattened into Sunni by default. | Neg-Space 08a (rank 1), Contrarian 02e, Archaeological 06d, Journalistic 05 3.4, Analogical 03 B/D, Futurist 07 C4, Historical 01 §8 | Reify verdict: `(:Narrator)-[:EVALUATED_BY/ASSESSES]->(:Assessment/Verdict {grade, critic, work, edition, tradition, scheme, page})`; N contradictory verdicts per narrator; tradition is query-time projection; absent verdict stored explicitly as `NULL + reason="no_extant_evaluation_in_tradition"`, never inherited. |
| **R2** | **Structured-missingness GIGO** — 12% unknown + unstructured Sunni story-chains are *non-random*, root/common-link-concentrated; centrality/community come back confidently wrong, over-stating canonical Sunni hubs, under-representing Shia/Zaydi/Ibadi. | Neg-Space 08b (rank 2), Contrarian 02c (single strongest objection), Historical 01, Futurist 07 | Gate analytics on `sanad_confidence`; run on high-confidence subgraph then full, report metric *ranges across confidence strata*; ablation (delete +5/10/20% edges, Spearman top-k stability) — publish instability if unstable; carry `extraction_method` per edge; exclude unparsed traditions from cross-tradition centrality; attach Juynboll seeming-common-link caveat. |
| **R3** | **Cross-tradition phantom bridges via silent SAME_AS merge** — a naive merge manufactures transmission paths that never existed, then dominates betweenness/community. | Contrarian 02e, Analogical 03 B.1, Archaeological 06d/f, Neg-Space 08a, Journalistic 05 2.2 | Tradition-partitioned narrator identifiers; cross-tradition equivalence ONLY as explicit, evidence-tagged, confidence-scored `:IDENTIFIED_WITH`/`:SAME_AS`; human-confirm required, never auto-merge; keep `possibly_same_as` soft links so metrics run under both merge and split hypotheses. |
| **R4** | **Missing contemporaneity check** — temporally impossible edges (regex artifact or real inqitāʿ) presented with equal analytical weight; PageRank flows through impossible links. Cheapest high-value validation the whole field skips. | Neg-Space 08e (rank 3), Archaeological 06c (temporal pruning), Contrarian 02a (RDF would enforce it) | Capture death/birth/tabaqa/floruit (depends on R5 fix); automated pass: flag `student.birth_year > teacher.death_year` → `temporal_plausibility ∈ {ok,suspect,impossible,unknown}`; exclude `impossible` from analytics by default, surface as extraction-error or inqitāʿ candidate; `unknown` is its own bucket, never silently "ok". |
| **R5** | **Dropped metadata** — death-year/tabaqa/geography/narration-mode/taḥwīl omitted by every published schema; converts checkable historical claims into unfalsifiable edges; disables R4. | Neg-Space 08d (rank 5), Archaeological 06 (tabaqa/dates as disambiguating attributes), Futurist 07 (node features for GraphSAGE) | Narrator props `death_year, birth_year (ranged), tabaqa, locations[], kunya[], nasab[]` + `*_uncertain` flags; first-class multi-chain with `LINK {order, mode, tahwil_branch}`; detect taḥwīl explicitly, `tahwil_unresolved=true` excluded from continuity analytics; narration `mode` per link, default `unknown` not silently `samaa'`. |
| **R6** | **Grade provenance loss + copyright trap** — bare `grade="sahih"` is scholarly meaningless; the *only* source of many modern grades is 20th–21stc. copyrighted critical apparatus (al-Albani, al-Arnaʾūṭ, Dar al-Salam) — regenerating it may launder protected scholarly labor. | Neg-Space 08c (rank 4), Contrarian 02 (provenance per edge), Archaeological 06d (assessment provenance edge), Historical 01 (per-edge real provenance), Analogical 03 D.1 (per-edge source/license) | Forbid bare grades — ingest rejects grade with no grader, or `grade_unsourced=true` excluded from authoritative queries/UI; `(:Hadith)-[:GRADED]->(:Grading {grade,grader,work,edition,year,tradition,methodology})`; `:Source` node with license flag (`public_domain_classical` vs `modern_critical_edition_restricted`); do not redistribute restricted-edition verdicts — store citation/pointer not text; record digital-text witness per hadith. |
| **R7** | **Node-ID churn across regenerations** — IDs from row order/auto-increment/mutable-text-hash reshuffle every rebuild; "node 4471" becomes a different person; longitudinal/external citations silently break; churn concentrates in the volatile 12%. | Neg-Space 08g (rank 6), Systems 04 §0/§3 (the central code-level tension), Analogical 03 B.2 | Content-stable semantically-anchored keys: `RAWI:scholar_indx` → fallback `EXT:uuid5(NAMESPACE, norm_arabic_name)`; alias/`merge_history` table so re-extraction maps onto existing IDs; `DatasetVersion` node + `old_id→new_id` crosswalk with added/removed/merged/split; `first_seen/last_seen_version`; tombstone never delete (matches project memory directive). |
| **R8** | **Over-claiming grades / ethical-sectarian harm** — an algorithmic authenticity badge across five living traditions is implicitly a sectarian verdict; trust-undermining; compounds contested common-link method with corrupted input. | Neg-Space 08f (rank 7), Contrarian 02c, Futurist 07 (non-negotiable principle), Archaeological 06f | Descriptive not prescriptive ("al-Najashi graded X as…", not "this hadith is weak"); no global authenticity score — tradition-scoped, labeled, shown with dissenting verdicts; ship methodology+limitations statement in dataset and UI; human-scholar-in-loop disclaimer; per-tradition rijāl authorities only, no cross-application; conservative similarity thresholds; outputs framed "investigate," not "exists" (esp. link-prediction). |
| **R9** | **Premature/​wrong-tool operational debt** — adopting Neo4j on speculation buys a second DB's ops burden before data justifies it; AGE has a governance/maturity risk. | Contrarian 02b/02d (primary), Systems 04 (mitigates if Neo4j chosen) | "Prove you need it": Postgres edge table + recursive CTE / Apache AGE / networkx until a concrete interactive-product or repeated-large-scale-algorithm need appears; if Neo4j chosen, Systems 04's idempotent two-loader + DVC + DatasetVersion provenance contains the ops risk. |

---

## 5. THE DECISIVE QUESTIONS the project lead must answer before building

These are the forks that cannot be deferred — each gates a large, hard-to-reverse investment.

**Q1. Is the deliverable a research dataset/analysis, or an interactive product — and does that survive the Contrarian's ordering critique?**
This single answer resolves T1 and reorders the whole plan. *Research/dataset* → Contrarian's path (Postgres+networkx now, schema engine-agnostic, Neo4j/RDF deferred to demonstrated need). *Interactive product with sub-second multi-hop traversal for many users* → Neo4j is justified. The brief asserts Neo4j; the project lead must consciously ratify or revise that premise. (Sources: 02 all, 04 §0, 07.)

**Q2. Will the project commit to entity resolution (canonical IDs + alias table + two-stage resolution) as a hard prerequisite before any analytic ships?**
≥6 personas say analytics are "confidently wrong" without it. Yes → D2 is funded and gates D7/D8. No → the analytics deliverable should be cut, not shipped with disclaimers nobody reads. (Sources: 02c, 06, 08b, 01, 07, 03 B.2.)

**Q3. What is the cross-tradition narrator policy — tradition-partitioned identifiers with explicit human-confirmed SAME_AS, accepting that some same-person links stay unasserted?**
This is the dataset's defining feature and the most intellectually serious modeling decision. A silent merge is the highest-leverage error after R1/R2. (Sources: 02e, 03 B.1, 06d, 08a, 05 2.2.)

**Q4. Will grades be stored only with full provenance (grader/work/edition/tradition/license), and will restricted modern-critical-edition grades be excluded from redistribution?**
This is simultaneously a scholarly-correctness and a legal-exposure decision; it must be settled before any grade is ingested. (Sources: 08c, 02, 06d, 01, 03 D.1.)

**Q5. Will the project ship the cross-tradition matn-reuse / GDS-vs-rijāl validation work, and if so, under what enforced framing discipline (descriptive, tradition-scoped, cited, human-in-loop, no global score)?**
This is the highest-value novel contribution *and* the highest ethical hazard; the fork is whether the team has the review discipline to ship it safely or should not ship it. (Sources: 07, 08f, 02c, 06f.)

**Q6. What is the canonical ID and versioning contract (stable key derivation, alias/merge table, DatasetVersion + crosswalk, tombstone policy) given the source regenerates and reassigns `id` every rebuild?**
Without this answered before D5, every regeneration silently breaks reproducibility and the no-delete project directive. (Sources: 04 §0/§3, 08g, 03 B.2.)

---

### Preserved dissent (do not let the schema majority bury this)

Five personas (01, 03, 05, 07, and partly 04) design *for* Neo4j on the brief's premise. Only the **Contrarian (02)** systematically interrogates whether Neo4j — or any graph database, or graph analytics on the current data — should be built at all yet, and **Negative-Space (08)** independently corroborates the Contrarian's strongest single point (structured-missingness GIGO, R2) and adds that the prior art the schema personas reuse is structurally mono-tradition and "not fit for purpose." The convergence on *schema mandates* (C1–C8) is robust and engine-agnostic; the convergence on *building Neo4j now* is **not** present — it is an artifact of the brief's framing, challenged on the evidence by 02 and 08. Q1 must be answered before that framing is treated as settled.
