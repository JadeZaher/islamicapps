---
type: proposal
---
# Format gap: a connecting chain written AFTER the names it connects to

For the owner of the reader toolchain (`v3_2/expand_v3_2.py`, `v3_4/expand_v3_4.py`, `validate_v3_4.py`, `holds_*`, `to_submission_*`, `chain_fix_engine.py`). Nothing of theirs was edited; the proposal runs in `reviewer/out_of_order_validator.py` only.

## The case (pilot item cr1-750b73, found by the adjudication)

Text: «وروى عبد الرحمن بن مهدي، عن عكرمة بن عمار، نحو رواية ابن المبارك … **حدثنا بذلك إسحاق بن منصور حدثنا عبد الرحمن بن مهدي**». The compiler states an isnad (Ibn Mahdi from Ikrima) without hearing it
himself, then closes with the chain that connects him to it. The right route is Ishaq, Ibn Mahdi, Ikrima. In route order the last name (Ikrima) stands EARLIER in the text than the names before it,
and the reader format requires levels in text order: `expand_v3_2._locate` looks for each level after the previous one's end and fails with `order: g0l2i0 'عكرمة بن عمار' occurs only before the previous level`.
Both readers wrote two routes instead (compiler, Ibn Mahdi, Ikrima; and compiler, Ishaq, Ibn Mahdi), the first of which the text never states: the compiler does not hear from Ibn Mahdi. The reviewer wrote the right route and the
validator refused it, which voided its whole packet in the pilot (now per item, `README-v1_1.md` §1).

## The smallest extension

Two opt-in keys, nothing else changes:

```json
{"levels": [[{"surface": "إسحاق بن منصور", "kind": "narrator"}],
            [{"surface": "عبد الرحمن بن مهدي", "kind": "narrator", "occurrence": 2}],
            [{"surface": "عكرمة بن عمار", "kind": "narrator", "out_of_order": true}]],
 "connecting_span": "حدثنا بذلك إسحاق بن منصور حدثنا عبد الرحمن بن مهدي"}
```

- `out_of_order: true` on every item of ONE level (never the first): that level, and the levels after it, are written BEFORE the connecting span, in text order among themselves.
- `connecting_span` on that group: the exact words of the text that connect to the flagged level. Every level before the flagged one is written INSIDE it.
- Why a span and not only a flag: the flag alone would let any reordering through (the same worry `chain-reader/AGENTS.md` records for tail links). The span makes it checkable: the earlier names must end before it,
  the connecting names must lie inside it, and the span must be an exact substring. A flag on the first level, on several levels, on a variant group, on a partly flagged level, a span with no flag, a flag with no span,
  a span not in the text, a span that does not contain the connecting names: each is refused (`out_of_order_validator.shape_errors`, `expand`).

Implementation (`out_of_order_validator.py`, about 100 lines, reusing `expand_v3_4` and `validate_v3_4` unchanged): the output is rewritten into text order (flagged levels first, keys removed), validated and
expanded by the existing tool, the span and the offsets are checked, and each route of that group is put back in route order. Routes keep the located links; the earlier-written links carry `out_of_order: true`
and the route carries `connecting_span`. Unflagged outputs go straight to `validate_v3_4`, byte for byte as today. Tested on cr1-750b73 (`tests/test_reviewer_v1_1.py::FormatGap`): v3.4 refuses the pilot's reading; the
flagged reading expands to `الترمذي (compiler_head) > إسحاق بن منصور > عبد الرحمن بن مهدي > عكرمة بن عمار*` (`*` out of order); five misdeclared variants are refused; the reviewer validator takes it only with `--allow-out-of-order`.

## What the toolchain owner must change to adopt it

| where | change |
|---|---|
| `v3_2/expand_v3_2.py` (`ITEM_KEYS`, `GROUP_KEYS`, `check_shape`, `expand`) | accept `out_of_order` and `connecting_span`; locate flagged levels before the span; keep route order; put `out_of_order: True` on those links and `connecting_span` on the route. Wrap rather than copy, as v3_4 does (`expand_v3_4` imports v3_2): a `v3_5` layer, or this file's proxy-and-reorder as is |
| `v3_4/validate_v3_4.py` | call the shape errors above; unchanged for unflagged outputs |
| every consumer of link offsets | **links of one route are no longer monotone**: `matn_start = max(end)` still holds (the span is last), but `holds_v3_*` shape and `remark_span` checks, `collapse_repeats` (the same man twice in succession), the stored-chain comparison in `score.py`, and any code assuming `link[i].end <= link[i+1].start` must skip links with `out_of_order` |
| `canonical()` / `readings_agree` | no change: route keys are names in route order; a reader who writes the same route with the flag agrees with one who does not (it never has to) |
| `to_submission_v3_*`, `chain_fix_engine.py` | the planned mention's `span` is the link's own offsets (already per link); add `connecting_span` to the fix's notes; nothing else if spans are only displayed |
| reader prompt (v3.5) | one rule and one example (this item). Until then the readers cannot write it, so they split it into two routes: expect this class to stay a disagreement or a hold |
| reviewer prompt (v1.2) | replace the v1.1 line "refer, and give the route in words" by the format. Until then `refer_to_human` with `question` beginning "format: connecting chain after the names" |

## Deferred, with the trigger

- Several out-of-order boundaries in one group, and an out-of-order shared tail: not needed by the one observed case; add when a second shape appears.
- How common the class is: not counted. A search for «حدثنا بذلك» after the last written link, over the tranches' texts, would size it (trigger: the owner wants the reader prompt changed).
