# Archaeological Dig: Cross-Tradition Narrator Entity Resolution for an Isnad Graph

**Persona:** Archaeological (dig into the techniques in depth)
**Research question:** Turn messy extracted narrator strings (diacritized al-Kafi Arabic, English-transliterated Thaqalayn chains, kunya/laqab collisions, divergent Sunni/Shia rijal evaluations) into stable, disambiguated graph nodes.
**Date:** 2026-05-16

> Methodology note: `WebFetch` was permission-denied in this environment, so every claim below is grounded in `WebSearch` result excerpts (publisher abstracts, PMC/MDPI/Springer/Oxford/ScienceDirect/KITAB summaries). Numbers quoted are from those abstracts; verify exact figures against the PDFs before production use. I flag the few places where the search snippet was ambiguous.

---

## 0. Executive shape of the solution

The literature converges on a **two-stage "retrieve-then-rerank" architecture** that maps naturally onto a Neo4j isnad graph:

1. **Blocking / candidate generation** — from a raw surface form ("Abu Ja'far", "muhammad b. ya'qub", "عن أبي عبد الله") produce a small candidate set of authority-file narrator IDs using normalization + name-component decomposition + graph-structural priors (who appears before/after in the chain).
2. **Scoring / re-ranking** — an AraBERT (or KITAB classical-Arabic BERT) contextual model plus graph signals (network prominence, teacher-student edge plausibility, tabaqa/generation compatibility) picks the winner.
3. **Identity ≠ assessment** — the resolved node carries *one* physical-person identity but *N* tradition-tagged reliability assessments hung off it as separate nodes/edges, never merged.

The state of the art on the benchmark dataset reports **97.8% accuracy** (Mosa 2025, KG+Transformer); the previous bar was **94.6%** (AraBERT two-stage re-rank, Mahmoud et al. 2024) and **92.9 micro-F1 / 83.5 on real six-books test** (AR-Sanad 280K original, 2022). The gap between synthetic-validation (~95-98%) and real-text (~83%) numbers is the single most important honesty signal in this whole literature.

---

## (a) Controlled-vocabulary / training datasets: AR-Sanad 280K and Sanadset 650K

### AR-Sanad 280K / 280K-v2 — the closest thing to a labeled narrator-resolution training set

- **Source of identities:** scraped from the *Khadem Al-haramyn* narrator site — **18,861 narrators** listed; the released dataset can identify **18,298 narrators**.
- **Per-narrator schema (this is effectively a ready-made authority file):**
  - Full name (canonical `ism + nasab + ...`)
  - **"Appearance forms" / صور الورود** — the short surface strings actually used in chains (e.g. just a kunya, or `ism b. father`). This is the gold for building a surface-form → ID lexicon.
  - **Shuhra** (the by-name a transmitter is famous under)
  - **Rank by Ibn Hajar** (the 12-class taqrib grading — a Sunni assessment field)
  - Birth/death date
  - **narrated-from / narrated-to lists** (the graph edges — directly importable as Neo4j `:NARRATED_FROM` relationships)
- **Surface-form ambiguity statistics (critical design numbers):**
  - **61,598 unique appearance forms** across 18,298 narrators.
  - **Only 3,477** appearance forms are shared by more than one narrator; **the rest are unique**. → Implication: ~94% of surface strings resolve by exact lexicon lookup; the hard disambiguation problem is concentrated in a **~3.5K-string ambiguity core** (this is exactly the "Abu Ja'far" / "Hisham" / "muhammad b. ..." collision set). Build your blocking around that asymmetry: cheap exact-match path for the 94%, expensive contextual path for the 6%.
- **Artificial-sanad generation:** sanads are synthesized by walking the narrated-from/to graph to create plausible chains, then substituting each narrator with one of his appearance forms — i.e. **distant-supervision data augmentation**. You can reproduce this generator on your own al-Kafi/Thaqalayn graph to create training pairs without manual labeling.
- **Reported accuracy:**
  - Best single model = fine-tuned **AraBERT**: **92.9 micro-F1, 30.2 Sanad Error Rate (SER)** on synthetic validation.
  - On a **real test set from the Sunni "six books"**: **83.5 micro-F1, 60.6 SER** — a ~10-point F1 / 2x SER degradation. This is the realistic ceiling for a model trained on synthetic chains and applied to real text.
  - **280K-v2** is an updated release that "represents real hadiths more accurately" (closes part of the synthetic→real gap).
- **Code/artifacts:** GitHub `somaia02/Narrator-Disambiguation` ships narrators' info + trained AraBERT models — directly reusable.
- Papers/links:
  - MDPI Information 13(2):55 — https://www.mdpi.com/2078-2489/13/2/55
  - DOAJ — https://doaj.org/article/584d83a2a1da4ad0891e8ee18a8f6a07
  - GitHub — https://github.com/somaia02/Narrator-Disambiguation

> **Tradition caveat:** AR-Sanad's identities and the "Ibn Hajar rank" field are **Sunni-centric** (six-books world). It is a strong *Sunni* authority file and a strong *technique* template, but it will **not** contain Shia-only Imami narrators (e.g. companions of the Imams who never appear in Sunni chains) and its single grading column embodies exactly the identity-vs-assessment conflation you must avoid. Use it for the Sunni half and the pipeline, not as the cross-tradition authority.

### Sanadset 650K (and the smaller Sanadset 368K) — large raw corpus, weak as an authority file

- **650,986 records** from **926 classical Arabic hadith books** — a *single CSV, 6 columns*.
- **Tagging scheme:** hadith decomposed with `<SANAD>...</SANAD>` and `<MATN>...</MATN>`; **every narrator wrapped in `<NAR>...</NAR>`**; the last column = number of narrators in the chain. Companion files: `books.csv` (the 926 source books), `hadith_samples.csv`, `translated_samples.csv`.
- **Honest limitation as a vocabulary:** `<NAR>` spans are **raw surface strings, NOT stable IDs**. Sanadset gives you *segmentation* (where each narrator boundary is) and *breadth* (926 books) but **not entity resolution** — there is no narrator key joining "أبو عبد الله" instances together. So Sanadset is best used as: (i) a large unlabeled corpus for self-supervised / MLM domain adaptation of an Arabic BERT, (ii) a segmentation training source, (iii) raw material to *bootstrap* a vocabulary by clustering `<NAR>` strings against AR-Sanad's appearance-form lexicon.
- Links: PMC — https://pmc.ncbi.nlm.nih.gov/articles/PMC9440281/ ; ScienceDirect — https://www.sciencedirect.com/science/article/pii/S2352340922007478 ; Mendeley Data (v4 = 650K, v3 = 368K) — https://data.mendeley.com/datasets/5xth87zwb5/4

**How to use them as controlled vocabulary / training data (concrete recipe):**
1. Ingest AR-Sanad 280K-v2 narrator table as the **seed authority file** → one Neo4j `:Narrator` node per ID, with `appearanceForm` array property + `:NARRATED_FROM` edges.
2. Run AR-Sanad's artificial-sanad generator on **your** al-Kafi/Thaqalayn graph to mint distant-supervision training chains for the Shia side.
3. Use Sanadset 650K (+ Sanadset/Multi-IsnadSet) as the **unlabeled MLM corpus** to domain-adapt AraBERT to classical isnad Arabic before fine-tuning.

---

## (b) The 97.8% KG+Transformer (Mosa 2025) and the 94.6% AraBERT re-rank (Mahmoud et al. 2024)

### Mahmoud, Nabil, Saif et al. 2024 — "Narrator identification by querying Sanad graph + NarratorsKG" (AR-Sanad 280K-v2)

- Published *Neural Computing & Applications* 36:23169–23180 (2024). https://link.springer.com/article/10.1007/s00521-024-10194-2
- **Pipeline (the reusable two-stage core):**
  1. Build **NarratorsKG**: a knowledge graph of narrators + their narrated-from/to relations (the AR-Sanad graph as a KG).
  2. **Stage 1 — embedding retrieval:** encode the query (the ambiguous narrator *in its chain context*) to a query embedding; retrieve **top-k** nearest narrator entities by embedding similarity (this is the *blocking / candidate generation* step, but learned rather than rule-based).
  3. **Stage 2 — AraBERT re-rank:** AraBERT scores each of the k candidates against the context and emits the final prediction.
- **Result: 94.6% accuracy** on AR-Sanad 280K validation. Key contribution vs. the 2022 baseline: **explicitly exploiting the sanad graph structure** instead of treating the chain as flat text.

### Mosa 2025 — "Synergizing structure and semantics: a KG-Transformer framework" (state of the art)

- *Digital Scholarship in the Humanities* (Oxford), advance article, DOI `10.1093/llc/fqaf088`. https://academic.oup.com/dsh/advance-article/doi/10.1093/llc/fqaf088/8253513 ; RG mirror https://www.researchgate.net/publication/395464842
- **Architecture (from abstract — internal hyperparameters were not in the snippet, flagged):**
  - A **Knowledge Graph encodes narrator-network topology** (global structure).
  - A **Transformer** provides deep contextual / semantic understanding of the chain text (local semantics).
  - **Stage 1:** the KG generates a *"high-probability set of candidate identities"* (graph-prior candidate generation — same blocking philosophy as Mahmoud, but the explicit framing is "structure narrows, semantics decides").
  - **Stage 2:** a **hybrid scoring model** ranks candidates on **(i) global network prominence** (how central/likely the candidate is in the transmission graph — degree/PageRank-like priors) **+ (ii) local semantic compatibility** (transformer match of the candidate's profile to the surrounding chain).
  - Explicitly positioned against the two failure modes you care about: *"traditional methods lack scalability and modern language models overlook crucial network structures."*
- **Result: 97.8% accuracy on AR-Sanad 280K-v2**, new SOTA.
- **Reusability for your Neo4j build — this is the blueprint:** the "global network prominence" term is *literally a Cypher/GDS computation* (degree centrality, PageRank, betweenness on the `:NARRATED_FROM` graph). The "local semantic compatibility" term is an AraBERT/classical-BERT cross-encoder over the chain window. You can rebuild this without their code: GDS for term (i), a fine-tuned bi-encoder for Stage-1 candidate retrieval, a cross-encoder for term (ii). The novelty is the *combination*, which is trivially re-implementable on Neo4j GDS + HuggingFace.

> **Honest caveat on 97.8%:** this is on **AR-Sanad 280K-v2's synthetic/semi-real benchmark**, dominated by the easy 94% of unique surface forms. The 2022 paper's own real-six-books drop to 83.5 F1 is the more credible expectation for *unseen real chains*, and **none of these papers test cross-tradition (Shia) chains or transliterated English chains at all** — that is genuinely uncharted, so treat any single-number SOTA as an upper bound on the easy, in-distribution, Sunni-Arabic case.

---

## (c) Blocking / candidate-generation + scoring for Arabic person names

### Name-component decomposition (the linguistic backbone)

Arabic names = up to five components, *no fixed order*: **ism** (given), **nasab** (`ibn/bint X ibn Y...` lineage), **kunya** (`Abu/Umm ...`, teknonym), **laqab** (epithet/title, often `al-`), **nisba** (`-i / -iyy(a)` tribe/place/profession). Robust recognition heuristics (from the naming-system literature):
- Kunya → token starts `Abū / Abu / Abi / Umm` (Arabic `أبو/أبي/أم`).
- Nasab → `ibn / bin / b. / bint` chain; recurse the genealogy.
- Nisba → token ending `-ī / -iyy / -iyya` and/or leading `al-`.
- Laqab → remaining `al-`-prefixed honorific/descriptive token not parseable as nisba.

→ **Decompose every surface string into a typed bag** `{ism, [nasab...], kunya, laqab, nisba}`. Block/score on *component-aligned* comparison, not whole-string — "Abū Jaʿfar Muḥammad b. Yaʿqūb al-Kulaynī" vs "Abū Jaʿfar" should match on kunya but the *engine must know kunya alone is low-selectivity* (kunya is exactly the al-Baqir / al-Jawad / al-Kulayni collision axis).

### Normalization (must run before any matching)

- Arabic-script: strip tashkīl/diacritics & tatwīl; normalize alef variants (أ إ آ ا → ا), yā'/alef-maqsura (ى → ي), tā' marbūṭa (ة → ه), hamza seats; unify `ابن/بن/ب.`.
- Cross-script (the al-Kafi-Arabic ↔ Thaqalayn-English problem): transliteration is many-to-many. Use **one-to-many Levenshtein with character-equivalence classes** (Freeman et al., "Cross-linguistic name matching in English and Arabic" — a Levenshtein extension with equivalence classes; https://www.researchgate.net/publication/228735060). Either romanize Arabic to a canonical scheme (or back-transliterate English to Arabic) *then* compare in one space — don't compare across scripts directly.

### Candidate generation (blocking) layers, cheapest → costliest

1. **Exact appearance-form lookup** against the AR-Sanad lexicon (resolves ~94% per the 3,477/61,598 statistic).
2. **Normalized exact** (after the normalization above).
3. **Component-keyed blocking:** block on `(normalized ism, normalized father-ism)` or `(kunya, nisba)` pairs; standard ER blocking cuts >80% of pair comparisons (CNF blocking removed 82% on PubMed 80M — same family of technique applies here).
4. **Phonetic:** run **Soundex + Metaphone in parallel** (Metaphone better for long Arabic consonant clusters) on romanized forms for transliteration variants.
5. **Fuzzy / embedding:** Levenshtein-with-equivalence-classes for spelling drift; **embedding kNN** (the Mahmoud Stage-1 "query embedding → top-k") for the contextual cases that surface forms alone can't separate.
6. **Graph-structural blocking (the highest-precision lever, unique to isnads):** the *adjacent narrators in the chain* massively constrain identity. "Abū Jaʿfar" narrating *from* a known 2nd-century companion and *to* al-Kulaynī's teacher generation ⇒ candidate set collapses to al-Baqir, not al-Kulaynī. Implement as a Cypher query: candidates whose `:NARRATED_FROM`/`:NARRATED_TO` neighbors and **tabaqa/death-date window** are consistent with the resolved neighbors. This is precisely the "query the Sanad graph" idea of Mahmoud 2024 and the "network topology" half of Mosa 2025.

### Scoring (re-rank the blocked candidates)

Combine, per candidate:
- **Component-weighted string similarity** (ism/nasab high weight & high selectivity; kunya/laqab low weight, high collision).
- **Phonetic + edit-distance** sub-scores.
- **Contextual embedding similarity** (AraBERT/classical-BERT cross-encoder over the chain window — Mahmoud/Mosa Stage 2).
- **Graph priors:** network prominence (GDS PageRank/degree), teacher-student edge plausibility, **tabaqa/generation & death-date temporal feasibility** (a narrator cannot transmit from someone who died after his own generation — a hard pruning constraint, cheap and very high precision).
- AML/ER practice: prefer **entity-resolution probability** ("do these refer to the same person, given context") over raw **string similarity** — fold in death date, tabaqa, region (al-Thurayya nisba→place) as disambiguating attributes, exactly as sanctions screening folds in DOB/nationality.

---

## (d) Same physical narrator, tradition-specific evaluations — identity ≠ assessment

This is a **modeling decision, not an ML problem**, and the rijal sources make clear why it must be enforced:

- The *same* transmitter is graded **differently across and within traditions**: Sunni jarḥ-wa-taʿdīl vs. Imami Shia rijal (which only formalized in the 5th c. AH), and even within Shia the literature "is not void of contradictions related to al-Jarḥ wa al-Taʿdīl"; al-Khūʾī's *Muʿjam Rijāl al-Ḥadīth* (24 vols, 15,000+ Shia transmitters) and the *Bahth al-Fihristī* method explicitly start from the *historical divergence of Sunni vs. Shiʿi transmission*.
- A narrator a Sunni critic deems thiqa may be majhūl or even ḍaʿīf in Imami rijal (and vice-versa) — and a *Wāqifī/Faṭḥī/ghālī* tag is itself sect-relative. Merging these into one "reliability" attribute destroys information and is scholarly indefensible.

**Recommended graph model (Neo4j):**

```
(:Narrator {id, canonicalName, components{ism,nasab,kunya,laqab,nisba},
            deathYear, tabaqa, appearanceForms[]})           // PHYSICAL IDENTITY — one node, tradition-neutral
   -[:NARRATED_FROM]->(:Narrator)                              // the isnad graph
   <-[:ASSESSES]-(:Assessment {tradition:'Sunni'|'Imami'|...,  // ASSESSMENT — many nodes per narrator
                               grade, gradeScheme:'IbnHajar-Taqrib'|'Khui'|...,
                               critic, sourceWork, sect_tag, confidence})
   -[:SAME_AS]->(:AuthorityRef {scheme:'OpenITI'|'Wikidata'|'AR-Sanad', extId})
```

Rules:
1. **Identity resolution and assessment ingestion are separate passes.** Resolve who the person is first (graph + name + ML); attach gradings second, each stamped with `tradition`, `critic`, `sourceWork`, `gradeScheme`.
2. **Never collapse `Assessment` nodes** across traditions or critics. A hadith's authenticity query then *parameterizes* by tradition: a Shia-grading query traverses `:ASSESSES {tradition:'Imami'}`, a Sunni query the Sunni ones, over the *same* identity backbone.
3. Contradictions (intra-Shia jarḥ disagreements) become first-class queryable data, not a merge conflict.
4. Keep an **assessment provenance** edge to the exact rijal work (Taqrīb, Mīzān, Muʿjam Rijāl al-Ḥadīth, Rijāl al-Najāshī…) so disagreements are auditable.

Sources: wikishia *Muʿjam rijāl al-ḥadīth* — https://en.wikishia.net/view/Mu'jam_rijal_al-hadith_(book) ; al-Islam.org Ilm al-Rijāl — https://al-islam.org/ask/topics/7693 ; Bahth al-Fihristī — https://shiiticstudies.com/2020/03/21/a-new-approach-to-authenticating-shia-hadith-the-bahth-al-fihristi/ ; Shiʿi narrator-criticism critique — https://mahajjah.com/a-presentation-and-critique-of-hadith-transmitter-criticism-al-jarh-wa-al-tadil-according-to-the-shia/

---

## (e) Existing controlled vocabularies / authority files and how to align

| Resource | What it gives you | Alignment strategy |
|---|---|---|
| **AR-Sanad 280K-v2 narrator table** | ~18,298 Sunni narrators, IDs, appearance forms, shuhra, Ibn-Hajar rank, narrated-from/to, dates | Use as **primary Sunni authority key**; import IDs as `:Narrator.id`; lexicon = exact-match blocking layer |
| **al-Khūʾī Muʿjam Rijāl al-Ḥadīth** (via Thaqalayn / Dirāyat al-Ḥadīth) | 15,000+ **Shia** transmitters, alphabetical, narrated-from/to, reliability | Use as **primary Shia authority key**; scrape Thaqalayn.net structured library (Shia counterpart that AR-Sanad lacks) |
| **OpenITI + KITAB person IDs** | OpenITI `AuthorID = deathYear(4-digit) + shuhra`; CTS-compliant URIs; KITAB isnad/person work | Map your nodes to OpenITI URIs for premodern-corpus interop; KITAB's isnad annotations (Ibn ʿAsākir TMD) are a labeled eval set |
| **Wikidata / DBpedia** | Wikidata has an **`OpenITI author ID` property (P13870)**; many companions/Imams have QIDs; DBpedia pages for narrators (e.g. al-Ḥasan b. Muḥammad b. al-Ḥanafiyya) | Add `:SAME_AS (:AuthorityRef {scheme:'Wikidata'})`; pivot AR-Sanad ⇄ OpenITI ⇄ Wikidata via P13870 |
| **Normalized Narrator Encyclopedia (TEI)**, Maraoui et al. 2022 | TEI model: each narrator a `<persName xml:id=...>`, NER from Wikipedia; P/R/F ≈ 0.96 | Reuse the **TEI schema** + `xml:id` convention as your interchange/export format |
| **SemanticHadith KG** (semantichadith.com) | RDF KG of 6 collections, ontology, **interlinked to Wikidata & DBpedia** | Reuse ontology classes for narrator/sanad; consume their Wikidata links as alignment seeds |
| **Sanadset 650K / Multi-IsnadSet / Hadith Narrators Kaggle (+24K)** | Raw segmented chains; Kaggle 24K narrator table | Bootstrapping/MLM corpus + supplementary name lists; NOT authority keys |
| **al-Thurayya gazetteer** | 2,000+ classical Arabic toponyms, georeferenced | Resolve **nisba → place** as a disambiguating attribute & for region priors |

**Alignment method:** anchor on the two domain authorities (AR-Sanad for Sunni, al-Khūʾī/Thaqalayn for Shia) as the canonical key spaces; treat OpenITI/Wikidata as the **interop hub** (Wikidata P13870 is the existing bridge); record every cross-link as a confidence-scored `:SAME_AS` edge, never a node merge. For the cross-tradition same-person case (a Companion in both Sunni six-books and Shia rijal), create **one identity node with two `:SAME_AS` authority refs and two+ tradition-tagged `:Assessment` sets** — the model in (d).

---

## (f) Honest accuracy ceilings and where human-in-the-loop is mandatory

- **Synthetic vs. real gap is the headline:** AR-Sanad model = 92.9 F1 synthetic but **83.5 F1 on real six-books** (SER doubles 30→60). Mosa's 97.8% is on the *synthetic-leaning v2 benchmark*. Plan for **real-text accuracy in the low-to-mid 80s%, not high 90s**, on in-distribution Sunni Arabic.
- **The 94/6 split sets expectations:** ~94% of surface forms are unique → near-perfect by lookup; almost all error concentrates in the **~3.5K ambiguous-form core** — and that core (kunya/laqab collisions like "Abū Jaʿfar", "Hishām", bare "Muḥammad b. …") is *exactly your hardest, highest-value target*. KITAB found individuals with **up to 25 surface forms**, ~50% of persons multi-form; their hand-annotated Ibn ʿAsākir set (2,379 isnads, 14,454 names, 90% manually annotated, only 44 distinct persons) shows how labor-intensive gold truth is.
- **Out-of-distribution = unmeasured:** *no published system* reports numbers on (i) Shia/Imami chains, (ii) English-transliterated Thaqalayn chains, (iii) cross-tradition same-person linking. Expect a further accuracy drop here; these are research-grade, not solved.
- **Author-name-disambiguation analogy ceilings:** even in well-resourced bibliometric AND, real deployments land at **pairwise F1 ≈ 0.90–0.92** on unseen test data (the 99%+ figures are on curated/synthetic sets) — consistent with the hadith synthetic→real pattern.
- **Where humans are mandatory (HITL design):**
  1. **Ambiguous-core adjudication** — any candidate where top-1 vs top-2 score margin is small, or kunya/laqab-only match → route to a rijal expert. Use **active learning** (prioritize highest-uncertainty / highest-graph-impact nodes; AND literature shows active learning materially reduces labeling cost).
  2. **Cross-tradition same-person assertions** — auto-suggest `:SAME_AS`, **never auto-merge**; require human confirm (theological/historical stakes).
  3. **Assessment attachment** — grade extraction from rijal works is itself error-prone; human verifies `tradition`/`critic`/`scheme` stamping.
  4. **Bootstrap seed audit** — distant-supervision (artificial-sanad) labels are noisy; sample-audit before training.
  - Practical loop: confidence-threshold auto-accept the unique-form 94%; queue the ambiguous core + all cross-tradition links to experts; feed confirmations back as training data (closing the AR-Sanad-style augmentation loop on real, expert-verified pairs).

---

## Key sources (URLs)

- AR-Sanad 280K — https://www.mdpi.com/2078-2489/13/2/55 · https://github.com/somaia02/Narrator-Disambiguation · https://doaj.org/article/584d83a2a1da4ad0891e8ee18a8f6a07
- Mahmoud/Nabil/Saif 2024 (NarratorsKG, AR-Sanad 280K-v2, 94.6%) — https://link.springer.com/article/10.1007/s00521-024-10194-2 · https://dl.acm.org/doi/10.1007/s00521-024-10194-2
- Mosa 2025 KG-Transformer 97.8% (DSH/Oxford, fqaf088) — https://academic.oup.com/dsh/advance-article/doi/10.1093/llc/fqaf088/8253513 · https://www.researchgate.net/publication/395464842
- Sanadset 650K — https://pmc.ncbi.nlm.nih.gov/articles/PMC9440281/ · https://www.sciencedirect.com/science/article/pii/S2352340922007478 · https://data.mendeley.com/datasets/5xth87zwb5/4
- KITAB isnad disambiguation — https://kitab-project.org/Mapping-Who-s-Who-in-Isnads-First-Steps/ · https://kitab-project.org/networks-named-entities
- Learning to Identify Narrators (2-model LSTM-CNN-CRF, F1 96.15/95.74) — https://www.sciencedirect.com/science/article/pii/S1877050921012369
- Normalized Narrator Encyclopedia TEI (Maraoui 2022) — https://www.scielo.org.mx/scielo.php?script=sci_arttext&pid=S1405-55462022000301283
- SemanticHadith KG — https://dl.acm.org/doi/10.1016/j.websem.2023.100797 · http://www.semantichadith.com
- Cross-linguistic Arabic-English Levenshtein (Freeman et al.) — https://www.researchgate.net/publication/228735060
- Arabic naming system — https://en.wikipedia.org/wiki/Arabic_name · https://arabic-for-nerds.com/translation/how-are-family-names-constructed-in-arabic/
- OpenITI / Wikidata P13870 — https://maximromanov.github.io/OpenITI/ · https://www.wikidata.org/wiki/Property:P13870 · https://kitab-project.org/docs/openITI
- Shia rijal: al-Khūʾī Muʿjam — https://en.wikishia.net/view/Mu'jam_rijal_al-hadith_(book) · Thaqalayn — https://thaqalayn.net/ · Bahth al-Fihristī — https://shiiticstudies.com/2020/03/21/a-new-approach-to-authenticating-shia-hadith-the-bahth-al-fihristi/
- al-Thurayya gazetteer — https://althurayya.github.io/
- Entity-resolution / AND ceilings & blocking — https://www.science.org/doi/10.1126/sciadv.abi8021 · https://link.springer.com/article/10.1007/s00799-025-00428-6
- Arabic name matching (AML practice) — https://www.babelstreet.com/blog/fuzzy-name-matching-techniques
