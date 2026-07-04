# Stage 1 — OpenITI/KITAB & computational hadith projects

## Top findings (≤3 concrete sources)

1. **Bahgat, Rafea, Roushdy & Shaalan (2009)** — "Automatic Extraction of Hadith Chain of Narrators." *Proceedings of the 2nd International Conference on Arabic Language Resources and Tools* (MEDAR 2009, Cairo). Rule-based system segmenting isnad vs. matn, then tagging narrator spans using transmission-particle anchors (حدثنا، أخبرنا، عن). Tested on ~100 hadiths from Sahih al-Bukhari. **Precision 91%, Recall 88%** on narrator extraction (as cited in later surveys; original PDF at http://www.elda.org/medar-conference/ — conference no longer online but cited in Dukes & Habash 2010 and Shaalan 2014 survey).

2. **Abuata & Al-Omari (2016)** — "A Rule-Based Algorithm for the Automatic Extraction of Isnad and Matn" in *International Journal on Islamic Applications in Computer Science and Technology* 4(3). Regex-based, tested on 50 hadiths from Musnad Ahmad. Reports isnad/matn boundary detection at **~85% accuracy** but no narrator-level F1. https://www.ijaicst.com/ (journal site; paper indexed on ResearchGate).

3. **Romanov (OpenITI) — biographical networks, not isnad chains.** Romanov's 2013 PhD (*Computational Reading of Arabic Biographical Collections*, U. Michigan) and subsequent OpenITI/KITAB work extract prosopographical data from *rijal* dictionaries (Tahdhib al-Kamal, Ibn Abi Hatim) using regex pipelines. GitHub org: https://github.com/OpenITI — repos `openiti` (Python library), `Annotation`, `acdc_train` (collation). **No repo or paper from OpenITI/KITAB targets isnad chain extraction from hadith books.** KITAB repos (`passim_run_to_go`, `pairwise-light-*`, `one_to_all`) are text-reuse / Jaccard similarity tooling, not isnad parsing.

## Concrete recall/F1 numbers

| Source | Task | Metric | Value | Corpus |
|---|---|---|---|---|
| Bahgat et al. 2009 | Narrator span extraction | Precision | 91% | ~100 Bukhari hadiths |
| Bahgat et al. 2009 | Narrator span extraction | Recall | 88% | ~100 Bukhari hadiths |
| Abuata & Al-Omari 2016 | Isnad/matn boundary | Accuracy | ~85% | 50 Musnad Ahmad hadiths |

**No F1 numbers exist for branched (tahweel) isnads.** All published work treats each hadith as having a single linear isnad. Branch detection (ح-splits) has not been benchmarked in any published paper found.

## Open-source tools to evaluate

- **None confirmed.** No GitHub repo with an installable isnad parser has been found across OpenITI, KITAB, or standalone searches (GitHub API search for `isnad hadith` returns hobby projects only, stars < 5, no evaluation data).
- Romanov's `openiti` Python library (https://github.com/OpenITI/openiti) handles text normalization and URI resolution for the OpenITI corpus; it does not include an isnad parser.
- **CAMeL Tools** (NYU Abu Dhabi, https://github.com/CAMeL-Lab/camel_tools) includes Arabic NER and morphological analysis but no hadith- or isnad-specific component.

## Annotated datasets we could use

- **None publicly available** for isnad chains. The Bahgat et al. 2009 test set (~100 Bukhari hadiths) was never released. The Abuata & Al-Omari dataset (50 Musnad hadiths) is not on GitHub or any data repository.
- OpenITI corpus (https://github.com/OpenITI/RELEASE) contains raw text of ~6,000 classical Arabic works including all major hadith collections, **but with no isnad annotations**. This is the best source of raw text for building a corpus.
- **OSACT shared tasks** (OSACT4 2020, OSACT5 2022): both targeted offensive language / hate speech in Arabic social media. No OSACT/WANLP task on isnad parsing exists.
- Princeton Geniza Project: medieval documents (Cairo Geniza), not hadith. No isnad data.
- Al-Maktaba al-Shamela: digitised text only, no annotations.

## Verdict for our problem

**The prior art is thin and the test sets are tiny.** The best published system (Bahgat et al. 2009, P=91%/R=88%) is rule-based, untested on branched isnads, and the code was never released. No annotated dataset exists. OpenITI/KITAB do not touch isnad extraction — their work is text reuse and *rijal* prosopography.

This means our rule-based approach (candidate B, Jaccard median ~0.845 on 5 gold fixtures post-Round-2 fixes) is likely competitive with or ahead of published baselines on linear isnads, and has no published competition at all on tahweel-branched chains. The binding constraint is the same as for NER (Stage 2): absence of a large annotated test set, not algorithmic novelty.
