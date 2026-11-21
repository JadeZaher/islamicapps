"""Build the fixed OpenITI parse and its diff report. Files only: nothing outside fixed/ is written, no database is touched.

    python -I -X utf8 datasets/hadith-data/extraction-quality/fixed/build_fixed.py

Writes (in this directory): parsed_hadiths.fixed.json, diff_report.md, diff_summary.json, checks_before_after.json.
Reads: the OpenITI sources, ../output/production_snapshot.jsonl.gz (read-only copy of the production rows), ../output/summary.json.
See AGENTS.md in this directory for the extraction model.
"""
from __future__ import annotations

import collections
import gzip
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
EQ_DIR = os.path.dirname(HERE)
DATASETS = os.path.dirname(os.path.dirname(EQ_DIR))
sys.path.insert(0, DATASETS)
sys.path.insert(0, EQ_DIR)
sys.path.insert(0, HERE)
import parse_openiti as po  # noqa: E402
import check_fixed  # noqa: E402

SOURCES = {
    "rabi": os.path.join(po.OPENITI_DIR, "rabi", "jamic_sahih_ibadiyya.txt"),
    "zayd": os.path.join(po.OPENITI_DIR, "zayd", "musnad_zaydiyya_052.mARkdown"),
    "rida": os.path.join(po.OPENITI_DIR, "zayd", "musnad_zaydiyya_052.mARkdown"),
}
PARSERS = {"rabi": po.parse_rabi, "zayd": po.parse_zayd, "rida": po.parse_rida_appendix}
EXAMPLES = ["rabi_0001", "rabi_0001b", "rabi_0140", "rabi_0335", "rabi_0880", "rabi_0881", "rabi_0225", "zayd_0026", "zayd_0007",
            "zayd_0022", "zayd_0429", "rida_0032"]


def source_record_id(record):
    return f"{record['id']}|{record['hadith_no']}|{record['page_ref']}"


def load_snapshot():
    path = os.path.join(EQ_DIR, "output", "production_snapshot.jsonl.gz")
    rows = {}
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            row["work"] = row["source_record_id"].split("|")[0].split("_")[0]
            rows[row["source_record_id"]] = row
    return rows


def classify_change(before: str, after: str) -> str:
    a, b = po.strip_edition_markers(before), after
    if before == after:
        return "unchanged"
    if a == b:
        return "markup_only"
    if a.startswith(b):
        return "tail_removed"
    if b.startswith(a):
        return "extended"
    if b.endswith(a):
        return "prefix_added"
    if a in b:
        return "extended_both_sides"
    return "other"


def shorten(text, head=170, tail=110):
    text = text or ""
    return text if len(text) <= head + tail + 5 else f"{text[:head]} … {text[-tail:]}"


def main():
    parsed = {work: PARSERS[work](SOURCES[work]) for work in ("rabi", "zayd", "rida")}
    generated = datetime.now(timezone.utc).isoformat()
    fixed_path = os.path.join(HERE, "parsed_hadiths.fixed.json")
    with open(fixed_path, "w", encoding="utf-8") as handle:
        json.dump({"generated_utc": generated, "parser": "datasets/parse_openiti.py", "note": "Not wired into any live path; see LOAD_STEPS.md",
                   "works": parsed}, handle, ensure_ascii=False, indent=1)

    snapshot = load_snapshot()
    summary, lines = {}, []
    for work in ("rabi", "zayd", "rida"):
        records = parsed[work]["hadiths"]
        by_srid = {source_record_id(r): r for r in records}
        prod = {k: v for k, v in snapshot.items() if v["work"] == work}
        absorbed = {a: r["id"] for r in records for a in r["absorbed_ids"]}
        preserved = [k for k in prod if k in by_srid]
        disappeared = []
        for key in sorted(set(prod) - set(by_srid)):
            short = key.split("|")[0]
            disappeared.append({"source_record_id": key, "reason": f"absorbed into {absorbed[short]}" if short in absorbed else "unexplained"})
        categories, detail = collections.Counter(), collections.defaultdict(list)
        for key in preserved:
            category = classify_change(prod[key]["text_ar"], by_srid[key]["text_ar"])
            categories[category] += 1
            detail[category].append(by_srid[key]["id"])
        new_keys = [k for k in by_srid if k not in prod]
        split_children = [k for k in new_keys if "#" in k.split("|")[0]]
        recovered = [k for k in new_keys if "#" not in k.split("|")[0]]
        parents_with_children = {r["split_from"] for r in records if r["split_from"]}
        low = [r["id"] for r in records if r["split_confidence"] == "low"]
        kinds = collections.Counter(k for r in records for k in r["commentary_kinds"])
        stream = " ".join(
            [r["text_ar"] for r in records] + [c for r in records for c in r["commentary"]] + [f for r in records for f in r["footnotes"]]
            + [u["text"] for u in parsed[work].get("unassigned_blocks", [])] + [d["text"] for d in parsed[work].get("dropped_chunks", [])])
        stream = po.collapse_ws(stream)
        missed_path = os.path.join(EQ_DIR, "output", "missed_source_reports.jsonl.gz")
        missed = collections.Counter()
        with gzip.open(missed_path, "rt", encoding="utf-8") as handle:
            for line in handle:
                item = json.loads(line)
                if item["work"] != work or item["reason"] in ("biographical_introduction", "preamble"):
                    continue
                text = po.collapse_ws(po.strip_edition_markers(po.normalise_block(item.get("text", ""))))
                missed[(item["reason"], "now_in_output" if text and text in stream else "still_absent")] += 1
        summary[work] = {
            "records_before": len(prod), "records_after": len(records), "production_source_record_ids_preserved": len(preserved),
            "disappeared": disappeared, "text_changes": dict(categories), "text_unchanged": categories["unchanged"],
            "text_changed": sum(v for k, v in categories.items() if k != "unchanged"),
            "new_ids_split_children": len(split_children), "split_parent_records": len(parents_with_children),
            "newly_recovered_ids": [k.split("|")[0] for k in recovered],
            "records_that_absorbed_a_fragment": sum(1 for r in records if r["absorbed_ids"]),
            "absorbed_ids": sorted(absorbed), "records_with_carried_prefix": sum(1 for r in records if r["prefix_from_id"]),
            "low_confidence_splits": len(low), "high_confidence_splits": len(records) - len(low),
            "continuation_chains_with_inherits": sum(1 for r in records if r["sanad_inherits_from"]),
            "records_with_footnotes": sum(1 for r in records if r["footnotes"]),
            "footnote_marker_only_records": sum(1 for r in records if r["footnote_markers_without_text"]),
            "records_with_commentary": sum(1 for r in records if r["commentary"]), "commentary_strings": sum(kinds.values()),
            "commentary_kinds": dict(kinds), "split_kinds": dict(collections.Counter(r["split_kind"] for r in records)),
            "verbatim_strings_checked": parsed[work]["verification"]["strings_checked"],
            "verbatim_failures": parsed[work]["verification"]["failures"],
            "unassigned_blocks": [{"line": u["line"], "chars": len(u["text"])} for u in parsed[work].get("unassigned_blocks", [])],
            "dropped_chunks": parsed[work].get("dropped_chunks", []),
            "audit_missed_source_items": {f"{k[0]}:{k[1]}": v for k, v in sorted(missed.items())},
            "text_change_examples": {k: v[:8] for k, v in detail.items() if k != "unchanged"},
        }

    checks = check_fixed.run(parsed)
    with open(os.path.join(HERE, "checks_before_after.json"), "w", encoding="utf-8") as handle:
        json.dump(checks, handle, ensure_ascii=False, indent=1)
    with open(os.path.join(HERE, "diff_summary.json"), "w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=1)
    write_report(parsed, summary, checks, snapshot, generated)
    print(json.dumps({w: {k: v for k, v in s.items() if k in ("records_before", "records_after", "text_unchanged", "text_changed",
                                                             "new_ids_split_children", "low_confidence_splits", "verbatim_failures")}
                      for w, s in summary.items()}, ensure_ascii=False, indent=1))


def write_report(parsed, summary, checks, snapshot, generated):
    out = ["# Fixed parse vs production: diff report", "",
           f"Generated {generated} by `build_fixed.py` from `datasets/parse_openiti.py` (fixed). Files only: `parsed_hadiths.fixed.json` is a new file; "
           "no live path, database or commit was touched.", ""]
    works = ("rabi", "zayd", "rida")
    row = lambda label, key: f"| {label} | " + " | ".join(str(summary[w][key]) for w in works) + " |"
    out += ["## Counts", "", "| | rabi | zayd | rida |", "|---|---|---|---|",
            row("records before (production)", "records_before"), row("records after (fixed)", "records_after"),
            row("production `source_record_id`s preserved exactly", "production_source_record_ids_preserved"),
            row("text unchanged (byte for byte)", "text_unchanged"), row("text changed", "text_changed"),
            row("new ids from splits (`#2`, `#3`...)", "new_ids_split_children"), row("production records that were split", "split_parent_records"),
            row("records that absorbed another old record (fragment merge or page-break continuation)", "records_that_absorbed_a_fragment"),
            row("records that received a carried chain-opener prefix", "records_with_carried_prefix"),
            row("high-confidence sanad/matn splits", "high_confidence_splits"),
            row("low-confidence splits (`sanad_ar` = `matn_ar` = null)", "low_confidence_splits"),
            row("continuation chains with `sanad_inherits_from`", "continuation_chains_with_inherits"),
            row("records with `footnotes`", "records_with_footnotes"), row("records with `commentary`", "records_with_commentary"),
            row("commentary strings", "commentary_strings"), row("verbatim strings checked", "verbatim_strings_checked"), ""]
    out += ["Newly recovered (ids that were not in production and are not split children): "
            + "; ".join(f"{w}: {', '.join(summary[w]['newly_recovered_ids']) or 'none'}" for w in works), "",
            "Verbatim check: every `text_ar`, `sanad_ar`, `matn_ar`, footnote and commentary string is a substring of the source after the pipeline's "
            "normalisation (NFKC, controls, page and milestone markers, footnote markers) plus the marker strip (`=`, leading `V`, lone `*`), "
            "blocks joined by one space. Failures: " + "; ".join(f"{w}: {len(summary[w]['verbatim_failures'])}" for w in works) + ".", ""]
    out += ["## How the text of preserved records changed", "", "| change | " + " | ".join(works) + " |", "|---|---|---|---|"]
    names = sorted({k for w in works for k in summary[w]["text_changes"]})
    for name in names:
        out.append(f"| {name} | " + " | ".join(str(summary[w]["text_changes"].get(name, 0)) for w in works) + " |")
    out += ["", "`tail_removed` = the production text starts with the new text (footnote block, commentary, heading or the later reports of a split were cut off); "
            "`markup_only` = only `=`/`V`/`*` markers differ; `extended` = text added (merged fragment, restored orphan line); "
            "`prefix_added` = a chain opener carried over from the previous report; `extended_both_sides` / `other` = both.", ""]
    out += ["## Ids that disappear, and why", ""]
    for w in works:
        items = summary[w]["disappeared"]
        out.append(f"- **{w}**: " + (", ".join(f"`{d['source_record_id']}` ({d['reason']})" for d in items) if items else "none"))
    out += ["- **zayd_0118** (`الثياب للصلاة:`, a `~~` line after a bab heading) is a chapter title tail, not a report; it is already absent from production "
            "(the replay saw it, the production load did not), and every later zayd id is unchanged.", ""]
    out += ["## Text no longer attached to any record", ""]
    for w in works:
        blocks = summary[w]["unassigned_blocks"] + [{"line": d["line"], "chars": len(d["text"]), "reason": d["reason"]} for d in summary[w]["dropped_chunks"]]
        out.append(f"- **{w}**: {len(blocks)} blocks: " + (", ".join(f"line {b['line']} ({b['chars']} chars{', ' + b['reason'] if 'reason' in b else ''})" for b in blocks) or "none"))
    out += ["", "Rabi's unassigned blocks are volume front/back matter, empty or orphaned titles, and the unnumbered closing «حديث الشفاعة» "
            "(lines 6582-6632) that the old parser glued onto the last numbered report; they are kept in `parsed_hadiths.fixed.json` under `unassigned_blocks`.", ""]
    out += ["## Source reports the audit listed as missed", "", "| work | item | now in output |", "|---|---|---|"]
    for w in works:
        for key, value in summary[w]["audit_missed_source_items"].items():
            out.append(f"| {w} | {key.split(':')[0]} | {key.split(':')[1]} x {value} |")
    out += ["", "## Audit checks re-run on the fixed parse (records flagged, before -> after)", ""]
    before, after = checks["before"], checks["after"]
    flags = sorted({f for w in works for f in list(before.get(w, {}).get("flags", {})) + list(after[w]["flags"])})
    out += ["| flag | rabi | zayd | rida |", "|---|---|---|---|"]
    for f in flags:
        out.append(f"| {f} | " + " | ".join(f"{before.get(w, {}).get('flags', {}).get(f, 0)} -> {after[w]['flags'].get(f, 0)}" for w in works) + " |")
    out.append("| records | " + " | ".join(f"{before[w]['records']} -> {after[w]['records']}" for w in works) + " |")
    out.append("| clean (no defect flag) | " + " | ".join(f"{before[w]['clean']} -> {after[w]['clean']}" for w in works) + " |")
    out.append("| text-level clean | " + " | ".join(f"{before[w]['text_level_clean']} -> {after[w]['text_level_clean']}" for w in works) + " |")
    out += ["", "Rules are the audit's (`deterministic_checks.py`: `split_chain_matn`, `RE_ZAYD_OPENER`, `RE_ORDINAL_HEADING`, the gloss heuristic) applied to the "
            "fixed records' `text_ar` / `sanad_ar` / `matn_ar`; `commentary_misattributed` and the dropped-source-line `truncated` kind cannot occur any more "
            "(comments are attached to their own record; orphan lines are text). `sanad_latin_not_arabic_span` now counts Latin in `sanad_ar` (the Latin `sanad` "
            "list is the resolver's, not the parser's). Remaining flags, by id, are in `checks_before_after.json` (`after.<work>.flagged`).", ""]
    for w in works:
        remaining = {k: [x["id"] for x in v][:12] for k, v in after[w]["flagged"].items() if k not in ("sanad_matn_split_wrong",)}
        out.append(f"- **{w}** remaining (first 12 ids per flag): " + "; ".join(f"{k}: {', '.join(v)}" for k, v in remaining.items() if v))
    out += ["", "## 12 before / after examples", ""]
    by_id = {}
    for w in works:
        for r in parsed[w]["hadiths"]:
            by_id.setdefault(r["id"], []).append(r)
    prod_by_short = collections.defaultdict(list)
    for key, value in snapshot.items():
        prod_by_short[key.split("|")[0]].append(value)
    for ex in EXAMPLES:
        out += [f"### {ex}", ""]
        for p in prod_by_short.get(ex, []):
            out += ["**Before** (production)", "", f"- text_ar: {shorten(p['text_ar'])}", f"- matn_ar: {shorten(p['matn_ar'], 120, 60) or '(empty)'}",
                    f"- sanad: {shorten(p['sanad'], 120, 40) or '(empty)'}", ""]
        if not prod_by_short.get(ex):
            out += ["**Before**: not in production (dropped by the old parser).", ""]
        for r in by_id.get(ex, []):
            out += [f"**After** (`{r['id']}`, page_ref `{r['page_ref']}`, page_start `{r['page_start']}`, lines {r['line_start']}-{r['line_end']})", "",
                    f"- text_ar: {shorten(r['text_ar'])}", f"- sanad_ar: {shorten(r['sanad_ar'], 150, 90) if r['sanad_ar'] is not None else 'null'}",
                    f"- matn_ar: {shorten(r['matn_ar'], 120, 60) if r['matn_ar'] is not None else 'null'}  (split_confidence `{r['split_confidence']}`, kind `{r['split_kind']}`)"]
            if r["sanad_inherits_from"]:
                out.append(f"- sanad_inherits_from: `{r['sanad_inherits_from']}`")
            if r["footnotes"]:
                out.append(f"- footnotes: {r['footnotes']}")
            for kind, text in zip(r["commentary_kinds"], r["commentary"]):
                out.append(f"- commentary [{kind}]: {shorten(text, 150, 60)}")
            if r["absorbed_ids"]:
                out.append(f"- absorbed_ids: {r['absorbed_ids']}")
            if r["prefix_from_id"]:
                out.append(f"- prefix carried from: `{r['prefix_from_id']}`")
            out.append("")
        if ex == "rida_0032":
            children = [r for r in parsed["rida"]["hadiths"] if r["split_from"] == "rida_0032"]
            out += [f"`rida_0032` is followed by {len(children)} split children: " + ", ".join(f"`{c['id']}`" for c in children)
                    + f". Chapter titles inside it («{children[0]['bab'] if children else ''}» ...) are now `bab` values, not reports.", ""]
    out += ["## Limits and what was not done", "",
            "- Sanad/matn: `sanad_ar` / `matn_ar` are filled only when the closing «قال:» (or a colon, quote or «رسول الله» attribution after it) is clear; "
            "otherwise both are null and `split_confidence` is `low` (counts above). A matn that would open with another reporting verb "
            "(«قال: قال ابن عباس ...», «وقال صلى الله عليه وسلم: ...» with no chain) is also left null rather than guessed.",
            "- `split_chain_matn` is the audit's function with three changes: a closing «قال» followed by «حدثني ...» is a chain link, punctuation after the closing verb "
            "stays on the sanad, and «ومن طريقه» counts as a continuation phrase. A matn is never cut inside a word (asserted in the tests).",
            "- Rabi paragraphs that open «قال جابر:» / «قال أبو عبيدة:» and the arranger's prose in volume 3 are not «قال الربيع» comments, footnotes or «تنبيه»; "
            "they stay in `text_ar` as before (the advisory `commentary_tail` rows above). Whether they are the report's own discussion is a curation call.",
            "- Zayd `(وقال)` / `(قال)` sub-sayings inside one record are not split (advisory `multiple_sayings`, 18 records). "
            "A page-break paragraph whose verb sits after a sentence end is split there; one whose verb is mid-sentence continues the previous report.",
            "- rida pages P444 and P445 of the source repeat the same text; `rida_0007#4` is the first copy's truncated tail «... قال: قال» (flagged "
            "`fragment_only_chain` above) and the reports are present twice. Not deduplicated: the source says it twice.",
            "- rida_0001 still begins with the editor's explanation of the chain (the source has no break between it and the Sahifa's own chain); its `bab` is the first "
            "printed line of the paragraph «الباب الاول في الذكر ولما كانت ...». rida `bab` values come from the printed first line or the matched «الباب <ordinal> في ...» phrase.",
            "- Split children (`#2`, ...) carry the parent's `hadith_no` and legacy `page_ref`; `page_start` is the page of the paragraph the report starts in "
            "(block granularity). Production `page_ref` (the page at the *next* report's start) is kept on purpose so `record_id` does not change.",
            "- The Latin `sanad` list and `chain_indx` are produced downstream by `regen_unified_csvs.py` from `text_ar`; the parser does not write them.", ""]
    with open(os.path.join(HERE, "diff_report.md"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
