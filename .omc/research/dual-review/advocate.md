---
type: review
date: 2026-11-21
role: advocate (two-sided review; an adversarial reviewer works independently; a third party synthesizes)
branch: refactor/postgres-drizzle
---

# Advocate review: Shura wa Istehsan after the Postgres refactor

**Method.** Every load-bearing claim below was checked against the repository or a live store, not taken from the
documents' summaries. Sources: the development Postgres (`islamicapps_dev`, read-only session with
`default_transaction_read_only=on`, current dataset version `87f89127…`, `identity_candidates_load`, complete); the
production Neo4j (read-only `executeRead` count queries through `neo4j-driver`, credentials never printed, script in
the session scratchpad); the load reports under `datasets/hadith-data/development/pg-load-2026-11-21/`; the
diagnostics outputs on disk; `hadith-kg.db` opened `mode=ro&immutable=1`; code under `src/`. No file other than this
report was written in the repository; no build, commit or write query was run.

Where a number was not measured by me, it is marked *(doc)* with its file.

---

## 1. What is solid, and should not be reopened

| Decision / work | What I checked | Result | What would change my mind |
| --- | --- | --- | --- |
| **Postgres instead of Neo4j** (design §1.1) | Neo4j relationship types in production: `INCLUDES, FROM_SOURCE, FROM_TRADITION, INGESTED_IN, HAS_CHAIN, HAS_ASSESSMENT, UNDER_SCHEME, INCLUDES_MENTION, NARRATED_FROM`. All fixed-depth. Arabic trigram search in Postgres: `ilike '%بالنيات%'` 27 ms, `'%الصلاه%'` 25 ms (EXPLAIN ANALYZE, bitmap scan on `hadiths_text_ar_normalized_trgm_idx`, 73 MB) | The graph store was used as a document store with joins. Postgres does the same queries at interactive speed | A product requirement for variable-length path queries at request time (e.g. "all routes from narrator A to B") that cannot be precomputed offline |
| **One writer per table** (§4.1) | Grepped every `insert into / update` of pipeline tables (`hadiths, translations, chains, chain_mentions, narrators, hadith_assessments`) under `src/`: only `src/db/load/**` and test fixtures (`src/db/queries/__tests__/fixture-database.ts`). App writes go only to curation tables (`src/db/queries/commentary.ts:88-190`) and `curation_audit` (`src/db/queries/write.ts:61`) | Holds in code | A server action that writes a pipeline table; or, at deploy, the app still connecting as superuser (RUNBOOK line 39-40 says it does today: the rule is enforced by convention, not by a role) |
| **Stable ids + reload idempotence** | `load-2-reload.report.json` and `load-5-reload.report.json`: mode `reload`, `rowsChanged 0`, `facetRowsChanged 0`, sum of inserted+updated+derivedUpdated+retired over all 18 tables = 0. `projection.sha256` and `projection-repeat.sha256` are byte-identical (`diff` clean) | Proven twice on the real 99,283-report corpus, plus determinism of the projector | A reload that changes rows with identical input, or a projection whose bytes depend on run order/hash seed |
| **Ids survive a real change** | Load 4 (candidates) on top of load 2: chains inserted 14,017 / updated 17,063 / retired 12,964 with `expectedRetired` equal; `mentions_surface_changed_under_same_id 18,535` reported, `orphaned_decisions 0` | Retire-not-delete works and the "same id, different surface" hazard of §4.2 is detected and counted, not silently replayed | Decisions replayed onto a mention whose surface changed |
| **Verified-identity rule** (only text-confirmed source index or a reviewer decision sets `narrator_id`) | Live mentions: 538,513; with `narrator_id`: 83,949, all `resolution = source_index`. The 27 rows with `exact_registry` + `narrator_id` are all retired (from load 2). `db:verify` checks the view predicate (`src/db/AGENTS.md` §Verified link) | Holds in data | Any live `narrator_id` with a name-match basis |
| **Tiered, atomic resolver with placeholder exclusion** | Candidate counts by basis in the current version: `name_exact 25,414`, `name_spelling_fold 18,542`, `name_kunya_only 5,559`, `source_index 75,216`, `source_index_confirmed_by_text 88,190`; dropped placeholder claims 2,755; `confirmed_but_contested 4,241` kept unresolved | The resolver is used only to *propose*; disagreement is shown not hidden | Evidence that tier-1 folds create wrong matches at a material rate (a reviewed sample; none exists yet — this is a gap, not a refutation) |
| **Rights as a gate** | `collection_rights` rows: 0. `public_hadiths`: **0**. `public_translations`: 0. `pg_get_viewdef('public_hadiths')` references the override. The owner's preview override sits on the *previous* version (`30cd1c84…`, `public_override_by = owner`); the current version `87f89127…` has none | Fail-closed works: a new load does not inherit a prior approval. (Side effect: the approved public preview is currently empty — see §4) | A path that shows a non-cleared work, e.g. a query that reads `hadiths` instead of `public_hadiths` on a public page |
| **Arabic integrity** | Load checks "Arabic round trip: SHA-256 recomputed in the database equals arabic_sha256 — violations 0" and "translations bound to their hadith Arabic hash — violations 0" | Holds | Any rewrite of `text_ar` in the projector |
| **Grades as attributed claims, not scores** | `hadith_assessments`: `grade_value → collection_label 'ثابت'` 29,915 (correctly *not* a grade); `gradings_full → cited_ruling` 16,835 with grader, work, volume, page split | Postgres corrects a real error in Neo4j, where the same 29,915 `ثابت` labels sit under `grade_scheme = sunni_7tier` as if they were grades | — |
| **Report correspondence method** | README: deterministic across two hash seeds; recall measured (same wording 100%, all classes 77%); precision read on a 150-pair stratified sample; matn isolation routes around 1,597 misattached and 12,617 chain-carrying `matn_ar` values | Methodologically the strongest single piece of work in the session | A blind second reader disagreeing materially with the author's 150-pair reading (it is one reader, the author) |
| **Biography verification** | README tables: lexicon death years agree or are consistent with Taqrib for 1,588 / 1,663 (95.5%); generation 5,128 / 5,194 (98.7%) | The lexicon is a faithful Taqrib-family transcription where checkable; errors are typed (century slips, transpositions) | Agreement driven by circularity is already acknowledged in the README; what would change it is an independent source (al-Isaba, Usd al-Ghaba) disagreeing at scale |

What is solid but **not yet proven**: the restore procedure (§2.5.1 says "rehearsed once in step 8" — not done), the
least-privilege role (not applied), and the memory budget (dev database is 1,582 MB in `public`; `chain_mentions`
613 MB, `hadiths` 509 MB; §1.4's 250-450 MB RAM estimate is plausible only if the hot set is small — untested).

---

## 2. Local sources versus the Neo4j copy

**Short answer: the ETL from local sources is right, and the planned "export curation from Neo4j" step is almost
empty.** I reached production Neo4j (read-only) and counted. Neo4j was populated from the very same local files:
`src/scripts/lib/regen/mode-fullregen.ts:97-98` reads `datasets/hadith-data/all_hadiths_unified.csv` and
`datasets/narrator-data/all_rawis.csv`; the 21 biographies came from `src/scripts/seed-narrator-bios-phase0.ts`
(in git). Neo4j is a *downstream, older projection* of the local data, not an independent source.

### Measured in production Neo4j (2026-11-21)

- Labels present: Narrator, Hadith, MatnVariation, Chain, Scholar, ScholarVerdict, Source, HistoricalEvent, Location,
  Commentary, ReligiousTradition, SourceText, CrossCulturalParallel, MotifTag, SchoolOfThought, Practice,
  DatasetVersion, NameMention, Assessment.
- Node counts: **Commentary 0, CrossCulturalParallel 0, SourceText 0, MotifTag 0, Location 0, HistoricalEvent 0,
  Epoch 0, SchoolOfThought 0, Citation 0, BibliographicWork 0, Scholar 0, ScholarVerdict 0, Practice 0,
  MatnVariation 0**; ReligiousTradition 4 (Sunni, Imami, Zaydi, Ibadi: name only); NameMention 4,944.
- `RESOLVES_TO` edges: 0. Any relationship with `reviewed_by`: 0. No human identity decision exists in Neo4j.
- Hadith 99,283; non-blank English 68,515 (Sunni 33,588, Imami 33,225, Ibadi 1,004, Zaydi 698). No hadith carries
  an `_enriched_at` / `_extraction_method` property (0).
- Chains: Sunni 64,356 (51,230 with ≥1 narrator, 145,510 inclusions); Imami 33,225 (10,747; 13,964); Ibadi 1,004
  (62; 73); Zaydi 698 (2; 3). `NARRATED_FROM` 80,240.
- Narrators 24,326; `death_date_hijri` 3,951; `death_date_gregorian` 554; `bio` present but blank on all;
  `bio_summary` / `reliability_consensus` / phase-0 fields on exactly 21; `bio_tadil` 20; `bio_jarh` 7.
- **The 21 biographies match the git seed file verbatim**: every `bio_summary`, `bio_tadil` and `bio_jarh` string
  fetched from Neo4j is found byte-for-byte (after joining the file's `' + '` string concatenations) in
  `src/scripts/seed-narrator-bios-phase0.ts` (21 of 21).
- Source nodes 32 (Sunni 29, Ibadi 1, Zaydi 2, **Imami 0**). Assessments: 399,064 nodes in four schemes, each scheme
  applied to every hadith regardless of tradition (e.g. `zaydi_3tier` on all 99,283, all placeholders).

### Field-by-field

| Data | Neo4j (production) | Local pipeline → dev Postgres | Better copy, and why | Only in Neo4j? |
| --- | --- | --- | --- | --- |
| Arabic text | 99,283, no `record_id`, no hash | 99,283 (8 without Arabic), `arabic_sha256` recomputed in-db, 0 violations; 34 collections incl. 21 distinct Imami works | **Local/PG**: hash-bound, durable ids, correct work identity (Neo4j has no Imami Source node at all) | No |
| English | 68,515, no provenance fields; Ibadi/Zaydi English is unlabelled machine output | Public table 66,776 (Sunni 33,588, Imami 33,188, Ibadi **0**, Zaydi **0**); candidate stream 31,652 (29,915 classical Sunni with no model identity, 1,733 gemma-4, 4 manual); plus 2,082 hy-mt2 and 10,662 glyph-substitution candidates on disk | **Local**: more English (98,430 non-blank) and every row says where it came from. Neo4j's 1,739 "extra" are the same machine text without a label | No |
| Chains | One chain per hadith (no taḥwīl branches), 159,550 inclusions | 114,597 chains (branches), 538,513 mentions; Pure Canon chain field replaces 26,438 matn-only extractions; 4,391 no-isnad reports get no invented chain | **Local/PG**: structurally correct; Neo4j invents chains from matn-only text for Ahmad/Muwatta/Darimi | No |
| Narrator identity links | 159,550 name-match inclusions, incl. 13,964 on Imami chains matched against a Sunni-derived lexicon; 0 reviewed | 83,949 verified (Sunni, K6 index confirmed by the Arabic); 212,921 labelled candidates (Sunni); Imami/Ibadi/Zaydi 0 | **PG** for trust; Neo4j for *apparent* coverage. Neo4j's links are reproducible from the local resolver and are exactly what the owner ruled are candidates, not identities | No |
| Gradings | 399,064 nodes, 352,315 placeholders (88.3%); 29,915 `ثابت` miscast as `sunni_7tier` grades; 16,834 Imami | 46,750 rows: 29,915 `collection_label`, 16,835 `cited_ruling` with work/vol/page; on disk: Tirmidhi 2,707 compiler statements, 5,163 Taqrib verdicts, 268 inline statements | **PG**: typed and attributed | No |
| Narrator biography fields | death year 3,951; 21 phase-0 bios | Lexicon (24,326) + 60,725 parsed assertion candidates + 17,893 *cited* assertion candidates (Taqrib, Tahdhib, hadith-kg); the 21 bios in git | **Local** (citations exist only locally) | **No** — the 21 bios are verbatim in git |
| Parallels / source texts / motif tags | 0 / 0 / 0 | 0 (tables exist) | Neither has any | No |
| Commentaries | 0 | 0 | — | No |
| Locations, historical events | 0, 0 | Seed of 32 locations, 54 events in `src/scripts/seed-historical-data.ts` (uncited) | Local (the only copy) | No |
| Teacher/student network | `NARRATED_FROM` 80,240 (name-matched) | `narrator_teachers` 55,674 from the lexicon; `narrator_transmissions` 10,635 (both ends source-index verified) | PG (stricter, explainable) | No (derived) |
| NameMention | 4,944 surface nodes | 538,513 mention rows | PG | No (derived) |

**Verdict.** Nothing I could find exists only in Neo4j. The RUNBOOK's next-step 3 ("Export curation from Neo4j:
commentaries, events, parallels, the 21 biographies") reduces to seeding the 21 bios from the git file (recorded as
Sunni, per the owner) and the 54/32 seed rows from the seed script — both local. Neo4j's remaining value is as a
*comparison baseline* (it shows what the live site displays today) and as an insurance snapshot before retirement.
Cheapest safe path: one read-only `neo4j-admin`/APOC-free dump of node/edge counts plus the 21 narrator nodes to a
file, then drop the export track.

What I could not verify in Neo4j: the content of every English cell against the local CSV (I compared counts per
tradition, which match the local "source" rows plus the gemma machine rows); whether any property was hand-edited on
a hadith node after load (no enrichment properties exist; I did not diff text).

---

## 3. Easier ways to populate the archive (joins and reuse, not new extraction)

Ranked by yield per unit of effort. "Yield" numbers are measured unless marked *est.*

### 1. Imami narrator identities from Riwayat (not planned anywhere)
- **Populates** `chain_mention_candidates` for Imami reports (today 0 candidates on 169,536 Imami mentions; every
  Imami hadith is `unresolved` or `extraction_failed`).
- **Yield.** Riwayat matches 21,472 Imami reports (64.6%); 20,933 to exactly one Riwayat report (17,339 whole-text
  equal) — measured from `report_join_riwayat.jsonl.gz`. Riwayat's Shi'i chains carry an asserted narrator id on
  152,163 of 181,922 mentions (83.6%), 134,614 of them from Thaqalayn's own annotation (*doc*, biography-verification
  README). *Est.* ~90,000 Imami mention candidates (21k reports × ~5.1 mentions × 0.84).
- **Cost.** Small: the K6 sidecar pattern already exists (`reconciled/build_k6_source_index_sidecar.py`: position
  alignment against the extracted Arabic, corroboration classes). Needs a new authority key space
  (`narrator:riwayat:N…`, design §4.2 already reserves `narrator:imami:<work>:<entry>`), and a basis label
  `external_index` distinct from `source_index`.
- **Licence.** CC0 for Riwayat's identifications; texts are Thaqalayn's (we already hold them). Clean.
- **Integrity risk.** Medium-low: reported precision 0.98 vs MIDS (*doc*); it is another project's claim and must
  be shown as such ("identified by Riwāyāt"), never as verified. Re-attribute Riwayat's Musnad Zayd / Musnad
  al-Rabi' rows (labelled `sunni` there).

### 2. Sunni chains with ids from hadith-kg, especially where the K6 index cannot help
- **Populates** candidates for Sunni reports with no verified link; it is the *only* route for the Pure Canon works
  (Ahmad, Muwatta, Darimi, Shafi'i: 29,915 reports, 0 verified links today).
- **Yield** (joining `report_join_hadith_kg.jsonl.gz` to the dev database's `chain_status`, assuming the join file's
  `id` is the K6 key, the convention `grading-recovery` uses): single-candidate matches on K6 reports that are
  `unresolved` 12,329, `extraction_failed` 45, `partial` 5,062; on Pure Canon/other 6,917. About **24,000 reports**
  gain a source-asserted chain, ~17,400 of them with nothing verified today.
- **Cost.** Medium: same alignment code; hadith-kg narrator ids join to `scholar_indx` only by name + death year
  (766 unique), so hadith-kg narrators become a second authority with `narrator_same_as` candidates.
- **Licence.** CC BY 4.0 with the attribution line in `datasets/sources/external/hadith-kg/README.md`.
- **Integrity risk.** Medium. hadith-kg's `sanads.hukum` and `max_rank` are machine-computed isnad verdicts
  ("إسناده متصل ، رجاله ثقات" on 98,652 chains) — **never import them as grades**; they violate "no computed grade".

### 3. Load what is already built: biography and grading candidates
- **Populates** `biographical_assertions`, `citations`, `narrator_assessments`, `hadith_assessments`.
- **Yield.** 17,893 cited assertion candidates + 13,909 citations (Taqrib/Tahdhib/hadith-kg); 5,163 Taqrib verdicts
  attributed to Ibn Hajar; 2,707 Tirmidhi compiler statements; 500 narrators gain a death year, 185 a birth year.
- **Cost.** Small: rows are already shaped for the §5.8 tables; needs the two assertion migrations (§5.14 "later").
- **Licence.** CC BY-NC-SA (OpenITI) and CC BY (hadith-kg) — non-commercial confirmation (untangling-plan step 1).
- **Risk.** Low if shown as "cited, unreviewed"; withhold the 61 Taqrib conflicts.

### 4. Re-source the Sunni Arabic — and consider hadith-kg alongside OpenITI
- **Populates** a lawful public Sunni corpus (today 64,356 Sunni reports are blocked; 23 non-Sunni works can clear).
- **Yield.** hadith-kg reproduces 37,671 of our Sunni reports (58.5%; Nasa'i 93.1%, Ibn Majah 85.7%, Bukhari 78.0%)
  with Arabic under **CC BY 4.0**, which is more permissive than OpenITI's NC-SA. Its `books` table carries edition
  fields (`city, dar, tabaa`) and `hadiths.page_no` is set on 715,783 of 715,790 rows — the page locators the K6
  rows lack entirely (provenance-recovery: 34,441 K6 rows have no volume, page or URL).
- **Cost.** Medium: a per-work re-ingest with `record_id` continuity (keep `k6:` ids, swap the Arabic, re-hash).
- **Licence.** CC BY 4.0 from the compiler; residual: hadith-kg was compiled from hadithdb (2017), whose own terms
  are unknown — same residual class the register accepts for OpenITI's Shamela-family sources. The rights register
  does not mention hadith-kg as a route; it should be assessed next to OpenITI.
- **Risk.** Textual: edition differences change matns; the report-correspondence output can measure it.

### 5. Show the Ibadi and Zaydi English that already exists, labelled
- **Populates** English for 1,702 Ibadi/Zaydi reports (0 today in Postgres; the live Neo4j site shows them).
- **Cost.** Very small if reader mode may show `translation_candidates` with a "machine translation, unreviewed"
  marker; the rights register already rates this English `clear_with_conditions (project MT; review gate)`.
- **Risk.** It is machine output (gemma-4-e4b; the July pilot found fidelity errors). Showing it labelled is honest;
  hiding it makes the two smallest traditions visibly poorer than today's site.

### Also worth doing (smaller or riskier)
- **Riwayat crosswalks** (`narrator_source_id` to `itq`, `kg`, `sh`, `thq`, `mids`): 632 of 644 dual joins agree
  with hadith-kg, 0 disagree — a free consistency check and a bridge to SemanticHadith/MIDS ids.
- **hadith-kg `aqwal`**: 127,863 critic statements, minus 11,660 `تعليق` → ~116,000 attributed jarh/ta'dil
  statements, usable once hadith-kg narrators are an authority (move 2).
- **Najashi/Tusi verdicts** for an Imami authority: 532 + 172 + 78 `ثقة` entries (*doc*); matches 734 Riwayat
  narrators uniquely (28,571 mentions).
- **Imami gradings already loaded** (16,835): nothing more to do except the Mohseni/Behbudi rights question.

---

## 4. Gaps nobody listed (or listed only in passing)

1. **Qur'an linking — none.** No route, table, plan or track mentions it (`grep` of `docs/`, `conductor/`). Yet
   hadith-kg has `hadith_ayas`: **117,194 Qur'an quotations with character offsets in 87,554 hadiths**. Joining
   our matched reports to those offsets, then to a verse-indexed text, gives verse links cheaply. The
   report-correspondence README already names Qur'an quotations as its main false-positive shape — the same index
   would fix that.
2. **Browsing a collection in order — not built.** Routes: `/`, `/hadith`, `/hadith/[id]`, `/narrator`,
   `/narrator/[id]`, `/comparative`, `/glossary`, admin. No collection, book or chapter page; no previous/next on a
   hadith page (`client-page.tsx` has none); the `books` (371) and `chapters` (8,291) tables have no reader query.
   Sunni has **0** reports with `chapter_id` (Imami/Ibadi/Zaydi: 100%). hadith-kg's `topics` tree (54,862 nodes
   over 20,745 meaning groups) is a ready thematic index for matched Sunni reports.
3. **No "how to cite", no dataset version on the page.** `dataset_versions` is excellent internally, but a hadith
   page never shows the version id or a stable citation string, so a published quote cannot be traced to a dataset
   version. Cheap: render `version_label` + short hash + permalink.
4. **The approved preview is currently empty.** `public_hadiths = 0` because the override is on the previous
   version. Every reload needs a re-approval (or the approval should name a policy, not a version). Not a bug in
   the gate; an operational trap before a demo.
5. **Imami, Ibadi and Zaydi pages are visibly poorer than Sunni and than today's site.** 0 identity candidates,
   0 English for Ibadi/Zaydi, no gradings for Ibadi/Zaydi. Yet they are the first works that can lawfully go public
   (23 works, 34,372 reports). The first public release would therefore show exactly the thinnest pages. Moves 1 and
   5 above fix most of it.
6. **Crawl policy.** `X-Robots-Tag: noindex` is set only for admin and sign-in (`src/proxy.ts:19, 61`); there is no
   `robots.ts` or `sitemap.ts`. A preview of unreviewed data is indexable; a release has no sitemap.
7. **Interface language.** `<html lang="en">` (`src/app/layout.tsx:38`); no i18n library or plan. An Arabic archive
   has no Arabic interface. RTL is handled per Arabic block (`ArabicText.tsx` sets `lang="ar"`, `dir`), which is
   correct, but there is no accessibility audit on record.
8. **Researcher export.** `/api/export/hadiths` is curator-only (`requireCurator`). The brief promises "exportable
   with attribution"; there is no public dump with licence and version — the natural partner to the rights gate.
9. **Contribution-system prerequisites not listed.** The plan (`Open_Scholarly_Contribution_System_Plan.docx`)
   needs email registration/verification, roles, endorsements. Missing from §5.15: email delivery, account recovery,
   spam/abuse controls, personal-data handling, and above all a **contributor licence** — derived data is CC BY-NC-SA
   share-alike, so contributions must be licensed compatibly or they cannot be published.
10. **Tests.** No `npm test` script; 14 TypeScript test files, 10 of them Neo4j-era (`src/scripts/__tests__`).
    Flow tests exist for the loader and queries (good), but nothing drives a page, and nothing tests the RTL/Arabic
    rendering or the public/preview gate through HTTP beyond `http-gate.test.ts`.
11. **Search quality.** Normalised substring search works and is fast, but there is no ranking, no stemming/roots,
    and no phrase-with-variants handling (`ة` is kept, so a user typing `الصلاه` gets 41 rows, `الصلاة` 4,661 — the
    query is normalised the same way, so this only bites users typing colloquial spellings).
12. **Hygiene.** Four leftover test schemas (`query_fixture*`, 42 tables each) in the dev database.
13. **Monitoring.** Only an uptime probe on `/api/health` is planned (§2.6); no error tracking, no alert on a failed
    load or a stale preview, no restore drill done yet.

---

## Sharpen

- **Pattern.** Candidate/decision split with a single writer per table (`chain_mention_candidates` vs
  `narrator_surface_decisions`), and *content-addressed versions* (`dataset_versions.id` = projection hash) — the
  reason reload idempotence is provable, not asserted.
- **Architecture.** The verified-identity rule makes Imami chains empty until an Imami authority exists; the cheapest
  mitigation is an external-index basis (Riwayat) shown as a labelled claim.
- **Deferred.** I did not diff Neo4j English cell-by-cell, did not test the hadith-kg id→`k6:` mapping beyond its
  plausibility, and did not measure memory on a Railway instance.
- **Efficiency.** Retire the `neo4j-curation-export` track: the only curated content (21 bios) is already in git.
