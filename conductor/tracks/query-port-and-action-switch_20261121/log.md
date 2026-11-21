---
type: track-log
track: query-port-and-action-switch_20261121
---

# Log

## 2026-11-21 — app data layer lane

- Query layer `src/db/queries/` (see its AGENTS.md): hadith, hadith-review, isnad, narrator, narrator-review,
  assessment, history, location, commentary, commentary-review, comparative, comparative-review, curation, write,
  health, enums, contracts, mappers, sql-helpers. All public reads go through `public_*` views.
- Actions: `src/app/actions/read/{hadith,narrator,comparative}.ts`, `src/app/actions/curation/{commentary,comparative,
  history,location,review,search}.ts` + `schemas.ts` (zod). Section 9.3 actions in `review.ts` and the two publish
  actions. Pages read query functions directly (rule 2), so page-only reads are not public POST endpoints.
- Pages switched: `/hadith`, `/hadith/[id]` (+ `data.ts`, `layout.tsx`), `/narrator`, `/narrator/[id]` (+ `data.ts`,
  `layout.tsx`, `generateMetadata`), `/comparative`, every `/admin/*` page. No page imports the Neo4j actions.
- `graph-actions.ts`, `comparative-actions.ts` kept, marked for the retirement sweep, writes gated.
  Client components that still import them: `admin/commentaries/client.tsx` (searchHadiths, searchNarrators,
  create/update/deleteCommentary), `admin/comparative/client.tsx` (all comparative writes, searchHadiths),
  `admin/events/client.tsx`, `admin/locations/client.tsx`, `admin/hadith/client.tsx` (exportHadiths),
  `comparative/client.tsx` (searchParallels). Same names exist under `actions/curation/*` and `actions/read/*`.
- `/api/health`; ESLint layering rules in `eslint.config.mjs` (DB imports and `sql` templates banned in
  `src/app/**` and `src/components/**`; `*-review` queries banned outside admin and curation).
- Interface-lane handoffs applied: plain tradition labels, empty-state copy, chain health and tracesToProphet
  removed, narrator metadata, not-found decided in segment layouts (404 status still blocked by root loading.tsx).
- Schema gaps: `apply_decision(unit_id)` absent (decisions recorded, `applied: false`); no owner commentary policy
  column (publish requires a citation); `hadith_embeddings` not shipped (rights do not update it).
- Deferred: `/api/export/hadiths` streaming route; keyset pagination for admin; research route,
  `commit-parallel.ts`, `find-parallels`, `db:audit` ports; release-gate and parity test ports.
