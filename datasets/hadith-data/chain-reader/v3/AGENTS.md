---
type: reference
---
# v3/: design notes

Operating instructions: `README.md` (what changed and why, numbers), `batch-001/RUN.md` (the run), `HOLDS.md`. Code carries one-line docs and points here. Nothing in this directory runs a model or writes the database;
the builders read production through a read-only session. Everything outside `v3/` (`context/`, `analysis*/`, `pilot/`, `outputs/`) is imported read-only; module names are distinct (`expand_v3`, `holds_v3`, `validate_v3`, `norm_v3`) so v2 and v3 import side by side.
Python writes in this directory use `newline="\n"` (Windows text mode writes CRLF and breaks hashes and JS string literals).

## fold
- `expand_v3.TextViews` holds the text twice. **As written first** (marks and tatweel removed: exactly v2's matching, so an `occurrence` counts the spelling the reader wrote), **folded second** (alif-maqsura/ya, Persian ی/ک, hamza carriers,
  ة/ه, kunya case أبو/أبي/أبا, a space after «و»). The first version folded only; the converter's validation found it: with kunya folding, `occurrence: 2` of «أبي» counted «أبو بكر» and put a link before the previous one (cr-0128, cr-0197).
  Where v2 found a surface, v3 finds the same place; v3 only adds surfaces v2 refused. The surface is always the text's own characters.
- A stray `occurrence` on a surface that stands once is ignored (and noted in `tool_notes`); an `occurrence` that fewer matches satisfy is still an error.
- Not folded: a marker inside a name («الحسين بن (ي‍) زيد», cr-0070 B stays invalid) and a name the reader completed beyond the text (cr-0141).
- `norm_v3.link_key` is the comparison form of one link: attached «و», trailing epithet («الكاتب», «العدل» ...) and a trailing nisba after at least two name words dropped. It equates readings that differ only by such a tail, on purpose: identity is not decided here.
  `same_man` merges two neighbouring narrator links: equal keys of two or more words, or the article-marked short form of a full name that continues with «بن» («المعتمر» / «معتمر بن سليمان»). «محمد» then «محمد بن علي» and «محمد بن الحسن» then «محمد بن الحسن الصفار» stay two men.

## expand
- Compiler head: not added when the route's first written link is the compiler under a spelling listed in `work_profiles_v3.json` (`compiler_aliases` by link_key equality, `compiler_alias_runs` as a word run inside a longer name,
  `compiler_alias_scope` first|any; `any` only for al-Muwatta, where the field often writes Yahya then Malik). v2 skipped the head when the short name stood in ANY link, so a Muslim chain starting «مسلم بن إبراهيم» lost its head; a bare name shared with a transmitter
  (Abu Dawud al-Tayalisi, Muhammad b. Isma'il) is never an alias. Musnad Zayd: compiler Abu Khalid al-Wasiti by owner ruling (2026-11-22), head added, aliases listed.
- `profile_for(context)` finds the profile by `context.work.key`; a packet without it (the v2 pilot's) falls back to its own compiler name.
- Groups may carry `"variant": true` (rule 4); expanded routes carry `group` and `variant`. Variant routes count in `canonical()` (agreement) and are skipped by `routes_end_at_different_links`.
- Output format `shura-chain-reader-output/3` = /2 plus the optional group key. Items, kinds and the 400-route cap are unchanged.

## holds
See `HOLDS.md`. The flag rule is the judge's: a `needs_ruling` flag holds only when both readers set it, because readings that differ are never applied anyway and one reader's flag caught 3 of 13 wrong readings at a cost of 13 right ones per 2 wrong.

## previous reports (the real defect of the second pilot)
The six back-reference reports that "arrived with no previous report and no flag" were all detected by v2's opening test. The lookup failed: `hadith_no_int` and the printed number repeat inside a Thaqalayn section or chapter
(the 23 reports of cr-0019's Kamal al-Din section all have `hadith_no_int` 21), so `key(p) < myKey` found nothing, and the chapter pool is empty when the report is a chapter's first. **Order is the provider file and the numeric provider id** (`backref_lib.orderedBooks`;
`source_record_id = provider-file:39|hadith:102`; Sunni K6 reports have a numeric provider id too). From a report, `walkBack` passes back references (`has_written_chain: false`) until a report that writes its own chain (it does not itself open
with a back reference and its first 320 letters hold two transmission words), at most 12; every intermediate is carried (90-140 characters each), the named chain is not elided (cr-0193's `…`), and `previous_reports` sit outside the 3,000-character budget under their own cap of 2,600.
`needs_previous_report` is set only for a pronoun or isnad-phrase opening (not for a bare «وعن X», which is how al-Faqih writes a saying: read from its text, held, never flagged).
The opening test widened: «وعنه», «بإسناده», «بالإسناد الأول», «بنفس الإسناد», «بالسند», a leading «ح» and «وعن X». «بهذا الإسناد» inside the first 160 letters is a closing back reference, not an opening (Muslim: 733 such reports).
JS (`backref_lib.cjs`) and Python (`holds_v3.OPENING`) are the same regex; `tests/backref_cases.json` runs both.

## prompt
`tools/chain_body_v3.md` (v2's body with the seven rule changes in place) + v1's tradition conventions + seven worked examples (v2's, trimmed, `work.key` and `has_written_chain` added), built by `tools/make_prompt_v3.py`, which fails the build when an example does not
validate against its real text, a quoted Arabic fragment is not in its pilot report, one of eight full pilot readings does not validate and expand as its rule says, or the prompt is longer than v2's. `prompt-v3.json` records version, sha256 and the build checks.
The prompt names no pilot id. Rules that changed: 3 (tail), 4 (second isnad, variant), 5-6 (source/subject: «كنا عند X» moved from a link to a place), 7 (same man), 8 (the answer names the man), 11 (`needs_ruling`), Previous reports (d).

## batch
`draw_population.cjs` (live uncertain reports) -> `draw_batch.py` (seeded, exclusions from every `chain-audit/**/sample_check.csv`, `verdicts.tsv`, the pilot's reports and the prompt-example report ids) -> `build_context_v3.cjs` (packets of 20, `--reports-out` the private hidden half)
-> readers -> `validate_v3.py` -> `triage_v3.py` -> `to_submission.py`. Opaque ids are `b1-` plus six hex of a salted hash; the salt and the map are in `private/` only. Packet order is shuffled across works.
The manifest binds the sample, the profiles, the builder, the lib and the sidecars by sha256; rebuild the packets if any of them changes.

## submission
The submit tool (`reviews/ai/tools/chain-fix-submit.ts`, being integrated by another agent) pins three things the v3 readers cannot satisfy yet: the prompt hash (`chain-reader/prompt.md`), the views (`text_only`, `text_and_stored_chain`; these readers saw text and context),
and the blind-packet rule of a `text_only` view. It also validates v1-shaped outputs, so `to_submission.py` writes that shape (compiler head dropped, `imam_in_text` as `narrator`; `reader_output_v3` rides along) and refuses to submit readings with inherited links
(the tool refuses stored chains that repeat earlier names). Provenance is in `run`: prompt version and sha256, model id and run id from the pass's RUN.txt line for the packet, packet id, UTC times, the second reader's run.

## deferred
- A judged out-of-sample measurement of the three new holds and of the tool changes: batch 001 (trigger: the batch is run and read).
- Reading «وعن X» in al-Faqih (406 bare «عن» openings in the corpus, mostly his) as back references is the spec's; whether a saying without a chain should be held for it is the owner's call (they are held now, never flagged).
- `needs_previous_report` could also be set when the walk-back finds nothing and a full chain follows the opening (readable but held today).
- Previous report across a chapter boundary is solved by book order; Sahifat al-Rida (204 openings) and Musnad al-Rabi' use `sanad_inherits_from` / the parent, not the walk.
- A marker inside a name («(ي‍)») and a name completed beyond the text stay invalid.
