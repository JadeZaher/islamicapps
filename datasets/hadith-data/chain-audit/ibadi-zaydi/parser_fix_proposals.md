---
type: diagnostic
---
# Parser and mention-builder fix proposals (nothing here was applied)

Origin of the chains: `neo4j_export/export_bundle.py` builds every mention from the report's whole `text_ar`
(`text_ar = row["text_ar"]`, line 1009; `surface_branches = extract_isnad_branches(text_ar)`, lines 1277 and 1287). The extractor
is `extract_isnad_unified.py`. The OpenITI parser's own chain cut (`sanad_ar`, `sanad_inherits_from`, `split_confidence`) reaches
the `hadiths` table through `pg_export/export_postgres.py` lines 852-873 and is never read by the mention builder, so the chain a
reader sees on the report page (`sanad_ar`) and the chain stored as mentions are produced by two unrelated rules. Most defects below
follow from that. Report counts are distinct reports from `detectors.cjs` on production (1,901 reports); `corrections.jsonl` has
the per-mention rows.

| # | Fix | Where | Reports changed |
|---|---|---|---|
| P1 | Carry the inherited chain | `export_bundle.py` 1277/1287 + `parse_openiti.py` `RE_CONTINUATION_CHAIN` 404-405 | 253 (rabi 49, rida 204) |
| P2 | Build mentions from `sanad_ar`, not `text_ar`; no chain when `split_confidence='low'` | `export_bundle.py` 1277/1287 | 375 (rabi 98, rida 151, zayd 126) |
| P3 | Honorific / waw splits | `extract_isnad_unified.py` `_split_co_transmitters` 196-221, `_HONORIFIC_RE` 45-53 | 24 (zayd 18, rabi 6) |
| P4 | Links after `(ع م)` / after «قال: قال X» / after «بلغني عن X» | `_matn_start` 183-194, `_extract_segment_branches` 260-299 | 126 (rabi 64, zayd 59, rida 3) |
| P5 | Colon splits the compiler opener | `_extract_segment_branches` 275-279 (`prefix`) | rabi 3 + 11 «وعن/وكان» connectors |
| P6 | Imam chain of Sahifat al-Rida | follows from P2 on `rida_0001` | 1 report, which P1 then gives to 202 |
| P7 | Riwayat identity of a kunya-only surface | `pg_export/external_identity.py` `standing_identity` 96-132 (line 121) | 272 reports, 272 mentions |
| P8 | Relation words | resolver (`regen_unified_csvs.resolve_narrator`), not the extractor | 663 reports, 1,495 mentions |

## P1 Inherited chains: opener stored as a narrator, inheriting reports without a chain

Measured: 226 rabi+rida reports have the opener («وبهذا السند», «وباسناده», «ومن طريقه», «ومن طريق X») or a bare `قال` stored as a
narrator (D1a); 229 inheriting reports (27 rabi, 202 rida) keep none of the parent's mentions (D1b); 13 inheriting reports have no
chain at all (D5c); 22 rabi reports open with «ومن طريق X (عنه)» but `sanad_inherits_from` is null (D1c). Consequence: none of these 253
reports contributes a teacher/student pair. Sahifat al-Rida is worst: 204 of 205 reports inherit, so the Sahifa has no usable chain
except where a report spells it out (`rida_0021`).

1. `parse_openiti.py` line 404-405, `RE_CONTINUATION_CHAIN`: add the form with a name between: `ومن\s+طريق\s+\S+(?:\s+\S+){0,3}?(?:\s+عنه)?` so
   «ومن طريق ابن عباس عنه» is a continuation (22 rabi reports). Record the named transmitter in a new field (`continuation_via`) so the
   mention builder can replace the parent's Companion with him.
2. `export_bundle.py` before line 1277: when the report has `sanad_inherits_from_record_id`, set
   `surface_branches = copy.deepcopy(chain_of(parent))` (memoise; follow the pointer to the root; guard against cycles; the pointers are
   chains of at most a few hops, e.g. `rida_0005#4 -> #3 -> #2 -> rida_0005`). If `continuation_via` is set, replace the last link of the
   copy with that name. Do not call `extract_isnad_branches` on a continuation report.
3. Acceptance: D1a, D1b, D1c, D5c go to 0; `narrator_transmissions` gains edges only where the parent chain is itself right (P2/P6 first).

## P2 One definition of the chain: use the parser's `sanad_ar`

Measured: after P1, 375 reports still store matn words or frame words as narrators: `قال` (D3b, 145), matn text captured as a narrator
(D3d, 97), name + `أنه/أنها/بلغني/سئل` fused (D3f, 104), question frames «سألت زيدا بن علي» (D3i, 30), Qur'an formulas «في قوله تعالى» (D3h, 13),
the Prophet as a mention (D2b, 1). Cause: `_matn_start` (line 183) only recognises a matn boundary by a Prophet attribution or a speech verb
followed by no link, and `_extract_segment_branches` (line 260-264) falls back to `_clean_surface(chain_text)` over the whole text when it
finds no link, so a report with no isnad («وقال صلى الله عليه وسلم: «إن لم يكن الشهداء…»») becomes a chain made of the matn.

1. In the mention builder pass `sanad_ar` instead of `text_ar` for the three OpenITI works (the parser already applies the owner's convention:
   the chain runs through the reporting verb). Where `sanad_ar` is null (`split_confidence='low'`, 370 reports) emit no chain rather than the
   whole-text guess; of the 323 low-confidence reports that have a chain, 161 are flagged by a structural detector and 41 of the 54 sampled are wrong.
2. In the segment fallback (line 262-264), return `[]` when `chain_text` has no link and contains no name-led surface (`RE_NAME_LED` in the parser).
3. Add the Qur'an formula and question frames to `_TRAILING_FRAME_RE` (line 54-60): `في\s+قول(?:ه|ك)?`, `سألت|وسألت|سئل|وسئل`.

## P3 Waw splits inside honorifics and ordinary words

`_split_co_transmitters` (line 196-221) splits on `\s+و(?=\S)` unless the previous token is a patronymic connector. «علي بن أبي طالب كرم الله وجهه»
splits into «…كرم الله» and «جهه …matn…» (a spurious second branch on 17 zayd + 2 rabi reports, plus the honorific kept in the first name on
16), the Qur'an word «وجوه» into «جوه…» and «ولو» into «لو» (5 reports); 24 reports in all.

1. `_HONORIFIC_RE` (line 45-53): add `كرم\s+الله\s+وجهه(?:\s+ورضي\s+عنه)?` and `رضي\s+الله\s+عنه`-style forms already there; it must run before `_split_co_transmitters`.
2. `_split_co_transmitters`: do not split when the token after the waw is `جهه|جوه|جهي` or a single-letter-stem word (`لو`, `لا`, `ما`, `من`): only split when what follows looks like a name (starts with `ال`, `ابو|ابي|ابن|عبد|ام` or ends a `بن` chain).
3. Acceptance: D3g, D3c, D3k go to 0.

## P4 Links that stop the chain early

Measured: 126 reports have links written after the last stored mention (D6a 70, D6c 9, D6d 53, overlap removed). Three shapes, all confirmed against the
online texts: (a) Zayd: «عن جده (ع م) عن علي» / «عن علي (ع م) انه» without a `قال` — the chain ends at `جده` (53 reports) or keeps `انه` in the last surface;
(b) Rabi: «جابر بن زيد قال: قال جابر بن عبد الله» (9) and «قال: بلغني عن X قال» (56): the named source is a link; (c) Rida: «وباسناده قال: حدثني أبي جعفر قال: …
حدثني أبي عن أبيه عن جده الحسين بن علي عن ابيه علي» (3).

1. `_LINK_RE` (line 21-28): treat `قال[:\s]+قال\s+<name-start>` and `بلغني\s+(?:ان\s+)?عن` as links; add `انه|انها|ان` to the trailing frame (`_TRAILING_FRAME_RE`) *before* the whole surface is cut at the first match, so `علي انه كان يستحب …` is cut to `علي`.
2. `_matn_start` (line 183-194): a `(ع م)` or honorific between `جده` and the next `عن` must not end the chain: strip `_HONORIFIC_RE` matches before searching for `_LINK_RE`.
3. Acceptance: D6a/D6c/D6d go to 0 except genuine balagha without a named source.

## P5 Colon splits the compiler opener

`_extract_segment_branches` lines 275-279 clean the text before the first link as one surface; `_PUNCT_RE` (line 61) turns the colon into a space, so «قال الربيع بن حبيب: أبو عبيدة
عن جابر…» becomes the single mention «الربيع بن حبيب أبو عبيدة» (3 reports; `rabi_0002`, `rabi_0018`, `rabi_0862`). Split `prefix` on `[:：]` before `_clean_surface`. The connector
`وعن` / `وكان` kept in a surface (12 reports) is the same family: `_LEADING_LABEL_RE` (line 62-64) should also strip `وعن\s+`, `وكان\s+`, `كان\s+`.

## P6 The Imam chain of Sahifat al-Rida is not stored

`rida_0001` writes: «… عن أبي القسم عبد الله بن احمد بن عامر الطائي بالبصرة قال: قال حدثني أبي سنة مائتين وستين، قال حدثني علي بن موسى الرضى … قال حدثني أبي موسى بن
جعفر، قال حدثني أبي جعفر بن محمد، … علي بن أبي طالب». The extractor stops at the first `قال: قال` (`_matn_start`, speech verb, line 183-194); the stored chain is the 16 editorial transmitters of the
Yemeni manuscript tradition and ends at Abu al-Qasim. Independent edition: `openiti_rida_zaydiyya121_text.html` (al-Tabarsi route) has the same Imam chain «حدثني علي بن موسى الرضا (ع) سنة أربع وتسعين ومائة قال حدثني أبي موسى بن جعفر
قال حدثني أبي جعفر بن محمد قال حدثني أبي محمد بن علي قال حدثني أبي علي بن الحسين قال حدثني أبي الحسين بن علي قال حدثني أبي علي بن أبي طالب». Fix: P4 item 1 (`قال: قال حدثني` is a link) and P2 (`sanad_ar` for `rida_0001`
is null today because `split_confidence='low'`; the parser's `RE_ENDS_IN_CHAIN` should accept a long «قال حدثني» ladder as one chain). After P1, all 202 inheriting reports get the Imam chain. The report also begins mid-sentence
(«شيخه، وجاء السند من الدين…») because the editor's preface was cut at the wrong place; that is a parser boundary issue (`parse_rida_appendix`) and the text before «فاقول أروي هذه الصحيفة» is commentary, not chain.

## P7 Riwayat identity for a kunya-only surface

272 rabi mentions of «أبو عبيدة» are resolved to `narrator:riwayat:N0013779` (name «مسلم بن أيمن») with candidate basis `source_riwayat_confirmed_by_text`, detail `full_agreement:full_name_key`
(source refs `riwayat:H0201944`, `riwayat:H0201945`, …). The work itself names him «أبو عبيدة مسلم بن أبي كريمة التميمي» (`rabi_0001`) and Wikipedia ar (Musnad al-Rabi page) writes «الربيع عن شيخه أبو عبيدة مسلم بن أبي كريمة
عن جابر بن زيد»; the patronymic differs, so the identity is at best unproven. The edge `N0013779 -> N0001547` (Abu Ubayda ← Jabir b. Zayd) carries `hadith_count` 252 in `narrator_transmissions`, i.e. the whole Ibadi spine rests on it.
`standing_identity` (`external_identity.py` line 121) accepts `source_riwayat_confirmed_by_text` for any mention that is not label-like. Proposal: do not let a kunya-only surface («أبو X») be "confirmed by text" by
a source whose full name is not in the text; add a per-work override table (Ibadi: «أبو عبيدة» = Muslim b. Abi Karima) maintained by a curator with a citation; until then leave unresolved. The existing
`narrator:rawi:17736` is named «ومسلم بن أبي كريمة» (leading waw artefact); whether it is the same person is for the curator.

## P8 Relation words

661 zayd reports store «ابيه», «جده» (and «آبائه» ×6) as literal mentions (1,486 mentions). They are written that way and the order is right, but the teacher/student view cannot use them (zero zayd and zero rida
mentions are resolved; Zayd contributes no `narrator_transmissions` edge). The Musnad names the ancestors in its first report (`zayd_0001`: «زيد بن علي عن ابيه علي بن الحسين عن جده الحسين بن علي»);
a document-scoped resolution (relation word → the ancestor named in the work's opening isnad, citing `zayd_0001`) is evidence-backed. It belongs in the resolver, not the extractor
(`AGENTS.md` §Uniform source-surface extraction says the extractor keeps `أبيه`/`جده`). Not proposed for the mention builder.

## What would change in numbers

If P1-P6 land and the mention builder reads `sanad_ar`: reports with a structural defect fall from 617 (rabi 213, rida 205, zayd 199) to those the sample shows are not covered (balagha sources without a link,
sayings with several questions): estimated under 5 % of reports. P7 changes 272 reports' identity but leaves the chain order untouched.
