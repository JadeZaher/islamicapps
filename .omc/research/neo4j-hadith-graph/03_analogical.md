# Analogical Lens: Neo4j Hadith Isnad Graph Schema

**Persona:** ANALOGICAL — port concrete data models from adjacent KG domains.
**Date:** 2026-05-16
**Question:** Neo4j schema for multi-tradition hadith isnad/narrator network
(Narrator, Hadith, Collection, Chapter; NARRATED_FROM / APPEARS_IN / ATTRIBUTED_TO;
fields attributed_to, narration_level, sanad, sanad_confidence, grade, tradition).

---

## Executive thesis

The single most consequential decision is whether transmission edges
(`NARRATED_FROM`) and attribution (`ATTRIBUTED_TO`) stay as plain edges or are
**reified into nodes**. Every mature analogous KG that needed to attach
per-link uncertainty, provenance, or context **reified the relationship**:
OpenAlex `Authorship`, W3C PROV `Derivation`/`Attribution`, Semantic Scholar
citation-context objects, GEDCOM-X `Conclusion`/`SourceReference`. Hadith
`sanad_confidence`, tradition-scoped `grade`, and disputed `attributed_to`
are exactly the per-link, per-source, per-tradition qualifiers those domains
reified. The recommendation below is a hybrid: keep a fast plain
`NARRATED_FROM` edge for graph algorithms, but make the **Isnad/Sanad a
first-class node** (matching the SemanticHadith ontology and Multi-IsnadSet
Neo4j model) and attach grading + confidence as qualifier nodes/relationship
properties.

---

## A. Scholarly citation / co-authorship graphs

### A.1 OpenAlex — the reified `Authorship` object

OpenAlex is "a heterogeneous directed graph" of 8 entity types (WORKS,
AUTHORS, SOURCES, INSTITUTIONS, TOPICS, PUBLISHERS, FUNDERS, GEOS). The
load-bearing pattern: an author is **not** linked directly to a work. The
`Authorship` object reifies the claim *"author A, affiliated with
institution(s) I, is a creator of work W"* and carries qualifiers:

```
Authorship {
  author_position: "first" | "middle" | "last"   // ORDINAL position in list
  author: <Author ref>
  institutions: [<Institution ref> ...]
  countries: [...]
  is_corresponding: bool
  raw_author_name: string        // string as printed, BEFORE disambiguation
  raw_affiliation_strings: [...]
}
```

**Transferable patterns:**

1. **`author_position` → `narration_level`.** OpenAlex encodes order in a
   list as an explicit ordinal on the reified link, exactly the role of
   `narration_level` in a sanad (Companion=1, Successor=2, …). Store it on
   the reified isnad-link, not implicitly via traversal depth, because the
   same narrator appears at different levels in different chains.
2. **`raw_author_name` vs disambiguated `author`.** OpenAlex keeps the
   *surface string as printed in the work* separate from the resolved Author
   entity. Hadith narrators are referenced by kunya/nisba/laqab variants;
   keep `raw_narrator_string` on the link and a resolved `Narrator` node —
   never collapse them at ingest (you lose audit + re-disambiguation ability).
3. **Affiliation as a list on the link, time-scoped to the work.** The
   tradition or madhhab a narrator is *claimed under in a given chain* is a
   link-scoped fact, not a global node property — model `tradition` on the
   chain/link, not (only) on the Narrator.

Source: https://docs.openalex.org/api-entities/works/work-object/authorship-object
· https://arxiv.org/abs/2205.01833

### A.2 Semantic Scholar Academic Graph (S2AG) — qualified citation edges

S2AG: ~205M publications, ~2.5B citation edges. Each citation edge is **not**
a bare `CITES`; it carries classified qualifiers:

```
(:Paper)-[:CITES {
   intents: ["background" | "method" | "result"],  // multi-valued classifier
   is_influential: bool,                            // weighted-link flag
   contexts: ["...verbatim citing sentence..."]     // evidence snippet
}]->(:Paper)
```

**Transferable patterns:**

- **`intents` → narration mode.** S2AG types *why/how* one paper invokes
  another. Hadith transmission has analogous typed modes — the *ṣīghat
  al-adāʾ* (سمعت, حدثنا, أخبرنا, عن, أنّ). Model the transmission verb as a
  typed property on `NARRATED_FROM` (`sigha: "sami'tu" | "haddathana" |
  "'an" | "anna"`); `ʿanʿana` vs explicit audition is the hadith analog of
  weak vs. strong citation and feeds `sanad_confidence`.
- **`is_influential` → `sanad_confidence` as a derived weighted flag.** A
  boolean/score on the edge, computed by a model, that downstream graph
  algorithms weight by. Mirror with `sanad_confidence: float` +
  `confidence_method: "rule" | "model" | "manual"`.
- **`contexts` → evidence text.** Keep the verbatim chain string (`sanad`
  text) on the link as the citable evidence snippet — never only the
  parsed/normalized form.

Source: https://www.semanticscholar.org/faq/citation-intent ·
https://dl.acm.org/doi/10.1145/3487553.3527147

---

## B. Genealogy graphs — person disambiguation & uncertain links

### B.1 GEDCOM→Neo4j (AuraDB / GenoPro GFG)

Canonical Neo4j genealogy import creates **`Person`**, **`Union`** (a
reification of marriage/partnership, *not* a direct PARENT edge), and
**`Place`** nodes:

```
(:Person {id, firstName, lastName, birthYear, deathYear, sex})
(:Person)-[:FATHER|:MOTHER]->(:Union)
(:Union)-[:CHILD]->(:Person)
(:Person)-[:BORN_IN|:DIED_IN]->(:Place)
```

The **`Union` reification node** is the pattern: an n-ary fact
(two parents + multiple children + marriage event) cannot be a single binary
edge, so it becomes a node. **A single hadith narration event is structurally
identical**: one Hadith + an ordered set of narrators + a collection context
= an n-ary fact → reify as an **`Isnad`/`Chain`** node (this is exactly what
the Multi-IsnadSet and SemanticHadith models independently arrived at, §E).

The "Graphs for Genealogists" (GFG) work adds **multi-graph linking**:
separate graphs (GEDCOM tree, DNA-kit graph, record graph) are joined by
relationships from a *user-curated link file* connecting a node in one graph
to a node in another. **Port directly:** cross-tradition narrator identity
(the same historical person appearing in Sunni *rijāl* and Shiʿi *rijāl*)
should be a **curated `SAME_AS`/`IDENTIFIED_WITH` edge with provenance**,
not a hard merge — preserves each tradition's distinct evaluation.

Source: https://neo4j.com/blog/developer/discover-auradb-free-importing-gedcom-files-and-exploring-genealogy-ancestry-data-as-a-graph/
· https://jogg.info/wp-content/uploads/2022/11/101.003-Article.pdf

### B.2 GEDCOM-X conceptual model — Persona vs. Person, Conclusion, Confidence

The most directly transferable disambiguation model. GEDCOM-X separates:

- **`Persona`** — a person *as asserted by a single source* (surface
  identity, may be wrong/partial).
- **`Person` (Subject)** — the resolved real-world individual, "something
  with a unique and intrinsic identity."
- **`Conclusion`** — *any* interpreted fact is explicitly a conclusion, not
  raw truth; carries a **`confidence`** enum: `High | Medium | Low`.
- **`SourceReference`** — every conclusion links to the source(s) it rests
  on.
- **`Evidence`** — links a Subject to the Personas/Conclusions supporting it.

**Transferable schema for narrator disambiguation:**

```
(:NarratorMention {raw_string, source_collection, source_ref})   // = Persona
   -[:RESOLVES_TO {confidence: "high"|"medium"|"low",
                   method, asserted_by}]->
(:Narrator {canonical_id, primary_name, kunya, nisba, dates})    // = Subject
```

This solves the hadith **mukthirūn / mushtarik / muhmal** problem (homonymous
or under-specified narrators): you never destroy the ambiguous mention; you
attach a *confidence-qualified resolution edge*, and can hold **competing
resolutions simultaneously** (rijāl scholars disagree on identity). The
`confidence` enum is the genealogy-proven prior art for `sanad_confidence`'s
categorical sibling.

Source: https://github.com/FamilySearch/gedcomx/blob/master/specifications/conceptual-model-specification.md
· http://gedcomx.org/GEDCOM-X-and-the-Genealogical-Research-Process.html

---

## C. Provenance graphs — W3C PROV: uncertainty/attribution as first-class

PROV-O core: `prov:Entity`, `prov:Activity`, `prov:Agent`. Chains of entities
use `prov:wasDerivedFrom`; agent responsibility uses `prov:wasAttributedTo`
(Entity→Agent) and `prov:wasAssociatedWith` (Activity→Agent).

The key pattern is the **qualified relation**: a binary shortcut edge can be
*reified* into an intermediate class so extra properties attach to the link
itself:

```
:hadith42  prov:wasDerivedFrom        :hadith42_via_chainA .   # shortcut
:hadith42  prov:qualifiedDerivation [
              a            prov:Derivation ;
              prov:entity  :hadith42_via_chainA ;
              :confidence  "0.82"^^xsd:float ;
              :tradition   "sunni" ;
              :grader      :ibn_hajar
           ] .
```

PROV explicitly ships *both* the shortcut (`wasDerivedFrom`) and the
qualified node (`qualifiedDerivation` → `prov:Derivation`). **This is the
exact hybrid recommended for hadith:** keep fast plain `NARRATED_FROM` for
pathfinding/centrality, *and* a `prov:Derivation`-style qualifier node
(`:IsnadAttribution`) carrying `sanad_confidence`, `tradition`, `grade`,
`attributed_to`, `grader`. Map to PROV directly: `Narrator` ≈ `prov:Agent`;
`Hadith` text ≈ `prov:Entity`; the act of narration ≈ `prov:Activity`;
attribution of a hadith to the Prophet/Imam ≈ `prov:wasAttributedTo` with a
**qualified `prov:Attribution`** carrying `attributed_to` + dispute status.

**Transferable patterns:**

1. Reify the uncertain edge into a qualifier node (`prov:Derivation` /
   `prov:Attribution`) → `sanad_confidence` and `attributed_to`-disputes
   become first-class, queryable, and individually source-able.
2. Keep the binary shortcut edge alongside it for performance — PROV
   sanctions the redundancy.
3. `prov:wasAttributedTo` precisely models `ATTRIBUTED_TO` (hadith → Prophet
   ﷺ / Imam / Companion); qualify it to record *contested* attribution
   (marfūʿ vs. mawqūf vs. mursal is an attribution-level dispute).

Source: https://www.w3.org/TR/prov-o/ · https://www.w3.org/TR/prov-dm/

---

## D. Biomedical KGs — entity resolution at scale & controlled vocabularies

### D.1 Hetionet — metagraph, per-edge license/source, multi-source merge

Hetionet v1.0: 47,031 nodes (11 metanodes), 2,250,197 edges (24 metaedges),
integrated from **29 databases**. Design facts:

- **Metagraph / schema layer.** A separate `definitions.json` formally
  defines every metanode, metaedge, and node/edge property — a machine-
  readable schema. *Port:* maintain a `tradition`-aware metagraph manifest
  for hadith (which edge types/grades are valid per tradition).
- **Directionality declared per metaedge.** Only `Gene–regulates–Gene` is
  directed; all others undirected. *Port:* `NARRATED_FROM` is *strictly
  directed* (heard-from → transmitter); `APPEARS_IN`, `IDENTIFIED_WITH`
  undirected — declare per relationship type explicitly.
- **`source` and `license` on every node AND edge.** Provenance is per-edge
  because the same edge may come from multiple of the 29 DBs. *Port:* every
  `NARRATED_FROM` / grade carries `source_collection`,
  `source_edition`, `extractor`, and (for grades) `grading_authority` — a
  hadith edge is only as trustworthy as its rijāl source.
- **Multi-source edges merged, not duplicated.** Compound–binds–Gene merges
  DrugBank/ChEMBL/DrugCentral/BindingDB into one edge with a source list.
  *Port:* the same narration attested by Bukhari *and* Muslim → one logical
  link with a `sources: []` array, not two parallel edges.

Source: https://het.io/ · https://neo4j.het.io/guides/hetionet.html ·
https://github.com/hetio/hetionet · https://elifesciences.org/articles/26726

### D.2 BioCypher / Mondo — ontology alignment for grading vocabularies

BioCypher maps curated data onto *selectable, linkable ontologies*; MedGraph
uses the Mondo disease ontology to normalize NER output; Neosemantics (n10s)
bridges RDF↔Neo4j. **Transferable pattern — controlled vocabulary as nodes,
not string literals:** hadith **grade** is *not* a free-text property. Make
each grade a node in a tradition-scoped vocabulary, so the Sunni ṣaḥīḥ/ḥasan/
ḍaʿīf scale and the Twelver ṣaḥīḥ/ḥasan/muwaththaq/ḍaʿīf scale and the Ibāḍī/
Zaydī scales coexist and align without flattening:

```
(:Grade {label:"sahih", tradition:"sunni", scale:"ibn_salah",
         rank:1, uri:"hadith:grade/sunni/sahih"})
(:Grade {label:"muwaththaq", tradition:"twelver", scale:"rijal", rank:3})
(:Grade)-[:ALIGNS_WITH {equivalence:"approximate"}]->(:Grade)
```

Source: https://neo4j.com/blog/developer/biocypher-biomedical-knowledge-graphs/
· https://github.com/rubalsxngh/MedGraph-Biomedical-Knowledge-Graph-with-Mondo-Ontology

---

## E. SemanticHadith ontology & Multi-IsnadSet Neo4j model (direct prior art)

### E.1 SemanticHadith Ontology v2.0.1 (Kamran, Abro & Basharat, 2023; JWS 78:100797)

Ontology-driven KG over 6 major Sunni collections; published as RDF/OWL via
OntoRefine; ontology + KG public on GitHub (A-Kamran/SemanticHadith-V2).
Modeled facts confirmed across sources:

- Hadith decomposed into **`matn`** (content) and **`sanad`** (chain) as
  distinct modeled constituents — *not* a single text blob.
- Core classes include **Hadith**, **Narrator**, **Book/Collection**,
  **Chapter**, and the **chain of narrators** as a structured object.
- Object property **`hasNarrator`** relates Hadith→Narrator; chain order is
  carried as a structured/ordered construct (the sanad object), not implicit.
- NLP pipeline extracts narrator mentions → mapped to OWL individuals via
  mapping rules (surface mention → resolved individual, the §B.2 pattern).

**Transferable:** validates the canonical node set
(Hadith / Narrator / Collection / Chapter) and that **sanad is a modeled
object, not a derived path** — i.e., reify the chain.

Source: https://www.sciencedirect.com/science/article/abs/pii/S1570826823000264
· https://a-kamran.github.io/SemanticHadith-V2/ ·
https://github.com/A-Kamran/SemanticHadith-V2 ·
https://www.semantic-web-journal.net/system/files/swj3651.pdf

### E.2 Multi-IsnadSet (MIS) — Sahih Muslim, Neo4j (Farooqi et al., 2024, *Data in Brief* 54:110439)

- **Directed multigraph**: **2,092 narrator nodes**, **77,797 edges** =
  Sanad–Hadith connections; built in Neo4j (also NetworkX/Gephi/Cytoscape).
- A **multi-directed graph**: parallel edges between the same two narrators
  carry *different* hadith/chain identities — i.e., the edge is keyed by
  `(narrator_from, narrator_to, hadith_id, chain_id)`, not just node pair.
- Per-entry record: original book, hadith number, MATN, narrator list,
  **narrator count**, **narrator sequence** (ordered), **ISNAD count**
  (multiple chains per hadith).
- Research framing shifts from longest/shortest sanad to **optimum/authentic
  sanad considering narrator qualities** — i.e., **edge weighting by
  narrator reliability** is the intended query, which *requires*
  `sanad_confidence` + per-narrator grade to live on/near the edge.
- Companion finding (Sahih Bukhari SNA, arXiv:2102.02009): narrator network
  is **scale-free** → hub narrators dominate; disambiguation errors on hubs
  are catastrophic, reinforcing the §B.2 confidence-qualified resolution.

**Transferable patterns (most directly applicable of all):**

1. **Multigraph keyed edges:** `NARRATED_FROM` must permit parallel edges
   distinguished by `hadith_id` + `chain_id`; never dedupe to a simple
   narrator-pair edge or you lose which chain a transmission belongs to.
2. **`narration_level` = explicit ordered `narrator_sequence`**, stored as
   a position int on each chain-link (the OpenAlex `author_position` pattern,
   independently re-derived here).
3. **`ISNAD count` ⇒ reify the chain**: one hadith has many chains → an
   `Isnad`/`Chain` node per chain, `Hadith-[:HAS_CHAIN]->Isnad`,
   `Isnad-[:HAS_LINK {position}]->Narrator`, enabling per-chain
   `sanad_confidence` and per-chain `grade`.

Source: https://pmc.ncbi.nlm.nih.gov/articles/PMC11096860/ ·
https://www.sciencedirect.com/science/article/pii/S2352340924004086 ·
https://arxiv.org/abs/2102.02009 ·
https://www.sciencedirect.com/science/article/pii/S1319157821000215

---

## F. Synthesized recommended Neo4j schema (ports applied)

```cypher
// --- Core entity nodes (SemanticHadith-validated set) ---
(:Hadith   {id, matn_ar, matn_norm, hadith_number})
(:Narrator {id, primary_name, kunya, nisba, laqab, death_year_ah})
(:Collection {id, title, tradition, compiler})
(:Chapter  {id, title, ordinal})

// --- Reified chain (Union/Isnad/prov:Derivation pattern: §B.1,§C,§E) ---
(:Isnad    {id, tradition, sanad_text,            // verbatim evidence (§A.2)
            sanad_confidence,                     // float, model/rule (§A.2)
            confidence_method})                   // rule|model|manual

(:Hadith)-[:HAS_CHAIN]->(:Isnad)
(:Isnad)-[:HAS_LINK {narration_level,             // ordinal (§A.1,§E.2)
                      sigha}]->(:Narrator)        // audition verb (§A.2)
(:Hadith)-[:APPEARS_IN {ordinal}]->(:Chapter)-[:PART_OF]->(:Collection)

// --- Fast shortcut edge kept ALONGSIDE reified chain (PROV §C) ---
// multigraph: keyed by hadith_id + chain_id (§E.2)
(:Narrator)-[:NARRATED_FROM {hadith_id, chain_id, narration_level,
                             tradition, sigha}]->(:Narrator)

// --- Attribution as qualified relation (prov:wasAttributedTo §C) ---
(:Hadith)-[:ATTRIBUTED_TO {attributed_to,         // Prophet|Imam|Companion
                           level,                  // marfu'|mawquf|mursal
                           disputed:bool}]->(:Authority)

// --- Grade as controlled-vocab node, tradition-scoped (Hetionet/Mondo §D) ---
(:Grade {label, tradition, scale, rank, uri})
(:Isnad)-[:GRADED {grading_authority, source_ref}]->(:Grade)
(:Grade)-[:ALIGNS_WITH {equivalence}]->(:Grade)   // cross-tradition map

// --- Disambiguation: mention vs. resolved (GEDCOM-X Persona/Subject §B.2) ---
(:NarratorMention {raw_string, source_collection, source_ref})
   -[:RESOLVES_TO {confidence, method, asserted_by}]->(:Narrator)

// --- Cross-tradition identity: curated, NOT merged (GFG §B.1) ---
(:Narrator)-[:IDENTIFIED_WITH {asserted_by, confidence}]->(:Narrator)

// --- Per-edge provenance everywhere (Hetionet §D.1) ---
//   every NARRATED_FROM / GRADED / RESOLVES_TO also carries:
//   {source_collection, source_edition, extractor, sources:[]}
```

### Top transferable lessons (ranked)

| # | Pattern | Donor domain | Hadith application |
|---|---------|--------------|--------------------|
| 1 | Reify the uncertain link into a node | PROV `Derivation`, OpenAlex `Authorship`, GEDCOM `Union` | `Isnad` node holds `sanad_confidence`, per-chain `grade` |
| 2 | Keep binary shortcut edge *and* qualifier node | W3C PROV (`wasDerivedFrom` + `qualifiedDerivation`) | fast `NARRATED_FROM` for SNA + `Isnad` for provenance |
| 3 | Ordinal position on the link | OpenAlex `author_position`, MIS `narrator_sequence` | `narration_level` on `HAS_LINK` |
| 4 | Surface mention ≠ resolved entity; confidence-qualified resolution; competing resolutions allowed | GEDCOM-X Persona/Subject, OpenAlex `raw_author_name` | solves mushtarik/muhmal narrator disambiguation |
| 5 | Controlled vocabulary as nodes, ontology-aligned | Hetionet/Mondo/BioCypher | tradition-scoped `Grade` nodes + `ALIGNS_WITH` |
| 6 | Per-node AND per-edge `source`/`license`; merge multi-source into one edge with `sources[]` | Hetionet (29 DBs) | rijāl source provenance on every grade/edge |
| 7 | Cross-graph identity = curated link, never hard merge | GFG genealogy multi-graph linking | cross-tradition `IDENTIFIED_WITH`, traditions stay distinct |
| 8 | Typed relation qualifier (intent/sigha) feeds confidence | Semantic Scholar citation `intents`/`is_influential` | `ʿanʿana` vs explicit audition → `sanad_confidence` input |
| 9 | Declare directionality per relationship type | Hetionet metagraph | `NARRATED_FROM` directed; `IDENTIFIED_WITH` undirected |
| 10 | Multigraph keyed by (hadith,chain), not node pair | Multi-IsnadSet Neo4j | parallel `NARRATED_FROM` edges per chain preserved |

---

## Sources

- OpenAlex Authorship object — https://docs.openalex.org/api-entities/works/work-object/authorship-object
- OpenAlex paper (arXiv) — https://arxiv.org/abs/2205.01833
- Semantic Scholar citation intent — https://www.semanticscholar.org/faq/citation-intent
- S2AG (ACM) — https://dl.acm.org/doi/10.1145/3487553.3527147
- GEDCOM→Neo4j (Neo4j blog) — https://neo4j.com/blog/developer/discover-auradb-free-importing-gedcom-files-and-exploring-genealogy-ancestry-data-as-a-graph/
- Graphs for Genealogists (JoGG) — https://jogg.info/wp-content/uploads/2022/11/101.003-Article.pdf
- GEDCOM-X conceptual model — https://github.com/FamilySearch/gedcomx/blob/master/specifications/conceptual-model-specification.md
- GEDCOM-X research process — http://gedcomx.org/GEDCOM-X-and-the-Genealogical-Research-Process.html
- W3C PROV-O — https://www.w3.org/TR/prov-o/
- W3C PROV-DM — https://www.w3.org/TR/prov-dm/
- Hetionet — https://het.io/ ; Neo4j guide — https://neo4j.het.io/guides/hetionet.html ; repo — https://github.com/hetio/hetionet ; eLife — https://elifesciences.org/articles/26726
- BioCypher — https://neo4j.com/blog/developer/biocypher-biomedical-knowledge-graphs/
- MedGraph/Mondo — https://github.com/rubalsxngh/MedGraph-Biomedical-Knowledge-Graph-with-Mondo-Ontology
- SemanticHadith (ScienceDirect) — https://www.sciencedirect.com/science/article/abs/pii/S1570826823000264
- SemanticHadith ontology site — https://a-kamran.github.io/SemanticHadith-V2/
- SemanticHadith repo — https://github.com/A-Kamran/SemanticHadith-V2
- SemanticHadith (SW Journal PDF) — https://www.semantic-web-journal.net/system/files/swj3651.pdf
- Multi-IsnadSet (PMC) — https://pmc.ncbi.nlm.nih.gov/articles/PMC11096860/
- Multi-IsnadSet (Data in Brief) — https://www.sciencedirect.com/science/article/pii/S2352340924004086
- SNA Hadith Bukhari (arXiv) — https://arxiv.org/abs/2102.02009
- Social network analysis of Hadith narrators — https://www.sciencedirect.com/science/article/pii/S1319157821000215
