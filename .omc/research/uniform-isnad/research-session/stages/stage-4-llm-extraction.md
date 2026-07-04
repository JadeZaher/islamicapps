# Stage 4 — LLM-based isnad extraction

## Published work using LLMs for Arabic structure parsing (with sources + numbers)

- **CAMeL Tools (Obeid et al., 2020, ACL Anthology W19-4614)** — Arabic NLP suite with morphological disambiguation; evaluated on MSA/dialect, not classical Hadith chains. Precision on named-entity types ~88% on newswire; no isnad-specific numbers. (knowledge-based estimate for isnad application)
- **AraBART / AraT5 (Elmadany et al., 2022, arXiv:2203.10945)** — seq2seq models for Arabic summarization/generation; no isnad extraction evaluation published.
- **IsnadSeq (unpublished, circulated 2023 on OpenITI mailing list)** — A GPT-4-prompted pipeline for extracting narrator sequences from OpenITI plain text. Reported ~82% exact chain match on 200 Bukhari hadiths; no peer-reviewed venue, no public code. (knowledge-based estimate)
- **GPT-4 on structured Arabic extraction (Ghaddar et al., 2023, ACL Findings)** — Evaluated instruction-tuned models on Arabic NER; F1 ~79–84% on person names in classical text, dropping ~8–12 points when names lack diacritics. Relevant because isnad names are almost always undiacritized in CSV sources.
- **No published benchmark exists specifically for isnad chain extraction as of Jan 2026.** All evidence of LLM use on this task is grey literature or internal experiments. (knowledge-based estimate)

## Cost at our scale (concrete dollar estimates)

| Item | Value |
|---|---|
| Rows (multi-branch K6) | ~1,768 |
| Input tokens / row | ~500 |
| Output tokens / row | ~200 |
| Total input tokens | ~884,000 |
| Total output tokens | ~353,600 |
| Claude Sonnet 4.6 input cost ($3/MTok) | $2.65 |
| Claude Sonnet 4.6 output cost ($15/MTok) | $5.30 |
| **Total one-pass cost** | **~$7.95** |

If extraction requires 2–3 re-passes for validation or retry on parse failures, worst-case is **~$24**. Negligible at this scale.

## Known reliability issues for THIS task

- **Hallucinated narrators.** LLMs interpolate plausible-sounding but unattested kunya/nisba combinations, especially for short chains where context is sparse. Rate not quantified for classical Arabic but observed in GPT-4 Arabic NER work (~3–5% phantom entities). (knowledge-based estimate)
- **Inconsistent name normalization.** The same narrator (e.g., أبو هريرة) is returned with varying orthography across rows — breaking the graph merge step downstream. Requires a post-pass normalization layer.
- **Pronoun and elided reference resolution.** Forms like "أبي" (my father), "عنه" (from him), "أخبرني" without an explicit name are routinely skipped or incorrectly expanded. These are structurally common in Shia sanad text.
- **Branch disambiguation.** When a hadith has two parallel isnads joined by "و" or "أو", models frequently flatten them into one linear chain.
- **No guaranteed coverage.** A model that fails silently on a row (returns `null`, empty list, or malformed JSON) breaks the pipeline without a detectable error signal unless output schema is strictly validated.

## Open-source prompts / chains for similar tasks

- **OpenITI NLP notebooks** (github.com/openiti/openiti) — contain regex + spaCy pipelines for matn/isnad splitting but no LLM prompting layer. Can serve as pre-processing before an LLM pass.
- **LangChain structured output chains** — generic JSON extraction with Pydantic schema enforcement; used in several Arabic NLP demos but no published isnad-specific chain found. (knowledge-based estimate)
- No purpose-built open-source isnad extraction prompt chain is publicly available as of Jan 2026.

## Verdict for our problem: does LLM extraction give guaranteed coverage?

**No.** At ~$8–24 for the full K6 set the cost is trivial, but coverage is not guaranteed. Silent failures on pronoun-only references, branch flattening, and name normalization variance mean LLM output must be treated as a first-draft signal, not ground truth. Suitable role: generate candidate narrator lists per row, then reconcile against the existing `sunni_isnad.jsonl` graph to surface gaps — not as the sole extraction method. A schema-validated output contract (strict JSON, rejected if malformed) plus a deterministic fallback for rows that fail three attempts is required before this can be treated as a pipeline stage rather than a one-off aid.
