# source-identity (diagnostic only)

What the hadith-kg and Riwayat sidecars (`reconciled/README.md` §External sources) add to the identity of our chain
names, and how the three id sources (K6, hadith-kg, Riwayat) agree. Every row here is unreviewed; a source id is that
source's claim. Nothing here changes a canonical asset or the projection.

## Licence of these outputs

Derived from hadith-kg (**CC BY 4.0**: "hadith-kg (الجامع — Hadith Knowledge Graph) by emadjumaah,
https://huggingface.co/datasets/emadjumaah/hadith-kg, revision 8ae7e3d5"; changed: re-keyed to this project's reports
and mentions, unreviewed) and the Riwayat corpus (**CC0 1.0** for its own layer; cite Abdullah Ansar, v1, Zenodo 2026,
doi:10.5281/zenodo.23630501). Riwayat ids inherited from hadith-kg carry hadith-kg's CC BY 4.0; ids inherited from
Thaqalayn's annotation carry Thaqalayn's CC BY 4.0 ("Credit Thaqalayn (Stichting Thaqalayn) … indicate any changes";
`docs/rights/rights-register.md` §4).

## Command (repo root, after the two reconciled builds; about 1 minute)

```
python -B datasets/hadith-data/diagnostics/source-identity/measure_source_identity.py
```

Inputs (hashed in the JSON header): the six reconciled external sidecars, the projection's `chain_mentions.csv` and
`chain_mention_candidates.csv`, the corpus. "Unidentified today" = a projection mention with no candidate of any basis
(the 174,678 Sunni and 175,057 Imami/Ibadi/Zaydi names).

## Files

| File | Rows | Contents |
| --- | ---: | --- |
| `source_identity_measurements.json` | | Everything below, plus per-work gains, gains by report agreement class (claim counts), agreement examples, the Riwayat Imami registry profile with duplicate-name examples, Qur'an coverage, the judgement summary |
| `imami_sample_60.csv` | 60 | Imami mentions with a Riwayat claim, chosen by SHA-256 rank (stable across rebuilds): our surface with its student and teacher, Riwayat's narrator id, name and other forms, `id_method`, origin, basis, agreement |
| `imami_sample_60_judgement.csv` | 60 | My reading of each row against the Arabic: `right` / `plausible` / `wrong` with a note. A machine reading, not a reviewer decision |
| `review_worksheet_150.csv` | 150 | Stratified by tradition, dataset and confirmed/unconfirmed: Sunni hadith-kg 20 confirmed + 15 unconfirmed, Sunni Riwayat 15 + 10, Imami Riwayat 30 + 31, Ibadi 8 + 7, Zaydi 8 + 6 (all that exist; the shortfall goes to Imami unconfirmed). Blank `reviewer_judgement`, `reviewer_note`, `reviewer`, `reviewed_on` |

## Results (2026-11-21)

### Mentions unidentified today that gain a source claim

| Tradition | Mentions | Unidentified today | Gain any claim | Confirmed by text | Unconfirmed only |
| --- | ---: | ---: | ---: | ---: | ---: |
| Sunni | 363,456 | 174,678 | **51,369 (29.4 %)** | 24,021 | 27,348 |
| Imami | 169,536 | 169,536 | **61,298 (36.2 %)** | 15,606 | 45,692 |
| Ibadi | 2,402 | 2,402 | **877 (36.5 %)** | 697 | 180 |
| Zaydi | 3,119 | 3,119 | 8 (0.3 %) | 0 | 8 |

- **By dataset** (unidentified mentions; a mention can have both): Sunni hadith-kg 42,048 (10,644 confirmed),
  Riwayat 41,405 (22,743 confirmed), both 32,084. Imami: Riwayat only (hadith-kg has no Imami work). Ibadi: both
  (Musnad al-Rabi' is in hadith-kg and inherited by Riwayat).
- **By work**, gain among unidentified: Sunni Ibn Majah 61.5 %, al-Nasa'i 58.6, Abu Dawud 43.2, Bukhari 36.8, Tirmidhi
  34.8, Muslim 26.6, Ahmad 25.0 (25,064 mentions, the largest absolute gain), Darimi 19.9, Muwatta 14.4; Shafi'i has no
  chains. Imami al-Kafi 49.4 % (43,756 mentions, 14,497 confirmed), Kamil al-Ziyarat 60.6, Kitab al-Zuhd 63.3, Amali
  Mufid 38.8, Ghayba Tusi 35.8, Mu'jam 29.3, Ghayba Nu'mani 25.1, Faqih 22.7, Ma'ani 18.1, Thawab 17.2, Amali Saduq
  16.3, Khisal 15.1, Tawhid 12.9, Uyun 10.7; Kamal al-Din, Risalat al-Huquq and Sahifat al-Rida have no Riwayat
  counterpart; Nahj al-Balagha has 2 Riwayat rows.
- **Who asserted the Imami ids** (claims): Thaqalayn's own annotation carried by Riwayat 52,861 (15,245 confirmed),
  Riwayat's automatic linking 8,425 (361 confirmed), Riwayat manual gold 12. Sunni: 156,009 upstream (hadith-kg's
  annotation), 1,063 automatic.
- **Why Zaydi gains nothing.** Only 62 of 698 reports match hadith-kg's Musnad Zayd by our matn and 13 Riwayat
  (different editions), and hadith-kg has no `sanads` for 55 of those 62.

### Reports with every name carrying a source claim

| Tradition | Reports with a chain | Every name has a K6 claim today | Every name has a K6 or external claim | Every name has a confirmed claim |
| --- | ---: | ---: | ---: | ---: |
| Sunni | 62,006 | 12,886 | **25,806** | 18,162 |
| Imami | 29,699 | 0 | **2,704** | 2,024 |
| Ibadi | 964 | 0 | **328** | 271 |
| Zaydi | 689 | 0 | 0 | 0 |

"Confirmed" counts a K6 `source_index_confirmed_by_text` or an external `_confirmed_by_text` claim. The Imami
number is low because Riwayat's chains usually end in an Imam written as a kunya (`أبي عبد الله`), which is carried
but flagged kunya-only, and because single-token Thaqalayn labels (`حماد`, `أبان`, 17,875 Imami mentions) are dropped
under the placeholder rule.

### Three-way agreement on Sunni mentions (the independent check)

The ids live in different key spaces, so agreement is measured without any name link: for every mention that two
sources both claim, a pairing (K6 lexicon id, external id) "agrees" when each is the other's most frequent partner
over all co-claimed mentions (mutual dominant pairing). A year-based lexicon link is a second, independent check.

| | Co-claimed mentions | Mutual pairing | Both confirmed by text: mutual | Via a name+death-year link: same / different |
| --- | ---: | ---: | ---: | ---: |
| K6 vs hadith-kg | 96,331 | **90,295 (93.7 %)** | 19,855 of 20,972 (94.7 %) | 11,134 / 1,246 (89.9 %) |
| K6 vs Riwayat | 108,121 | **100,565 (93.0 %)** | 41,565 of 44,140 (94.2 %) | 35,825 / 2,093 (94.5 %) |
| hadith-kg vs Riwayat (Riwayat's own `kg` crosswalk) | 130,894 | **129,732 same (99.1 %)**, 1,155 different, 7 no crosswalk | | |

- 545 of 3,237 hadith-kg narrators co-occur with more than one K6 id (657 of 3,455 for Riwayat). Part of that is the
  lexicon's own duplicates; the rest are real disagreements.
- **K6 and hadith-kg are independent** (muslimscholars-derived ids vs hadithdb 2017); 93.7 % agreement between them is
  the strongest evidence here. **Riwayat's Sunni ids are not independent of hadith-kg**: 130,638 of 130,894
  co-claimed Riwayat ids are `source_annotation_kg`, so the 99.1 % is a consistency check of Riwayat's re-keying, not
  corroboration. Its 1,155 differences are mostly Riwayat position shifts.
- Links whose basis used K6 positions (4,306 hadith-kg, 22,007 Riwayat mentions) are excluded from the year-link
  column, because using them would be circular.

**The metric is a floor, not an exact rate.** A pairing counts as "not mutual" whenever either id is more often
paired with someone else. That catches real conflicts, but also cases where both sources are right and one of them
is noisy elsewhere (`أبو اليمان` below), and cases where K6 used a duplicate lexicon row.

Disagreement examples (`agreement_examples`, chosen by SHA-256 rank so they are stable across rebuilds):

| Mention | Surface | K6 says | External says | Reading |
| --- | --- | --- | --- | --- |
| `mention:k6:28255:0000:0004` | قيس بن أبي غرزة | 11046 قيس بن أبي حازم (confirmed) | hadith-kg 6509 قيس بن أبي غرزة | **K6 is wrong**, and was confirmed by text only through the shared `قيس بن أبي` tokens |
| `mention:k6:22228:0001:0001` | سفيان | 20012 سفيان الثوري (confirmed) | hadith-kg 3443 سفيان بن عيينة (confirmed) | the classic Sufyan ambiguity; both sources commit, both confirmed: shown as contested |
| `mention:k6:222:0000:0000` | خالد | 20423 خالد الطحان (confirmed) | hadith-kg 2680 خالد بن مخلد (confirmed) | real conflict on a bare ism |
| `mention:k6:29504:0000:0001` | أبو داود | 30002 أبو داود السجستاني | hadith-kg 3585 سليمان بن داود بن الجارود (al-Tayalisi) | a transmitter inside the chain, so al-Tayalisi; K6 points to the compiler |
| `mention:k6:5051:0000:0000` | حفص بن عمر الحوضي | 34062 حفص بن عمر أبو عمر | hadith-kg 2438 حفص بن عمر بن الحارث (usual K6 partner 30329, same man) | a lexicon duplicate, not a disagreement |
| `mention:k6:1074:0000:0000` | أبو اليمان | 30330 الحكم بن نافع (confirmed) | Riwayat N0000006 حكم بن نافع (confirmed) | **same man**: counted "not mutual" because Riwayat's id is often paired with Shu'ayb |
| `mention:k6:17461:0000:0000` | عبدة بن سليمان المروزي | 38365 عبدة بن سليمان المروزي | Riwayat N0000646, usually عبدة بن سليمان الكلابي | Riwayat conflates two Abdas |
| `mention:k6:5500:0000:0001` | غندر | 20278 محمد بن جعفر غندر (confirmed) | Riwayat N0000851 محمد بن جعفر, usually Ibn Abi Kathir | Riwayat's record spans namesakes |
| `mention:k6:28826:0001:0002` (hadith-kg vs Riwayat) | شعبة | | hadith-kg شعبة بن الحجاج; Riwayat يحيى بن سعيد القطان | Riwayat shifted a position |
| `mention:k6:14337:0001:0006` (hadith-kg vs Riwayat) | علي | | hadith-kg علي بن أبي طالب; Riwayat محمد بن جعفر | Riwayat shifted a position |

### Riwayat as an Imami narrator registry

7,030 Riwayat narrators carry an asserted id in a Shi'i chain (6,024 labelled `shia`, 953 `sunni_or_unknown`, 53
`sunni`; 6,151 narrators are labelled `shia` in all).

- **Names are Thaqalayn's labels.** 4,150 take their name from Thaqalayn (`thq`), 1,926 were created by Riwayat
  from a full name in a chain (`chains_new`), the rest from Itqan, SemanticHadith or hadith-kg. A Thaqalayn name is
  the surface as written in a chain (`ابْنِ مَحْبُوبٍ`, `أَحْمَدَ بْنِ مُحَمَّدٍ`), so an id identifies a label
  more often than a person, and agreement between our surface and that name is weak evidence.
- **Name shapes**: 5,440 have a nasab (`بن`), 809 start with a kunya; token counts 1: 309, 2: 608, 3: 2,148, 4:
  1,623, 5: 1,008, 6+: 1,333. Placeholders: 306 bare single token, 122 kunya-only (the Imams among them: `أبي عبد الله
  ع` alone has 11,928 mentions), 78 collective (`عدة من أصحابنا`), 30 relational (`أبيه`), 1 nameless. By mentions:
  125,909 person-like, 17,875 single-token, 7,878 kunya-only.
- **Biography is almost absent**: 860 have any field. Death year 649, tabaqa 806, birth year 200, city 366, death
  city 231, madhhab 152, tribe nisba 658, family 417 (mostly narrators shared with Sunni chains).
- **Crosswalks**: 4,174 Thaqalayn ids (2 narrators with two), 876 hadith-kg, 810 Itqan. 47 carry a Riwayat quality
  flag.
- **Duplicates**: 129 normalized names are held by 285 ids. Examples: `علي بن إبراهيم`, 7 ids (5,522 mentions on one,
  the others 1-5 with a leading tatweel `ـ` artefact, 16 such names); `محمد بن يحيى`, 6 ids; `أحمد بن محمد`, 5
  ids; and Riwayat-created duplicates of the Imams with different blessing formulas. Records that merge different men
  are visible in the forms (`أحمد بن محمد بن عيسى` also carries `أبو بكر الحمصي`).
- **Lexicon links**: 225 of the 7,030 link to a lexicon row, all by Sunni-context evidence. That is expected: the
  lexicon has almost no Imami narrators, and nothing links on name alone.
- Overlap with al-Najashi and al-Tusi was measured before (`diagnostics/biography-verification/` §Imami): exactly one
  headword for 734 Riwayat Shi'i narrators.

### Imami sample: 60 mentions read against the Arabic (`imami_sample_60_judgement.csv`)

**51 plainly right, 8 plausible, 1 wrong.**

- *Plausible* (8): Thaqalayn's single id for an ambiguous label that the id does not resolve (`علي بن محمد` twice,
  `أحمد بن محمد`, `ابن فضال`, `محمد بن قيس`), the kunyas `أبي بصير` and `أبي أيوب`, and one record Riwayat created
  from the surface itself.
- *Wrong* (1): `أبو الحسن أحمد بن محمد بن الحسن` in al-Mufid's *Amali* is Ibn al-Walid's son (from his father);
  Riwayat's `matn_chain_extracted` id is Ibn Miqsam al-Muqri', another man.
- By origin: 52 Thaqalayn-annotation rows (45 right, 7 plausible, 0 wrong); 8 Riwayat automatic-linking rows (6
  right, 1 plausible, 1 wrong). By basis: 14 `source_riwayat_confirmed_by_text` (11 right, 3 plausible: the labels `أحمد بن
  محمد`, `ابن فضال`, `علي بن محمد`; text confirmation cannot fix a label-level id), 46 unconfirmed (40 / 5 / 1).
- An earlier random draw of 60 (before the kunya-abbreviation fix; superseded and not kept as a file) read 50 right, 6
  plausible, 4 wrong, and all 4 wrong were automatic links. Examples: `ranker` gave the Imami `ابن بكير` (Abd Allah b.
  Bukayr, from Zurara) the Sunni Egyptian Yahya b. Bukayr; `joint_unique` gave `محمد بن عبد الرحمن النهدي` Abu Khalifa
  al-Fadl b. al-Hubab. That alignment passed only through the weak `ism_nasab_core_agrees` tier, whose subsequence
  test finds `محمد بن عبد الرحمن` inside Abu Khalifa's long nasab.
- Reading: Thaqalayn's own annotation is reliable at the level of the label; Riwayat's automatic linking is where the
  errors are. Hence the load proposal: `riwayat_automatic_linking` claims never verify.

### Qur'an quotations (`reconciled/hadith_kg_quran_citations.jsonl.gz`)

1,615 hadith-kg quotation spans fall in our matched reports. **1,197 are re-located exactly** in our Arabic (896 in
whole-text matches, 301 in matn-contained matches), in 1,032 reports (1,026 Sunni, 3 Ibadi, 3 Zaydi): Bukhari 345,
Muslim 189, Tirmidhi 188, Abu Dawud 160, Nasa'i 131, Ahmad 77, Ibn Majah 76, Darimi 13, Muwatta 11, Rabi' 4, Zayd 3.
1,194 carry hadith-kg's verse reference, all 114-name sura labels recognised. Not re-located: 264 absent from our text
(our matn is only part of their report), 106 repeated in our text, 48 under 10 letters. A first build found only 604
spans: hadith-kg's inline labels (`سورة العلق آية 1-3`) had kept every verse-quoting report from matching whole-text,
and the crosswalk now strips them.

## What was not done, and why

- **No Imami biography, verdict or tabaqa**: Riwayat has almost none for Imami narrators (860 of 7,030 with any field).
  An Imami authority needs Najashi/Tusi curation; `imami_rijal` stays reserved for that.
- **No lexicon link for Imami-only narrators**, by design (no name-only links, no cross-tradition links).
- **hadith-kg's name check is strict.** `rawis` has no kunya or laqab field, so `غندر`, `أبي الزبير` and `أبو بكر بن أبي
  شيبة` cannot be confirmed against hadith-kg even when the id is right. Its `same_length_name_mismatch` count
  (10,126) is larger than its `full_agreement` count (7,147). Borrowing Riwayat's kunya forms would mix sources and was
  not done.
- **Relational positions** (`عن أبيه`) are never corroborated: neither dataset gives parent links in our key space.
- Zaydi: see above. Nahj al-Balagha: Riwayat has 2 rows.
- The 150-row worksheet is drawn but not reviewed.
