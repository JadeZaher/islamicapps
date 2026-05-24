# Insight 02 — Phased, GIGO-Safe Delivery Roadmap

**Role:** Emergent-Insight Agent 2 (Phased Roadmap)
**Inputs:** 01–08 personas + crucible_01 (convergence/tension) + crucible_02 (evidence/feasibility audit)
**Date:** 2026-05-16

---

## 0. The non-negotiable honesty contract (applies to every phase)

This roadmap is built on what the evidence crucible *verified on disk*, not on the prompt's premises. Five facts gate everything:

1. **It is brownfield with a LIVE idempotency bug.** `src/scripts/import-datasets.ts:370-389` does `MERGE (n:Narrator {id:$id})` with `id = uuidv4()` minted fresh per run (line 311). It does **not** use `neo4j-helpers.ts`. **Every re-run duplicates every narrator node.** The helpers are aspirational scaffolding, not the wired path.
2. **The same importer hard-codes the R1 fallacy.** Line 315/378 stores `n.reliability` as a scalar on the Narrator node — the single most destructive modeling error (C1, 7/8 personas), already in production code.
3. **The row count is wrong.** All eight personas inherited "69,368" from the prompt. `all_hadiths_unified.csv` on disk = **78,951 data rows** (78,952 lines incl. header). The clean view is 37,043. Nobody re-counted; the Systems validation gate "expected ≈ 69,368" would fail on the real file.
4. **Accuracy numbers are search-digest, Sunni-synthetic.** 97.8% / 94.6% are abstract-only, on AR-Sanad synthetic data dominated by the easy 94% of unique surface forms. The honest planning ceiling is **~83 F1 on real Sunni Arabic**; **cross-tradition (Shia/Zaydi/Ibadi) and transliterated chains are entirely unmeasured = research-grade**.
5. **`~12% unknown attribution` is unverified.** `classify_attribution.py` has an `unknown` bucket and `--stats` mode but no one ran it. Plausible by design; **must be measured, not assumed.**

**The GIGO firewall:** the graph is a sound *navigational/representational* artifact from Phase 1; it is **NOT a sound analytical engine** until entity resolution + Sunni-story-chain parsing + uncertainty propagation are done and stratified. No centrality/community/grading number is ever shipped as a *result* before Phase 3's gate passes. Descriptive framing only ("extracted chain", "al-Najashi graded X as…") — never "this hadith is weak", never a global authenticity score.

**STOP-THE-LINE rule:** each phase boundary is a hard gate. If any exit criterion fails, the line stops — no downstream phase begins, no analytic is exposed. Gates are measured, logged to the `DatasetVersion` node, and require explicit sign-off. A failed gate is a *finding to publish*, not noise to hide.

---

## PHASE 0 — Must-Fix-Now (stop the bleeding) · Effort: S · Reliability: production

**Purpose:** retire the live bug and the false dataset facts before any schema work. Nothing here asserts accuracy; it is pure correctness.

### Entry criteria
- None. This is the unconditional first work. Any current graph build is non-idempotent and node-id-churning.

### Scope (exactly three things)
1. **Kill narrator duplication.** Rewrite `import-datasets.ts:370-389` to `MERGE (n:Narrator {narrator_key})` where `narrator_key = "RAWI:" + scholar_indx` (the curated, regen-stable key from the 24,326-row `all_rawis.csv`). `id = randomUUID()` moves to `ON CREATE` only. Route through the existing `neo4j-helpers.ts` (`mergeNodeByKey`) so the wired path equals the aspirational one. Apply the same fix to the 5 sibling importers (`import-classical/shia/zaydi/musnad/pure-canon`) and `link-sanad-chains.ts`.
2. **Pin the true record count.** Re-count `all_hadiths_unified.csv` from disk → **78,951** (note the line/record artifact: 78,952 lines incl. header; clean view 37,043). Write the real numbers into a dataset-version sidecar manifest + an in-graph `(:DatasetVersion {version, row_count, sha256, git_commit, generated_at})`; every Hadith `MERGE (h)-[:LOADED_FROM]->(dv)`. Delete every "69,368" assertion from code/gates/docs.
3. **Stable business keys, generalized.** Generalize the existing `_sunni_key = "{source}|{hadith_no}"` to **all** traditions (`hadith_biz_key`); OpenITI rows use `"{source}|{kitab}.{bab}.{hadith_no}"` to guarantee uniqueness. Narrator fallback for names not in `all_rawis.csv`: `narrator_key = "EXT:" + uuid5(NAMESPACE, normalized_arabic_name)` (deterministic across regens).

### Exit criteria (STOP-THE-LINE gate G0)
- Running the importer **twice** produces byte-identical node/edge counts (idempotency proven, not asserted) — automated test.
- `MATCH (n:Narrator) WITH n.narrator_key AS k, count(*) c WHERE c>1 RETURN k` returns **zero rows**.
- `n.reliability` scalar **removed** from the Narrator MERGE (replaced by Phase-1 Assessment, or temporarily dropped — it is the R1 bug; do not preserve it on the node).
- Real row count pinned in sidecar + `DatasetVersion`; no "69,368" remains in the repo.
- `~12% unknown` **measured**: run `classify_attribution.py --stats`, record the true `unknown` fraction in the manifest.

### Reliable vs deferred
- **Reliable now:** idempotency, stable keys, true counts, provenance node. All mechanical, primary-verified.
- **Deferred:** all schema reification (Phase 1), all analytics (Phase 3).

### Risk retired
**R7 (node-ID churn)** and the live duplication bug; the false-fact risk (planning on a wrong count). Removing the scalar `reliability` also pre-empts **R1** entering deeper.

---

## PHASE 1 — Honest Foundation (schema + provenance, NO analytics) · Effort: M · Reliability: production

**Purpose:** load the corpus into the convergent, engine-agnostic schema with full provenance and per-edge confidence. This phase is honest *regardless of extraction noise* because it asserts structure + provenance only — never accuracy.

### Entry criteria
- G0 passed (idempotent, keyed, counted).
- **Q1 ratified** (crucible_01): is the deliverable a research dataset or an interactive product? The schema below is engine-agnostic; the *engine* (Neo4j vs Postgres+AGE/networkx vs RDF) is consciously decided here, not assumed. The Contrarian's ordering critique is answered by designing the schema first and gating the engine on demonstrated need. Default: keep the existing Neo4j layer (brownfield, already wired) but the schema must remain portable.

### Scope — the schema all schema-personas converged on (C1, C2, C3, C7)
- **Reify the chain.** `(:Hadith)-[:HAS_CHAIN]->(:Chain)`; `(:Chain)-[:HAS_LINK {position}]->(:Narrator)`; one hadith → N chains (multi-isnad first-class, C3). Keep a **fast shortcut** `(:Narrator)-[:NARRATED_FROM {chain_id, position, term, edge_confidence, tradition}]->(:Narrator)` alongside (PROV-sanctioned redundancy, two-layer model C2).
- **Reify Authority.** `(:Hadith)-[:ATTRIBUTED_TO {narration_level}]->(:Authority)` — one shared Prophet ﷺ node across traditions; `attributed_to`/`narration_level` from the repo's own `classify_attribution.py` person+level design (verified-primary).
- **Tradition-scoped Assessment, NEVER a scalar grade (C1 — the most robust finding, 7/8 personas).** `(:Hadith)-[:GRADED_AS]->(:Assessment {grade, grade_source, grade_scheme})-[:UNDER_SCHEME]->(:Tradition)`. A Sunni *sahih* and a Zaydi/Imami verdict are physically distinct nodes, filtered by `grade_scheme`. **Absence is representable:** Zaydi/Ibadi with no extant rijal verdict → explicit `grade=NULL, reason="no_extant_evaluation_in_tradition"`, never inherited from Sunni.
- **Forbid bare grades (R6).** Ingest rejects any grade without `grader`/`work`/`edition`/`tradition`, or stamps `grade_unsourced=true` and excludes it from authoritative queries/UI. `:Source` node carries a license flag (`public_domain_classical` vs `modern_critical_edition_restricted`); restricted-edition verdicts stored as citation pointer, **not redistributed text** (copyright trap).
- **Per-edge provenance + confidence as first-class (C6).** Every `NARRATED_FROM`/`GRADED_AS` carries `source_collection`, `extraction_method ∈ {regex, story-unstructured, manual}`, and `edge_confidence`. Keep the legacy per-hadith `sanad_confidence` integer immutable (no-delete directive); derive per-chain/per-edge rollups where defensible (full derivation depends on Phase 2 — see T3).
- **NameMention bridge (prep for Phase 2).** Unresolved/noisy tokens (`"ه سمع علقمة بن وقاص الليثي"`, verified on disk) become `(:NameMention {raw_text})` that still participate in the chain via `NARRATED_FROM`, with `(:NameMention)-[:RESOLVES_TO {confidence}]->(:Narrator)` added in Phase 2. Topology stays intact while identity resolution proceeds separately.
- **Constraints first** (uniqueness on every business key + node-key on `assessment_id`; relationship indexes on `edge_confidence`, `chain_id+position`).

**Explicitly NOT in Phase 1:** no PageRank/centrality, no community detection, no link prediction, no matn-reuse, no automated grading, no GDS projection used as a result. The graph is a finding aid only.

### Exit criteria (STOP-THE-LINE gate G1 — the validation gates)
Run on generated CSVs **before** load and via Cypher **after** load; fail-closed on any breach:
- **Counts:** loaded `:Hadith` == manifest `row_count` (78,951 full / 37,043 clean — whichever view loaded); `:Chain` ≥ `:Hadith` (multi-isnad never collapses below 1:1).
- **Dangling edges:** zero `NARRATED_FROM`/`HAS_LINK` endpoints with null `narrator_key`; zero `HAS_CHAIN` orphans; every `Assessment` has exactly one `UNDER_SCHEME`.
- **Constraint coverage:** all declared uniqueness/node-key constraints present (`SHOW CONSTRAINTS` assertion); no scalar `reliability`/bare `grade` on any node (anti-regression assertion for R1/R6).
- **Confidence distribution:** every `NARRATED_FROM` has non-null `edge_confidence` and `extraction_method`; the distribution is logged (histogram by `extraction_method` × `tradition`) — this is the baseline Phase 3 will stratify on. A degenerate distribution (all-equal confidence, or `extraction_method` missing for a tradition) **fails the gate**.
- **Provenance:** 100% of hadith have `LOADED_FROM`→`DatasetVersion`; 100% of grades have a `:Source` with a license flag.

### Reliable vs deferred
- **Reliable now:** the entire schema (corroborated by PROV/OpenAlex/GEDCOM-X primary specs + the repo's own `classify_attribution.py`) — the strongest, safest finding in the corpus.
- **Deferred:** entity resolution accuracy (Phase 2), every analytic (Phase 3), cross-tradition links (Phase 2+).

### Risk retired
**R1** (unified-narrator fallacy — structurally impossible now), **R6** (grade provenance/copyright), partially **R5** (metadata slots exist: `death_year`, `tabaqa`, `locations[]`, `kunya[]` nullable + `*_uncertain`).

---

## PHASE 2 — Entity Resolution (the gate everything analytic depends on) · Effort: M (cheap path) → L-XL (hard core) · Reliability: production (94% path) / research-grade (ambiguous core)

**Purpose:** turn `NameMention` surface forms into resolved `Narrator` identities. Crucible_01 §3 is explicit: **D2 is THE gate — every analytic (Phase 3) and grading-support (Phase 4) is "confidently wrong" until this is done and uncertainty propagated.**

### Entry criteria
- G1 passed.
- **Q2 ratified:** the project commits to entity resolution as a hard prerequisite before any analytic ships. If "no", the analytics deliverable (Phase 3) is **cut**, not shipped with disclaimers nobody reads.

### Scope — the asymmetric two-path strategy (Archaeological 06)
1. **Cheap path first — exact lexicon lookup (~94%, but unproven here).** Normalize (strip tashkīl/tatwīl, unify alef/yā'/tā'-marbūṭa/hamza, `ابن/بن/ب.`) then exact-match against `all_rawis.csv` `scholar_indx` + appearance forms / AR-Sanad lexicon. The 94% figure is AR-Sanad Sunni-synthetic — **build the mechanism, do NOT promise 94% on this data**; measure actual coverage and report it.
2. **Hard core — the ~3.5K ambiguous collision set.** ~3,477 of 61,598 surface forms are shared (kunya/laqab collisions: "Abū Jaʿfar", "Hishām", bare "Muḥammad b. …"). Two-stage retrieve→rerank: graph-structural blocking (adjacent narrators + tabaqa/death-year temporal feasibility — a cheap, high-precision hard prune) → AraBERT/classical-BERT cross-encoder. **Mandatory human-in-the-loop:** any small top-1/top-2 margin or kunya-only match routes to a rijal expert; active learning prioritizes highest-uncertainty/highest-graph-impact nodes.
3. **Cross-tradition SAME_AS — explicit + reviewed ONLY (C4, R3).** `(:Narrator)-[:IDENTIFIED_WITH {asserted_by, confidence, evidence}]->(:Narrator)` — auto-*suggest*, **never auto-merge**; human-confirm required (theological/historical stakes). Tradition-partitioned identifier spaces stay distinct; keep `possibly_same_as` soft links so Phase 3 can run metrics under **both merge and split hypotheses**. A silent merge manufactures phantom bridges that dominate betweenness — the highest-leverage error after R1/R2.
4. **Alias / merge_history table** so re-extraction maps onto existing IDs (older cluster retains the ID); feeds the `DatasetVersion` crosswalk (`old_id→new_id`, added/removed/merged/split).

### Exit criteria (STOP-THE-LINE gate G2)
- Cheap-path coverage **measured and reported** (the real %, not 94%); resolved vs `NameMention`-remaining counts logged per tradition.
- Hard-core: a held-out, **expert-annotated** eval set exists (even small, KITAB-style); real-text F1 reported per tradition with the honest caveat ("Sunni Arabic ≈ low-80s ceiling; Shia/Zaydi/Ibadi/transliterated = unmeasured/research-grade — do NOT quote 97.8%").
- **Zero auto-merged cross-tradition identities** (assertion: every `IDENTIFIED_WITH` has `asserted_by` = a human reviewer id).
- Every resolution is a confidence-qualified edge; no `NameMention` destroyed; competing resolutions allowed (GEDCOM-X Persona/Subject).
- Temporal-feasibility data (`death_year`/`tabaqa`) populated for resolved narrators → enables Phase 3's contemporaneity pass (R4).

### Reliable vs deferred
- **Reliable:** the exact-lookup mechanism, the schema for confidence-qualified resolution, the HITL workflow.
- **Deferred / research-grade:** the ambiguous-core ML accuracy on non-Sunni and transliterated chains (explicitly unmeasured — frame as research, not a solved number).

### Risk retired
**R3** (phantom cross-tradition bridges — structurally impossible without human sign-off), the core of **C5/R2** prerequisite (resolution is the gate that makes analytics defensible).

---

## PHASE 3 — Confidence-Gated Analytics (decision-support, never authority) · Effort: S (algos) but gated by L validation · Reliability: needs-validation → conditionally production

**Purpose:** run GDS centrality/community/continuity **as decision-support only**, with confidence-projection predicates, honest accuracy caveats, and validation against rijal literature **before any UI exposure**.

### Entry criteria
- G2 passed (entity resolution done, uncertainty propagated, cross-tradition links human-reviewed).
- **D3 done:** Sunni story-form chains parsed; taḥwīl (ح) branches resolved or flagged `tahwil_unresolved=true` (excluded from continuity analytics); the measured `unknown` fraction carried as `extraction_method` per edge.
- **D6 done:** temporal/contemporaneity pass — flag `student.birth_year > teacher.death_year` → `temporal_plausibility ∈ {ok,suspect,impossible,unknown}`; `impossible` excluded from analytics by default; `unknown` is its own bucket, never silently "ok". (R4 — the cheapest high-value validation the whole field skips.)

### Scope (production-reliable GDS, used as screening only)
- **Confidence-projection predicate on every GDS projection:** `WHERE r.edge_confidence >= θ AND r.tradition = $t AND r.extraction_method <> 'story-unstructured'`. Low-confidence edges are **never deleted** — excluded by predicate so different analyses pick different θ.
- ArticleRank/Betweenness (madār/pivot — proxy for *kathrat al-riwāya*, **NOT** *ʿadāla/ḍabṭ*); Leiden (transmission schools); WCC/shortest-path (**structural** continuity FLAG, not a munqaṭiʿ verdict — tadlīs is invisible to topology).
- **Mandatory GIGO discipline (C5/R2, Contrarian's single strongest objection):** run on the high-confidence subgraph first, then full; **report every metric as a RANGE across confidence strata, never a point value**. Ablation: randomly delete +5/10/20% of edges, measure Spearman top-k stability. **If top-k is unstable under simulated loss comparable to the measured unknown fraction, publish the instability instead of the rankings.** Exclude unparsed traditions from cross-tradition centrality (format-confounded). Attach a Juynboll seeming-common-link caveat to every centrality output.

### Exit criteria (STOP-THE-LINE gate G3 — required before ANY UI exposure)
- **Rijal-literature validation:** Spearman ρ of GDS ArticleRank vs Ibn Ḥajar *Taqrīb* ṭabaqāt (Sunni) and vs Najāshī/Ṭūsī (Imami) computed and reported **per tradition**. This is the field's missing validation and the highest-value defensible experiment. A weak/negative ρ is a publishable finding and **still gates UI** (the metric is then labeled "does not proxy classical thabat for this tradition").
- Ablation stability documented; unstable top-k → rankings withheld from UI, instability published.
- Every analytic output carries: confidence stratum, tradition scope, ablation caveat, "centrality ≠ thiqa" / Juynboll caveat. **No global authenticity score exists anywhere.**
- Sign-off that framing is descriptive, tradition-scoped, citation-grounded, human-in-loop (R8 ethical gate across five living traditions).

### Reliable vs deferred
- **Reliable (conditionally):** GDS as a *screening/prioritization* layer that compresses the scholar's search space — *after* stratification + validation.
- **Deferred:** anything presented as a result without the Spearman validation + ablation; automated grading; link-prediction.

### Risk retired
**R2** (structured-missingness GIGO — contained by stratification + ablation, not eliminated), **R4** (contemporaneity), **R8** (ethical over-claiming — descriptive framing enforced at the gate).

---

## PHASE 4 — Research Frontier (optional, clearly labeled EXPERIMENTAL) · Effort: L-XL · Reliability: research-grade

**Purpose:** the genuinely novel, genuinely unvalidated contributions. Ships **only** behind an "EXPERIMENTAL — candidates for scholarly takhrīj, not established results" label, and only if Phase 3's framing discipline held.

### Entry criteria
- G3 passed.
- **Q5 ratified:** the team has demonstrated (via Phase 3) the review discipline to ship epistemically hazardous output safely. If not, Phase 4 does not ship — Negative-Space/Contrarian win.

### Scope (each strictly candidate-surfacing, never assertive)
- **Cross-tradition matn-reuse (BGE-M3 + vector index)** — the never-published Sunni/Twelver/Zaydī/Ibāḍī map. `(:Hadith)-[:MATN_PARALLEL {score}]->(:Hadith)`. Conservative thresholds (Rezwan itself flags semantic similarity as the weak link); hits are *candidates for takhrīj*, not established *ṭuruq*.
- **GDS link-prediction** — epistemically = "fabricating a ṭarīq". Frame outputs **"investigate"**, never "exists". Suspected-dropped-narrator flags only.
- **GraphRAG/HybridRAG scholar assistant** — answers grounded in retrieved chain subgraphs with mandatory rijal-`grade` provenance citations; never an authority.
- **Tradition-aware grading dashboard** — per-tradition model heads (a single global classifier on mixed-tradition `grade` is methodologically invalid); outputs structural indicators + confidence + provenance; the scholar issues the grade.

### Exit criteria (G4)
- Every artifact labeled EXPERIMENTAL with shipped methodology + limitations statement; `grade` is ground-truth/eval-target, never a model output presented as authority; no global score; per-tradition rijal authorities only (no cross-application).

### Risk retired
Converts the highest-value contributions from "GIGO/hazard if shipped as fact" to "defensible research" — only under enforced framing discipline.

---

## Phase dependency & gate summary

```
P0 (fix bug, true count, stable keys) ──G0──▶ P1 (reified schema + provenance, NO analytics)
   ──G1 (counts/dangling/constraints/confidence-dist)──▶ P2 (entity resolution + reviewed SAME_AS)
   ──G2 (resolution measured, zero auto-merge)──▶ P3 (confidence-gated GDS, rijal-Spearman validation)
   ──G3 (validated, ablation-stable, descriptive)──▶ P4 (EXPERIMENTAL frontier, optional)
```

Each `Gn` is STOP-THE-LINE: fail → line stops, no downstream phase, failed gate published as a finding. The dataset is a sound finding aid from P1; it becomes a sound analytical engine only at G3. The convergence on *schema* (C1–C8) is engine-agnostic and robust; the convergence on *building analytics now* does not exist — it is gated, on the evidence, by G2 and G3.
