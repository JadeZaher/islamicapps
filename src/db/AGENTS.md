# src/db — PostgreSQL + Drizzle data layer

Design source of truth: `docs/architecture/data-architecture.md` (sections 3, 4, 5, 7, 11). This file holds
the rationale that code comments point to, plus every decision taken while implementing step 4.
`src/lib/db/AGENTS.md` describes the outgoing Neo4j layer; its still-valid invariants are carried over below.

## Layout

| Path | What |
| --- | --- |
| `schema/enums.ts` | The 35 enums of section 5.2, the two identity-candidate enums (0006) and the five correspondence enums (0007) |
| `schema/columns.ts` | Pipeline, curation and link bookkeeping column groups; `restrictForeignKey`; `isLive` |
| `schema/operations.ts` | `dataset_versions`, `curation_audit` |
| `schema/corpus.ts` | traditions, sources, collections, collection_rights, books, chapters, hadiths, translations; `public_hadiths`, `public_translations` view declarations |
| `schema/narrators.ts` | narrators, narrator_lexicon_profiles, narrator_aliases, narrator_teachers; narrator_source_profiles, narrator_external_ids, narrator_link_candidates (0010) |
| `schema/evidence.ts` | bibliographic_works, editions, citations |
| `schema/isnad.ts` | chains, chain_mentions, chain_mention_candidates, chain_absence_dispositions, narrator_surface_decisions; `narrator_lifespans`, `narrator_transmissions`, `public_chain_links`, `public_chain_mention_candidates`, `public_chain_mention_candidates_v2` declarations |
| `schema/assessments.ts` | hadith_assessments, narrator_assessments, narrator_bios |
| `schema/history.ts` | locations, historical_events, narrator_events, narrator_locations; `published_historical_events` declaration |
| `schema/commentary.ts` | commentaries, commentary_hadiths, commentary_narrators |
| `schema/comparative.ts` | religious_traditions, schools_of_thought, source_texts, cross_parallels, motif_tags, four link tables |
| `schema/correspondence.ts` | report_correspondence_candidates, report_correspondence_cluster_members, report_correspondence_decisions; `report_correspondence_shown_pairs`, `report_correspondence_display`, `public_report_correspondences` declarations |
| `client.ts` | The app's only client (server-only, lazy, globalThis-cached, max 5) |
| `connection-options.ts` | `DATABASE_URL` check and TLS rule, shared by client, migrator and verify |
| `migrate.ts` | Programmatic migrator (`npm run db:migrate`); the pre-deploy command bundles it to `migrate.mjs` |
| `verify.ts` | Catalog verification (`npm run db:verify`); exits 1 on any mismatch |
| `advisory-locks.ts` | Fixed advisory-lock keys |
| `ops/indexes-heavy.sql` | Concurrent heavy index builds, run by an operator after a load (`npm run db:heavy-indexes`). Never a migration |
| `ops/railway-tuning.sql`, `ops/apply-tuning.ts` | Section 2.4 server settings via `ALTER SYSTEM`, applied by an operator; never a migration |
| `target-database.ts` | `--database development|production` (+ `--confirm-production`) for every operator script |
| `../../drizzle/core/` | The single migration stream (generated plus hand-written SQL) |

## Ownership and the reload contract

Every table has one owner class (section 4.1). Pipeline tables carry `first_seen_/changed_in_/retired_in_dataset_version_id`,
`updated_at`, `retired_at`; a reload upserts by stable ID and retires by anti-join, never deletes. Curation
entity tables carry `created_/updated_/retired_ at/by`; curation link tables carry an identity `id`,
`created_at/by`, `retired_at/by` and a partial unique index on the linked pair `where retired_at is null`.
Nothing is hard-deleted (owner rule); every foreign key is `on delete restrict`, so an accidental delete
fails loudly instead of cascading.

Derived columns on pipeline tables (`chain_mentions.narrator_id/resolution/link_kind/decision_id`,
`hadiths.source_text_status/chain_status/grading_status`, `chains.verified_link_count`) are written only by
the loader and by the SQL functions. Facet defaults are the worst state, so a freshly inserted row is never
shown as better than it is.

## Standing identity (one predicate, three places)

Naming (owner, 2026-11-21): the automatic top tier is **machine-reviewed**, never "verified"; a sample found about 5%
of it wrong where two people share a name. "Verified" is reserved for a reviewer's decision. Enum values and column
names (`verified_link_count`, `verified_basis`, `human_verified`) are unchanged; every reader-facing label and doc uses the
new words, and the teacher-student network built from this tier is machine-reviewed.

Since `0006`: a mention has a standing identity (what the code calls a verified link) when `resolution in ('source_index','human_verified','derived_relation_verified')`
and `narrator_id` points at a live narrator. `exact_registry` is no longer in the list: a name match is a candidate,
never a link. The predicate is written in `public_chain_links` and twice in `refresh_publication_facets` (all three
redefined in `0006_mention_identity_candidates.sql`); `db:verify` fails if the view still names `exact_registry`.
`narrator_transmissions` keeps a stricter rule: both neighbours `resolution_basis = 'source_index'`, or both
`human_decision` (mixed pairs are not counted; owner question below).

## Identity candidates (owner decisions 2026-11-21)

Where the name matcher and the K6 source index both identify a narrator they disagree on 24-49% of matches, so one
`narrator_id` per name misrepresents the data. Decisions: (a) show every identity for a name with its source, both
when they disagree; (b) kunya-only lexicon entries may match, marked; (c) sanads stay per tradition, so automatic
name matches are emitted only for Sunni reports; (d) placeholder lexicon rows are never a target, except kunya-only
rows through (b).

- **`chain_mention_candidates`** (pipeline, written only by the loader): one row per (mention, narrator, basis),
  unique on that triple, with `detail` (resolver tier or K6 agreement class) and `source_position` (set exactly for
  the two source bases, check). Bases: `name_exact` (resolver tier 0), `name_spelling_fold` (tiers 1-2),
  `name_kunya_only` (`kunya_only_candidate` in `regen_unified_csvs.py`), `source_index` (the K6 source's own index
  at a position the Arabic corroborates, in a report whose agreement class is not full), and
  `source_index_confirmed_by_text` (the sidecar's report-level basis `source_index_corroborated_by_text`: full
  agreement, or every source id aligned). `reviewer_decision` is never stored (check): one writer per table, so the
  public view reads it from `narrator_surface_decisions` through `chain_mentions.decision_id`.
- **What sets `chain_mentions.narrator_id`** (the verified identity, meaning unchanged from section 5.5): the loader
  writes it only for a mention with a `source_index_confirmed_by_text` candidate that no other candidate contradicts
  (`resolution = 'source_index'`, `resolution_basis = 'source_index'`, `extraction_method =
  'source_index_confirmed_by_text'`, confidence 1.0); a reviewer decision writes the rest. A name match, a kunya-only
  match and an unconfirmed source index never do. A confirmed but contested mention stays `unresolved` with both
  candidates shown (`verified_narrator` in `export_postgres.py`). **A kunya-only candidate never contests** (owner,
  2026-11-21): it is a label shown beside the other candidates and ignored when deciding whether the identity stands
  and in every analysis; 1,328 mentions gained their machine-reviewed identity with this rule.
- **`narrators.placeholder_reason`** (pipeline): `registry_placeholder_reason` of the lexicon row, so the
  "never a placeholder target" rule is checkable in SQL.
- **`public_chain_mention_candidates`**: every candidate of a public mention with `basis`, `detail` and
  `verified_basis` (confirmed source index or reviewer decision). Unverified candidates appear here and nowhere in
  `public_chain_links.narrator_id` or `narrator_transmissions`.
- **Load invariants** (`load/verify-data.ts`): candidate on a live mention of the same hadith naming a live narrator;
  no placeholder target except `name_kunya_only`, which targets only `kunya_only_name` rows; no name basis on a
  non-Sunni report; an automatic `narrator_id` has its confirming candidate and no non-kunya candidate contests it.

## External identity (0010-0011; owner decisions 2026-11-21, fifth round)

The source identity claims built in `datasets/hadith-data/reconciled/` (hadith-kg, the Riwayat corpus) are loaded as
candidates, following that README's load proposal. Projection rules: `datasets/hadith-data/pg_export/AGENTS.md`
§External identity.

- **External narrators are narrator rows under their own authority** (`narrator_authority` `hadith_kg`, `riwayat`), ids
  `narrator:hadith-kg:<rawi id>` and `narrator:riwayat:<N id>`, `authority_key` the dataset id, no `scholar_indx`. Only
  records some claim or link names are loaded (15,529). The Imams are a fourth authority, `imam_register`
  (`narrator:imam:<1-12>`, from `pg_export/imam_kunya_conventions.json`), so an Imami chain's Imam is never the Sunni
  lexicon's row (no cross-tradition merge).
- **`narrator_source_profiles`** (one per external or register row): the dataset's own fields verbatim (`assertions`
  jsonb), licence, `asserted_by`, and `label_reason` when the source's id names a label as written in chains rather than
  an established person (`riwayat_label_reason`: placeholder name, a name several ids hold with real use, Riwayat's own
  merge or junk flag, a bare nasab). No verdict column (G-1); hadith-kg's `rank` stays in the jsonb and is never shown.
- **`narrator_external_ids`**: Riwayat's crosswalk ids (Thaqalayn, hadith-kg, Itqan, SemanticHadith). **`narrator_link_candidates`**:
  the sidecar's machine links from an external record to a lexicon row, with evidence. Candidates only: they compare two
  claims, never merge narrators (G-5).
- **Candidate bases** added to `mention_candidate_basis`: `source_hadith_kg`, `source_hadith_kg_confirmed_by_text`,
  `source_riwayat`, `source_riwayat_confirmed_by_text` (with `source_position`, `source_ref` and
  `source_assertion_origin`, each set exactly for the external bases, checks), `imam_kunya_convention`,
  `imam_kunya_candidate`. Placeholder reasons added: `relational_name`, `collective_or_anonymous_name`,
  `hadith_kg_stub_narrator`.
- **Standing identity, extended.** The predicate is unchanged (`resolution in (...)` and a live `narrator_id`; written once
  in `public_chain_links`, twice in `refresh_publication_facets`); what the loader may write into `narrator_id` widened.
  `resolution`/`resolution_basis` stay `source_index` (the historic name of the automatic tier, like
  `verified_link_count`) and `extraction_method` names the evidence: `source_index_confirmed_by_text`, `two_sources_agree`
  (a K6 claim and a hadith-kg claim whose person keys meet), `source_hadith_kg_confirmed_by_text`,
  `source_riwayat_confirmed_by_text` (an annotation origin, never `riwayat_automatic_linking`, never a label record),
  `imam_kunya_convention`. Uncontested means no two contesting candidates name different people of one registry: person
  keys bridge records through link candidates and Riwayat's single hadith-kg crosswalk id; an unlinked pair across
  registries is not comparable. Kunya-only names, an undecided shared Imam kunya and placeholder records never contest.
  The teacher-student view inherits the tier unchanged (both neighbours `resolution_basis = 'source_index'`).
- **Views (0011).** `public_chain_links` gains `name_latin`, `name_latin_basis`, `name_latin_narrator_id` and
  `standing_basis` at the end. `public_chain_mention_candidates` now returns only the pre-0010 bases, so a build that
  predates them reads what it understands; `public_chain_mention_candidates_v2` returns every basis with `source_ref`,
  `source_assertion_origin` and `tier_basis`. `db:verify` checks both definitions.
- **Load invariants** (`load/verify-data.ts`): no candidate targets a placeholder except the labelled kinds; an automatic
  `narrator_id` rests on the evidence its `extraction_method` names and is uncontested (person keys, same rule as the
  projection); the tier never rests on a Riwayat automatic link; Imam-kunya candidates only in Imami chains and only on
  register rows; external narrators carry one profile naming their source; provider English only on Imami Thaqalayn
  reports.

## Latin names (0010)

`chain_mentions.name_latin` / `name_latin_basis` (`name_latin_basis` enum) / `name_latin_narrator_id`: every name in a
chain carries a Latin form where a source or rule gives one, computed in the projection, never at request time:
`provider_english` (Thaqalayn's English sanad, Imami only), `identity_name` (the English name of the standing identity,
or of the one person all candidates name; the narrator whose name it is is recorded), `transliteration_vocalized`,
`transliteration_table`. A check keeps the three columns consistent. `narrators.name_latin` / `name_latin_basis` carry a
transliteration for external rows, which have no English name. Rules: `datasets/hadith-data/pg_export/AGENTS.md`
§Latin names.

## OpenITI extraction fields (0012; owner request 2026-11-21)

The corrected parse of al-Rabi, Musnad Zayd and Sahifat al-Rida (`datasets/parse_openiti.py`, `extraction-quality/fixed/`)
splits a report into an Arabic chain span and a matn, notes where a chain repeats an earlier one, and separates the
edition's own notes from the text. Four nullable columns on `hadiths` carry it; they are NULL for every other work.

- `sanad_ar`: the chain span exactly as written in `text_ar` (a substring, checked at load), NULL unless the split is confident.
- `split_confidence` (`high` | `low`, check): `low` means the parser left the text whole: `sanad_ar` and `matn_ar` are NULL
  and the page shows `text_ar` once, with no split.
- `sanad_inherits_from`: the id of the report whose chain a continuation («وبهذا السند», «وباسناده», «ومن طريقه») repeats,
  checked at load to be a live report of the same collection. No foreign key: a self-reference would order the merge.
- `source_notes` (jsonb list, check): `{kind, text_ar}` with kind `compiler_comment` (al-Rabi's own remark or gloss),
  `arranger_note`, `editor_footnote` or `note`. Never part of `text_ar`; the page shows them in their own labelled block credited
  to OITI. One column, not a table: notes live and die with the report row, so they can never be bound to stale Arabic, and no
  loader path or `NOT NULL` English column (`commentaries.text`) is involved.
- Projection: `reconciled/openiti_extraction.jsonl.gz` (built by `build_openiti_extraction_sidecar.py`, hash-bound to the exact
  `text_ar`); `export_postgres.py` refuses an OpenITI report without a row, a row bound to other Arabic, or a dangling inheritance.
- `public_hadiths` is `select h.*`, whose column list froze at creation: 0012 replaces it with the same body, which appends the
  new columns at the end and leaves every dependent view alone. A build older than 0012 reads the columns it knows.
- Ids: `#2`, `#3` mark parts the parser split off a numbered report (`hadith:openiti:rida:rida_0004#2|4|V01P442`); the `#`
  is part of the id and is percent-encoded in the URL (`reportPart` in `src/lib/citation/reference.ts` words it "No. 4, part 2").
  An id the parser absorbed into another report is retired by the loader like any report that leaves a projection: the row is
  kept, readers get 404 (no redirect).
- Sahifat al-Rida stays Imami (`openiti:imami:rida_*`, as loaded since the first load). The first corrected parse had set
  its tradition to Zaydi, which would have retired all 35 ids; `parse_openiti.py` is fixed and the record ids are unchanged.
- Load invariants (`load/verify-data.ts`): a stored span lies inside its own text and a low-confidence split stores none; a
  continuation names a live report of the same collection; every source note has a known kind and Arabic text.

## Chain chronology guard (0013; owner report 2026-11-21)

The owner found wrong teachers on narrator pages (ʿUmar b. al-Khattab, d. 23, "taught by" al-Awzaʿi, d. 157). Three causes:
the K6 source index names a homonym and "confirmed by text" only checks that the name agrees; a flattened tahwil puts two
routes in one chain; and the 0006 view tested only one side of the chronology. Positions: 0 is the collector's own shaykh,
p+1 is the teacher of p (in Bukhari the higher position dies earlier in 12,348 of 14,071 dated pairs).

- **One rule, two places.** `datasets/hadith-data/pg_export/chain_chronology.py` `transmission_chronology` and the
  `narrator_transmissions` CASE: a pair is impossible when the student was born after the teacher died, the teacher was
  born after the student died, or the teacher died more than 60 years after the student (lexicon years; a recorded 0 is not
  a year). The 60 is measured: of the 26,530 pairs the lexicon's own teacher lists name with both deaths known, 0.35% put
  the teacher's death more than 60 years after the student's (0.87% at 40, 0.11% at 100), and those are mostly the
  lexicon's own century slips (Khalid b. al-Harith d. 106 for 186). A pair the lexicon's teacher list names is never
  impossible: it is `disputed` ("the lexicon lists this teacher, but its years say ..."), because a year is wrong, not the
  identity. `narrator_teachers` stays "never transmission evidence"; it is used only as evidence that a date is wrong.
- **Projection (identity).** A standing identity that makes an adjacent pair impossible is withheld:
  `chain_mentions.narrator_id` stays NULL, every candidate stays, and `identity_withheld_reason` says why in plain words
  (check: never on a `source_index` row). The loader treats it as part of the derived identity tuple
  (`derivedFromStaging` in `load/tables.ts`), written in the same statement as `resolution_basis`: as a content column it
  was merged first and the check failed mid-load (first production attempt, rolled back). Who is withheld is decided per pair (`pg_export/AGENTS.md` §Chain chronology):
  the name in conflict with two or more dated members of its route while its partner conflicts only with it; else the one
  the lexicon's teacher lists do not tie to its other neighbour; else both, with "the chain cannot tell which of the two
  names is wrong". A student born at most 20 years after the teacher died is left standing (a broken chain, irsal, does
  not show a wrong identity; al-Nakhaʿi from Ibn Masʿud is 15): the view still labels the pair impossible.
- **Seam guard (view).** A narrator standing twice in one chain marks a flattened tahwil. Every pair between his first and
  last position is dropped (`seams` CTE): the seam lies in that window and nowhere else, so no cross-route pair survives and
  no pair outside it is lost. A repeated narrator is never withheld by the projection (that would move the seam). Re-splitting
  branches is not done (the Sunni audit lane's seam list, next round).
- **Reads.** `getNarratorNetwork` drops `impossible` pairs from both lists and both totals; undated pairs stay.
  `public_chain_links` appends `identity_withheld_reason` (CREATE OR REPLACE); the chain view and the narrator's chain list
  show it beside the candidate. `db:verify` checks the view keeps the symmetric rule, the 60 and the seam CTE; `db:verify-data`
  checks a withheld mention keeps a tier candidate and that no standing source-index pair outside irsal range is impossible.
- **Lexicon fields (same migration).** `narrator_lexicon_profiles.source_fields` (jsonb object): places of stay, parents,
  spouses, siblings, children (with the lexicon's `[N]` entry numbers), tags and interests verbatim, brackets stripped from
  tags and interests (they carry slugs and a `[Grade:Thiqah]` label, which is never shown). `tabaqah_raw` now carries the
  lexicon's `grade` column, which is its generation class (`Comp.(RA) [1st Generation]`; 43 distinct values, all classes,
  centuries, generations or a madhhab), never a reliability verdict.

## Chain builder (0014; owner request 2026-11-22, round 2)

Two audits (`datasets/hadith-data/chain-audit/ibadi-zaydi/`, `imami/`) found order right everywhere and the defects in how
chains are cut. The builder, not rows by hand, is fixed: `datasets/hadith-data/pg_export/chain_builder.py`
(`pg_export/AGENTS.md` §Chain builder).

- `chain_mentions.inherited_from_mention_id` (nullable, no FK: a self-reference would order the merge): the written mention
  a continuation repeats. The row copies that mention's surface and candidates, so the name shows and feeds the teacher list.
  Checked at load: a live written mention of the same collection with the same surface, in a report that inherits a chain.
- `mention_candidate_basis.named_in_opening_isnad`: the work's own opening isnad names the person (Musnad Zayd only,
  `opening_isnad_rules.json`); the detail cites the opening report. A tier basis (`public_chain_mention_candidates_v2`,
  `standing_identity`), credited `OITI`. Register rows may be its target (`narrator:imam:<n>`, and `narrator:imam:zayd`, which
  the register lacked: added under the register mechanism, its profile naming Musnad Zayd `zayd_0001`).
- `link_kind` is now written for these chains: `derived_relation` («أبيه», «جده» read through the rule), `anonymous` (a
  balagh gap). The chain view words them ("From the earlier report's chain", "Unnamed transmitter").
- `public_chain_links` appends `inherited_from_mention_id` (CREATE OR REPLACE). `db:verify` checks it and the tier basis.
- **0015 (Imami chains).** `chains.suspension` (check: `back_reference`, `mid_chain_start`, `route_given_elsewhere`): the chain
  relies on another; the page says so in plain words. `public_chain_links` appends `chain_suspension`. `narrator_transmissions`
  (0013 body) adds one guard: an `anonymous` or `not_a_narrator` position is never one side of a pair. `db:verify` checks both;
  `db:verify-data` checks that no such position carries an automatic identity.
- **0016 (Sunni chains).** `mention_candidate_basis.edition_identification` (a printed edition's note names the person; a tier
  basis that stands over the source index it corrects, so it is exempt from the uncontested check; Sunni lexicon rows only, detail
  required) and `chains.missing_link_after` (check: inside the chain). `public_chain_links` appends `chain_missing_link_after`.

## Chain structure gate (0017; owner request 2026-11-22, round 4)

Three rounds of builder rules did not move the Sunni strict chain-defect rate (10.7% -> 17.3% -> 18.0%), and the owner's
complaint is wrong teachers and students. So the goal changed to the precision of what is asserted: a chain whose structure
no tested rule stands behind is shown as stored, says so, and forms no teacher-student pair. Detectors, measurement and the
operating point: `datasets/hadith-data/pg_export/AGENTS.md` §Chain structure gate; numbers in
`datasets/hadith-data/chain-audit/structure-gate/`.

- `chains.structure_status` (`checked_by_rule` | `uncertain`) and `chains.structure_reasons` (text[] of stable codes from
  `pg_export/chain_structure.py`), one check: checked has no reasons, uncertain has at least one. NULL only on rows loaded
  before 0017: the view treats NULL as before the gate, so production kept its network between the migration and the load.
  `checked_by_rule` is never worded "verified" ("verified" is reserved for a human decision).
- `narrator_transmissions` (0015 body) adds one guard: `c.structure_status IS DISTINCT FROM 'uncertain'`. The seams CTE is
  computed from the same standing set, so an uncertain chain neither forms pairs nor moves a seam. Narrator page lists and
  totals read the view, so they follow.
- `public_chain_links` appends `chain_structure_status` and `chain_structure_reasons`; the chain view shows one plain line
  under an uncertain chain ("The reading of this chain's routes has not been checked; it is not used for teacher and student
  lists") and the reasons in words (`src/app/hadith/[id]/components/chain-structure.ts`).
- Retired, not flagged: every chain of Kitab al-Duafa and Risalat al-Huquq (prose and rijal entries), and chains read from a
  Sunni chapter heading («باب …» as the report text). The loader retires their earlier rows; reports stay.
- Round 5 recalibrated the detectors (no schema change): the 15 small Imami works are no longer withheld as a block and new shape tests were
  added (`pg_export/AGENTS.md` §Gate recalibration). The out-of-sample rates are in `chain-audit/round4/`; `/method` states them.
- `db:verify` checks both view changes; `db:verify-data` checks every live chain has a status and every network pair stands
  in a live checked chain. Flow test: `queries/__tests__/structure-flows.test.ts`.

## Chain fixes (0019, 0020; owner 2026-11-22)

Model readers read a report's Arabic and write its routes; agreeing, unheld readings replace the rule-built chain, labelled. Design,
states, rules: `docs/review/chain-fix-pipeline.md`; tools: `reviews/ai/tools/chain-fix-*.ts`, `reviews/ai/AGENTS.md`.

- **Tables** (`schema/chain-fixes.ts`): `chain_fixes` (immutable reading bound to the Arabic and the reader text),
  `chain_fix_submissions` (one reader run, with model, prompt hash, packet, quotes), `chain_fix_decisions` (curation; retired rows are
  the transitions; states add `held` with `hold_codes`), `chain_fix_reviews` (one row per reviewer; AI rows name model and prompt),
  `chain_fix_applications` (every database write with `base_rows`, so a revert is exact), `chain_fix_work_settings` (per work: may a
  chain read by model feed lists; seeded `false` for every work). One writer for all: `ops/chain-fix-apply.ts` (`npm run db:chain-fixes`;
  flow test `ops/__tests__/chain-fix-apply.test.ts`). They are curation-class: never in the load contract, never block a load.
- **`chains.chain_fix_id`** (content column) and two structure statuses, `read_by_model` and `verified_by_reviewer` (check: no
  reasons, a fix named). "Verified" only after a named person's confirmation. The projection replays the overrides file after every
  builder and before the gate (`pg_export/AGENTS.md` §Chain fixes); an absent file is a no-op.
- **Ids are reused**: the unique keys on (hadith, branch) and (chain, position) span retired rows, so a fix writes the projection's own
  ids and keeps the rows it replaced in `base_rows` instead of retiring them beside new ones.
- **Network guard** (`narrator_transmissions` `feeding` CTE): rule-checked and reviewer-verified chains feed lists; a chain read by
  model only where `chain_fix_work_settings.read_by_model_in_network` is true for its collection (false everywhere at 0019).
- **0020** widens `chain_fix_submissions.view` with `text_and_context` (reader v3: text and the sources' context, never the stored
  chain; blind for the agreement rule).
- **Not applied by any tool**: readers' other findings (identity, lexicon dates, duplicates, text, translation, metadata). They are a
  file store only this round (`reviews/ai/records/chain-fixes/proposals/`), listed by `chain-fix-status --proposals`; no table yet.
- `db:verify` checks the widened status check, the network guard and the view tails; `db:verify-data` holds nine chain-fix checks and
  reports (not fatal) a rejected fix still applied.
- **0021 (first model-read fixes, 2026-11-22).** Additive. `chain_fixes.disposition` (`no_chain_by_reading`, check: no planned chain),
  `chain_fix_submissions.tool_version` (`v3` | `v3_1`: the reader tool that expanded and held the reading; the prompt columns name what
  the reader ran) and `inherited_from` (jsonb list). **Where "no chain by reading" lives**: on the fix, not in `chain_absence_dispositions`.
  That table is curated "no isnad by nature" with its own writer (the curation actions); a model reading awaiting review is a different
  claim with a different writer (`chain-fix-apply.ts`), it reverts with its fix, and a load replays it from the overrides file. One writer
  per table holds. View `public_chain_fix_dispositions`: one row per public report whose latest application of such a fix is `applied`,
  whose live decision has an effect, bound to the current Arabic, with no live chain; the page reads it. View
  `public_chain_fix_mention_kinds`: per mention of a model-read chain, `imam_in_text` or `inherited` from the fix's plan, so the page
  labels the source named in the text without a new mention column. An inherited name is a real `chain_mentions` row with
  `inherited_from_mention_id` (the 0014 mechanism); the inherited-mention load check now also accepts `extraction_method = 'chain_fix_reader'`.
  Two new `db:verify-data` checks: an applied no-chain fix leaves no live chain and plans none; an inherited name in a model-read chain
  repeats a mention of a rule-checked or reviewer-verified chain.

- **Variant remarks (2026-11-22, no migration).** A remark that another version names another transmitter lives in
  `chain_fixes.planned -> 'variant_remarks'` (the immutable fix row already holds `planned` jsonb; its check only types `chains`), never in
  `chains`, `chain_mentions` or a view of its own. The page's chain query (`chainNodesJson`) reads it beside `public_chain_fix_labels`
  (which gates publication), so a revert, a rejection or a changed text removes it with the chain. `routes_key` and the structure
  gate ignore it. A view would have meant a migration and a load for no new data.

## Compiler as first transmitter (0019; owner ruling 2026-11-22)

Every chain of a work with a known compiler is headed by him: `chains.compiler_narrator_id` and `compiler_link` (`direct` |
`indirect`, check: both or neither). Derived, never a mention: mention ids, positions and the structure gate's text checks are
untouched. Rules: `datasets/hadith-data/pg_export/AGENTS.md` §Compiler as first transmitter.

- **Pairs**: `narrator_transmissions` adds (compiler, position 0) for a `direct`, unsuspended, feeding chain whose position 0 stands,
  student position -1, method `compiler_of_work`; the same chronology CASE applies. `db:verify-data` accepts such a pair as standing.
- **Records**: `narrator_authority.work_register` (`narrator:work:<slug>`), a person the work credits (its compiler, or a transmitter
  it names in full: Abu ʿUbayda Muslim b. Abi Karima in Musnad al-Rabiʿ), with a `work_register` profile naming the work. Reused rows
  where a standing rule of that tradition already identifies the person (Malik, Ahmad, al-Darimi, Abu Dawud; al-Kulayni and
  al-Husayn b. Saʿid as Riwayat records). `named_in_opening_isnad` may now target `work_register` rows, in Musnad al-Rabiʿ too.
- `public_chain_links` appends `chain_fix_id`, `chain_compiler_narrator_id`, `chain_compiler_link`; the chain view shows the compiler
  above position 0 with "Compiler of the work; not written in the text".

## Report correspondences (0007; design §5.5.1)

Reports that carry the same matn in another work or tradition, from `diagnostics/report-correspondence/`. Reports are
linked, never narrators or chains. One writer per table: the loader writes candidates and cluster members; curators
write decisions.

- **Pair order is byte order.** `hadith_id_a < hadith_id_b` is checked `collate "C"`: the database collation
  (`en_US.utf8`) ignores punctuation at the first level, so it can order `hadith:k6:…` ids differently from the Python
  job. `orderPair` in `queries/correspondence-decisions.ts` orders by bytes too.
- **Hash binding, twice.** The projection drops (and counts) a pair whose Arabic hash differs from the loaded text; the
  display rule also joins both hashes, so a text changed by a later load hides the pair until it is rebuilt. A decision
  binds to the hashes the reviewer read and applies only while both still match: re-queued, never silently reapplied.
- **One display rule.** `report_correspondence_shown_pairs` (confirmed at any score; else same wording, variant at
  Jaccard >= 0.4, partial at containment >= 0.7, unless rejected). `report_correspondence_display` is both directions;
  `public_report_correspondences` adds the public gate. All three are written without CTEs: a CTE referenced twice is
  materialized whole, which would scan every pair for one report's family.
- **Decision semantics.** `confirmed` means one report or passage; a confirmation may carry only a machine class as its
  reading (check). `same_ruling_different_attribution`, `shared_formula_only`, `shared_quran_quotation` go with a
  rejection or uncertain. Revising retires the live row and points the new one at it (`supersedes_decision_id`).
- **FK names.** The two pipeline tables pass a short prefix (`report_corr_*`) to `pipelineBookkeepingForeignKeys`: the
  full table names push the generated names past Postgres's 63 bytes (decision 4 below), which `db:verify` caught.

## Migrations

- One stream, `drizzle/core`, applied by `src/db/migrate.ts`: `lock_timeout 5s`, `statement_timeout 60s`,
  the data-write advisory lock, three retries on lock timeout. The drizzle 0.45.4 migrator runs all pending
  migrations in ONE transaction (verified in `pg-core/dialect.js`), so `create index concurrently` can never be
  a migration: heavy indexes live in `ops/indexes-heavy.sql`.
- Order: `0000_extensions` (pg_trgm, unaccent; idempotent) -> `0001_core_schema` (generated) ->
  `0002_table_storage` (fillfactor 90) -> `0003_views` -> `0004_functions` -> `0005` (research feature removed) ->
  `0006_mention_identity_candidates` (generated table, enums and column, then hand-written: `public_chain_links`
  and `refresh_publication_facets` redefined, `public_chain_mention_candidates` created, `narrator_transmissions`
  dropped and recreated with its two indexes) -> `0007_report_correspondences` (generated tables and enums, then the
  three hand-written views) -> `0008_epochs` (the history lane's pending `epochs` table and `published_epochs` view,
  promoted from `ops/pending/`; idempotent) -> `0009_public_english_policy` (enum value
  `source_provided_and_machine_allowed`, `public_translations` redefined; see §Public English) ->
  `0010_external_identity` (generated: enum values, the three external tables, Latin-name and source-reference columns,
  checks) -> `0011_external_identity_views` (hand-written views, see §External identity) -> `0012_openiti_extraction_fields` (generated:
  four nullable `hadiths` columns and two checks, then a hand-written `CREATE OR REPLACE VIEW public_hadiths`, see §OpenITI
  extraction fields) -> `0013_chain_chronology_guard` (generated: `chain_mentions.identity_withheld_reason`,
  `narrator_lexicon_profiles.source_fields` and two checks; hand-written: `public_chain_links` appended, `narrator_transmissions`
  dropped and recreated with its two indexes; see §Chain chronology guard) -> `0014_chain_builder_openiti` (generated:
  enum value `named_in_opening_isnad`, `chain_mentions.inherited_from_mention_id`; hand-written: `public_chain_links` appended,
  `public_chain_mention_candidates_v2` counts the new basis; see §Chain builder) -> `0015_chain_builder_imami` (generated:
  `chains.suspension` and its check; hand-written: `public_chain_links` appended, `narrator_transmissions` dropped and recreated
  with the anonymous-gap guard and its two indexes) -> `0016_chain_builder_sunni` (generated: enum value
  `edition_identification`, `chains.missing_link_after` and its check; hand-written: `public_chain_links` appended,
  `public_chain_mention_candidates_v2` counts the new basis) -> `0017_chain_structure_gate` (generated: `chains.structure_status`,
`structure_reasons` and their check; hand-written: `public_chain_links` appended, `narrator_transmissions` dropped and recreated
with the structure guard and its two indexes; see §Chain structure gate) -> `0018_machine_english_gate` (hand-written: the machine branch
  of `public_translations` also needs a recorded model and provenance; see §Public English) -> `0019_chain_fixes_compiler` (generated:
  the six chain-fix tables, `chains.chain_fix_id`/`compiler_narrator_id`/`compiler_link`, the widened structure check, enum value
  `work_register`, the widened profile source check; hand-written: settings seeded off, `public_chain_links` appended,
  `public_chain_fix_labels`, `narrator_transmissions` dropped and recreated with the feeding guard and compiler pairs; see §Chain fixes,
  §Compiler as first transmitter) -> `0020_chain_fix_reader_v3_view` (the `text_and_context` view) -> `0021_chain_fix_dispositions` (generated:
  `chain_fixes.disposition`, `chain_fix_submissions.tool_version` / `inherited_from` and their checks; hand-written: views
  `public_chain_fix_dispositions`, `public_chain_fix_mention_kinds`; see §Chain fixes) -> `0022_chain_fix_tool_v3_2` (generated: the
  `tool_version` check widened with `v3_2`). A `--custom` generate snapshots the previous schema: after promoting a
  table into `schema/`, check `drizzle-kit generate` reports no changes, and fold its snapshot into the custom one if not.
- Hand-written migrations are created with `npx drizzle-kit generate --custom --name=<name>` so the journal
  and snapshot stay consistent; views are declared in TypeScript with `.existing()` so drizzle-kit ignores them.
- Expand only (section 2.6). Views written as `select h.*` freeze their column list at creation: adding a
  column to `hadiths` or `translations` needs the dependent public views recreated in the same migration.
  `narrator_transmissions` depends on `narrator_lifespans`; redefining lifespans means drop and recreate the
  materialized view (and its two indexes) in that migration.
- `pgvector` is installed on the Railway database but is created by the step 11 migration, not here.

## Locks

`DATA_WRITE_LOCK_KEY = 4741100001` (migrator and loader, session-level). `NETWORK_REFRESH_LOCK_KEY = 4741100002`
(`refresh_network`, transaction-level). `refresh_network()` takes the data-write key **shared** with
`try`: another session's load or migration makes it return false, while the loader's own session (which holds
the key exclusively) can still call it. The literals are duplicated in `0004_functions.sql`.

## Client

`getDatabase()` creates the postgres.js pool on first use, never at import (so `next build` never connects),
and caches it on `globalThis` so dev hot reload does not multiply pools. `db` is a Proxy over it. Options per
section 3.3: `max 5`, `idle_timeout 20`, `connect_timeout 5`, prepared statements on (no transaction pooler).
On SIGTERM it ends the pool with a 5 s timeout and exits only when no other SIGTERM listener (Next.js) exists.
Scripts (`migrate.ts`, `verify.ts`) never import `client.ts`: `server-only` throws outside the react-server
condition.

## Carried over from src/lib/db/AGENTS.md (still valid)

- Narrator and event scalar fields are compatibility projections, not publication evidence. No loader may treat a
  provenance tag, a raw date string or an unverified seed marker as a citation.
- The historical publish gate (`publication_ready`, `human_verified`/`source_verified`, nonblank
  `citation_source`, nonblank `citation_locator` or `citation_url`) is now enforced twice: the
  `historical_events_publication_gate_check` constraint on write and `published_historical_events` on read.
- The history seed may refresh an event's content only while it is `unverified_seed` and not
  `publication_ready`. A changed seed definition for a reviewed or published event needs a new review.
- Competing evidence is never collapsed: separate assertion rows, lifespans as ranges. A cited unknown or open
  range is valid; an exact year is never invented.
- Narrator-by-event overlap is computed at read time on `narrator_lifespans` x `published_historical_events`;
  no overlap rows are stored. Only direct involvement (`narrator_events`) is persisted.
- Stable unique keys for people, works, editions, citations, assertions, events and epochs (section 4.2).

## Decisions made during implementation (step 4)

Where the doc was ambiguous or contradicted the orchestrator brief, the stricter reading was chosen.

1. **Layout.** Schema files are flat in `src/db/schema/<domain>.ts` (orchestrator brief) instead of the doc's
   `schema/core/`; migrations stay in `drizzle/core` (doc). `narrator_bios` lives in `assessments.ts`,
   `dataset_versions` and `curation_audit` in `operations.ts`.
2. **Only the 40 launch tables are declared.** The doc says schema files for the 7 later tables exist from
   step 4, but declaring them would make drizzle-kit migrate them. Each later table (`translation_candidates`,
   `resolution_review_units`, `narrator_same_as`, `biographical_assertions`, `temporal_assertions`, `epochs`,
   `hadith_embeddings`) is declared together with its migration. No launch table has a foreign key into them.
3. **All 35 enums are created,** including `calendar`, which only later tables use (harmless, expand-only).
4. **Explicit constraint names** (`<table>_<column>_fk`, `_key`, `_check`, `_idx`): drizzle's default FK names
   exceed Postgres's 63-byte limit and would be truncated silently.
5. **Every FK is `on delete restrict`;** the doc states no other behaviour anywhere.
6. **`chain_absence_dispositions` carries curation bookkeeping.** Its table omits the line, but section 5.1 puts
   it on every curation entity table.
7. **Public override is all-or-none over three columns:** `num_nonnulls(public_override_by, public_override_reason,
   public_override_at) in (0, 3)` (the doc's check names only by and reason) and only on `non_release`.
8. **Surface decision target is an equivalence:** `target_narrator_id` is set if and only if the kind is
   `same_as` or `derived_relation` (the doc says "required for"; a collective or anonymous decision with a
   target would be incoherent, since replay assigns no narrator).
9. **`cross_parallels.status` has no column default.** The doc's default depends on `origin` (`proposed` for
   `ai_research`, `published` for `manual`), which a column default cannot express; the writer must set it.
10. **Verified link requires a live narrator** (see above). Consequence: `human_verified` mentions with link kind
    `collective`, `anonymous` or `not_a_narrator` are not links, so such a chain is `partial`, not `complete`.
11. **`narrator_lifespans` before assertions ship:** death prefers a `published` bio whose citation is live and
    reviewed (section 5.8 predicate), else the lexicon; birth comes from the lexicon only (bios have no birth
    year); `basis` is the weakest source any bound came from; one row per live narrator with at least one bound;
    `claim_count = 0`, `disputed = false`.
12. **`public_hadiths`** also requires a live collection, a live `collection_rights` row and the current version's
    `load_status = 'complete'`. **`public_chain_links`** exposes `narrator_id` and `confidence` only on verified
    links and returns every live mention, so the isnad always reads as written.
13. **`grading_status`:** `collection_label` rows are ignored (they are never a grade), so "only
    `compiler_criterion` rows" means only among displayable kinds.
14. **`source_text_status`:** "blank" Arabic means no non-whitespace character; the locator fields are
    blank-trimmed too.
15. **`text_tsv`** is `to_tsvector('english'::regconfig, text)`; the explicit cast keeps the generated column
    immutable.
16. **`refresh_network()`** skips via the shared data-write lock instead of reading `load_status`, so a stale
    `loading` row cannot block it forever and the loader can call it; it stamps `network_refreshed_at` on the
    current version. Both functions have `EXECUTE` revoked from `PUBLIC`; `roles.sql` will grant it to `app_rw`.
17. **`refresh_publication_facets(hadith_ids text[])`** is implemented now (section 11.2 is fully specified);
    `apply_decision(unit_id)` is not (see Deferred).
18. **TLS:** an explicit `sslmode` in the URL wins; otherwise the doc rule (off for `*.railway.internal`,
    `require` elsewhere).
19. **`db:migrate` runs `src/db/migrate.ts`,** not `drizzle-kit migrate`, so the lock and timeouts apply locally
    exactly as in the pre-deploy command.
20. **`maintenance_work_mem = '128MB'`** in `indexes-heavy.sql` is a chosen value; the doc gives none.
21. **`db:verify` is the catalog half** of the doc's `db:verify`. The section 11.4 data invariants and the server
    settings checks join it in step 5.
22. **Environment override:** the database is Railway PostgreSQL 18.6, used directly; the doc's local
    `pgvector:pg18` container on 5442 was not set up (orchestrator instruction).

## Public English (0009; owner decision 2026-11-21)

All 34 works are cleared with `english_policy = 'source_provided_and_machine_allowed'` (`npm run db:record-rights`).
`public_translations` then exposes reviewed English, `source_provided` English and `machine_unreviewed` English, each row
with its `state`, `source`, `translator` and `model`; `unknown_provenance` never (it cannot be credited). The page labels
each row through `englishLabel`/`englishReference` (`src/lib/sources/report-credit.ts`): "Source-provided English, not
reviewed here" credited to the text source and its translator (`WORK_CREDITS`), or "Unreviewed machine translation.
May contain errors that change the meaning; the Arabic is authoritative." (owner 2026-11-22) credited to `SWI`, the model in the credit line.

- **Why the policy is compared as text.** The migrator runs every pending migration in one transaction, and Postgres
  refuses an enum value as a literal in the transaction that added it ("unsafe use of new value"), so `0009` and the load
  check compare `english_policy::text`. `db:verify` fails if the view loses the machine branch, gains
  `unknown_provenance`, or drops the quality or hash gate.
- **Honorific symbols are not leakage** (projection `2026.11.21.4`). 10,650 Sunni and 9 Imami source-provided English
  texts were held out of `public_translations` as `arabic_leakage` only because they write ﷺ (U+FDFA), a one-character
  honorific symbol, which the bundle's release QA counts as Arabic script. The projection reclassifies a text whose only
  Arabic-script characters are those symbols as `complete` (`english_quality`, counted in
  `counts.translation_quality_reclassified`); 741 Imami texts with real Arabic stay held. Sunan Abi Dawud `k6:19122` was one.
- **What is loaded (0018, 2026-11-22).** Machine English reaches `translations` through the projection, not a candidate table:
  `export_postgres.py --machine-english machine_translation_candidates/machine_english_overlay.jsonl.gz` (written by
  `diagnostics/translation-run-2/translate_gap_fill.py finalize`, hash-bound in the manifest) feeds
  `pg_export/machine_english.py`, which re-gates every draft (hash equals the report's, screen accepted, pinned model, not
  truncated, no Arabic script beyond honorific symbols, Latin share, length ratio, no refusal or meta text) and writes a
  `machine_unreviewed` row with `model` and a `provenance_source` naming journal, prompt version and hash, provider and time.
  The table is unique on (hadith, language), so a report has one English row: **source-provided English first** (a report with
  complete reviewed or source English keeps it and gets no machine row); a report whose source English fails QA has that row
  replaced in place (same id); the machine draft is never shown beside it. `translation_candidates` stays unmigrated (the
  candidate stream still lists drafts, including those held out).
- **Gate in the database.** `0018` adds `t.model IS NOT NULL AND t.provenance_source IS NOT NULL` to the machine branch of
  `public_translations`; `db:verify` fails if either is missing from the view. `db:verify-data` checks that every public row is
  complete, hash-bound and within policy, that every live `machine_unreviewed` row is complete, hash-bound and names model,
  source and provenance, and that `unknown_provenance` English never exists (the old "no candidate-only rows" check now covers
  only that, assessments and citations).

## Operator scripts and production

Every operator script defaults to the development database (`DATABASE_URL`) and refuses the production database there.
Production needs both `--database production` and `--confirm-production` (`target-database.ts`), which points
`DATABASE_URL` at `DATABASE_URL_PRODUCTION` for that process only: `db:load`, `db:verify-data`, `db:heavy-indexes`,
`db:seed-history`, `db:seed-narrator-bios`, `db:approve-preview`; `db:record-rights` and `apply-tuning.ts` require
`--database` explicitly. `db:migrate` and `db:verify` read `DATABASE_URL` as before (set it for the one command). The
production flag is deliberately two words: a script never writes production because one variable was mistyped.

## Server tuning (section 2.4)

`ops/railway-tuning.sql`, applied with `npx tsx src/db/ops/apply-tuning.ts --database production --confirm-production`
(server-wide: development and production share the server), then `pg_reload_conf()`. Never restarts; prints what waits
for a restart (`shared_buffers`, `max_connections`, `huge_pages`). Deviation: `max_connections = 40`, not 20, because the
development database, its test fixtures and the loader share the server with the production app (decision 22). Restricted
roles (`ops/roles.sql`) are still deferred, so every client is the template superuser and the 3 reserved slots are not
headroom.

## Deferred

- External identity: the Qur'an citation table (README proposal d) is not loaded; Riwayat's Imami label records stand
  only as candidates when label-like; bare Abu Jaʿfar / Abu al-Hasan / Abu Muhammad with the marker stay undecided
  candidates until the owner rules on them (`imam_kunya_conventions.json`).
- Identity candidates: mixed transmission pairs (one confirmed source-index neighbour, one human decision); whether a
  kunya-only candidate should contest a confirmed source identity (it does now); source-index claims that name a
  placeholder row are dropped and counted in the projection manifest, not emitted; the narrator page still lists
  only reports where the narrator is a verified link.
- `ops/roles.sql` (`schema_owner`, `app_rw`, grants, `app_rw` timeouts). The step 4
  migrations ran as the Railway template superuser, so every object is owned by it: `roles.sql` must
  `REASSIGN OWNED` / `ALTER ... OWNER TO schema_owner` before the app switches roles.
- `apply_decision(unit_id)`: written with the loader's decision replay (step 5/6) so both share one SQL path,
  including the narrower-scope-wins rule and the position - 1 condition for `derived_relation`.
- `src/db/load/*`, section 11.4 checks, `src/db/queries/*`, `withReadRetry`, the ESLint import rule, the
  Dockerfile `migrate.mjs` bundle and `railway.json` pre-deploy command.
- The 7 later tables (decision 2).
