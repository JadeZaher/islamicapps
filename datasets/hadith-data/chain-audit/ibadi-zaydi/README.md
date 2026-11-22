---
type: diagnostic
---
# Chain audit: Ibadi (Musnad al-Rabi), Zaydi (Musnad Zayd) and Sahifat al-Rida

Lane scope: isnad order and teacher/student correctness for the three OpenITI works (1,005 + 691 + 205 = 1,901 reports, production, read-only).
Nothing outside this directory was edited, nothing was written to the database, no file was deleted (one superseded file was renamed:
`detectors.cjs.corrupt.bak`, a `sed` accident, kept). Each tradition is read in its own terms; no chain was judged by Sunni rijal.

## Result in five lines

1. **Order is not the problem.** 0 of 5,882 stored mentions are out of written order (`D2a`; 5,877 aligned to the text), no chain runs Prophet-first, no teacher/student pair runs in both directions inside these works. The extractor emits left to right and the position index is that order.
2. **Content is.** 617 of 1,901 reports (rabi 213, zayd 199, rida 205) carry at least one structural defect: a continuation opener or a bare `قال` stored as a narrator, matn words stored as narrators, a chain that stops before a link that is written, a name fused with a frame word.
3. **Measured on a uniform random sample of 44 reports per work (132, each checked against an online text):** structural error rate rabi 25.0 % (95 % CI 14.6-39.4), zayd 25.0 % (14.6-39.4), rida 100 % (92.0-100); population-weighted 33.1 % (24.9-41.2).
4. **Sahifat al-Rida has no usable chain.** 204 of 205 reports are «وباسناده …» continuations and none of them receives the inherited chain; the Imam chain itself (al-Rida → Musa → Jafar → … → Ali) written in `rida_0001` is not stored. Zayd and Rida have **zero resolved narrators**, so neither contributes a `narrator_transmissions` edge.
5. **One identity carries the Ibadi spine, and it looks wrong.** «أبو عبيدة» (272 mentions) is resolved to `narrator:riwayat:N0013779` «مسلم بن أيمن»; the work and Wikipedia name him «مسلم بن أبي كريمة». The edge N0013779 → Jabir b. Zayd has `hadith_count` 252.

## What was done

`load_cache.cjs` (read-only dump) → `detectors.cjs` (25 rules, below) → stratified sampling and comparison with online texts (`online_compare.py`, six rounds) → hand adjudication
(`review/round*.tsv`, one line per report: verdict, kind, evidence note) → `finalize.py` (rates, `sample_check.csv`, `corrections.jsonl`, `summary.json`).
Position convention (from the lane brief): 0 is nearest the compiler, the last position nearest the Prophet; the stored order must equal the written order of the text.

### Sample and loop (rounds)

| Round | Reports | Random | Detector | Online text found | New pattern found |
|---|---|---|---|---|---|
| 1 | 42 | 21 | 21 | 40 | honorific split on waw («كرم الله وجهه» → «جهه …matn»); rida `قال` opener; missing «علي» after «عن جده (ع م)» |
| 2 | 42 | 21 | 21 | 39 | Companion named after «قال: قال X»; Qur'an «وجوه» split on waw; «علي انه» frame word |
| 3 | 42 | 21 | 21 | 34 | Qur'an citation formula «في قوله تعالى»; «وسئل النبيء» |
| 4 | 36 | 18 | 18 | 29 | connector «وعن»; Zayd «حدثني أبو خالد قال: سألت زيدا» (Zayd link missing) |
| 5 | 30 | 15 | 15 | 28 | one function-word fragment («ولو» → «لو»); otherwise nothing new |
| 6 | 36 | 36 | 0 | 34 | held-out, detectors frozen: 17 wrong, 15 flagged (88 %); 2 misses («علي انه كان يستحب …» fused, «وكان زيد بن علي») turned into `D3f`/`D3j` |
| total | 228 | 132 | 96 | 204 | |

Rounds 1-5 each led to detector changes and a re-run on all 1,901 reports; round 5 produced no new pattern class, round 6 is the held-out check. Recall on the random half is 66/66 after the final detectors, **but those detectors were
tuned on the same reports; the honest out-of-sample number is round 6: 15 of 17 wrong chains flagged before the last generalisation, 0 false positives on 36.**

### Online sources

| Source | Used for | Result |
|---|---|---|
| OpenITI GitHub raw, `0125AH` Zayd: `Zaydiyya0000056-ara2` (izbacf.org edition, «المجموع الفقهي والحديثي») and `Shia000811-ara1` (Dar Maktabat al-Hayat, Beirut) | independent texts of Musnad Zayd (our parse is `Zaydiyya0000052-ara1`) | worked; 75 of 76 sampled Zayd reports located |
| OpenITI `0225AH` Sahifat al-Rida: `Zaydiyya0000121-ara1.completed` (al-Tabarsi route) and `Masaha001003-ara1` | independent recensions of the Sahifa; Imam chain; sibling-report evidence | worked; 55 of 76 sampled Rida reports located (the rest are reports the two editions do not contain); the Imam chain is written there verbatim |
| OpenITI `0175AH` Rabi `ShamIbadiyya0000155-ara1` (master and `pre-clean` branch) | the written chain of each Rabi report (same transcription as ours, so this checks the chain builder, not the transcription) | worked; **not independent** |
| ar.wikipedia «مسند الربيع بن حبيب» and «أبو عبيدة مسلم بن أبي كريمة» | shape of the Ibadi chain; identity of Abu Ubayda | worked |
| shamela.ws (search is JavaScript; category pages 1-12 listed) | an Ibadi or Zaydi edition | **did not work**: the books are not in the Shamela main library |
| turath.io search API (`api.turath.io/search`) | a second text of any of the three works | **did not work**: none of the three is indexed (queries saved in `fetched/turath_search_*.json`) |
| ar.wikisource.org | Rabi text | search reachable, no Rabi text |
| archive.org, ketabonline.com, al-maktaba.org, alukah.net, noor-book, ibadi sites | | timed out, 403, or no such host; recorded, not retried further |

**Consequence for Rabi:** no independent online transcription of the Musnad al-Rabi could be reached. The 44 random Rabi reports are compared with the written chain in the raw OpenITI file and the chain shape with Wikipedia.
That finds extractor errors (the dominant class) but cannot find a transcription error shared by our text and OpenITI. All pages are in `fetched/` with a header (URL, UTC time, intent); the quote in each `sample_check.csv` row is the exact original Arabic from the saved file.
Only public references and public Arabic text were sent anywhere.

## Counts per detector and work (full corpus)

Reports with at least one hit (mention-level counts are in `summary.json` → `hits`):

| Detector | Meaning | rabi | zayd | rida |
|---|---|---|---|---|
| D1a opener_as_narrator | «وبهذا السند / وباسناده / ومن طريقه / ومن طريق X» or a bare `قال` stored as a narrator | 46 | 0 | 180 |
| D1b inherited_chain_missing | report inherits a chain but stores none of the parent's mentions | 27 | 0 | 202 |
| D1c undeclared_continuation | opens with a continuation formula but `sanad_inherits_from` is null | 22 | 0 | 0 |
| D5c inheriting_no_chain | inheriting report with no chain at all (absent from the teacher/student view) | 1 | 0 | 12 |
| D2a order_reversed | stored order differs from written order | 0 | 0 | 0 |
| D2b prophet_as_mention | the Prophet as a mention (in this case the matn of a report with no chain) | 1 | 0 | 0 |
| D2c compiler_as_mention | الربيع / أبو خالد stored (informational) | 61 | 11 | 0 |
| D3a relation_as_mention | «ابيه / جده / ابائه» as literal mentions | 1 | 661 | 1 |
| D3b not_a_narrator | reporting verb (`قال`) | 2 | 1 | 142 |
| D3c not_a_narrator | honorific «كرم الله» kept in the name | 0 | 16 | 0 |
| D3d not_a_narrator | matn words or a verb frame fused into / standing as a narrator | 47 | 40 | 10 |
| D3e merged_names | two persons in one surface | 3 | 1 | 0 |
| D3f other | name + frame word (أنها / أنه / بلغني / سئل) | 26 | 77 | 1 |
| D3g not_a_narrator | orphan branch from splitting «كرم الله وجهه» / «وجوه» on waw | 2 | 17 | 0 |
| D3h not_a_narrator | Qur'an citation formula | 7 | 5 | 1 |
| D3i not_a_narrator | question frame «سألت / سئل» inside a surface | 18 | 11 | 1 |
| D3j other | connector «وعن / وكان» kept in a surface | 11 | 1 | 0 |
| D3k not_a_narrator | function word left by a waw split («ولو» → «لو») | 4 | 1 | 0 |
| D4a misidentified | «أبو عبيدة» resolved to a patronymic without «أبي كريمة» | 272 | 0 | 0 |
| D4b misidentified | resolved narrator shares no name token with the surface | 0 | 0 | 0 |
| D4c same_narrator_twice | | 0 | 1 | 0 |
| D5a missing_chain | written chain, none stored | 2 | 3 | 0 |
| D5b chain without written chain | | 0 | 0 | 0 |
| D5d low_confidence_chain | `split_confidence='low'` report that has a chain (informational) | 226 | 46 | 51 |
| D6a other | links written after the last stored mention | 56 | 11 | 3 |
| D6b missing_chain | the Imam chain in `rida_0001` | 0 | 0 | 1 |
| D6c other | Companion after «قال: قال X» missing | 9 | 0 | 0 |
| D6d other | link after «جده» (Ali) missing | 0 | 53 | 0 |
| any structural hit (all except D2c, D3a, D4a, D5d) | | 213 | 199 | 205 |

Answers to the five questions of the brief:

1. **Openers / inherited chains.** The opener is stored as a narrator on 226 reports (46 rabi, 180 rida). Inheriting reports (231: 27 rabi, 204 rida) get **no** inherited mentions: D1b is 229 of 231, the other 2 already carry a spelled-out chain. 13 have no chain at all. All of them are therefore absent from the teacher/student view. 22 further rabi reports are continuations the parser did not recognise (`RE_CONTINUATION_CHAIN` lacks «ومن طريق X عنه»).
2. **Order.** 0 reversed (5,877 of 5,882 mentions aligned; the other 5 are surfaces the text does not repeat). No Prophet-first chain. The compiler is stored on 61 rabi reports (`الربيع`; position 0 in 56 of the 57 clean mentions, the rest fused with a frame word or the next name), on 11 zayd reports (Abu Khalid, positions 0-5 depending on how many book transmitters precede him) and omitted on the rest: an inconsistency, not an order error (a policy decision, nothing to "fix").
3. **Relations, collectives, frame words, matn.** «ابيه/جده/ابائه» literal on 663 reports (all written that way, none resolved, 1,495 mentions); frame or matn words captured as narrators on 375 reports (group P2). **Low-confidence reports (370; rabi 259, rida 58, zayd 53):** 323 have a chain, 47 have none; 161 of the 370 are flagged structurally (rabi 90, rida 58, zayd 13); among the 54 sampled `D5d` reports 41 were wrong and 13 sane, so most low-confidence chains are not sane.
4. **Identities.** The only systematic wrong person is Abu Ubayda (272). «جابر بن زيد» → Jabir b. Zayd (254 mentions, plus 32 bare «جابر» resolved to him) and the Companions agree with the surface; no «Jabir b. Abd Allah» confusion was found (`D4a` second rule: 0). No pair in both directions inside these works (24 resolved pairs); one report repeats a narrator (question frame). The identity layer of Zayd and Rida is empty (0 of 3,422 mentions resolved).
5. **Missing / spurious chains.** Written chain, none stored: 5 (3 confirmed, 2 are narration with no chain, correctly empty). Spurious: chains made of matn on 97 reports (D3d), 145 more with a bare `قال`.

## Measured error rates (random half, n = 44 per work, 95 % Wilson CI)

| | structural error | identity error | relation words left literal |
|---|---|---|---|
| rabi | 11/44 = 25.0 % (14.6-39.4) | 12/44 = 27.3 % (16.3-41.8) | 0/44 |
| zayd | 11/44 = 25.0 % (14.6-39.4) | 0/44 | 41/44 = 93.2 % (81.8-97.7) |
| rida | 44/44 = 100 % (92.0-100) | 0/44 | 0/44 |
| population-weighted | 33.1 % (24.9-41.2) | | |

*Structural error* = the stored chain differs from the written chain by a wrong, extra, missing or fused link (identity and literal relation words are counted separately). Detector precision on the sampled hits is 100 % except `D3a` 97 % and `D5a` 60 % (three of five).
Of 54 sampled low-confidence chains 13 are sane. Legitimate shapes that must not be "fixed" were seen and kept: balagha (`بلغني عن …`), mursal of Jabir b. Zayd directly from the Prophet (`rabi_0928`, `0955`, `0969`, `0998`), a statement of the Imam alone.
Wikipedia states the same: part 4 of the Musnad carries mursal of Jabir and other chains, so Jabir at position 0 is correct.

## Ordered fix list (details, functions and lines in `parser_fix_proposals.md`)

1. **P1 + P6, carry the inherited chain and store the Imam chain** — 253 reports (rabi 49, rida 204); makes Sahifat al-Rida usable and adds the first Rida edges. Highest value per line changed.
2. **P2, build mentions from `sanad_ar`, none when the split is low-confidence** — 375 reports; removes every matn/frame-as-narrator case at once (D3b/d/e/f/h/i/j).
3. **P7, stop «أبو عبيدة» being "confirmed by text" from a kunya** — 272 reports; the whole Ibadi spine depends on it. Curator input needed; until then unresolved is safer than wrong.
4. **P4, links after `(ع م)`, «قال: قال X», «بلغني عن X»** — 126 reports.
5. **P3, honorific and waw splits** — 24 reports. **P5, colon/connector** — 14 reports.
6. **P8, resolve «ابيه/جده» from the Musnad's opening isnad** (resolver, with the citation `zayd_0001`) — 663 reports; the only way Zayd enters `narrator_transmissions`.

## What was not checked

- Chains of Rabi reports beyond the 44+54 sampled against an independent transcription (none exists online here); a transcription error common to OpenITI and our text.
- The identity of the book transmitters in Musnad Zayd and Sahifat al-Rida (the 5-16 editorial names before the Imam), and the three Riwayat narrators other than Abu Ubayda (checked only by name token).
- Whether Riwayat's N0013779 is a different person in Riwayat's own data: only the patronymic difference and the work's own text are evidenced; the proposed action is withdrawal, not replacement (no `proposed_narrator_id` was given anywhere).
- Report boundaries (merged reports such as `rida_0029`), `narrator_transmissions.hadith_count` recomputation, translation, grading.
- 24 of 228 sampled reports could not be located in an online edition (mostly Rida reports outside the two editions); they are judged from the written text and a sibling report, marked in `sample_check.csv` (`online_located = no`).

## Files

| File | |
|---|---|
| `corrections.jsonl` | 3,075 rows: `opener_as_narrator` 245 high; `inherited_chain_missing` 264 high; `not_a_narrator` 434 high / 6 medium; `relation_as_mention` 1,495 high; `other` 254 high / 99 medium; `misidentified` 272 medium; `missing_chain` 1 high / 5 medium. `D5d` (informational) and `D2a` (0) are not emitted. Confidence is high when the detector confirmed in the sample at ≥90 % with ≥3 hits. |
| `parser_fix_proposals.md` | P1-P8 |
| `sample_check.csv` | 228 reports: our chain, online chain, agree, error flags, detectors, URL, exact quote |
| `summary.json` | all counts, rates, precision, fix-group sizes |
| `detectors.cjs`, `lib.cjs`, `load_cache.cjs`, `online_compare.py`, `finalize.py`, `make_fixtures.cjs`, `fetch.sh`, `turath.py`, `show*.{cjs,py}`, `peek.cjs`, `q*.cjs`, `explore*.cjs` | scripts (the last three groups are scratch explorers) |
| `rounds/`, `review/` | per-round picks with online evidence, hand verdicts |
| `fetched/` | every saved page with header; `fixtures/confirmed_examples.json` real examples for the tests |
| `test_detectors.cjs` | 30 tests: every detector fires on a confirmed real report; legitimate shapes stay clean; `D2a`, `D4b`, `D5b` have no real hit in production so they run on a mutated real chain |

Run: `node --env-file=.env.local datasets/hadith-data/chain-audit/ibadi-zaydi/load_cache.cjs <cache.json>` (needs `DATABASE_URL_PRODUCTION`; the scripts read the cache path from `lib.cjs`), `node detectors.cjs`, `python -I -X utf8 finalize.py`,
`node --test datasets/hadith-data/chain-audit/ibadi-zaydi/test_detectors.cjs`.
