---
type: runbook
updated: 2026-11-21
---

# Runbook

The current state of the Shura wa Istehsan build-out, for whoever picks it up
next. Authoritative design: `docs/architecture/data-architecture.md`. Readable
summary: `docs/architecture/brief-schema.html`. Track index: `conductor/tracks.md`.

## Goal

Build the app out fully: Postgres data layer, loaded and reconciled data,
refined interface, access control, and the contribution system. Delivered by
parallel lanes, each driven through its conductor track, with the session
lead reviewing, verifying and committing at each join.

## State on 2026-11-21

| Area | State |
| --- | --- |
| Branch | `refactor/postgres-drizzle`, local only, not pushed. Checkpoint of the pre-refactor tree is `af2f90b` |
| Live site | Unchanged. Still the 22 July build reading Neo4j. Nothing has been deployed this session |
| Build | `npx tsc --noEmit` clean, `npx next build` succeeds. 64 lint errors remain in pre-existing admin code |
| Postgres | Railway service `Postgres` (official image, PostgreSQL 18.6, SSL) in project `hadith-ontology`. Two databases: `railway` (production, schema only) and `islamicapps_dev` (development, safe to load and reset). Both migrated: 40 tables, 5 views, 1 materialized view; extensions `vector`, `pg_trgm`, `unaccent` |
| Schema code | `src/db/` (Drizzle schema, client, migrator, `verify.ts`), migrations in `drizzle/core/` |
| Neo4j | Still running and still the live store. Not to be removed before cutover and owner approval |
| you.com research feature | Removed from code, schema and docs. `YOU_API_KEY` is still set on the Railway `islamicapps` service; remove it with the next deploy (deleting a variable triggers a redeploy from GitHub `main`, which is older than the running build) |
| Conductor | 16 Neo4j-era tracks archived under `conductor/archive/2026-11-21-neo4j-era/`; 15 current tracks |

## Environment

- `.env.local` (git-ignored): `DATABASE_URL` is the development database over
  the public proxy; `DATABASE_URL_PRODUCTION` is the production database;
  `NEO4J_*` reach the live Neo4j.
- Railway CLI is linked to the project in this folder. `railway variables -s <service> --kv`
  prints raw values; never echo them.
- The app service's `DATABASE_URL` references the Postgres private URL. It is
  the superuser; the design requires a restricted role before cutover.
- `npm run db:migrate`, `npm run db:verify`, `npm run db:generate`.
- Local native PostgreSQL 16 has no pgvector; do not use it for this project.
- Three files under `datasets/hadith-data/` are access-denied at the OS level
  (`curation_backlog.csv`, `curation_manifest.json`,
  `curation_candidate_manifest.json`). Leave them; they are not in git.

## Decisions made by the owner

- PostgreSQL on Railway with Drizzle. The design's recommendations (section 14)
  are accepted for now.
- Plain parallel subagents, not scripted multi-stage workflows.
- you.com is not paid for: the research feature is removed.
- Name-segment matching is removed. Narrator matching uses a name invariant:
  five spelling rules, a fix to strip blessing formulas from lexicon names at
  extraction, and a kunya rule guarded to multi-component names. Hamza and
  ta marbuta folding are not adopted.
- Translation gaps use `tencent/hy-mt2-30b-a3b` on OpenRouter, key read at
  runtime from `~/.pi/agent/models.json`, output as unreviewed candidates.
- The Open Scholarly Contribution System plan is in scope: six planned tables
  (design section 5.15).
- Cross-tradition presentation (2026-11-21): every chain shows the tradition
  and source it comes from. The same report may appear in several traditions;
  those copies are linked at the level of the report so a reader can see that
  a hadith is carried by more than one tradition, while each sanad stays
  separate. Narrator identities are not merged across traditions
  automatically.
- OpenITI rijal texts under CC BY-NC-SA are acceptable. Material derived from
  them carries that licence: non-commercial, share-alike, with attribution.
- Kunya-only lexicon entries: automatic matching is allowed only as a labelled,
  lower-confidence match (shown with a marker, excluded from verified
  transmissions). This reading of the owner's answer is to be confirmed.
- Code is committed to the branch at each join. Nothing is pushed or deployed
  without the owner asking.

## Rules every lane follows

- Never delete or overwrite a dataset; write new files. Code moves to
  `src/scripts/archive/` unless the owner asks for removal.
- No identity, grade, date or translation is asserted by a machine. Machine
  output is a labelled, unreviewed candidate.
- Grades are attributed to a scholar within a tradition. No computed grade.
- One writer per table: pipeline tables or curation tables, never both.
- Lanes own disjoint paths (see each track's `metadata.json`). Shared files
  such as `package.json` are edited only by the session lead at a join.
- One verification sweep at a join: `npx tsc --noEmit`, `npx next build`,
  `npm run db:verify`, the Python suite.

## Lanes

| Lane | Tracks | Owns |
| --- | --- | --- |
| Data platform | `bundle-to-postgres-loader`, `neo4j-curation-export` | `src/db/load/**`, `datasets/hadith-data/pg_export/**`, `src/scripts/db/**` |
| App data layer | `query-port-and-action-switch`, `containment-and-access-control` | `src/db/queries/**`, `src/app/actions/**`, `src/lib/auth/**`, `src/proxy.ts`, server `page.tsx` data wiring |
| Interface | `ui-polish` | `src/components/**`, client components and route-state files under `src/app/**`, `globals.css` |
| Data gaps | `data-gap-diagnostics`, `narrator-identity-resolution`, `translation-recovery`, `grading-coverage`, `evidence-and-biography-curation` | `datasets/hadith-data/diagnostics/**`, candidate files, the canonical narrator normalizer |

## Open items for the owner

- Rights status for each source work; nothing is publishable until recorded.
- Whether provider English may be shown without row-by-row review.
- Which tradition the 21 hand-written narrator verdicts belong to.
- An off-machine copy of the datasets.
- When to push the branch and when to deploy.

## Pick-up checks

```
git log --oneline -12
npx tsc --noEmit && npm run db:verify
railway status
```
