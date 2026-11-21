# Hadith corpus data-quality and full-load readiness

Audit date: 2026-07-21  
Translation/consolidation handoff updated: 2026-07-23

## Verdict

The 99,283-record unified corpus remains the correct local base, but it is **not
yet eligible for a canonical Neo4j full load**. The latest strict, fail-closed
regeneration writes 12,841 deterministic backlog rows: 12,831 translation
status/content failures, two additional translation source-identity collisions,
and eight missing Arabic source texts. All 99,283 rows still lack a
publication-ready translation review state, 99,079 lack a complete
registry-backed `chain_indx`, and the citation-bound evidence bundle contains no
claims or citations.

The larger backlog and lower chain count are intentional consequences of
stricter QA, not evidence that canonical data was replaced. Translation checks
now reject inline placeholders, copied Arabic after Unicode normalization, any
Arabic-script leakage, and output with less than 80 percent Latin letters.
Narrator identity is exact-normalization-only and atomic: one unresolved,
ambiguous, invalid, or non-positive surface empties the whole row rather than
leaving a plausible partial chain. The Imami source-work registry is now fully
resolved for this candidate, but that passing gate cannot compensate for the
text, review, chain, provenance, or evidence failures. The loader must continue
to reject the preserved legacy CSV because it predates the new identity,
provenance, and curation columns.

The archived unified Excel files are not fuller assets. Each contains 97,550
data rows and 18 columns—1,733 fewer rows and eight fewer legacy columns than
the active 99,283-row CSV. They are retained as review and recovery evidence,
not selected as production inputs.

## Canonical corpus profile

| Tradition | Records | Strict candidate `chain_indx` present |
| --- | ---: | ---: |
| Sunni | 64,356 | 192 |
| Imami | 33,225 | 8 |
| Ibadi | 1,004 | 4 |
| Zaydi | 698 | 0 |
| **Total** | **99,283** | **204** |

The candidate gate reports zero invalid chain encodings and zero unknown
narrator-ID references because it emits only positive IDs already present in the
registry. Its failure is the 99,079 rows with no complete chain. Every one of the
204 nonblank candidate chains still needs record- and narrator-level citations
before it can support a fully traceable biography.

Current source reconciliation gaps:

- The live Thaqalayn V2 manifest ranges advertise 33,191 records, but its sole
  apparent delta, `Kitab-al-Ghayba-Numani/469`, returns the API's no-hadith
  error and is absent from the public hadith sitemap. The verified ingestible
  delta against the 33,190-row local snapshot is therefore zero; the unavailable
  ID must not be synthesized. A full staged refresh attempted on 2026-07-22 UTC
  published nothing because the manifest's 659-row Kamal al-Din bulk endpoint
  returned an empty array and sampled record endpoints returned no-hadith
  errors. The complete local 659-row file was preserved for a later retry.
- Re-parsing the pinned current OpenITI Zaydi text produces 699 records, one
  more than the 698-row checked-in derivative.
- The active Ibadi and Rida counts match their current local parses (1,004 and
  35 respectively).
- All 33,190 local Thaqalayn rows now resolve by exact V2 `provider_book_id` to
  21 durable source works. The registry keeps Al-Amali (Mufid) separate from
  Al-Amali (Saduq), and Kitab al-Ghayba (Tusi) separate from Kitab al-Ghayba
  (Nu'mani). The candidate source-registry gate passes with zero unregistered
  source rows, source-name mismatches, tradition conflicts, missing source
  labels, unavailable registries, missing or unknown Imami work IDs, and
  unsupported traditions or grade traditions. Provider metadata establishes
  work identity only; it is not evidence for compiler biography, chronology, or
  publication rights.

## Sanad extraction and narrator resolution

The current 32-record, provenance-backed gold evaluation shows that
`canonical_uniform` passes its extraction gate: overall branch-count accuracy,
median branch Jaccard, and median ordered similarity are each `1.000`, with zero
errors. Each of the Sunni, Imami, Ibadi, and Zaydi subsets also records `1.000`
branch-count accuracy, mean branch Jaccard, and mean ordered similarity. This
validates the branch extraction behavior on the fixture set; it does not turn
an Arabic name surface into a cited narrator identity.

`sanad_resolution_audit.json` separately rescans the preserved canonical GZIP,
whose SHA-256 is
`f8b5cebf8a379756f1f4703b46d94c5ca1186f9853e1b0ef7a5df0c8f84cc173`.
It finds extracted chains on 84,781 of 99,283 rows, no extracted chain on
14,500, and two extraction-limit rows. Under exact normalized unique-registry
matching, only 527 extracted rows fully resolve; 84,254 contain at least one
unresolved surface. The audit attempts 437,476 surface occurrences and records
387,359 unresolved occurrences. Its seven emitted Unicode-normalization
equivalence candidates are machine-audited review leads only: they assert no
scholarly alias and cannot complete a chain. Kunya, four-character prefix, and
containment matches likewise remain non-resolving curation candidates.

That audit is a diagnostic over the preserved canonical snapshot, not the
blocked regenerated candidate. Its 527 resolvable rows therefore do not replace
the candidate manifest's authoritative release count of 204 complete chains.

## Translation completeness

The generator now recovers all 29,915 classical Sunni translations that the
published master had discarded:

- 29,888 come from `classical_canon_enhanced.csv`.
- 27 Musnad al-Shafi'i rows come from
  `classical_translations_clean.jsonl` only where immutable `pc_*` ID, canonical
  source, and exact stripped Arabic text agree.
- Conflicting failed/retranslated attempts are never selected.

After recovery, 98,430 records have nonblank English. The stricter candidate
marks 86,452 translations `complete` and records 12,831 rows with a non-complete
translation status. Including the separate source-identity and Arabic-source
checks, the deterministic backlog is:

| Issue | Records |
| --- | ---: |
| Missing English | 853 |
| Arabic-script leakage in English | 11,953 |
| Placeholder | 10 |
| Suspiciously short against a long Arabic record | 1 |
| English equals Arabic after normalization | 14 |
| One English reused across divergent records under one source identity | 2 |
| Missing Arabic source text | 8 |
| **Total backlog rows** | **12,841** |

Those 12,841 issue rows cover 12,840 unique `record_id` values because
`k6:23280` has both Arabic leakage in its English field and missing source
Arabic.

The QA order is deliberately strict. A nonblank cell is still blocked when it
contains Arabic script, has less than 80 percent Latin letters, contains an
inline `TODO` or `PLACEHOLDER`, or equals the Arabic after NFKC normalization.
The two identity-collision rows retain `translation_status=complete` but remain
separate release blockers, as do the eight rows missing source Arabic.

The 853 blanks are all in K6 sources: Muslim 354, Tirmidhi 186, Bukhari 177,
Ibn Majah 128, and Nasa'i 8. Local backups and archives contain no translations
for them. Official source recovery is preferred; any generated fallback must be
labeled with model/version and cannot be marked reviewed merely because it is
nonblank.

An additional local audit joined 19 historical OpenITI translation-backup rows
to current records by immutable identity and exact Arabic: 15 Zaydi and one
Ibadi `no_english_text` row, plus three Ibadi `same_as_arabic` rows. All 19
complete backup `text_en` values were rejected after content inspection because
they contain prompt/meta text, model self-correction or missing-input messages,
or a translation of different Arabic. No override was written. The projected
reduction from those backups is therefore zero, and those candidates do not
reduce any current blocker until clean translations are acquired and reviewed.

Translation review is also not complete: the candidate records 33,588 rows as
`source_status_unknown`, 33,190 as `source_provided`, 31,652 as
`machine_unreviewed`, and 853 with no review status because English is missing.
No row currently carries either publication-ready state (`human_verified` or
`source_verified`). A `complete` translation status therefore means only that
the translation passed the structural/content checks; it is not a scholarly or
publication approval.

Within the 31,652 `machine_unreviewed` rows, 1,733 identify
`google/gemma-4-e4b`, four identify `manual:claude-opus-4.7`, and the 29,915
classical recoveries retain an archive source but no model identity. Those
classical translations still require acquisition-log/model reconstruction or
human edition verification before the translation provenance can be called
complete.

`translation_overrides.jsonl` is the only curated override surface. Every entry
is bound to a stable `record_id` and exact Arabic SHA-256 and records translation
source and review state. A stale hash, unknown ID, duplicate override, model
refusal, copied Arabic, placeholder, or non-English output aborts regeneration.

The separate local-only candidate artifact now contains 21 distinct K6
`translation:missing` rows: one historical pilot and 20 candidates from a
two-worker bounded concurrency run. All 21 passed mechanical validation and
remain explicitly `candidate_only` / `machine_unreviewed`; the hardened run had
zero rejections, errors, invalid identities, or lost claims. These candidates
do not change the 853-row missing-translation gate. Promotion requires an
individually authored, hash-bound override after qualified human review against
an authoritative source or edition.

The separate OpenRouter rejection pilot selected 14 exact rows across Sunni,
Imami, Ibadi, and Zaydi rejection classes using `google/gemini-2.5-flash`. It
cost `$0.0701776` for 48,242 prompt and 22,282 completion tokens. Thirteen rows
passed mechanical checks and one non-text Imami separator (`* * * * *`) was
correctly rejected as copied/wrong-language output. Independent content review
classified the 13 accepted rows as eight pass, four concern, and one fail. The
failure was a 30,498-character Al-Kafi row whose apparently complete response
silently omitted one full warning passage; the model still returned `stop` and
declared no uncertainty. The 55,003-character Imami output passed structural
anchor and boundary checks but was not exhaustively reviewed. The unrestricted
full paid run was therefore blocked at that point pending long-text coverage
controls, source-row prefiltering, a larger stratified pilot, and qualified
Arabic review. See `machine_translation_candidates/OPENROUTER_PILOT_REPORT.md`.

A later hardened `r6` stress pilot used one canonical request per report with
exact ordered 500--800-character source segments, client-side segment-count and
coverage gates, and audited zero-cost rate-limit retry. Five linguistic rows
from 192 through 55,003 source characters returned complete segment ID sets;
the non-text separator was rejected before dispatch. The pilot cost
`$0.1368034` for 78,528 prompt and 45,298 completion tokens. Independent review
confirmed that the previously omitted Al-Kafi debtor/respite/divine-shade
passage was present and that an ordinary `إياكم` object pronoun remained
correctly translated as "you." It also found exact 933-character English reuse
across two distinct source segments in the 55,003-character `ʿUyun` row. The
`r7` validator now fails closed on substantial duplicate translations across
distinct source hashes and identifies those exact two segments offline.

The bounded full `r7` candidate run first processed 91 rows for `$0.0573624`
before its host process ended immediately after claiming `k6:5616`. Two Task
Scheduler launcher trials each completed `k6:3631` for `$0.0006061`; the
PowerShell wrapper then mistook the normal progress line on native stderr for a
terminating error. They ended after claiming `k6:3666` and `k6:3681`,
respectively. These attempts are quarantined because each claimed row may have
been in flight without a durable OpenRouter response ID. A fresh one-worker
`r7` run using separate native process streams and battery-safe scheduling then
started on 2026-07-22 with 12,827 selected translation rows and an `$11.80`
ceiling. It excluded
`thaqalayn:06840b21d9e61e1ab351aec4`, a confirmed Kitab al-Ghayba
Introduction/paratext, and `thaqalayn:2a1ca7a8bc366eadfcbcb80f`, the known
55,003-character report reserved for a separately journaled multi-request
translation path. It also excluded the spend-ambiguous `k6:5616`, `k6:3666`,
and `k6:3681` rather than risking unjournaled duplicate charges, plus the
already completed `k6:3631`. The reduced ceiling left room for the
known `$0.0585746` spent by prior full-run attempts under the overall `$12`
guardrail.

Semantic monitoring paused that `r7` worker cleanly after the boundary record
`k6:16257`: 1,517 durable events comprised 1,439 accepted candidates, 70
expected Arabic-leakage rejections, and eight model-uncertainty rejections, for
`$1.0546744`. Exact evidence showed two material contextual errors:
`k6:16093` reversed the observer and actor in a report about Mu'awiyah seeing
al-Sa'ib's act, and `k6:16103` read `العتق` as freed slaves instead of virgins
or young unmarried women in the Eid context. Review also identified `k6:7471`
flattening a lawful/unlawful legal contrast into "analysis or prohibition" and
`k6:12234` inventing running where the Arabic says that the speaker arrived
first or ahead. The quality pause prevented new claims without killing an
in-flight request; the worker then exited with no open claim.

The `r8` continuation hardens both the prompt and deterministic validation for
grammatical agency, contextual polysemy, legal and demographic terms, and
invented motion or speed. It also binds suffix processing to the exact unique
anchor and an ordered eligible-prefix SHA-256 that is recomputed in the paid
iterator before the first suffix row. The integrated suite passes all 150
tests. A paid four-row regression pilot over the four cases above accepted all
four for `$0.0048875`; independent Arabic-to-English review found complete
isnads and matns, the corrected meanings, and no leakage or duplication.

After that gate passed, a fresh `r8` suffix worker started on 2026-07-22 with
11,310 selected rows strictly after `k6:16257`, ordered-prefix digest
`881faecd5278f2a813448e7bab30b22c457caf4ef85cf461be01a9b1f0a6e33d`, the
same two source-quality exclusions, and a `$10.65` run ceiling. The run is now
deliberately quality-paused after 4,142 durable events and `$3.5027292`: 3,564
accepted `machine_unreviewed` candidates, 560 expected Arabic-leakage
rejections, and 18 model-uncertainty rejections. The checkpoint has zero active
claims and records `openrouter_terminal_error` quality-pause evidence. The
Windows task `IslamicAppsOpenRouterV8Suffix` is Ready with exit code 2, and the
recurring quality monitor has been deleted.

The pause followed two confirmed fidelity defects. `k6:17921` rendered passive
`لا نورث ما تركنا صدقة` as active “We do not inherit,” reversing the doctrinal
relation. `k6:18013` rendered contextual `أفضل شىء؟` (“Did anything remain?”)
as “The best thing.” Prompt and validator regressions are required before any
resumption. All output remains `candidate_only` / `machine_unreviewed`; it is
excluded from canonical rows, overrides, and the consolidation graph bundle.

The pilot also exposed source-quality blockers that translation cannot repair:
three translation-backlog rows contain no Arabic-script source at all (blank,
`s`, and `* * * * *`), one Ibadi source is explicitly abbreviated, one Zaydi
source ends mid-clause at `ولم`, and the two giant Imami rows carry implausible
`attributed_to=Prophet Muhammad (qudsi)` metadata. These require source
reclassification or correction before scale-up.

Ten source-level resolutions are recorded separately in
`curation_dispositions.jsonl`. They include seven corrected official references,
one split row that must be merged/tombstoned, one source-introduction row that
must be reclassified outside `Hadith`, and one Muwatta translation recovery that
is pending reuse rights. A disposition documents the path to resolution; it does
not satisfy the Arabic or translation gate and contains no protected translation
body.

## Citation-bound graph evidence

`evidence_curation.json` remains intentionally empty: it contains zero
citations, biographical assertions, source-author assertions, historical-event
assertions, and epoch assertions. Its manifest remains
`ready_for_graph_publication: false` with status
`awaiting_cited_claim_curation`. The candidate derives the same five zero actual
counts from the bundle and fails each corresponding required-coverage check,
plus `not_ready_for_graph_publication`. The zero uncited and unreviewed counts
are vacuous because there are no claims to review.

This gate is fail-closed: the schema and manifest are valid, but a valid empty
bundle is not evidence. Historical seed nodes, registry metadata, and a flipped
manifest boolean cannot substitute for citation-bound, independently reviewed
claims.

## Railway production graph state

The read-only audit of Railway project `hadith-ontology` found 99,283 `Hadith`
and 99,283 `Chain` nodes, matching the active local record count. Every hadith
has exactly one chain and there are no orphan chain nodes. However, only 62,041
chains contain at least one resolved narrator; 37,242 are empty. The graph has
159,550 `Chain` to `Narrator` inclusions and 80,240 narrator-to-narrator links.

Production is a legacy load, not the new publication artifact:

- all 99,283 hadiths lack `record_id`, `source_record_id`, provenance, and the
  translation-status/source/review fields;
- 68,515 hadiths have nonblank English, so production predates recovery of the
  classical translations present in the local candidate;
- all 32 source nodes have a name and tradition, but none has an author/compiler,
  author birth/death date, or provenance locator;
- all 24,326 narrator identities exist, but no narrator has a canonical Hijri
  birth year or a nonblank publication biography/citation; 3,951 have a Hijri
  death value and only 21 have the manually curated phase-0 summary fields;
- there are no `HistoricalEvent`, `Epoch`, or citation nodes; and
- 352,315 of 399,064 assessment nodes (88.28%) are explicit
  `no_extant_evaluation` placeholders. Substantive assessments exist for 29,915
  Sunni records and 16,834 Imami assessment instances, but none for the Ibadi or
  Zaydi schemes.

All 26 constraints and 66 indexes were online, and the audit found no duplicate
legacy hadith IDs, duplicate narrator `scholar_indx` values, chain orphans, query
errors, OOMs, or fatal database log entries. This confirms structural
consistency while exposing the identity, provenance, translation, biography,
and historical-citation gaps.

The database currently sleeps and wakes normally under Railway's service
policy. Each observed startup also warns that forwarded headers are accepted
from any proxy and any hostname; configure Neo4j `allow_proxies` and
`allow_hosts` before treating the endpoint as publicly hardened.

Cost policy: keep Serverless/App Sleep enabled and perform all curation, tests,
and import rehearsal locally. At the audited 2.206 GB average memory profile,
continuous awake compute models at roughly $22/month before plan credits,
whereas a 10% awake share models near $2.46 including current volume usage.
These are resource estimates, not total invoices: the selected Railway plan's
base subscription still applies (Hobby's published $5 base includes up to $5
of resource usage).
Routine tests now require a dedicated `NEO4J_TEST_URI` and explicit opt-in so
they cannot wake or mutate Railway production. See
`.omc/research/railway-cost-guardrails-2026-07-20.md` for assumptions and
owner-controlled alert/hard-limit recommendations.

## Narrator biography readiness

`datasets/narrator-data/all_rawis.csv` has 24,326 unique narrator identities but
is an identity/relationship lexicon, not a complete biographical corpus. It has
no narrative biography, Arabic/English name pair, tabaqah, geographic region,
or record-level citation fields.

| Assertion | Substantive rows | Coverage |
| --- | ---: | ---: |
| Birth year (Hijri) | 386 | 1.59% |
| Death year (Hijri, positive) | 3,830 | 15.74% |
| Both Hijri endpoints | 374 | 1.54% |
| Neither Hijri endpoint | 20,484 | 84.21% |
| Birth place | 7,364 | 30.27% |
| Death place | 2,675 | 11.00% |

Thirty-eight of the 374 complete Hijri pairs place death before birth. Several
Gregorian values are truncated ranges, and high-fill fields such as
`death_reason=Natural` appear defaulted rather than source-supported. The only
real local biography seed covers 21 narrators and names general reference works
but lacks edition/volume/page citations.

A publication-grade model must store competing assertions rather than collapse
them into one date. Each biographical claim needs narrator ID, claim type/value
or date range, calendar, uncertainty, source work/author, edition, volume/page
or stable URL, quoted-location hash, retrieval date, and review status.

## Historical context and epochs

The existing seed contains 54 events and 32 locations. Only 15 events are
categorized as political, 14 as military, and 17 as scholarly; almost every
entry is a point year. There is no epoch/dynasty dataset or general epoch
overview, and no event has a record-level citation, edition, page, URL,
confidence, or provenance field.

This seed therefore cannot meet the requirement to show every relevant
political event during a narrator's lifetime. It is an unverified starter
catalog. The seeder now derives deterministic IDs, and narrator-lifetime queries
use canonical Hijri bounds plus interval overlap without interpreting two
unknown bounds as “all events.” The seeder also fails before writes because two
events reference `Egypt` while the location catalog contains only Cairo/Fustat;
that mapping must be sourced rather than guessed. Existing Railway random-ID
history nodes would require a one-time reconciliation, although production
currently has none.

The target historical layer needs:

- cited events with start/end ranges, place, category, scope, and competing
  date/source assertions;
- cited epochs/dynasties with start/end ranges and general overviews;
- explicit collection-formalization milestones through the core hadith
  collections;
- a relevance rule that distinguishes “occurred during lifetime” from “directly
  affected this narrator”; and
- uncertainty-safe behavior when one or both life endpoints are unknown.

## Full-load contract

The production artifact is `all_hadiths_unified.csv.gz`, never Excel. A load is
allowed only when `curation_manifest.json` reports `ready_for_full_load: true`,
its count matches the streamed input, all stable record IDs are unique, every
Arabic/English/grade/source-work gate passes, and every row has resolved
`chain_indx`. The current candidate has 99,079 rows without chain IDs, zero
invalid chain encodings, and zero unknown ID references because only
registry-backed IDs are emitted. The whole-sanad requirement therefore remains
a separate release blocker even after the 12,841 deterministic backlog rows are
cleared. On a successful publication, the
generator records the logical CSV SHA-256 plus the physical CSV/GZIP hashes and
sizes under `published_dataset`; the loader recomputes the logical input hash and
requires an exact match. The current blocked manifest intentionally has no
`published_dataset` entry, so the loader rejects it.

The latest default Thaqalayn regeneration, not `--no-shia`, is blocked with
candidate content SHA-256
`256c8cfbca12937ca1414926c007c6f63098af6f80629ca25ae4187ee8e6550c`.
Because no valid ready publication manifest existed, the active and candidate
manifest paths contain the same non-ready bootstrap payload; their file SHA-256
is `224c1d1e054bccb1b6669d2c92c8abf0ae8d214d76e34d5ac84469e437a72d2b`.
Neither manifest has a `published_dataset` binding. Fail-closed regeneration
left all six canonical data artifacts unchanged:

| Canonical artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `all_hadiths_unified.csv` | 172,159,256 | `a21d97da2724a69736478b0ce8759507ef05206aecb73c52ba9005d051a8eb22` |
| `all_hadiths_unified.csv.gz` | 32,043,881 | `f8b5cebf8a379756f1f4703b46d94c5ca1186f9853e1b0ef7a5df0c8f84cc173` |
| `all_hadiths_clean.csv` | 60,160,130 | `6659e319d61a2c82657da28233cd8454aa05d8ecefdf38d1ea065b0b819f076b` |
| `all_hadiths_clean.csv.gz` | 13,593,654 | `5d0919b3525cead792158af8e8b28d908364e269c528a23e67f853ac9bc1dfef` |
| `all_hadiths_shia.csv` | 91,022,501 | `92fb8695b2e586c0a86dc03a83c9a9c9e86cc7b9d2962b2b4ffbd47e50bc096e` |
| `all_hadiths_shia.csv.gz` | 17,910,992 | `066c7089a9b6fd3524b4a16849896b112899f4cbc692b7699689e596bbed24c3` |

For a clean local database, the fastest final path is an offline
`neo4j-admin database import full` with a dry run, explicit off-heap budget,
measured maximum UTF-8 field/read buffer, strict malformed-row handling, and
post-import schema creation. The online TypeScript path remains useful for
bounded development loads. Its production full-regeneration mode is now
clean-target/blue-green only: it streams CSV/GZIP/JSONL, preflights the entire
corpus before mutation, and refuses a non-empty application graph. DatasetVersion
staging is audit metadata, not transaction isolation; an incomplete target is
discarded rather than promoted or repaired in place.

## Machine-readable evidence

- `curation_candidate_manifest.json`: latest failed-candidate input/content
  hashes, schema, counts, and gate evidence.
- `curation_manifest.json`: last valid published binding, or a nonready
  bootstrap manifest when no valid publication exists yet.
- `curation_backlog.csv`: one deterministic row per current publication blocker.
- `sanad_resolution_audit.json` and `narrator_alias_candidates.json`: bounded
  exact-resolution diagnostics over the preserved canonical GZIP.
- `.omc/research/uniform-isnad/algo-evaluation.md`: current provenance-backed
  extraction evaluation over the 32-record gold fixture.
- `evidence_curation.json` and `evidence_curation_manifest.json`: current empty,
  non-ready citation-bound graph-evidence bundle and its derived counts.
- `AGENTS.md`: canonical identity, translation, provenance, and load rules.
- `datasets/sources/*.md`: upstream source, license, scope, and citation registry.
