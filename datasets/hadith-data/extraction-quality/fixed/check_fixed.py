"""The audit's deterministic checks (deterministic_checks.py rules) re-run on the fixed parse.

Same flag names and rules as the audit, applied to the fixed records' own fields (text_ar, sanad_ar, matn_ar). Counts are records
flagged per work; the "before" side is the audit's output/summary.json. Read-only. See fixed/AGENTS.md.
"""
from __future__ import annotations

import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EQ_DIR = os.path.dirname(HERE)
sys.path.insert(0, EQ_DIR)
import deterministic_checks as dc  # noqa: E402

RE_PAGE_RESIDUE = dc.RE_PAGEISH
RE_PROSE_AFTER_QUOTE = re.compile(r"»\s*[.،]?\s+(?=\S)")
RE_GLOSS_TAIL = re.compile(r"[.»؟!]\s+و?قال\s+الربيع\s*:")


def flags_of_record(work: str, record: dict, heading_titles) -> dict:
    """flag -> (severity, evidence) for one fixed record."""
    text = record["text_ar"]
    flags = {}
    if dc.RE_RULE.search(text):
        flags["footnote_leak"] = ("defect", "rule line in text")
    marks = []
    if dc._skip_markup(text):
        marks.append("leading_marker")
    if re.search(r"\s\*+\s*$", text) or re.search(r"(?:^|\s)\*(?:\s|$)", text):
        marks.append("asterisk")
    if RE_PAGE_RESIDUE.search(text):
        marks.append("page_or_milestone_residue")
    if work != "rabi" and re.search(r"\(¬?\d+\)", text):
        marks.append("footnote_marker_residue")
    if marks:
        flags["markup_leak"] = ("defect", ",".join(marks))
    split = dc.split_chain_matn(text)
    if split["kind"] == "chain_only":
        flags["fragment_only_chain"] = ("defect", text[:80])
    merged = []
    if work == "rida":
        if dc.RE_ORDINAL_HEADING.search(text):
            merged.append("bab_heading_inside")
        if len(dc.RE_RIDA_OPENER.findall(text)) > 1:
            merged.append("multiple_reports")
    elif work == "zayd":
        # the audit rule also fires on «قال: حدثني زيد بن علي» inside one chain; a second report needs a sentence end before the opener
        if [m for m in dc.RE_ZAYD_OPENER.finditer(text) if m.start() > 2 and re.search(r"[.!؟»]\s*$", text[:m.start()])]:
            merged.append("multiple_reports")
        elif [m for m in dc.RE_ZAYD_OPENER.finditer(text) if m.start() > 2]:
            flags["merged_records_audit_rule_only"] = ("advisory", "opener inside one chain")
    elif any(len(title) >= 8 and re.search(r"[.»؟!]\s+" + re.escape(title) + r"(?:\s|$)", text) for title in heading_titles):
        merged.append("kitab_heading_inside")
    if merged:
        flags["merged_records"] = ("defect", ",".join(merged))
    if RE_GLOSS_TAIL.search(text):
        flags["commentary_tail"] = ("defect", "inline «قال الربيع» gloss left in the text")
    elif work == "rabi":
        last = list(RE_PROSE_AFTER_QUOTE.finditer(text))
        if last:
            tail = text[last[-1].end():]
            if len(tail) >= 12 and "«" not in tail and (dc.GLOSS_CUE.match(tail) or last[-1].end() > 0.5 * len(text)):
                flags["commentary_tail"] = ("advisory", "text_after_closing_quote")
    if len(text) > 30 and dc.RE_ENDS_IN_CHAIN.search(text[-90:]) and split["kind"] != "chain_only":
        flags["truncated"] = ("defect", "record_ends_inside_a_chain")
    problems = []
    matn, sanad = record.get("matn_ar"), record.get("sanad_ar")
    if matn and dc.RE_VERB_START.match(matn.strip()):
        problems.append("matn_starts_with_reporting_verb")
    if matn:
        at = text.find(matn.strip()[:25])
        if at > 0 and not text[at - 1].isspace():
            problems.append("matn_starts_mid_word")
    if split["confidence"] == "high" and split["kind"] in ("chain_and_matn", "continuation_chain"):
        expected = text[split["matn_start"]:].strip()[:40]
        audit_cut_is_unreliable = expected.lstrip().startswith(tuple(".،,:؛")) or bool(dc.RE_VERB_START.match(expected.lstrip(" .،,:؛")))
        if (matn or "").strip()[:40] != expected and record["split_confidence"] == "high" and not audit_cut_is_unreliable:
            problems.append("matn_differs_from_rule_split")   # (the audit rule leaves '، قال:' on the matn side; ours keeps it on the sanad)
        if sanad is None and record["split_confidence"] == "high":
            problems.append("chain_present_but_sanad_empty")
    if problems:
        flags["sanad_matn_split_wrong"] = ("defect", ",".join(problems))
    if sanad and dc.LATIN.search(sanad):
        flags["sanad_latin_not_arabic_span"] = ("defect", sanad[:60])
    if work == "zayd" and len(dc.RE_SAYING.findall(text)) >= 2:
        flags["multiple_sayings"] = ("advisory", "")
    return flags


def run(fixed_works: dict, summary_path: str | None = None) -> dict:
    """fixed_works: {work: parse dict}. Returns {work: {records, clean, text_level_clean, flags, flagged_ids}} plus the audit's 'before'."""
    before = {}
    summary_path = summary_path or os.path.join(EQ_DIR, "output", "summary.json")
    if os.path.exists(summary_path):
        with open(summary_path, encoding="utf-8") as handle:
            before = json.load(handle)["works"]
    after, text_flags = {}, {"footnote_leak", "markup_leak", "fragment_only_chain", "merged_records", "commentary_tail", "truncated"}
    for work, parsed in fixed_works.items():
        titles = {h.get(key) for h in parsed["hadiths"] for key in ("kitab", "section") if h.get(key)}
        counts, flagged = collections.Counter(), collections.defaultdict(list)
        clean = text_clean = 0
        for record in parsed["hadiths"]:
            flags = flags_of_record(work, record, titles)
            for name, (severity, evidence) in flags.items():
                counts[name] += 1
                flagged[name].append({"id": record["id"], "severity": severity, "evidence": evidence})
            defects = {n for n, (sev, _e) in flags.items() if sev == "defect"}
            clean += not defects
            text_clean += not (defects & text_flags)
        after[work] = {"records": len(parsed["hadiths"]), "clean": clean, "text_level_clean": text_clean,
                       "flags": dict(sorted(counts.items())), "flagged": {k: v for k, v in flagged.items()}}
    return {"before": before, "after": after}


if __name__ == "__main__":
    fixed_path = os.path.join(HERE, "parsed_hadiths.fixed.json")
    with open(fixed_path, encoding="utf-8") as handle:
        works = json.load(handle)["works"]
    result = run(works)
    print(json.dumps({w: {k: v for k, v in d.items() if k != "flagged"} for w, d in result["after"].items()}, ensure_ascii=False, indent=2))
