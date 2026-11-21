# history: cited events, eras and narrator involvement (candidates)

Load-ready candidate files that make the history layer citable and balanced across the four traditions. Every row
carries one complete citation (work, edition as its OpenITI header names it, locator, verbatim Arabic passage with its
character span, source SHA-256, licence) and an AI-review record. Each source's account of an event is its own claim;
competing dates are kept side by side, never merged. Nothing here edits the seed, `src/**`, `drizzle/**` or the database.

## Commands (repo root; standard library only)

```
python -B datasets/hadith-data/history/fetch_sources.py --verify        # checksums of the downloaded texts (no network)
python -B datasets/hadith-data/history/build_history_candidates.py      # ~10 s, deterministic (byte-identical reruns)
python -B datasets/hadith-data/history/validate_citations.py            # pre-load validator; exit 1 on any failure
python -B datasets/hadith-data/history/sample_for_judgement.py          # writes output/sample_50_judged.csv
```

`fetch_sources.py` without `--verify` downloads any missing text from GitHub, pinned to a commit, with client identity
`generic-client/1.0` and nothing else sent.

## Inputs (SHA-256)

| Input | SHA-256 |
| --- | --- |
| `src/scripts/db/seed-history.ts` (54 events, 32 places, 38 eras; read as text) | `279749da758cfcdd2c26babec10c64293d7afe91ac05c8dda490beb05516a4cc` |
| `diagnostics/biography-verification/lexicon_rijal_links.jsonl.gz` (Taqrib entry to lexicon row, unique links only) | `56cad0c9d003a479ae986b77a0681221c2251c630ee939484c0a2b563e5a122a` |
| OpenITI `0852IbnHajarCasqalani.TaqribTahdhib.JK000121-ara1` (already on disk) | `178d493bd150032bc64a81ed4397d7e4a828209ee690deed283c1e63cada4637` |
| OpenITI `0240IbnKhayyatCusfuri.Tarikh.JK000412-ara1` | `2f6bb2a4012eef27307c5ba244205d4391445f4928a1a71c92bb4368b2c89c2f` |
| OpenITI `0310Tabari.Tarikh.Shamela0009783BK1-ara1` | `bcf92c29492a25317b64b3af7df00e498a3d6e5fefadff490c01c6e7690c92fd` |
| OpenITI `0911Suyuti.TarikhKhulafa.Shamela0011997-ara1` | `cb64ba4de9a6b4d9d0659dc582d07d61a3f4617177f33201ee948ddb0620ff11` |
| OpenITI `0911Suyuti.TabaqatHuffaz.JK000753-ara1` | `7151039d775463dd498a803de7ff586ceaacf2ac7284ef02ce042cfd209dfe08` |
| OpenITI `0413ShaykhMufid.Irshad.Shia001294Vols-ara1` | `8d54fefec481d38e3b0937360a6b31a91e23b5605285faec31bfd233dbdcfd70` |
| OpenITI `0460ShaykhTusi.Ghayba.Zaydiyya0000283-ara1` | `84a0ed1850ccae6e00efdc522241c7aa35d7bb71c1b0159894b26c27860335c8` |
| OpenITI `0424AbuTalibYahyaHaruni.IfadaFiTarikhAimma.Zaydiyya0000088-ara1` | `c2fc1cd797ae096b1060762fa9a8acdce22b8cf269f062ec21a35aafefbaa6dd` |
| OpenITI `0362AbuFarajIsbahani.MaqatilTalibiyyin.Shamela0012404-ara1` | `c75803177016ae6b55428e82dce74ce48bc2c625ef351462ee9b9b8733c82a08` |
| OpenITI `0670AhmadDarjini.TabaqatMashayikhBiMaghrib.ShamIbadiyya0000107-ara1` | `1c4b6a9c3cd00cfc3c1d23b70ca3d83be7b4a2a4e3c01c85c58f8d159f8117e2` |
| OpenITI `0928AbuCabbasShammakhi.Siyar.ShamIbadiyya0000115-ara1` | `dbe665ca840f2df2e64dbc7ef2be15f6e89ae7474b6fead28c0412fbf54ffc63` |
| OpenITI `1332NurDinSalimi.TuhfatAcyan.ShamIbadiyya0000281-ara1` | `311a6a95f283ca5a3df5f533a5b96539be701c9ff35834dc63f8fe560d65d2a9` |

`output/summary.json` repeats these hashes from the run that produced it.

## Sources fetched (2026-11-21) and licences

All from OpenITI's public GitHub repositories, each pinned to a commit; URL, commit, bytes and SHA-256 are in each
directory's README under `datasets/sources/external/<name>/` and in `sources_manifest.json`. Total 25.4 MB. Licence:
**CC BY-NC-SA 4.0** (OpenITI release 2025.1.9, Zenodo 10.5281/zenodo.17767721): attribution to OpenITI and the upstream
library, non-commercial use only, derivatives (these outputs included) under the same licence.

| Directory | Work | Tradition of the work's author | Use |
| --- | --- | --- | --- |
| `openiti-0240KhalifaIbnKhayyat.Tarikh` | Khalifa b. Khayyat, *Tarikh* | Sunni | Annals to 232: prophetic, caliphal, Umayyad, early Abbasid dates; Talib al-Haqq |
| `openiti-0310Tabari.Tarikh` | al-Tabari, *Tarikh al-Rusul wa-al-Muluk* | Sunni | Annals to 302: Kaba fire 64, al-Andalus 92, Baghdad 145, Mihna 218, Zaydi risings |
| `openiti-0911Suyuti.TarikhKhulafa` | al-Suyuti, *Tarikh al-Khulafa* | Sunni | Abbasid accessions and deaths, Buyid and Seljuk entry, Mongol conquest |
| `openiti-0911Suyuti.TabaqatHuffaz` | al-Suyuti, *Tabaqat al-Huffaz* | Sunni | Full-year deaths of the compilers and later scholars |
| `openiti-0413ShaykhMufid.Irshad` | al-Mufid, *al-Irshad* | Imami | Births and deaths of the Imams |
| `openiti-0460ShaykhTusi.Ghayba` | al-Tusi, *Kitab al-Ghayba* | Imami | The fourth deputy's death, 329 |
| `openiti-0424AbuTalibHaruni.IfadaFiTarikhAimma` | Abu Talib al-Haruni, *al-Ifada* | Zaydi | Zayd b. Ali, al-Hadi, al-Nasir al-Utrush |
| `openiti-0353AbuCabbasHasani.Masabih` | Abu al-Abbas al-Hasani, *al-Masabih* | Zaydi | Fetched; no claim adopted yet |
| `openiti-0362AbuFarajIsbahani.MaqatilTalibiyyin` | Abu al-Faraj al-Isfahani, *Maqatil al-Talibiyyin* | not assigned | Zayd b. Ali's death (121) |
| `openiti-0670AhmadDarjini.TabaqatMashayikh` | al-Darjini, *Tabaqat al-Mashayikh* | Ibadi | Abu al-Khattab, the Rustamids of Tahert |
| `openiti-0928Shammakhi.Siyar` | al-Shammakhi, *Kitab al-Siyar* | Ibadi | Abu al-Khattab's oath, 140 |
| `openiti-1332Salimi.TuhfatAcyan` | al-Salimi, *Tuhfat al-Ayan* | Ibadi | The Omani imamates |

**Not fetched or not found, listed for the owner:** Ibn al-Saghir's chronicle of the Rustamid imams (not found in the
OpenITI repositories checked); a full *Sira* of al-Hadi ila al-Haqq (only a fragment, `MinSiratHadi`, is in OpenITI);
Ibn al-Athir's *al-Kamil* and Ibn Kathir's *al-Bidaya* (the obvious sources for 447, 552, 590 and 656 with written
centuries; large, not fetched in this pass); any source for the end of the Zaydi imamate in 1382/1962 (outside the
premodern corpus). No text was fetched under any licence other than OpenITI's.

## Method

1. **Claims are specified, passages are found.** `claims_spec.py` names, per claim, a work, an anchor phrase and the
   date as the source words it (`stated`). `build_history_candidates.py` finds the anchor in the downloaded text
   (`history_text.py`: markup removed, a letter fold for search only, an offset map back to the file), cuts a verbatim
   sentence window clipped to the section the hit sits in (or the whole rijal entry), and records the page (`PageV`
   marker after the passage), OpenITI line, section heading, annal heading (for annalistic works) and the character and
   byte span in the file. Nothing is typed in by hand except the anchor and the claimed year.
2. **Annals.** Khalifa and al-Tabari date an event by the year heading it sits under (`سنة خمس عشرة`, `ثم دخلت سنة …`);
   such a claim is marked `date_basis: section_heading` and the year is read from that heading.
3. **Years are read from the words.** `year_from_words` parses Arabic year words (units, teens, tens, hundreds); the
   claim passes only if the words give exactly the claimed year. Ibn Hajar's *Taqrib* usually omits the century (his
   introduction gives a rule by tabaqa); such rows are kept, cited, and fail with `century_not_written`.
4. **Each account is its own claim.** Al-Mufid's 95 and Ibn Hajar's 93 for Ali b. al-Husayn's death are two rows with
   two perspectives (`perspective.source_tradition`, `perspective.event_tradition_context`); so are al-Waqidi's 121 and
   Hisham's 122 for Zayd b. Ali in al-Tabari, al-Haruni's 122 and Abu al-Faraj's 121. `competing_years_in_cited_sources`
   lists the others.
5. **Narrator involvement only where an entry states it.** Taqrib entries are scanned for participation or death at a
   named battle (`شهد بدرا`, `قتل يوم الحرة`, `استشهد بالقادسية`, `قتل مع علي بصفين` …). A row is dropped when negated
   (`لم يشهد`), and fails when a kin word precedes it (`أبوه شهد`), when it is reported with `قيل`/`يقال`/`زعم`, when the
   entry rejects it (`ولا يصح`), or when the entry has no unique lexicon link. The nisba `البدري` is not treated as
   participation. Overlapping dates are never used (the app computes overlap at read time).

## How history claims are AI-reviewed

*(Plain-language text for a public page.)*

Dates, eras and events in this archive come from named books. Before a date is shown, a program checks it against the
book it cites. No language model is used; the checks are fixed string and number comparisons anyone can re-run.

A claim is shown as **AI-reviewed, source cited** only when all of these hold:

1. **The citation is complete.** We name the book, its author, the printed edition the digital text was made from, the
   volume and page (or entry number), and we quote the Arabic passage exactly. We also record where in the digital file
   the quotation sits and a fingerprint (SHA-256) of that file, so anyone can find and re-check it.
2. **The passage itself states the date.** The words of the date must appear in the quoted passage, or, in a
   year-by-year chronicle, in the year heading the passage sits under. The year written in those words must equal the
   year we show. If the book gives an age, a duration ("he stayed thirteen years"), a reckoning such as "the Year of the
   Elephant", or leaves out the century, the claim is kept with its citation but **not** shown as reviewed.
3. **Disagreement is shown, not hidden.** When books give different dates for the same event, each book's date is a
   separate claim with its own citation, labelled with the book and its tradition. We never pick one.

What fails, and stays unpublished: a seed date with no passage found; a passage that only paraphrases or implies the
date; a year whose century the source does not write; a narrator's presence at an event that the source reports only
as "it is said", or rejects, or that cannot be tied to one narrator.

AI review is a first check, not a scholar's verdict. Any number of human reviewers may add their own review of any
claim; each review is recorded separately with who made it and when.

## Results (run of 2026-11-21)

**Claims:** 182 date claims, all with a complete citation (182 cited, 0 not yet cited); AI review: **163 passed, 19
failed** (15 century not written, 4 not stated as a year). Narrator-event involvement: 64 rows, all cited; 22 passed, 42
failed (39 no unique narrator link, 5 "it is said", 1 rejected by the source, 1 subject may differ). `validate_citations.py`:
171 citations re-read from their spans, 0 failures.

**Seed events (54):** supported by a cited passage 29; supported with a competing source date 1 (Siege of Makkah:
al-Tabari 64, Khalifa's annal 63); cited source contradicts the seed 2; cited but the date is not a stated year 3; nothing
found 19 (of which 10 are the "compiles/writes/era" rows proposed for splitting below).

| Seed event | Seed | Source | Source date | |
| --- | ---: | --- | ---: | --- |
| Ali becomes Caliph | 35 | Khalifa, annal of 36: `فيها بويع علي` | 36 | contradicted (annal placement; see sample) |
| Uthman becomes Caliph | 23 | Khalifa, annal of 24: `فيها استخلف عثمان` | 24 | differs from the event row; inside the seed era's own 23-24 range |
| Siege of Makkah | 64 | al-Tabari: `احترقت الكعبة يوم السبت لثلاث ليال خلون من شهر ربيع الأول سنة أربع وستين` / Khalifa annal 63 | 64 / 63 | agrees, with a competing account |
| Ibn Majah (death, split row) | 273 | al-Suyuti, *Tabaqat al-Huffaz*: `مات سنة ثلاث وثمانين ومائتين` | 283 | the OpenITI text reads 283; flagged `possible_text_variant` |
| Birth of the Prophet | -53 | Khalifa: `والمجتمع عليه عام الفيل` | Year of the Elephant | cited, not a Hijri year |
| First revelation | -13 | Khalifa: `بعث … وهو ابن أربعين` | age 40 | cited, not a year |
| Fall of Baghdad | 656 | al-Suyuti: `ولما دخلت سنة ست وخمسين` | [6]56 | century not written |

Nothing found on disk for: Battle of the Trench, Battle of Tours, Isra and Miraj, migration to Abyssinia, first and
Uthmanic collection of the Quran, Dome of the Rock, foundation of Basra and of Fustat, and any dated compilation.

**Eras (38):** both boundaries cited and passing for 31. Start: supported 33, contradicted 2 (Caliphate of Ali: 36;
Zaydi imamate in Yemen: al-Haruni dates al-Hadi's oath to **280**, the seed says 284), not a stated year 2, nothing found
1 (Makkan period's start). End: supported 31, competing 1 (first four caliphs: 40 and 41), not a stated year 2 (Buyid end
and Abbasid end: 447 and 656 lack the century in al-Suyuti), nothing found 3 (Seljuk end 552/590, Zaydi Caspian state
316, Zaydi imamate 1382), open-ended 1. Ibadi first imamate in Oman ends 133 in al-Salimi and 134 in Ibn al-Athir as
al-Salimi quotes him: both kept.

**New candidate events (51), by tradition context:** Imami 13 (deaths of the eleven Imams from al-Mufid with Ibn Hajar's
Sunni accounts beside them where he states one, the twelfth Imam's birth in Imami belief, al-Samuri's death), Zaydi 7,
Ibadi 10, Sunni-scholarly 10 (the compilers' and later scholars' deaths that replace the "compiles" rows), general 11.
49 have at least one passing claim. Three examples:

- **Imami**, death of Musa b. Jafar al-Kazim, al-Mufid, *al-Irshad* v2 p215: `وقبض عليه السلام ببغداد في حبس السندي بن شاهك لست خلون من رجب سنة ثلاث وثمانين ومائة، وله يومئذ خمس وخمسون سنة` → 183.
- **Zaydi**, oath to al-Hadi in Yemen, Abu Talib al-Haruni, *al-Ifada* v1 p102: `فخرج عليه السلام إلى هناك، فبايعه أبو العتاهية وعشائره … وذلك سنة ثمانين ومائتين` → 280.
- **Ibadi**, the Rustamid imamate, al-Darjini, *Tabaqat al-Mashayikh* v1 p43: `تاهرت على رأس ستين ومائة ، وذكر بعضهم أنه ولى سنة اثنين وستين ومائة` → 160, some say 162.

**Sample re-read (50 rows: 40 date claims, 10 involvement rows; `output/sample_50_judged.csv`):** right 47, doubtful 3,
wrong 0. Doubtful: the Mihna row dates the Mihna's start, not Ahmad b. Hanbal's own examination; Ali's oath sits under
Khalifa's annal of 36 though he puts Uthman's killing in 35; al-Kazim's death sentence names him only by pronoun. One
wrong row found during an earlier read (the "sixteen years" anchor for al-Bukhari's *Sahih* hit a sentence about his age)
was removed before this sample was drawn, and the nisba `البدري` (which matched `العبدري`) was dropped from the
involvement patterns.

## Seed defects: proposals (the seed script is not edited)

- **"Compiles"/"writes"/"era" rows (10).** Each is paired with a death event carrying its own citations
  (`event_candidates` → `proposal.action = split_compilation_event`). Nine seed years are the author's death year; al-Bukhari's
  232 is neither his death (256 in al-Suyuti) nor a dated compilation. No text on disk dates any compilation, so the
  compilation date is proposed as **unknown**; the seed rows should be retired or retitled once the death events load.
- **"Egypt" (al-Shafii's death, al-Nasai's row).** Proposed place `location:proposed:egypt-misr`, "Egypt (Misr)", a
  region with no coordinates. In these sources *Misr* names the province (Ibn Hajar: al-Shafii `نزيل مصر`); Fustat was its
  capital in this period and Cairo was founded only in 358. Linking either event to Fustat or Cairo would assert a city
  the passage does not state. A curator can add a city link where a source names one.

## Load specification (for the schema owner)

All ids are stable: seed events keep `stableSeedId('historical-event', title, legacy year)` (verified against production),
new events use the same rule over (title, first passing year); citations `cit:history:<hash of uri|span>`; claims
`hclaim:…`; involvement `hinv:…`.

1. **`bibliographic_works` / `editions`** from `output/works_and_editions.json`: `work_id`, `title`, `title_ar`, `author`,
   `author_death_year_hijri`, `openiti_uri`; edition `editor`, `publisher`, `place`, `year`, `locator_scheme`,
   `rights_status = 'pending'` (licence CC BY-NC-SA, non-commercial; owner rights gate). `tradition_id` from
   `tradition_of_author` where it is one of the four; *Maqatil al-Talibiyyin* stays null.
2. **`citations`** from `citations.jsonl.gz`: `id`, `work_id`, `edition_id`, `volume`, `page`, `locator` = `locator_text`,
   `quote_ar`, `retrieved_at` = 2026-11-21, `review_state = 'candidate_only'`. The span, SHA-256 and source file need
   three columns the table lacks (`source_span jsonb`, `source_sha256 text`, `source_file text`) or a side table keyed by
   citation id; run `validate_citations.py` before every load.
3. **`historical_events`** from `event_candidates.jsonl.gz`: seed rows update in place (title, years, `citation_id` of the
   primary passing claim, `citation_source` = its `source_reference`, `citation_locator` = `locator_text`); new rows insert
   with `origin` = a new `history_lane` value (or `ai_research`), `location_id` from the gazetteer. The event row's year is
   the primary account's; every account stays in the claims table.
4. **Claims** (`date_claims.jsonl.gz`) need the planned `temporal_assertions` table (design §5.8): one row per claim with
   `subject_kind` (event | epoch_start | epoch_end), `subject_id`, `year_hijri`, `alternatives`, `month_day`, `stated_ar`,
   `date_basis`, `qualifier`, `attributed_to`, `perspective` (source work, source tradition, event tradition context),
   `citation_id`, and the review fields below. Competing claims are separate rows.
5. **`epochs`** from `epoch_candidates.jsonl.gz`: keep the seed's ranges; set `citation_id` to the first passing start
   claim; where a cited year falls outside the seed range (Ali 36, Zaydi Yemen 280), widen the range or add the boundary
   claim, never overwrite silently.
6. **`narrator_events`** from `narrator_event_candidates.jsonl.gz` (rows with a `narrator_id` and `event_id`; new-event
   rows after those events load): `narrator_id`, `event_id`, `role` (Participant | Killed | Examined), plus `citation_id`
   and the review fields (the link table has no citation column today: add one).
7. **`locations`** from `location_candidates.jsonl.gz`: 32 seed rows (ids kept; coordinates labelled editorial) and 15
   proposals (Egypt (Misr), Tahert, Tripoli, Hadramawt, Oman, Yemen, Khurasan, Tabaristan, Daylam, Tus, Samarra,
   al-Yamama, Maskin, al-Andalus, Iraq) with Arabic forms, `kind`, and `cited_in_citation_ids` (passages naming the place;
   forms marked `ambiguous_forms`, such as `أحد` and `المدينة`, need a reader). Places are shared with narrator records by id.
8. **`event_name_forms.json`**: id, key, Arabic forms (as written and folded) for all 105 events and 38 eras. The rijal
   lane (`datasets/hadith-data/rijal/rijal_extract.py` `EVENTS`) already maps its event mentions to these titles and keys
   (`battle-of-yamama`, `battle-of-al-harra`); its unmapped forms Khaybar, Hunayn, Tabuk and al-Nahrawan now have cited
   events here (`campaign-of-khaybar`, `battle-of-hunayn`, `campaign-of-tabuk`, `battle-of-nahrawan`).

**Review state: two independent fields, not one ladder.**

- `ai_review`: `{rule: 'history-ai-review-v1', procedure, model: null, outcome: passed | failed, checks[], failure_reasons[], passage_checked}`.
  Each check says what was compared and the result, so a reader can see it.
- `human_reviews`: a list, empty today, each `{reviewer_id, reviewed_at, verdict: confirms | disputes | corrects,
  note, corrected_value?}`. Many separate reviewers per item; never a single "the reviewer". This should be the shared
  review table the general review lane designs, keyed by (item kind, item id).

**Publication (owner decision 2026-11-21: AI-reviewed claims publish).** Publish a claim when `citation_status = cited`
and `ai_review.outcome = passed`, labelled "AI-reviewed, source cited" with its citation; publish an event or era when it
has at least one such claim. Under the current schema this means the gate (`verification_status in (human_verified,
source_verified)`) needs a value or a parallel column for AI review; `source_verified` should not be reused, because the
glossary reserves "verified" for a reviewer. What becomes public today: 30 of 54 seed events (29 supported + Siege of
Makkah), 49 new events, 31 eras with both boundaries passing (start-only eras could show an open end), 22 narrator-event
links; everything else stays a cited, unpublished candidate.

**Drawing timelines per perspective.** For one narrator or one chain, draw one row per perspective (a source work, grouped
by its tradition): eras as bands from that perspective's cited boundary claims (a disputed boundary as a gradient over
its range), events as markers at each account's year, the narrator's life span from that perspective's biographical
claims (rijal lane), and involvement links as markers on the narrator's row. Every band, marker and span carries its
`citation_id`; hovering shows the quotation and locator. Rows are never merged: where al-Mufid and Ibn Hajar date the
same death differently, two markers appear on two rows. Overlap between a narrator and an era is computed at read time.

## Files (`output/`)

| File | Rows | Contents |
| --- | ---: | --- |
| `citations.jsonl.gz` | 171 | Complete citations with verbatim passage, span, SHA-256, licence |
| `date_claims.jsonl.gz` | 182 | Event and era-boundary claims, one per account, with AI review and perspective |
| `event_candidates.jsonl.gz` | 105 | 54 seed events (assessment, split proposals) + 51 new events |
| `epoch_candidates.jsonl.gz` | 38 | Per era: cited start and end years and assessment |
| `narrator_event_candidates.jsonl.gz` | 64 | Narrator involvement stated in Taqrib entries (+ al-Tabari's Mihna list) |
| `location_candidates.jsonl.gz` | 47 | Egypt (Misr) proposal, 32 seed places reconciled, 14 further proposals |
| `event_name_forms.json` | 143 | Ids and Arabic name forms of events and eras |
| `works_and_editions.json` | 12 | Work and edition records from the OpenITI headers |
| `summary.json` | | All counts, input hashes, seed dates contradicted |
| `nothing_found.json` | 2 | Exploratory searches that found no dated statement |
| `sample_50_judged.csv` | 50 | Re-read sample with judgements (`sample_judgements.json`) |
| `review_worksheet_150.csv` | 150 | Blank reviewer worksheet: 120 date claims and 30 involvement rows (fixed hash order) |

## Not done

- Tahdhib al-Kamal, al-Najashi, al-Tusi's *Rijal* and *Fihrist*, hadith-kg and Riwayat were not mined for event dates:
  they date people, not events; the rijal lane carries their per-person timelines.
- Offices (appointed judge of a city) are not events in the schema; not proposed.
- *al-Masabih* is fetched but no claim was adopted from it.
