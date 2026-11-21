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
- Rights are the publication gate. A per-work rights register
  (`docs/rights/rights-register.md`) carries the evidence and a proposal; the
  owner approves each work. Nothing is cleared by default.
- The development data snapshot may be served publicly as a preview, with a
  visible notice driven by database state. The approval and the notice are
  removed after the first release (see "Remove after the first release").
- Chain display: show every identity match for a name with its source; where
  sources disagree, show both. Only source-index matches confirmed by the
  Arabic text, and reviewer decisions, count as verified.
- Kunya-only entries match automatically but are marked "matched by kunya
  only". All terms, including kunya, are defined in the glossary
  (`src/lib/glossary/terms.ts`, `/glossary`).
- The 21 hand-written narrator verdicts are Sunni.
- Lexicon dates and places are to be rechecked against authoritative sources
  before they are relied on.
- Fetch hadith-kg and the Riwayat corpus into `datasets/sources/external/`.
- Push the branch to GitHub; ask before any production deploy. The push needs
  the 140 MB `unified_hadith_consolidated.csv` removed from unpushed history
  (approved): rewrite the unpushed commits, ignore the file, keep it on disk.
- Dataset backups go to a Railway bucket in the same project.
- After cutover the first priority is the contribution system.
- Curator names are decided at cutover.
- Code is committed to the branch at each join. Nothing is pushed or deployed
  without the owner asking.

## Remove after the first release

The development snapshot is served publicly as a preview under the owner's recorded approval (2026-11-21), with a
visible notice. When a release dataset version becomes current the notice already hides itself (it is driven by
`dataset_versions`); remove the rest:

- [ ] Revoke the approval row: `npx tsx src/scripts/db/approve-preview.ts --revoke --by <owner> --reason "first release is current"`
  (clears `public_override_*` and writes a `revoke_preview` row to `curation_audit`; the `approve_preview` audit row stays as history).
- [ ] Delete the notice component: `src/components/PreviewNotice.tsx`, `src/components/PreviewNoticeBar.tsx`, the
  `<PreviewNotice />` line and import in `src/app/layout.tsx`, and `getPreviewNotice` in `src/db/queries/dataset.ts`
  (delete the file if nothing else is in it).
- [ ] Delete the glossary `preview` entry the notice links to (`/glossary#preview`, `src/lib/glossary/terms.ts`) if no longer wanted.
- [ ] Delete `src/scripts/db/approve-preview.ts` if no further previews are wanted, and the "preview notice" flow in
  `src/db/queries/__tests__/http-gate.test.ts`.
- [ ] Delete the "Preview approval" section of `src/db/queries/AGENTS.md` and this section.

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

## Status at end of the 2026-11-21 session

Branch `refactor/postgres-drizzle` is pushed to GitHub. Nothing is deployed;
the live site still runs the July build on Neo4j.

Done and committed: Postgres schema (41 tables, 6 views), loader with 25 data
checks, query layer, curator access control with audit, refined interface,
glossary, rights register, preview notice, identity candidates with basis
labels, reconciled chain sidecars, translation and recovery candidates,
report-correspondence candidates, biography verification, dataset backup.

Next, in order:

1. Owner decisions: approve the 23 rights-clear works; rebuild the Sunni
   Arabic from OpenITI or wait on permissions; whether a kunya-only match may
   block a confirmed source identity; whether a correct passphrase should
   always succeed despite the per-name sign-in limit.
2. Report correspondences: tables (candidates, decisions, cluster members),
   loader, hadith-page section, review screen. Proposal in
   `datasets/hadith-data/diagnostics/report-correspondence/README.md`.
3. Export curation from Neo4j (commentaries, events, parallels, the 21
   biographies, recorded as Sunni) into the curation tables.
4. Load recovered data: generation markers, places, cited Imami rulings,
   Tirmidhi compiler statements, Taqrib verdicts and cited date candidates.
5. Identity review: the function that applies a reviewer decision, and a
   review screen over the queue.
6. Database roles, memory tuning, backups, deploy config; confirm at deploy
   that Railway's edge overwrites a client-sent `X-Real-IP`.
7. Cutover with the owner's approval, then about a week of observation, then
   retire Neo4j.
8. Contribution system (design section 5.15), the owner's first priority
   after cutover.

Known defects to fix in the ETL: 1,597 Sunni rows carry another report's matn
(non-unique join on source and hadith number); 12,617 matn values still
contain the chain; the census and audit count an empty chain as resolved;
Riwayat labels Musnad Zayd and Musnad al-Rabi' as Sunni.

## Owner decisions, second round (2026-11-21)

- The repository stays public: the project is built in the open.
- Main may deploy to the live site. Cutover happens at the next green join:
  migrate and load the production database, record rights, then merge to
  main and push. The live site then shows only rights-cleared works.
- Rights cleared at cutover: the 23 works the register finds clear (20
  classical Imami works from Thaqalayn, CC BY 4.0; Jami' al-Sahih, Musnad
  Zayd and Sahifat al-Rida from OpenITI, CC BY-NC-SA), Arabic with the
  required attribution, plus the project's own machine translations for
  those works, labelled as unreviewed machine translation.
- The archive is non-commercial; material derived from OpenITI texts is
  published share-alike under the same licence.
- Sunni Arabic: re-source from openly licensed copies (hadith-kg, OpenITI)
  and send the permission requests in parallel. The owner sends the
  requests; drafts are in docs/rights/rights-register.md.
- Identity tiers: the automatic top tier is "machine-reviewed" (AI review),
  never "verified". "Verified" is reserved for a decision by a permitted
  human reviewer. The project is open source so that review can be open.
- Kunya-only matches are a label only. They do not contest another identity
  and are ignored for grading and analysis.
- No human curators for now. The pipeline is the only writer on the
  deployment and review is machine-only until a base is in place. The admin
  stays locked (no curator configured).
- The three access-denied curation files were not locked on purpose. The
  owner unlocks them from an elevated shell; then they are backed up.

## Owner decisions, third round (2026-11-21)

- Rights: SETTLED. The owner holds permission with full scope. All 34 works
  are cleared for publication, Arabic and English, with the attribution lines
  the rights register words. Record every work as cleared at cutover. Do not
  reopen or re-raise this.
- Translation model pinned: `tencent/hy-mt2-30b-a3b` (OpenRouter) for
  Arabic to English. A registry records which model did which work
  (`datasets/hadith-data/model_registry.json`, `docs/models.md`).
- Auth primitives stay in the code but off the front end, behind an enable
  gate that defaults to off. No sign-in or admin surface is exposed while it
  is off.
- Rijal: a narrator may have many rijal entries. Each entry is kept under the
  author and work it comes from (a "rijal author" root: Ibn Hajar, al-Mizzi,
  al-Najashi, al-Tusi, and so on) and labelled by that author. Entries are
  not collapsed to one per narrator, and an ambiguous link is kept as several
  candidate entries rather than dropped.
- Crediting every source is the most important requirement. Every kind of
  borrowed material shows its credit where it appears: text source and work,
  translator or translation model, grader, rijal author and book, the dataset
  behind an identity claim. A missing credit is a defect.
- Source credit is kept simple: one source-record reference page with a
  source summary, and short link references (a source code and name)
  wherever material appears.
- Design direction: minimalist Swiss (International Typographic) style with
  simple, ultra-flat geometric SVG. Strict grid, typography-led hierarchy,
  near-black and off-white with one accent, flat fills, hairline rules, no
  gradients, shadows or decorative cards. A project-wide design-system pass
  applies it after the current wave lands.

## Owner decisions, fourth round (2026-11-21)

- The Imams' conventional kunyas in Imami chains (with the honorific marker)
  identify that Imam and count toward the machine-reviewed tier. Ordinary
  kunya-only names stay labels.
- Two independent sources naming the same person (the six-books source index
  and hadith-kg) count toward the machine-reviewed tier under their own
  label, "two sources agree".
- Lexicon dates, places and generations are shown on public narrator pages
  with a "narrator lexicon, not yet cited" label and source reference. The 61
  values that conflict with Taqrib are held back. Cited values are shown
  alongside where they exist.
- Deploy to the live site now and iterate. Later waves deploy as they land.
- DESIGN.md at the repository root is the maintained design reference. It
  builds on the owner's shared UI/UX guidance.

State after this join: 45 tables and 10 views; migrations 0000 to 0008;
the all-chains view, report correspondences, eras, source registry and
credits, browse pages, stable report addresses, the auth switch (off by
default) and the model registry are in.
