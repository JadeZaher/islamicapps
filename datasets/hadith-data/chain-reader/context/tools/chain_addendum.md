## Context (version 2)

`context` is evidence that comes with the report. It is separate from `text`. Every item names its `source`: K6I (the K6
dataset's narrator index), HKG (hadith-kg), RWY (Riwayat corpus), THQ (Thaqalayn), NMC (Pure Canon), OITI (OpenITI),
MSD (the narrator lexicon), SUN (sunnah.com), SWI (this archive's own rules).

- The `text` is the authority for what is WRITTEN. Every link must be an exact substring of `text` (with offsets), except the
  derived kinds below.
- `work`: the work, its compiler, the book and chapter, and how the work usually writes chains.
- `source_claims`: what other datasets say this report's chain is, as they wrote it. They are CLAIMS, not answers, and are
  often wrong or partial: K6I lists the lexicon's name for each id (not the written words) and does not separate routes; RWY
  is a machine reading and may take a phrase for a name; THQ's English may give only the first link. When `sources_agree`
  says they differ, believe the text, not the majority.
- `name_facts`: death year, generation and place that a source gives for a name it placed in the chain. Use them only to
  notice an impossible reading (a man who died before his teacher was born); never to decide who someone is, and never to
  merge or split names.
- `previous_reports` and `parent_report`: the chain of the report(s) before this one. Needed only when this report opens
  with a back-reference («عنه», «بهذا الإسناد») or in the middle of a chain.
- `correspondences`: the same saying in other works, with the chain written there. Evidence of how a chain may run, not a
  reading of this text.
- `archive_flags`: where the archive's own rules were unsure. A hint about where to look, never a hint about what is right.
- Do not use anything in `context` to add a name the text does not write, except through the derived kinds.

## Derived links and the owner's rulings (version 2)

Four rulings (2026-11-22). Three extra link kinds carry them; two have no offsets.

1. **The compiler heads every chain of his work.** If `context.work.compiler.head_of_every_chain` is true, the FIRST link of
   every route is `{"surface": <context.work.compiler.ar, copied exactly>, "start": null, "end": null, "kind": "compiler_head",
   "from": "work"}`. Do not look for him in the text. If the text itself already writes the compiler as a link (a Muwatta chain
   field naming Malik), that written link stands and you add no `compiler_head`. If the flag is false, add none.
   (This replaces v1's "the compiler is never a link".)
2. **The Imam named only in the words after the chain is the chain's last link.** Imami reports only. «قال سألت أبا عبد الله»,
   «سمعت أبا جعفر يقول», al-Faqih's «وقال الصادق (عليه السلام)»: the Imam is the last link of the route, kind `imam_in_text`,
   the surface copied from the text with its offsets (it may lie at or after `matn_start`: this kind is exempt from rule 7's
   "no link in the matn"), written as the report names him, never completed. An Imam written inside the chain after «عن» stays
   `narrator`. A Companion named in a Sunni saying stays `narrator` (rule 2).
3. **A bare kunya is never identified by you.** Write it as written («أبي عبد الله»); say nothing about who he is.
4. **The Prophet is the end of a chain, not a link.** Never a link. Set the route's `ends_at` to `"prophet"` when the text
   attributes the saying to him, otherwise `"other"`.
5. **`inherited`**: when the report's chain is «بهذا الإسناد» or «وبإسناده» and `previous_reports` (or `parent_report`) carries
   that chain as one simple route, you may write the names of that chain that this report takes over as links
   `{"surface": <exact words of that item's chain_text>, "start": null, "end": null, "kind": "inherited", "from": "prev1"}`
   (the item's `ref`), in order, before the report's own links; then do not also write the «بهذا الإسناد» back_reference for the
   same phrase. If the previous chain has several routes, or you are unsure how much is taken over, write the back_reference
   link as in version 1 and say so in `notes`.

## Fixes (version 2)

`fixes` is a list (often empty). Each item is a PROPOSAL filed for review; you never apply it and the archive decides:
`{"kind": ..., "reason": "one sentence", "evidence": [{"source": "text" | a source code, "quote": "<exact words>"}], "confidence": "low" | "medium" | "high"}`.
`quote` must be copied exactly from `text` (source `"text"`) or from that source's context item. File a fix when your
reading differs from what a source claims, or when you notice a data problem outside chain structure. Kinds:
`chain_differs_from_source` (your reading differs from a source's), `wrong_identity` (a name a source attached to a position
cannot be the man the text names), `lexicon_date_impossible` (a death year in `name_facts` cannot be right for this chain),
`lexicon_records_look_like_one_person` (two lexicon records in `name_facts` look like one man), `text_garbled` (the Arabic
text is damaged or merged), `translation_contradicts_arabic` (the English sanad contradicts the Arabic), `data_problem_other`.
Do not file a fix for a difference you cannot quote on both sides. Never "improve" the stored Arabic: report the words as
they stand and what the other source has.
