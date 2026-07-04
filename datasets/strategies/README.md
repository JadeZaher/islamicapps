# Strategies

One file per distinct methodology — algorithm, decision, evaluation procedure, or pipeline mode — that the project uses to transform raw sources into the unified hadith graph.

Strategy files exist for the same reason source files do: they make the project's *reasoning* citable. A future contributor (human or AI) should be able to read one file and understand not just *what* an algorithm does, but *why we picked it*, *what we evaluated against*, and *what it doesn't handle*. See [`_TEMPLATE.md`](./_TEMPLATE.md).

## Index

| Slug | Strategy | Status | Domain |
| --- | --- | --- | --- |
| [uniform-tahweel-aware-isnad-extraction](./uniform-tahweel-aware-isnad-extraction.md) | Rule-based parser for taḥwīl-aware isnad chains | ✅ active | Isnad parsing |
| `tier2-llm-isnad-reconciliation` | LLM second-opinion fallback for suspicious isnad rows | ⏳ pending | Isnad parsing |
| `tiered-narrator-entity-resolution` | Multi-tier matching of narrator surface forms → `scholar_indx` | ⏳ pending | Entity resolution |
| `attribution-classification` | Rule-based marfu/mawquf/maqtu classifier | ⏳ pending | Hadith classification |
| `tahweel-occurrence-audit` | Statistical audit of ح-marker distribution per source | ⏳ pending | Evaluation |
| `neo4j-reified-isnad-schema` | `:Chain` reification + multi-edge graph model | ⏳ pending | Graph schema |
| `vector-embedding-pipeline` | CAMeLBERT-CA / BGE-M3 embeddings for semantic search | ⏳ pending | Search |
| `comparative-parallel-discovery` | Staged review of cross-cultural parallels | ⏳ pending | Comparative study |
| `narrator-biographical-enrichment` | Read-only jarḥ wa taʿdīl enrichment from rijal sources | ⏳ pending | Narrator enrichment |
| `regen-pipeline-modes` | fullregen / repair / enrich / diff orchestration | ⏳ pending | Pipeline architecture |
| `arabic-text-cleanup` | Mechanical + LLM purification of OCR/typing artifacts | ⏳ pending | Text preprocessing |

> Status legend: ✅ active · ⏳ pending documentation · 🚧 experimental · 📦 superseded.

## Adding a new strategy

1. Copy [`_TEMPLATE.md`](./_TEMPLATE.md) to `datasets/strategies/<your-slug>.md`.
2. Fill in the front-matter. The non-obvious required fields:
   - `evaluation_method` and `evaluation_results` — if you don't have these yet, mark `status: experimental` and link the open evaluation track.
   - `consumes_sources` — slugs from `datasets/sources/`. Wrong slugs will fail the credits build.
3. Write the prose, especially **Why we picked this over alternatives** — that's the section that gives the next contributor (or auditor) the most leverage.
4. Add a row to the index above.
5. Re-run `npm run build:credits`.

## When to write a new strategy file vs. amend an existing one

Write a new file when:

- A new algorithm replaces an existing one (mark the old one `status: superseded` and link forward).
- A pipeline gains a distinct *mode* with its own evaluation criteria (e.g. `regen-fullregen` vs `regen-repair`).
- A new source brings in a new methodology unique to it (e.g. Zaydi-specific grading reconciliation).

Amend an existing file when:

- The same strategy gets a parameter tuned or a bug fixed.
- The strategy's scope expands to a new tradition but the method is unchanged.
- New evaluation evidence lands for an existing strategy.

When in doubt, prefer a new file with a clear `supersedes:` link — superseded files stay in the repo as evidence of the project's reasoning history, not deleted.
