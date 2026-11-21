# rijal: the author-rooted rijal layer (load-ready, unreviewed)

Every rijal entry is kept under the AUTHOR and WORK it comes from, many per narrator, labelled by that author. A link
from a narrator (lexicon row, Riwayat label, or a name as written in our Imami chains) to an entry is a
**candidate**: several candidates are never resolved to one, ambiguous links are kept with their evidence, and no
link crosses traditions on a name. Verdict words are recorded exactly as written, in the scheme of the author who
wrote them. Nothing here asserts an identity, grade or date. Everything is `review_state: candidate_only`.

## Licence and credit

Everything derived from the OpenITI rijal texts is **CC BY-NC-SA 4.0** (attribution, non-commercial, share-alike).
Source short reference **RIJ**. Each work's `required_attribution` line is in `output/rijal_works.json`; every
record repeats work, edition, locator, verbatim passage, source span and source SHA-256 in its `citation`.
Riwayat labels: CC0 (their own layer). Lexicon (`all_rawis.csv`) and hadith-kg (CC BY 4.0) appear only in the
availability index, as their own sources, never as rijal text.

## Inputs (SHA-256)

| Input | SHA-256 |
| --- | --- |
| OpenITI `0852IbnHajarCasqalani.TaqribTahdhib.JK000121-ara1.completed` | `178d493bd150032bc64a81ed4397d7e4a828209ee690deed283c1e63cada4637` |
| OpenITI `0742Mizzi.TahdhibKamal.Shamela0003722-ara1.mARkdown` | `f4f26e71dd9c0c70ef09285fc0b4de8abe3fe586c0eddba19985155df175f58f` |
| OpenITI `0450Najashi.Rijal.Shia002931-ara1.mARkdown` | `a34bc95dbf6afef2b860bfd99e6a47fd16e3d16d2879ab145d30bf0abb5941e6` |
| OpenITI `0460ShaykhTusi.Rijal.Shia002935-ara1.mARkdown` | `955b2b7114a5e2d96f11d23b0638c4ab2c9ec3a57ab13119d97cf7c2e128f678` |
| OpenITI `0460ShaykhTusi.Fihrist.Shia002934-ara1.mARkdown` | `1c4975a18ca0bae40d4c062edad05eef5a8c2c243951dcc2a9bf785415db88df` |
| OpenITI `0460ShaykhTusi.IkhtiyarMacrifatRijal.Shia002932VolsBK1-ara1.mARkdown` | `788e8c530c1c48f76c6df0b6b0cca4ecec5ad27a1c64aa5fa9a0069ae94f3787` |
| `inputs/imami_chain_mentions.tsv.gz` (production, dataset version `e2430eae…`, SELECT only) | `f6c89576c69ddb73b65d5ac227ceba446b8d16f5223da7b4e04066aa2d968f16` |
| Riwayat `hadith_master.db`, lexicon `all_rawis.csv`, code files | in `output/rijal_manifest.json` `inputs_sha256` |

## Commands (repo root; standard library; no network; no database writes)

```
bash datasets/hadith-data/rijal/export_imami_chain_mentions.sh       # refresh the chain snapshot (read-only session)
python -B datasets/hadith-data/rijal/build_rijal_layer.py            # ~8 min, deterministic bytes
python -B datasets/hadith-data/rijal/validate_citations.py           # pre-load citation check, exit 1 on failure
python -B datasets/hadith-data/rijal/render_narrator_matrix.py --scholar-indx 11358
cd datasets/hadith-data/rijal && python -B -m unittest test_rijal_extract
```

## Modules

| File | What |
| --- | --- |
| `rijal_extract.py` | Pure: verdict terms per author scheme with negation / hearsay / other-subject flags; Imam readings; teachers, students, routes; books; Kashshi sections and reports; Mizzi lists; name shapes and match bases; life facts; gazetteer; citation checks |
| `build_rijal_layer.py` | Registry, entries, statements, perspective cells, timelines, links, availability, events, coverage, samples, manifest |
| `validate_citations.py` | Re-reads every cited span from its source file and checks hash and passage |
| `render_narrator_matrix.py` | One narrator's perspectives matrix and per-source timelines (the page shape) |
| `export_imami_chain_mentions.sh` | The production chain snapshot (SELECT only, `default_transaction_read_only=on`) |
| `test_rijal_extract.py` | Table-driven tests on real passages, including passages that must not yield a verdict |

Reuse: `diagnostics/biography-verification/rijal_parsing.py`, `rijal_sources.py`, `verify_lexicon_against_rijal.py`
(Taqrib and Mizzi parsers, conservative lexicon link), `reconciled/external_source_logic.py`
(`external_name_placeholder`), `regen_unified_csvs.py` name folds; all imported, none edited. Extensions are made at
runtime only: women (`### $$`) in al-Tusi and al-Mizzi, Taqrib's four `$DIC_NIS$` entries, Mizzi numbers in
parentheses `(412)`, and al-Kashshi's `### |` sections.

## Registry (`output/rijal_works.json`)

| Work id | Author (death, from the OpenITI header) | Tradition | Edition (header) | Verdict scheme |
| --- | --- | --- | --- | --- |
| `rijal_work:ibn_hajar_taqrib` | Ibn Hajar al-Asqalani (852) | sunni | ed. Muhammad Awwama, Dar al-Rashid, 1406 | `ibn_hajar_taqrib_maratib` |
| `rijal_work:mizzi_tahdhib_kamal` | al-Mizzi (742) | sunni | ed. Bashar Awwad Ma'ruf, Mu'assasat al-Risala | `mizzi_reported_statements` (critics he quotes become their own perspectives) |
| `rijal_work:najashi_rijal` | al-Najashi (450) | imami | 5th printing, 1416 | `najashi_rijal_terms` |
| `rijal_work:tusi_rijal` | al-Tusi (460) | imami | ed. Jawad al-Qayyumi al-Isfahani, 1415 | `tusi_rijal_terms` |
| `rijal_work:tusi_fihrist` | al-Tusi (460) | imami | ed. Jawad al-Qayyumi, 1417 | `tusi_fihrist_terms` |
| `rijal_work:kashshi_ikhtiyar` | al-Kashshi, selection by al-Tusi (460); al-Kashshi's own date not in the header (null, stated) | imami | Mir Damad / Mahdi al-Raja'i, 1404 | `kashshi_reported_statements` |

## Entries and what was extracted

| Work | Entries | Statements (on subject / flagged) | Generation | Death clause / with a year | Teachers / students | Books |
| --- | ---: | --- | --- | --- | --- | --- |
| Taqrib | 8,828 | 8,203 / 0 (verdict span) | tabaqa 8,460 | 2,947 / 2,657 | - | - |
| Tahdhib al-Kamal | 8,643 (incl. 266 women) | 11,722 (4,782 entries with one on the subject / 765 flagged), attributed to the quoted critic | - | 2,811 / 1,856 | 6,863 / 7,371 | - |
| al-Najashi | 1,269 | 851 (673 / 14) | Imams named 369 | 58 / 22 | 176 / 600 | 3,032 in 1,028 entries |
| al-Tusi, Rijal | 6,429 (incl. 64 women) | 699 (681 / 3) | Imam chapter for every entry: al-Sadiq 3,225, al-Baqir 468, Prophet 468, Ali 449, al-Rida 319, al-Kazim 273, al-Hadi 187, al-Sajjad 171, al-Jawad 116, al-Askari 103, al-Husayn 99, al-Hasan 41, none 510 | 151 / 74 | 109 / 413 | - |
| al-Tusi, Fihrist | 910 | 164 (132 / 2) | Imams named 11 | 7 / 2 | 14 / 635 (route students) | 1,273 in 846 entries |
| al-Kashshi | 428 sections (5 paratext skipped), 1,158 reports | 149 (20 / 127: a report term counts for the subject only when the clause names him) | - | 22 / 2 | - | - |

Term flags: `negated` (ليس بثقة), `hearsay_or_reported` (يقال: إنه كان فطحيا), `subject_may_differ` (أخوه ثقة),
`speaker_quoted`; `عدة من أصحابنا` and every term inside a transmission route are not terms. Dates keep ranges,
`وقيل` alternatives, bounds, and regnal datings (`في خلافة عمر`) unnormalised.

## Links (`rijal_links_*.jsonl.gz`; every candidate kept, `selected: false`)

- **Lexicon -> Taqrib / Tahdhib** (tier A full key, tier B exact nasab chain + tokens; parity: all 9,514 of
  biography-verification's unique links reproduced, 0 differ). Of 23,460 linkable rows: Taqrib one 6,056, several
  289; Tahdhib one 4,657, several 166; none in either 16,773. 866 placeholder rows never link. Lexicon rows never
  link to Imami works (name alone across traditions).
- **Imami** (Najashi, Tusi x2, Kashshi only). Name bases: `exact_full_name`, `nasab_prefix_and_tokens`,
  `short_name_in_headword` (one ism, a kunya alone, ابن فلان: only at its place in the headword and only with
  corroboration). Corroboration: `tusi_section_imam_is_imam_narrated_from` (the Imam right after the name in the
  chains), `..._is_chain_head_imam` (weaker), `entry_imam_is_...` (Najashi's روى عن), `entry_teacher_is_chain_teacher`,
  `entry_student_is_chain_student`. Ranked by summed weight; ties share a rank; nothing picked.

| | Names | one candidate | several | none | Occurrences: one / several / none |
| --- | ---: | ---: | ---: | ---: | --- |
| Riwayat Shi'i labels | 7,030 | 848 | 1,373 | 4,809 | 9,894 / 106,661 / 35,608 of 152,163 mentions |
| Our Imami chain names (keys; 20,506 normalized surfaces) | 19,142 | 1,082 | 1,508 | 16,552 | 10,805 / 80,697 / 78,031 of 169,533 mentions |

Skipped and counted: collective/relational names, Imam names, short names without corroboration (395 / 623),
short names with more than 300 homonyms.

## Sample judgement (`output/sample_60_judgements.csv`, read against the Arabic; not a reviewer decision)

| Set (stratum) | right | plausible | wrong |
| --- | ---: | ---: | ---: |
| lexicon, one candidate (10) | 9 | 1 | 0 |
| lexicon, several (10) | 0 | 10 | 0 |
| Imami, one candidate (20) | 15 | 5 | 0 |
| Imami, several (20) | 8 | 5 | 7 |

Every wrong row is a bare common name (أبان, سعيد, هشام, جابر, محمد بن يحيى, محمد بن الحسن, سليمان بن داود)
where the candidate set is right to be large but the top-ranked entry is not the usual referent: the rank is a
reading aid, never a choice. `output/review_worksheet_150.csv` is the blank 150-row worksheet (same strata).

## Perspectives matrix, timelines, events, availability

- `rijal_perspective_cells.jsonl.gz` (213,883): one row per (perspective, aspect, value): `perspective_id`
  (`perspective:<work>` or `perspective:mizzi_tahdhib_kamal:quoted:<critic>`), `tradition`, `aspect` in
  verdict_term, reliability_qualifier, generation_or_imam, death_date, places, teachers, students, books,
  doctrinal_or_other_note; `verbatim_ar`, `normalised`, flags, locator, citation. An absent pair = silent source.
- `rijal_timeline_facts.jsonl.gz` (16,022): died 9,118, born 1,171, resided 2,064, travelled/arrived 1,449,
  held office 704, present at an event 794, regnal dating 722; per perspective, never merged. Places: 3,194 mapped,
  1,339 written but unmapped. `gazetteer_proposed.json` (63 places, `proposed_unreviewed`; `عمان` left out: Oman
  and Amman are written alike).
- `narrator_event_candidates.jsonl.gz` (634): the entry names the event; 196 carry the history lane's event
  title/key (`history/claims_spec.py`, hash recorded); the rest keep the event as written. Never inferred from dates.
- `biography_availability.jsonl.gz` (50,498): per narrator, each source with `link_state`
  (`lexicon_row_itself`, `dataset_record_itself`, `unique_machine_link_unreviewed`,
  `possible_entry_link_not_established`) and what it covers. Lexicon: several sources 9,532, lexicon only 14,794.
  Riwayat labels: several 124, one 1,355, nothing 5,551 (1,436 with possible entries). Our Imami chain names: one
  964, nothing 18,178 (1,584 with possible entries). By generation in `rijal_coverage.json`.
- `render_narrator_matrix.py` renders the page shape; `output/examples/` holds `علي بن ظبيان` (25195) and
  `أبان بن تغلب` (20577 + the Imami chain name), the second showing Ibn Hajar's `ثقة تكلم فيه للتشيع` beside
  al-Tusi's `ثقة، جليل القدر، عظيم المنزلة في أصحابنا`.

## Citations (`validate_citations.py`, `output/citation_validation.json`)

Every record carries one citation: work (author, title, tradition), edition as the OpenITI header names it, locator
(volume, page, entry number; unnumbered entries say `unnumbered entry (file line N)`), verbatim passage, character
span in the source file (code points; the files are LF-only), `RIJ`, licence, source file and SHA-256. The validator
re-reads each span: **313,681 cited and verified, 0 failures; 69,948 `not_yet_cited` with a reason**: 50,498
availability index records and 19,142 chain-name records (not rijal passages by nature), 166 cells and 140 timeline
facts whose extracted value is not a contiguous run of the source, and 2 empty entries.

## Load specification (for the schema owner; nothing here edits `src/` or `drizzle/`)

Pipeline tables, one writer (the loader), ids as emitted:

1. `rijal_authors (id 'rijal_author:<key>', name_en, name_ar, tradition_id, death_year_hijri null-able, death_note)`.
2. `rijal_works (id 'rijal_work:<key>', author_id, selector_author_id null, bibliographic_work_id -> bibliographic_works,
   tradition_id, title_en, title_ar, verdict_scheme, openiti_uri, edition jsonb, licence, required_attribution,
   source_sha256)`; each also gets a `bibliographic_works` + `editions` row (`rights_status` per the register).
3. `rijal_entries (id 'rijal_entry:<work>:<number>', work_id, entry_number, volume, page, pages text[], headword_ar,
   headword_keys text[], passage_ar, passage_sha256, source_span int4range, extracted jsonb, citation_id)`; one
   `citations` row per entry (work, edition, volume, page, locator = entry number, quote_ar = passage).
4. `rijal_entry_statements (id 'rijal_statement:…', entry_id, scheme, term_id, term_verbatim, clause_verbatim,
   speaker_verbatim, flags text[], is_verdict_on_subject, citation jsonb)`.
5. `rijal_perspective_cells` and `rijal_timeline_facts` as emitted (keys `cell_id`, `timeline_fact_id`), plus
   `rijal_event_candidates` (`candidate_id`, `history_event_ref` resolved to `historical_events.id` once the history
   lane publishes ids).
6. `rijal_entry_link_candidates (id 'rijal_link:<set>:<name>:<entry>', entry_id, link_set in
   ('lexicon','riwayat','imami_chain_name'), narrator_id null-able, external_ref, name_as_written, name_basis,
   evidence jsonb, evidence_score, rank, candidate_count, review_state default 'candidate_only')`. Only a reviewer
   promotes a candidate (a curation table `rijal_entry_link_decisions`), never the loader.
7. `narrator_assessments`: one `critic_ruling` per (reviewed or unique link, statement with `is_verdict_on_subject`):
   `tradition_id` = the work's tradition, `critic` = the author or the quoted critic "as quoted by al-Mizzi",
   `quote_ar` = term as written, `citation_id` = the entry's citation, `status 'proposed'`. `narrator_verdict` has
   no Imami terms, so add `verdict_term_id text` and `verdict_scheme text` and keep `verdict = 'not_applicable'`
   until a reviewed mapping exists; `narrator_assessment_candidates.jsonl.gz` is this projection for Taqrib.
8. Imami narrators: `narrator_authority = 'imami_rijal'` rows only after a reviewer accepts an entry for a chain name.

**Narrator page.** A matrix: rows are perspectives grouped by tradition in alphabetical order (Ibadi, Imami, Sunni,
Zaydi), then the lexicon and datasets; columns are the aspects; each cell the verbatim Arabic with its locator and a
RIJ credit link; an empty cell says the source is silent; candidate rows carry "possible entry, link not
established" and stay visible. Below it, one timeline row per perspective. Above both, the availability line ("no
biography is available in any source the archive holds" when the class is `nothing`).

## Not done, and why

- Kashshi timelines: its reports speak of many people; extracting dated facts would attach them to the wrong man.
- Kashshi and Najashi teachers named inside narratives, Tusi Fihrist footnotes: the OpenITI Fihrist keeps editor
  footnotes inline (`كما في رجال النجاشي`), and some extracted names are footnote text; flagged by low agreement only.
- Mizzi speakers: `وقال في موضع آخر` becomes its own perspective instead of the previous speaker's.
- Regnal datings are never turned into years (needs the history lane's cited reigns); `في خلافة أبي جعفر` keeps one
  token of the ruler.
- No cross-tradition identity: أبان بن تغلب in Taqrib and in Najashi/Tusi are shown side by side for the same written
  name, never merged by the machine.
- Lexicon names with an inner alternative (`عاصم بن بهدلة / بن أبي النجود`) find no entry under the conservative key.
- Source-side defects: the OpenITI Najashi/Fihrist carry OCR artefacts (`أآلهتنا` for `س`), kept verbatim.
