---
type: pilot
---
# Context packets and prompt v2 for the chain reader

Nothing here runs a model, writes to the database or touches `outputs/`, `prompt.md`, `pilot/` or `analysis/`. Design reasons: `AGENTS.md`; sources: `SOURCES.md`;
online checks: `ONLINE_SOURCES.md`; holds: `HOLDS.md`; scoring: `score_v2_notes.md`.

## Two passes, one builder

| pass | reads | needs | packets |
|---|---|---|---|
| **chain reader** (`prompt-v2.md`) | the text + chain context (below) | offline; independent of our stored chain | `pilot-v2/packets/` |
| **text and metadata checker** (`prompt-v2-text.md`) | the text + `text_and_metadata` | may fetch public pages (`ONLINE_SOURCES.md`) | `pilot-v2/packets-text/` |
| third, **reconciling** reader (only where A and B disagree) | both readings and the stored chain | `--stored-chain`, readings embedded | built on demand |

**Decision: separate passes.** Chain readers stay offline, deterministic and independent (agreement only means something if nothing shared a fetched page or a
search quota); the checker is the only caller of the network (Turath 429 after ~230 requests, Noor after ~100), so its failures (`not_checked`) cannot contaminate a chain
reading; each prompt stays small for Haiku. One builder serves both: `build_context.cjs --kind chain|text|both`.

```
node --env-file=.env.local datasets/hadith-data/chain-reader/context/build_context.cjs --kind chain|text [--out-dir D] [--hadith-ids file.json] [--limit N]
      [--stored-chain] [--no-archive-flags]          # --stored-chain for the reconciling reader only
node --env-file=.env.local datasets/hadith-data/chain-reader/context/coverage.cjs > context/coverage.json
python -I -X utf8 context/tools/make_prompt_v2.py          # prompt-v2.md, prompt-v2-text.md (every worked example is validated at build time)
python -I -X utf8 context/tools/coverage_tables.py         # the tables below
python -I -X utf8 -m unittest discover -s context/tests -p "test_validate_v2.py"; node --test context/tests/test_build_context.cjs
```

Packets are `{"id": "cr-NNNN", "text", "context"}`, the same 284 reports, same order, same 12 packet files and the same text as v1 (`pilot/packets/`), so v1 and v2 compare
on one labelled set. Ids stay opaque (no work name, no `hadith:` id anywhere in a packet; checked). The work is named inside `context.work`, as intended.
`pilot-v2/*/manifest.json` records counts per context kind, bytes, input hashes (pilot rows, work profiles, builder, sidecars), the production dataset version and the UTC time.

## What the chain reader gets (`context`)

Every item carries its `source` code; items are claims, never answers. Order below is also the priority (last dropped first when over budget).

1. `work`: name, tradition, `compiler` (added by the tool, not by the reader), book, chapter, report number, a line of chain convention.
2. `previous_reports` (`prev1`..): the chain span (`chain_text`) and opening (`text_head`) of the report(s) before, when the report opens with a back reference or mid-chain
   (`عنه`, `وبهذا الإسناد`, `بالإسناد الأول`, `عن`, or a stored `suspension`), up to three while each opens the same way; `parent_report` for OpenITI continuations.
   **`needs_previous_report: true`** when such a report has a short remainder and no previous report was found: the reader must answer `cannot_read_without_previous_report`.
3. `source_claims`: K6I narrator index (the lexicon's names for its ids, one flat list), HKG sanads, RWY chain mentions (machine reading; surfaces without diacritics), THQ English
   sanad, NMC / no-chain statements; `sources_agree` (computed, source against source, never against our chain) and `sources_absent` (what has nothing, said explicitly).
4. `archive_flags`: the gate's reasons in plain words, `suspension`, up to two identity-withheld reasons (without the name). **Derived from our stored chain's shape**, so it is the one
   item that leans toward it; `--no-archive-flags` builds without it (recommended as an ablation on run B).
5. `name_facts`: death year, generation and place per name a source placed (MSD via the K6 id for Sunni reports; HKG and RWY records as the dataset gives them), with up to three
   same-name lexicon rows (death year only) for Sunni names. **No Sunni lexicon row is shown for an Imami name** (no Imami source links one); Ibadi/Zaydi get HKG/RWY records only.
6. `correspondences` (`corr1`..3): the same matn in other works with that work's chain text, confirmed first, then same wording, variant, by Jaccard; found by SWI.
7. `source_notes`: OpenITI compiler/editor notes.

Omitted when over budget, first to last: `source_notes`, `name_facts` (same-name lists first, then to six names), `correspondences` (to two, then 160 characters each), `archive_flags`,
`source_claims`, `previous_reports`, `parent_report`. A packet records `omitted_for_size`.

## What the text and metadata checker gets (`context.text_and_metadata`)

`stored_text_sha256`, `copies` (every other local copy of the text with a computed difference: `identical_after_normalisation`, `identical_except_word_spacing`, `ours_inside_theirs`,
`theirs_inside_ours`, `differs` with `ours_span`/`theirs_span`, or the OpenITI raw-file check), `source_file_hashes`, `statement` (says plainly when there is **no second local copy**, itself a
finding), `metadata` (`ours`; stored `gradings` with grader and source; `local` values from hadith-kg, Riwayat, Thaqalayn; computed `disagreements`; `not_stored`) and `lookup` (public keys for the
online check: collection and number, matn phrase, opening words, hadith-api and Thaqalayn API addresses). Comparisons ignore diacritics, punctuation, spacing, a printed number and the «ﷺ» sign.

## Size budget

Chain context: soft cap **3,000 characters of JSON per report**, text context 3,600. Why: a packet is 25 reports in one call; the pilot text averages ~450 characters and 3,000 characters of Arabic JSON is about 1,300 tokens, so a 25-report packet stays near 50-60k tokens
(a v1 packet was about 15k) and the fixed prompt (~30k characters) is paid once. A bigger context dilutes a small model's attention to the text, which is the authority.

| | median | p95 | max |
|---|---|---|---|
| chain context (characters) | 1,688 | 2,917 | 3,048 (the omission note adds ~40 over the cap) |
| text context | 2,196 | 2,625 | 2,964 |
| a whole report line (text + chain context) | 2,162 | | 8,622 (a 6,000-character Uyun report) |
| a packet file (25 reports, chain) | | | 22,301 to 67,356 |

## Coverage (pilot: 284 reports; corpus: live reports)

### Pilot: share of reports with each chain-context kind, by tradition

| kind | Sunni (136) | Imami (133) | Ibadi (10) | Zaydi (5) | all (284) |
|---|---|---|---|---|---|
| previous_reports | 2% | 21% | 0% | 0% | 11% |
| parent_report | 0% | 0% | 0% | 0% | 0% |
| source_claims | 99% | 92% | 40% | 20% | 92% |
| sources_agree | 57% | 0% | 30% | 20% | 29% |
| name_facts | 64% | 14% | 40% | 20% | 39% |
| correspondences | 36% | 38% | 40% | 20% | 37% |
| archive_flags | 45% | 45% | 10% | 0% | 43% |
| source_notes | 0% | 0% | 20% | 0% | 1% |

omitted for size (chain): {'name_facts': 36, 'correspondences': 7, 'archive_flags': 2, 'source_claims': 1}; reports with something omitted: 36

### Pilot: source claims by source, by tradition

| source | Sunni | Imami | Ibadi | Zaydi |
|---|---|---|---|---|
| K6I | 85% | 0% | 0% | 0% |
| HKG | 57% | 0% | 30% | 20% |
| RWY | 57% | 52% | 40% | 20% |
| THQ | 0% | 89% | 0% | 0% |
| NMC | 14% | 0% | 0% | 0% |

### Pilot: text and metadata, by tradition

| | Sunni | Imami | Ibadi | Zaydi | all |
|---|---|---|---|---|---|
| at least one second local copy | 60% | 100% | 100% | 100% | 81% |
| at least one copy independent of our source file | 60% | 52% | 40% | 40% | 55% |
| a computed difference found | 24% | 5% | 30% | 40% | 15% |
| no second local copy (finding) | 40% | 0% | 0% | 0% | 19% |
| book stored | 86% | 100% | 100% | 100% | 93% |
| chapter stored | 86% | 100% | 100% | 100% | 93% |
| report number stored | 100% | 100% | 100% | 100% | 100% |
| volume stored | 0% | 100% | 100% | 100% | 52% |
| page stored | 0% | 0% | 100% | 100% | 5% |
| url stored | 0% | 100% | 0% | 0% | 47% |
| a grading stored | 14% | 26% | 0% | 0% | 19% |
| a local source gives metadata for comparison | 60% | 100% | 40% | 40% | 78% |

### Corpus (live reports): second local copy and populated metadata, by work

| work | reports | indep. copy (hadith-kg / Riwayat / either) | source-file copy | book | chapter | number | volume | page | url | grading |
|---|---:|---|---|---|---|---|---|---|---|---|
| ibadi:musnad-rabi | 1,005 | 44% / 43% / 44% | 100% | 100% | 99% | 100% | 100% | 100% | 0% | 0% |
| imami:al-amali-mufid | 387 | 0% / 94% / 94% | 100% | 100% | 100% | 100% | 100% | 0% | 100% | 4% |
| imami:al-amali-saduq | 1,082 | 0% / 38% / 38% | 100% | 100% | 100% | 100% | 100% | 0% | 100% | 0% |
| imami:al-kafi | 14,245 | 0% / 75% / 75% | 100% | 100% | 100% | 100% | 100% | 0% | 100% | 97% |
| imami:al-khisal | 1,282 | 0% / 42% / 42% | 100% | 100% | 100% | 100% | 100% | 0% | 100% | 5% |
| imami:al-tawhid-saduq | 575 | 0% / 33% / 33% | 100% | 100% | 100% | 100% | 100% | 0% | 100% | 3% |
| imami:fadail-al-shia | 45 | 0% / 64% / 64% | 100% | 100% | 100% | 100% | 100% | 0% | 100% | 0% |
| imami:kamal-al-din | 659 | 0% / 0% / 0% | 100% | 100% | 100% | 100% | 100% | 0% | 100% | 0% |
| imami:kamil-al-ziyarat | 750 | 0% / 90% / 90% | 100% | 100% | 100% | 100% | 100% | 0% | 100% | 0% |
| imami:kitab-al-duafa | 226 | 0% / 1% / 1% | 100% | 100% | 100% | 100% | 100% | 0% | 100% | 0% |
| imami:kitab-al-ghayba-numani | 468 | 0% / 56% / 56% | 100% | 100% | 100% | 100% | 100% | 0% | 100% | 0% |
| imami:kitab-al-ghayba-tusi | 774 | 0% / 50% / 50% | 100% | 100% | 100% | 100% | 100% | 0% | 100% | 0% |
| imami:kitab-al-mumin | 201 | 0% / 8% / 8% | 100% | 100% | 100% | 100% | 100% | 0% | 100% | 0% |
| imami:kitab-al-zuhd | 290 | 0% / 96% / 96% | 100% | 100% | 100% | 100% | 100% | 0% | 100% | 0% |
| imami:maani-al-akhbar | 829 | 0% / 44% / 44% | 100% | 100% | 100% | 100% | 100% | 0% | 100% | 0% |
| imami:man-la-yahduruhu-al-faqih | 6,382 | 0% / 53% / 53% | 100% | 100% | 100% | 100% | 100% | 0% | 100% | 6% |
| imami:mujam-al-ahadith-al-mutabara | 555 | 0% / 79% / 79% | 100% | 100% | 100% | 100% | 100% | 0% | 100% | 77% |
| imami:nahj-al-balagha | 2,260 | 0% / 0% / 0% | 100% | 100% | 100% | 100% | 100% | 0% | 100% | 0% |
| imami:risalat-al-huquq | 49 | 0% / 0% / 0% | 100% | 100% | 100% | 100% | 100% | 0% | 100% | 0% |
| imami:sahifat-al-imam-ali-al-rida | 205 | 0% / 0% / 0% | 0% | 100% | 100% | 100% | 100% | 100% | 0% | 0% |
| imami:sifat-al-shia | 71 | 0% / 34% / 34% | 100% | 100% | 100% | 100% | 100% | 0% | 100% | 0% |
| imami:thawab-al-amal | 1,106 | 0% / 31% / 31% | 100% | 100% | 100% | 100% | 100% | 0% | 100% | 0% |
| imami:uyun-akhbar-al-rida | 954 | 0% / 23% / 23% | 100% | 100% | 100% | 100% | 100% | 0% | 100% | 1% |
| sunni:abudawud | 5,260 | 71% / 70% / 71% | 0% | 100% | 100% | 100% | 0% | 0% | 0% | 0% |
| sunni:ahmad | 23,529 | 28% / 28% / 28% | 0% | 0% | 0% | 100% | 0% | 0% | 0% | 100% |
| sunni:bukhari | 7,370 | 74% / 73% / 74% | 0% | 100% | 100% | 100% | 0% | 0% | 0% | 0% |
| sunni:darimi | 2,477 | 26% / 22% / 26% | 0% | 0% | 0% | 100% | 0% | 0% | 0% | 100% |
| sunni:ibnmajah | 4,227 | 85% / 84% / 85% | 0% | 100% | 100% | 100% | 0% | 0% | 0% | 0% |
| sunni:muslim | 7,596 | 57% / 54% / 57% | 0% | 100% | 100% | 100% | 0% | 0% | 0% | 0% |
| sunni:muwatta | 1,855 | 22% / 17% / 22% | 0% | 0% | 0% | 100% | 0% | 0% | 0% | 100% |
| sunni:nasai | 5,774 | 92% / 91% / 92% | 0% | 100% | 100% | 100% | 0% | 0% | 0% | 0% |
| sunni:shafii | 2,054 | 11% / 11% / 11% | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 100% |
| sunni:tirmidhi | 4,214 | 59% / 59% / 59% | 0% | 100% | 100% | 100% | 0% | 0% | 0% | 0% |
| zaydi:musnad-zayd | 691 | 30% / 9% / 30% | 100% | 100% | 98% | 100% | 100% | 100% | 0% | 0% |

| tradition | reports | indep. copy (any) | source-file copy | book | chapter | number | volume | page | url | grading |
|---|---:|---|---|---|---|---|---|---|---|---|
| ibadi | 1,005 | 44% | 100% | 100% | 99% | 100% | 100% | 100% | 0% | 0% |
| imami | 33,395 | 56% | 99% | 100% | 100% | 100% | 100% | 1% | 99% | 44% |
| sunni | 64,356 | 51% | 0% | 54% | 54% | 97% | 0% | 0% | 0% | 46% |
| zaydi | 691 | 30% | 100% | 100% | 98% | 100% | 100% | 100% | 0% | 0% |

## Credit codes

THQ Thaqalayn (CC BY 4.0), OITI OpenITI (CC BY-NC-SA 4.0), SUN sunnah.com, NMC NabiMuhammad.com, MSD narrator lexicon, K6I K6 narrator index, RIJ OpenITI rijal texts, HKG hadith-kg (CC BY 4.0), RWY Riwayat (CC0),
SWI this archive. Each context item names the source whose words it holds; SWI marks something this archive computed (flags, correspondences, comparisons). A fix must cite these codes (or `text`, or `online` with a URL).

## What could not be provided, and why

- **A second text for Sunni six-book reports without a hadith-kg/Riwayat match** (about half) and for Kamal al-Din, Nahj, Risalat al-Huquq, Sahifat al-Rida: no local copy exists; the packet says so. The original K6/sunnah.com
  rows sit in `archive/datasets.7z` and were not re-read; the Pure Canon xlsx is not parsed at build time (its sidecar hash only); no raw OpenITI file for Sahifat al-Rida is held.
- **Source-file copies are not independent**: Thaqalayn's JSON and the OpenITI raw files are what we loaded from. The OpenITI raw check is weak (11 of 15 pilot Ibadi/Zaydi reports are `not_located`, from page markers and orthography; flagged as no evidence).
- **Imami name facts from a lexicon**: none (rule above). **Rijal-layer facts** (Najashi, Tusi, Ibn Hajar): not used, because every link is `candidate_only` and mostly ambiguous (`SOURCES.md`).
- **Teacher and student lists of the lexicon** (`narrator_teachers`): not shown; they would invite the reader to complete chains from memory of who taught whom.
- **Online checks**: instructions and keys only; nothing was fetched. sunnah.com and dorar.net are blocked to automated reading.
- **Ibadi and Zaydi lexicon facts**: only through hadith-kg/Riwayat records; `external_narrator_lexicon_links` is the route to add more where a source links them.
- **Previous report for every back-reference opening**: supplied for 31 pilot reports; 4 are flagged `needs_previous_report`; others whose remainder is a full chain are readable but still held (`HOLDS.md`).
- The stored chain is not in chain packets (see `AGENTS.md`), by design.
