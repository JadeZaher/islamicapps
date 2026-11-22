---
type: reference
---
# v3_1/: design notes

Operating instructions: `../tranches/RUN.md` (the full run), `batch-001/RETRIAGE.md` (the numbers), `README.md` (what changed). Code carries one-line docs and points here. Nothing in this directory runs a model or writes the database; the builders read production through a read-only session.
`v3/`, `analysis-*/`, `context/`, `pilot/` and `outputs/` are imported read-only; module names are distinct (`expand_v3_1`, `holds_v3_1`, `validate_v3_1`, `norm_v3_1`, `triage_v3_1`, `to_submission_v3_1`, `backref_lib_v3_1.cjs`, `build_context_v3_1.cjs`) so v3 and v3.1 import side by side.
Python writes use `newline="\n"`. The rest is a copy of v3 (`v3/AGENTS.md` holds its reasons: fold, expand, previous reports, batch); only the changes are here.

## Owner rulings of 2026-11-22 and where each lives
1. **The asker is a link** («سأل / سئل / كتب / شكا / سأله»): the route is asker, then the one asked (`imam_in_text` for an Imam). The one asked written as a pronoun is taken from the earlier report; neither named: no named link. Prompt rule 5; `holds_v3_1.asker_not_a_link` checks mechanically that a named asker has a link (`named_asker_offset`).
2. **Al-Faqih openers lean on the earlier report** («وقال عليه السلام», «وقضى عليه السلام», «وسئل: عن», an asker with a pronoun, a bare «وعن X»): the Imam or the chain is taken from the previous report as `inherited`, citing it; held when none is found. Prompt section Previous reports;
   `build_context_v3_1.cjs` walks back; the hold is `back_reference_without_previous_report` / `back_reference_only` with the widened opening test (`holds_v3_1.inherits_from_previous`).
3. Kept: the person whose words are relayed is the last link; a person only in the scene, whose action is described, at whose place it was heard, or who comments, is not; the compiler heads every chain (the tool adds him); the Prophet ends the chain; a second isnad counts only for the same saying.
4. Still not ruled, so `needs_ruling` and only these: «قضى أمير المؤمنين … في» with no transmitter; the author of a cited book; a narrated encounter where the Imam speaks and acts; two sayings with a second isnad; «ورواه X عن Y فلم يرفعه»; «روي عن الأئمة»; a first-person narrative with implicit transmission;
   the Prophet as the speaker of a one-sentence report with no transmitter. Prompt rule 11. The tool does not hold on them (no deterministic cue): the reader's flag, when both passes set it, is the guard; `retriage.json` lists the 6 judged eligible readings that turn on one (`withheld_judged_undecided_or_unruled`) and keeps them out of `eligible_to_apply.txt`.

## previous reports: the walk and `supplies`
`backref_lib_v3_1.walkBack(list, index, readerText, limit, widened)` stops at the nearest earlier report that writes its chain, and, when `widened`, at one whose opening NAMES the speaker (`SPEAKER_NAMED`: «قال / قضى / سأل / كتب / روي / سئل» followed by a word that is not a pronoun, a honorific, «ان», the Prophet,
an attached «و» or «قلت»). `widened` applies to Imami reports opening as `bare_an`, `asker_pronoun` or `implicit_speaker` only: a Sunni report's earlier report that begins «قال رسول الله» is not a speaker to inherit. The stopping report carries `supplies: "chain" | "speaker"` (`has_written_chain: true` for both, so v3's validators and holds read it
unchanged); a speaker report's `chain_text` is its first 320 letters, so the Imam's name is inside it and the validator can check an `inherited` surface against it. Every intermediate is carried, the limit is 12. The private reports file lists each previous report's hadith id (`previous_reports`), for the submission's `inherited_from`.
Measured on the 44 reports of batch 001 with such openings plus the pronoun and isnad-phrase ones: 24 needed a previous report, 21 found one (9 by a named speaker). Over the 9,784 reports of the tranches: 242 needed one, 205 found one (58 by a speaker), 7 are flagged `needs_previous_report`.

## fold
`norm_v3_1.link_key` adds: a case-ending alif on the last word (four letters or more: «جابرا» = «جابر», «الرضا» = «الرض» on both sides), the dual nisba («المصريان»), an Imam's laqab alone for «أبو الحسن الرضا» (no «بن» in the name; «علي بن موسى الرضا» stays full), «لل» for «ال» after an attached «ل». `expand_v3_1.canonical()` also drops a CLOSING
back reference to the isnad («بهذا / في هذا الإسناد») as `score.py` already does. `expand_v3_1.TextViews.locate` tries as written, folded, and folded with the words allowed to touch («بنجعفر», «أبو الحسنموسى»: a typo or a zero-width character where the text lost its space), and `(?:ال|لل)` for the first word («للرضا»);
the surface returned is the text's own characters. Not folded: a reader's correction of a text typo («أبي طالب» for «بيطالب»: 6e0cb4 A stays invalid), and a restated name that is longer than the first («سبيعة بنت الحارث الأسلمية»).

## empty readings
An empty reading is `status: read` with `groups: []`: "this report has no isnad". `holds_v3_1.empty_reading_state` decides: a transmission word followed by a name before the saying holds it; an asker / inherited-speaker / «وعن» / first-person opening or a name after a speech word holds it as unsettled (v3.1 reads those as links);
otherwise it is applicable and `triage_v3_1` marks it `applies: no_chain`. The saying region is the text before the first quote or colon (200 letters at most): the saying itself is not scanned, so a name inside the matn never holds an empty reading. The detectors were written against the 57 empties of batch 001 (in-sample).

## submission (built 2026-11-22 by the pipeline owner: `reviews/ai/AGENTS.md` §Chain fixes; `to_submission_v3_1.py --only --reader-prompt v3` built batch 001's envelopes)
- `to_submission_v3_1.py` writes `packet-NNN.envelope.json` as v3 does, plus per fix `inherited_from: [{ref, previous_report_id, supplies, surfaces}]` for a reading that takes names from a previous report; `output` is the v1-shaped copy, `null` when no route has a written link (the v3 reading in `reader_output_v3` is what the engine reads).
- NEW `packet-NNN.no_chain.envelope.json`, `format: shura-chain-no-chain-envelope/1`: each fix `{output (the empty reading), disposition: "no_chain_by_reading", reason, evidence: [{quote}], stored_chain_surfaces, external_citation: null}`. The pipeline must: retire the stored chain (non-destructively, as every override), record on the report that it has no chain by reading
  with the run provenance, and treat the two passes as the agreement as for a chain. All of it is now in the pipeline (`../tranches/RUN.md` section 0); the envelope's `run.tool_version` (`v3_1`) names this tool, `run.prompt_sha256` the prompt the reader ran.

## prompt
`tools/chain_body_v3_1.md` + v1's tradition conventions + examples, built by `tools/make_prompt_v3_1.py`, which fails the build when an example does not validate against its real text, a quoted Arabic fragment is not in its pilot report, one of eight full pilot readings does not validate and expand as its rule says, or the prompt is longer than `v3/prompt-v3.md` (27,328 letters).
The v3 examples 2 (al-Kafi co-transmitters), 6 (`عنه` with a shared tail) and 7 (a filed fix) were dropped to make room; the rules they taught (2, 3, Fixes) stay in the text. Four examples are real batch-001 reports in `examples/example-packets.jsonl` with the contexts the v3.1 builder wrote: 4cbe02 (the named asker), 05f29e (a pronoun asker, the Imam inherited from a chain),
38f586 (an inherited speaker), 2c405e (no isnad). `prompt-v3_1.json` records version 3.1.0, sha256, length and the build checks.

## deferred
- Reading the three tranche-1 judge samples against the in-sample detectors (`empty_reading_*`, `asker_not_a_link`, the `routes_end` exemption): trigger, the first tranche's `judge/`.
- A hold for the points still unruled (item 4): no cue is cheap enough; trigger, a ruling.
- 37 of the 242 tranche reports that need a previous report find none within 12 (held `back_reference_without_previous_report`); the Kitab al-Mumin / Sahifat al-Rida / al-Shafi'i shapes where the chain is elsewhere by design are not changed (v3/README.md section 3).
- The prompt has not been run: the only evidence for it is the examples' validation and the v3 outputs re-triaged. The first tranche is the first run.
