# Crucible Agent 2 — Evidence Quality & Feasibility Audit

**Scope:** Audit of the 8 persona reports against (1) sourcing rigor, (2) the
*actual* repo, (3) feasibility for THIS dataset's quality, (4) honest MVP vs
full vision. Skeptical and concrete. Repo files were read directly; figures
re-counted from disk where possible.

---

## 0. Headline verdicts (read this first)

1. **This is BROWNFIELD, not greenfield.** Every concrete repo claim the
   Systems persona made checks out: `src/lib/db/neo4j-helpers.ts`,
   `neo4j.ts`, `schema.ts`, `datasets/narrator-data/all_rawis.csv`
   (**24,326 data rows**, `scholar_indx` + teachers/students — exact), the
   `_sunni_key` id-churn comment (`regen_unified_csvs.py:77-84`, verbatim),
   `sunni_isnad.jsonl` (34,440 rows), per-collection `PROVENANCE.json`, the
   batched-UNWIND TS importers, `link-sanad-chains.ts`. A Neo4j layer already
   exists and runs.
2. **The Systems persona UNDERSTATED the id-churn flaw.** It says
   `neo4j-helpers.ts` "already encodes the right conventions" and the build
   merely needs to "generalize" them. **False in practice:** the live
   production importer `src/scripts/import-datasets.ts:370-389` does
   `MERGE (n:Narrator {id: $id})` where `id = uuidv4()` minted fresh per run
   (line 311). It does **not** call the helpers. Re-running the importer
   **duplicates every narrator node**. The helpers are *aspirational
   scaffolding*, not the wired path. "Regen for Neo4j" is brownfield with a
   **broken idempotency story that must be fixed first**, not inherited.
3. **The row count cited by ALL EIGHT personas (69,368) is wrong /
   stale.** `all_hadiths_unified.csv` on disk = **78,951 data rows**
   (78,952 lines incl. header). Every persona inherited "69,368" from the
   prompt; none re-counted. Not fatal to any schema argument, but it means
   no persona validated the single most basic dataset fact, and the
   Systems validation harness's "expected ≈ 69,368" gate would **fail on
   the real file**.
4. **The disambiguation literature numbers are search-digest, not
   verified-primary**, and three personas said so honestly. The schema
   recommendations (reify the chain; identity ≠ assessment; tradition-
   partitioned grades) are **well-corroborated and low-risk**; the
   *accuracy promises* (97.8% / 94.6%) are **not** safe to quote for this
   dataset.

---

## 1. EVIDENCE QUALITY — confidence ratings of load-bearing claims

WebFetch was permission-denied for at least the Archaeological persona
(explicit methodology note, line 7) and the abstract-only character of the
Historical/Futurist/Analogical numeric claims indicates the same constraint.
Ratings: **verified-primary** (repo or primary doc), **search-digest**
(publisher abstract / search snippet, plausible but unconfirmed),
**speculative** (inference beyond the snippet).

| Claim | Personas | Rating | Note |
|---|---|---|---|
| AR-Sanad 280K-v2 per-narrator schema (appearance forms, shuhra, Ibn-Hajar rank, narrated-from/to) | Hist, Arch, Fut | **search-digest** | Consistent across 3 personas + GitHub `somaia02/Narrator-Disambiguation` cited; schema shape credible, exact fields unconfirmed from PDF |
| **97.8% accuracy (Mosa 2025, KG+Transformer, AR-Sanad 280K-v2)** | Hist, Arch, Fut | **search-digest** | Abstract-only. Arch persona explicitly flags it is on a *synthetic-leaning v2 benchmark dominated by the easy 94%*. Do NOT quote as an expected number. |
| **94.6% (Mahmoud 2024 AraBERT re-rank)** | Arch, Fut | **search-digest** | Same caveat; Springer DOI cited but abstract-only |
| **92.9 F1 synthetic → 83.5 F1 real six-books (SER 30→60)** | Arch | **search-digest** | This is the *honest* number and the one to plan against; still abstract-derived, not PDF-verified |
| **94% exact-lookup / 3,477-of-61,598 ambiguous-core** | Arch | **search-digest** | The 3,477/61,598 ratio is a specific snippet figure; *directionally* trustworthy (the asymmetry is real in onomastics) but the exact integers are unverified and Sunni-only |
| MIS = 2,092 nodes / 77,797 edges, Sahih Muslim | Hist, Anal, Fut, NS | **search-digest** (cross-corroborated) | Stated identically by 4 personas citing PMC11096860 + ScienceDirect; high inter-source agreement → treat as reliable-secondary |
| SemanticHadith chose RDF/OWL for LOD interop | Contr, Hist | **search-digest** | Consistent, plausible, central to the contrarian case; unverified from primary |
| KITAB 1,070 names → 63 forms → 25 individuals | Hist | **search-digest** | Single-snippet; illustrative not load-bearing |
| Rezwan 1.39M narrations, isnad/matn split 9.33/10 | Hist, Fut | **search-digest** | Single arXiv abstract; the "9.33/10" is a snippet figure — speculative as a quality guarantee |
| Reify chain / `Authority` / `Assessment`; identity ≠ assessment; tradition-scoped grade | Anal, Jour, Arch, NS | **verified-primary (design) + search-digest (precedent)** | The *design pattern* is corroborated by PROV/OpenAlex/GEDCOM-X primary specs AND by the repo's own `classify_attribution.py` person+level design — this is the strongest, safest finding |
| Repo: helpers/schema/all_rawis/id-churn/importers exist | Sys, Jour | **verified-primary** | Read directly. See §2. |
| 69,368 row count | ALL EIGHT | **WRONG** | Disk = 78,951. Nobody re-counted. |
| ~12% unknown attribution | Contr, NS, Fut (premise) | **unverified** | Inherited from prompt; `classify_attribution.py` has an `unknown` bucket and a `--stats` mode, but no persona ran it and the audit could not (no shell). Plausible by design (conservative classifier) but **unconfirmed**. |

**Bottom line on evidence:** the *schema/architecture* recommendations rest on
primary specs + the repo itself = trustworthy. Every *accuracy percentage* is
search-digest from abstracts, all Sunni-Arabic-synthetic, **none tested on
Shia/Zaydi/Ibadi or transliterated chains** (Arch and Fut both state this
plainly — credit to them). Treat 83.5 F1 (real, Sunni) as the optimistic
ceiling; cross-tradition is **unmeasured = research-grade**.

---

## 2. REPO REALITY-CHECK (the greenfield-vs-brownfield determinant)

Verified by direct read:

| Systems-persona claim | Reality | Status |
|---|---|---|
| `src/lib/db/neo4j-helpers.ts` (`mergeNodeByKey`, `mergeEdge`, `buildPipelineKey`) | Exists, 201 lines, exactly those exports + `_merge_sentinel` pattern | **TRUE** |
| `src/lib/db/neo4j.ts` `runWrite`=`executeWrite` retry-safe | Exists, confirmed `session.executeWrite` | **TRUE** |
| `schema.ts` constraints on `Narrator.id`, `Narrator.scholar_indx`, `Hadith.id`, `Chain.id`, `Hadith.dataset_row_id` idx | Exists; `Narrator.id` + `Narrator.scholar_indx` BOTH uniqueness-constrained; `Chain` constrained; `dataset_row_id` is an index | **TRUE** |
| `all_rawis.csv` 24,326 rows, `scholar_indx`, teachers/students | **24,326 data rows** exactly; columns include `scholar_indx`, `teachers`, `students`, `teachers_inds`, `students_inds` (id-bearing) | **TRUE (exact)** |
| `regen_unified_csvs.py` master `id` reassigned every rebuild; `_sunni_key="{source}|{hadith_no}"` | Verbatim in lines 77-84 incl. the docstring rationale | **TRUE (exact)** |
| `sunni_isnad.jsonl` per-hadith `sanad`/`sanad_confidence`, confidence per-hadith | 34,440 rows; `sanad_confidence` ∈ {0,2,...} per-hadith; noisy token `"ه سمع علقمة بن وقاص الليثي"` present exactly as Journalistic quoted | **TRUE (exact)** |
| Per-collection `PROVENANCE.json` | Exists for zaydi/ibadi/rida | **TRUE** |
| Batched-UNWIND TS importers (`import-*.ts`) | 6 importers exist (classical, shia, zaydi, musnad, pure-canon, datasets) | **TRUE** |
| `link-sanad-chains.ts` fuzzy name→Narrator, batched MERGE | Exists; `Hadith→MatnVariation→Chain→Narrator` + `HEARD_FROM`; fuzzy normalizeAr | **TRUE** |
| **"helpers already encode the right conventions" — implying the wired path is sound** | **FALSE.** Live `import-datasets.ts:370-389` does `MERGE (n:Narrator {id:$id})`, `id=uuidv4()` per run; `scholar_indx` only `ON CREATE`; does not import the helpers. Re-run = full narrator duplication. | **MISLEADING** |
| `classify_attribution.py` produces `narration_level`+`attributed_to` (person+level) | Exact: docstring states the "person + level" design; enums match Journalistic §0 verbatim | **TRUE (exact)** |

**Determination:** BROWNFIELD. The data layer and a Neo4j layer exist and the
*authority vocabulary the whole disambiguation plan depends on*
(`scholar_indx`, 24,326 curated narrators with teacher/student id-lists)
**already exists and is already partially wired**. This is a large positive
the Contrarian persona did not credit. **However**, the production importer's
UUID-per-run MERGE means the *current* graph build is non-idempotent and
node-id-churning — the Negative-Space (g) and Systems §3 concerns are not
hypothetical, they are the **current live bug**. First deliverable must be
"make the existing importer idempotent on `scholar_indx`/`_sunni_key`,"
not a new schema.

---

## 3. FEASIBILITY (effort S/M/L/XL × reliability) for THIS data

Data reality: ~78.9k rows, best-effort regex Sunni isnad (heuristic, ḥ/taḥwīl
"takes first chain"), `unknown` attribution bucket (proportion unverified),
24,326-narrator Sunni-leaning authority list, no Shia/Zaydi/Ibadi rijal
vocabulary on disk.

| Capability | Effort | Reliability on THIS data | Verdict |
|---|---|---|---|
| Reified `Chain`/`Isnad` + `Authority` + `Assessment` schema (Anal/Jour/Arch) | **M** | **production** | Pure modeling; corroborated by primary specs + repo's own person+level design. Do this. Honest regardless of extraction noise (structure ≠ accuracy claim). |
| Idempotent re-load (stable `_sunni_key`/`RAWI:scholar_indx` keys, fix the UUID-MERGE) | **S–M** | **production** | Small, mechanical, highest ROI. Prerequisite for everything. |
| ~94% exact-lookup entity resolution (cheap path) | **M** | **needs-validation** | The 94% is AR-Sanad Sunni-synthetic; on `all_rawis` + raw sanad strings expect lower. Exact-match on `scholar_indx` aliases is sound *as a mechanism*; the *coverage %* is unproven here. Build it; do NOT promise 94%. |
| Retrieve-rerank (AraBERT/embeddings) for the ambiguous core | **L–XL** | **research-grade** | Real-text Sunni ceiling ≈ 83 F1 (search-digest); Shia/Zaydi/Ibadi + transliterated = **unmeasured**. Needs Arabic-BERT infra, training pairs, HITL. Not a first deliverable. |
| GDS ArticleRank / Betweenness (madār/pivot) | **S** | **needs-validation** | Algorithm is production; *interpretation* is corrupted by non-random missingness (NS-b, Contrarian-c). Reliable only if confidence-stratified + ablation-tested + framed as "centrality≠thiqa" (Futurist's gate). |
| GDS Leiden (transmission schools) | **S** | **needs-validation** | Same caveat; defensible as exploratory, not as a result, until stratified |
| WCC / shortest-path continuity flagging | **S** | **production (as a FLAG)** | Reliable to *flag* structurally broken chains; NOT a munqaṭiʿ verdict (tadlīs invisible to topology — Futurist) |
| Cross-tradition matn-reuse (BGE-M3 + vector index) | **L** | **research-grade** | Genuinely novel, genuinely unvalidated; Rezwan itself flags semantic similarity as the weak link. Candidate-surfacing only. |
| GDS link-prediction (missing transmissions) | **M** | **do-not-ship-as-fact** | Epistemically = "fabricating a ṭarīq" (Futurist). Investigate-only or skip. |
| Cross-tradition unified narrator node | n/a | **category error** | Contrarian-e / NS-a / Arch-d unanimous: tradition-partitioned identity + curated `SAME_AS`, never a merge. This is a *constraint*, not a feature. |

---

## 4. MINIMUM VIABLE (honest, not GIGO) vs FULL VISION

**Minimum Viable First Deliverable (honest, shippable, ~S–M):**

1. **Fix idempotency on the existing pipeline.** Make `import-datasets.ts`
   (and siblings) MERGE narrators on `RAWI:scholar_indx` (and `EXT:uuid5`
   fallback) and hadith on `{source}|{hadith_no}` via the *existing*
   `neo4j-helpers.ts`. Re-runs must be no-ops. (Closes the live bug;
   Systems §3 / NS-g.)
2. **Reify the chain + Authority + Assessment** per the Analogical/
   Journalistic/Archaeological consensus (the one place all schema-focused
   personas agree and it's backed by primary specs + the repo's own
   `classify_attribution.py`). Keep the fast `NARRATED_FROM` shortcut.
3. **Tradition-partitioned grades; never a bare `grade` or unified
   reliability scalar.** `Assessment{grade,grade_source,grade_scheme}`.
   Absence representable (`no_extant_evaluation`).
4. **Carry provenance + `sanad_confidence` + `extraction_method` on every
   edge; no analytic ships without confidence-stratification + an ablation
   number.** Descriptive framing only ("extracted chain", "X graded by Y"),
   no global authenticity score.
5. **Re-count and pin the real row total (≈78.9k), write a dataset-version
   sidecar + in-graph `DatasetVersion`.** Stop citing 69,368.

This is honest because it is structure + provenance + idempotency — none of
it asserts disambiguation accuracy or historical centrality it cannot back.

**Explicitly OUT of the MVP (full vision, research-grade):** retrieve-rerank
disambiguation, cross-tradition matn-reuse, GDS centrality *as results*,
link-prediction, GraphRAG, tradition-aware automated grading. These are
defensible *research* contributions (Futurist is right that the cross-
tradition map is novel) but every one is unvalidated on this data and
several are GIGO or epistemically dangerous if shipped as fact.

**Cross-cutting honesty requirement (Contrarian + Negative-Space, correct):**
GIGO here is *structured, root-concentrated* missingness, not random — so
centrality/community numbers are "confidently wrong" until stratified by
`sanad_confidence` and ablation-tested. The graph is a sound *navigational/
representational* artifact today; it is **not** a sound *analytical engine*
until the disambiguation + Sunni-story-chain-parsing + uncertainty-
propagation work is done. Build the MVP as a finding aid, defer the
analytics claims.
