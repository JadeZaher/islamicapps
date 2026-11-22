---
type: reference
---
# Holds: why a reading is queued, not applied

For the fix pipeline's decide step (`docs/review/chain-fix-pipeline.md`; not edited here). `context/holds.py` computes the holds
from a reading the tool has expanded (`context/expand.py`); the reader never sees them. A hold **never changes a reading and never
discards one**: the report goes to the review queue with its codes. A reading with no hold is only *eligible* for the ordinary
decide step; nothing here auto-applies anything, and the analysis (`analysis/README.md` §3) shows two agreeing Haiku readings are
not yet better than the stored chains.

```python
holds = compute_holds(reading, output, text, context, stored_surfaces)   # [{"code", "detail"}]
```

`stored_surfaces` (the archive's stored chain, as strings) is used only here; the reader may not see it.

| code | when | why (evidence in `analysis/`) | tuning |
|---|---|---|---|
| `drops_stored_name` | a stored name whose words (attached «و» allowed) stand in the text is in no link of the reading (name equal, or one a contiguous word run of the other) | cr-0010: the reading lost a name the text writes; the stored chain kept it | none |
| `reading_empty_stored_has_links` | the reading has no link and the stored chain has | analysis §6.6 | none |
| `too_many_routes` | more than 8 routes after expansion (expansion above 400 is refused with the same name) | cr-0059 had 18 routes, truncated differently by two passes | limit `MAX_ROUTES` |
| `nested_jami` | two or more «جميعا» / «كلهم» in the chain region (text before the last non-Imam link), or one together with a «؛» | nested convergence was not read right in any of 5 audited reports (cr-0032, 0065, 0143, 0219, 0187) | heuristic by count; refine when the reader returns nested groups |
| `nested_semicolon` | two or more «؛» / «;» in the chain region (several isnads joined by semicolons) | same five reports | as above |
| `back_reference_without_previous_report` | the text opens with «وبهذا الإسناد», «بهذا الإسناد», «بالإسناد الأول», «عنه», «عن», «وعن» (after a number), or says «بهذا الإسناد» in its first 160 letters, and the packet carries no `previous_reports` / `parent_report` | the main Imami failure: 6 inherited-chain readings, each replacing a long stored chain by a short one | opening list `OPENING` in `holds.py` and `opensWithBackReference` in `build_context.cjs` |
| `cannot_read_without_previous_report` | the reader answered that status (the packet was flagged `needs_previous_report`) | by design | none |
| `needs_ruling` | the reader set `needs_ruling`: subject-or-source of an event, a title («الإمام»), a placement the rulings do not settle | cr-0015, 0027, 0237, 0137, 0139 | owner policy ends the hold per case type |

Not a hold (handled elsewhere): an output that fails `validate_v2.py` or whose surface the tool cannot find (`expand` returns the error:
`surface_not_in_text`, `occurrence`, `order`, `too_many_routes`) is an invalid output, not a reading.

Operating notes for the decide step:

- Hold codes are stable strings; store them with the queued fix. A report with several holds lists all.
- Agreement between two readers is `expand.canonical()` equality (the set of routes of folded surfaces, derived links dropped): `[[A,B],[C]]`
  and two groups `A→C`, `B→C` compare equal.
- Not yet held, seen in the analysis, recorded for later: a second-isnad marker after the matn («وحدثنيه», «ح», «رواه») where the reading has one group (analysis §6.6).
  The reader is now told a second isnad is a route, so the hold waits for evidence that it is still missed.
