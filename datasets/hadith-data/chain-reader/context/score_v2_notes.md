---
type: reference
---
# Scoring v2 outputs fairly

`context/score_v2.py` wraps the unchanged `score.py`. What it does, and why:

1. **Expand first.** v2 outputs are levels and groups without offsets; `expand.py` finds every surface in the text (diacritics ignored, a comma
   between the words of a name tolerated), expands to routes, sets `matn_start` after the last ordinary link, and only then does the v1 scorer see the
   reading. Offset failures no longer exist; a surface the tool cannot find (`surface_not_in_text`, `occurrence`, `order`) is an invalid output and is
   listed as such.
2. **Drop what stored chains cannot hold.** `compiler_head` (added by the tool) and `inherited` links are dropped; a route made only of dropped links vanishes.
   Otherwise every stored chain lacking the compiler or taken from the previous report would be a miss.
3. **`imam_in_text`**: `--imam drop` (default) removes it, since stored chains were built before the ruling; `--imam keep` turns it into a narrator so
   a stored chain that does hold the Imam compares equal. Report both: they answer different questions (reading quality against ruling coverage).
4. **The attached-«و» artifact (analysis §4: 13 correct readings scored as misses).** `score.py` drops a stored name from its reduced route when the text
   writes it with an attached «و» («وأحمد بن عبدة»), so the reader's right name looked like an extra. `score_v2.py` replaces `score.surface_in_text` by a
   version that also accepts the attached «و», in memory, and runs the scorer **twice**: `<out>` (corrected, the figure to read) and `<out>-v1wa`
   (v1's behaviour, for comparison with the text-only pilot). Report both columns.
5. **Same 284 reports, minus declared exclusions.** `--exclude pilot-v2/exclude_prompt_fragments.txt` leaves out the five pilot reports quoted as rule
   fragments in the v2 prompt (cr-0029, 0090, 0138, 0237, 0258). `pilot-v2/owner_ruling_or_cannot_tell.tsv` lists the reports the analysis judged
   `cannot_tell` or whose nested/inherited structure needs a ruling: score them separately or exclude them; the list gives the v2 packet state for each.
6. **Holds.** With `--packets pilot-v2/packets` the holds of every reading are written to `<out>-holds.tsv` (columns: id, expand error, hold codes), so
   agreement can be reported with and without held reports.
7. **What `score.py` still cannot say.** It compares with the stored chain, which is wrong for about a third of the pilot; the analysis (`analysis/`) is the
   human measure. Agreement between two runs should use `expand.canonical()` (set of routes, folded) rather than the v1 byte comparison.

Not changed: `score.py`, `norm.py`, `validate.py`, `prompt.md`, `outputs/`, `pilot/`.
