# Stage 5 — Adjacent-domain techniques that could transfer

(Persisted from S5's inline reply on 2026-06-12 — agent's Write tool was denied in its context. Verbatim below.)

## Citation extraction (GROBID/ParsCit) — transfer potential

**Tool:** GROBID (GeneRation Of BIbliographic Data), a CRF/deep-learning pipeline for structured extraction from scholarly PDFs.

**Native performance:** GROBID achieves F1 ~0.93–0.96 on header-field extraction and ~0.87–0.92 on reference-string parsing across English/European academic corpora (Tkaczyk et al. 2018 evaluation; knowledge-based estimate for the neural CRF variant).

**Transfer to isnad:** Superficially appealing — both tasks decompose a linear string into typed spans (author, title, year ↔ narrator, kunyah, death-date). The analogy breaks at the ح-branch point. GROBID assumes one citation per input unit; a compound hadith with ح has two transmission chains sharing a post-convergence tail, encoded in a single sentence with no typographic delimiter other than the letter ح mid-string. The model would need to learn that ح triggers a fork and that the post-ح segment is shared by both branches, not a second standalone citation. There is no analogue of that structure in bibliography extraction. Transfer potential: **low** for branching isnads; reasonable for single-chain isnads if retrained on Arabic.

## Phylogenetic tree inference — transfer potential

**Tool:** RAxML-NG (or MrBayes for Bayesian inference), the standard maximum-likelihood/Bayesian tree reconstructors used in stemmatics and manuscript studies.

**Native performance:** On simulated nucleotide alignments RAxML-NG recovers the correct tree topology in >95% of cases at moderate branch-length variance; on manuscript stemmatics (OpenStemmata corpus) ~0.80–0.85 Robinson-Foulds accuracy (knowledge-based estimate).

**Transfer to isnad:** The hadith isnad is a phylogenetic problem in spirit — common links, bundle formation, and shared transmission tails are exactly what stemmatics models. Harald Motzki and Juynboll applied this reasoning manually. However, phylogenetic tools require a pre-computed character matrix (aligned variant readings across witnesses). Building that matrix presupposes reliably extracted isnads. Phylogenetics is therefore a downstream consumer of isnad extraction, not a substitute for it. Transfer potential: **none** for the extraction step itself; **high** for post-extraction comparative analysis.

## Multiple sequence alignment (MAFFT/MUSCLE) — transfer potential

**Tool:** MAFFT v7, a progressive/iterative MSA tool that handles large sets of divergent sequences via FFT-based homology detection.

**Native performance:** On BAliBASE benchmark protein alignments MAFFT achieves sum-of-pairs scores of ~0.85–0.92 (knowledge-based estimate); degrades gracefully on highly divergent sequences rather than silently failing.

**Transfer to isnad:** The idea: align variant isnad strings across multiple hadith witnesses to locate the shared post-ح suffix automatically — using MSA to detect the convergence point. This is more direct than the phylogenetics approach because it operates on raw text. The obstacle is that Arabic names are morphologically rich and standard MSA algorithms use character-level edit distance, not semantic identity. Two orthographic variants of the same narrator (أبو هريرة vs أبي هريرة) produce misalignments. A name-normalisation layer must precede alignment. With that pre-processing, MAFFT-style alignment could reliably locate the shared tail in ح-branching texts. Transfer potential: **moderate** — a viable heuristic for convergence-point detection, not a complete extraction pipeline.

## Other approaches found

**Dependency parsing (CAMeL Tools / FARASA):** Arabic dependency parsers label syntactic head-dependent relations. A single-chain isnad is a ʿan-chain (X عن Y عن Z) that dependency parsing handles well. ح-branches produce mid-sentence coordination structures that parsers may misattach. Recall on single chains: high (~0.88 F1 on newswire Arabic, knowledge-based estimate); recall on branched isnads: untested and likely lower.

**Exhaustive FST with explicit ح rules:** Hand-crafted finite-state transducers (OpenFST) with production rules for every known branch topology. Not an adjacent domain, but achieves high precision; recall is bounded by how exhaustively branch patterns are enumerated at grammar-authoring time.

## Verdict: would any of these GUARANTEE coverage?

No. None provides guaranteed coverage for ح-branching isnads:

- **GROBID/ParsCit** — designed for unbranched linear structures; requires fundamental architectural change to handle shared-suffix branches.
- **Phylogenetics** — downstream of extraction, not a solution to it.
- **MAFFT-style MSA** — transfers a useful heuristic (locating the convergence point), not a guarantee; depends on upstream name normalisation.
- **Dependency parsing** — adequate for single chains; unproven on ح-branches.

The guaranteed-coverage bar requires exhaustive enumeration of all branch topologies (a grammar problem, Stage 3) combined with robust name normalisation. No off-the-shelf adjacent-domain tool eliminates that requirement. The most actionable transfer is MSA-style alignment to automatically locate the shared post-convergence suffix once candidate branch points (ح tokens) have been flagged, reducing annotation burden without promising completeness.
