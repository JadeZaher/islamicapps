# reconciled (non-destructive re-ETL sidecars)

Source data the canonical pipeline drops, recovered from the original files and keyed by the canonical
`record_id`. Nothing here writes `chain_indx`, `text_ar` or any canonical CSV, GZIP or manifest, and nothing here is a
release input. A source-provided id is the source's claim, not a verified identity. Every row carries
`review_state: unreviewed`.

## Build (repository root; deterministic: identical inputs give byte-identical outputs)

```
python -B datasets/hadith-data/reconciled/build_k6_source_index_sidecar.py     # about 1 minute
python -B datasets/hadith-data/reconciled/build_pure_canon_chain_sidecar.py    # about 1 minute
```

The scripts reuse `diagnostics/chain-reconciliation/reconcile_common.py` (corroboration tiers, alignment) and import
the canonical normalizer and extractor at run time. The output layout is fixed: JSON with sorted keys, gzip mtime 0,
and no timestamps. Input and code SHA-256 values, output hashes and counts are in each `*.manifest.json`.

## Files

| File | Key | Contents |
| --- | --- | --- |
| `k6_source_index.jsonl.gz` | `k6:<id>` (the canonical K6 key from `all_hadiths_clean.csv.gz`) | Original K6 `chain_indx` from `archive/datasets.7z` as an ordered id list, `agreement_class` against the Arabic, `basis`, per-position name tiers or aligned positions, ids missing from the registry, `arabic_sha256` for join verification |
| `pure_canon_chain.jsonl.gz` | `pure-canon:<pc id>` | The source's separate `chain` text byte-for-byte, `chain_sha256`, the canonical extractor's branches, `chain_status`, and how many surfaces a `text_ar` extraction would invent (`text_ar` is matn only for these works) |
| `no_chain_in_source.jsonl.gz` | `pure-canon:<pc id>` or the canonical `thaqalayn:` key | Reports whose source has no isnad (`source_dataset_ships_no_chain`: Pure Canon rows without `chain`, all of Shafi'i; `work_without_isnad_by_design`: Nahj al-Balagha). `suppress_extracted_chain: true`: never show a chain extracted from their text |

## Basis labels (K6)

| `basis` | When |
| --- | --- |
| `source_index_corroborated_by_text` | `full_agreement` (same length, every position name-consistent) or `multi_branch_all_source_ids_aligned` |
| `source_index_<class>` | Any other class: `same_length_name_mismatch`, `length_differs_source_longer`, `length_differs_text_longer`, `multi_branch_partial`, `no_text_chain`, `extraction_limit` |
| `no_source_index` | The original row had no ids |

Corroboration tiers and the alignment rule are described in `diagnostics/chain-reconciliation/README.md` §Method.
Corroboration uses the resolver at build time, so rebuild after any resolver change.

## Joins

- **K6.** The original CSV's `id` is not unique, so rows join by file position. The Arabic and the source label must
  be byte-identical to the canonical input; a mismatch aborts the build.
- **Pure Canon.** Rows come straight from `pure_canon.jsonl` for the four ingested works. The key is the loader's own
  `pure-canon:<id>`.
- **Nahj al-Balagha.** The key is built with `regen.apply_thaqalayn_identity` from the provider file id and the
  upstream hadith id.

## Not carried

The Pure Canon closing compiler statements (workbook column L) and edition header rows are already extracted by
`diagnostics/grading-recovery/` and `diagnostics/provenance-recovery/`. The Companion-named column was not attempted.

## External sources: hadith-kg and the Riwayat corpus

What two open datasets say about our reports' chains, carried onto our own report and mention ids. A dataset's
narrator id is **that dataset's claim**; agreement with our Arabic is recorded, never a verification. Our tradition
is always carried; identities are never merged across traditions; nothing here imports a computed verdict or grade.
Measurements, the Imami sample and the review worksheet are in `diagnostics/source-identity/`.

```
python -B datasets/hadith-data/reconciled/build_external_report_crosswalk.py     # ~1.5 min
python -B datasets/hadith-data/reconciled/build_external_identity_sidecars.py    # ~4 min, needs the crosswalk
python -B datasets/hadith-data/diagnostics/source-identity/measure_source_identity.py   # ~1 min
cd datasets/hadith-data/reconciled && python -B -m unittest test_external_source_logic
```

Inputs, all read-only: `datasets/sources/external/hadith-kg/hadith-kg.db` and
`datasets/sources/external/riwayat-corpus/hadith_master.db` (opened `mode=ro&immutable=1`, nothing in those
directories executed), the record_id corpus `development/incomplete-curation/all_hadiths_unified.incomplete.csv.gz`,
the loaded projection `development/pg-load-2026-11-21/projection-candidates/canonical/` (`chain_mentions.csv` for
the mention ids, `chain_mention_candidates.csv` for today's K6 claims), the lexicon, and the biography-recovery date
candidates. Every input, code file and output is bound by SHA-256 in the two manifests. **If the projection is
rebuilt, rebuild these sidecars**: claims are keyed by its mention ids and carry `surface_ar` so a loader can refuse
a mismatch.

### Modules

| File | What |
| --- | --- |
| `external_source_logic.py` | Pure rules: work map, match selection, external placeholder names, basis labels, Riwayat id origin, lexicon-link rule, Qur'an label parsing and re-location |
| `external_source_io.py` | Paths, read-only SQLite connection, corpus and projection readers, licence lines |
| `build_external_report_crosswalk.py` | Step 1, the report crosswalk |
| `build_external_identity_sidecars.py` | Steps 2, 3 and 5: registries, lexicon links, per-mention claims, Qur'an spans |
| `test_external_source_logic.py` | Table-driven tests on real rows, including the cases that must not match, link or corroborate |

Reused, not copied: `narrator_normalize` and the name folds (`regen_unified_csvs.py`), `MatnIsolator`
(`diagnostics/report-correspondence/matn_isolation.py`), `classify` and `align`
(`diagnostics/chain-reconciliation/`), `align_source_index` (the projection's shared-trunk rule, imported from
`pg_export/export_postgres.py`), `rijal_sources.name_key` and `_raw_years` (`diagnostics/biography-verification/`).

### Method

**1. Report crosswalk** (`external_report_crosswalk.jsonl.gz`). Letters-only text: `narrator_normalize`, then Arabic
base letters. hadith-kg writes an editorial label after each Qur'an quotation (`سورة العلق آية 1-3`); it is
removed from the external text first (Riwayat's Sunni texts inherit it), otherwise no report quoting a verse could
ever match. Classes: `whole_text_equal`; `our_matn_contained` (our matn, isolated by `MatnIsolator`, at least 40
letters, is a substring of their text starting and ending at word boundaries); `ambiguous` (several same-work
candidates, or one external report picked by several of ours: recorded with up to 10 candidates, never used). Only
external books mapped to our `source_work_id` (`WORK_MAP`) are read: a parallel in another book is a different
report with a different chain. Riwayat's `tradition` is kept as `external_tradition_label` only (it labels Musnad
Zayd and Musnad al-Rabi' `sunni`). Both Arabic hashes are stored (`arabic_sha256` ours, `external_arabic_sha256`
theirs, of the text as stored).

**2. External narrator registries.** One row per narrator as the dataset describes it, fields verbatim under
`dataset_assertions` with `asserted_by`, never verified here. hadith-kg: `rawis` (rank wording, tabaka, raw
birth/death strings, age, residence, death place, nasab, profession, tadlis/ikhtilat flags, stub flag), the chain
positions it occupies per tradition context (book 55 Zaydi, book 56 Ibadi, the rest Sunni), and the Riwayat
narrators whose `kg` crosswalk points at it. Riwayat: `narrator` fields, every non-`observed` name form with type and
source, the crosswalk ids (`itq`, `chains`, `kg`, `sh`, `thq`, `mids`), quality flags, and asserted mentions per
tradition context (Musnad Zayd and Musnad al-Rabi' re-attributed).

**Lexicon links** (`external_narrator_lexicon_links.jsonl.gz`). No dataset carries a muslimscholars id, so there is
no explicit crosswalk to `scholar_indx`. A link needs all of: the canonical name key (`rijal_sources.name_key`) held
by exactly one narrator in that dataset and exactly one non-placeholder lexicon row; the narrator appears in Sunni
chains (the lexicon is the Sunni-centred register; an Imami-only narrator never links); and corroboration, either an
overlapping death year (lexicon year from `biography-recovery`, hadith-kg's raw year or Riwayat's `death_year`) or K6
position agreement (at the mentions where both claim someone, the K6 id is this lexicon row for the strict majority
of both the external narrator's and the lexicon row's co-claims). A year conflict blocks a name+year link. A lexicon
row claimed by two external narrators links to neither. Riwayat narrators with exactly one `kg` crosswalk id whose
hadith-kg narrator is linked inherit that link (`riwayat_kg_crosswalk_to_linked_hadith_kg_narrator`), once per row.
Placeholder names and hadith-kg stubs never link. Two external narrators are never merged.

**3. Per-mention source claims** (`external_mention_claims.jsonl.gz`, keyed by `mention_id`). The external ordered
list: hadith-kg `sanad_rawis` of every sanad of the report in id order, the author at `pos 0` dropped; Riwayat
`chain_mention` by `chain_no`, `pos`, with mentions that carry no asserted id kept as unknown positions (they count
for length and can never corroborate). `guess_narrator_id` is not used. Our side: the projection's branches. The K6
`classify` runs unchanged through `ExternalNames`, a stand-in registry whose forms are the dataset's own names
(hadith-kg `name`, `nickname`; Riwayat `std_name` and every non-`observed` form; never the observed chain surfaces,
which would make the check circular) with no parent links (so `أبيه` is never corroborated). Claims are emitted
only at aligned positions (name-consistent under the K6 tiers), plus a taḥwīl branch position that inherits through
an identical opening (`align_source_index`, `:shared_trunk`), exactly as the K6 projection does. External names that
cannot name a person (relational, collective, bare single token, no name) are dropped and counted; kunya-only names
and hadith-kg stubs are carried but never confirmed.

**5. Qur'an quotations** (`hadith_kg_quran_citations.jsonl.gz`). For each used hadith-kg match, each `hadith_ayas`
span: the labels are parsed (sura name, sura number from the 114-name table, aya range, verbatim label), the
remaining quotation is normalized and must occur exactly once in our letters-only text, starting and ending at word
boundaries, and our text must give the same letters character by character as whole-string. The span is then mapped
back to code-point offsets in our `text_ar` (trailing marks included), with `quote_ar` and its hash. Nothing is
guessed: a span that is absent, repeated, shorter than 10 letters, or in a report whose normalization is not
character-local is not emitted (counted in the manifest). Verse references are hadith-kg's; a label naming no known
sura keeps `sura_number: null`.

### Basis labels (mention claims)

| `basis` | When |
| --- | --- |
| `source_hadith_kg_confirmed_by_text` / `source_riwayat_confirmed_by_text` | The report's class is `full_agreement` (same number of names, every position name-consistent) or `multi_branch_all_source_ids_aligned`, and the external name is person-like (not kunya-only, not a hadith-kg stub) |
| `source_hadith_kg` / `source_riwayat` | Any other class, at a position the alignment corroborates (or inherits through a shared opening) |

Each claim also carries `report_agreement_class`, `name_tier`, `shared_trunk`, `agreement_detail`, the external report,
chain and position, the external narrator id and name, `external_name_flag`, the lexicon link if any, and for
Riwayat `external_id_method`, `external_id_confidence` and `external_id_origin`: `upstream_annotation` (hadith-kg's or
Thaqalayn's own annotation carried by Riwayat), `riwayat_manual_gold`, or `riwayat_automatic_linking` (Riwayat's
linker, ranker, joint tagger, gap model or Claude labels: a machine assertion).

### Not imported

hadith-kg `sanads.hukum` (a computed sentence on the isnad) and `matn` hukm labels, `max_rank`, `aqwal`, meaning
groups and embeddings; Riwayat `guess_narrator_id`, `narrator_edge` and its suspect flags, `isnad_node` floruit ranges,
and Claude labels except as the recorded `id_method` of an asserted id. hadith-kg's `rank` wording is carried in the
registry as the dataset's unattributed assertion and must not be displayed as a verdict.

### Files and results (build of 2026-11-21; all bytes reproduced by a second build)

| File | Rows | Licence | Contents |
| --- | ---: | --- | --- |
| `external_report_crosswalk.jsonl.gz` (+ `.manifest.json`) | 91,791 | hadith-kg CC BY 4.0; Riwayat CC0 (texts: their sources) | One row per (our report, dataset) with any same-work candidate: class, `used`, candidates, both hashes, external locator |
| `hadith_kg_narrators.jsonl.gz` | 49,844 | CC BY 4.0 | hadith-kg narrators as hadith-kg describes them |
| `riwayat_narrators.jsonl.gz` | 193,014 | CC0 (names inherited from hadith-kg CC BY 4.0, from Thaqalayn CC BY 4.0) | Riwayat narrators, name forms, crosswalk ids, flags |
| `external_narrator_lexicon_links.jsonl.gz` | 3,051 | as its dataset | Candidate links to `scholar_indx` with the evidence |
| `external_mention_claims.jsonl.gz` | 366,007 | as its dataset | Per-mention source claims keyed by our `mention_id` |
| `hadith_kg_quran_citations.jsonl.gz` | 1,197 | CC BY 4.0 | Qur'an quotation spans in our text's coordinates with hadith-kg's verse reference |
| `external_identity_sidecars.manifest.json` | | | Inputs, code and output hashes; counts below |

**Crosswalk (used = unique on both sides, same work):**

| Our tradition (reports) | hadith-kg whole / matn / ambiguous | used | Riwayat whole / matn / ambiguous | used |
| --- | --- | ---: | --- | ---: |
| Sunni (64,356) | 21,662 / 11,125 / 3,257 | **50.9 %** | 21,487 / 10,529 / 4,028 | **49.7 %** |
| Imami (33,225) | no Imami work in hadith-kg | 0 | 17,427 / 1,157 / 139 | **55.9 %** |
| Ibadi (1,004) | 254 / 153 / 21 | 40.5 % | 254 / 148 / 26 | 40.0 % |
| Zaydi (698) | 0 / 62 / 0 | 8.9 % | 0 / 13 / 49 | 1.9 % |

By work (hadith-kg used %): al-Nasa'i 91.8, Ibn Majah 84.6, Bukhari 74.0, Abu Dawud 70.6, Tirmidhi 59.3, Muslim 56.7
(1,395 ambiguous: Muslim repeats texts), Ahmad 28.4, Darimi 25.6, Muwatta 21.8, Shafi'i 11.1 (the Pure Canon
matn-only editions differ). Riwayat Imami: Kitab al-Zuhd 96.2, Amali Mufid 93.8, Kamil al-Ziyarat 90.4, Mu'jam 78.9,
al-Kafi 74.6, Fada'il 64.4, Ghayba Nu'mani 56.4, Faqih 53.5, Ghayba Tusi 50.3, Ma'ani 43.5, Khisal 41.6, Amali Saduq
38.4, Sifat 33.8, Tawhid 32.9, Thawab 30.9, Uyun 22.5, Mu'min 8.0, Du'afa' 1.3, Nahj 0.1 (2 rows in Riwayat). These are
lower than the earlier "any book, any candidate" join (`diagnostics/biography-verification/`: al-Kafi 93.1 %) because
uniqueness on both sides and the same work are now required. Independent checks, not used for matching: Riwayat's
own `kg` id equals our hadith-kg text match for **32,430 of 32,430** reports matched in both; Riwayat's Thaqalayn
locator ends in our URL's chapter and hadith numbers for 14,579 of 18,584 Imami matches (the 4,005 others are
numbering-scheme differences: the Faqih's global hadith numbers, chapters off by one).

**Claims** (mention claims by basis): Sunni hadith-kg 40,283 confirmed + 105,921 unconfirmed, Riwayat 90,752 +
66,325; Imami Riwayat 15,606 + 45,692 (after the kunya flag); Ibadi hadith-kg 539, Riwayat 697 + 178; Zaydi 14. Dropped
as placeholder names: Imami 6,380 bare single token, 168 collective, 92 relational; Sunni 5,993 single token. Report
classes, hadith-kg Sunni: full 7,147, all aligned 491, same length name mismatch 10,126, source longer 7,585, partial
4,946; Riwayat Imami: full 3,735, all aligned 254, name mismatch 9,415, text longer 2,366, source longer 1,411, partial
1,330. hadith-kg has no kunya or laqab field, so `غندر`, `أبي الزبير`, `أبو بكر بن أبي شيبة` never confirm against it.

**Lexicon links**: hadith-kg 1,194 (327 name+year, 537 name+K6, 330 both), Riwayat 1,857 (317 / 545 / 503, plus 492
through Riwayat's kg crosswalk; 659 Riwayat narrators linked directly agree with their crosswalk, 0 disagree). Not
linked: name not unique (3,938 hadith-kg, 12,030 Riwayat), no corroboration (3,202 / 3,195), no Sunni context (71 /
2,555), year conflict (63 / 97).

**Qur'an**: 1,615 spans in matched reports, 1,197 re-located (896 in whole-text matches, 301 in matn matches), 1,194
with a verse reference; not re-located: 264 absent from our (partial) text, 106 repeated, 48 under 10 letters.

Gains, the three-way agreement and the Imami sample are in `diagnostics/source-identity/README.md`.

### Load proposal (not implemented; the schema and loader belong to the data-platform lane)

**a. Candidate bases.** Add four values to `mention_candidate_basis`: `source_hadith_kg`,
`source_hadith_kg_confirmed_by_text`, `source_riwayat`, `source_riwayat_confirmed_by_text`. One
`chain_mention_candidates` row per claim: `id = candidate:<record_id>:<branch>:<position>:<basis>:<external narrator
id without "narrator:">`, `narrator_id` the external narrator row (b), `detail = agreement_detail`, `source_position =
external_list_index`; widen the `source_position` check to the six source bases. Add two nullable columns, each set
exactly for the four new bases: `source_ref` (`hadith-kg:hadith:<id>` or `riwayat:<H id>`, from the crosswalk) and
`source_assertion_origin` (`dataset_index` for hadith-kg; Riwayat's `external_id_origin`). The loader refuses a
claim whose `mention_id` is not live or whose `surface_ar` differs from the mention's, and a report whose
`arabic_sha256` differs from `hadiths.arabic_sha256`.

**b. External narrators.** Add `hadith_kg` and `riwayat` to `narrator_authority` (`imami_rijal` stays reserved for a
curated Najashi/Tusi authority: Riwayat's Shi'i narrators are mostly Thaqalayn's per-label ids, not rijal entries).
Rows: `id = narrator:hadith-kg:<rawi id>` / `narrator:riwayat:<N id>`, `authority_key` the dataset id, `scholar_indx`
null, `name` and `name_ar` the dataset's name as written, `placeholder_reason` from `name_placeholder_reason`
(extend `narrator_placeholder_reason` with `relational_name`, `collective_or_anonymous_name` and
`hadith_kg_stub_narrator`). Load only narrators that some claim names or that a link names, not the whole registries.
New pipeline tables: `narrator_external_ids (narrator_id, namespace, external_id, asserted_by)` for Riwayat's
crosswalk ids, and `narrator_source_profiles (narrator_id, source, assertions jsonb, licence, review_state default
'source_unverified')` for `dataset_assertions`; `narrators` keeps no verdict column (G-1) and hadith-kg `rank` stays
in the jsonb, never displayed as a verdict. The machine lexicon links go to a candidate table
`narrator_link_candidates (external_narrator_id, rawi_narrator_id, basis, evidence jsonb, review_state)`; only a
reviewer promotes one into `narrator_same_as` (G-5: never automatic).

**c. What counts as verified.** The owner's rule, per mention: a source claim confirmed by the text and uncontested.
Proposed precisely: a candidate verifies when its basis ends in `_confirmed_by_text`, its `source_assertion_origin`
is not `riwayat_automatic_linking` (Riwayat's linker is a machine) and its name is not flagged, and no other candidate
of the mention is known to name someone else. "Known": same authority and a different id, or a different authority
whose narrator is linked (reviewed `narrator_same_as`, or a link candidate) to a different person. An unlinked
cross-authority pair (K6 says lexicon 20005, hadith-kg says its rawi 3443) is "not comparable", not a contest, and the
mention verifies to the lexicon narrator when K6 confirms, else to the external narrator. Two sources: K6 and
hadith-kg are independent compilations (muslimscholars-derived ids vs hadithdb 2017), and at mentions both claim they
pair the same way at least 93.7 % of the time (`diagnostics/source-identity/`). Riwayat's Sunni ids are 99.8 %
hadith-kg's own annotation (`source_annotation_kg`), so Riwayat agreeing with hadith-kg is **not** a second source.
The Imami sample supports the origin rule: 52 Thaqalayn-annotation rows read 0 wrong, 8 automatic-linking rows read
1 wrong (and 4 of 4 wrong in an earlier draw). Kunya-only names never verify under the owner's rule; that includes the
Imams (`أبي عبد الله ع`, 11,928 mentions), whose kunya is conventional in Imami usage. Whether Imami chains get an
exception for the Imams' kunyas is an owner question. Recommendation:
show "two independent sources agree" (K6 + hadith-kg, or hadith-kg/Thaqalayn + a reviewer) as a label, and let
independent agreement at a name-consistent position verify a mention whose report class is not full; owner decision.

**d. Qur'an citations.** A pipeline table `hadith_quran_citations`: `id = quran:<record_id>:<start>:<end>:<n>` (one
row per verse reference; a span without a reference gets one row with null verse), `hadith_id` FK, `start`, `end`
(code points of `hadiths.text_ar`), `quote_sha256`, `sura_number` (1-114, null allowed), `sura_name_as_written`,
`aya_from`, `aya_to`, `label_verbatim`, `basis = 'source_hadith_kg'`, `source_ref` (`hadith-kg:hadith:<id>:<seq>`),
`review_state` default `unreviewed`, pipeline bookkeeping. Load check: `substring(text_ar from start + 1 for end -
start)` hashes to `quote_sha256` (Postgres counts characters, as Python does).

**e. Attribution on the page.**
- hadith-kg (CC BY 4.0; requires credit, licence link and an indication of changes), wherever a `source_hadith_kg*`
  candidate, a hadith-kg narrator or a Qur'an reference from it is shown: "Narrator identification [Qur'an
  reference] from hadith-kg (الجامع — Hadith Knowledge Graph) by emadjumaah, CC BY 4.0. Matched to this text by Shura
  wa Istehsan; not reviewed." Link the dataset page and https://creativecommons.org/licenses/by/4.0/.
- Riwayat (CC0 for the authors' layer; attribution not required, citation requested): "Narrator identification from
  the Riwāyāt corpus (Abdullah Ansar, v1, Zenodo 2026, doi:10.5281/zenodo.23630501)." When `external_id_method` is
  `source_annotation_kg`, add the hadith-kg line (the id is hadith-kg's, CC BY 4.0). When it is
  `source_annotation_thaqalayn` or `thaqalayn_id_on_reparsed_span`, add: "Identification by Thaqalayn (Stichting
  Thaqalayn), CC BY 4.0; changed: re-keyed to this edition. Not endorsed by Thaqalayn." (Thaqalayn's terms, quoted
  in `docs/rights/rights-register.md` §4.)
- A page that shows several bases shows each line once, next to the chain; a credits page lists all three.
