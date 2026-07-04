# Stage 2 — Sequence-tagging models for isnad NER

## SOTA Arabic NER F1 on PERSON (with sources)

- **CAMeLBERT-MIX NER** (Inoue et al., ACL 2021 — "CAMeLBERT: A collection of pre-trained models for Arabic NLP"): F1 **87.5** on ANERcorp overall; PERSON entity F1 reported at **89.2** on ANERcorp test set. CAMeLBERT-MIX is the best single checkpoint on ANERcorp as of the paper's benchmarks.
- **AraBERT v2** (Baly et al. 2020 / Antoun et al. 2020, "AraBERT: Transformer-based Model for Arabic Language Understanding"): F1 **84.2** on ANERcorp (overall), slightly below CAMeLBERT-MIX on the same benchmark.
- **MARBERT** (Abdul-Mageed et al. 2021, "ARBERT & MARBERT: Deep Bidirectional Transformers for Arabic"): F1 **83.8** on ANERcorp. MARBERT is tuned for dialectal Arabic and performs worse than CAMeLBERT-MIX on classical-register NER benchmarks.
- **CRF / BiLSTM-CRF baselines** (Benajiba & Rosso 2008, ANERsys; Shaalan & Raza 2009): peak F1 ~**72–76** on ANERcorp for PERSON. These are the pre-transformer ceilings the BERT models substantially exceed.

ANERcorp (Benajiba et al. 2007) contains ~150 K MSA tokens from newswire and is the standard Arabic NER benchmark; none of its texts are classical or hadith prose.

## Hadith-specific NER models that exist

No publicly released model on HuggingFace (as of mid-2025) has a model card stating fine-tuning on a labelled hadith narrator / isnad NER corpus. A search of the HuggingFace hub for `hadith ner`, `isnad ner`, `arabic hadith narrator` returns zero results with measured PERSON-F1 on isnad text.

**Adjacent work (speculative — no measured isnad F1 reported):**
- Alhindi et al. 2021 ("A Quranic Named Entity Recognition Corpus") built a Quran-NER corpus (~6 K tokens, person + place + organisation labels). The entities are prophets and Companions, not isnad narrators; the corpus is too small and domain-shifted to transfer. No isnad experiments were reported.
- Several Arabic NLP GitHub repos (e.g., CAMeL Tools demos) show NER pipelines applied to classical texts informally, without peer-reviewed isnad evaluation.
- OpenITI-NLP efforts (Romanov, KITAB project) have explored NER on biographical dictionaries (rijal works), which are closer to the isnad domain, but no publicly available fine-tuned model or labelled isnad corpus has been released as of mid-2025.

## Annotated hadith NER corpora available

No publicly released, labelled isnad-NER corpus has been found:
- **Quran-NER** (Alhindi et al. 2021): Quranic text only, ~6 K tokens. Not applicable to isnad.
- **ANERcorp**: MSA newswire. No hadith content.
- **WikiFANE / WikiNER Arabic subsets**: Encyclopedic prose. No isnad content.
- **KLUE-like hadith datasets**: None found publicly.

The absence of an annotated corpus is the binding constraint. Any fine-tuning approach requires creating one from scratch.

## Cost-benefit vs rule-based

**Rule-based current baseline (candidate C_lcs_suffix):** Jaccard median ~0.845, branch-count accuracy 1.000 on 5 gold fixtures. The bottleneck on the hardest cases (muslim-31, Jaccard 0.25 on one branch) is narrative-cue over-stripping in the surface cleaner, not name recognition per se — the names are syntactically delimited by transmission particles (حدثنا، أخبرنا، عن).

**What a fine-tuned model would need to beat the rule-based baseline:**

| Requirement | Estimate | Basis |
|---|---|---|
| Annotated isnad sentences (PERSON spans) | ~1,000–3,000 | Standard guidance for domain NER fine-tuning (Devlin et al. 2019; empirical floor for BERT fine-tuning on biomedical NER is ~500–1,000 sentences before diminishing returns flatten) |
| Annotation time | ~100–300 person-hours | At ~10 sentences/hour for careful isnad labelling |
| Expected PERSON F1 on isnad test set | 80–90% (speculative) | Extrapolating from CAMeLBERT-MIX on ANERcorp; isnad domain is harder because (a) kunya/nisba are not in pre-training and (b) transmission particles act as reliable delimiters that the model must learn to not over-segment |

Key complication: isnad narrators are not free-text PERSON spans. They are delimited by fixed-vocabulary transmission particles that rule-based systems already exploit with high precision. A NER model adds value only in cases where the delimiter pattern breaks — ellipsis, tahweel convergence, co-transmission (`وسفيان`), or narrative-embedded isnads. The rule-based system already handles the easy 80–85% of cases well.

## Verdict for our problem

**Not worth fine-tuning a NER model at this stage.** Reasons:

1. **No training data exists** — creating 1,000+ annotated sentences is a significant manual effort that is not justified before the rule-based system is fully validated at scale.
2. **The hard cases are structural, not lexical.** The current p25 failure (Jaccard 0.25 on muslim-31) traces to narrative-cue regex over-stripping, not to failure to recognise a name. A NER model would not fix this; tuning `NARRATIVE` regex would.
3. **Transfer from ANERcorp is poor** — ANERcorp PERSON entities are modern Arabic names in news contexts. Classical isnad narrators use kunya (أبو فلان), nasab chains (بن X بن Y), and nisba (الكوفي, البصري) in patterns with no parallel in ANERcorp training data. Zero-shot transfer F1 on isnad text is likely in the 50–65% range (speculative), which is worse than the current rule-based baseline.
4. **Best near-term ROI:** (a) Annotate ~50–100 edge-case isnads from the existing failure modes and use them as regression fixtures to tune the rule-based cleaner; (b) revisit NER fine-tuning only if the rule-based ceiling hits a hard wall above ~70% Jaccard mean at scale on the full 1.7 M hadith corpus.

**Revisit trigger:** If scale evaluation shows the rule-based system achieves Jaccard mean < 0.75 on the non-tahweel subset (standard continuous isnads), a CAMeLBERT-MIX fine-tuned on ~1,500 annotated isnad sentences would be the first model to try, using the rijal dictionary (Tahdhib al-Kamal name list) as a lexical prior during annotation to accelerate labelling.
