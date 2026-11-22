# v3_4/: design notes

Operating instructions and numbers: `README.md`. Code carries one-line docs and points here. Nothing in this directory runs a model or writes a database.
`v3/`, `v3_1/`, `v3_2/`, `v3_3/`, `tranches/` are read-only from here; module names are distinct (`*_v3_4`) so they import side by side. Python writes use `newline="\n"`.

## base
v3.4 wraps instead of copying: `expand_v3_4` imports `expand_v3_2` (v3.3 has no expansion of its own and imports it unchanged), `holds_v3_4` imports `holds_v3_3` (fallback `holds_v3_2`).
A copy would freeze whatever v3.3 looked like at copy time while its tool agent was still editing it; a wrapper adds only the saying layer and a later v3.3 change flows in, with the tests as
the guard. The cost: a breaking change in a base module breaks v3.4 too (that is the point of the tests).

## sayings
Owner ruling (b): two sayings, each with its own isnad, are both stored, each route labelled with its saying. The label lives on the GROUP (`saying`, `saying_opens`), not on items: a group
is already "one family of routes", and the reader decides sayings per isnad, not per name.
- `saying_opens` is text, not a number: a model cannot count characters, but it can copy words, and the page needs words to show («Chain of the second saying: «أنها لم تكن تفعل ذلك»…»).
  It is located like a surface (fold-tolerant) after the saying's last link, then after its first link, then anywhere: an opening placed at the start of a story still validates (with a note).
- `shared_tail` must be null when labelled: a tail written once would otherwise attach to every group, across sayings. A later saying writes the names it shares (as «قال وحدثني X» keeps the head).
- A single labelled saying is allowed (db16ed-like reports where only the second saying has an isnad): the label then says which saying the chain carries.
- Agreement is per saying: two readers who split the same routes differently into sayings do not agree (the page label would depend on which pass is applied).

## holds
The shape holds compare routes of one report on the assumption that they carry one saying and so should share a head or a tail. Routes of different sayings need not, so the
SHAPE_CODES run per saying (sub-reading with its own `matn_start`); everything else (variant, mutabaʿa, poem cue, Imami, previous-report and needs-ruling holds) runs on the whole reading,
which is the conservative side. Per-saying checking loses one real check, a later saying that drops the shared head («قال بكير وحدثني»), so `saying_route_starts_inside_another_route` restores
exactly that: a later saying's route whose first name stands inside an earlier saying's chain.
`two_sayings_not_supported` is the same device as v3.2's `has_variant_group`: it holds what the pipeline cannot yet store, and `--sayings-supported` lifts it in triage only.

## prompt
Same generator approach as v3.2 (the v3.2 generator is imported for its helpers and pilot checks); budget = v3.2's length, so new rules forced examples out. The dropped ones are the
classes the tranche-02 judge found fixed in both passes; their rules keep their quotes. Example 1 shows only its work (its previous report taught nothing the inherited example 6 does not).

## re-read
Packets reuse the source packet line's `text` and `context` verbatim: a rebuilt context would be a different input and the re-read would not be comparable with the first read.
Opaque ids `r4-` + salted sha256 (salt only in `private/`), order an md5 shuffle, so a reader cannot tell the source, the reason or the earlier reading from a packet.

## jobs
`make_jobs_v3_4.py` converts `jobs.json` (whatever prompt it names) into a NEW `jobs-v3_4.json`; it refuses a tranche that has outputs (reading half a tranche under one prompt and half under
another would make its triage meaningless) unless `--force`.
