# Historical Persona — Evolution & Prior Art of Graph Databases for Hadith Isnad Networks

**Research question:** Regenerating a multi-tradition hadith dataset (69,368 rows: Sunni Kutub al-Sittah, Imami/Thaqalayn, Zaydi Musnad Zayd, Ibadi Musnad al-Rabiʿ, Sahifat al-Ridā) into a Neo4j knowledge graph centered on the isnad/sanad narrator network.

**Lens:** What has actually been built (2019→2026), the concrete data models used, what proved durable, and what was regretted.

---

## 0. Timeline of prior art (the durable spine)

| Year | Project | Backend | Scope | Graph contribution |
|------|---------|---------|-------|--------------------|
| 2014–2016 | e-Narrator / HadithRDF (Al-Hajjar et al.) | OWL/RDF | Narration tree ontology | First hadith narration-tree ontology; established Hadith / Matn / Sanad / Narrator class skeleton later reused everywhere |
| 2019 | "A Novel Graph-Based Representation for Hadith Sanad" (Luthfi et al., IJATCSE) | Python + Neo4j | Single-book proof of concept | First explicit Neo4j Cypher isnad graph; A-POS + A-NER node/edge extraction; narrator attributes from Rijāl DB |
| 2021 | "Social Network Analysis of Hadith Narrators from Sahih Bukhari" (Aslam et al., arXiv 2102.02009 / IEEE) | NetworkX + Neo4j + Gephi + Cytoscape | Sahih Bukhari | Scale-free network finding; 16 narrator communities; geographic drift Mecca/Medina → Kufa/Baghdad |
| 2022 | KITAB / OpenITI "From Networks to Named Entities and Back Again" | passim + BERT clustering | Whole OpenITI corpus | Isnad-as-linear-network + NER disambiguation pipeline; the canonical "name ambiguity" treatment |
| 2022 | Van Bruggen "Graphs are everywhere — Religious Texts" (4-part blog + gist) | Neo4j + GDS | Kaggle Hadith Narrators dataset | Most reproducible end-to-end Neo4j model; bipartite + projected mono-partite design; PageRank on narrators |
| 2022 | Sanadset 650K (Mendeley/ScienceDirect) | CSV (tagged) | 650,986 records / 926 books | The de-facto large isnad text corpus with `<SANAD>`/`<NAR>` tagging |
| 2023 | SemanticHadith v1 (Kamran/Butt/Basharat, *Web Semantics* 78) | OWL/RDF + SPARQL | 6 Sunni collections | First standardized published hadith KG with live SPARQL endpoint |
| 2024 | Multi-IsnadSet (MIS) (Farooqi et al., *Data in Brief* 54:110439) | Neo4j + NetworkX + Gephi + Cytoscape | Sahih Muslim multi-isnad | 2,092 narrator nodes / 77,797 edges; explicit multi-isnad-per-hadith modeling |
| 2024 | NarratorsKG on AR-Sanad 280K-v2 (Mahmoud et al., *Neural Computing & Applications* 10.1007/s00521-024-10194-2) | KG + Transformer (AraBERT) | 280K synthetic sanads | KG-topology + embedding retrieval; 97.8% narrator-ID accuracy |
| 2025 | "Synergizing structure and semantics" (Oxford *DSH*, 10.1093/llc/fqaf088) | KG + Transformer hybrid | Isnad networks | Hybrid graph-topology + contextual LM for narrator disambiguation |
| 2025 | Ilm / arriqaaq.com ("Searching the Quran and Sunnah") | **SurrealDB** (graph+vector+BM25) | 34,457 hadith / 18,000+ narrators | Single-DB multi-model; RRF fusion of graph + vector + full-text — closest practitioner analogue to this project |
| 2025 | Rezwan corpus (arXiv 2510.03781, Najm Institute) | LLM pipeline + HF dataset | **1.39M narrations / 1,289 books, Shia + Sunni** | LLM isnad/matn separation at 9.33/10; the only project at multi-tradition scale comparable to this one |
| 2026 | SemanticHadith v2 / "Semantic Enrichment of Hadith Corpus" (SAGE 22104968261431425; SWJ) | OWL/RDF + OntoRefine | 6 collections + similarity links | Expert-validated similarity edges baked into the KG for explainable querying |

---

## 1. The Multi-IsnadSet (MIS) — the most-cited concrete Neo4j isnad model

**Source:** Farooqi, Malick, Shaikh, Akhunzada, "Multi-IsnadSet MIS for Sahih Muslim Hadith with chain of narrators, based on multiple ISNAD," *Data in Brief* 54 (2024) 110439.
URLs: https://www.sciencedirect.com/science/article/pii/S2352340924004086 · https://pmc.ncbi.nlm.nih.gov/articles/PMC11096860/ · https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4726768

**Exact figures (confirmed across PMC + ScienceDirect):**
- **2,092 nodes** = individual narrators
- **77,797 edges** = Sanad–Hadith transmission connections
- Directed graph; source = Sahih Muslim; scraped via web crawling
- Per-hadith record fields: original book, hadith number, **MATN** (text), **list of narrators**, narrator count, **sequence of narrators**, **ISNAD count** (the multi-isnad differentiator)

**Data model (as built):**
- Single node label conceptually = `Narrator` (the 2,092 nodes). Edges are narrator→narrator transmission links aggregated across all isnads of Sahih Muslim. The hadith itself is carried as record metadata / edge context rather than as a first-class densely-connected node — this is a *narrator-centric mono-partite* model.
- Delivered in CSV + graph form; loaded into **Neo4j** (Cypher), **NetworkX**, **Gephi**, **Cytoscape** in parallel (quadruple-tooling is a recurring pattern — Neo4j for storage/query, Gephi/Cytoscape for visualization, NetworkX for algorithmics).

**What worked:** The "ISNAD count" property — explicitly modeling that one hadith has *multiple* parallel chains (mutābaʿāt / shawāhid). This is the single most important durable schema idea for a serious isnad graph and is exactly what a multi-tradition graph needs (a hadith node fans out to N chains).
**What was thin:** Hadith is not a strong node; matn-level cross-collection linking is absent; single collection only (no cross-tradition). Narrator identity is surface-form based (no rijāl disambiguation layer).

---

## 2. Van Bruggen — the most reproducible end-to-end Neo4j recipe

**Sources (4-part series + gist):**
- Part 1 (intro): https://blog.bruggen.com/2022/06/graphs-are-everywhere-also-in-religious.html
- Part 2 (import narrators): https://blog.bruggen.com/2022/07/graphs-are-everywhere-also-in-religious.html
- Part 3 (import hadiths): https://blog.bruggen.com/2022/07/graphs-are-everywhere-also-in-religious_5.html
- Gist (Cypher): https://gist.github.com/rvanbruggen/a6e2e80a6fa7a253f46de9fbe9ce361f

**Data model (as built):**
- Node `:Scholar` (a.k.a. narrator) with properties including *areas of interest* and *tags*; sourced from a **Kaggle "Hadith Narrators Dataset"** (CSV).
- Node `:Hadith` imported in part 3 (actual hadith text + English translation scraped separately).
- Relationship `(:Hadith)-[:NARRATED]->(:Scholar)` linking a hadith to each scholar in its chain (a **bipartite** Hadith↔Scholar layer).
- A derived **`AGGREGATED_HADITH_CHAIN`** relationship `(:Scholar)-[:AGGREGATED_HADITH_CHAIN {numberOfHadiths}]->(:Scholar)` — a **projected mono-partite, weighted, scholar-only subgraph** built specifically so that PageRank / centrality run on a clean weighted narrator network.
- Visualization styling: rule-based relationship thickness by `numberOfHadiths`; filter to hide edges with < 10 hadiths.
- Tooling: **Neo4j Data Importer** (no-code CSV mapping) for ingest; **Neuler / Neo4j GDS playground** for algorithms (PageRank for "important scholars").

**Durable lesson (the key architectural takeaway for this project):** the explicit *two-layer* design — keep a raw **bipartite** layer (Hadith—NARRATED—Narrator) for provenance/fidelity, and materialize a **projected weighted mono-partite** narrator→narrator layer (`AGGREGATED_HADITH_CHAIN` with a weight) for graph-data-science. Mixing the two into one layer is the most common regret elsewhere. He also explicitly flagged "messiness in the data required data wrangling for a richer model" — i.e., narrator identity normalization is the hard part, predicted by everyone.

---

## 3. SemanticHadith (v1 2023 → v2 2026) — the RDF/OWL lineage

**Sources:**
- v1 paper: Kamran, Butt, Basharat, "SemanticHadith: An ontology-driven knowledge graph for the hadith corpus," *Web Semantics* 78 (2023) 100797 — https://www.sciencedirect.com/science/article/abs/pii/S1570826823000264 · https://dl.acm.org/doi/10.1016/j.websem.2023.100797
- Ontology docs: https://a-kamran.github.io/SemanticHadith-V2/ · GitHub: https://github.com/A-Kamran/SemanticHadith-V2 (ontology v2.0.1 + KG public)
- KG / SPARQL endpoint: http://www.semantichadith.com · RDF dump: https://figshare.com/articles/dataset/Semantic_Hadith_RDF/7964558
- v2 / enrichment: "Semantic Enrichment of Hadith Corpus — Knowledge Graph Generation From Islamic Text," Kamran/Butt/Basharat, SAGE 2026 (10.1177/22104968261431425) · SWJ preprint https://www.semantic-web-journal.net/system/files/swj3651.pdf

**Ontology core classes (the durable skeleton, traceable back to 2014 e-Narrator/HadithRDF):**
- `Hadith` — composed of two parts via part-of relations
- `Matn` — the report text (`Hadith hasMatn Matn`)
- `Sanad`/`Isnad` — the chain entity, related to Hadith as a separate first-class entity ("part of" Hadith)
- `Narrator` — individuals in the chain
- `HadithBook`, `HadithChapter`, `HadithCollection`, `HadithClass` (grade) — the bibliographic/grading scaffold
- `Topic` — thematic tagging (added/strengthened in v2)
- Object properties relate Matn and Sanad to Hadith via "part of" / `hasMatn`; narrators related into the Sanad.

**Scope:** 6 Sunni collections published as RDF; v2 adds **expert-validated cross-hadith similarity links baked directly into the KG** for explainable querying, generated via NLP (NER + relation extraction) → OntoRefine → OWL individuals.

**What proved durable:** The `Hadith / Matn / Sanad / Narrator / Book / Chapter / Collection / Class` class skeleton has survived essentially unchanged from 2014 (e-Narrator/HadithRDF, https://www.researchgate.net/publication/262687526) through 2026. **Adopt this vocabulary for the Neo4j label set** — it is the closest thing to a standard.
**What was regretted / limits:** RDF/OWL + SPARQL is heavy for *traversal* workloads (variable-length isnad path queries, centrality). The v2 move to "bake similarity edges into the graph" is an implicit admission that pure SPARQL inference at query time didn't scale for exploration — they precomputed and materialized. The lesson for a Neo4j build: **precompute and store derived edges (chain links, similarity, narrator co-occurrence) as real relationships**, don't compute at query time.

---

## 4. AR-Sanad / NarratorsKG / Sanadset — the disambiguation lineage

- **Sanadset 650K** (Mendeley 5xth87zwb5 v4; *Data in Brief* — https://www.sciencedirect.com/science/article/pii/S2352340922007478 · https://pmc.ncbi.nlm.nih.gov/articles/PMC9440281/): 650,986 records, 926 books. Single CSV, 6 variables; first variable = diacritized hadith with chain wrapped in `<SANAD>…</SANAD>` and each narrator in `<NAR>…</NAR>`. **Format lesson:** inline span-tagging of sanad/narrator in raw text is a proven, simple ingestion contract — easy to parse into nodes/edges deterministically.
- **AR-Sanad 280K-v2 + NarratorsKG** (Mahmoud et al., *Neural Computing & Applications* 2024, https://link.springer.com/article/10.1007/s00521-024-10194-2): builds a Knowledge Graph of narrator-network *topology*, then a 2-stage retriever — query embedding → top-k nearest narrator entities in the KG → **AraBERT re-rank** → final ID. **97.8% accuracy.** Confirms that graph topology *alone* is insufficient for narrator identity; you need topology + a language model. v2 fixed the v1 dataset for "more realistic" sanads (synthetic-data realism was a regret of v1).
- **Oxford DSH 2025 "Synergizing structure and semantics"** (https://academic.oup.com/dsh/advance-article/doi/10.1093/llc/fqaf088/8253513): generalizes the hybrid KG-topology + transformer pattern for narrator disambiguation. State of the art as of the cutoff.

**Durable lesson:** narrator identity resolution (onomastic ambiguity — kunya/laqab/nasab variants, the same man under 63 surface forms) is *the* recurring failure mode in every project. The mature 2024–2025 answer is **graph structure + contextual embeddings, not rules**. Schema implication: a `Narrator` node needs a stable canonical ID *plus* an `aliases`/surface-form list *plus* an embedding property, and ingestion must include a disambiguation pass.

---

## 5. KITAB / OpenITI — the historian's corpus-scale isnad work

**Sources:** https://kitab-project.org/networks-named-entities · https://kitab-project.org/Mapping-Who-s-Who-in-Isnads-First-Steps/ · https://kitab-project.org/c/ · OpenITI docs https://kitab-project.org/docs/openITI

- Isnads modeled as **simple linear networks**: nodes = transmitters, edges = "transmitted to". Detected at corpus scale in OpenITI via ML; text reuse via the **passim** algorithm.
- Disambiguation: multilingual English-Arabic **BERT word embeddings**, averaged over multi-word names, then **clustering** to merge surface forms. Reported test set: **1,070 names, 63 surface forms → 25 individuals** — a sharp quantification of how severe the alias problem is (~43:1 surface-to-entity ratio in the worst region).

**Durable lesson:** the historian community's verdict is that the isnad is fundamentally a *linear chain joined into a DAG across hadiths* (a "common-link" structure — Schachtian/Juynboll isnad-bundle theory), and that **edge directionality = direction of transmission** (teacher → student). This is the historiographically correct edge semantics and matches MIS and Van Bruggen.

---

## 6. Closest practitioner analogues to *this* project

- **Ilm / arriqaaq** (https://www.arriqaaq.com/ilm/): 34,457 hadith (Kutub al-Sittah), **18,000+ narrators**, interactive narrator network, reliability assessments, teacher-student transmission, pivot-narrator detection, word-level matn variant comparison. Architecturally argues *against* the classic 4-service stack (Neo4j + Elasticsearch + Pinecone + Postgres) in favor of **one multi-model DB (SurrealDB)** doing graph edges + BM25 + HNSW vectors + `search::rrf()` fusion in one round-trip. Directly relevant tension for this project: Neo4j-centric vs. multi-model. Even if Neo4j is chosen, the RRF-fusion-of-graph+vector+full-text pattern is the proven UX target.
- **Rezwan** (arXiv 2510.03781; HF `najm-institute/rezwan_corpus`): the *only* prior project at genuinely **multi-tradition Shia+Sunni scale** — 1.39M narrations / 1,289 books. LLM pipeline does isnad/matn separation (scored 9.33/10 vs. human) and 12-language MT, diacritization, tagging, cross-text semantic links. Validates that an automated LLM isnad/matn split is reliable enough to seed a 69K-row multi-tradition graph; flags diacritization + semantic-similarity as still-weak. Cost note: ~229,000 expert-hours of work done in months.

---

## 7. Maturation 2019 → 2026: what got better

1. **2019:** isnad graph = proof of concept, single book, rule/NER extraction, no identity resolution (Luthfi et al., http://www.warse.org/IJATCSE/static/pdf/file/ijatcse58815sl2019.pdf — SVM/GBM, F1 0.82–0.90).
2. **2021–2022:** SNA era — scale-free analysis, communities, centrality on single collections; quadruple-tooling (Neo4j+NetworkX+Gephi+Cytoscape) becomes standard (Bukhari SNA arXiv 2102.02009).
3. **2023–2024:** standardization — SemanticHadith gives a reusable ontology; MIS gives a reusable Neo4j multi-isnad dataset with hard figures.
4. **2024–2026:** identity resolution solved well enough (NarratorsKG 97.8%; DSH hybrid), and the field moves to **multi-model + LLM-assisted, multi-tradition** (Ilm, Rezwan, SemanticHadith v2 with materialized similarity edges).

---

## 8. Schema decisions: DURABLE vs REGRETTED (the actionable core)

**Durable / proven — adopt these:**
- **Class skeleton** `Hadith / Matn / Sanad(Isnad) / Narrator / Book / Chapter / Collection / Class(grade) / Topic` — unchanged 2014→2026 (SemanticHadith lineage). Use as Neo4j label set.
- **Two-layer graph (Van Bruggen):** raw bipartite `(:Hadith)-[:NARRATED]->(:Narrator)` for fidelity **+** materialized weighted mono-partite `(:Narrator)-[:TRANSMITTED_TO {hadithCount}]->(:Narrator)` for GDS/centrality. Do not collapse to one layer.
- **Edge direction = transmission direction** (teacher→student / earlier→later), per KITAB/Juynboll bundle theory.
- **Multi-isnad as first-class** (MIS `ISNAD count`): a hadith fans out to N parallel chains (mutābaʿāt/shawāhid) — essential for a multi-tradition graph where the same matn recurs across collections/traditions.
- **Materialize derived edges** (chain links, similarity, co-occurrence) as stored relationships — SemanticHadith v2's lesson that query-time inference doesn't scale.
- **Span-tagged ingestion contract** (`<SANAD>`/`<NAR>`, Sanadset 650K): deterministic, simple, proven for 650K records.

**Regretted / pitfalls to avoid:**
- Surface-form narrator identity with no canonical-ID + alias + embedding layer → KITAB's 63→25 / 1,070-name collapse; mandatory disambiguation pass (graph topology + AraBERT-style embeddings, the 2024–2025 consensus).
- Pure RDF/OWL+SPARQL for traversal/centrality workloads — heavy; SemanticHadith effectively retreated to precomputed edges. Neo4j (property graph) is the better fit for variable-length isnad path + GDS, which is why MIS/Van Bruggen/Bukhari-SNA all chose it.
- Single-collection scope (MIS, Bukhari-SNA) doesn't generalize to cross-tradition; cross-collection / cross-tradition matn linking must be designed in from the start (only Rezwan + SemanticHadith v2 attempted it).
- Synthetic-only sanads (AR-Sanad v1 → fixed in v2) — keep real provenance per edge (which collection/book/hadith number each transmission edge came from), or analytics mislead.
- Treating Hadith as weak edge-metadata (MIS) loses matn-level cross-references; make Hadith a strong node.

---

## Key sources (URLs)
- MIS: https://www.sciencedirect.com/science/article/pii/S2352340924004086 · https://pmc.ncbi.nlm.nih.gov/articles/PMC11096860/
- Van Bruggen: https://blog.bruggen.com/2022/06/graphs-are-everywhere-also-in-religious.html · https://blog.bruggen.com/2022/07/graphs-are-everywhere-also-in-religious_5.html · https://gist.github.com/rvanbruggen/a6e2e80a6fa7a253f46de9fbe9ce361f
- SemanticHadith v1: https://www.sciencedirect.com/science/article/abs/pii/S1570826823000264 · v2: https://github.com/A-Kamran/SemanticHadith-V2 · https://a-kamran.github.io/SemanticHadith-V2/ · http://www.semantichadith.com · SAGE 2026: https://journals.sagepub.com/doi/10.1177/22104968261431425
- NarratorsKG / AR-Sanad 280K-v2: https://link.springer.com/article/10.1007/s00521-024-10194-2
- Oxford DSH hybrid: https://academic.oup.com/dsh/advance-article/doi/10.1093/llc/fqaf088/8253513
- Sanadset 650K: https://www.sciencedirect.com/science/article/pii/S2352340922007478 · https://data.mendeley.com/datasets/5xth87zwb5/4
- KITAB isnad networks: https://kitab-project.org/networks-named-entities · https://kitab-project.org/Mapping-Who-s-Who-in-Isnads-First-Steps/
- Bukhari SNA: https://arxiv.org/abs/2102.02009 · https://www.sciencedirect.com/science/article/pii/S1319157821000215
- 2019 graph proof: http://www.warse.org/IJATCSE/static/pdf/file/ijatcse58815sl2019.pdf
- e-Narrator/HadithRDF (2014): https://www.researchgate.net/publication/262687526
- Ilm/arriqaaq: https://www.arriqaaq.com/ilm/
- Rezwan 1.2M+ corpus: https://arxiv.org/abs/2510.03781 · https://huggingface.co/datasets/najm-institute/rezwan_corpus
