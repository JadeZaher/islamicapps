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
