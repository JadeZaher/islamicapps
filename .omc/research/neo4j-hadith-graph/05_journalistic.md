# Neo4j Data Model for a Multi-Tradition Hadith Isnad Graph — Journalistic / Practitioner How-To

**Persona:** Journalistic (practitioner how-to, exact recommendations)
**Date:** 2026-05-16
**Question:** Concrete, current best-practice Neo4j data model for a multi-tradition hadith isnad/narrator graph.

---

## 0. Grounding in the actual project data

Schema recommendations below are pinned to the fields the project already produces (verified in the repo, not assumed):

- `datasets/classify_attribution.py` produces **two** terminus fields per narration:
  - `narration_level` ∈ `{marfu, imam, mawquf, maqtu, unknown}`
  - `attributed_to` ∈ `{"Prophet Muhammad", "Prophet Muhammad (qudsi)", "Imam Ali", "Imam al-Sadiq", … "Zayd ibn Ali", "Ahl al-Bayt", "Companion", "Successor", "unknown"}`
- `datasets/hadith-data/sunni_isnad.jsonl` records per-hadith: `id, hadith_no, source, sanad` (ordered array of narrator name strings), `sanad_count`, `companion`, `matn_ar`, **`sanad_confidence`** (integer, e.g. `0` / `2`). Confidence is currently stored **per-hadith**, not per-edge — important modeling input (see §3.3).
- Traditions present: Sunni, Imami (Twelver), Zaydi, Ibadi, Musnad al-Rida — each with its own grading frame; a Sunni "sahih" and a Zaydi/Imami assessment must never collide (see §3.4).

The single most important real-data fact: `sanad` is an **ordered list of raw name strings** with known noise (`"ه سمع علقمة بن وقاص الليثي"`). Narrator identity resolution is a separate problem from graph topology — the model must let an unresolved name still participate in a chain (see §3.6).

---

## 1. Core design decision: reify the chain, do not use a bare relationship

Naive model: `(:Narrator)-[:NARRATED_TO]->(:Narrator)` and `(:Narrator)-[:NARRATED]->(:Hadith)`.

**Reject it.** A single `NARRATED_FROM` edge between two narrators is ambiguous the moment a narrator pair appears in many different hadiths with different positions, confidence, and tradition context. Neo4j's own guidance: *"If you find yourself wishing to put an index on a relationship property … factor that relationship out into a node — you're treating that relationship as a first-class object."* ([Neo4j modeling designs](https://neo4j.com/docs/getting-started/data-modeling/modeling-designs/), [GraphAware: qualifying relationships](https://graphaware.com/blog/neo4j-qualifying-relationships/)). The isnad link **is** a first-class object: it carries position, per-occurrence confidence, transmission term (`ʿan` / `ḥaddathanā` / `samiʿtu`), and belongs to a specific chain in a specific hadith.

The academic precedent agrees: the MIS multi-isnad dataset for Sahih Muslim explicitly models a *multi-directed* graph where the same narrator pair recurs across 77,797 Sanad-Hadith edges over 2,092 narrator nodes ([Multi-IsnadSet, Data in Brief 2024, PMC11096860](https://pmc.ncbi.nlm.nih.gov/articles/PMC11096860/)). rvanbruggen's reference Neo4j hadith implementation likewise keeps an aggregated weighted projection separate from the raw per-hadith `NARRATED` edges so PageRank runs on the aggregate ([Bruggen blog, 2022](https://blog.bruggen.com/2022/07/graphs-are-everywhere-also-in-religious.html), [gist](https://gist.github.com/rvanbruggen/a6e2e80a6fa7a253f46de9fbe9ce361f)).

**Chosen pattern: a `Chain` (reified isnad) node** sits between `Hadith` and the ordered narrator links. This cleanly solves multi-valued isnad (one hadith, many chains) — each chain is its own node, an interleaved linked list problem that Neo4j docs explicitly name ([linked-list KB](https://neo4j.com/developer/kb/creating-and-working-with-linked-lists/)).

---

## 2. Proposed schema

### 2.1 Node labels

| Label | Purpose | Key property | Other properties |
|---|---|---|---|
| `Narrator` | A transmitter (rawi). Identity-resolved canonical person. | `narrator_id` (stable slug) | `name_ar`, `name_en`, `kunya`, `laqab`, `death_year_h`, `generation` (tabaqa), `resolved` (bool) |
| `NameMention` | A raw, *unresolved* name string as it literally appears in a sanad. Optional bridge node (see §3.6). | `mention_id` | `raw_text`, `normalized` |
| `Hadith` | A single narration (matn + metadata). | `hadith_uid` (`{collection}:{hadith_no}`) | `hadith_no`, `matn_ar`, `matn_en`, `narration_level`, `attributed_to`, `sanad_confidence` (per-hadith, legacy/global) |
| `Chain` | One reified isnad (one path of transmission for one hadith). | `chain_id` (`{hadith_uid}#{n}`) | `chain_index`, `length`, `chain_confidence`, `is_primary` (bool) |
| `Collection` | A book/canon (Sahih Bukhari, al-Kafi, Musnad Zayd…). | `collection_id` | `title_ar`, `title_en`, `compiler`, `tradition` (denormalized for fast filter) |
| `Book` / `Chapter` | Structural division inside a collection (kitab / bab). | `section_id` | `title`, `order` |
| `Tradition` | Sunni / Imami / Zaydi / Ibadi / (Twelver vs sub-school). | `tradition_id` | `name` |
| `Authority` | The terminal speaker the report is attributed to (Prophet ﷺ, a named Imam, a Companion, a Successor, Ahl al-Bayt, unknown). Reified so cross-tradition queries share one Prophet node. | `authority_id` | `name`, `type` (`prophet`/`imam`/`companion`/`successor`/`ahl_al_bayt`/`unknown`), `is_qudsi` (bool) |
| `Assessment` | **Reified grade.** One scholar's/source's verdict on one hadith *within one tradition*. Never collapsed. | `assessment_id` | `grade` (e.g. `sahih`, `hasan`, `daif`, `muwaththaq`, `mursal`), `grade_source` (e.g. `al-Albani`, `al-Majlisi`, `Zaydi-default`), `grade_scheme` (`sunni`/`imami`/`zaydi`/`ibadi`), `rationale`, `created_at` |

`Grade` is **not** a node label. The grade *value* lives on the `Assessment` node together with its `grade_source` and `grade_scheme`. This is the qualifying-relationship / reification pattern applied to verdicts ([GraphAware](https://graphaware.com/blog/neo4j-qualifying-relationships/)): a Sunni `sahih` and a Zaydi verdict are two distinct `Assessment` nodes that physically cannot overwrite each other.

### 2.2 Relationship types

```
(:Hadith)-[:IN_COLLECTION]->(:Collection)
(:Hadith)-[:IN_SECTION]->(:Chapter)-[:PART_OF]->(:Book)-[:PART_OF]->(:Collection)
(:Collection)-[:OF_TRADITION]->(:Tradition)
(:Hadith)-[:HAS_CHAIN]->(:Chain)                     // 1 hadith → N chains (multi-isnad)
(:Chain)-[:HAS_LINK { position }]->(:Narrator)        // membership + position (set/index lookup)
(:Narrator)-[:NARRATED_FROM { ... }]->(:Narrator)     // ordered link WITHIN one chain (see props)
(:Chain)-[:STARTS_WITH]->(:Narrator)                  // entry pointer (collector end)
(:Chain)-[:ENDS_AT]->(:Narrator)                      // terminal narrator (closest to source)
(:Hadith)-[:ATTRIBUTED_TO]->(:Authority)              // narration_level + attributed_to
(:Hadith)-[:GRADED_AS]->(:Assessment)-[:UNDER_SCHEME]->(:Tradition)
(:Narrator)-[:SAME_AS]->(:Narrator)                   // identity merge candidates (optional)
(:NameMention)-[:RESOLVES_TO { confidence }]->(:Narrator)   // §3.6 unresolved-name bridge
```

**Property placement decisions (the load-bearing choices):**

- `NARRATED_FROM` is **scoped to a single chain** and carries:
  - `chain_id` — which reified chain this edge belongs to (lets you index/filter without walking through the `Chain` supernode)
  - `position` — integer index of the *source* narrator in that chain (0 = collector)
  - `term` — transmission verb extracted from the sanad/matn (`ʿan`, `ḥaddathanā`, `akhbaranā`, `samiʿtu`, `qāla`); analytically critical (a `samiʿtu` link is stronger than an `ʿan`)
  - `edge_confidence` — **per-edge** transmission confidence (see §3.3)
  - `tradition` — denormalized for GDS filtering without a join
- `position` lives on **both** `HAS_LINK` (set membership / "who is at slot 3") **and** is implied by `NARRATED_FROM` ordering. The `NARRATED_FROM` linked list is the source of truth for traversal; `HAS_LINK.position` is a denormalized index for fast "give me chain as array" / centrality-input queries. Neo4j docs explicitly bless a single-linked-list-plus-parent-pointer pattern and warn against doubly-linked lists ([linked-list KB](https://neo4j.com/developer/kb/creating-and-working-with-linked-lists/)) — so use only `NARRATED_FROM` (collector → source direction), never a redundant `NARRATED_TO`.

### 2.3 ASCII diagram

```
                 (:Tradition "Zaydi")
                        ^
                        | OF_TRADITION
   (:Collection "Musnad Zayd") <--IN_COLLECTION-- (:Hadith) --ATTRIBUTED_TO--> (:Authority {Imam Ali, type:imam})
                                                     |  \
                                          HAS_CHAIN  |   \  GRADED_AS
                                          /          |    \
                                    (:Chain #0)  (:Chain #1)  (:Assessment {grade:'muwaththaq',
                                       |               |        grade_source:'Zaydi-default',
                       STARTS_WITH/ENDS_AT  HAS_LINK{pos}        grade_scheme:'zaydi'})
                                       |               |               |
                                       v               v          UNDER_SCHEME
            (:Narrator collector) -NARRATED_FROM{pos:0,term:'haddathana',
                                    edge_confidence:0.9,chain_id}-> (:Narrator) -...-> (:Narrator terminal)
```

---

## 3. Modeling the specific hard fields

### 3.1 `narration_level` + `attributed_to`

These two are a *person + level* pair (the code comment in `classify_attribution.py` says exactly this). Model as **one `ATTRIBUTED_TO` edge to a reified `Authority` node**, with `narration_level` on the edge and the canonical authority on the node:

```cypher
MERGE (a:Authority {authority_id: 'prophet-muhammad'})
  ON CREATE SET a.name='Prophet Muhammad', a.type='prophet', a.is_qudsi=false
MERGE (h)-[r:ATTRIBUTED_TO]->(a)
SET r.narration_level = 'marfu', r.is_qudsi = false
```

Why a node, not just two properties on `Hadith`: every cross-tradition "all marfūʿ reports that terminate at the Prophet" query, and any centrality on *who reports stop at*, needs `Authority` as a shared join target. A single Prophet ﷺ node shared across Sunni/Imami/Zaydi/Ibadi corpora is the entire point of a multi-tradition graph. For `imam` level, `attributed_to` ("Imam al-Sadiq", "Zayd ibn Ali", "Ahl al-Bayt") becomes the `Authority.name`/`authority_id`; `unknown` gets a single shared `authority_id:'unknown'` node so they are filterable, not silently merged.

### 3.2 Tradition placement

Put `tradition` **on `Collection`** as the source of truth (`Collection-[:OF_TRADITION]->Tradition`), and **denormalize** it onto `Hadith`, `Chain`, `NARRATED_FROM`, and `Assessment.grade_scheme`. Denormalization here is deliberate: GDS graph projections and broken-chain queries must filter by tradition without a 3-hop join on every row. Neo4j's qualifying-relationship benchmark shows property/relationship-type filtering beats deep traversal for this exact "subset of a big graph" case ([GraphAware](https://graphaware.com/blog/neo4j-qualifying-relationships/)).

### 3.3 `sanad_confidence` — per-edge vs per-hadith

The data currently stores it **per-hadith** (`sunni_isnad.jsonl` → `sanad_confidence: 2` / `0`). Recommendation: **keep both, at different granularities, do not throw the existing one away** (and per project memory, never destroy existing fields):

- `Hadith.sanad_confidence` — keep the existing per-hadith integer as-is (legacy/global signal: 0 = no/empty sanad, higher = parsed cleanly).
- `Chain.chain_confidence` — per reified chain (a hadith with 3 chains can have one clean and two broken).
- `NARRATED_FROM.edge_confidence` — **per-edge** float `0.0–1.0`, the analytically correct granularity. Derive it initially from term strength (`samiʿtu` > `ḥaddathanā` > `ʿan` > inferred) × name-resolution confidence. This is the property GDS will filter and weight on.

Rule of thumb: *store confidence at the finest grain you can defend, aggregate upward for convenience.* Edge-level is finest; chain and hadith levels are cached rollups.

### 3.4 Tradition-specific grade — the no-collision requirement

**Hard rule: never put `grade` as a property on `Hadith`.** A reified `Assessment` node per (hadith, source) pair:

```cypher
MATCH (h:Hadith {hadith_uid:'sahih-bukhari:1'})
MERGE (asm:Assessment {assessment_id:'sahih-bukhari:1#albani'})
  SET asm.grade='sahih', asm.grade_source='al-Albani',
      asm.grade_scheme='sunni', asm.created_at=datetime()
MERGE (h)-[:GRADED_AS]->(asm)
WITH asm MATCH (t:Tradition {tradition_id:'sunni'}) MERGE (asm)-[:UNDER_SCHEME]->(t)
```

A Zaydi verdict on the same matn is a *different* `Assessment` node (`…#zaydi-default`, `grade_scheme:'zaydi'`). They are physically incapable of colliding because they are distinct nodes; queries always filter `WHERE asm.grade_scheme = $scheme`. This is exactly the "different relationship types / qualifier node beats single-property" finding ([GraphAware qualifying relationships](https://graphaware.com/blog/neo4j-qualifying-relationships/); reinforced by Neo4j context-graph provenance modeling, [Neo4j blog 2026](https://neo4j.com/blog/agentic-ai/hands-on-with-context-graphs-and-neo4j/)).

### 3.5 Multi-valued isnad (one hadith, many chains)

Solved structurally by the `Chain` node: `(:Hadith)-[:HAS_CHAIN]->(:Chain)` cardinality 1→N. Each `Chain` is its own linked list of `NARRATED_FROM` edges carrying `chain_id`. This is the interleaved-linked-list pattern Neo4j docs describe for "same items, multiple sequences" ([linked-list KB](https://neo4j.com/developer/kb/creating-and-working-with-linked-lists/)) and matches the MIS multi-isnad academic model ([PMC11096860](https://pmc.ncbi.nlm.nih.gov/articles/PMC11096860/)). Mark the strongest with `Chain.is_primary=true`.

### 3.6 Unresolved / noisy name strings

Real sanads contain garbage tokens (`"ه سمع علقمة بن وقاص الليثي"`). Two-tier:

- Resolved tokens → directly `(:Narrator {resolved:true})`.
- Unresolved/ambiguous → `(:NameMention {raw_text})` that still participates in the chain via `NARRATED_FROM`, plus `(:NameMention)-[:RESOLVES_TO {confidence}]->(:Narrator)` once disambiguated (many-to-one allowed). This keeps topology intact while identity resolution proceeds independently and analytics can choose to include or exclude `:NameMention` nodes.

### 3.7 Modeling uncertain / low-confidence edges so analytics can filter

Every analytic edge (`NARRATED_FROM`) carries `edge_confidence` (float) **and** `tradition`. GDS projections then filter at projection time:

```cypher
CALL gds.graph.project.cypher(
  'isnad_strong',
  'MATCH (n:Narrator) RETURN id(n) AS id',
  'MATCH (a:Narrator)-[r:NARRATED_FROM]->(b:Narrator)
   WHERE r.edge_confidence >= 0.6 AND r.tradition = "Sunni"
   RETURN id(a) AS source, id(b) AS target, r.edge_confidence AS weight'
);
```

GDS PageRank/Betweenness consume `relationshipWeightProperty: 'weight'` ([Neo4j PageRank docs](https://neo4j.com/docs/graph-data-science/current/algorithms/page-rank/), [Betweenness docs](https://neo4j.com/docs/graph-data-science/current/algorithms/betweenness-centrality/)). Low-confidence edges are *never deleted* — they are excluded by the projection predicate, so different analyses can pick different thresholds.

---

## 4. Constraints & indexes (run these first)

```cypher
// --- Uniqueness / node keys (also create backing composite indexes) ---
CREATE CONSTRAINT narrator_id  IF NOT EXISTS FOR (n:Narrator)   REQUIRE n.narrator_id  IS UNIQUE;
CREATE CONSTRAINT hadith_uid   IF NOT EXISTS FOR (h:Hadith)     REQUIRE h.hadith_uid   IS UNIQUE;
CREATE CONSTRAINT chain_id     IF NOT EXISTS FOR (c:Chain)      REQUIRE c.chain_id     IS UNIQUE;
CREATE CONSTRAINT coll_id      IF NOT EXISTS FOR (c:Collection) REQUIRE c.collection_id IS UNIQUE;
CREATE CONSTRAINT trad_id      IF NOT EXISTS FOR (t:Tradition)  REQUIRE t.tradition_id IS UNIQUE;
CREATE CONSTRAINT auth_id      IF NOT EXISTS FOR (a:Authority)  REQUIRE a.authority_id IS UNIQUE;
// Composite NODE KEY: an assessment is unique per hadith+source+scheme (the no-collision guarantee)
CREATE CONSTRAINT asm_key      IF NOT EXISTS FOR (a:Assessment)
  REQUIRE (a.assessment_id) IS NODE KEY;

// --- Lookup / traversal indexes ---
CREATE INDEX narrator_name   IF NOT EXISTS FOR (n:Narrator) ON (n.name_ar);
CREATE INDEX hadith_attr     IF NOT EXISTS FOR (h:Hadith)   ON (h.narration_level, h.attributed_to);
CREATE INDEX coll_tradition  IF NOT EXISTS FOR (c:Collection) ON (c.tradition);
CREATE INDEX asm_scheme      IF NOT EXISTS FOR (a:Assessment) ON (a.grade_scheme, a.grade);
// --- Relationship property indexes (Neo4j 4.3+/5.x) for confidence/tradition filtering ---
CREATE INDEX rel_conf  IF NOT EXISTS FOR ()-[r:NARRATED_FROM]-() ON (r.edge_confidence);
CREATE INDEX rel_chain IF NOT EXISTS FOR ()-[r:NARRATED_FROM]-() ON (r.chain_id, r.position);
```

A node-key constraint automatically backs a composite index, so no separate index is needed on `assessment_id` ([Neo4j create-constraints docs](https://neo4j.com/docs/cypher-manual/current/constraints/syntax/), [search-performance indexes](https://neo4j.com/docs/cypher-manual/current/indexes/search-performance-indexes/create-indexes/)). Relationship range indexes are first-class in Neo4j 5.x and are what makes the `edge_confidence` / `chain_id` filters fast without walking the `Chain` node.

---

## 5. Cypher for the four common queries

### 5.1 Full chain reconstruction (one hadith, all its isnads, in order)

```cypher
MATCH (h:Hadith {hadith_uid:'sahih-bukhari:1'})-[:HAS_CHAIN]->(c:Chain)
MATCH p = (start:Narrator)-[:NARRATED_FROM* {chain_id: c.chain_id}]->(end:Narrator)
WHERE (c)-[:STARTS_WITH]->(start) AND (c)-[:ENDS_AT]->(end)
RETURN c.chain_id AS chain,
       c.is_primary AS primary,
       [n IN nodes(p) | coalesce(n.name_en, n.name_ar)] AS isnad,
       [r IN relationships(p) | {term:r.term, conf:r.edge_confidence}] AS links
ORDER BY c.chain_index;
```

(The `{chain_id: c.chain_id}` relationship-pattern predicate keeps the variable-length walk inside the one reified chain — the reason `chain_id` is denormalized onto the edge.)

### 5.2 Narrator centrality input (weighted projection → PageRank)

```cypher
CALL gds.graph.project.cypher(
  'isnad_w',
  'MATCH (n:Narrator) RETURN id(n) AS id',
  'MATCH (a:Narrator)-[r:NARRATED_FROM]->(b:Narrator)
   WHERE r.edge_confidence >= 0.5
   RETURN id(a) AS source, id(b) AS target,
          avg(r.edge_confidence) AS weight'        // collapse multigraph → weighted
);
CALL gds.pageRank.stream('isnad_w', {relationshipWeightProperty:'weight'})
YIELD nodeId, score
RETURN gds.util.asNode(nodeId).name_ar AS narrator, score
ORDER BY score DESC LIMIT 25;
```

Mirrors rvanbruggen's `AGGREGATED_HADITH_CHAIN` weighted-projection-then-PageRank approach ([Bruggen blog](https://blog.bruggen.com/2022/07/graphs-are-everywhere-also-in-religious.html)) and Neo4j GDS weighting docs ([PageRank](https://neo4j.com/docs/graph-data-science/current/algorithms/page-rank/)).

### 5.3 Broken-chain detection (gaps / dangling / missing terminus)

```cypher
// (a) chain whose declared length != actual traversable hop count → a gap
MATCH (h:Hadith)-[:HAS_CHAIN]->(c:Chain)-[:STARTS_WITH]->(s:Narrator)
MATCH path = (s)-[:NARRATED_FROM* {chain_id:c.chain_id}]->(e:Narrator)
WHERE (c)-[:ENDS_AT]->(e)
WITH c, h, max(length(path)) AS hops
WHERE hops + 1 <> c.length
RETURN h.hadith_uid, c.chain_id, c.length AS declared, hops+1 AS reachable;

// (b) chain that never reaches an Authority (mursal / munqati' candidate)
MATCH (h:Hadith)-[:HAS_CHAIN]->(c:Chain)
WHERE NOT (h)-[:ATTRIBUTED_TO]->(:Authority)
   OR c.length = 0
RETURN h.hadith_uid, c.chain_id, h.narration_level;

// (c) unresolved links still in the path (analytics quality gate)
MATCH (c:Chain)-[:HAS_LINK]->(m:NameMention)
WHERE NOT (m)-[:RESOLVES_TO]->(:Narrator)
RETURN c.chain_id, count(m) AS unresolved ORDER BY unresolved DESC;
```

### 5.4 Cross-tradition shared-matn (same report, different canons/grades)

```cypher
// Hadiths sharing a matn cluster, surfaced across traditions with their
// tradition-scoped grades side by side (no grade collision because each
// Assessment is its own node, filtered by scheme).
MATCH (h:Hadith)-[:IN_COLLECTION]->(col:Collection)-[:OF_TRADITION]->(t:Tradition)
WHERE h.matn_cluster_id = $cluster        // produced by separate matn-similarity job
OPTIONAL MATCH (h)-[:GRADED_AS]->(asm:Assessment)
RETURN t.name AS tradition,
       col.title_en AS collection,
       h.hadith_uid,
       h.narration_level,
       collect(DISTINCT {scheme:asm.grade_scheme,
                          grade :asm.grade,
                          source:asm.grade_source}) AS verdicts
ORDER BY tradition;
```

(The matn cluster id is computed by the vector/embedding pipeline noted in project memory; the graph only stores the cluster key and lets each tradition keep its own `Assessment` nodes — that is the cross-tradition payoff.)

---

## 6. Summary of the load-bearing recommendations

1. **Reify the isnad** with a `Chain` node; never rely on a bare narrator→narrator edge — it cannot carry per-occurrence position/confidence/term and breaks under multi-isnad.
2. **Single-linked `NARRATED_FROM`** (collector→source) carrying `chain_id, position, term, edge_confidence, tradition`; no doubly-linked list.
3. **Reify both `Authority` and `Assessment`.** One shared Prophet ﷺ node across traditions; one `Assessment` node per (hadith, source, scheme) so a Sunni *sahih* and a Zaydi/Imami verdict are physically distinct and filtered by `grade_scheme` — they cannot collide.
4. **Confidence at every grain, finest is canonical:** `edge_confidence` (analytic truth) → `chain_confidence` → keep legacy `Hadith.sanad_confidence`. Never delete weak edges; exclude them in GDS projections by predicate.
5. **`NameMention` bridge** keeps noisy unresolved names in the topology without polluting `Narrator` identity.
6. Constraints + relationship property indexes (`edge_confidence`, `chain_id+position`) make chain reconstruction and centrality projections fast.

---

## Sources

- [Neo4j — Modeling designs (Getting Started)](https://neo4j.com/docs/getting-started/data-modeling/modeling-designs/)
- [Neo4j — Graph Modeling Guidelines (Developer Guides)](https://neo4j.com/developer/guide-data-modeling/)
- [Neo4j KB — Creating and working with linked lists in Cypher](https://neo4j.com/developer/kb/creating-and-working-with-linked-lists/)
- [Neo4j — Create constraints (Cypher Manual)](https://neo4j.com/docs/cypher-manual/current/constraints/syntax/)
- [Neo4j — Create search-performance indexes (Cypher Manual)](https://neo4j.com/docs/cypher-manual/current/indexes/search-performance-indexes/create-indexes/)
- [Neo4j GDS — PageRank](https://neo4j.com/docs/graph-data-science/current/algorithms/page-rank/)
- [Neo4j GDS — Betweenness Centrality](https://neo4j.com/docs/graph-data-science/current/algorithms/betweenness-centrality/)
- [Neo4j Blog (2026) — Hands On With Context Graphs and Neo4j (provenance/qualifier modeling)](https://neo4j.com/blog/agentic-ai/hands-on-with-context-graphs-and-neo4j/)
- [GraphAware — Modelling data in Neo4j: qualifying relationships](https://graphaware.com/blog/neo4j-qualifying-relationships/)
- [Multi-IsnadSet (MIS) for Sahih Muslim, Data in Brief 2024 — PMC11096860](https://pmc.ncbi.nlm.nih.gov/articles/PMC11096860/)
- [Social Network Analysis of Hadith Narrators (ScienceDirect S1319157821000215)](https://www.sciencedirect.com/science/article/pii/S1319157821000215)
- [Social Network Analysis of Hadith Narrators from Sahih Bukhari (arXiv 2102.02009)](https://arxiv.org/abs/2102.02009)
- [rvanbruggen — Hadith Narrator Graph (gist)](https://gist.github.com/rvanbruggen/a6e2e80a6fa7a253f46de9fbe9ce361f) / [Bruggen Blog, July 2022](https://blog.bruggen.com/2022/07/graphs-are-everywhere-also-in-religious.html)
- [A Novel Graph-Based Representation for Hadith Sanad (IJATCSE)](http://www.warse.org/IJATCSE/static/pdf/file/ijatcse58815sl2019.pdf)
- Project files grounding the schema: `datasets/classify_attribution.py`, `datasets/hadith-data/sunni_isnad.jsonl`, `datasets/extract_isnad.py`
