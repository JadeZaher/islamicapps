---
type: reference
---
# context/: design notes

Operating instructions: `README.md`. Code carries one-line docs and points here.

## packets
- Independence. Chain readers A and B never see the stored chain, our candidate identities, or anything keyed to our mentions (`external_mention_claims`,
  `chain_mention_candidates`): source claims are read RAW from K6's index, hadith-kg and Riwayat, so agreement between readers means two readings of the text.
  I agree with the owner on this and add three caveats. (1) `archive_flags` are derived from the stored chain's shape (not its names); they say where to look.
  Kept by default because the owner asked for them; run B without them (`--no-archive-flags`) to measure the lean. (2) `name_facts` are for names a *source* placed, not our stored names.
  (3) The reconciling reader gets the stored chain as one reading among three, described as a rule-built reading with a known defect rate, in randomised order, from a different model
  or temperature than A/B; showing it to A/B would turn agreement into agreement with the stored chain.
- Back-reference reports: the gate in `build_context.cjs` (`opensWithBackReference`, folded text, so diacritics and hamza spellings do not defeat it) supplies up to three previous reports.
  A short remainder with no previous report sets `needs_previous_report`; the validator rejects a short reading for such a packet. A full chain after the opening is readable but held (`holds.py`).
- Previous report order: the number printed before the text (it repeats in `hadith_no`), else `hadith_no_int`.
- Name facts for Sunni reports come through the K6 id only; hadith-kg's `tabaka` (1-38) and Riwayat's `tabaqa` are labelled with their scales, never merged.
- No process is left running; the builder opens two SQLite files read-only and immutable and a read-only Postgres session.

## output format (v2) and the tool
- The reader writes levels and groups, no offsets (the analysis: offset failures cost 12 points of agreement; a no-link-after-`matn_start` check contradicted the source-in-saying rule).
  `expand.py` finds surfaces (diacritics ignored, a comma inside a name tolerated, `occurrence` for repeats), expands levels to routes, adds the compiler head by work, sets `matn_start`.
  Two equivalent readings compare equal through `canonical()`. A reading above 400 expanded routes is refused (`too_many_routes`).
- `ends_at` of the first v2 draft was dropped (nothing asked for it downstream; the Prophet rule stays a prompt rule). `compiler_head` is a tool kind, not a reader kind.
- `fixes` are proposals filed for review; the validator only checks that quotes are real (exact substring of the text or of the named context item, letters-only fold), that online claims carry a URL, and that
  `differs` comes with a fix of the right kind. It never judges the reading.

## text and metadata
- Differences are computed by the builder, not by the model: normalised equality, word-spacing-only, containment either way, or the first differing spans. The model only decides what to file.
- Numbering schemes legitimately differ (Muslim 2945 against 2097); the prompt forbids `wrong_number` without an online quote or a conflict inside one scheme.

## deferred
- Rijal-layer facts and lexicon teacher/student lists (trigger: reviewed `narrator_same_as` links for the pilot's Imami narrators).
- Pure Canon xlsx re-read and K6 original rows from `archive/datasets.7z` as extra local copies (trigger: a parser for either).
- A hold for a second-isnad marker after the matn when the reading has one group (trigger: the v2 pilot shows it is still missed).
- Fresh labelled sample for the back-reference gate: the analysis chose it after seeing the errors (in-sample).
