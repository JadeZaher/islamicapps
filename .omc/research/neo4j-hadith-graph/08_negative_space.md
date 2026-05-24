# Negative Space: What Hadith Isnad-Graph / Neo4j Projects Systematically Omit or Get Wrong

**Persona:** Negative-Space (the gaps and silent failures)
**Research question:** Regenerating a multi-tradition isnad dataset (Sunni / Imami / Zaydi / Ibadi / Rida; 69,368 rows; regex-extracted sanad with ~12% unknown attribution; unstructured Sunni story-form chains; `sanad_confidence` flag) into a Neo4j graph.
**Date:** 2026-05-16

> Framing note: This memo deliberately catalogues *only* the failure modes, omissions, and silent corruptions. It is not a balanced assessment — the other personas cover what works. Every gap below is paired with a concrete mitigation that fits a 69k-row, multi-tradition, best-effort-extraction reality.

---

## 0. The meta-gap: the literature itself omits the multi-tradition problem

Almost every published computational isnad project is **single-collection and single-tradition** — overwhelmingly Sunni, usually *Sahih al-Bukhari* or *Sahih Muslim* alone:

- The MIS / Multi-IsnadSet dataset is **Sahih Muslim only** (2,092 narrator nodes, 77,797 edges) ([ScienceDirect S2352340924004086](https://www.sciencedirect.com/science/article/pii/S2352340924004086); [PMC11096860](https://pmc.ncbi.nlm.nih.gov/articles/PMC11096860/)).
- "Social Network Analysis of Hadith Narrators" is **Sahih Muslim** with a Bukhari comparison ([ScienceDirect S1319157821000215](https://www.sciencedirect.com/science/article/pii/S1319157821000215)).
- "Social Network Analysis of Hadith Narrators from Sahih Bukhari" is **Bukhari only** ([IEEE 9348299](https://ieeexplore.ieee.org/document/9348299/); [arXiv 2102.02009](https://ui.adsabs.harvard.edu/abs/2021arXiv210202009A/abstract)).
- Rolf van Bruggen's well-known Neo4j hadith demo is a **single Sunni canonical-collection** toy graph ([blog.bruggen.com](https://blog.bruggen.com/2022/06/graphs-are-everywhere-also-in-religious.html); [GitHub gist](https://gist.github.com/rvanbruggen/a6e2e80a6fa7a253f46de9fbe9ce361f)).

**The silent failure:** there is essentially **no published methodology** for a *cross-tradition* isnad graph. Imami/Zaydi/Ibadi/Rida material, and the Sunni–Shia evaluative split, are the dataset's defining feature and exactly the part the prior art does not address. Any methodology copied from these papers will inherit a mono-tradition data model that structurally cannot represent this dataset's core reality. **Mitigation:** treat the multi-tradition design as net-new engineering, not a port; do not assume any published schema is fit for purpose; validate every modeling choice against at least one non-Sunni tradition before generalizing.

---

## (a) The unified-narrator fallacy — one node, many evaluations

### The gap
The standard pipeline "normalize the Sanad and assign a **unique identifier to each narrator**" ([PMC11096860](https://pmc.ncbi.nlm.nih.gov/articles/PMC11096860/)) collapses a person into a single node and then attaches *one* reliability value. For a multi-tradition corpus this is the single most destructive error, because **tradition-specific ta'dil/tajrih is the entire point of rijal science**, not a metadata attribute:

- "Sunni and Shia hadith collections differ because scholars from the two traditions have different opinions as to the reliability of the narrators... Narrators who took the side of Abu Bakr and Umar rather than Ali are seen as unreliable by the Shia. Sunni scholars put trust in narrators such as Aisha, whom Shia reject." ([WebSearch synthesis citing the MIS corpus literature and Wikipedia *Biographical evaluation*](https://en.wikipedia.org/wiki/Biographical_evaluation)).
- The grading **vocabularies are not even commensurable**: Sunni rijal uses a graded ladder (Thiqah Thabt, Saduq, Maqbul, Layyin, Da'if, Matruk, Mastur, La Yu'raf...), while classical Imami rijal works largely operate on Thiqah vs. Majhul with **no written biography and no jarh/ta'dil statement for thousands of narrators** ([TwelverShia.net](https://www.twelvershia.net/2014/02/14/accuracy-in-judging-a-narrators-reliability-sunnah-vs-shia/); [ShiaChat "Grading Hadiths"](https://www.shiachat.com/forum/blogs/entry/66-grading-hadiths-an-introduction/)).
- Even *within* Imami rijal the verdicts split (al-Najashi vs. Ibn al-Ghada'iri vs. al-Tusi vs. al-Kashshi; al-Hilli vs. al-Khu'i), and ~75% of *Rijal al-Tusi*'s tawthiqat concern authors/compilers, not chain transmitters ([Mahajjah, al-Hilli vs. al-Khu'i](https://mahajjah.com/a-presentation-and-critique-of-hadith-transmitter-criticism-al-jarh-wa-al-tadil-according-to-the-shia/); [Al-Islam.org Ilm al-Rijal](https://al-islam.org/ask/topics/7693/questions-about-Ilm-al-Rijal)).

A "unified narrator" node with a single `reliability` property silently **picks a winner** — usually whichever tradition's rijal corpus was scraped first — and **erases the disagreement that is the scholarly content**. Zaydi and Ibadi evaluative traditions, which barely appear in any digital rijal source, are silently flattened into the Sunni judgment by default.

A second, opposite failure: **one historical name, many actual people** (the disambiguation problem). "Sufyan" = Sufyan al-Thawri (d. 161) *or* Sufyan ibn 'Uyaynah (d. 198); chains usually give first names only ([WebSearch synthesis; cf. Studio Arabiya *Ilm al-Rijal*](https://studioarabiya.com/ilm-al-rijal-in-hadith/)). Regex extraction with ~12% unknown attribution will both **over-merge** distinct people into one node and **fail to merge** kunya/nasab variants of one person — corrupting degree, betweenness and community structure simultaneously.

### Mitigation
- **Never store a scalar `reliability` on a Narrator node.** Model evaluation as a reified edge/node: `(:Narrator)-[:EVALUATED_BY]->(:Verdict {grade, source_authority, source_work, tradition, edition, page})`. One narrator can carry N contradictory verdicts; queries must specify a tradition lens.
- Make **tradition a query-time projection**, not a node merge: maintain `:Narrator` identity nodes but resolve reliability through a tradition-scoped subgraph (Imami / Zaydi / Ibadi / Sunni / Rida views).
- Tag every node with an **identity-confidence** score distinct from `sanad_confidence`; expose ambiguous identities (`possibly_same_as`) as soft links, not hard merges, so analysts can run metrics under both merge and split hypotheses.
- For traditions with **no surviving rijal verdict** (much of Zaydi/Ibadi/Rida), store an explicit `verdict = NULL, reason = "no_extant_evaluation_in_tradition"` rather than inheriting a Sunni grade. Absence must be representable.

---

## (b) Extraction error propagating into graph analytics — quantified GIGO

### The gap
PageRank, betweenness, and community detection are run on the graph as if it were ground truth. With **~12% unknown attribution** and Sunni story-form chains left **unstructured**, the graph is missing a large, *non-random* fraction of its edges — and the algorithms do not announce this; they return confident numbers.

Evidence the degradation is severe and quantifiable:

- The criminal-network GIGO study (arXiv:2501.01508 / EPJ Data Science 2025) finds that **"missing data renders most node-ranking methods ineffective"** and that effectiveness "remains weak even with relatively low percentages of missing data" — accurate ranking requires *near-complete* network knowledge ([arXiv 2501.01508](https://arxiv.org/abs/2501.01508); [EPJ Data Science](https://epjdatascience.springeropen.com/articles/10.1140/epjds/s13688-025-00553-x); [arXiv PDF](https://arxiv.org/pdf/2501.01508)).
- General community-detection evaluation work warns insights become "biased" on incomplete real-world networks where communities "are not defined objectively" ([Nature Sci. Reports srep30750](https://www.nature.com/articles/srep30750)).
- PageRank "assumes a single node type"; mixing node types yields meaningless comparisons ([WebSearch synthesis; cf. Cambridge Intelligence on PageRank/EigenCentrality](https://cambridge-intelligence.com/eigencentrality-pagerank/)).

The error here is **structurally biased, not random noise**:
1. The 12% unknown attributions are concentrated in *weak/late/obscure* transmitters — exactly the periphery — so dropping them **inflates the apparent centrality of the famous common links** (al-Zuhri, Nafi', the Imams) and manufactures artificially tight communities.
2. Unstructured Sunni story-form chains contribute **zero or malformed edges**, so any cross-tradition comparison ("Sunni narrators are less central") is an **artifact of extraction format**, not history.
3. Even the best reported extractor (GTAF) is **~95% accuracy on a 20-hadith hand-picked test of one collection**, *Muwatta Malik* ([gtaf.org evaluation blog](https://gtaf.org/blog/evaluating-the-performance-of-our-narrator-chain-extraction-system-for-hadith-analysis/)). A regex extractor at scale on five traditions will be far below this, and the errors correlate with chain style — so the noise is not i.i.d. and cannot be averaged away.
4. This collides with the **Juynboll common-link problem**: a "seeming" common link can be an artifact of *fabricated or under-sampled* isnads ([Wikipedia *Isnad-cum-matn analysis*](https://en.wikipedia.org/wiki/Isnad-cum-matn_analysis); [academia.edu, Common Link & Hadith Terminology](https://www.academia.edu/43937917/The_Common_Link_and_its_Relation_to_Hadith_Terminology)). Graph centrality cannot distinguish a historically real common link from one produced by missing edges.

**Net GIGO risk:** centrality rankings and community partitions on this graph will be *confidently wrong*, with errors pointing systematically toward over-stating canonical Sunni narrators and under-representing Shia/Zaydi/Ibadi structure.

### Mitigation
- **Gate analytics on `sanad_confidence`.** Run PageRank/Louvain on the high-confidence subgraph first; then re-run on the full graph; **report metrics as ranges across confidence strata**, never single point values.
- **Sensitivity / ablation analysis:** randomly delete an additional 5/10/20% of edges and measure rank-correlation (Spearman) of top-k centrality. If top-k is unstable under simulated loss comparable to the known 12%, **publish that instability instead of the rankings**.
- **Exclude unstructured Sunni story-chains from any cross-tradition centrality comparison**, or flag results as format-confounded; never compare a regex-parsed tradition against an unparsed one.
- Carry an edge property `extraction_method` (regex / story-unstructured / manual) and let every analytical query filter on it; treat structurally-missing-by-format edges as *missing*, not *absent*.
- Where centrality is reported, attach a Juynboll-style caveat: high centrality may indicate a *sampling/seeming* common link, not historical importance.

---

## (c) Provenance & grade-attribution loss — and a copyright trap

### The gap
A node or hadith carrying a bare `grade = "sahih"` is **scholarly meaningless**: a grade is a *verdict by a specific grader, in a specific work, in a specific edition*. The digital-text literature documents that this loss is the norm:

- "Digital editions and e-books tend to **omit the critical apparatus**... in many digitally searchable forms of Arabic/Persian material there is the **complete removal of the critical apparatus**... and with it any semblance of this polyphonic reception history." ([KITAB, *Studying Hadith Commentaries in the Digital Age* / Roger Pearse on critical apparatus](https://www.roger-pearse.com/weblog/2025/09/02/how-do-we-represent-the-critical-apparatus-when-we-make-our-critical-edition/); [OpenITI](https://maximromanov.github.io/OpenITI/)).
- A grade with no `grader` is uninterpretable across traditions: al-Albani's "sahih" ≠ a classical "sahih" ≠ an Imami "sahih li-ghayrihi" ≠ a Zaydi/Ibadi judgment. A unified `grade` column flattens incompatible epistemologies into one string (the same fallacy as (a), at the hadith level).

**The copyright trap (rarely mentioned by graph projects):** the *only* place many hadith carry modern grades is in **20th–21st-c. critical editions and takhrij apparatus** (e.g., al-Albani's gradings, Shu'ayb al-Arna'ut's tahqiq, Dar al-Salam editions). Scraping `grade` from those into a "regenerated dataset" can **reproduce a copyrighted scholarly apparatus** — the editor's original critical labor — even though the medieval matn/isnad is public domain. OpenITI/KITAB curate provenance and metadata precisely because origin/witness of digital texts is "obscure" and must be tracked ([KITAB corpus/about](https://kitab-project.org/corpus/about); [OpenITI](https://maximromanov.github.io/OpenITI/)). A graph that ships bare grade nodes both loses scholarly meaning *and* may launder protected apparatus with no attribution.

### Mitigation
- **Forbid bare grade values.** Schema: `(:Hadith)-[:GRADED]->(:Grading {grade, grader, work, edition, year, tradition, methodology})`. A grade with no grader is rejected at ingest, or stored as `grade_unsourced = true` and excluded from all authoritative queries/UI.
- Maintain a `:Source` provenance node per grading with license status (`public_domain_classical` vs. `modern_critical_edition_restricted`). Surface the license flag in any export; **do not redistribute grades whose only source is a restricted critical edition** — store a pointer/citation, not the verdict text.
- Record the **digital text witness** (which scan/edition the regex ran over) on every hadith, mirroring OpenITI/KITAB provenance practice, so grades and chains are traceable to a witness, not "the internet".
- Display tradition + grader together in any UI ("Sahih per al-Albani, *Sahih al-Jami'*, 2nd ed.") so no algorithmic grade is ever shown unattributed.

---

## (d) Missing metadata that graph projects routinely drop

### The gap
The published isnad graphs model essentially **(narrator)-[narrates]->(narrator)** and little else. The fields needed to do *real* hadith science are exactly the ones omitted:

- **Death-year / tabaqa / birth-year** — required for any continuity (ittisal) and contemporaneity check; biographical evaluation explicitly depends on "date and place of birth, teachers and students, and date of death" ([Wikipedia *Hadith studies*](https://en.wikipedia.org/wiki/Hadith_studies); [Wikipedia *Biographical evaluation*](https://en.wikipedia.org/wiki/Biographical_evaluation)). The MIS-style schemas store narrator nodes with **no death-year/tabaqa field at all**.
- **Geography** — proximity is part of the plausibility test (could these two have met?) and is dropped from every SNA paper reviewed.
- **Multiple chains per hadith** — a single hadith routinely has several isnads; collapsing to one path destroys corroboration (mutaba'at/shawahid) analysis. MIS's own framing emphasizes "multiple ISNAD" precisely because single-path modeling is inadequate ([SSRN 4726768](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4726768)) — yet most downstream graphs still flatten it.
- **Taḥwīl (ح, the chain-switch marker)** — a single narration with `ح` encodes *parallel* sub-chains. Regex extraction over story-form Sunni text will almost always **mis-handle taḥwīl**, either merging parallel chains into a false single path or dropping a branch — silently fabricating or destroying transmission links.
- **Narration mode (samaa', ijaza, 'an'ana, munawala)** — affects strength; never modeled.

Each omission converts a *checkable historical claim* into an *unfalsifiable graph edge*.

### Mitigation
- Narrator node properties: `death_year`, `birth_year` (nullable, ranged), `tabaqa`, `locations[]`, `kunya[]`, `nasab[]`, with explicit `*_uncertain` flags.
- Model the hadith→chain relationship as **first-class multi-chain**: `(:Hadith)-[:HAS_CHAIN]->(:Chain)-[:LINK {order, mode, tahwil_branch}]->(:Narrator)`. Never collapse a hadith to one path.
- Detect and **explicitly represent taḥwīl** as a branch point; where the regex cannot resolve it, set `tahwil_unresolved = true` and exclude that chain from continuity analytics.
- Store narration `mode` per link where extractable; default `unknown` (not silently "samaa'").

---

## (e) The contemporaneity check almost nobody implements

### The gap
The most basic historical sanity test — **a student cannot narrate from a teacher who died before the student was born / before they could have met** — is **absent from every computational isnad graph reviewed**. Classical biographical evaluation does exactly this: "it is determined whether the individual was actually able to transmit the report, deduced from their **contemporaneity and geographical proximity**" ([Wikipedia *Hadith studies*](https://en.wikipedia.org/wiki/Hadith_studies)). Juynboll's whole apparatus rests on temporal plausibility of links ([Brill, *Islam at 250*, Juynboll & al-Zuhri](https://brill.com/display/book/edcoll/9789004427952/BP000007.xml); [Wikipedia *Isnad-cum-matn analysis*](https://en.wikipedia.org/wiki/Isnad-cum-matn_analysis)).

Because graph projects drop death-years (gap d), they **cannot** run this check — so they present temporally impossible edges (a regex artifact, or a genuine munqati'/mursal break) with the **same visual and analytical weight as sound ones**. PageRank then flows through links that are historically impossible. This is the single highest-leverage validation the field skips.

### Mitigation
- Once death/birth/floruit years exist (gap d), run an automated **temporal-plausibility pass**: for every `LINK(teacher→student)`, flag if `student.birth_year > teacher.death_year` or if the overlap window is implausibly short; emit `temporal_plausibility ∈ {ok, suspect, impossible, unknown}`.
- **Exclude `impossible` edges from analytics by default**; surface them as candidate extraction errors *or* candidate inqita' (broken chain) — both are findings, not noise to hide.
- Add a complementary **geographic-plausibility** flag where locations exist.
- Treat `unknown` (missing dates) as its own bucket — do not let missing-date links pass as "ok".

---

## (f) Ethical / community pitfalls of algorithmic grades across living traditions

### The gap
Presenting a computed or scraped grade as authoritative is not just a data problem — it is a **community and epistemic-authority problem**, and the AI-hadith literature is explicit about it:

- Risks include "limited explainability of AI models, and **weak integration between algorithmic reasoning and Islamic epistemology**"; no standardized benchmark datasets exist ([ACM TALLIP systematic review 10.1145/3434236](https://dl.acm.org/doi/10.1145/3434236); [al-Qanatir, *Integration of AI in Hadith Studies*](http://www.al-qanatir.com/aq/article/download/1309/923)).
- "AI tools designed for scholarly purposes could be **repurposed or manipulated to serve ideological, political, or sectarian agendas**" and "the absence of a comprehensive ethical framework risks **undermining the trust of the Muslim community**" ([al-Qanatir](https://al-qanatir.com/aq/article/view/1309); [ResearchGate 398677751](https://www.researchgate.net/publication/398677751_THE_INTEGRATION_OF_AI_IN_HADITH_STUDIES_CHALLENGES_AND_GUIDELINES)).
- Hadith meaning is "deeply contextual" — reductionism is itself the ethical failure ([ejpi.uis.edu.my PRISMA review](https://ejpi.uis.edu.my/index.php/ejpi/article/download/333/244/2363)).

For a corpus spanning **Sunni, Imami, Zaydi, Ibadi and Rida**, an algorithmic grade is implicitly a sectarian verdict: declaring a narrator "weak" using Sunni rijal de-legitimizes hadith load-bearing for Imami/Zaydi practice, and vice versa. A graph UI that shows a single colored "authenticity" badge is, to a practitioner of the disadvantaged tradition, a takfir-adjacent claim made by a script.

### Mitigation
- **Frame outputs as descriptive, never prescriptive:** "extracted chain", "this is how al-Najashi graded narrator X", *not* "this hadith is weak". The system reports *who said what*, not a verdict of its own.
- **No global authenticity score.** Any score is tradition-scoped, labeled, and shown alongside the dissenting traditions' verdicts (ties back to (a)/(c)).
- Ship an explicit **methodology + limitations statement** in the dataset and UI (extraction is best-effort regex, 12% unknown, confidence flag meaning) so no user mistakes it for tahqiq.
- Keep a human-scholar-in-the-loop disclaimer; position the graph as a *finding aid for researchers*, aligned with the literature's "augmentative tool, not substitute" consensus.
- For each tradition, prefer that tradition's own rijal authorities for that tradition's hadith; do not cross-apply.

---

## (g) Reproducibility: node-ID churn when the upstream dataset regenerates

### The gap
The dataset is **regenerated** (re-OCR, re-regex, re-dedup; the repo already shows churned/compressed/deleted data artifacts). If narrator/hadith **node IDs are derived from row order, hashes of mutable text, or auto-increment**, every regeneration **reshuffles identities**:

- Lack of data-versioning is a recognized contributor to the "**reproducibility crisis**"; reproducing a prior analysis is impossible if the underlying data changed and differences aren't tracked ([CODATA Data Science Journal, *Versioning Data*](https://datascience.codata.org/articles/10.5334/dsj-2021-012); [Zenodo 3772870, data-versioning best practices](https://zenodo.org/records/3772870)).
- Persistent identifiers must remain stable and resolvable even when the object moves/changes; URLs/auto-IDs suffer link-rot equivalents ([McGill, *Persistent Identifiers*](https://douglas.research.mcgill.ca/persistent-identifiers/); [project-thor versioning case study](https://project-thor.readme.io/docs/examples-of-versioning-with-identifiers)).
- ML/graph reproducibility specifically requires **data versioning + entity stability** among its pillars ([Wiley AI Magazine, Semmelrock et al. 2025](https://onlinelibrary.wiley.com/doi/10.1002/aaai.70002)).

**Silent failure:** a paper or downstream graph cites "narrator node 4471 has highest betweenness"; after regeneration node 4471 is a different person. Cross-version diffs, longitudinal claims, and any external citation **silently break** with no error raised. The 12% unknown-attribution rows are the *most* volatile between runs, so the churn concentrates exactly where confidence is already lowest.

### Mitigation
- **Content-stable, semantically anchored IDs:** derive narrator IDs from a normalized canonical name + disambiguating biography (death-year/tabaqa) hashed deterministically — *not* from row order or mutable raw text. Maintain an explicit `aliases`/`merge_history` table so a re-extraction maps onto existing IDs instead of minting new ones.
- **Version every regeneration** (dataset DOI/semantic version) and ship a **node-ID crosswalk** (`old_id -> new_id`, plus `added/removed/merged/split`) so prior analyses are reproducible and diffable.
- Persist a `first_seen_version` / `last_seen_version` on nodes; never silently delete (consistent with the project's own "never delete data, back up/move" memory directive) — tombstone instead.
- Pin analytics outputs to a dataset version in all reports; a centrality claim without a dataset version is non-reproducible by construction.

---

## Priority ranking of the gaps (highest GIGO / harm leverage first)

1. **(a) Unified-narrator fallacy** — corrupts the dataset's entire reason for existing (multi-tradition); fix the schema before anything else.
2. **(b) Biased extraction error into analytics** — every published centrality/community number on this graph is suspect until confidence-stratified.
3. **(e) Missing contemporaneity check** — cheapest high-value validation the whole field skips; depends on (d).
4. **(c) Provenance/grade loss + copyright** — scholarly *and* legal exposure from bare grade nodes.
5. **(d) Dropped metadata** — the enabling fix for (e) and honest analytics.
6. **(g) Node-ID churn** — quietly destroys reproducibility across the planned regenerations.
7. **(f) Ethical framing** — non-technical but trust-critical across five living traditions.

---

## Sources

- Multi-IsnadSet (MIS), Sahih Muslim — [ScienceDirect S2352340924004086](https://www.sciencedirect.com/science/article/pii/S2352340924004086) · [PMC11096860](https://pmc.ncbi.nlm.nih.gov/articles/PMC11096860/) · [SSRN 4726768](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4726768) · [DOAJ](https://doaj.org/article/43e4f48c20094f13aff04ed79e32da3c)
- Social Network Analysis of Hadith Narrators — [ScienceDirect S1319157821000215](https://www.sciencedirect.com/science/article/pii/S1319157821000215) · [IEEE 9348299 (Bukhari)](https://ieeexplore.ieee.org/document/9348299/) · [arXiv 2102.02009](https://ui.adsabs.harvard.edu/abs/2021arXiv210202009A/abstract)
- van Bruggen Neo4j hadith graph — [blog.bruggen.com](https://blog.bruggen.com/2022/06/graphs-are-everywhere-also-in-religious.html) · [GitHub gist](https://gist.github.com/rvanbruggen/a6e2e80a6fa7a253f46de9fbe9ce361f)
- Sunni vs. Shia narrator grading — [TwelverShia.net](https://www.twelvershia.net/2014/02/14/accuracy-in-judging-a-narrators-reliability-sunnah-vs-shia/) · [ShiaChat Grading Hadiths](https://www.shiachat.com/forum/blogs/entry/66-grading-hadiths-an-introduction/) · [Mahajjah al-Hilli vs al-Khu'i](https://mahajjah.com/a-presentation-and-critique-of-hadith-transmitter-criticism-al-jarh-wa-al-tadil-according-to-the-shia/) · [Al-Islam.org Ilm al-Rijal](https://al-islam.org/ask/topics/7693/questions-about-Ilm-al-Rijal) · [Wikipedia Biographical evaluation](https://en.wikipedia.org/wiki/Biographical_evaluation)
- Disambiguation / ilm al-rijal — [Studio Arabiya Ilm al-Rijal](https://studioarabiya.com/ilm-al-rijal-in-hadith/) · [Studio Arabiya Ilm al-Isnad](https://studioarabiya.com/ilm-al-isnad-in-hadith/)
- GIGO / data-quality in network analysis — [arXiv 2501.01508](https://arxiv.org/abs/2501.01508) · [EPJ Data Science](https://epjdatascience.springeropen.com/articles/10.1140/epjds/s13688-025-00553-x) · [arXiv PDF](https://arxiv.org/pdf/2501.01508) · [Nature Sci. Reports srep30750](https://www.nature.com/articles/srep30750) · [Cambridge Intelligence PageRank/EigenCentrality](https://cambridge-intelligence.com/eigencentrality-pagerank/)
- Extractor accuracy — [GTAF narrator-chain evaluation](https://gtaf.org/blog/evaluating-the-performance-of-our-narrator-chain-extraction-system-for-hadith-analysis/) · [GTAF NER+LLM](https://gtaf.org/blog/extracting-knowledge-from-hadith-using-named-entity-recognition-and-llms)
- Common link / contemporaneity — [Wikipedia Isnad-cum-matn analysis](https://en.wikipedia.org/wiki/Isnad-cum-matn_analysis) · [Wikipedia Hadith studies](https://en.wikipedia.org/wiki/Hadith_studies) · [academia.edu Common Link & Terminology](https://www.academia.edu/43937917/The_Common_Link_and_its_Relation_to_Hadith_Terminology) · [Brill Islam at 250 (Juynboll/al-Zuhri)](https://brill.com/display/book/edcoll/9789004427952/BP000007.xml)
- Critical-edition apparatus / provenance / copyright — [KITAB corpus/about](https://kitab-project.org/corpus/about) · [OpenITI](https://maximromanov.github.io/OpenITI/) · [Roger Pearse on critical apparatus](https://www.roger-pearse.com/weblog/2025/09/02/how-do-we-represent-the-critical-apparatus-when-we-make-our-critical-edition/) · [KITAB Studying Hadith Commentaries](https://www.academia.edu/103291544/Studying_Hadith_Commentaries_in_the_Digital_Age)
- AI-hadith ethics — [ACM TALLIP 10.1145/3434236](https://dl.acm.org/doi/10.1145/3434236) · [al-Qanatir Integration of AI](https://al-qanatir.com/aq/article/view/1309) · [al-Qanatir PDF](http://www.al-qanatir.com/aq/article/download/1309/923) · [ResearchGate 398677751](https://www.researchgate.net/publication/398677751_THE_INTEGRATION_OF_AI_IN_HADITH_STUDIES_CHALLENGES_AND_GUIDELINES) · [ejpi PRISMA review](https://ejpi.uis.edu.my/index.php/ejpi/article/download/333/244/2363)
- Reproducibility / versioning / persistent IDs — [CODATA Versioning Data](https://datascience.codata.org/articles/10.5334/dsj-2021-012) · [Zenodo 3772870](https://zenodo.org/records/3772870) · [McGill Persistent Identifiers](https://douglas.research.mcgill.ca/persistent-identifiers/) · [project-thor versioning](https://project-thor.readme.io/docs/examples-of-versioning-with-identifiers) · [Wiley AI Magazine Semmelrock 2025](https://onlinelibrary.wiley.com/doi/10.1002/aaai.70002)
- Narrator databases referenced — [muslimscholars.info](https://www.muslimscholars.info/) · [isnad.io](https://isnad.io/) · [muhaddithat/isnad-datasets (GitHub)](https://github.com/muhaddithat/isnad-datasets)
