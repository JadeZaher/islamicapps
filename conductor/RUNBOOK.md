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
| Live site | Still the 22 July build reading Neo4j until `main` is pushed. Production database ready: see "Production state" below |
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

## Production state (2026-11-21, go-live pass)

The production database (`railway` on the Railway Postgres) is migrated, loaded and ready; the live service still runs
the July build until the session lead merges `refactor/postgres-drizzle` to `main` and pushes.

| What | State |
| --- | --- |
| Migrations | Production: `0000` to `0011` (`0010`/`0011` external identity, 2026-11-21 names pass); `db:verify` passes. Development: `0009`, not touched since (owner: no development database) |
| Dataset version | Production: `bbafb2f142136246bcf30abcbb3b0d04452555dc5ca64c2eef5df8664e4f11f5` (projection `2026.11.21.4`, `development/pg-load-2026-11-21/projection-v4`), current and complete; logs `prod-load-3.log` (failed on `/dev/shm`, rolled back), `prod-load-4.log` (loaded), `prod-load-5-reload.log` (identical reload: 0 rows changed). Superseded: `e2430eae…` (`2026.11.21.3`) |
| Preview approval | Recorded on production for `bbafb2f1…`: by `owner`, "preview while data is under review; approved 2026-11-21" |
| Rights | All 34 works `cleared`, English policy `source_provided_and_machine_allowed`, actor `system:owner-decision` (`npm run db:record-rights`) |
| Public | 99,273 reports (Sunni 64,348, Imami 33,223, Ibadi 1,004, Zaydi 698); 66,017 English texts, all source-provided (was 55,359: 10,658 held back only for the ﷺ symbol); 114,594 chains; 157,471 machine-reviewed links (Sunni 132,815, Imami 23,959, Ibadi 697); 27,173 teacher-student links; 66,666 correspondence pairs shown; 0 eras and 0 events (38 eras and 54 events seeded, unpublished until cited); 21 biographies seeded, unpublished |
| Search indexes | `indexes-heavy.sql` built on production |
| Server tuning | Applied with `ALTER SYSTEM` and reloaded; `shared_buffers`, `max_connections`, `huge_pages` wait for a Postgres restart |
| Service variables | `SITE_URL=https://islamicapps-production.up.railway.app` and `NEXT_TELEMETRY_DISABLED=1` set with `--skip-deploys`; `AUTH_ENABLED` and `PRIVATE_PREVIEW` absent (off) |
| Config | `railway.json`: Dockerfile builder, health check `/api/health` (120 s), restart on failure. Migrations stay manual (no pre-deploy command) |

### Deploy (session lead)

1. Pick-up checks: `npx tsc --noEmit`, `npm run db:verify` (development), and the same `db:verify` with `DATABASE_URL`
   set to the production URL.
2. Merge `refactor/postgres-drizzle` into `main` and push. Railway builds the Dockerfile and deploys; the deploy
   succeeds only when `/api/health` answers 200 (the database is reachable).
3. Check the live site: `/`, `/collections`, a report per tradition, `/narrator/narrator%3Arawi%3A20001`, `/sources`,
   `/glossary`, `/api/health`; `/admin` and `/sign-in` answer 404.
4. Restart the Postgres service once, at a quiet moment, so `shared_buffers = 64MB`, `max_connections = 40` and
   `huge_pages = off` take effect; then `select name, setting, pending_restart from pg_settings where pending_restart`
   returns no rows.
5. After the first deploy, remove the old variables (each deletion redeploys): `NEO4J_URL`, `NEO4J_USERNAME`,
   `NEO4J_PASSWORD`, `NEO4J_PLUGINS`, `HEAP_INITIAL_SIZE`, `HEAP_MAX_SIZE`, `PAGECACHE_SIZE`, `NODE_CSV_URLS`,
   `RELATION_CSV_URLS` (inspect the two CSV URLs for embedded credentials first), `YOU_API_KEY`. Keep the Neo4j
   service itself until the owner approves its removal (cutover track, phase 5).
6. Before 2026-12-01: Railway now warns that `railway.json` keeps working only until that date; translate it with
   `railway config migrate` and review the result.

### Roll back

- **App:** in Railway, redeploy the previous deployment of `islamicapps` (the July Neo4j build) from the deployments
  list, or revert the merge on `main` and push. Neo4j and its variables are still in place, so the old build runs as
  before; do not delete the `NEO4J_*` variables until the new build has been stable.
- **Data:** the production database can be reset to "nothing public" without losing anything:
  `npx tsx src/scripts/db/approve-preview.ts --revoke --by owner --reason "<why>" --database production --confirm-production`
  hides every report at once (the gate in `public_hadiths`). A bad load rolls back by itself (one transaction; the
  version row is marked `failed`).
- **Migrations:** expand only; `0009` adds an enum value and redefines one view, so the July build is unaffected.

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

## Owner decisions, fifth round (2026-11-21)

- The site went live on main at commit b00af72 on 2026-11-21.
- No development database. Work against production directly; the site is
  low traffic and breakage is acceptable. `islamicapps_dev` is to be retired.
  Keep the safeguards that protect data: additive migrations, transactional
  loads, data invariants, backups.
- Gap filling runs as a matrix of parallel agents, one per gap. Data-side
  lanes write only new files under their own directory and produce
  load-ready output with a load specification. One lane at a time owns the
  schema, migrations, projection and loader.
- Narrator names carry a Latin form beside the Arabic, names link to narrator
  pages, and English is rendered on detail pages.

## Owner decisions, sixth round (2026-11-21)

- Neo4j may be retired at any time. Take and verify the final dump first.
- Publication: claims are published as "AI-reviewed", with the review
  workflow and the citations documented and visible. Human review is not
  required to publish.
- Human review is plural: any item may carry reviews from many separate
  human reviewers. There is never a single reviewer or one overwritten
  status.
- The goal is discussion around every hadith from every side, driven by
  context: threads anchored to a precise context (a report, a telling, a
  chain, a name in a chain, an identity claim, a grading, a passage, a
  narrator, an event) and surfaced from every view that touches it.
- AI reviews are done by dedicated specialist reviewer agents that are cut
  off from context: each sees only a self-contained review packet and works
  from a saved, documented system prompt (`reviews/ai/prompts/`). Every
  review records the model that performed it, the prompt version and hash,
  and the time. Rule-based checks are recorded separately as procedures, with
  no model. "AI-reviewed" is never claimed for an item no reviewer saw.
- Narrator pages show a perspectives matrix: one row per source of a view
  (each rijal author and work, each critic quoted by name, the lexicon, any
  external dataset), grouped by tradition; columns are the aspects a view can
  speak to (verdict as written, generation, dates, places, teachers and
  students, notes). Cells hold the verbatim text with its locator; an empty
  cell means that source is silent. Disagreement is shown, never reduced to a
  consensus. Report gradings follow the same shape.
- One citation standard throughout. Every claim shown to a reader carries the
  same required record: the work (author, title, tradition); the edition or
  digital source as its own metadata names it; the locator (volume, page,
  entry, verse, or URL with retrieval date, or dataset version and record
  id); the verbatim passage relied on; the source short reference and
  licence; and the hash of the text it was checked against. A claim without
  one is labelled "not yet cited". The standard is defined in
  docs/review/citations.md and checked by a validator; every lane's output
  must pass it before it is loaded.
- Narrator biography: the page states whether any biography is available and
  from which sources, and what each covers; "no biography in any source the
  archive holds" is said plainly. Narrators are connected to events and
  places through cited passages. Timelines are drawn per perspective: one row
  per source or tradition for the same narrator, never merged, so agreement
  and difference are visible. The same citation standard applies.

## Neo4j retired (2026-11-21)

- Owner approved retirement after a verified dump. Final export is in the
  backup bucket under `neo4j-final/2026-11-21/` (626,938 nodes, 1,539,277
  relationships); all three objects were re-hashed by the session lead and
  match `docs/backups/neo4j-final-2026-11-21.manifest.jsonl`.
- Deleted on Railway: service `neo4j-hadith-graph-alltraditions` and volume
  `neo4j-volume`. Removed from the `islamicapps` service: `NEO4J_URL`,
  `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_PLUGINS`, `HEAP_INITIAL_SIZE`,
  `HEAP_MAX_SIZE`, `PAGECACHE_SIZE`, `NODE_CSV_URLS`, `RELATION_CSV_URLS`,
  `YOU_API_KEY`. The service keeps `DATABASE_URL`, `SITE_URL`,
  `NEXT_TELEMETRY_DISABLED`.
- Still to do in code: delete the Neo4j-era files nothing imports
  (`src/lib/db/neo4j*.ts`, `src/app/actions/graph-actions.ts`,
  `comparative-actions.ts`, the Neo4j scripts and tests) and the
  `neo4j-driver` dependency; remove `NEO4J_*` from `.env.local`.
- Backups: `db/2026-11-21/` and `db/2026-11-21-schema0011/` in the bucket;
  restore drill passed (docs/backups/README.md). The three locked curation
  files are still not backed up.
- Open operations items: restart Postgres once when no load is running
  (pending `shared_buffers`, `max_connections`); Postgres memory peaked at
  4.5 GB during loads against a 250 to 450 MB budget, to be re-measured at
  rest; `railway.json` conversion before 2026-12-01 drops the restart policy
  if applied as generated (see docs/backups/README.md operations notes).

## Specialist review pilot 1 (2026-11-21)

- Model `claude-opus-5-5`, fresh subagent per packet, packet staged alone.
- Narrator identity: 46 claims recorded (13 supports, 4 contradicts, 10
  contested, 19 insufficient evidence); hidden known answers 3 of 5.
- Report correspondence: 4 of 6 packets recorded at first attempt (21 pairs);
  two rejected by the recorder (inexact quotes; reading and outcome
  mismatch) and re-run with fresh reviewers.
- Finding: identity packets need each candidate's rijal passages and
  attested teachers and students.

## Names, identities and English pass (2026-11-21)

The owner's three problems with the live all-chains view, fixed (code uncommitted on `refactor/postgres-drizzle`;
production database already loaded). Detail: `src/db/AGENTS.md` §External identity and §Latin names,
`datasets/hadith-data/pg_export/AGENTS.md`, `DESIGN.md` change log.

- **Latin names.** Every chain name carries a Latin form where a source or rule gives one, computed in the projection
  with its basis (`chain_mentions.name_latin*`): Thaqalayn's English, the identified record's name, or a transliteration
  of the vowelled text or of curated name parts; otherwise Arabic alone. Coverage of public names: Sunni 86.4%, Imami
  90.0%, Zaydi 87.1%, Ibadi 56.0%.
- **Identities.** hadith-kg and Riwayat claims (366,007) loaded with their records as narrators (15,529) and an Imam
  register (12). Machine-reviewed now also on hadith-kg or Thaqalayn's annotation confirmed by the text, two sources
  agreeing (6,791) and the Imams' kunyas in Imami chains (9,561). Names with any identity (linking to a page): Sunni
  240,147 of 363,456, Imami 67,002 of 169,530, Ibadi 877 of 2,402, Zaydi 8 of 3,119.
- **English.** The family view, each telling and report lists show public English with the same label and credit as
  the report page, and "No English available yet" where none exists.

### Deploy (session lead)

1. Production is ahead of the deployed build and safe for it: migrations are additive; `public_chain_mention_candidates`
   still returns only the bases the deployed build knows; the deployed build shows the 10,658 newly public English texts
   and the new machine-reviewed links (merged in its diagram), and simply does not show Latin names or external
   claims until the new code ships.
2. Pick-up checks: `npx tsc --noEmit`; `DATABASE_URL=<production> npm run db:verify`;
   `npm run db:verify-data -- --database production --confirm-production`.
3. Commit, merge `refactor/postgres-drizzle` to `main`, push. No migration or load is needed at deploy.
4. Check live: `/hadith/k6/19122/chains` (Latin names, Imam link to `/narrator/narrator%3Aimam%3A6`, English under each
   telling), `/hadith/openiti/ibadi/rabi_0003%7C3%7CV01P006` ("No English available yet"),
   `/narrator/narrator%3Ariwayat%3AN0152717`, `/narrator/narrator%3Ariwayat%3AN0001038` (label notice).
5. Roll back the code by redeploying `b00af72`; the data needs no rollback for it. To return the data to `e2430eae…`,
   load `projection-v3` again (a full load) and re-record the preview approval.

### For the owner

- Check `datasets/hadith-data/pg_export/imam_kunya_conventions.json`: which kunya plus marker means which Imam. Bare Abu
  Jaʿfar (2,346 mentions), Abu al-Hasan (315) and Abu Muhammad (1) stay undecided candidates; say if bare Abu Jaʿfar
  should mean al-Baqir by convention.
- Two-part Thaqalayn labels (`أحمد بن محمد`, `محمد بن يحيى`, …) are not treated as label-like: 11,157 of the 14,398
  Imami mentions machine-reviewed through Riwayat rest on such labels (707 records). Say if they should be labels (then
  they stay candidates).
- The loader now runs with parallel query off (the container's `/dev/shm` is too small for the load's joins); a
  Postgres restart is still pending for the tuning in "Production state".

## OpenITI extraction fix (2026-11-21)

The corrected parse of al-Rabi, Musnad Zayd and Sahifat al-Rida (`datasets/hadith-data/extraction-quality/fixed/LOAD_STEPS.md`
followed) is in production; code is uncommitted on `refactor/postgres-drizzle`. Detail: `src/db/AGENTS.md` §OpenITI extraction
fields, `datasets/hadith-data/pg_export/AGENTS.md` §OpenITI report structure, `src/app/hadith/[id]/AGENTS.md`.

- **Loaded** (dataset version `bed23aaaaf16…`, projection `2026.11.21.5`, incomplete-curation preview build, preview approval
  re-recorded): hadiths +173 new, 1,728 updated (755 with new Arabic; the other 973 gained the new columns or lost the old
  machine English from the file), 9 retired (`zayd_0009 0045 0047 0140 0308 0430 0469 0610`, `rida_0002`). 99,447 reports
  (Ibadi 1,005, Zaydi 691, Imami 33,395 with the 205 Sahifat al-Rida reports). 1,531 confident splits, 370 low, 231 continuations,
  142 reports with 149 source notes. `db:verify` OK, `db:verify-data` OK (35 checks, 3 new for the new columns), reload not run.
- **Schema**: migration `0012_openiti_extraction_fields` (additive: `hadiths.sanad_ar`, `sanad_inherits_from`, `split_confidence`,
  `source_notes`; `public_hadiths` replaced with the same body so it exposes them). Already applied to production.
- **A retired id** answers 404 (the row is kept, `retired_at` set); no redirect.
- **Parser correction**: Sahifat al-Rida stays `Imami`. The first corrected parse said `Zaydi`, which would have changed every
  rida `record_id` (35 retired, 205 new under another tradition).
- **Rebuilt for the new Arabic**: unified CSV (incomplete-curation), report correspondence v1 (135,976 pairs, 54,934 members),
  external crosswalk and identity sidecars (hadith-kg, Riwayat; claims 366,241), Qur'an citations (`quran/`, validated),
  correspondence v2 (154,305 pairs; its `recall_v2.json` was not re-measured, the old one is in `output.20261121_1735.bak/`),
  `reconciled/openiti_extraction.jsonl.gz` (new). **Stale** (file-only, loaded nowhere, or more than one command):
  `reconciled/structure/*` (needs `--production-dump <csv>`), the Qur'an review worksheets and readings that cite OpenITI ids
  (`quran_review_worksheet_150.csv`, `quran_reading_80.csv`), `lsh_recall.json` of correspondence v1, and the machine-English
  candidates for OpenITI (`translation_candidates.csv` 31,652 -> 29,915 rows: the corrected parse does not carry `text_en`;
  the originals are in `*/translations.jsonl`, keyed by parsed id, never reuse for a changed hash).
- **Not done**: English for the 173 new and 755 changed reports (OpenRouter out of credit; the page says "No English available
  yet"); the release curation gate (`curation_manifest.json` is not ready: new ids have no reviewed English);
  `load-flow.test.ts` could not run (development database is at an earlier migration; see `src/db/load/AGENTS.md`).
- **Access-denied files**: `development/incomplete-curation/` held files an earlier sandbox account owned (`all_hadiths_shia.incomplete*`,
  `all_hadiths_clean.incomplete*`, `all_hadiths_unified.incomplete.csv`, `classical_narrator_gap.incomplete.csv`,
  `curation_manifest.incomplete.json`; also `datasets/hadith-data/curation_*.json|csv`). They were moved aside as
  `*.20261121_1630.bak` (still unreadable by this account) and regenerated, with Thaqalayn rebuilt from `shia-hadith/v2_books`
  (no `--no-shia`: the reusable gz was the unreadable one). The Imami rows came out identical (the load changed 0 Thaqalayn rows).

### Deploy (session lead)

1. Pick-up checks: `npx tsc --noEmit`; `DATABASE_URL=<production> npm run db:verify`;
   `npm run db:verify-data -- --database production --confirm-production`.
2. Commit, merge `refactor/postgres-drizzle` to `main`, push. The pre-deploy `migrate.mjs` finds 0012 already recorded.
3. Check live: `/hadith/openiti/ibadi/rabi_0001%7C1%7C` (matn «نية المؤمن…» alone, chain span under Isnad),
   `/hadith/openiti/ibadi/rabi_0001b%7C1%7C` ("Chain continues from No. 1"), `/hadith/openiti/ibadi/rabi_0225%7C225%7CV01P060`
   (Notes in the source edition, credited OITI), `/hadith/openiti/zaydi/zayd_0007%232%7C7%7CV01P064` (No. 7, part 2),
   `/hadith/openiti/zaydi/zayd_0009%7C9%7CV01P065` (404).
4. The deployed build (`6e67b2e`) is safe on this data: it ignores the new columns, shows `matn_ar` where present and the whole
   text for the 370 low-confidence reports.

### Rollback

- Code: redeploy `6e67b2e`; the data needs no change for it.
- Data: there is no `pg_dump` 18 here, so there is no one-command return to `bbafb2f1…`. Options: restore the bucket backup
  `db/2026-11-21-schema0011/` (docs/backups/README.md; loses the 0012 columns, which only the new code reads), or load the
  previous projection after rebuilding it against the 0012 catalog from the `*.20261121_162559.bak` parse files and
  `all_hadiths_unified.incomplete.csv.gz.20261121_1630.bak` (the loader refuses a projection whose header is not the live
  catalog, so `projection-v4` as it stands cannot be loaded). Curation rows before the load: `development/openiti-fix-2026-11-21/curation-dump-before/`.
- After any load into production, run `npm run db:approve-preview -- --database production --confirm-production --by owner
  --reason "..."` at once: a new current version has no override and `public_hadiths` is empty until it is recorded (this load: about a minute).

## Chain chronology guard (2026-11-21)

The owner's report: wrong teachers on narrator pages (ʿUmar b. al-Khattab, d. 23, listed as a student of al-Awzaʿi, ʿUbaydullah
b. ʿUmar b. Hafs and al-Faryabi). Detail: `src/db/AGENTS.md` §Chain chronology guard, `datasets/hadith-data/pg_export/AGENTS.md`
§Chain chronology, `src/db/queries/AGENTS.md` §Lexicon on public narrator pages.

- **Rule.** A machine-reviewed identity may not make an adjacent pair impossible on the lexicon's years (student born after
  teacher died; teacher born after student died; teacher died more than 60 years after the student). The projection withholds
  it (candidates kept, reason stored in `chain_mentions.identity_withheld_reason`); the view labels anything left impossible
  and the network drops it. Pairs between two occurrences of one narrator (a flattened tahwil) never form.
- **Loaded**: migration `0013_chain_chronology_guard` (additive) applied to production first, then projection `2026.11.21.6`
  (`development/openiti-fix-2026-11-21/projection-v6`, catalog `catalog-0013.json`), preview approval re-recorded. Curation rows
  before the load: `development/chronology-guard-2026-11-21/curation-dump-before/`; logs beside it.
- **Biography tab**: the lexicon's record (generation, dates, places, family, tags, credited MSD) first, then the per-narrator
  hadith detail. `narrator_bios` has 21 proposed, uncited rows, so no reviewed biography is public yet.

### Deploy

1. Order matters: `0013` before the code (the code reads `public_chain_links.identity_withheld_reason` and
   `narrator_lexicon_profiles.source_fields`). It is applied; the pre-deploy `migrate.mjs` finds it recorded.
2. Checks: `npx tsc --noEmit`; `DATABASE_URL=<production> npm run db:verify`; `npm run db:verify-data -- --database production
   --confirm-production`; `python -I datasets/hadith-data/pg_export/test_chain_chronology.py`;
   `npx tsx --conditions=react-server src/db/queries/__tests__/chronology-flows.test.ts` (private schema on the development
   server; does not migrate the development database).
3. Push to `refactor/postgres-drizzle` and `main`.
4. Live: `/narrator/narrator%3Arawi%3A3` lists no al-Awzaʿi, ʿUbaydullah b. ʿUmar or al-Faryabi under teachers;
   `/hadith/k6/28147/chains` shows «عمر» with "Identity withheld. Chronology: ..." and the K6 candidate.

### Rollback

- Code: redeploy `88b54f5`; it ignores the two new columns, and the 0013 view only removes impossible and seam pairs.
- Data: `projection-v5` cannot be loaded as it stands (its header lacks the two 0013 columns). To restore the withheld
  identities, re-export with `contest_chain` returning no withholdings (same ids: the load only rewrites the 522 changed
  mention rows) and load it, then re-record the preview approval at once.
- View: a new migration restoring the 0006 definition of `narrator_transmissions` (drop, create, two indexes). Never edit 0013.

## Chain builder round 2 (2026-11-22)

The isnad fix cycle's second round: two finished audits (`datasets/hadith-data/chain-audit/ibadi-zaydi/`, `imami/`) agree order
is right and chains are cut wrong. The builder is fixed, not rows. Detail: `src/db/AGENTS.md` §Chain builder,
`datasets/hadith-data/pg_export/AGENTS.md` §Chain builder. Logs and dumps: `datasets/hadith-data/development/chain-builder-r2-2026-11-22/`.

### Milestone 1: al-Rabi, Musnad Zayd, Sahifat al-Rida (projection `2026.11.22.1`)

- **Parser**: `RE_CONTINUATION_CHAIN` accepts «ومن طريق X»; 22 al-Rabi reports now declare their parent (text unchanged; old
  files `*.20261122_r2m1.bak`). The OpenITI sidecar now carries `matn_ar` and the projection reads it.
- **Schema**: `0014_chain_builder_openiti` (additive) applied to production before the load.
- **External claims** rebuilt against an interim projection without OpenITI claims (`EXTERNAL_SIDECAR_PROJECTION`); Sunni and
  Imami claims identical (364,579 rows), OpenITI 1,662 -> 1,551; claims are no longer aligned onto inherited mentions.
- **Loaded**: dataset version `2c42b08e…`, 16,655 rows changed, preview approval re-recorded at once. Sunni and Thaqalayn chains,
  mentions and candidates: 0 rows differ from projection `2026.11.21.6`.

Deploy: migration `0014` first (done), then push to `refactor/postgres-drizzle` and `main`; the pre-deploy `migrate.mjs` finds it
recorded. Live checks: `/hadith/openiti/ibadi/rabi_0332%7C332%7CV01P084` (inherited names, "From the earlier report's chain"),
`/hadith/openiti/imami/rida_0001%7C1%7CV01P439` (Imam chain), `/hadith/openiti/imami/rida_0003%7C3%7CV01P441`,
`/hadith/openiti/zaydi/zayd_0170%7C170%7CV01P167` (Imam register links), `/narrator/narrator%3Ariwayat%3AN0001547` (Jabir b. Zayd).

Rollback: code, redeploy `877b700` (it ignores the new column; the new basis reads as its raw name). Data: load
`development/openiti-fix-2026-11-21/projection-v6` again after re-exporting it with the 0014 catalog (its chain_mentions header
lacks `inherited_from_mention_id`, so re-export from the `*.20261122_r2m1.bak` sidecars), then re-record the preview approval.
Never edit 0014; a later migration restores the two view bodies of 0013/0011 if needed.

### Milestone 2: Imami chains (projection `2026.11.22.4`)

- **Schema**: `0015_chain_builder_imami` (additive: `chains.suspension`; `public_chain_links.chain_suspension`; `narrator_transmissions`
  recreated with the anonymous-gap guard) applied to production before the load.
- **External claims** rebuilt twice against interim projections without Thaqalayn claims; non-Imami claims identical except
  3 rows of `rabi_0253` (the milestone 1 claims were built before its «صاحب رسول الله» fix).
- **Loads**: the first attempt (`2026.11.22.2`) failed the new inherited-mention check (it required `hadiths.sanad_inherits_from`,
  which Thaqalayn reports do not have) and rolled back; the second (`2026.11.22.3`) was started before that check was fixed and
  failed the same way; `2026.11.22.4` also keeps the formula-only chains («وبهذا الإسناد» with nothing after it) so the page
  can say the report relies on the previous one. Preview approval re-recorded after the successful load.

Deploy: `0015` is applied; push to both branches. Live: `/hadith/thaqalayn/07b3c9089c6fc4b7ed88073a/chains` (al-Kafi 3/4/16/1,
two routes), a Faqih «و روى» report `/hadith/thaqalayn/000fabb7bcb6211feb2d377f` ("The compiler gives his route ... elsewhere"),
`/hadith/thaqalayn/0034cac887c15c7dfc9a3956` ("Chain relies on the previous report"), `/hadith/thaqalayn/05071e9f53ff6d02c6eb4590`
("Unnamed transmitter").

Rollback: code, redeploy the milestone 1 commit (it ignores `chains.suspension` and `chain_suspension`). Data: load
`development/chain-builder-r2-2026-11-22/projection-m1` again after re-exporting it with the 0015 catalog (its `chains.csv`
lacks `suspension`), with the `*.20261122_r2m2.bak` external sidecars, then re-record the preview approval.

### Milestone 3: Sunni chains (projection `2026.11.22.5`; audit `chain-audit/sunni/`)

- **Schema**: `0016_chain_builder_sunni` (additive: basis `edition_identification`, `chains.missing_link_after`,
  `public_chain_links.chain_missing_link_after`, `public_chain_mention_candidates_v2`) applied to production before the load.
- **External claims** rebuilt against an interim projection without Sunni claims; non-Sunni claims identical apart from 3 rows in
  two Thaqalayn reports whose formula-only chains returned in `2026.11.22.4`.
- **K6 source index**: aligned to the bundle's branches as before, then carried through the re-cut by each mention's origin
  (0 more reports lose their alignment; 1 differed before and still does).
- **For the owner** (not changed): 56 medium order-reversed rows, 105 Prophet-as-mention rows, the lexicon's death year 354 for
  `narrator:rawi:38420` (a shaykh of Abu Dawud, d. 275), `narrator:rawi:27536` and `25603` (likely one person, two records), and
  the 95 medium «أبي» rows after Ibn Numayr (`identity_rule:abdallah_ibn_numayr_father`).

Deploy: `0016` is applied; push to both branches. Live: `/hadith/k6/28195/chains` (two routes), `/hadith/k6/28147/chains`
(«عمر» = ʿUmar b. ʿAbd al-Wahid, "named by a printed edition's note", cited), `/hadith/k6/18025/chains`,
`/narrator/narrator%3Arawi%3A3` (no al-Awzaʿi, ʿUbaydullah b. ʿUmar or al-Faryabi among teachers).

Rollback: code, redeploy the milestone 2 commit (it ignores the new column; the new basis shows its raw name). Data: load
`development/chain-builder-r2-2026-11-22/projection-m2c` after re-exporting it with the 0016 catalog and the
`*.20261122_r2m3.bak` external sidecars, then re-record the preview approval.

## Chain builder round 3 (2026-11-22)

The round 2 re-check (`datasets/hadith-data/chain-audit/round2/`, README first) found round 2 helped Imami, al-Rabi, Zayd and
Rida but not Sunni (strict defects 17.3% against 10.7%), with regressions: Sunni seam re-cuts defective 27/30, 162 names
trimmed after «سمعا/حدثتني», 190 Ibadi/Zaydi reports with a written chain and none stored, Rida chains past the named speaker.
Rules and rationale: `datasets/hadith-data/pg_export/AGENTS.md` §Chain builder and §Sunni chains (round 3 bullets). Logs, dumps,
projections: `datasets/hadith-data/development/chain-builder-r3-2026-11-22/`. No migration this round (catalog `0016` unchanged).

Every export now runs `python -I datasets/hadith-data/pg_export/check_projection.py <projection>` before the load (~10 s): the
file-level chain invariants of `db:verify-data`, so a nine-minute load cannot fail on one of them.

### Milestone A: regressions (projection `2026.11.22.6`)

- **Sunni**: a seam splits only at a route head and only when a tested rule gives the earlier route its shared tail; any route
  stopping at «ح» takes its shared tail; the extractor is re-run past a wording attribution or a convergence word; a transmission
  verb inside a surface is a link; asides («وأنا أسمع», «في حديث X», «الآخران») are not names.
- **al-Rabi, Musnad Zayd**: a low-confidence report that opens with the work's fixed isnad gets that chain (148 of 190).
- **Sahifat al-Rida**: a continuation stops at the speaker it names (13 chains shortened, 3 regain the whole chain).
- **External claims** rebuilt against an interim projection without Sunni and OpenITI claims (`reconciled-interim-a`,
  `projection-a-interim`; sidecars backed up as `*.20261122_r3a.bak`): 368,575 -> 375,415 claims. Imami chains and candidates
  identical; 44 Imami mentions lose a standing identity because Riwayat N0152816 and N0002797 now meet the "name held by several
  ids" label rule (label status counts claims across the corpus).
- **Loaded**: dataset version `83a827a8…`, 72,277 rows changed (chains +29 ~5,413 retired 807; mentions +11,152 ~12,543 retired
  4,351; candidates +16,768 ~5,514 retired 9,834), 437 s, every check passed; preview approval re-recorded at once
  (`approve-a.log`). Curation rows before the load: `curation-dump-before-a/`.
- **Numbers**: short Sunni chain (<= 3) beside a long sibling (>= 5) in K6: 679 before round 2, 817 after it, 372 now. Sunni standing
  identities 132,358 -> 135,381 (every collection up), Ibadi 484 -> 525, Zaydi 2,452 -> 2,566, Imami 27,788 -> 27,744;
  `narrator_transmissions` 27,111 -> 27,586 rows.

Deploy: no migration and no app code change; push to both branches. Live: `/hadith/k6/7805/chains` (both routes to Ibn ʿAbbas),
`/hadith/k6/7852/chains` (al-Shaʿbi on both routes), `/hadith/k6/4489/chains` (one route, no false seam), `/hadith/k6/28195/chains`
(two routes), `/hadith/openiti/ibadi/rabi_0094%7C94%7CV01P029` (Abu ʿUbayda > Jabir > unnamed «بلغني»),
`/hadith/openiti/imami/rida_0031%2323%7C31%7CV01P490` (stops at ʿAli b. al-Husayn).

Rollback: data, load `development/chain-builder-r2-2026-11-22/projection-m3` again (exported with the same `0016` catalog, so it
loads as it stands), then re-record the preview approval; the `*.20261122_r3a.bak` sidecars restore the external claims it was
built with. Code: the builder change is export-time only; `40264df` rebuilds `projection-m3`.

### Milestone B: remaining patterns (projection `2026.11.22.7`)

- **Sunni surfaces** (re-check pattern 3): a clause after a name goes, the name stays (`clause_trim`: «زرارة بن أوفى يحدث»,
  «عائشة أنها», «الحارث بن مسكين قراءة عليه»); a surface that opens with one is no name, except «قال/قالت X». Chapter headings
  («باب …») stored as chains are gone. 40 sampled trims: no name lost.
- **Imami** (pattern 6): Thawab al-Aʿmal is re-read with its Persian ya/kaf folded for matching only (stored letters unchanged);
  a lone «و», «و قد روى», a leading «حدثني», «ره» and an Imam's words after his name are not names; a branch opening with a
  sentence that names nobody is matn (Amali al-Saduq 93: 192 chains -> 0); the Imam the text names after the last stored link is
  added (486).
- **«جميعا»** (pattern 7): commas and «؛» allowed; al-Kafi's «A عن B و C عن D عن E» with two of al-Kulayni's shaykhs is two routes
  meeting at E (Kafi 19 now matches Noor 118532); the hanging group keeps its own letters.
- **«غير واحد»** (pattern 8) is one unnamed collective in both traditions.
- **Not done**: concatenated isnads (pattern 9, 400 mentions in 181 reports): telling where a second isnad starts needs the
  compiler's route list, and a count rule would cut true long chains.
- **External claims** rebuilt against an interim projection without Sunni and Thaqalayn claims (`reconciled-interim-b`; sidecars
  backed up as `*.20261122_r3b.bak`): 375,415 -> 374,373 claims. OpenITI chains, mentions and candidates identical to milestone A.
- **Numbers** (production `2026.11.22.5` -> A -> B): Sunni mentions carrying a verb, aside or clause word 6,699 -> 5,376 -> 902;
  Sunni «غير/احد» halves 233 -> 48; Imami lone «و» 785 -> 1, «حدثني» inside a name 459 -> 0, «ره» 549 -> 11, «غير/احد» halves
  522 -> 31, reports with more than 30 chains 1 -> 0; K6 short-beside-long 817 -> 372 -> 337. Standing identities: Sunni 135,381 ->
  136,551, Imami 27,744 -> 28,515 (Ibadi 525, Zaydi 2,566 unchanged); `narrator_transmissions` 27,586 -> 27,992 rows.
- **Loaded**: dataset version `62bcf443…`, 74,282 rows changed (chains +18 ~2,014 retired 2,693; mentions +1,604 ~23,304 retired
  12,531; candidates +9,200 ~3,624 retired 10,935), 505 s, every check passed; preview approval re-recorded at once (`approve-b.log`).
  Curation rows before the load: `curation-dump-before-b/`.

Deploy: no migration and no app code change; push to both branches. Live: `/hadith/thaqalayn/1adbb3bc592355214cdb0be0/chains`
(Kafi 19: two routes meeting at Ibn Mahbub), `/hadith/thaqalayn/f02c69a82883b8f2aa7763ce/chains` (Thawab: «سعد بن عبد الله» back, no
matn), `/hadith/thaqalayn/a1472a2b00e9f4b54e31e78f/chains` («غير واحد من أصحابنا», one unnamed collective), `/hadith/k6/27269/chains`
(no «أنا أسمع» route, «الحارث بن مسكين» without «قراءة عليه»).

Rollback: data, load `projection-a` again (same catalog), then re-record the preview approval; `*.20261122_r3b.bak` restores the
external claims it was built with. Code: redeploy the milestone A commit (`cc91b0e`); the builder change is export-time only.

For the owner (not changed, round 3): al-Kafi 7 (`8a5b2230`) has the Kafi 19 shape and now reads two routes meeting at Ibn Mahbub
(Noor could not be reached for it); 42 al-Rabi/Zayd reports whose opening is not the work's fixed shape («قال الربيع عن X», «سألت
زيدا», the book's later sections) still store no chain; Faqih «وَ قَالَ الصادق» statements whose only stored mention was «و» now
have no chain (the extractor never read the Imam; adding him from the text is the same kind of rule as the deferred «قال سألت أبا
عبد الله»); the Ibn Numayr «أبي» stitch (`identity_rule:abdallah_ibn_numayr_father`) still waits on your ruling.

### Milestone B2: follow-up (projection `2026.11.22.8`)

The live check of milestone B found a short route it introduced (`k6:14609`: «ابن نمير > أبي» beside «ابن نمير > محمد بن بشر >
…»): the co-transmitter test located «أبي» at its first occurrence in the text («أبو بكر بن أبي شيبة»). It now uses the chain-ordered
spans, and one written name twice in a row collapses to one mention (relations excepted). 10 Sunni reports change; Imami and OpenITI
rows are identical to B. External claims rebuilt as before (`reconciled-interim-b2`, sidecars backed up as `*.20261122_r3b2.bak`).
- **Loaded**: dataset version `f153d736…`, 1,951 rows changed (92 Sunni reports: 82 self-loops such as «الزهري > الزهري» or «أبي
  معاوية > أبو معاوية» collapsed, the rest co-transmitter routes completed), 422 s, every check passed; preview approval re-recorded
  at once (`approve-b2.log`). Sunni standing identities 136,551 -> 136,549; `narrator_transmissions` 27,992 -> 27,993.
  Rollback: load `projection-b` again, then re-record the approval.

## Chain structure gate (round 4, 2026-11-22)

Three rounds of builder rules left the Sunni strict defect rate at 10.7% -> 17.3% -> 18.0%, so round 4 gates what is asserted
instead: every chain is `checked_by_rule` or `uncertain` with reasons; an uncertain chain is shown as stored with one plain line
and forms no teacher-student pair. Detail: `src/db/AGENTS.md` §Chain structure gate, `datasets/hadith-data/pg_export/AGENTS.md`
§Chain structure gate, measurement and operating point `datasets/hadith-data/chain-audit/structure-gate/README.md`. Logs, dumps,
projection: `datasets/hadith-data/development/chain-structure-gate-2026-11-22/`.

- **Schema**: `0017_chain_structure_gate` (additive: `chains.structure_status`, `structure_reasons` and a check;
  `public_chain_links` appends `chain_structure_status`, `chain_structure_reasons`; `narrator_transmissions` recreated with
  `structure_status IS DISTINCT FROM 'uncertain'`, so rows loaded before the gate kept their pairs until the load). Applied to
  production before the export (`prod-migrate-0017.log`); catalog `catalog-0017.json`.
- **Projection `2026.11.22.9`**: 110,999 chains (258 retired by the gate: Kitab al-Duafa and Risalat al-Huquq 238, chapter
  headings 20; one external claim on a retired Duafa chain dropped, counted; «غیر واحد» with Persian letters merged: 1 chain).
  Checked by rule: Sunni 55,821 of 76,262 (73.2%; K6 text works 68.0%, Sahih Muslim 47.4%, Pure Canon 80.9%), Imami 20,348 of
  33,229 (61.2%; al-Kafi 91.3%, the 15 small works 0%), al-Rabi 95.0%, Musnad Zayd 99.3%, Sahifat al-Rida 99.5%.
  `check_projection.py` passed before the load.
- **Gate on the read verdicts** (round-3 random sample, strict, before -> among checked): Sunni 18.0% -> 2.6%, K6 25.4% -> 4.3%,
  Imami 17.0% -> 3.2%, al-Rabi 16.1% -> 7.7% (cannot be shown below 5%), Zayd 2.5% -> 0%, Rida 0% -> 0%.

### Deploy

1. Order: `0017` before the code (the code reads `public_chain_links.chain_structure_status`). It is applied; the pre-deploy
   `migrate.mjs` finds it recorded.
2. Checks: `python -I datasets/hadith-data/pg_export/test_chain_structure.py`; `npx tsc --noEmit`; `DATABASE_URL=<production> npm
   run db:verify`; `npm run db:verify-data -- --database production --confirm-production`; `npx tsx --conditions=react-server
   src/db/queries/__tests__/structure-flows.test.ts`.
3. Push to `refactor/postgres-drizzle` and `main`.
4. Live: `/narrator/narrator%3Arawi%3A3`; `/hadith/k6/10685/chains`, `/hadith/k6/19535/chains`, `/hadith/k6/5344/chains` show
   "The reading of this chain's routes has not been checked ..." with reasons; a clean Bukhari chain (`/hadith/k6/4643/chains`)
   shows no such line.

### Rollback

- Code: redeploy the round-3 commit (`f6a73fe`); it ignores the two new columns, and the network stays gated (the view is data).
- Network only: a new migration recreating `narrator_transmissions` with the 0015 body (drop, create, two indexes). Never edit 0017.
- Data: an export from before this round cannot load (the loader refuses a header without the two 0017 columns). To restore the
  retired Duafa, Huquq and heading chains, export from this commit with `PROSE_WORKS` empty and `retire_reason` returning None
  (and, for an ungated network without a migration, `GATE_REASONS` empty), load it, then re-record the preview approval at once.
  Curation rows before the load: `curation-dump-before/`.

## Gate recalibration (round 5, 2026-11-22)

Round 4's independent reading (`datasets/hadith-data/chain-audit/round4/README.md`, 520 items from production) found the gate's published
rates were in-sample and too low: strict defects among checked chains Sunni 8.3% (4.6-14.7), six-books 10.6%, Imami 4.0% (al-Faqih 4/20), Pure Canon
2.9%, al-Rabi 5.0%, Rida 4.0%, Zayd 0/25; pair precision 149/150 = 99.3%; 40 of 60 withheld chains were correct. `/method`
(`src/lib/review/procedures.ts`) and `chain-audit/structure-gate/README.md` now say so, and say the recalibrated gate has no out-of-sample rate yet.
Detail, tables and the per-change ablation: `datasets/hadith-data/chain-audit/round5/README.md`; rules: `pg_export/AGENTS.md` §Gate recalibration.

- **Changes** (`pg_export/chain_structure.py`; no migration): the 15 small Imami works are no longer withheld as a block (`UNCHECKED_WORKS` is empty);
  `FEATURES` adds shape tests (Faqih sayings and asker+Imam links, «/» links, «حدثناه», third-person hearing verbs after the last link, «وعن» joining two
  Imami routes, an inherited chain's own hearing verb) and exemptions (Pure Canon glosses, Pure Canon chain-field tails, label formulas); `sibling_skips_link`
  is a new gate reason; `MANY_ROUTES` stays 3 (narrowing releases 18-22% defective chains). Split: tuning = rounds 2/3, held-out = round 4's 370 readings;
  the tightenings were read from round 4, so their held-out gain is by construction. Tests: `test_chain_structure.py` (`RoundFiveRecalibration`, real round-4
  rows in `chain-audit/round5/fixtures.json`).
- **Projection `2026.11.22.10`** (dataset version `bc798caea6e4...`): same 110,999 chains and mentions, only status and reasons moved. Checked by rule:
  88,349 of 110,999 (79.6%, was 77,630 = 69.9%); Sunni 58,287 (76.4%; six-books 67.6%, Pure Canon 89.4%), Imami 28,602 (86.1%; al-Kafi 91.3%, al-Faqih 81.2%),
  al-Rabi 94.9%, Zayd 99.3%, Rida 98.5%. 11,925 chains released, 1,206 newly withheld. `check_projection.py` passed before the load; the load ran in
  409 s with the loader's own invariants green and the approval was re-recorded at once (`approve.log`).
- **Network**: `narrator_transmissions` 25,465 -> 25,893 rows (Sunni 22,263 -> 22,578, Imami 3,189 -> 3,302; 502 pairs gained, 74 lost). 134 narrators gained a
  first teacher or first student, 13 lost all teachers and 19 all students. 70 of the 502 new pairs read against the Arabic: 70/70 adjacent.
- Logs, projection, curation dump, the before/after pair snapshots: `datasets/hadith-data/development/gate-recalibration-2026-11-22/`. Round-5 scripts
  (`recalibrate.py`, `new_pairs.py`, `pairs_snapshot.cjs`, `dump_curation.cjs`, `regained.cjs`) live in `chain-audit/round5/`.

### Rollback

- Load `development/chain-structure-gate-2026-11-22/projection` (projection `2026.11.22.9`, the round-4 gate) and re-record the preview approval at once;
  or restore the gate by putting the 15 works back in `UNCHECKED_WORKS` and emptying `FEATURES` / `GATE_REASONS - {sibling_skips_link}` in `chain_structure.py`,
  then export, check, load, approve. Curation rows before the load: `curation-dump-before/`.
- Next measurement: a round 6 reading of fresh chains (passed, withheld, pairs) is the only way to put a rate on the recalibrated gate.


## Machine translation publish (2026-11-22)

The owner topped up OpenRouter and asked for the translations to be finished and shown. Detail: `datasets/hadith-data/diagnostics/translation-run-2/README.md`
§Resume; publication path `src/db/AGENTS.md` §Public English and `datasets/hadith-data/pg_export/AGENTS.md` §Machine English overlay; model record
`datasets/hadith-data/model_registry.json`, `docs/models.md`. Logs, projection, curation dump: `datasets/hadith-data/development/machine-english-2026-11-22/`.

- **Translation**: `tencent/hy-mt2-30b-a3b` (every response returned that exact id, provider `Tencent`) over the 33,420 public reports with no public English. The three
  corrected OpenITI works first, from their current text (al-Rabi 1,004, Musnad Zayd 688, Sahifat al-Rida 205 reports), then the rest. 33,307 reports carry a gated draft
  (Sunni 30,684, Ibadi 1,004, Imami 931, Zaydi 688); 113 stay without English (91 failed the screen twice, 22 not translatable). Spend US$0.7767 (journal) and US$0.8767 in all
  with the scorer, measured on the key's own usage (`GET /api/v1/key`: 2.0295 -> 2.9062), against a US$15 cap; 4.88 million tokens.
- **Publication** (smallest path, no candidate table): the projection writes the drafts as `translations` rows (`state machine_unreviewed`, `model`, `provenance_source`) through
  `pg_export/machine_english.py`, which re-gates each one; source-provided English always wins (a report has one English row); a failing row was replaced in place (731 rows).
  `0018_machine_english_gate` (additive) makes the view require `model` and `provenance_source` for the machine branch; `db:verify` and `db:verify-data` check it.
- **Projection `2026.11.22.11`** (dataset version `6df54aa39ff7...`): translations 66,776 -> 99,352 (+32,576 inserted, 731 updated); the loader's 46 invariants passed; the approval was
  re-recorded at once (`approve.log`). Production now: 99,437 public reports, 99,324 with English (33,307 machine), 113 without.
- **Read of 40 random drafts** (10 per tradition): 5 meaning-level errors (Sunni 3, Zaydi 2), Ibadi 0; worst: «ردوا السائل» ("give the beggar") rendered "They rejected the liquid".
  The page's label says "Unreviewed machine translation (tencent/hy-mt2-30b-a3b)"; nothing says it is reliable.
- **Scorer** (`qwen/qwen3.7-flash`, 1,901 corrected OpenITI reports, US$0.0995): 1,898 scored; 1,195 (63%) score 3 on all three axes; results in `extraction-quality/output/score_summary_corrected.json`. Parsing was not changed.

### Deploy

1. Order: `0018` first (applied to production before the load, `prod-migrate-0018.log`), then the load, then the approval; no app code changed, so no redeploy is needed for the data to show.
2. Re-run later: `python -I datasets/hadith-data/diagnostics/translation-run-2/translate_gap_fill.py snapshot|run|finalize ...` (resumable, journals the `usage.cost` of every call; a rerun never pays for a report
   whose Arabic hash already has a final event), then `finalize --output datasets/hadith-data/machine_translation_candidates/machine_english_overlay.jsonl.gz`, then the export (`--machine-english` defaults to that file),
   `check_projection.py`, `npm run db:load -- --bundle <dir> --database production --confirm-production`, `npm run db:approve-preview -- --database production --confirm-production --by owner --reason "..."` at once,
   `DATABASE_URL=<production> npm run db:verify`, `npm run db:verify-data -- --database production --confirm-production`.
3. Live: an al-Rabi, a Zayd, a Rida and a Pure Canon (Ahmad) report show "Unreviewed machine translation (tencent/hy-mt2-30b-a3b)" credited to SWI; Bukhari `/hadith/k6/4643` shows its source-provided English with no machine label.

### Rollback

- Hide machine English at once, no load: `update collection_rights set english_policy = 'source_provided_allowed' where retired_at is null and english_policy::text = 'source_provided_and_machine_allowed'`
  (the view's machine branch needs the machine policy); undo by setting it back (`npm run db:record-rights -- --database production --confirm-production`).
- Remove the rows: load `development/gate-recalibration-2026-11-22/projection` (projection `2026.11.22.10`; the 32,576 machine rows leave the projection and are retired, the 731 replaced rows return to
  their old failing text), then re-record the approval at once. Curation rows before this load: `development/machine-english-2026-11-22/curation-dump-before/`.
- Never edit `0018`; a later migration restores the 0009 view body if the gate must be dropped.

## Chain fix pipeline integration and compiler ruling (2026-11-22)

Two lanes in one load. (A) The chain-fix pipeline (`docs/review/chain-fix-pipeline.md`, all twelve checklist steps) is integrated and
**applies nothing yet**: no reading has been submitted; the overrides file is absent. (B) Owner rulings of 2026-11-22: the compiler heads
every chain of his work; Abu ʿUbayda's own record in Musnad al-Rabiʿ; the bare kunya rule in every tradition. Detail: `src/db/AGENTS.md`
§Chain fixes, §Compiler as first transmitter; `datasets/hadith-data/pg_export/AGENTS.md` (same sections and §Bare kunya rule);
`reviews/ai/AGENTS.md` §Chain fixes; numbers and readings `datasets/hadith-data/chain-audit/compiler-ruling/README.md`. Logs, projection,
snapshots, curation dump: `datasets/hadith-data/development/compiler-chain-fix-2026-11-22/` (local).

- **Schema**: `0019_chain_fixes_compiler` (six chain-fix tables, `chains.chain_fix_id`/`compiler_narrator_id`/`compiler_link`, the two
  fix statuses, `work_register`, `public_chain_links` and `public_chain_fix_labels`, `narrator_transmissions` with the feeding guard and
  compiler pairs) and `0020_chain_fix_reader_v3_view` (view `text_and_context`), both additive, applied to production before the export
  (`prod-migrate-0019.log`, `prod-migrate-0020.log`). Every chain, mention and candidate row and the whole network hashed identical
  before and after the migration (`rows-hash-before-0019.json`, `rows-hash-after-0019.json`).
- **Projection `2026.11.22.12`** (dataset version `dbff1b417a74...`): 124,645 rows changed, 525 s, every loader check passed, approval
  re-recorded at once (`approve.log`). Chains: only `compiler_narrator_id`/`compiler_link` (and `missing_link_after` on 10 Sunni chains,
  from identities) changed; `chain_fix_id` is null on all 110,999; structure statuses identical (88,349 checked). Mentions: 5,250 rows,
  identity and Latin columns only; no surface or position moved (`chain-audit/compiler-ruling/row_diff.json`).
- **Network**: `narrator_transmissions` 25,893 -> 27,659 (Sunni 22,578 -> 24,264, Imami 3,302 -> 3,373, Ibadi 11 -> 21, Zaydi 3 -> 4);
  2,584 compiler pairs; 802 pairs lost to the bare kunya rule. 1,347 narrators gained a first student, 13 a first teacher; 112 lost all
  teachers and 84 all students (kunya rule). Standing identities: Sunni 136,549 -> 132,215, Imami 28,489 -> 28,467, Ibadi 525 -> 1,303,
  Zaydi 2,566. Readings: 30/30 compiler pairs right, 30/30 kunya gains right, 28 of 30 kunya losses removed a right identity (owner
  decision needed, `README.md` §3).

### Operating the fix pipeline (once a batch is judged)

1. Readers write outputs; `chain-reader/v3/triage_v3.py`, then `v3/to_submission.py` (envelopes) — see `v3/batch-001/RUN.md`.
2. `npx tsx reviews/ai/tools/chain-fix-submit.ts --envelope <e> --reports <private reports> [--database production]` (check with
   `--check-only` first); `npx tsx reviews/ai/tools/chain-fix-decide.ts` writes `state.json`, `queue.json` (accepted, held, disputed)
   and `datasets/hadith-data/chain-fixes/accepted_overrides.jsonl.gz`.
3. `npm run db:chain-fixes -- --database production --confirm-production --dry-run`, then without `--dry-run`: mirrors the store into
   the tables and writes each accepted fix (one transaction per report, under the data-write lock). Never during a load.
4. Commit the store and the overrides file; the next export replays them (`counts.chain_fixes`).
5. Final review: `npx tsx reviews/ai/tools/chain-fix-review.ts --fix <id> --decision confirmed|rejected --reviewer <name> --note ...`,
   then `npm run db:chain-fixes -- ... --revert-rejected` in the same sitting. Proposals: `chain-fix-status.ts --proposals`,
   `chain-fix-review.ts --proposal <id> --decision accepted|rejected`.
6. Lifting the network exclusion for one work (owner only, after its agreed-reading error rate is published on `/method`):
   `update chain_fix_work_settings set read_by_model_in_network = true, note = '<measurement and date>', updated_at = now(), updated_by = '<name>' where collection_id = '<collection>'`,
   then `select refresh_network()`.

### Deploy

1. Order: `0019`, `0020` (applied), the load (done), the approval (done); then push the code to `refactor/postgres-drizzle` and `main`
   (the chain view reads `chain_compiler_*` and `public_chain_fix_labels`; the pre-deploy `migrate.mjs` finds both migrations recorded).
2. Checks: `npx tsc --noEmit`; `npm run build`; `DATABASE_URL=<production> npm run db:verify`; `npm run db:verify-data -- --database production --confirm-production`;
   `npx tsx reviews/ai/tools/__tests__/chain-fix.test.ts`; `npx tsx --test src/db/ops/__tests__/chain-fix-apply.test.ts`; the Python suites in
   `pg_export/`, `chain-fixes/`, `chain-reader/`.
3. Live: an al-Rabiʿ chain (`/hadith/openiti/ibadi/rabi_0021%7C21%7CV01P011/chains`) reads al-Rabiʿ (compiler, not written) -> Abu ʿUbayda (own
   record) -> Jabir b. Zayd; `/narrator/narrator%3Awork%3Aal-bukhari` lists teachers; `/narrator/narrator%3Arawi%3A3` shows no al-Awzaʿi;
   `/method#chain-fix-agreement`, `#compiler-of-the-work`, `#identity-bare-kunya`.

### Rollback

- Bare kunya rule only: `KUNYA_RULE_AUTHORITIES = {}` in `pg_export/external_identity.py` (the OpenITI demotion of round 2 does not return),
  export, `check_projection.py`, load, approve.
- Compiler heads only: empty `compilers` in `pg_export/work_register.json`, export, load, approve (the view forms no compiler pair once the
  columns are null). Abu ʿUbayda: empty `named_in_full`.
- Everything in the data: load `development/machine-english-2026-11-22/projection` after re-exporting it with the 0019 catalog (its `chains.csv`
  lacks the three 0019 columns), then re-record the approval. Curation rows before this load: `curation-dump-before/`.
- Code: redeploy `f9cc5e1` (it ignores the new columns and views). Never edit 0019 or 0020; a later migration restores the 0017 body of
  `narrator_transmissions` if compiler pairs must go without a load.

## Bare kunya rule narrowed (2026-11-22)

The first form of the ruling (`9532839`: one carrier in the work's source, every work) withheld 4,431 Sunni and Imami identities the sources assert
per report; 28 of 30 read were right, and Musnad Ahmad's «أبي هريرة» failed the ruling's own example. Four forms were measured on those mentions
(`datasets/hadith-data/chain-audit/compiler-ruling/README.md` §3a, `kunya_options/`): (a) the rule only in the three OpenITI works, (b) 90, 95 or
98 percent dominance, (c) dominance or chronology support. A stratified fresh reading of 135 (not the 30 of before): every stratum at 90 percent
dominance or more 90/90 right, the low stratum 39/45; (b) and (c) withhold 557 to 2,298 right identities to keep out about 74 to 159 wrong ones,
so **(a) ships**. Detail: `pg_export/AGENTS.md` §Bare kunya rule; public rule `identity-bare-kunya` (`/method`) rewritten, version `2026.11.22.1`.

- **Projection `2026.11.22.13`** (dataset version `54f7591d915d...`): 12,681 rows changed, 553 s load; every loader check passed; approval re-recorded at
  once (`development/bare-kunya-narrowed-2026-11-22/approve.log`). Against `.12` only identity columns of mentions (4,472 rows: narrator, resolution,
  method, confidence, link kind, withheld reason, Latin name) and, on chains, `missing_link_after` (10, from identities) and the compiler head of three
  Abu Dawud chains changed (`kunya_options/table_diff.json`; the other 21 tables identical). Against `.11` (before the ruling) Sunni and Imami standing
  identities are identical row for row; only the OpenITI changes remain (Ibadi 525 -> 1,303).
- **Standing identities** `.12` -> now: Sunni 132,215 -> 136,549; Imami 28,467 -> 28,489; Ibadi 1,303 -> 1,303; Zaydi 2,566 -> 2,566.
  **Teacher-student pairs** (`narrator_transmissions`): 27,659 -> 28,468 (Sunni 24,264 -> 25,068, Imami 3,373 -> 3,378, Ibadi 21, Zaydi 4); 815 pairs gained,
  6 lost to the chronology guard; 112 narrators regained teachers, 86 regained students, 1 lost his only teacher.
- **Found, not changed**: three Abu Dawud chains (`chain:k6:15470:0000`, `15600`, `18811`) read «أبو داود» (al-Tayalisi) as Abu Dawud al-Sijistani, the
  compiler, so the compiler head (direct) is no longer added to them (3 pairs); the source's assertion is wrong there (read verdicts in `reading_135.tsv`).
- Machine English label (owner, same day): "Unreviewed machine translation. May contain errors that change the meaning; the Arabic is authoritative."
  (`MACHINE_ENGLISH_LABEL` in `src/lib/sources/report-credit.ts`); the model stays in the credit line (`englishReference`), SWI credit kept.
- Housekeeping: `chain-reader/analysis-v2/`, `chain-reader/v3/batch-001/{packets,outputs,triage,RUN.md,draw.json}` committed; `v3/batch-001/private/` is
  git-ignored; `v3/to_submission.py` no longer refuses inherited-link readings nor re-validates the v1-shaped copy (the submit tool reads `reader_output_v3`).

### Deploy

1. Data is loaded and approved (`prod-load.log`, `approve.log`); then push the code to `refactor/postgres-drizzle` and `main` (label, `/method` text).
2. Checks run: `npx tsc --noEmit`; `npm run build`; `npm run db:verify`; `npm run db:verify-data -- --database production --confirm-production` (54 checks pass); Python suites; review and glossary tests.
3. Live: a Musnad Ahmad chain with «أبي هريرة» (`mention:pure-canon:pc_87025:0000:0005`) shows Abu Hurayra; `rabi_0021` reads al-Rabiʿ <- Abu ʿUbayda (own record) <- Jabir b. Zayd;
   `/narrator/narrator%3Arawi%3A3` lists no al-Awzaʿi; an al-Rabiʿ report with machine English shows the new label.

### Rollback

- Back to the first form of the rule: in `external_identity.py` set `KUNYA_RULE_WORKS` to every work id (or restore `9532839`), export, `check_projection.py`, load, approve.
- No rule at all: `KUNYA_RULE_AUTHORITIES = {}`, export, load, approve (OpenITI keeps its one-carrier gains only if the rule stays; with `{}` they stand too).
- Data of the previous version: load `development/compiler-chain-fix-2026-11-22/projection` (`.12`), then re-record the approval. Code: redeploy `9532839` (label back to the model-named form).

## First model-read fixes applied (batch 001) (2026-11-22)

The first chain readings by model readers are live: batch 001 (500 uncertain reports, two blind `claude-haiku-5-5` passes under prompt v3.0.0) re-triaged by the
v3.1 tool, then cross-checked with the v3.2 tool. Of the 394 cleared readings (`chain-reader/v3_1/batch-001/eligible_to_apply.txt`) **348 stand applied**: 258 rewritten routes, 60 stored
routes confirmed (status only), 30 "no chain is written in this report". **46 wait** (`reviews/ai/records/chain-fixes/queue.json`): 30 reports that also have a rule-checked chain
(`stored_chain_checked_by_rule`, so no teacher-student pair moves), 3 whose chain later reports repeat (`cited_by_later_report`), 4 with a variant remark (`has_variant_group`),
1 inheriting from an uncertain chain, 11 held by the v3.2 tool (9 of them applied first and reverted the same day). Detail: `reviews/ai/AGENTS.md` §Chain fixes,
`datasets/hadith-data/chain-fixes/AGENTS.md`, `src/db/AGENTS.md` §Chain fixes (0021, 0022). Logs, plans, projection and diffs: `datasets/hadith-data/development/first-model-fixes-2026-11-22/` (local).

- **Schema**: `0021_chain_fix_dispositions` (no-chain disposition, tool version, inherited sources, views `public_chain_fix_dispositions` and
  `public_chain_fix_mention_kinds`) and `0022_chain_fix_tool_v3_2`, both additive, applied to production before any write (`prod-migrate-0021.log`, `prod-migrate-0022.log`).
- **Apply**: `prod-apply.log` (357 written, 0 skipped; plan `plan-applied.json`), `prod-revert-v32.log` (9 reverted). Identities of the 348: 2,179 mentions written before the
  revert; of the applied rows 200 kept a standing identity, 1,422 kept candidates only (985 unresolved names with unchanged neighbours, 437 with a changed neighbour), 557 are new
  (unresolved, no candidate); 58 are the source named in the text. `narrator_transmissions` unchanged: 28,468 rows, same content hash before and after (`transmissions-*.json`).
- **Replay**: projection `2026.11.22.14` (`projection/`, overrides file hash-bound) rewrites the fixed reports' rows by the apply's rule; its chain, mention and candidate rows for all
  394 reports equal production's (0 differences in 591 / 3,101 / 3,076 rows: `replay-diff-final.json`; control against `.13`: thousands of differences). Revert test: one fix
  reverted (rows equal `base_rows` as jsonb, every column) and re-applied (`prod-revert.log`, `prod-reapply.log`).
- **Load**: projection `2026.11.22.14` loaded into production (`prod-load.log`, dataset version `ac14c3699d37...`): **0 rows changed** in every table, all load
  checks pass; preview approval re-recorded at once (`approve.log`).
- **Checks**: `db:verify` OK; `db:verify-data` all invariants hold (two new chain-fix checks); 20 applied reports read against the Arabic (`read20.json`): all right, page rows equal the plan.

### Deploy

1. Done: 0021, 0022, the apply, the revert of the nine, the store and overrides committed. Then push the code to `refactor/postgres-drizzle` and `main` (page labels, `/method`).
2. Checks: `npx tsc --noEmit`; `npm run build`; `npx tsx reviews/ai/tools/__tests__/chain-fix.test.ts`; `npx tsx --test src/db/ops/__tests__/chain-fix-apply.test.ts`;
   `python -I datasets/hadith-data/chain-fixes/test_chain_fix_engine.py`; the `pg_export/` and `chain-reader/` Python suites.
3. Live: a six-books fix (`/hadith/k6/4950/chains`: "Read by model (claude-haiku-5-5), 2026-11-22; awaiting final review", no "not checked" line); an al-Faqih no-chain report
   (`hadith:thaqalayn:d02d9bf97373f3d079a5d999`: "No chain is written in this report (read by model ...)"); an other-Imami fix with the source named in the text
   (`hadith:thaqalayn:9daf7c805a204c1a52d9fa20`: «أبي الحسن» "Named in the report text"); `/narrator/narrator%3Arawi%3A3` lists no al-Awzaʿi.
4. Done: the `.14` load (0 rows changed) and the approval. The next full load replays the overrides (`--chain-fixes` default).

### Revert all / rollback

- One fix: `npm run db:chain-fixes -- --database production --confirm-production --revert <chain-fix:id>`; record why (`chain-fix-hold.ts --fix <id> --code <code> --detail ... --by ...`
  or a human review), then `chain-fix-decide.ts` so the overrides drop it before the next load.
- All of batch 001: pass every applied fix id (`state.json` `database: applied`) to `--revert` (one transaction per report, rows restored from `base_rows`); then move
  `datasets/hadith-data/chain-fixes/accepted_overrides.jsonl.gz` aside (never delete) so the next export replays nothing.
- A failed apply rolls back per report and leaves the rest; rerun the same command (written fixes are seen as applied and skipped).
- Schema: never edit 0021/0022; the views and columns are additive and harmless when empty. Code: redeploy `98a7277` (it ignores the new views; model-read chains then show without the label).

## Variant remarks and tranche dry runs (2026-11-22)

No schema change, no load, no fix applied to production. Three things built, two measured. Detail: `datasets/hadith-data/chain-fixes/AGENTS.md` (§variant groups and remarks, §compiler mark per route),
`reviews/ai/AGENTS.md` (v3.2 tool), `datasets/hadith-data/chain-reader/tranches/AGENTS.md` §Dry run. Local logs and scratch stores: `datasets/hadith-data/development/tranche-dry-run-2026-11-22/` (git-ignored).

- **Variant remarks.** A reader group marked `variant: true` («بمثل حديث سليمان بن بلال») never becomes a route. `chain-fix-submit --variant-notes-supported` (with `to_submission_v3_2.py --variant-notes-supported`
  building the envelope) stores the union of both passes' remarks on the fix as `planned.variant_remarks` (`chain_fixes.planned` is jsonb, so no migration; each remark marked `a`, `b` or both, with the runs),
  refuses a fix whose two passes' routes differ, and drops only the `has_variant_group` hold (`variant_only_reading` stays). Overrides carry `variant_remarks` on any effect; replay counts them and makes no row.
  The chain page reads `chain_fixes.planned -> 'variant_remarks'` beside `public_chain_fix_labels` and shows "The report mentions another version: <Arabic sentence> · names <names>" under the chain
  (a remark one pass wrote is marked "noted by one of the two readers"). A revert, rejection or changed text removes it with the chain. Flow tests: `reviews/ai/tools/__tests__/chain-fix.test.ts` (envelope, switch, decide,
  override, replay, rejection), `src/db/ops/__tests__/chain-fix-apply.test.ts` (apply and revert, page read), `chain-fixes/test_chain_fix_engine.py` (`VariantRemarkTest`).
- **Compiler mark per route.** `WorkRegister.route_links` (`pg_export/work_register.py`) reads each later route's own opening words; the engine plans it as `compiler_link`, the apply writes it, replay uses it or computes it
  (`chain_fix_projection.rewrite_rows(..., register)`). `hadith:k6:2400` route 1 «وقال الليث»: direct -> indirect (test `CompilerHeadPerRouteTest`). Of the 129 later routes of the 76 applied multi-route fixes that a compiler heads,
  **4 differ from production**: `chain:k6:2400:0001`, `chain:k6:348:0001`, `chain:k6:6230:0001` (direct -> indirect, «وقال X») and `chain:k6:23555:0002` (indirect -> direct, «حدثنا بذلك»). Production is **not** changed: the next full
  load writes them (a load then changes exactly those 4 chain rows' `compiler_link`; the model-read chains feed no list, so `narrator_transmissions` does not move). A name-opening work (al-Kafi, al-Saduq) and a co-transmitter joined by «و» keep the report's mark.
- **Dry runs** (`dry_run_tranche.py`, `dry_run_report.py`; `chain-fix-apply.ts --dry-run --no-mirror` is the store-free rehearsal: each report's transaction inserts its fix row, applies, records the tally and rolls back). Eligible = the v3.2
  triage (tranche 01 read under prompt v3.1, tranche 02 under the v3.2 draft). Per group (six Sunni books / al-Faqih / other Imami), without -> with `--variant-notes-supported`:

| | eligible in | refused | recorded | held by the pipeline | would apply | routes rewritten | stored chain confirmed | no chain | inherited links | source named in text | variant remark |
|---|---|---|---|---|---|---|---|---|---|---|---|
| t01 six Sunni | 577 -> 620 | 0 | 577 -> 620 | 42 -> 43 | 535 -> 577 | 424 -> 453 | 110 -> 123 | 1 | 0 | 0 | 0 -> 42 |
| t01 al-Faqih | 52 | 0 | 52 | 10 | 42 | 38 | 0 | 4 | 8 | 25 | 0 |
| t01 other Imami | 105 | 0 | 105 | 12 | 93 | 76 | 11 | 6 | 5 | 28 | 0 |
| **t01 total** | 734 -> 777 | 0 | 734 -> 777 | 64 -> 65 | **670 -> 712** | 538 -> 567 | 121 -> 134 | 11 | 13 | 53 | 0 -> 42 |
| t02 six Sunni | 549 -> 612 | 0 | 549 -> 612 | 38 -> 40 | 511 -> 572 | 390 -> 437 | 121 -> 135 | 0 | 0 | 0 | 0 -> 61 |
| t02 al-Faqih | 48 | 1 | 47 | 6 | 41 | 30 | 4 | 7 | 4 | 16 | 0 |
| t02 other Imami | 109 -> 111 | 0 | 109 -> 111 | 10 -> 11 | 99 -> 100 | 81 -> 82 | 15 | 3 | 3 | 20 | 0 -> 1 |
| **t02 total** | 706 -> 771 | 1 | 705 -> 770 | 54 -> 57 | **651 -> 713** | 501 -> 549 | 140 -> 154 | 10 | 7 | 36 | 0 -> 62 |

  Refused: one (t02 al-Faqih): the reader's validator, «order: r1 link 5 starts at 175 before link 4 ends at 327» (a second route not in text order). No stale text. Held (pipeline, archive side), codes may stack on one fix:
  `stored_chain_checked_by_rule` 54 (t01) / 49 (t02) and with the switch 55 / 51; `inherited_source_chain_uncertain` 8 / 2 (al-Faqih and other Imami: an earlier report whose chain is not rule-checked); `inherited_name_not_in_source_chain` 2 / 0;
  `cited_by_later_report` 1 / 3 (4 with the switch). Without the switch the 43 and 65 variant readings never reach an envelope (the reader tool holds them as `has_variant_group`); with it none is held for that. Remarks written by both passes 32, by pass A only 10, by pass B only 9 (tranche 01).
  **`narrator_transmissions`: nothing would touch it**: no would-apply fix has a rule-checked or unstatused chain (that is what the hold keeps out), all 34 `chain_fix_work_settings` are `false`, and the view holds 28,468 rows (unchanged).
  Caveat: the "with" runs rehearse only the fixes the "without" run did not have (its plan stands for the rest: `apply-plan.json` `merged_with_baseline`).
- **Rule-checked chains (measured, behaviour unchanged; owner decision pending).** The readings held as `stored_chain_checked_by_rule` (batch 001: 30; tranche 01: 55; tranche 02: 51; 136 reports with 144 rule-checked chains):
  the agreed reading leaves **93 reports with every rule-checked chain identical** and **changes a rule-checked chain in 43** (51 of the 144 chains changed, 93 identical; batch 001 9 of 30 reports, tranche 01 20 of 55, tranche 02 14 of 51).
  Teacher-student pairs of those chains (present in `narrator_transmissions`): 271 report-pair incidences, 252 distinct pairs. If the reports' chains leave the lists (a model-read chain feeds none): **42 pairs disappear** (supported by no other report; 28 reports lose at least one),
  the rest only lose a supporting report; **0 pairs appear**. If the readings were admitted instead: 181 of the 271 are kept by the reading (both names adjacent, identity carried) and **0 appear** (the carry rule forms no new pair). Per source (incidences / vanishing): batch 001 29 / 2; tranche 01 132 / 23; tranche 02 110 / 17.
  Ten examples with the stored chain, the reading and the text quote: `chain-reader/tranches/dry-run-2026-11-22/rule-checked-examples.json` (kinds: a non-chain word stored as the chain; a missing co-transmitter route; the compiler stored as the first link; a taḥwīl merged into one chain; a name taken from the other route; a relation prefix «أبيه» dropped).
  Numbers per fix: `rule-checked-measure.json`.
- **Checks**: Python suites (`pg_export` 100, `chain-fixes` 28, `chain-reader/v3_2` 27, `tests` 21, `v3` 24, `v3_1` 45), `chain-fix.test.ts`, `chain-fix-apply.test.ts` (4), `structure-flows` / `flows` / `chain-builder-flows`, `tsc`, `npm run build`: see the sweep line below.
  Two lessons from the rehearsal: a killed `chain-fix-apply --dry-run` leaves its backend `idle in transaction` holding the data-write advisory lock until reaped (found in `pg_locks`, reaped by exact pid); and a driver loop must be started once with `run_in_background`, never with `&`.

### Rollback
- Variant remarks: stop passing `--variant-notes-supported` (the hold returns); the remark lives only on the fix row. Compiler mark: make `route_links` return no marks (replay then copies the first chain's, as before); code: redeploy `de483e6`.

## AI review tier, tools v3.3/v3.4, rule-checked ruling (milestone 1, 2026-11-22)

Owner rulings of 2026-11-22 wired into the pipeline; **no fix applied, no reading released**. Detail: `reviews/ai/AGENTS.md` (§Tools v3.3 and v3.4, §Sayings,
§Rule-checked ruling, §AI review tier), `datasets/hadith-data/chain-fixes/AGENTS.md` (§tools v3.3 and v3.4, §AI review), `src/db/AGENTS.md` §AI review tier.
Logs: `datasets/hadith-data/development/ai-review-tier-2026-11-22/` (local).

- **Tools.** Engine and CLIs register tool `v3_3` and tool/prompt `v3_4` (prompt sha256 `b63fd535…`); a later tool reads an earlier prompt's output, never the reverse.
  v3.3 runs with ONE correction, a patch module (`chain-reader/v3_3/holds_v3_3_pipeline.py`): `route_at_most_half_the_longest` is v3.2's un-narrowed rule
  (t01-6d7565, b1-2c5437, b1-cb35a4 held; t02-1552aa held again). v3.4's holds stand on the same corrected base, per saying.
- **Sayings.** `--sayings-supported` (submit) lifts `two_sayings_not_supported`; the engine writes `planned.chains[].saying` and `planned.sayings`; the page heads
  each route "Chain of the first saying" / "Chain of the second saying" with the opening words. Tested on the v3.4 example t01-520f51 (no real labelled
  reading exists: the v3.4 re-read has not run).
- **Reviewer tier.** Specialist `chain-reviewer` 1.1.0 (`1136aec2…`) registered (`/method`, `reviews/ai/specialists.json`, `model_registry.json`).
  `chain-review-record.ts --batch <set> [--extra-second <dir>] [--expect <outcomes.tsv>]` records per item; outcomes are `review_rules_v1_1.outcome`
  itself (through `chain-fixes/review_bridge.py`) on the fix's current state. Flow test on the pilot's real outputs: `reviews/ai/tools/__tests__/chain-review.test.ts`.
- **Rule-checked ruling.** `stored_chain_checked_by_rule` is no longer added and is a lifted code in the decide rule. Nothing changed on production for it
  in this milestone (the store was not re-decided; the overrides file is the 348 of batch 001).
- **Quotes.** Evidence quotes stand when the letters are exact (harakat U+064B-0652, U+0670, tatweel, Qur'anic marks U+06D6-06ED ignored) and are stored as the
  text writes them (`chain_fix_engine.locate_quotes`).
- **Schema** `0023_chain_fix_ai_review` (additive; `prod-migrate-0023.log`, `prod-verify-after-0023.log`).
- **Compiler marks** repaired through the pipeline (`npm run db:chain-fixes -- ... --repair-compiler-links --fix <id>`; dry run over all 76 multi-route fixes
  found exactly these 4: `prod-repair-dry-run.log`, `prod-repair.log`, store `records/chain-fixes/repairs/2026-11-22.jsonl`): `chain:k6:2400:0001`,
  `chain:k6:348:0001`, `chain:k6:6230:0001` direct -> indirect; `chain:k6:23555:0002` indirect -> direct.

### Deploy (milestone 1, done)

1. `0023` applied to production before any write; compiler marks repaired; projection `4dfa8367…` (replays the 348) loaded: **0 rows changed** in every table;
   approval re-recorded at once (`approve.log`); `db:verify`, `db:verify-data` pass. Commit `6db705c` pushed to `refactor/postgres-drizzle` and `main`; Railway
   deployment `1ffb936c` SUCCESS; `/api/health` 200; `/method#chain-tiers` serves the live table; `/hadith/k6/4950/chains` reads "Read by two models (claude-haiku-5-5), 2026-11-22".
2. Checks: Python suites (`chain-fixes` 32, `chain-reader` v3 24, v3_1 45, v3_2 27, v3_3 19, v3_4 17, reviewer 23, tests 21, `pg_export` 7 suites); `chain-fix.test.ts`;
   `chain-review.test.ts`; `chain-fix-apply.test.ts` (4); `npx tsx "src/app/hadith/[id]/components/__tests__/chain-tier-labels.test.ts"`; `tsc`; `npm run build`.

### Rollback (milestone 1)

- Code: redeploy `305f0ed` (it ignores 0023's columns and views). Schema: never edit 0023; its columns are nullable and its table empty.
- Compiler marks: the four repairs are logged in `records/chain-fixes/repairs/`; a revert of the fix restores its base rows (the old marks). The v3.3 correction: point
  `TOOLS["v3_3"]` at `holds_v3_3.compute_holds`.

## Tranches 01/02 applied, 27 batch-001 readings released, batch-001 AI reviews recorded (milestone 2, 2026-11-22)

Logs, plans, snapshots, diffs: `datasets/hadith-data/development/ai-review-tier-2026-11-22/` (local). Every write went through `chain-fix-submit` / `chain-fix-decide` /
`chain-review-record` / `npm run db:chain-fixes`; no hand SQL.

- **Envelopes**: `v3_3/to_submission_v3_3.py --only tranches/tranche-0N/triage-v3_3/eligible_v3_3.txt` (730 and 695; no variant flag, no release flag), all clean
  under `--check-only --database production`; rehearsal `tranches/dry_run_tranche.py --tool v3_3 --only ...` (`rehearsal/`): t01 719 apply / 11 held, t02 688 / 7
  held, 0 refused, 0 stale, 0 skipped. Recorded in the store (`--database production`), decided: 1782 accepted (348 + 27 + 719 + 688).
- **Ruling 5**: the 27 batch-001 readings held only by `stored_chain_checked_by_rule` (30 carry the code; 3 also have another hold and stay held) were re-checked
  with the corrected v3.3 tool (`b1_lifted.json`: no hold) and released by the lifted code. `narrator_transmissions` 28,468 -> 28,426: **42 pairs lost, 0 gained**, 206
  pairs lost a supporting report (`pairs-lost.json`); 3 narrators lost every teacher (rawi 12496 Muharrar b. Abi Hurayra, 2308 ʿAbd Allah b. Wahb b. Zamʿa, 24168
  al-Sakan b. al-Mughira) and 5 every student (those three, 11581 Hajjaj b. Hajjaj al-Bahili, 12256 ʿAbd Allah b. Nistas).
- **Apply**: `prod-apply.log` (1434 reports, 0 skipped, 59 min). Then the batch-001 reviews (`reviewer/review-applied-b001/`, the refolded record):
  `chain-review-record.ts --batch ... --extra-second .../second-pass-refolded --expect .../outputs-refolded/outcomes.tsv` (every outcome equal to the reviewer side's):
  332 AI reviewed, 6 disputed (stay applied), 10 corrections (two reviews alike) written as new fixes; their 10 readings reverted (`--revert-rejected`, queue
  `revert_before_apply`) and the corrections applied (`prod-revert-corrected.log`, `prod-apply-corrections.log`).
- **Replay**: a full export (`projection/`, 1782 overrides) equals production for every row of the 1782 reports (0 differences in 2,886 chain / 15,705 mention /
  18,469 candidate rows: `replay-diff.json`; control against the pre-apply projection: 9,847 / 23,233 / 5,290 differences). Revert test on `hadith:k6:30143`: rows equal
  `base_rows` on every column (`revert_equal.ts`), then re-applied.
- **Load gate**: the first load attempt failed one invariant and rolled back: the "two reader runs, one blind" check did not know the AI-correction path; it now
  requires two review runs that name the corrected fix (`load/verify-data.ts`), as 0023's decision check does.
- **Load**: projection `314221fa…` (second attempt, `prod-load-m2.log`): **0 rows changed**; approval re-recorded at once (`approve-m2.log`); `db:verify` and
  `db:verify-data` pass. 20 newly applied reports read against the Arabic (`read20.json`, seed 20261123): 20 right; page rows equal the plan in all 17 rewrites;
  the 3 confirmed-stored reports have every chain `read_by_model`.
- **Not done here**: the reviewer's built sets (`reviewer/review-*/`) still list 348 applied readings (its test `test_the_applied_set_is_the_fix_stores` fails by
  design now that the store moved): rebuild with `build_review_packets_v1_1.py --sets` before the next reviewer run. The two disputed readings that wait for a
  second review (b1-fea4e5, b1-2958ef: `second-pass-refolded/`) and the three referrals are listed in `queue.json` `ai_disputed_awaiting_second_review`.

### Deploy (milestone 2)

Data is written and loaded; push the code (`verify-data.ts` AI-correction invariant, the correction hold) to both branches. Live: a tranche rewrite
(`/hadith/k6/30143/chains`: "Read by two models"), an AI-reviewed batch-001 chain ("...; AI reviewed (claude-opus-5-5), <date>"), an AI correction
(`/hadith/k6/24636/chains`: "Corrected by AI review (claude-opus-5-5, 2 runs), <date>"), `/method#chain-tiers`.

### Rollback (milestone 2)

- One fix: `npm run db:chain-fixes -- --database production --confirm-production --revert <chain-fix:id>`, record why (`chain-fix-hold.ts` or a human review), decide.
- A tranche: pass every applied fix id of the tranche (`state.json`, submissions `t0N-*`) to `--revert`; move `accepted_overrides.jsonl.gz` aside only if every fix goes.
- An AI correction: a human `superseded`/`rejected` review on it, decide, `--revert-rejected`, then re-apply the readers' fix (it returns to the overrides).
- Ruling 5 back: re-add `stored_chain_checked_by_rule` to the submit tool and drop it from `LIFTED_HOLD_CODES`; decide; `--revert-rejected` reverts nothing by itself, so
  revert the fixes whose reports have a `checked_by_rule` chain in their base rows explicitly.
- Data of the previous version: load `projection-m1/` (`4dfa8367…`) only after reverting the fixes (a load replays whatever the overrides file holds).
- **Label date repair (after the push of `5bc93aa`)**: recording an AI mark had re-inserted 341 batch-001 decisions with the write time as `decided_at`, so
  "Read by two models, <date>" read 2026-11-23. The mirror now keeps the date when state and effect are unchanged, and
  `npm run db:chain-fixes -- --database production --confirm-production --repair-decided-at` restored the 341 to 2026-11-22 (`prod-repair-decided-at.log`); `db:verify-data` passes.

## Railway config conversion (milestone 3, 2026-11-22)

`railway config migrate --apply --service islamicapps` wrote `.railway/railway.ts` and cleared the service's stored Config File path. The generated file dropped
the builder and restart policy; `.railway/railway.ts` declares `source` (github, main), `preserve()` for `DATABASE_URL`, `NEXT_TELEMETRY_DISABLED`, `SITE_URL`,
`build: {builder: DOCKERFILE, dockerfilePath: Dockerfile}`, and `deploy: {healthcheckPath: "/api/health", healthcheckTimeout: 120, restartPolicyType: "ON_FAILURE",
restartPolicyMaxRetries: 5}` (field names from `railway` SDK `3.17.0` types). `railway config apply --yes` was applied to production: the service stores builder
DOCKERFILE, dockerfilePath Dockerfile, healthcheck `/api/health` 120 s, max retries 5; `restartPolicyType` reads `null` in the remote state (Railway's default
On Failure). There is no pre-deploy migrate command and no start command (Dockerfile CMD `node server.js`; migrations by hand), so none is declared.

- **Completed**: added `railway` (`^3.17.0`) to `devDependencies` (`package.json` / `package-lock.json`), removed `railway.json`, verified `npx tsc --noEmit` passes,
  and verified `railway config plan` (with `_=...railway.exe` because the SDK checks `$_ --version`) shows no deprecation warning and only
  `~ Update islamicapps deploy.restartPolicyType (null -> "ON_FAILURE")` (`Plan: 0 to add, 1 to change, 0 to destroy`).
- **Rollback**: `railway config migrate undo` (restores the path if a snapshot exists) or re-add `railway.json` and set the Config File path to `railway.json` in the service settings.

## Tranches 03–10 applied (milestone 4, 2026-11-23)

Logs, plans, catalog, projection, and diffs: `datasets/hadith-data/development/tranche-apply-2026-11-23/` (local). Every write ran sequentially through `chain-fix-submit` / `chain-fix-decide` / `npm run db:chain-fixes` / `db:load` / `db:approve-preview`.

- **Submit & Decide** (`submit-t03-t10.log`, `decide-t03-t10.log`): all 8 tranches' 0-refused envelopes (`t03-submissions/`–`t10-submissions/`, adding `--sayings-supported` for Tranches 07–10) submitted against `--database production`; `chain-fix-decide.ts` recorded **5,587** new fixes (**5,532** accepted, **55** held), bringing the store to **7,416** total fixes (**7,314** accepted, 92 held, 10 superseded) and rewriting `datasets/hadith-data/chain-fixes/accepted_overrides.jsonl.gz` to **7,314** reports:
  - `t03`: 672 accepted, 3 held (`route_at_most_half_the_longest` 1, `inherited_source_chain_uncertain` 2)
  - `t04`: 689 accepted, 12 held (`route_at_most_half_the_longest` 2, `cited_by_later_report` 3, `inherited_source_chain_uncertain` 6, `inherited_name_not_in_source_chain` 1)
  - `t05`: 700 accepted, 9 held (`route_at_most_half_the_longest` 1, `cited_by_later_report` 5, `inherited_source_chain_uncertain` 3)
  - `t06`: 673 accepted, 2 held (`inherited_source_chain_uncertain` 1, `cited_by_later_report` 1)
  - `t07`: 701 accepted, 8 held (`inherited_source_chain_uncertain` 6, `cited_by_later_report` 1, `inherited_name_not_in_source_chain` 1)
  - `t08`: 698 accepted, 7 held (`inherited_source_chain_uncertain` 4, `inherited_name_not_in_source_chain` 1, `cited_by_later_report` 2)
  - `t09`: 707 accepted, 9 held (`route_at_most_half_the_longest` 2, `inherited_source_chain_uncertain` 7)
  - `t10`: 692 accepted, 5 held (`inherited_source_chain_uncertain` 2, `cited_by_later_report` 2, `inherited_name_not_in_source_chain` 1)
- **Production Apply** (`prod-apply-t03-t10.log`, `plan-applied-t03-t10-run1.json`): succeeded on attempt 1 with exit 0; `mirror: 5587 decision rows changed`; `refresh_network: [{"refreshed":true}]`; **5,532** reports applied, **0** skipped (`replace_routes` 4,234, `set_status` 1,138, `replace_routes:no_chain_by_reading` 160; 984 chains retired, 6,793 chains written, 37,279 mentions written: 5,040 `kept_identity`, 22,283 `kept_candidates_only`, 9,889 `new`, 67 `inherited`, 507 `named_in_text`). Applications recorded in `reviews/ai/records/chain-fixes/applications/2026-11-24.jsonl`.
- **Replay & Load**:
  - Full export (`projection/`, `projection.log`) produced canonical `643da72450145efd00e6af6d76f8b44bcf8016b36724f150e4c72420a6f59b82`; `check_projection.py` (`check-projection.log`) checked 110,623 chains and 542,515 mentions (`PASS every file-level chain invariant`).
  - Replay diff over all 7,314 overridden reports (`replay-diff.json`): **0 differences** across 12,142 `chains`, 66,339 `chain_mentions`, and 81,265 `chain_mention_candidates`.
  - Production load (`prod-load-m4.log`, `prod-load-m4.report.json`): version `643da72450145efd00e6af6d76f8b44bcf8016b36724f150e4c72420a6f59b82`, **0 rows changed** across all 23 tables (`facets 0`, `network refreshed: false`); preview approval re-recorded immediately (`approve-m4.log`).
- **Verify**:
  - `npm run db:verify` against production (`verify-m4.log`): `OK: catalog matches src/db/schema and drizzle/core` (55 tables, 14 views, 1 materialized view, 24 of 24 migrations).
  - `npm run db:verify-data -- --database production --confirm-production` (`verify-data-m4.log`): `OK: all section 11.4 data invariants hold` (`public_hadiths=99437`, `override=true`, `transmissions=28271`).
  - Live `https://islamicapps-production.up.railway.app/api/health`: HTTP 200 (`{"status":"ok","database":"reachable","latencyMs":39}`).
  - Live `/method#chain-tiers` (`method.html`, HTTP 200): Rule-built, uncertain **10,743** (Ibadi 43, Imami 2,651, Sunni 8,044, Zaydi 5); Rule-built, checked **87,737** (Ibadi 798, Imami 28,411, Sunni 57,866, Zaydi 662); Read by two models **11,650** (Imami 1,838, Sunni 9,812); AI reviewed **492** (Imami 178, Sunni 314); Agent verified **0**; Verified by a person **0**; No chain, by reading (reports) **217** (Imami 215, Sunni 2).
