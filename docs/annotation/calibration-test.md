# Calibration Test

**Before you contribute real annotations, you must complete this one-time skills check.**
It takes about 30–60 minutes and ensures you and the annotation guide are on the same page.

---

## §1 — What the calibration test is

The calibration test is five hadith texts with taḥwīl — the standard chain-switch marker **ح** — where
the branch structure has been deliberately hidden. You annotate them exactly as you would during real
annotation work, then run a scorer that tells you how closely your answers match the hidden answer key.

There are no trick questions. Every hadith in the test appears in `tahweel-annotation-guide.md` §3 as a
worked example, or is a close variant. If you have read the guide carefully, this should feel like a
confirmation, not a surprise.

The threshold to contribute real annotations is a score of **0.85 or higher** (out of 1.0).
Annotators who score 0.95 or above are not required to re-take the calibration when the guide is updated.

---

## §2 — How to take the test

1. **Make your own working copy** of `calibration-test.jsonl`:
   ```
   cp calibration-test.jsonl <your-name>-calibration.jsonl
   ```
   Replace `<your-name>` with your initials or username (e.g. `jz-calibration.jsonl`).
   Do not annotate `calibration-test.jsonl` directly — your working copy is what the scorer reads.

2. **Open the file** in any text editor that handles UTF-8: VS Code, Notepad++, Sublime Text, or similar.
   Each line is one JSON object representing one hadith. The Arabic text is in `text_ar`.

3. **For each row, fill in the following fields:**

   - `expected_branches` — A JSON array of arrays. Each inner array is one branch of the isnād,
     listed in chain order from compiler-transmitter down to the Companion or endpoint.
     Example: `[["قتيبة بن سعيد", "أبو عوانة", "سماك بن حرب"], ["هناد", "وكيع", "إسرائيل"]]`
     Use the surface form exactly as it appears in `text_ar` — do not resolve kunya to proper names.

   - `notes` — Brief free-text note about anything unusual: naming variants, convergence point,
     ambiguous co-transmitters. A sentence or two is enough; leave blank if nothing to flag.

   - `annotator` — Your initials or username (e.g. `jz`, `sara.m`).

   - `annotated_at` — ISO-8601 timestamp in UTC, e.g. `2026-06-14T15:30:00Z`.

   - `difficulty` — Your subjective rating of this hadith's difficulty, from 1 (straightforward) to 5 (very complex).

4. **Save the file** in UTF-8 encoding (VS Code does this by default).

5. **Run the scorer:**
   ```
   python score_calibration.py --submission <your-name>-calibration.jsonl
   ```
   Run this from the `datasets/hadith-data/__tests__/fixtures/` directory,
   or provide full paths.

6. The scorer prints your **aggregate score** and a **per-row breakdown** showing where you matched
   the answer key and where you diverged.

---

## §3 — How the scoring works

For each hadith, the scorer compares your `expected_branches` to the hidden answer key, branch by branch.

For each branch pair (your Branch A vs the gold Branch A, your Branch B vs the gold Branch B, and so on),
it counts how many narrator surface forms you matched and divides by the total unique names across
your branch and the gold's branch combined. A perfect branch match is 1.0; a completely wrong branch is 0.0.

Your score for a row is the average across all branches in that hadith.
Your aggregate score is the average across all five rows.

The scorer uses Arabic text normalization — diacritics are stripped and alef variants are unified before
comparison — so minor vocalization differences do not count against you. However, Latin transliterations
(e.g. writing "Sufyan" instead of "سفيان") will not match and will lower your score.

**In plain terms:** you matched X% of the gold's narrators per branch on average.

---

## §4 — Honor rule

`.calibration-gold.jsonl` is the answer key. It is a dotfile in this directory.
**Do not open it before submitting your work.** Reading the answer key before scoring defeats the entire
purpose of the test and corrupts your calibration data.

If you want to study worked examples, use §3 of `tahweel-annotation-guide.md` — those examples are
public and exist precisely for preparation.

---

## §5 — What if I don't pass?

A score below 0.85 is not a judgment on your scholarship. It means you and the guide are reading
something differently, and it is worth finding out what before you annotate hundreds of hadiths.

1. Re-read the guide, especially §3 (the case types) and §4 (the decision tree).
2. Look at the per-row breakdown the scorer printed — pay attention to the rows with the lowest scores.
3. Re-take the test with a new working file (`<your-name>-calibration-v2.jsonl`).

There is no limit on re-takes.
