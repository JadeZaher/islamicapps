# pg_export — bundle to Postgres projection

`export_postgres.py` turns a **validated** Neo4j-format bundle (`neo4j_export/`) into one COPY-ready CSV per launch
pipeline table (`canonical/`) and a candidate stream (`candidates/`), each with a hash-bound manifest. Design:
`docs/architecture/data-architecture.md` §4.4, §6.2. Loader: `src/db/load/`.

```
npx tsx src/db/load/dump-catalog.ts <dir>/catalog.json
python datasets/hadith-data/pg_export/export_postgres.py --bundle <bundle> \
  --input datasets/hadith-data/development/incomplete-curation/all_hadiths_unified.incomplete.csv.gz \
  --rawis datasets/narrator-data/all_rawis.csv --legacy-master datasets/hadith-data/all_hadiths_unified.csv.gz \
  --catalog <dir>/catalog.json --output <new dir> [--reconciled datasets/hadith-data/reconciled]
  [--correspondence datasets/hadith-data/diagnostics/report-correspondence/output]
python -I datasets/hadith-data/pg_export/test_export_postgres.py
python -I datasets/hadith-data/pg_export/test_transliteration.py      # transliteration and mention spans
python -I datasets/hadith-data/pg_export/test_identity_rules.py       # provider English, Imam kunyas, the tier
python -I datasets/hadith-data/pg_export/test_chain_chronology.py     # chronology rule, seams, who is withheld
python -I datasets/hadith-data/pg_export/test_chain_builder.py        # chain builder on real works and the re-checks' cases
python -I datasets/hadith-data/pg_export/check_projection.py <dir>    # before any load: the file-level chain invariants (~10 s)
```

Since projection `2026.11.21.6` the catalog must come from a database migrated to `0013`
(`npx tsx src/db/load/dump-catalog.ts <out.json> --database production --confirm-production`; read-only).

## Refusals

No `import_ready: true`; validation report and manifest naming different bundles; any bundle file whose bytes or
SHA-256 differ from its manifest; a recomputed `content_sha256` that differs; a unified CSV or rawi file whose hash
differs from the bundle's inputs; a CSV header that is not exactly the live catalog's loadable columns; any hadith
whose `text_ar` does not hash to its `arabic_sha256`; an unknown tradition, narration level, translation review state
or `grade_value`; non-contiguous mention positions.

## Rules

- **Determinism.** Rows sorted by primary key, LF, UTF-8, no timestamps, `QUOTE_NOTNULL` (every non-null cell is
  quoted, so no value can be read as COPY's `\.` end marker). NULL is an unquoted empty cell; blank text is NULL.
  The manifest binds the resolver (`regen_unified_csvs.py`), `classify_attribution.py` and this script by SHA-256,
  because a change to any of them changes the output.
- **Arabic is never trimmed or rewritten.** `text_ar_normalized` and `name_ar_normalized` use
  `classify_attribution._norm` (search only).
- **Narrator names.** `io.ts` reads `name_english`/`name_arabic` columns that `all_rawis.csv` does not have, so the
  design's "port io.ts" would leave both null. `name_ar` is the resolver's `_extract_arabic_name_raw`; `name_en` is the
  text before the first parenthesised Arabic block. A string split, not an identity claim.
- **Chains** (projection `2026.11.21.2`). The bundle's text extraction, then the reconciled sidecars
  (`reconciled/README.md`), each file hash-checked against its build manifest and each row bound to the hadith's
  exact Arabic (a mismatch refuses): `no_chain_in_source` with `suppress_extracted_chain` drops every chain of that
  report (Shafi'i, Nahj al-Balagha); `pure_canon_chain` replaces the chains extracted from matn-only `text_ar` with
  the canonical extraction of the source's own `chain` field (`extraction_method = source_chain_field`, same
  `chain:`/`mention:` id scheme, empty branches dropped before numbering).
- **Identity candidates** (`chain_mention_candidates`; owner decisions 2026-11-21, `src/db/AGENTS.md` §Identity
  candidates). Per mention, every candidate is emitted with its basis; none is preferred:
  - Sunni reports only: `resolve_narrator` tier 0 -> `name_exact`, tiers 1-2 -> `name_spelling_fold`; otherwise
    `kunya_only_candidate` -> `name_kunya_only`. Imami, Ibadi and Zaydi reports get no name candidate.
  - K6 source index (`reconciled/k6_source_index.jsonl.gz`), only where the sidecar's `text_branches` equal the
    extracted branches exactly: at every `aligned_positions` entry (the positions the Arabic corroborates), basis
    `source_index_confirmed_by_text` when the report's basis is `source_index_corroborated_by_text`, else
    `source_index`; `detail` is the agreement class. A tahwil branch inherits the source id of a corroborated twin
    whose opening surfaces are identical up to that position (`:shared_trunk`); convergences are not inherited
    (`align_source_index`).
  - Placeholder rows are never a target (a source-index claim on one is dropped and counted); the only placeholder
    target is a kunya-only row through `name_kunya_only`.
- **`chain_mentions.narrator_id`** (the machine-reviewed identity; never called verified) is set only for an uncontested
  `source_index_confirmed_by_text` candidate (`verified_narrator`): `resolution = source_index`, `resolution_basis =
  source_index`, confidence 1.0. A `name_kunya_only` candidate never contests it (owner, 2026-11-21). Every
  other mention is `unresolved`. The bundle's `RESOLVES_TO` and the legacy master's `chain_indx` are no longer read
  for identity: the first is an older name match (and touched non-Sunni rows), the second differs from the K6
  source's own index on 16,156 of 34,324 comparable rows.
- **Manifest.** `inputs.reconciled_sidecars` binds the three sidecar files; `counts.identity_candidates` gives
  candidates per tradition and basis, mentions by agreement, verified links, confirmed-but-contested mentions and
  dropped claims; `counts.k6_sidecar_built_with_current_resolver` is false once `regen_unified_csvs.py` changes
  (rebuild the sidecar when the change affects resolution).
- **Matn** (projection `2026.11.21.3`). `matn_ar` is stored only when `diagnostics/report-correspondence/matn_isolation.py`
  (imported, not copied: `MatnIsolator` with no sidecars) accepts the column as the report's own matn: its Arabic
  letters occur inside the report's own text and it does not start where the text starts with three or more
  transmission links. Otherwise no matn is stored and `counts.matn_ar` records why and by work (1,597
  `matn_column_not_in_text`, 12,617 `matn_column_includes_chain`, all K6). Real-row test: Tirmidhi `k6:23658`.
- **Assessments.** Non-rulings in `gradings_full` (`لم يخرجه` 1,736, `سكت عنه` 46, back-references 24, 7 others) are
  excluded and counted (`gradings_full:non_ruling_excluded:<reason>`), using `NON_RULING_CLASSES` and `fold` imported
  from `diagnostics/grading-recovery/build_hadith_assessment_rows.py`. Pure Canon `grade_value = ثابت` is
  `collection_label` (never a grade). `gradings_full` segments
  are `cited_ruling` rows; `grade_canonical` and `grade_detail` port `grade-taxonomy.ts`; the parenthesised citation
  is split into work, volume and page.
- **Translations.** Bundle `review_state` `source_provided` and `source_status_unknown` both map to `state =
  source_provided`; the raw value stays in `review_state_raw`. Leading whitespace is trimmed from English only.
  `english_quality`: the bundle's `arabic_leakage` becomes `complete` when the only Arabic-script characters are the
  honorific symbols ﷺ ﷻ ﷽ and ؐ-ؓ (10,650 Sunni, 9 Imami in `2026.11.21.4`); real Arabic stays held. The rule belongs
  in `regen_unified_csvs.translation_issue` too (not changed here: the resolver's hash binds the K6 sidecar).
- **Candidates.** `machine_unreviewed` English from the master still goes to `candidates/translation_candidates.csv`
  (`machine_unreviewed` when a model is named, else `unknown_provenance`); the loader does not read it.
- **Machine English overlay** (projection `2026.11.22.11`; `machine_english.py`, `test_machine_english.py`). `--machine-english` (default
  `machine_translation_candidates/machine_english_overlay.jsonl.gz`; no file means none, recorded as `inputs.machine_english: null`) is bound
  in the manifest by SHA-256 with the pinned model. Per report: complete `human_verified`/`source_verified`/`source_provided` English is kept
  (source first); otherwise the draft is gated (`machine_english.gate`: hash, screen status, pinned model, finish reason, Arabic script,
  Latin share, length ratio 1.0 to 3.2, refusal or meta text) and becomes the report's one English row (`state` and `review_state_raw`
  `machine_unreviewed`, `quality_status` complete, `source` `hy-mt2-openrouter-v1`, `model` as the API returned it, `provenance_source`
  `machine_translation_candidates/<journal>|prompt=<version>|prompt_sha256=<12>|provider=<p>|at=<time>`). A failing existing row keeps its id
  and is replaced in place. A draft that fails is counted in `counts.machine_english.held_out_by_reason` and never shown.
- **Review units** are SHA-256 over `\x1f`-joined parts, NULL context as `''`: coarse (surface, teacher, work), fine
  (surface, teacher, student, work).
- **Report correspondences** (`--correspondence`, default `diagnostics/report-correspondence/output`). Refused when
  the output is missing or its `summary.json` names another unified CSV than `--input`; every pair's id, order, method,
  class, scope and basis is checked. A pair whose report is not loaded or whose Arabic hash differs from the loaded
  text is dropped and counted (`counts.report_correspondences`; 0 on 2026-11-21). The manifest binds the pair, member
  and summary files, `matn_isolation.py`, the extractor and the non-ruling rule by SHA-256.
- `slice_correspondence_fixture.py` cuts the report-family flow-test fixture (real rows, typed from the catalog).
- `slice_projection.py` cuts a referentially closed slice of real rows for the loader flow test, choosing reports
  with a verified link, a disagreement and a kunya-only candidate, and closing narrators over the candidates.
- **Tests.** `test_export_postgres.py` covers the pure rules, the sidecar rules on real sidecar rows, and real
  mentions read back from the projection under `development/pg-load-2026-11-21/projection-candidates` (`PG_PROJECTION`
  overrides; skipped when absent).

## External identity (projection `2026.11.21.4`; `src/db/AGENTS.md` §External identity)

`external_identity.py` reads the reconciled sidecars (`reconciled/README.md` §External sources), each file checked against
its build manifest, and refuses a claim whose mention, surface or report Arabic differs from the projection's. Rows:

- **narrators**: every hadith-kg or Riwayat record a claim or link names (`narrator:hadith-kg:<id>`,
  `narrator:riwayat:<N id>`), name as the dataset writes it, its transliteration (`name_latin`), placeholder reason
  (stubs: `hadith_kg_stub_narrator`); the twelve Imams from `imam_kunya_conventions.json` (`narrator:imam:<n>`).
- **narrator_source_profiles** (`dataset_assertions` verbatim; `label_reason` from `riwayat_label_reason`: placeholder,
  a name held by two or more ids each with at least 3 mentions and a tenth of the name's total, Riwayat's merge or junk
  flag, a bare `ابن X`), **narrator_external_ids** (Riwayat's crosswalk), **narrator_link_candidates** (the sidecar's lexicon
  links whose lexicon row is loaded and not a placeholder; one link per external record or the build refuses).
- **chain_mention_candidates**: one per claim (`candidate_id`), `source_position` the external list index, `source_ref`
  `hadith-kg:hadith:<id>` / `riwayat:<H id>`, `source_assertion_origin` `dataset_index` or Riwayat's origin.

**The tier** (`standing_identity`, table-tested in `test_identity_rules.py`). Evidence, strongest first: K6
`source_index_confirmed_by_text`; `two_sources_agree` (a K6 claim and a hadith-kg claim whose person keys meet: K6 and
hadith-kg are independent compilations; Riwayat's Sunni ids are hadith-kg's own and never a second source);
`source_hadith_kg_confirmed_by_text`; `source_riwayat_confirmed_by_text` when its origin is an annotation (never
`riwayat_automatic_linking`) and the record is not label-like; `imam_kunya_convention`. The mention must be uncontested
(`contests`): no two contesting candidates name different person keys within one registry. Person keys
(`PersonKeys.key`): a record's lexicon link, else a Riwayat record's single hadith-kg crosswalk id (and that record's
link), else itself. The same rule is the load invariant and the chain read (`PERSON_KEY_SQL`).

**Imam kunyas** (`imam_kunya.py`, data `imam_kunya_conventions.json`, owner-reviewable). Imami reports only; the surface
is exactly a listed kunya, optionally followed by one listed qualifier, with the honorific marker at the end of the
surface or right after the name in the report text (`mention_text.PlainText.honorific_after`). Unshared kunya or a
qualifier naming one Imam: `imam_kunya_convention`; a shared kunya with no qualifier: `imam_kunya_candidate` for each Imam
who shares it (a label, never a contest); other words after the kunya: nothing.

## Latin names (`transliteration.py`, `mention_text.py`, `provider_english.py`)

Per mention, first that applies: (a) `provider_english`, Imami Thaqalayn reports only: the dominant English form of the
name's folded key in `diagnostics/chain-reconciliation/output/imami_surface_lexicon.jsonl.gz` (hash-bound), spelling
variants pooled, at least half the pairings, a name and not a clause, and it must render the Arabic (first consonant, and
the last Arabic word heard after the first English word): this refuses alignments shifted by one name (بكر بن عبد الله بن
حبيب paired with "Tamim ibn Buhlool"); (b) `identity_name`: the English of the standing identity, or of the one person every
contesting candidate names (the lexicon's Latin run, as the page shows it, or the Imam register's name); (c) a
transliteration of the name as written in the glossary's scheme (`TRANSLITERATION_NOTE`): from the vowel marks of the
mention's own span in the report text (`locate_mentions`; the stored surface has no marks), a word without full marks
read from the curated table; or (d) the table alone when every word is in it. Otherwise none: Arabic alone. The table
leaves out spellings with two customary readings (معمر, عبيدة, حصين, حجر, حبان, سلام, عقيل) and non-name words.
`counts.latin_names` gives coverage by tradition and basis.

## OpenITI report structure (projection `2026.11.21.5`; `src/db/AGENTS.md` §OpenITI extraction fields)

`reconciled/openiti_extraction.jsonl.gz` (`build_openiti_extraction_sidecar.py`, run after `regen_unified_csvs.py`) carries
`sanad_ar`, `sanad_inherits_from_record_id`, `split_confidence`, `split_kind` and `source_notes` per OpenITI report, bound to the
SHA-256 of the unified `text_ar`. The exporter checks the file against its build manifest and refuses an OpenITI report with no
row, a row bound to other Arabic, an unused row and an inheritance that names a report not in the projection. It writes
`hadiths.sanad_ar`, `sanad_inherits_from` (`hadith:` + record id), `split_confidence` and `source_notes` (compact JSON);
`counts.openiti_extraction` gives the split confidence, inheritances and notes. `matn_ar` is unchanged: it still passes `accepted_matn`.

A corpus change that alters an OpenITI report's Arabic invalidates the external identity claims on its mentions, and those
are built from a projection's `chain_mentions.csv`. Break the cycle with an interim projection: export once with a copy of
`reconciled/` whose `external_mention_claims.jsonl.gz` has no `openiti:` rows (manifest hash updated in the copy), point
`EXTERNAL_SIDECAR_PROJECTION` at its `canonical/`, rebuild `build_external_report_crosswalk.py` and
`build_external_identity_sidecars.py`, then export for real. `slice_openiti_extraction_fixture.py` cuts the flow-test fixture.

## Chain chronology (projection `2026.11.21.6`; `src/db/AGENTS.md` §Chain chronology guard)

`chain_chronology.py` (table-tested in `test_chain_chronology.py`) runs per branch after the standing identities are known
and before the Latin names. Years are the lexicon's (`narrator_lexicon_profiles` birth and death, 0 dropped); the lexicon's
own teacher lists (`student_of`) are the attested pairs.

- **Rule** (`transmission_chronology`, the same CASE as `narrator_transmissions`): student born after teacher died; teacher
  born after student died; teacher died more than `DEATH_GAP_YEARS` (60) after the student. Attested pairs are exempt.
  Between non-adjacent members only the last two apply (intermediaries make a later birth possible).
- **Threshold.** Measured on projection `2026.11.21.5`: teacher death minus student death over the 52,175 adjacent standing
  pairs with both deaths has median -42, 99th percentile 36; on the 26,530 lexicon-attested pairs, the share above 20/40/60/100
  years is 1.88/0.87/0.35/0.11%. Above 40 the unattested chain pairs sampled were all misreadings (Abu Dawud al-Sijistani for
  al-Tayalisi, Muhammad b. Yahya b. Hibban for al-Dhuhli); 60 keeps a margin for the lexicon's own date slips. Withheld
  mentions at 40/50/60/80/100: 627/591/521/466/387.
- **Decision** (`contest_chain`), per impossible adjacent pair outside a seam window: (1) the name in conflict with at least two
  dated members of its route while its partner conflicts only with it; (2) else the name whose other neighbour the lexicon's
  teacher lists do not tie to it, when the partner's are; (3) else both, the reason saying the chain cannot tell which. A
  student born at most `IRSAL_YEARS` (20) after the teacher died stands (irsal); a narrator repeated in the chain is never
  withheld (the seam the view computes must not move). Routes are the segments between seam windows.
- **Output.** `chain_mentions.identity_withheld_reason` (reader-facing, "chronology: the person named here died in 23 AH,
  before the next transmitter was born (88 AH)"); candidates unchanged; a withheld identity never gives the Latin name
  (`identity_name`), so the name falls back to its transliteration. `counts.chain_chronology` records pairs decided,
  undecided, left as irsal, left to the view (repeated narrator), seam pairs and seam chains, and mentions withheld by
  tradition; `counts.identity_candidates.standing_withheld_by_chronology` by method.
- **Lexicon fields.** `narrator_lexicon_profiles.tabaqah_raw` is the lexicon's `grade` column (its generation class);
  `source_fields` is `lexicon_source_fields` (places of stay, family, tags, interests; tags and interests without brackets).
- `slice_chronology_fixture.py` cuts the flow-test fixture (k6:28147, k6:28195 and the first report with an irsal pair).

## Chain builder (projection `2026.11.22.1`; `src/db/AGENTS.md` §Chain builder)

`chain_builder.py` (table-tested in `test_chain_builder.py` on the real parsed works and the audit's cases,
`chain-audit/ibadi-zaydi/`) replaces the bundle's chains of al-Rabi, Musnad Zayd and Sahifat al-Rida. The canonical
extractor is reused unchanged, so no Sunni or Thaqalayn chain can move (measured: 0 rows differ outside OpenITI).

- **One span.** A report's own chain is cut from the parser's `sanad_ar`, never from `text_ar`. A low-confidence split
  (`split_confidence = low`) has no own chain: 307 reports lose a chain the old whole-text guess gave them (the audit found
  41 of 54 sampled such chains wrong).
- **Fixed-shape opening (round 3).** Low confidence about where the matn starts is not low confidence about the opening: when
  the text opens with the work's fixed isnad (`fixed_shape_span`, after the compiler is stripped) the chain is read from that
  span and stops at the first word the shape cannot explain. al-Rabi: «أبو عبيدة [عن | قال: قال] جابر بن زيد [عن | قال: قال |
  قال: سمعت] <Companion>», Abu ʿUbayda directly from a Companion, and «بلغني/بلغنا عن X» (X may be the Prophet: the balagh
  gap ends the chain); the Companion slot refuses verbs and collectives («جاء», «بلغني», «جملة», «أناسا»). Musnad Zayd: «[حدثني]
  زيد بن علي [عن أبيه [عن جده [عن علي]] | عن آبائه عن علي]», a slip («زيد بن علي بن ابيه») stops at Zayd. Any other opening stores
  no chain. 148 of the re-check's 190 reports get a chain back (al-Rabi 114, Zayd 34); the page still shows the text whole.
- **Continuations name their speaker (round 3).** The head of a low-confidence continuation, or the matn's first words when the
  span is only «وباسناده قال:», is read past «قال/قالت/سئل/حدثني» up to the speaker's blessing; a name that matches a link of the
  route shortens it there (`continuation_names_match`: the written form counts, «أبي جعفر» = «أبي جعفر بن محمد», and a bare
  «أبي» never stands for a longer name). Words that name no link («رسول اله», «رأيت النبي») are ignored: round 2 dropped the
  whole chain for them. «ومن طريق X» after a route ending at al-Rabi's own transmitter (Abu ʿUbayda, Jabir: no Companion
  written) adds X after him instead of replacing him.
- **Continuations.** A report the parser marks as continuing («وبهذا السند», «وباسناده», «ومن طريقه», and since round 2
  «ومن طريق X»: `parse_openiti.py` `RE_CONTINUATION_CHAIN`, 22 al-Rabi reports) carries its parent's mentions, each naming
  the written mention it repeats (`chain_mentions.inherited_from_mention_id`) and copying that mention's candidates. The
  opener is never a mention. A named link after the opener that is in the parent's chain shortens it there («وباسناده قال:
  حدثني علي بن الحسين»); for a low-confidence split only the head up to the first colon is read, and only to shorten.
  «ومن طريق X» replaces the parent's last link with X and becomes the route its own continuations repeat; «وباسناده» always
  repeats the work's route (a report that shortens it does not shorten the next one).
- **Compiler.** al-Rabi and Abu Khalid al-Wasiti (and the book transmitters written before them) are the work's
  attribution, never a mention. Sahifat al-Rida's chain is the Imam chain written in `rida_0001` from «علي بن موسى الرضا» to
  «علي بن أبي طالب»; the 16 editorial transmitters before it are not mentions. The «أبي» before «عن علي بن أبي طالب» is kept
  as written (the al-Tabarsi edition reads «حدثني أبي علي بن أبي طالب»; owner to decide).
- **Not names.** Honorifics and blessings (including «كرم الله وجهه», «(ع م)») are removed before the waw split; year
  phrases, «صاحب رسول الله», a leading «وعن / وكان / أن / حدثني», a trailing «أنه / أنها / قال / يقول / عنه ...» and the
  title «أمير المؤمنين» are not part of a name; a clause with a matn verb and no nasab is dropped. «قال: قال X:» at the head
  of an al-Rabi matn and «عن علي ...» at the head of a Musnad Zayd matn (the parser's span stops at «جده (ع م)») are links.
- **Balagh** («بلغني عن X») stays a balagh: an `anonymous` mention «بلغني» between the narrator and X, never repaired.
- **Musnad Zayd relations** (`opening_isnad_rules.json`, owner-reviewable): a chain of exactly «زيد بن علي، أبيه[، جده[،
  علي]]» gets candidates with basis `named_in_opening_isnad` and the detail citing `zayd_0001`: Zayd b. ʿAli
  (`narrator:imam:zayd`, a register row added and credited to the work), `narrator:imam:4`, `:3`, `:1`. The surfaces stay as
  written; «أبيه» and «جده» are `derived_relation`. Standing tier method `named_in_opening_isnad`.
- **Kunya alone** (`external_identity.demote_kunya_only`, the three works only): a surface that is a kunya alone can never be
  confirmed by text, so an external `*_confirmed_by_text` claim on it becomes the plain basis with the reason in `detail`
  (Abu ʿUbayda / Riwayat N0013779: 272; Abu Hurayra / N0000518: 60; 3 others). Applied to Sunni and Imami chains it would
  change many more; that is the owner's call.
- **External claims** are not aligned onto inherited mentions (`build_external_identity_sidecars.py`), which copy their
  written mention's candidates instead.

### Imami chains (projection `2026.11.22.2`; audit `chain-audit/imami/`)

`build_imami_chains` re-cuts every Thaqalayn report from the bundle's branches and the report text (the shared extractor is
still unchanged; Sunni and OpenITI rows: 0 differ apart from two Sunni mentions whose Riwayat record changed label status,
because label status counts claims across the corpus).

- **«جميعا» groups** (`jamian_groups`): «A عن B و C عن D جميعا عن E» is split at each waw with a link on both sides; each
  group is its own route meeting at E. A group that opens with one of al-Kulayni's shaykhs (the audit's list) is a route of
  its own; another hangs from the first group's opening name («علي بن إبراهيم عن أبيه و محمد بن عيسى عن يونس»). «A عن B و C
  جميعا» with no inner link is a plain co-transmitter level; a last group that ends in a co-transmitter level («عن صفوان و
  ابن أبي عمير جميعا») is ambiguous and left as read (counted).
- **Not narrators** (`clean_imami_mention`): a report verb («و روى», «قال», «سئل», «في رواية») is cut and the chain starts at
  the name; the Mujam's «3/45 الكافي» citation, footnote digits, a trailing «أو / مثله / في قوله / أنه / في الرجل ...», year and
  number words, a clause, the Saduq compiler opener («... بن بابويه»), and matn after an Imam are not names.
- **Suspended** (`chains.suspension`): `back_reference` (the opening is a pronoun or formula: «عنه», «وبهذا الإسناد»; kept as a
  `not_a_narrator` label with no identity), `route_given_elsewhere` (Man la Yahduruhu: «و روى X», the route is in the
  Mashyakha), `mid_chain_start` (al-Kafi: the opening name is not a shaykh of the compiler, stands first in under a fifth of
  its 20 or more appearances, and the text starts with it; the audit's rule with its text test corrected). Only «وبهذا
  الإسناد» right after a report of the same chapter (provider order) is filled in, and only when the link it then names is
  in that report's chain (`resolve_same_isnad`); the rest stay marked.
- **Anonymous gaps**: «X رفعه», «X عمن ذكره», «X عن رجل» become X and an `anonymous` mention; a standalone «رجل», «بعض أصحابه»
  is `anonymous`. A label position never carries an identity (its candidates stay), and `narrator_transmissions` excludes it.
- **Fused co-transmitters** «أبي و محمد بن الحسن» become one level of two branches; in al-Kafi a fused name whose second half
  is a shaykh of the compiler starts a second isnad instead, and (round 3) the first isnad takes the name both reach: the second
  isnad is the shaykh and his teacher, so the shared name is its third («… عن محمد بن إسماعيل و علي بن إبراهيم عن أبيه عن حنان
  بن سدير»). Concatenated isnads (D07) are not split (deferred: telling where a second isnad starts needs the compiler's route
  list; a count rule would cut true long chains).
- **Round 3 (re-check patterns 6-8).**
  - *Persian letters* (Thawab al-Aʿmal writes «حَدَّثَنِی»): the extractor's verbs miss them, so names after them were lost. The
    text is re-read on a copy with ی/ک folded to ي/ك (one letter for one, so offsets agree) and every surface is cut back out of
    the original (`persian_safe_branches`); the stored letters stay the source's. If one surface cannot be located, the bundle's
    branches stay.
  - *Not names*: a lone «و» left by «وَ حَدَّثَنِي»; «و قد روى X» and a leading «حدثني/حدثنا» (the verb goes, X stays); «ره»
    (رحمه الله) after a name; an Imam's name followed by his words or blessing in one surface («أمير المؤمنين نعم البيت …» ->
    «أمير المؤمنين»; never «أبي الحسن الرضا», whose qualifier decides the Imam, nor «أبو عبد الله أحمد بن عمار», a kunya and a
    name: `IMAM_SPEECH_START`, or three or more words with no nasab); a sibling that differs from a chain ending at an Imam only
    in its last surface, which names nobody («يتدلك بالزيت», `drop_matn_beside_imam`); a chain that is exactly the start of
    another. A branch that opens with a sentence and names nobody (no report verb or back-reference opens it, no nasab, no Imam)
    is matn, not an isnad (`is_prose_opening`; Amali al-Saduq 93 had 192 such chains).
  - *Links the extractor stopped short of*: «… عن أبي عبد الله عليه السلام» after the last stored link (`with_imam_tail`; the
    honorific must follow, so «قال سألت أبا عبد الله» is not used: owner, not ruled); «… و الحسن بن محبوب جميعا عن X» at the end
    (`with_jamian_tail`), shared by the co-transmitters of that last level.
  - *«جميعا» groups*: commas and «؛» around the links are allowed, the hanging group's opening name is cut from the original
    letters (round 2 wrote the folded «ابراهيم»), and the shaykh list ignores spacing («أبوعلي الاشعري»). al-Kafi «A عن B و C عن
    D عن E» with no «جميعا», A and C both shaykhs of al-Kulayni, is two routes meeting at E (`kulayni_parallel_groups`; Kafi 19
    matches Noor 118532; Kafi 7 has the same shape and gets the same reading).
  - *«غير واحد»* (an unnamed collective) split at the waw of «واحد» into sibling branches «غير» / «احد …» is one mention, marked
    unnamed (`merge_ghayr_wahid`, also for Sunni chains, where the sibling's origin is dropped with it).

### Sunni chains (projection `2026.11.22.5`; audit `chain-audit/sunni/`)

`build_sunni_chains` re-cuts a Sunni report after the K6 source index has been aligned to the bundle's branches; every moved
or trimmed mention keeps its bundle (branch, position) as `origins`, so its source-index claim follows it (the alignment is
never recomputed on the new branches). The rules are the audit's detectors, ported (`surface_gaps`, `seam_positions`):

- **Seam (round 3; round 2's rule cut 27 of 30 sampled chains wrong).** A break between two stored neighbours is a standalone
  «ح» in the text between them, a «ح» stored at the end of a surface («ابن شهاب ح»), or a waw-led verb («وحدثنا») with nothing
  after it. Each break records two facts: does the earlier piece's last name stand right before it (only asides: «وهو ابن زيد»,
  «يعني …», «واللفظ له»), and does only a verb stand between it and the next stored name (a route head). k6:16725's gap
  «ح وحدثنا مسدد، أخبرنا عيسى، … عن» has names after the «ح», so «ثور» is no head: the bundle had already joined that route.
  Pieces are resolved against every route of the report (`resolve_pending`): an earlier piece takes its **shared tail**
  (`shared_tail`) by (a) a later route repeating one of its last two names at a position after that route's head (suffix
  alignment, the extractor's own tahwil rule; «الزهري» and «ابن شهاب» count as one man, `SAME_MAN`, for convergence only), or
  (b), for a «ح» break only, the first convergence word («كلاهما/كلهم/جميعا/كل هؤلاء») after the break that stands directly
  after a later route's name, with no «رسول الله/النبي» between. A piece that does not end at its break, or does not start at a
  head, is dropped only when another route of the report already holds it (its start, resp. its end); otherwise the whole stored
  chain stays as it was (owner: no tested rule, no split; round 1's view guard covers a repeated narrator). A waw-verb break
  without «ح» splits only by (a): k6:4489 and k6:4794 («وحدثنا» with no «ح», turath prints no waw or Bukhari's «قال: وحدثنا»)
  are whole again; k6:28195 («قال وأخبرني», al-Awzaʿi twice) is two routes.
- **Short routes (`complete_short_routes`).** Any route, the bundle's or a split's, whose last name is followed by a «ح» gets its
  shared tail by (a) or (b); 7 of k6:11239's 11 routes stopped there. Co-transmitters joined by a waw at one position
  (`share_co_transmitter_continuations`) share what follows: a route that stops there, or skips a name its partner carries
  split off a verb («مطرف بن طريف، وعبد الملك بن سعيد، سمعا الشعبي»), takes the partner's continuation. Chains are located in
  the text in stored order (`ordered_spans`, also for the co-transmitter test): a repeated head («قتيبة بن سعيد» twice, k6:9600)
  or a common word («أبي» of «حدثنا أبي ومحمد بن بشر», not of «أبو بكر بن أبي شيبة», k6:14609) is found where it stands. One
  written name twice in a row is one mention (no narrator transmits from himself), except a relation («عن أبيه عن أبيه»).
- **Where the extractor stopped (`extend_stopped_branches`, the canonical extractor reused unchanged).** After a wording
  attribution naming a stored co-transmitter («قال ابن المثنى حدثنا», also «قال عبد أخبرنا وقال ابن رافع حدثنا») or a convergence
  word followed by «عن», the extractor is re-run on the text without that span and the branch is extended only when a
  re-extracted branch starts with exactly the stored one (k6:7805). «كلاهما عن X، بهذا الإسناد» adds X (the extractor drops a
  name before a back-reference). After the last stored name, «، أن عائشة، أخبرته» / «سمع X» add X, link by link (at most three).
  Added names have no origin, so no source-index claim moves onto them.
- **A transmission verb is a link** (`split_link_verbs`; round 2's trim dropped the name after it in 162 mentions). «X سمعا Y»,
  «X حدثتني Y», «X أنهما سمعا Y», «X أن Y أخبرته», «الزهري فأخبرني Y» are two names; frame words («أنهما», «يحدث», «زوج») are
  not part of a name, «قد/لقد» before a verb is no name, «ربيبة النبي» is a person. A name split off that the bundle already
  stores next («سمعا جابرا» before «جابر», accusative alif allowed: `same_name`) is not repeated. «أبي ومحمد بن بشر» in one
  surface is two co-transmitters (`split_fused_names`).
- **Asides that are not names.** «وأنا أسمع» (of «قراءة عليه وأنا أسمع»), «في حديث X», «في رواية X», «إنما هو», «الآخران»,
  «كل هؤلاء» join the formula class; a position left empty drops only the position unless a sibling branch holds a name at one of
  this branch's emptied positions and equals it elsewhere (then the branch was the aside's artefact): round 2 dropped any branch
  with an emptied position and k6:21409 and pc_20809 lost their only chain.
- **Clause after a name (round 3, milestone B; re-check pattern 3, `clause_trim`).** The name ends before the first word that never
  stands in one (`CLAUSE_WORD`: «يحدث», «يقول», «أنها», «قراءة», «أما», «إذا», «في», «كانت», «باب» …): «زرارة بن أوفى يحدث», «عائشة
  أنها», «الحارث بن مسكين قراءة عليه», «الزهري أما ابن منصور فقال». A surface that opens with one is no name, except «قال/قالت X»,
  which keeps X. «مرة» cuts only after a name word («سفيان مرة»; «مرة الهمداني», «عمرو بن مرة» stay). A cut that would leave a
  connector («بن») last leaves the surface as written. Long names without such a word are never trimmed. 40 sampled trims: no
  name lost.
- **Formula words** (the audit's high-confidence list: «بهذا الإسناد», «كلاهما», «مثله», «نحوه», «اللفظ», «حدثنا» ...) are cut out
  of a name; a surface with nothing of a name left is dropped; a branch that existed only because an aside («اللفظ لعمرو»,
  «تقاربا في اللفظ») was read as a co-transmitter is dropped (dropping just the aside would join its neighbours). The
  medium-confidence class (7 or more words without a nasab, «أنها», «قال» ...) is left: in the sample it held long names and
  real Companions («عائشة أنها»), so cutting it needs the trailing-frame rule tested on its own.
- **Co-transmitters.** Two neighbours joined only by a waw or comma become one level (two branches), so no pair forms between them.
- **Edition identifications** (`edition_identifications.json`, built by `build_edition_identifications.py` from the audit's
  high-confidence rows that cite a printed edition): basis `edition_identification`, detail the book, volume, page and the
  editor's words. It stands over the source index it corrects (`standing_identity`), is credited `SWI`, and is never called
  verified. The 95 medium «أبي» rows after Ibn Numayr are not stored.
- **Missing link** (`missing_link_after`): the last name is a person who died more than 120 years before the fully named student
  beside him; the chain says a link is missing, no name is invented.

## Chain structure gate (projection `2026.11.22.9`; `src/db/AGENTS.md` §Chain structure gate)

Round 4 stops adding builder rules (three rounds left Sunni at 10.7% -> 17.3% -> 18.0% strict) and gates what is asserted.
`chain_structure.py` (table-tested in `test_chain_structure.py` on the re-checks' rows, `chain-audit/structure-gate/fixtures.json`)
runs per report after every builder and before identities: `assess` returns reason codes per chain; none means
`checked_by_rule`. Inputs: the stored surfaces, which chains are inherited (their names are in the parent's text), and the
detection text: Pure Canon's own chain field, else the OpenITI `sanad_ar`, else `text_ar`. Persian ya/kaf are read as Arabic
for detection only.

- **Detectors in the gate** (codes): `duplicated_link` (neighbours one man: «حماد > حماد بن زيد», a bare name or «ابن X»
  only, since «أحمد بن محمد > أحمد بن محمد بن أبي نصر» are two men), `joined_names` («الحلبي و زرارة»), `ghayr_wahid_half`,
  `short_beside_long` (<= 3 beside >= 5), `repeated_name` (one name key twice, not adjacent; relations and labels excepted),
  `text_between_links` (words between two stored neighbours that are no link word, aside, wording attribution, year phrase or
  name the report stores elsewhere), `text_names_more_after` (a link word naming someone after the last stored link, before
  the matn reaches the Prophet; not for Thaqalayn, where «قال سألت أبا عبد الله» is the unruled Imam convention),
  `not_a_name` (a verb, clause or formula word, digits, one letter, six words without a nasab), `unaccounted_route_marker`
  (more «ح» than routes, or «جميعا/كلهم/كلاهما» with one route), `crossed_routes` (al-Kafi «أبيه > محمد بن إسماعيل», «ابن أبي
  عمير > الفضل بن شاذان»), `many_routes` (a K6 report with three or more routes read from its text) and `work_not_checked`
  (the 15 small Imami works of `UNCHECKED_WORKS`: 11 of 32 sampled chains defective; withdrawn in round 5, see below).
- **Measured only, not in the gate** (`assess(..., measure_all=True)`): `order_not_in_text`, `route_break_inside`, `long_chain`:
  on the labelled set they flagged no defect the gate's detectors had not already flagged, at a cost of correct chains.
- **Retired** (`retire_reason`): every chain of Kitab al-Duafa and Risalat al-Huquq, and a K6 report whose text is a chapter
  heading («باب …»; a Pure Canon report keeps the chain its source's chain field gives).
- **Measurement** (`chain-audit/structure-gate/measure.py`, results beside it): labelled units are the round-3 sample (random
  and populations) plus round-2 items whose report is unchanged since round 2 read it. The greedy curve and the per-tradition
  rates before and after the gate are in `results.json`; the operating point and why: `chain-audit/structure-gate/README.md`.
- **«غير واحد»** merge now also matches Persian letters («غیر») in `merge_ghayr_wahid`.
- Output: `chains.structure_status`, `chains.structure_reasons` (a pg array); `counts.chain_structure` gives status and
  reasons per tradition and the retired chains.

## Gate recalibration (round 5; `chain-audit/round5/README.md`)

Round 4's out-of-sample reading (`chain-audit/round4/`) showed the in-sample rates were too low (Sunni 8.3%, six-books 10.6%, al-Faqih 4/20) and
that the gate withheld mostly correct chains (40/60). `chain_structure.py` was recalibrated on a split: tuning = rounds 2/3, held-out = round 4's 370
chain readings; every change is reversible by name.

- **`FEATURES`** (a frozenset; remove a name to reverse that rule): `gloss_beside_name` (Pure Canon only: «يعني/هو ابن X» beside a name is the
  source's own gloss), `label_formula` («وبهذا الإسناد», «عمن حدثه» are label links), `saying_as_single_link` (3+ words, no nasab word, the whole chain),
  `asker_and_imam_in_one_link` («أخاه», «أخيه», «العبد الصالح» in a link), `tabi_slash` («/» in a link), `hadathanah`, `tail_hearing_shapes` («سمع», «نظر
  إلى», «قرأت على», «نشهد على», «من حدثك قال X», «قال X قال Y» after the last link, nasab-shaped names only), `waan_between_links` (Thaqalayn only:
  «وعن» between stored neighbours; the locator's waw prefix is read in the right neighbour's span, so the slice runs to its end),
  `inherited_tail` (a continuation's own hearing verb after the last name it repeats; never a bare «عن»), `pure_canon_tail_exempt` (a Pure Canon chain is the
  source's field: its later routes are not a lost tail).
- **`UNCHECKED_WORKS` is empty**: the 15 small Imami works are checked by the same tests as the rest (13 of 14 withheld sampled chains were correct).
- **`sibling_skips_link`** is a new gate reason: two routes of one report differ by one interior link.
- **`MANY_ROUTES` stays 3**: raising it releases correct and defective chains at 18 to 22% defective (`results.json`).
- Pure Canon note: `text_names_more_after` for Pure Canon read the chain field's own later routes as a lost tail (11 of 11 correct): exempt.
- Ablation (`recalibrate.py`): each change's flagged and released counts on both sets and in production; `fixtures.json` (real round-4 rows) drives the
  new tests in `test_chain_structure.py`.
- The recalibrated gate is NOT measured out of sample: its held-out gains rest on shapes read from the same items. Public wording (`/method`) says so.


## Chain fixes (projection `2026.11.22.12`; `src/db/AGENTS.md` §Chain fixes)

`chain_fix_projection.py` replays `chain-fixes/accepted_overrides.jsonl.gz` (`--chain-fixes`; absent or empty: nothing changes,
`counts.chain_fixes = {"overrides": 0}`) after every builder and before the gate, through `chain-fixes/replay.py`: a broken binding
(Arabic or reader text changed) drops the row and counts it; `replace_routes` takes the planned branches (kept names bring their
`origins`, so K6 and edition claims follow them; external claims move to the new mention id or are dropped and counted);
`set_status` / `annotate` mark the rule-built branches. A replayed branch is not gated: its status is the fix's, `chains.chain_fix_id`
names it. The manifest binds the overrides file and `replay.py` by SHA-256 (`inputs.chain_fixes`).

## Compiler as first transmitter (projection `2026.11.22.12`; owner ruling 2026-11-22)

`work_register.py` with `work_register.json` (owner-reviewable). Every chain of a work with a compiler gets `compiler_narrator_id`
and `compiler_link`; no mention is added, so ids, positions, review units and the gate's text checks are unchanged.

- **Not doubled**: no head when the text already writes him: the reader tool's own alias rule (`chain-reader/v3/expand_v3.py`
  `compiler_written` over `v3/work_profiles_v3.json`: the first written link under any listed spelling, any link for the Muwatta),
  the register's forms, or a standing identity on his record. Both files are bound in the manifest (`inputs.reader_v3_work_profiles`).
- **direct / indirect**: `direct` (a pair forms in the view) when the chain is not suspended and its opening is his own hearing:
  Sunni works and Musnad Zayd open with a hearing verb (`DIRECT_VERB`; «قال: أخبرني» quoting him counts, al-Mufid's Amali);
  works that open with the shaykh's name (al-Kafi, al-Saduq, al-Husayn b. Saʿid ...) are direct unless the opening is «قال»,
  «روى», «وعن», «عنه», «بهذا الإسناد» ... (`INDIRECT_OPENING`); al-Rabiʿ only when the first link is Abu ʿUbayda (the work's fixed
  shape). Otherwise `indirect`: the head is shown, no pair.
- **Records** (`narrators` with authority `work_register`, profile `work_register` naming the work): reused only where a standing
  rule of the tradition already identifies the person (counted on production; `reuse_basis` in the JSON), else created and credited
  to the work. Works without a compiler and why: `works_without_compiler`.
- **Named in full** (`named_in_full`): a transmitter the work's own opening report names in full where no source identity stands
  gets a work record and the basis `named_in_opening_isnad` (detail quotes the report). Musnad al-Rabiʿ: «أبو عبيدة» = Abu ʿUbayda
  Muslim b. Abi Karima al-Tamimi (rabi_0001); a source's confirmed claim on those mentions (Riwayat N0013779 «مسلم بن أيمن») is kept
  as an unconfirmed candidate (`demote_kunya_only`, detail says why).

## Bare kunya rule (projection `2026.11.22.13`; owner ruling 2026-11-22, narrowed the same day)

The ruling: a bare kunya (`external_identity.bare_kunya_key`: «أبو/أبي/أبا/أم X», «أبو عبد X») stands as an identity only when it is not
ambiguous: Abu Hurayra passes, a kunya genuinely shared by several narrators stays a candidate. **It applies where no curated per-report
narrator index exists: the three OpenITI works** (`KUNYA_RULE_WORKS` = `chain_builder.OPENITI_WORKS`: Musnad al-Rabiʿ, Musnad Zayd, Sahifat
al-Rida). There a standing identity on a bare kunya needs exactly one person carrying it in the work's own source (counted per work, kunya and
source over the written bare-kunya mentions: `KUNYA_RULE_AUTHORITIES`: K6, hadith-kg, Riwayat; placeholder and label-like records not counted);
else it is withheld with `identity_withheld_reason` «kunya only: N people carry «X» in this work's source ...», candidates unchanged. Everywhere
else (K6, Pure Canon and the Imami works) the source's own per-report assertion stands, as before `9532839`. Exempt in all works:
`imam_kunya_convention`, `named_in_opening_isnad`, `edition_identification`. Counts: `identity_candidates.standing_withheld_by_kunya_rule`,
`standing_bare_kunya_one_carrier`.

**Why not "one carrier in the work" everywhere (the first form, `9532839`).** A large work's source names a second bearer of almost every
common kunya somewhere (Musnad Ahmad's source gives 5 people for «أبي هريرة»), so the count failed the ruling's own example: it withheld 4,357
Sunni and 22 Imami identities of which 28 of 30 read were right. Options measured on those 4,431 (a bare-kunya identity with a standing source
claim, count by the same data) against a stratified fresh reading of 135 (`chain-audit/compiler-ruling/kunya_options/`): (a) OpenITI only;
(b) stands when one person holds at least 90, 95 or 98 percent of the kunya's assertions in the work's source; (c) as (b), or when the asserted
person is chronologically possible or attested against a neighbour (`chain_chronology`). Every stratum at 90 percent dominance or more read
90 of 90 right; the low-share stratum 39 of 45 (5 wrong, 1 unclear); share does not separate the wrong ones (right: 0.05 to 0.41; wrong: 0.03
to 0.59). Each of (b) and (c) withholds hundreds to thousands of right identities to catch the same ~160 wrong ones, so (a) ships.
In the three OpenITI works the rule withholds nothing today: every bare-kunya identity there has one carrier (60 Abu Hurayra mentions in
al-Rabiʿ, plus Abu Saʿid, Umm Salama), so the withholding case is covered by the pure rule and real claim counts (`test_identity_rules.py`).
