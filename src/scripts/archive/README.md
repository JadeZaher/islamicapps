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
- **`find-parallels.ts`** / **`ingest-approved-parallels.ts`** — comparative track
- **`link-sanad-chains.ts`** — `npm run db:link-sanads`
- **`backup-db.ts`** — DB backup utility
- **`audit-graph.ts`** — `npm run db:audit` (the generic Neo4j diagnostic that
  replaces the throwaway `_audit_gaps.ts`; see its CLI for `--section` flags)

Diagnostic scripts (`check-traditions.ts`, `verify-db.ts`,
`verify-migration.ts`, `diagnose-db.ts`, `data-readiness-audit.ts`) remain in
`src/scripts/` for the moment — their checks will be folded into
`db:regen --mode=test` (Phase 1 task 1.9) and they will be archived here at
that point (task 1.10).
