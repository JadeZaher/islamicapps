# quran (Qur'an quotations found directly in every report)

Qur'an quotation spans located in our own stored `text_ar`, each with its verse reference(s), the verbatim Tanzil
verse text and one complete citation block. Sidecars only: nothing here writes a canonical file, and every row is
`review_state: unreviewed`. Qur'an text: Tanzil (`datasets/sources/external/quran-tanzil/`, CC BY 3.0).

## Run (repository root; deterministic, a second build reproduced every output byte)

```
python -B datasets/hadith-data/quran/build_quran_citations.py       # ~40 s, streaming, ~300 MB
python -B datasets/hadith-data/quran/validate_citations.py          # ~30 s, exit 1 on any failure
python -B datasets/hadith-data/quran/validate_against_hadith_kg.py  # ~10 s
python -B datasets/hadith-data/quran/measure_quran_citations.py     # seconds
python -B datasets/hadith-data/quran/draw_review_samples.py         # worksheet (also writes a reading draw; see below)
cd datasets/hadith-data/quran && python -B -m unittest test_quran_logic
```

## Method

Both sides are reduced to a letters-only skeleton for comparison only (stored text untouched). `project_normalize` is
the project's `narrator_normalize` (NFKC, format controls, vocalization, tatweel, alef and ya variants). On top,
`fold_quranic_orthography` (separate, tested): every alef dropped (dagger alef, alif khanjariyya, alef wasla and madda
are written differently in Uthmani and imla'i), hamza and its seats (ء ؤ ئ) dropped, ta marbuta to ta (Uthmani writes
open ta in رحمت), Persian/Urdu shapes to Arabic. Both Tanzil editions are indexed as one letter stream per edition
(suras separated by `#`); a report is matched against each. Seeds are 10-letter k-grams at report word starts; each
occurrence is extended both ways to the maximal exact match, then trimmed so that it starts and ends on a report word
boundary **and** an edition word boundary (this removed half-word endings such as `بم` + `ا`). A span may cross
verses (never suras). All Qur'an places covering the winning interval are kept as candidates (no choosing among
repeated verses). Intervals from the two editions are pooled when identical, the longest wins an overlap. Offsets are
code points of the stored text, widened over silent characters so a span never starts or ends inside a word
(`إ` of `إذا`). Runtime: index 1.5 s, matching ~35 s for 99,283 reports (35.5 M characters).

**Classes** (`classify_span`): `formula` (span contained in a listed formula: basmala, hamdala, tahlil, istirja',
hasbala, `رضي الله عنهم`, `يا أيها الذين آمنوا`, `له الملك وله الحمد…`, ...; any cue); `common_phrase` (no strong cue,
at most 6 words, in 15 or more distinct reports); otherwise by cue and length:

| Cue | words | kind / confidence |
| --- | --- | --- |
| strong (brackets `﴿﴾`/`{}`, ۝, introducer such as قال الله/قوله/تلا/الآية, "سورة X", "الآية" after) | 5+ | citation / high |
| strong | 3-4 | citation / low |
| none | 15+ / 10-14 / 5-9 | citation / high / medium / low |
| none, or strong with 2 words | 4 or fewer | short_phrase (never a citation) |

Basmala, `عيسى بن مريم`, `في سبيل الله`, `رضي الله عنهما` are therefore recorded in `hadith_quran_phrases.jsonl.gz`,
not as citations.

### Choosing the parameters (data, hadith-kg as reference)

Where our spans overlap hadith-kg's markings (33,256 reports with a unique hadith-kg match; 1,274 carry markings),
share of our spans lying inside a hadith-kg quotation (a floor, not precision: hadith-kg marks only 12 % of its own
hadith): cued 5-6 words 91-94 %, cued 7+ words 92-97 %, cued 4 words 43 %, cued 2-3 words 66 %; uncued 4 words 5 %,
5 words 14 %, 6 words 26 %, 7-9 words 45 %, 10-14 words 48 %, 15+ words 70 %. Cues are what separate real quotation
from coincidence below 10 words; hence "4 uncued words is never a citation". The first reading (below) showed 5-9 uncued
words mostly real, so they stay `low` instead of being dropped.

## Validation against hadith-kg (`quran_validation.json`)

- **Recall** of hadith-kg's own quotations (>= 10 letters, locatable in our skeleton, 1,262): found whole 1,206 (95.6 %),
  partly 49, touched 7, missed 2. Another 254 of its quotations cannot be located in our text (its wording differs or
  our text is shorter); 97 are under 10 letters (not seedable). Not investigated further.
- **Its 1,197 already-placed spans** (`reconciled/hadith_kg_quran_citations.jsonl.gz`): 1,100 overlapped >= 90 % by one
  of our spans, 37 by 50-90 %, 27 under 50 %, 33 by none. Best-span class: 855 citation/high, 222 low, 20 medium,
  38 short_phrase, 16 common_phrase, 13 formula. hadith-kg's verse falls inside our candidate set in 1,157 of 1,161
  references with a sura (1,314 of 1,323 on all overlapping quotations).
- Class-level floors: high 92.8 % inside a hadith-kg quotation, low 36.9 %, medium 33.9 %, short_phrase 4.6 %,
  common_phrase 1.4 %, formula 1.7 %. Use hadith-kg agreement as corroboration, not as the truth:
  `quran_span_hadith_kg_agreement.jsonl.gz` gives it per span id.

## Reading of 80 matches (`quran_reading_80.csv`, one reader, not a scholar)

Stratified draw (sha256 ranking), read in full context. Real quotation / allusion or paraphrase / coincidental /
formula or speech:

| Stratum | n | real | other |
| --- | ---: | ---: | --- |
| citation high, cued | 14 | 14 | |
| citation high, uncued | 8 | 7 | 1 narrative paraphrase of 24:8 |
| citation medium | 8 | 7 | 1 Qur'anic wording recited as dhikr (9:129) |
| citation low, cued | 6 | 6 | |
| citation low, uncued | 12 | 11 | 1 coincidental echo of 3:77 in Prophetic speech |
| ambiguous candidates | 6 | 6 | (reference set contains the verse in each; one not verified) |
| short_phrase | 12 | 3 | 8 coincidental, 1 allusion |
| common_phrase | 8 | 0 | 7 coincidental, 1 speech |
| formula | 6 | 0 | 6 honorific or hamdala formulae |

Citation class: 51 of 54 real (94 %), 3 not. Excluded correctly: `رضى الله عنهما` (matches 5:119 and 9:100),
`لله رب العالمين`, `عيسى بن مريم`, `الحمد لله الذي`. Wrong or weak: `يوم القيامة ولا يزكيهم ولهم عذاب أليم` in "ثلاثة لا يكلمهم الله عز وجل..." (an echo of 3:77 in
Prophetic speech; it sits in `citation/low`. In the first pass the same wording was `high` because a bare `عز وجل` was an
introducer; that introducer was removed). Misses: three real short quotations sit in
`short_phrase` (`ولكل جعلنا موالي` is cued 3 words and now low; `أجعل الآلهة إلها واحدا`, `خذ العفو وأمر بالعرف` are
uncued 4 words). A pre-fix first pass found a wrong cross-verse tail (`ولي ولا نصير` + `يا`) and half-word endings;
both were repaired by the edition-boundary trim before this reading. The reading preceded one introducer fix (a
`ف`/`و` before قال الله) that added 66 citations; the 80 ids are unchanged in class. `draw_review_samples.py`
regenerates the worksheet and also a fresh unlabelled 80 draw; delete that file, the labelled reading is kept.
**`quran_review_worksheet_150.csv`**: 150 blank rows (disjoint from the reading), columns `verdict`,
`correct_reference`, `notes`, `reviewer` to fill.

## Results (`quran_measurements.json`)

11,080 citations (high 5,264, medium 1,089, low 4,727; 6,538 reports = 6.59 %; high-or-medium 4,250 reports =
4.28 %), plus 16,262 phrase rows (formula 2,742, common_phrase 6,775, short_phrase 6,745) that are not citations.

| Tradition | Reports | with a citation (any) | high or medium | citation spans |
| --- | ---: | ---: | ---: | ---: |
| Sunni | 64,356 | 3,017 (4.69 %) | 1,990 (3.09 %) | 4,186 |
| Imami | 33,225 | 3,401 (10.24 %) | 2,186 (6.58 %) | 6,656 |
| Ibadi | 1,004 | 74 (7.37 %) | 50 (4.98 %) | 175 |
| Zaydi | 698 | 46 (6.59 %) | 24 (3.44 %) | 63 |

By work (any-citation %): al-Tawhid (Saduq) 31.3, Ma'ani al-Akhbar 24.5, Fada'il al-Shi'a 22.2, Kamal al-Din 19.4,
Ghayba (Nu'mani) 19.4, Amali (Mufid) 16.5, Kafi 10.6; Sunni: Tirmidhi 10.3, Bukhari 9.6, Abu Dawud 5.3, Muslim 5.0,
Nasa'i 4.4, Ibn Majah 3.8, Ahmad 2.9, Darimi 2.9, Muwatta' 2.9, Shafi'i 0.4; Kitab al-Du'afa 0, Nahj 4.0, Faqih 6.1,
Rabi' 7.4, Zayd 6.6 (all works in the JSON). Position: matn 8,063; before the matn boundary 727; whole text is matn
(source ships no isnad) 1,172; no chain detected 313; straddling 42; boundary unknown 763. So quotations are
essentially in the chain-less part; the 727 before the boundary are narrative that precedes the matn, not isnad.
Ambiguity: 712 citations (6.4 %) have several candidate places (2: 486, 3: 94, 4: 44, 5: 32, 6+: 56); 1,106 span
more than one verse. Most-quoted verses (reports, unambiguous high/medium): 3:77 (42), 25:68 (35), 2:158 (34),
4:59 (34), 6:158 (33), 2:187 (31), 31:34 (31), 6:162 (30); 2,074 of 6,236 verses are quoted at least once.

## Files

| File | Rows | Contents |
| --- | ---: | --- |
| `hadith_quran_citations.jsonl.gz` | 11,080 | citations with the complete `citation` block |
| `hadith_quran_phrases.jsonl.gz` | 16,262 | formula / common_phrase / short_phrase spans (same fields, no `citation` block) |
| `quran_verses.jsonl.gz` | 6,236 | `quran_verses` reference rows, both Tanzil texts verbatim |
| `quran_span_hadith_kg_agreement.jsonl.gz` | per span in overlap | agreement with hadith-kg |
| `quran_citations.manifest.json` | | inputs, code and output SHA-256, parameters, editions |
| `quran_validation.json`, `quran_measurements.json`, `quran_citation_validation.json` | | results |
| `quran_reading_80.csv`, `quran_review_worksheet_150.csv` | 80 / 150 | reading with verdicts / blank worksheet |

Output hashes: citations `a224fe61…2f3c`, phrases `fa72bdf6…d7`, verses `a9f208e9…68f4` (full values in the manifest).

## One complete citation per emitted citation (`citation` block) and its validator

`validate_citations.py` checks every row before load: **work** `The Qur'an`; **edition** name and version equal to the
Tanzil file's own header (`Tanzil Quran Text (Simple Clean), version 1.1`); **locators** one per candidate (sura, aya
range, `ref`), ranges valid, nothing dropped; **verbatim** matched Tanzil text present in that edition's verse text and
equal to the span's skeleton; **span** `record_id`, start/end, text reproduced from the stored report, slice hash;
**source** code `TNZ`, short reference, URL, licence (CC BY 3.0 + URL), attribution wording; **hashes** `report_arabic_sha256`
equals the stored text's hash, `quran_file_sha256` equals the file on disk. A span without a verse is never emitted.
Result: **11,080 of 11,080 pass, 0 fail** (`quran_citation_validation.json`).

## Deferred

Cued quotations under 10 letters (`والعصر`, `إنا أعطيناك الكوثر`) cannot be seeded; quotations with an omitted or
substituted word are two spans, not one; the 254 unlocatable hadith-kg quotations and 33 unmatched placed spans are not
yet examined; introducers beyond the listed phrases; per-edition word-segmentation differences can drop a Uthmani-only
match. Revisit when the 150-row worksheet comes back: re-tune the class table from its verdicts.

## Load spec (for the schema owner; nothing here edits `src/`, `drizzle/` or the loader)

**`quran_verses`** (reference, 6,236 rows from `quran_verses.jsonl.gz`): `sura` (1-114), `aya`, `ref` text key
`<sura>:<aya>` primary key, `sura_name_ar`, `text_uthmani`, `text_simple_clean` (verbatim Tanzil), `source_code` `TNZ`.
Static; reload only if the Tanzil version changes.

**`hadith_quran_citations`** (one row per citation span, `id = quran:<record_id>:<start>:<end>`):
`hadith_id` FK, `span_start`, `span_end` (code points of `hadiths.text_ar`, `[start, end)`), `quote_sha256`,
`report_arabic_sha256` (must equal `hadiths.arabic_sha256`, else the row is stale and not shown),
`confidence` enum `high|medium|low`, `primary_cue`, `cues jsonb`, `words`, `candidate_count`, `ambiguous bool`,
`span_report_count`, `basis` enum `text_match|source_hadith_kg` (the 1,197 hadith-kg spans from `reconciled/` load with
`source_hadith_kg`, `source_ref` `hadith-kg:hadith:<id>:<seq>`; where both bases give the same span keep one row with
`corroborated_by_hadith_kg = true`, which may lift a `low` to display), `quran_edition_text_type`/`quran_version`,
`quran_file_sha256`, `review_state` default `unreviewed`, `part` (matn / before_matn / ...).
**`hadith_quran_citation_candidates`** (child, one row per candidate): `citation_id` FK, `sura`, `aya_from`, `aya_to`,
FK to `quran_verses` for `(sura, aya_from)` and `(sura, aya_to)`, `verbatim_quran_text`, `quran_edition_key`.
The ambiguous set is the candidate rows; nothing is chosen. Load checks: `substring(text_ar from start+1 for end-start)`
hashes to `quote_sha256`; `report_arabic_sha256 = hadiths.arabic_sha256`; every candidate verse exists; run
`validate_citations.py` first and abort on any failure. Phrase rows (`hadith_quran_phrases`) are not loaded for display.
**Credit**: `TNZ` in the sources registry (proposal in `datasets/sources/external/quran-tanzil/README.md`); the report page
and `/sources` carry the CC BY 3.0 attribution; hadith-kg's line is added where `source_hadith_kg` applies.

**Report page**: show confidence `high` and `medium` as a quiet inline marker after the span (the superscript reference
`3:77`, linking to `/quran/3/77` or the verse anchor), the span text itself unchanged; a hover/disclosure shows the
verbatim verse and the Tanzil credit; an ambiguous span shows the first candidate with "+n" opening the list; `low`
appears only in a "possible Qur'anic wording" disclosure, never inline. Never alter the report text.
**Browse path**: "Reports quoting this verse" at `/quran/<sura>/<aya>`: the verse (both texts), the reports with an
unambiguous high or medium span covering it (count shown, ambiguous and low listed separately), grouped by tradition,
and the sura index with quoted-verse counts. Indexes: `(sura, aya_from, aya_to)` on candidates, `(hadith_id)` on citations.
