# Arabic Hadith Pipeline Enhancement Research Report

**Date**: 2026-05-08
**Method**: Asymmetric Research Squad (8 parallel research agents)
**Scope**: OCR, parsing, QA, embeddings, standards, and pipeline architecture

---

## Executive Summary

The most impactful finding is that **clean, typed Arabic text already exists for both Zaydi and Ibadi collections** in the OpenITI corpus, sourced from community-proofread Shamela libraries. This eliminates the need for OCR entirely for these texts. Beyond this, the research identified a clear upgrade path across every pipeline stage.

### Top 5 Actionable Findings

1. **Skip OCR** -- Use OpenITI mARkdown files from `github.com/OpenITI/RELEASE` instead
2. **If OCR is ever needed** -- Replace easyocr (CER 0.20) with QARI-OCR v0.2 (CER 0.061) or Kraken (the DH gold standard used by OpenITI/KITAB)
3. **Grade labels must be tradition-specific** -- A bare "sahih" on a Zaydi hadith is a category error
4. **BGE-M3 + VectorChord** for embedding/search -- drop-in pgvector replacement, 100x faster
5. **DVC for dataset versioning** -- provenance tracking across OCR/parse/translate stages

---

## 1. OCR and Text Acquisition

### Skip OCR: Use OpenITI Instead

| Collection | OpenITI ID | Source |
|---|---|---|
| Musnad Zayd | `0122ZaydIbnCali.Musnad.Zaydiyya0000052-ara1` | Maktaba Shamila al-Zaydiyya |
| Musnad al-Rabi | `0170RabicIbnHabibAzdi.JamicSahih.ShamIbadiyya0000155-ara1` | Maktaba Shamila al-Ibadiyya |

Both are **typed and community-proofread** (not OCR'd). Available at:
- https://github.com/OpenITI/RELEASE
- https://usul.ai/t/musnad-al-imam-zayd/61
- https://usul.ai/t/musnad-al-rabi-ibn-habib/183

### If OCR Is Ever Needed (Future Collections)

**OCR Engine Ranking (Arabic, 2025-2026, KITAB-Bench ACL 2025):**

| Tier | Engine | CER | Notes |
|---|---|---|---|
| Top (open) | QARI-OCR v0.2 (2B param VLM) | 0.061 | Best open-source, runs locally, handles tashkeel |
| Top (open) | Qalam (SwinV2+RoBERTa) | ~0.01 WER | Best for manuscripts specifically |
| Gold DH standard | Kraken + eScriptorium | >95% CAR | Used by OpenITI/KITAB, trainable |
| Mid | Mistral OCR 3 (Azure) | ~0.05 | Commercial, 50% batch discount |
| Low | EasyOCR (current) | 0.20 | General purpose, poor on Arabic |
| Low | Tesseract 5 | 0.54-0.58 | Without fine-tuning |
| Avoid | PaddleOCR | N/A | RTL ordering bug, unusable for Arabic |

**Preprocessing Best Practices:**
- 400 DPI (confirmed sweet spot)
- CLAHE + Sauvola binarization (multiscale, window 15-25px at 300 DPI)
- NFKC normalization + explicit Arabic presentation form substitution
- Store original alongside normalized (never overwrite)
- Use CAMeL Tools + PyArabic for post-OCR normalization

**Key References:**
- KITAB-Bench: https://arxiv.org/abs/2502.14949
- QARI-OCR: https://huggingface.co/NAMAA-Space/Qari-OCR-0.1-VL-2B-Instruct
- Kraken: https://github.com/mittagessen/kraken

---

## 2. Parsing Strategies

### Hybrid Regex + LLM (Recommended)

The Rezwan corpus project (1.2M narrations, arXiv:2510.03781) validated this approach:
- **Regex handles 95-98%** of cases at high speed (isnad markers, chapter headers, numbered hadiths)
- **LLM handles the ambiguous residual** (confidence-scored, routed when below threshold)
- Expert evaluation: 9.33/10 on chain-text separation

### Three-Tier Confidence Scoring

Score every parsed hadith at three levels:
1. **Parse confidence** -- Was the isnad/matn split clean?
2. **Narrator confidence** -- Do all narrators match a known-good lexicon?
3. **Chain confidence** -- Are temporal relations between narrators plausible?

Records > 0.85 auto-accept; 0.60-0.85 go to reviewer; < 0.60 re-parse.

### Layout Analysis

The HATFormer project (arXiv:2410.02179) showed that bounding box info from OCR helps separate:
- Body text (matn)
- Footnotes (hawamish)
- Marginal commentary (hashiya)

**Key References:**
- Rezwan: https://arxiv.org/abs/2510.03781
- HATFormer: https://arxiv.org/abs/2410.02179

---

## 3. Tradition-Specific Grading (CRITICAL)

### The Problem

Applying Sunni-style "sahih/hasan/da'if" labels to Zaydi or Ibadi hadiths is a **category error**.

### Zaydi Differences
- Ijtihad overrides hadith in Zaydi jurisprudence
- Narrations evaluated on consistency with the Imam's known positions (content-based, not chain-based)
- Zaydi rijal tradition differs from Sunni biographical dictionaries

### Ibadi Differences
- Musnad al-Rabi authentication rests on Ibadi scholarly consensus
- Early Ibadi transmission was oral by design
- Applying Sunni narrator criticism is a category error

### Required Schema Change

Every grade label must carry:
- `grade_tradition`: Which tradition's grading system (Sunni, Imami, Zaydi, Ibadi)
- `grade_source`: Which scholar or reference work
- `grade_method`: isnad-based, matn-based, or consensus-based

---

## 4. Embeddings and Search

### Recommended Stack

| Component | Tool | Why |
|---|---|---|
| Embeddings | BGE-M3 | Top Arabic performer, 8192-token context, runs locally |
| Vector DB | VectorChord (replaces pgvector) | Drop-in swap, 100x faster indexing, stays in PostgreSQL |
| BM25 hybrid | ParadeDB pg_search | Arabic root-matching + semantic similarity |
| Graph analytics | Neo4j GDS | PageRank, Louvain, path verification for narrators |

### Domain-Specific Model

XLM-R2-ID-AR (arXiv:2501.10175) -- bilingual Arabic/English model trained on 50M-word Islamic corpus (hadith + tafsir). May outperform BGE-M3 on Islamic domain retrieval.

### Cross-Collection Deduplication

Embed matn with BGE-M3, cluster at cosine similarity >= 0.92, flag clusters spanning multiple collections as variant narrations.

### Narrator Analysis (Neo4j GDS)

Prior art exists (Multi-IsnadSet: 2,092 narrators, 77,797 edges):
- **PageRank**: Narrator importance ranking
- **Louvain**: School detection (Basran, Kufan, Madinan, Yemeni circles)
- **Shortest Path**: Chain continuity verification (detect mu'dal/broken chains)
- **AR-Sanad**: 97.8% narrator disambiguation via KG + AraBERT re-ranking

### Automated Grading Feasibility

- Isnad-based structural analysis: >91% accuracy (viable)
- Matn-based epistemological judgments: unreliable (not viable for production)
- Recommendation: Frame as "suggested preliminary assessment" only

**Key References:**
- BGE-M3: https://huggingface.co/BAAI/bge-m3
- VectorChord: https://github.com/tensorchord/VectorChord
- XLM-R2-ID-AR: https://arxiv.org/abs/2501.10175
- Multi-IsnadSet: https://www.sciencedirect.com/science/article/pii/S2352340924004086
- AR-Sanad: https://link.springer.com/article/10.1007/s00521-024-10194-2

---

## 5. Quality Assurance

### Validation Checklist

- [ ] Hadith count matches the book's own index (fihrist)
- [ ] Chapter count matches source
- [ ] All pages OCR'd / all sections parsed
- [ ] Encoding consistency (Unicode normalization form audit)
- [ ] Isnad/matn boundary validation (linguistic pattern check)
- [ ] Cross-reference against known-good sources (Shamela, OpenITI)
- [ ] Grade labels carry tradition-specific attribution

### Cross-Referencing

- KITAB passim algorithm for text-reuse detection across collections
- Semantic similarity pass across multi-tradition corpus
- Narrator name validation against controlled vocabulary

### Arabic OCR Confusion Pairs (Post-Processing)

| Confused | Fix Rule |
|---|---|
| ه / ة | Position: ة only word-final |
| ي / ى | Position: ى only word-final |
| ا / آ / أ / إ | Alef variant normalization |
| ب / ت / ث | Dot count verification |
| ف / ق | Dot count (1 vs 2 above) |
| ر / ز | Single dot above/below |
| ع / غ | Single dot presence |

---

## 6. Pipeline Architecture and Versioning

### DVC for Data Versioning

Each pipeline stage becomes a DVC stage:
```
PDF/mARkdown -> parse -> structured JSONL -> translate -> validate -> unified CSV
```

Add JSON provenance sidecar for each artifact:
```json
{
  "source": "OpenITI/0122ZaydIbnCali.Musnad.Zaydiyya0000052-ara1",
  "parse_script_sha": "abc123",
  "llm_model": "gemma-3-27b-it",
  "llm_prompt_sha": "def456",
  "timestamp": "2026-05-08T12:00:00Z",
  "tradition": "Zaydi"
}
```

### Pipeline Orchestration

Start with **Prefect 3** (task-level retries, caching, concurrency limits).
Migrate to **Dagster** if asset graph grows complex.

---

## 7. Interoperability Standards

### Recommended Exports

| Format | Audience | Priority |
|---|---|---|
| JSON/CSV (current) | Application use | Already done |
| OpenITI mARkdown | Academic tools (KITAB, passim) | High |
| TEI XML | Academic publishing | Medium |
| RDF/OWL (SemanticHadith) | Knowledge graph interop | Medium |
| Dublin Core metadata | Library systems | Low |

### Narrator Entity Alignment

Align with SemanticHadith ontology for:
- Wikidata/DBpedia linking
- Cross-project narrator deduplication
- Standardized entity URIs

---

## 8. Related Projects and Resources

| Project | What It Does | Relevance |
|---|---|---|
| OpenITI | 1,373+ annotated Arabic texts | Source texts, mARkdown format |
| KITAB | Text-reuse detection (passim) | Cross-collection analysis |
| Rezwan | 1.2M hadith LLM pipeline | Architecture reference |
| SemanticHadith | OWL ontology for Six Books | Schema reference |
| AR-Sanad | Narrator disambiguation | Enrichment pipeline |
| Shamela | 1B-word Arabic corpus | QA cross-reference |
| QARI-OCR | Arabic VLM OCR | Future OCR engine |

---

## Immediate Action Items

### This Week
1. Download OpenITI mARkdown files for both Musnad Zayd and Musnad al-Rabi
2. Write parser for OpenITI mARkdown format -> our structured JSON
3. Compare OpenITI text with our existing OCR output (quality diff)
4. Add `grade_tradition` and `grade_source` fields to schema

### This Month
5. Install CAMeL Tools + PyArabic for Arabic text normalization
6. Set up DVC for dataset versioning
7. Replace pgvector with VectorChord
8. Evaluate BGE-M3 embeddings on sample hadith data

### This Quarter
9. Build Neo4j GDS narrator analytics (PageRank, community detection)
10. Implement hybrid BM25 + vector search
11. Cross-collection deduplication via semantic similarity
12. TEI XML export capability

---

## 9. OCR Artifact Correction (If OCR Is Used)

### Correction Tier List

| Tier | Approach | Impact |
|---|---|---|
| 1 | Replace EasyOCR with QARI-OCR v0.2 | 60% CER reduction |
| 2 | Reference-based LLM correction (align to Sunnah.com/OpenITI, correct divergent spans only) | Highest precision |
| 3 | ByT5 fine-tuned on (OCR output, clean text) pairs | No tokenizer issues with Arabic |
| 4 | Narrator name validation against Sanadset 650K (fuzzy match, edit distance 1-2) | Catches proper noun errors |

### Critical Warning

**Bare LLM prompting without reference anchoring actively degrades output quality** on classical Arabic (arXiv:2502.01205, "No Free Lunches"). Always ground the LLM with reference text from a canonical edition.

### Available Resources

- **Sanadset 650K**: 650,986 narrator records from 926 hadith books (ScienceDirect)
- **AraSpell**: seq2seq Arabic correction, CER 1.11% (arXiv:2405.06981)
- **ByT5**: byte-level model, 40% WER reduction on Arabic diacritization
- **CAMeL Tools**: morphological spell-checking for classical Arabic
- **Sunnah.com API**: canonical Arabic text for cross-validation

### Key References
- No Free Lunches: https://arxiv.org/abs/2502.01205
- Reference-based correction: https://arxiv.org/abs/2410.13305
- AraSpell: https://arxiv.org/abs/2405.06981
- Sanadset 650K: https://www.sciencedirect.com/science/article/pii/S2352340922007478
- ConfBERT: https://arxiv.org/abs/2409.04117

---

## Full Reference List

### OCR and Text Processing
- KITAB-Bench (ACL 2025): https://arxiv.org/abs/2502.14949
- QARI-OCR v0.2: https://arxiv.org/abs/2506.02295
- Qalam: https://aclanthology.org/2024.arabicnlp-1.19/
- Kraken: https://github.com/mittagessen/kraken
- eScriptorium: https://escriptorium.readthedocs.io/
- OpenITI AOCP Phase Two: https://openiti.org/projects/OpenITI%20AOCP%20Phase%20Two.html
- Arabic-Nougat: https://arxiv.org/abs/2411.17835
- Advances in Arabic-Script OCR: https://arxiv.org/abs/2402.10943

### Hadith NLP and Analysis
- Rezwan 1.2M corpus: https://arxiv.org/abs/2510.03781
- AR-Sanad narrator ID: https://link.springer.com/article/10.1007/s00521-024-10194-2
- SemanticHadith v2: https://a-kamran.github.io/SemanticHadith-V2/
- Multi-IsnadSet: https://www.sciencedirect.com/science/article/pii/S2352340924004086
- KG-Transformer narrator disambiguation: https://academic.oup.com/dsh/article-abstract/40/4/1085/8253513
- Hadith grading ML feasibility: https://aljamei.com/index.php/ajrj/article/view/155
- IslamicMMLU benchmark: https://arxiv.org/abs/2603.23750

### Embeddings and Search
- BGE-M3: https://huggingface.co/BAAI/bge-m3
- XLM-R2-ID-AR: https://arxiv.org/abs/2501.10175
- VectorChord: https://github.com/tensorchord/VectorChord
- ParadeDB hybrid search: https://www.paradedb.com/blog/hybrid-search-in-postgresql-the-missing-manual

### Digital Humanities and Standards
- OpenITI: https://openiti.org/
- KITAB text reuse: https://kitab-project.org/methods/text-reuse
- OpenITI mARkdown: https://maximromanov.github.io/mARkdown/
- TEI hadith encoding: https://link.springer.com/chapter/10.1007/978-3-319-73500-9_16
- Shamela corpus (ACL): https://aclanthology.org/W16-4007/
- Dublin Core for Arabic manuscripts: https://www.researchgate.net/publication/371225678

### Arabic Text Processing
- CAMeL Tools: https://camel-tools.readthedocs.io/
- PyArabic: https://pypi.org/project/PyArabic/
- Unicode Arabic normalization: http://www.unicode.org/reports/tr15/

### Ethics and Community
- Copyright and Islamic books: https://en.islamonweb.net/copyright-infringement-an-islamic-viewpoint
- Digitizing SW Asian manuscripts: https://www.asor.org/anetoday/2023/07/digitizing-manuscripts-southwest-asia
- Zaydi fiqh history: https://www.leidenarabichumanitiesblog.nl/articles/a-short-history-of-zaydi-fiqh

### Pipeline Architecture
- DVC pipelines: https://doc.dvc.org/start/data-pipelines/data-pipelines
- Prefect 3: https://docs.prefect.io/v3/develop/global-concurrency-limits
- Dagster: https://dagster.io/blog/training-llms
