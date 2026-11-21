# `src/scripts/archive/` — deprecated ingestion / migration scripts

**Archived:** 2026-05-20
**By track:** [`neo4j_isnad_graph_regen_20260516`](../../../conductor/tracks/neo4j_isnad_graph_regen_20260516/)
**Authoritative spec:** that track's `spec.md` §9d (Script archive & cleanup)
**Policy:** per `MEMORY/feedback_no_delete_backup.md` — **archive, never delete.**
Every file in this directory is preserved (with git history where it was
tracked), prefixed with a one-line `DEPRECATED` header pointing here. They are
NOT loaded by anything in `package.json`.

If any file in this directory turns out to still be needed, move it back to
`src/scripts/` and remove the deprecation header — the move is fully
reversible.

---

## Why archive

The repo accumulated **32 TypeScript scripts touching Neo4j ingestion** —
six per-tradition importers, the buggy `import-datasets.ts` (uuidv4-per-run
narrator duplication + scalar `n.reliability` unified-narrator fallacy), a
fan of one-off migration scripts whose work is long done, and several scripts
that properly belong to other Conductor tracks. The `neo4j_isnad_graph_regen`
track consolidates ingestion into a single `src/scripts/regen-isnad-graph.ts`
with `--mode=test|fullregen|diff` and retires the rest.

---

## Disposition (19 archived here)

### Replaced by unified `db:regen` (8)

The unified runner reads `datasets/hadith-data/all_hadiths_unified.csv`
(expanded to include classical collections per FR-0.9) and is the **single
entry point** for every load. The per-tradition importers are no longer
needed.

| File | Replaced because |
|---|---|
| `import-datasets.ts` | Live narrator-duplication bug (`uuidv4()` per run) + unified-narrator fallacy (`n.reliability` scalar). Replaced by `regen-isnad-graph.ts`'s MERGE on `RAWI:scholar_indx` + reified `:Assessment`. Its `db:import` / `db:import:clear` package.json entries are also removed. |
| `import-classical-collections.ts` | Folded into `regen_unified_csvs.py` (FR-0.9) so classical collections flow through the same unified pipeline. |
| `import-musnad.ts` | Same — Musnad Ahmad now ingests via the unified CSV. |
| `import-pure-canon.ts` | Same source data (`pure_canon.jsonl`); same fold. |
| `import-shia-collections.ts` | Replaced — Imami flows through unified CSV via Thaqalayn build. |
| `import-zaydi-collections.ts` | Replaced — Zaydi flows through OpenITI parse → unified CSV. |
| `reimport-zaydi.ts` | One-shot Zaydi reimport; superseded. |
| `apply-schema.ts` | Superseded by `init-db.ts` (`npm run db:init`). |

### One-off migrations (work done) (7)

These performed one-time data migrations that have already shipped. Kept for
historical reference only.

| File | What it migrated |
|---|---|
| `backfill-tradition.ts` | Initial population of `Hadith.tradition`. |
| `tag-ibadi.ts` | One-shot Ibadi tagging on the original import. |
| `migrate-tradition-to-edges.ts` | Tradition-as-property → `:FROM_TRADITION` edges. |
| `migrate-shia-to-imami.ts` | Rename of `"Shia"` → `"Shia Imami"`. (The regen track's task 0.7 finishes the canonicalization to `"Imami"`.) |
| `migrate-source-names.ts` | Source name normalization (per `src/lib/constants/sources.ts`). |
| `rename-anthology-sources.ts` | Anthology source name renames. |
| `fix-name-arabic.ts` | One-pass Arabic-name backfill on Narrators. |

### Owned by other Conductor tracks (4)

Not ingestion concerns — these belong with the tracks responsible for the
specific enrichment. Archived here until the owning track formally adopts
them (move out of `archive/` and into a fresh script when that track runs).

| File | Owning track |
|---|---|
| `clean-hadith-text.ts` | [`text_cleanup_embedding_prep_20260425`](../../../conductor/tracks/text_cleanup_embedding_prep_20260425/) |
| `normalize-grades.ts` | [`grade_normalization_20260425`](../../../conductor/tracks/grade_normalization_20260425/) |
| `enrich-narrators-deep.ts` | [`narrator_enrichment_20260425`](../../../conductor/tracks/narrator_enrichment_20260425/) |
| `enrich-narrators-from-csv.ts` | [`narrator_enrichment_20260425`](../../../conductor/tracks/narrator_enrichment_20260425/) |

---

## Not archived (still active in `src/scripts/`)

Kept because they are referenced in `package.json` or remain operationally
useful:

- **`init-db.ts`** — `npm run db:init` (Neo4j schema init, idempotent)
- **`regen-isnad-graph.ts`** — `npm run db:regen` (the unified runner)
- **`remediate-legacy-scalar-assessment.ts`** — `npm run db:remediate-legacy-assessment`
- **`seed-historical-data.ts`** — `npm run db:seed-history`
- **`ingest-approved-parallels.ts`** — comparative track
- **`link-sanad-chains.ts`** — `npm run db:link-sanads`
- **`backup-db.ts`** — DB backup utility
- **`audit-graph.ts`** — `npm run db:audit` (the generic Neo4j diagnostic that
  replaces the throwaway `_audit_gaps.ts`; see its CLI for `--section` flags)

Diagnostic scripts (`check-traditions.ts`, `verify-db.ts`,
`verify-migration.ts`, `diagnose-db.ts`, `data-readiness-audit.ts`) remain in
`src/scripts/` for the moment — their checks will be folded into
`db:regen --mode=test` (Phase 1 task 1.9) and they will be archived here at
that point (task 1.10).

---

## 2026-06-10 addendum — chain-data ultrapilot batch probes

**Archived by:** investigation flow that produced [`uniform_isnad_extraction_20260609`](../../../conductor/tracks/uniform_isnad_extraction_20260609/).
**Policy:** same as above — preserved, not deleted; reversible via plain `mv` back to `src/scripts/`.

| Archived file | Was used for | Why archived |
|---|---|---|
| `diagnose-chain-data-2.ts` | Drill-down probe (Chain-node property dump for Tirmidhi #1, sibling-Chain-sharing audit, supernode chain-source breakdown, position-gap detection) during the 2026-06-05 chain-data diagnostic. | One-off — superseded by `diagnose-chain-data.ts` at the same level (which stayed live as the FR-6.6 acceptance test for the new track). Its specific queries are documented in the new track's spec §2.2. |
| `peek-tirmidhi-csv.ts` | Peek at raw CSV rows for a few specific Tirmidhi hadith ids (and an Imami sample) to confirm `chain_indx` shape before the W1/W3 patches. Uses the project's own `readUnifiedCsv` parser. | One-off — the row-shape facts it surfaced are now permanent in the new track's spec §2.1. Re-write in 30 seconds if needed; not worth keeping as a script. |
| `probe-tirmidhi-text.ts` | Pull the live `sanad` / `text_ar` / `matn_ar` for the canary hadith `626a2cb0-…` during the 2026-06-09 retraction-of-conclusion exchange (the moment we realised the sidecar's truncated sanad was dropping post-convergence narrators). | Pure ad-hoc probe; its job is now done. The text-reading itself is folded into the new track's Phase 1 unit-test fixtures (`text_ar` for FR-1.3 case (a) is exactly this hadith). |

### Promoted in the same batch (stayed in `src/scripts/`, renamed)

These three were probe scripts originally but proved generally useful — renamed with permanent names:

| Original | New name | Permanent purpose |
|---|---|---|
| `probe-chain-stats.ts` | [`report-chain-stats.ts`](../report-chain-stats.ts) | Per-source `:Chain` / `:INCLUDES` summary against the live Neo4j. Run as `npx tsx src/scripts/report-chain-stats.ts`. Useful as a quick state check during any chain-touching track. |
| `probe-neo4j-batch.ts` | [`bench-neo4j-batch.ts`](../bench-neo4j-batch.ts) | Realistic-shape MERGE batch timing probe (4 stages: Hadith MERGE, Chain MERGE, HAS_CHAIN MERGE, INCLUDES CREATE). Originally identified the 2026-06-08 `WRITE_TX_TIMEOUT_MS` 30s ceiling as the cause of fullregen retry-storms. Run when investigating Neo4j-write latency regressions. |
| `probe-neo4j-perf.ts` | [`bench-neo4j-latency.ts`](../bench-neo4j-latency.ts) | Single-MATCH + UNWIND-MATCH latency probe. Useful when triaging "is Railway slow today?" before tuning batch loaders. |
| `probe-tirmidhi.ts` | [`verify-tirmidhi-fix.ts`](../verify-tirmidhi-fix.ts) | Canary check for the chain on hadith `626a2cb0-…` (Jami' al-Tirmidhi #1). Will be the smoke test for `uniform_isnad_extraction_20260609` guardrails G-1/G-2/G-3. |

None of the 4 promoted scripts are wired into `package.json` — they're operator tools, run via `npx tsx`.
