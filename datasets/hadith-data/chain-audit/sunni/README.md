# Sunni isnad ordering and teacher/student audit

Lane output of the Sunni chain audit. Read-only against production (snapshot of **78,189 active chains, 363,456 active mentions, 64,356 hadiths** in the nine Sunni collections; `shafii` has no chains). Nothing outside this directory was written and nothing was written to the database.

## Files

| file | what |
|---|---|
| `detectors.cjs` | the deterministic detectors (pure functions over a snapshot) |
| `load_cache.cjs` | read-only dump of Sunni chains/mentions/narrators/lifespans to a local JSON cache |
| `run_detectors.cjs` | runs every detector, writes `detector_counts.json` |
| `sample.cjs`, `sample.json` | seeded stratified sample (random across collections + detector hits) |
| `online_check.cjs`, `online_check_api.cjs`, `online_results.json` | online re-reading and comparison |
| `manual_review.json` | my overrides after reading each flagged row against its online quote |
| `build_outputs.cjs` | builds `corrections.jsonl`, `sample_check.csv`, `summary.json` |
| `corrections.jsonl` | one row per defect |
| `sample_check.csv` | every sampled chain: our order, online order, agree/disagree, kind, URL, quote |
| `test_detectors.cjs`, `fixtures.json`, `make_fixtures.cjs` | offline test over the confirmed examples |
| `fetched/` | every fetched page, each with URL, UTC timestamp and intent |
| `identity_probe.cjs`, `identity_evidence.json` | editorial-identification probe and the three verified identifications behind `proposed_narrator_id` |
| `make_readme.cjs`, `tables.cjs`, `summary.json`, `detector_counts.json` | README generator and the counts it reads |

Rerun: `node --env-file=.env.local load_cache.cjs <cache>`, `node run_detectors.cjs <cache> <hits>`, `node online_check.cjs <cache> <round>`, `node build_outputs.cjs <cache> <hits>`, `node make_readme.cjs <cache>`, `node test_detectors.cjs`.

## Method

1. **Detectors (A).** Every detector runs over all active Sunni chains. Position 0 is the collector's shaykh; the last position is nearest the Prophet. Text gaps between adjacent surfaces are measured by locating each surface in `hadiths.text_ar` in order, with Arabic-aware boundaries (JS `\b` is ASCII-only, so lookarounds on `[ء-ي]` are used). Lifespans come from `narrator_lifespans` (basis `lexicon_unverified`).
2. **Blame.** A chronology contradiction names two mentions; the culprit is chosen by: contradicts both neighbours; bare relation word; the final mention is a Companion-era person so the other side is suspect; other neighbour supported vs unsupported; weaker (bare/single-token) surface. A fully named student beside a Companion who died more than 120 years earlier is reported as `missing_link`, not a wrong identity.
3. **Online loop (B).** 201 chains in four rounds. Round 1 (55) was read, the disagreements were grouped, and detectors were added or tightened for each new pattern (benign tahwil convergence excluded; formula/aside/verb-in-surface detector; sibling-branch coverage for co-transmitters; relation resolved by nasab; Companion-final blame). Round 2 (59) added aside-in-surface and page-marker handling; round 3 (52) added verb-fused surfaces, Tirmidhi grading formulas and the matn-only Pure Canon alignment; round 4 (35, drawn after those changes) produced no new defect class, only one detector refinement (a restated shaykh written shorter than the stored surface, e.g. «مالك» for «مالك بن أنس», is still a benign convergence), so the loop stopped there.
4. **Online re-reading.** The public opening words of the hadith (or, for the matn-only Pure Canon rows, its matn) are searched in the Turath full-text API; the hit is accepted only if at least 65% of our first 60 words occur in the aligned page slice. The online isnad is parsed independently into routes and names (glosses between hyphens, co-transmitters, «يعني …» asides marked as non-route names), then each stored chain is aligned to it in order. Verdicts: `ok`, `missing_link`, `branch_seam`, `order_reversed`, `not_a_narrator`. Fallback for numbered hadith when Turath was rate limited: the public hadith-api Arabic editions (six collections), with a 75% opening-word overlap guard.
5. Every non-`ok` row, and every random chain carrying a detector flag, was read against its online quote; `manual_review.json` records the overrides (false positives, kinds, unverifiable).

## Detector counts

Counts are hits (mention-level where a mention is blamed, chain- or hadith-level otherwise) per collection:

| detector | total | bukhari | muslim | nasai | tirmidhi | abudawud | ibnmajah | ahmad | darimi | muwatta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `non_name_surface` | 10,248 | 718 | 4,486 | 445 | 601 | 1,099 | 347 | 2,075 | 105 | 372 |
| `gap_has_unstored_words` | 2,841 | 412 | 768 | 427 | 434 | 480 | 320 | 0 | 0 | 0 |
| `length_outlier` | 2,834 | 126 | 1,274 | 42 | 76 | 122 | 27 | 731 | 59 | 377 |
| `bare_relation_resolved` | 2,496 | 632 | 595 | 395 | 274 | 309 | 291 | 0 | 0 | 0 |
| `companion_nonfinal` | 725 | 150 | 93 | 150 | 96 | 92 | 85 | 53 | 3 | 3 |
| `chrono_contradiction` | 604 | 94 | 82 | 103 | 80 | 105 | 140 | 0 | 0 | 0 |
| `seam_in_chain` | 543 | 94 | 301 | 58 | 35 | 25 | 28 | 1 | 0 | 1 |
| `tahwil_marker_vs_chain_count` | 530 | 157 | 149 | 31 | 82 | 40 | 10 | 39 | 4 | 18 |
| `truncated_before_companion` | 474 | 39 | 219 | 39 | 26 | 103 | 41 | 5 | 0 | 2 |
| `surface_name_mismatch` | 431 | 55 | 78 | 33 | 44 | 52 | 74 | 89 | 3 | 3 |
| `repeated_narrator` | 151 | 58 | 5 | 16 | 22 | 10 | 9 | 31 | 0 | 0 |
| `bidirectional_pair` | 111 | 16 | 14 | 23 | 21 | 10 | 17 | 10 | 0 | 0 |
| `prophet_as_mention` | 105 | 18 | 12 | 4 | 5 | 5 | 12 | 48 | 1 | 0 |
| `collector_self_mention` | 81 | 1 | 26 | 14 | 7 | 33 | 0 | 0 | 0 | 0 |
| `co_transmitter_gap` | 60 | 1 | 40 | 12 | 0 | 5 | 1 | 0 | 0 | 1 |
| `text_order_mismatch` | 11 | 7 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 |

Per extraction method of the mention involved (`no identity` = unresolved mention, `chain-level` = not tied to one mention):

| detector | K6 index | hadith-kg | Riwayat | two sources | no identity (null) | chain-level |
|---|---:|---:|---:|---:|---:|---:|
| `non_name_surface` | 322 | 40 | 180 | 32 | 9,674 | 0 |
| `gap_has_unstored_words` | 589 | 17 | 108 | 43 | 2,084 | 0 |
| `length_outlier` | 0 | 0 | 0 | 0 | 0 | 2,834 |
| `bare_relation_resolved` | 2,487 | 0 | 9 | 0 | 0 | 0 |
| `companion_nonfinal` | 538 | 49 | 122 | 16 | 0 | 0 |
| `chrono_contradiction` | 604 | 0 | 0 | 0 | 0 | 0 |
| `seam_in_chain` | 74 | 6 | 24 | 9 | 430 | 0 |
| `tahwil_marker_vs_chain_count` | 0 | 0 | 0 | 0 | 0 | 530 |
| `truncated_before_companion` | 379 | 0 | 55 | 40 | 0 | 0 |
| `surface_name_mismatch` | 47 | 83 | 290 | 11 | 0 | 0 |
| `repeated_narrator` | 66 | 16 | 61 | 8 | 0 | 0 |
| `bidirectional_pair` | 82 | 7 | 18 | 4 | 0 | 0 |
| `prophet_as_mention` | 0 | 0 | 3 | 0 | 102 | 0 |
| `collector_self_mention` | 20 | 7 | 7 | 0 | 47 | 0 |
| `co_transmitter_gap` | 4 | 1 | 0 | 0 | 55 | 0 |
| `text_order_mismatch` | 1 | 1 | 1 | 0 | 8 | 0 |

Detector definitions (full rule text is in `detectors.cjs`; evidence in each `corrections.jsonl` row):
- `chrono_contradiction`: adjacent identified mentions where the teacher dies more than 40 years after the student's latest death, or more than 120 years before the student's earliest death.
- `seam_in_chain`: a standalone «ح» or a waw-led new-route verb («وأخبرني», «وحدثنا») sits between two adjacent mentions of one stored chain and the text after it does not restate the previous shaykh (that is a benign convergence and is excluded). Gives `split_position`.
- `repeated_narrator`: the same narrator id at two positions of one chain. `text_order_mismatch`: surfaces occur in the text in a different order than stored (single-chain hadith).
- `tahwil_marker_vs_chain_count`: route breaks in the text exceed stored chains minus one (a leading «وحدثنا» is not a break). Review-only.
- `co_transmitter_gap`: adjacent mentions joined only by a waw/comma («فلان وفلان قالا»).
- `non_name_surface`: the surface contains a formula/aside/verb word («بهذا الإسناد», «كلاهما», «مثله», «قال», «انها», «حدثتني», «هذا حديث») or has 7 or more words without nasab connectors.
- `bare_relation_resolved`: «أبي/أبيه/جده…» resolved to a person; verdict `consistent`, `mismatch` or `unverifiable` against the student's own nasab (ism comparison). Only `mismatch` is a correction.
- `companion_nonfinal`: a narrator who is terminal in at least 70% of 20+ appearances sits mid-chain. Empirical, review-only (Companions legitimately narrate from Companions).
- `truncated_before_companion`: final mention is almost never terminal elsewhere. Review-only (it fires on legitimate mawquf/maqtu' statements).
- `bidirectional_pair`: pair stored in both directions; minority direction flagged. `chain_reversed`: most dated pairs have the teacher dying later.
- `prophet_as_mention`, `collector_self_mention`, `length_outlier`, `surface_name_mismatch` (nasab words of the surface absent from the resolved name; mostly orthography, review-only), `gap_has_unstored_words` (review-only).

## Online verification

### Sources tried

| source | result |
|---|---|
| sunnah.com | HTTP 403, Cloudflare «Just a moment…» challenge on every URL tried; no bypass attempted; not used |
| hadith.islam-db.com | reachable (200), but its catalogue lists only nine early works (Musnad al-Rabi', Musnad Zayd, Tafsir Mujahid, Jami' Ma'mar, Sahifat Hammam, …); no Sunni collection; not usable |
| dorar.net | HTTP 403 Cloudflare; not used |
| islamweb.net | home page reachable; no per-hadith numbered chain view was probed; not used |
| hadithtransmitters.hawramani.com | TLS certificate expired (`SEC_E_CERT_EXPIRED`); not fetched |
| shamela.ws | reachable; not used |
| **api.turath.io** (search by public Arabic text, then the printed-edition page text) | **worked** for all nine collections (Risala/Arnaut/Abd al-Baqi/Sultaniyya/Bashar editions, Musnad Ahmad Risala ed., Darimi, Muwatta Yahya). Rate limited with HTTP 429 (retry-after about 1,800 s) after roughly 230 requests |
| **cdn.jsdelivr.net hadith-api** (public Arabic editions by collection and number) | **worked** for Bukhari, Muslim, Nasa'i, Abu Dawud, Tirmidhi, Ibn Majah; the text lineage is sunnah.com, so it is independent of our parsing but not of our text |

Every fetched page is under `fetched/` with URL, UTC timestamp and intent. Only a collection plus number, or public Arabic opening words, was sent.

### Sample

201 sampled chains: 108 random (stratified across the nine collections) and 93 detector hits (about 2 per detector stratum per round). Rows with no online page found are `unverifiable` and excluded from rates; they are listed per collection below.

**Measured defect rate on the random half** (a chain counts as defective when the online text, or an online-confirmed detector flag, shows a missing link, a merged route, a non-narrator mention, or a co-transmitter stored as teacher): **9 of 84 verifiable = 10.7%, Wilson 95% CI 5.7% to 19.1%.**

Defect kinds on the random half: not_a_narrator 6, missing_link 3.

By collection (random half only):

| collection | sampled | verifiable | defects | rate | 95% CI |
|---|---:|---:|---:|---:|---|
| abudawud | 12 | 12 | 1 | 8.3% | 1.5% to 35.4% |
| ahmad | 12 | 6 | 1 | 16.7% | 3.0% to 56.4% |
| bukhari | 12 | 11 | 0 | 0.0% | 0.0% to 25.9% |
| darimi | 12 | 7 | 1 | 14.3% | 2.6% to 51.3% |
| ibnmajah | 12 | 11 | 1 | 9.1% | 1.6% to 37.7% |
| muslim | 12 | 10 | 2 | 20.0% | 5.7% to 51.0% |
| muwatta | 12 | 5 | 1 | 20.0% | 3.6% to 62.5% |
| nasai | 12 | 12 | 1 | 8.3% | 1.5% to 35.4% |
| tirmidhi | 12 | 10 | 1 | 10.0% | 1.8% to 40.4% |

Unverifiable rows by collection: ahmad 11, darimi 5, ibnmajah 2, muwatta 7, muslim 2, tirmidhi 2, bukhari 1, nasai 1. The Muwatta and Pure Canon Musnad Ahmad / Darimi rows store only the matn in `text_ar`, so the online isnad was located only when it sits on the same printed page before the matn.

Detector hit strata, share of sampled hits the online text/my reading confirmed as a defect (small n, indicative only):

| stratum | sampled | verifiable | confirmed | share |
|---|---:|---:|---:|---:|
| bare_relation_resolved:consistent | 1 | 1 | 0 | 0.0% |
| bare_relation_resolved:mismatch | 6 | 5 | 2 | 40.0% |
| bidirectional_pair | 6 | 5 | 1 | 20.0% |
| chrono_contradiction:high | 6 | 6 | 0 | 0.0% |
| chrono_contradiction:medium | 6 | 6 | 2 | 33.3% |
| co_transmitter_gap | 6 | 6 | 2 | 33.3% |
| collector_self_mention | 6 | 6 | 0 | 0.0% |
| companion_nonfinal | 6 | 6 | 0 | 0.0% |
| gap_has_unstored_words | 4 | 4 | 0 | 0.0% |
| non_name_surface | 4 | 4 | 4 | 100.0% |
| prophet_as_mention | 6 | 6 | 1 | 16.7% |
| repeated_narrator | 6 | 5 | 1 | 20.0% |
| seam_in_chain | 6 | 6 | 5 | 83.3% |
| surface_name_mismatch | 6 | 3 | 1 | 33.3% |
| tahwil_marker_vs_chain_count | 6 | 5 | 1 | 20.0% |
| text_order_mismatch | 6 | 6 | 6 | 100.0% |
| truncated_before_companion | 6 | 6 | 0 | 0.0% |

Read the table with care: identity-focused strata (`chrono_contradiction`, `bare_relation_resolved`, `surface_name_mismatch`, `companion_nonfinal`, `bidirectional_pair`, `collector_self_mention`, `truncated_before_companion`) cannot be confirmed or refuted by re-reading the chain order, so a low share there means "the printed order agrees", not "the detector is wrong". Their evidence is the DB lifespans/nasab in each row plus the three online identifications below. `companion_nonfinal` and `truncated_before_companion` were read as legitimate chains in every sampled case (Companions narrating from Companions; mawquf statements ending at a Follower), hence review-only.

Consistency check against the whole corpus: 9,951 of 78,189 chains (12.7%) carry at least one correction row and 4,849 (6.2%) a high-confidence one, in line with the random-half estimate above.

Identity defects are only partly visible this way: the online text confirms who is named in the chain but not which person the identifier points to. On the random half, 0 of 108 chains carried a high-confidence chronology contradiction (DB lifespans), so the sample cannot bound the identity-error rate; the full-corpus detector counts above are the measurement for identity (398 high-confidence mentions, a lower bound: it only sees pairs with known dates).

### What the online sources could and could not verify

- Could: route structure (flattened tahwil), order, co-transmitters stored as teacher -> student, formula/aside text stored as a narrator, missing narrators between stored mentions, verbs fused into surfaces.
- Could not: which person an identifier points to. Printed editions only gloss identity occasionally («حرب، وهو ابن شداد»). Lifespans (`narrator_lifespans.basis = lexicon_unverified`) were not independently verified.
- Turath text and the hadith-api text are the same wording as ours for K6 collections; agreement therefore confirms extraction/segmentation, not the isnad's historical truth.

## corrections.jsonl

11,981 rows (5,548 high, 6,433 medium); `proposed_narrator_id` present on 100 rows.

| kind | high | medium | total |
|---|---:|---:|---:|
| misidentified | 398 | 212 | 610 |
| branch_seam | 543 | 158 | 701 |
| order_reversed | 0 | 56 | 56 |
| not_a_narrator | 4,518 | 5,912 | 10,430 |
| co_transmitter | 60 | 0 | 60 |
| missing_link | 29 | 0 | 29 |
| other | 0 | 95 | 95 |
| **total** | 5,548 | 6,433 | 11,981 |

Schema: `{mention_id, chain_id, hadith_id, kind, detector, evidence:{rule, values, online_url?, quote?}, proposed_action, confidence, collection, ...}`. A seam row carries `split_position` (the position where the second route starts). `also_flagged_by` lists other detectors that hit the same mention. Review-only detectors (`tahwil_marker_vs_chain_count`, `companion_nonfinal`, `truncated_before_companion`, `surface_name_mismatch`, `gap_has_unstored_words`, `length_outlier`) are counted above but deliberately not emitted as corrections: their sampled precision is below what a correction needs.

## Identity proposals backed by an online identification

`proposed_narrator_id` is set only where a printed edition or commentary names the person, the quoted words were re-verified against the cached response when `corrections.jsonl` was built, and the id exists in `narrators`. Three identifications were found (search responses in `fetched/identity_*.json`):

- **narrator:rawi:27536** (surface «عمر» between «محمود بن خالد» and «الأوزاعي», currently narrator:rawi:3 (ʿUmar b. al-Khattab, d. 23)): «اسناده صحيح، عمر، هو ابن عبد الواحد الدمشقي، والاوزاعي، هو عبد الرحمن بن عمرو، ومحمد بن علي بن حسين، هو ابو جعفر الباقر» - سنن النسائي - ط الرسالة, vol 6 p 502; «و النسائي في الكبري تحفة الاشراف ١١/ ١٥١٩٩ عن محمود بن خالد، عن عمر بن عبد الواحد، عن الاوزاعي» - جامع الأصول, vol 3 p 413. Note: The DB holds two same-name rawi records (27536 with death 200 and no Dimashqi nisba; 25603 without dates); 27536 is chosen because its dates fit (student of al-Awzaʿi d. 157, teacher of Mahmud b. Khalid) - the integrator should merge or confirm the duplicate. Rows: 2.
- **narrator:rawi:38420** (surface «عمر بن الخطاب أبو حفص» followed by «الفريابي», currently narrator:rawi:3 (the Caliph)): «عمر بن الخطاب السجستاني القسيري، ابو حفص نزيل الاهواز، روي عن محمد بن يوسف الفريابي وغيره وعنه ابو داود وغيره» - جامع المسانيد والسنن, vol 4 p 269; «عمر بن الخطاب ابو حفص صدوق، اخرج له ابو داود. حدثنا الفريابي . هو محمد بن يوسف الفريابي» - شرح سنن أبي داود للعباد, vol 358 p 21. Note: narrator:rawi:38420 carries death 354 in narrator_lifespans, which cannot be a shaykh of Abu Dawud (d. 275) who narrated from al-Firyabi (d. 212); the lifespan row needs checking. Rows: 1.
- **narrator:rawi:20331** (bare «أبي» after «ابن نمير» / «محمد بن عبد الله بن نمير», currently resolved to a different person): «حدثنا محمد بن عبد الله بن نمير واللفظ الاتي له اي لابن نمير لا لابي بكر حدثنا ابي عبد الله بن نمير حدثنا عبيد الله بن عمر حدثني نافع عن ابن عمر» - الكوكب الوهاج شرح صحيح مسلم بن الحجاج, vol 14 p 341. Rows: 97.

Rows where the mention is currently unresolved (`other`, `assign_identity`, medium) rely on the same identification plus the student's own nasab (محمد بن عبد الله بن نمير has the father عبد الله); only the exact hadith named in the commentary (Muslim 1315 = `hadith:k6:10550`) is high.

## Fix list for the integrator (ordered)

1. Apply the evidence-backed identity proposals (`replace_identity` / `assign_identity` rows carrying `proposed_narrator_id`; three editorial identifications)
   - Expected correction: 100 mentions (5 high); also check `narrator:rawi:38420` (lifespan 354 cannot belong to al-Firyabi's pupil and Abu Dawud's shaykh) and the duplicate same-name records `narrator:rawi:27536` / `narrator:rawi:25603`.
2. Split flattened tahwil chains at the second route's first mention (`split_chain_at`; detectors `seam_in_chain`, `repeated_narrator`, `text_order_mismatch`)
   - Expected correction: 701 correction rows over 598 chains; about 2,495 mentions would move to a new branch (positions at or after the split point where known).
3. Retire formula / aside / matn-fragment mentions (`retire_mention`, `non_name_surface`): «بهذا الإسناد», «كلاهما», «مثله», «اللفظ لفلان», «قال X مرة», grading formulas, fused verbs
   - Expected correction: 10,248 mentions, of which 574 currently carry a narrator id (an identity assigned to a non-person); the rest are unresolved nulls.
4. Demote chronologically impossible identities (`demote_identity`, `chrono_contradiction`, high) and relation words resolved to the wrong person (`bare_relation_resolved` nasab mismatch)
   - Expected correction: 393 high-confidence mentions (605 including medium); the homonym classes are single-token names (زيد, محمد, علي, عمر) and «محمد بن يحيى»-style shaykh/Companion collisions.
5. Split co-transmitters stored as teacher -> student (`split_co_transmitters`, `co_transmitter_gap`)
   - Expected correction: 60 mentions.
6. Flag chains with a missing link (`flag_missing_link`): student and a late-dying Companion adjacent, or text between adjacent mentions
   - Expected correction: 29 mentions (high); `gap_has_unstored_words` (2,841) is review-only.
7. Re-check minority-direction pairs and reversed chains (`reorder`, `bidirectional_pair`, `chain_reversed`)
   - Expected correction: 56 mentions, all medium; none confirmed as reversal in the sample, so treat as a review queue.
8. Prophet stored as a narrator mention (`prophet_as_mention`)
   - Expected correction: 105 mentions.

## Not checked

- Identity correctness beyond what chronology and the student's own nasab expose: two homonyms of the same era are invisible.
- Lifespans themselves (`lexicon_unverified`); a wrong death year produces a false chronology hit or hides a real one.
- Ahmad, Darimi and Muwatta (Pure Canon, matn-only text): detectors that read the text gap (`seam_in_chain`, `co_transmitter_gap`, `gap_has_unstored_words`) cannot run, and online verification succeeded only when the isnad is on the same printed page. Their seam counts are therefore understated.
- Hadith-kg / Riwayat identities carry no lifespans for most narrators, so `chrono_contradiction` sees K6-index mentions only.
- `proposed_narrator_id` coverage is tiny by design (needs online identification).
- Whether a stored chain that agrees with the printed text is historically correct (isnad criticism) was not assessed.
- Sunnah.com, dorar and Hawramani could not be reached; no cross-check against a second chain-identifying site was possible.
