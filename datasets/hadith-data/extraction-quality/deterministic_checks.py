#!/usr/bin/env python3
"""Rule-based extraction audit of the OpenITI records (Ibadi rabi, Zaydi zayd, Imami rida).

Writes output/extraction_findings.jsonl.gz (one row per production record), output/records_with_windows.jsonl.gz
(input of score_with_model.py), output/missed_source_reports.jsonl.gz and output/summary.json.
Read-only: nothing outside this directory is touched. See README.md for the method and the flag definitions.

    python deterministic_checks.py [--snapshot output/production_snapshot.jsonl.gz] [--out output]
"""
from __future__ import annotations

import argparse
import bisect
import collections
import gzip
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eq_source as eq  # noqa: E402

AR = "ء-ي"
NOT_AR_BEFORE = rf"(?<![{AR}])"
CHAIN_VERB = r"(?:و?(?:حدثني|حدثنا|حدثتني|أخبرني|أخبرنا|أنبأنا|أنبأني|بلغني|بلغنا|سمعت|سمعنا|روى|رواه)|عن\b)"
RE_CHAIN_VERB_AT = re.compile(rf"^\s*{CHAIN_VERB}")
RE_SAID = re.compile(rf"{NOT_AR_BEFORE}(?:أنه\s+قال|أنها\s+قالت|فقال|وقال|قالت|قال|يقول)(?![{AR}])\s*(:)?")
RE_CONTINUATION_CHAIN = re.compile(rf"^(?:{NOT_AR_BEFORE}و?(?:بهذا|بنفس|بذلك)\s+(?:السند|الإسناد|الاسناد)|وباسناده|وبإسناده|وبسنده|وباسنادهم)")
RE_ATTRIBUTION = re.compile(rf"^(?:قال|فقال|وقال)\s+(?:رسول\s+الله|النبيء?|النبي)\s*(?:صلى\s+الله\s+عليه(?:\s+و?(?:على\s+)?آله)?(?:\s+وسلم)?)?\s*:?\s*")
RE_VERB_START = re.compile(rf"^(?:قال|فقال|وقال|قالت|يقول|قالوا)\b")
RE_LEAD_MARKUP = re.compile(r"^(?:=\s*|\.{3}\s*|V(?=[ء-ي])|\*\s*)+")
RE_ENDS_IN_CHAIN = re.compile(
    rf"(?:{NOT_AR_BEFORE}قال\s*:?\s*$|{NOT_AR_BEFORE}(?:حدثني|حدثنا|أخبرنا|أخبرني)\s+[^.:«»]{{1,40}}$)")
RE_HIDDEN_HEADER = re.compile(r"^\s*(?:PageV\d+P\d+\s+)?(\d+(?:مكرر)?)\)\s*(?:\.\.\.)?\s*")
RE_RULE = re.compile(r"_{3,}")
RE_PAGEISH = re.compile(r"PageV\d|\bms\d{2,}\b|¶|~~|\[\s*\d+\s*\]|\(¬")
RE_ORDINAL_HEADING = re.compile(
    rf"{NOT_AR_BEFORE}الباب\s+(?:الأول|الاول|الثاني|الثالث|الرابع|الخامس|السادس|السابع|الثامن|التاسع|العاشر|الحادي\s+عشر|\d+)"
    r"(?:\s*[:\-])?\s+(?:في|ذكر)\s+[^.:]{3,80}?(?=\s+(?:وباسناده|حدثني|عن)\b|$)")
RE_RIDA_OPENER = re.compile(rf"{NOT_AR_BEFORE}وباسناده")
RE_ZAYD_OPENER = re.compile(rf"(?:^|\s)=\s|{NOT_AR_BEFORE}(?:حدثني|حدثنا|أخبرنا)\s+زيد\s+بن\s+علي")
RE_SAYING = re.compile(rf"\(وقال\)|{NOT_AR_BEFORE}وسألت(?:ه|\s+زيدا)")
EDITORIAL_HEADINGS = {"تنبيه", "تتمة", "فصل", "فائدة", "خاتمة", "مسألة", "تنبيه:", "فصل:"}
LATIN = re.compile(r"[A-Za-z]")
GLOSS_CUE = re.compile(rf"^(?:والمراد|والمعنى|ومعنى|يعني|أي\b|يريد|قال\s+الربيع|وقال\s+الربيع|قال\s+أبو\s+عبيدة\s*:?\s*(?:المراد|معنى))")


# --------------------------------------------------------------------------- chain / matn splitting
def _skip_markup(text):
    m = RE_LEAD_MARKUP.match(text)
    return m.end() if m else 0


RE_ATTR_COLON = re.compile(
    rf"{NOT_AR_BEFORE}(?:عن|أن)\s+(?:رسول\s+الله|النبيء?|النبي)\s*(?:صلى\s+الله\s+عليه(?:\s+و?(?:على\s+)?آله)?(?:\s+وسلم)?)?\s*:")
RE_CHAIN_ANY = re.compile(rf"{NOT_AR_BEFORE}عن\b|حدثني|حدثنا|أخبرنا|أخبرني|بلغني|بلغنا|سمعت|أنبأنا|السند|الإسناد|وباسناده|وبإسناده")
RE_NAME_LED = re.compile(r"^\s*(?:أبو|ابو|ابن)\s")
# Musnad Zayd's fixed chain: «حدثني زيد بن علي عن أبيه عن جده عن علي (ع م)» (the reporting verb is often absent)
RE_ZAYD_FORMULA = re.compile(
    r"^(?:حدثني|حدثنا)\s+زيد\s+بن\s+علي\s+(?:عن|عليه\s+السلام\s+عن)\s+أبيه(?:\s+علي\s+بن\s+الحسين(?:\s+عليه\s+السلام)?)?"
    r"(?:\s+عن\s+جده(?:\s+الحسين(?:\s+بن\s+علي)?)?(?:\s+عن\s+(?:أمير\s+المؤمنين\s+)?علي(?:\s+بن\s+أبي\s+طالب)?)?)?"
    r"(?:\s*\(ع\s*م\)|\s+عليهم?\s+السلام)?")


def split_chain_matn(text: str):
    """Deterministic isnad/matn split.

    Returns dict(lead, sanad_end, matn_start, confidence, kind). The closing reporting verb («قال:») stays on the
    sanad side, as does a «قال رسول الله صلى الله عليه وسلم» attribution that follows it. kind is one of
    no_chain | chain_only | continuation_chain | chain_and_matn. confidence is high only when the closing verb is
    followed by a colon, an opening quote or a prophetic attribution.
    """
    lead = _skip_markup(text)
    body = text[lead:]
    out = {"lead": lead, "sanad_end": lead, "matn_start": lead, "confidence": "none", "kind": "no_chain"}
    if re.match(r"^\s*و?سأل", body):  # a question put to the imam: no isnad
        return out
    cont = RE_CONTINUATION_CHAIN.match(body)
    formula = RE_ZAYD_FORMULA.match(body)
    if formula and not re.match(r"^\s*(?:أنه\s+)?(?:قال|فقال|وقال|يقول)(?![ء-ي])", body[formula.end():]):
        rest = body[formula.end():]
        if len(rest.strip()) >= 6:
            skip = len(rest) - len(rest.lstrip())
            out.update(sanad_end=lead + formula.end(), matn_start=lead + formula.end() + skip, confidence="high", kind="chain_and_matn")
            return out
    limit = min(len(body), 1400)
    pos, end, confidence, close_at = 0, None, "low", None
    while pos < limit:
        m_said = RE_SAID.search(body, pos)
        m_attr = RE_ATTR_COLON.search(body, pos)
        cands = [m for m in (m_said, m_attr) if m and m.start() <= limit]
        if not cands:
            break
        m = min(cands, key=lambda c: c.start())
        if m_attr and (not m_said or m_attr.start() < m_said.start()):
            end, confidence, close_at = m.end(), "high", m.start()
            break
        after = body[m.end():]
        internal = bool(RE_CHAIN_VERB_AT.match(after)) or after.lstrip().startswith("=")
        if m.start() < 6 and re.match(rf"^قال\s+[^:«»]{{1,90}}:\s*{CHAIN_VERB}", body[m.start():]):
            internal = True  # «قال أبو عمرو الربيع بن حبيب: حدثني ...»: the opening قال introduces the first narrator
        if internal:
            pos = m.end()
            continue
        end = m.end()
        close_at = m.start()
        confidence = "high" if (m.group(1) or after.lstrip().startswith(("«", '"', "“")) or RE_ATTRIBUTION.match(after.lstrip())) else "low"
        break
    if end is None:
        if (cont or RE_CHAIN_ANY.search(body[:200])) and body.rstrip().endswith((":", "قال", "عن")) and (
                len(body) < 160 or (len(body) < 900 and "." not in body and "«" not in body)):
            out.update(sanad_end=len(text), matn_start=len(text), kind="chain_only", confidence="high")
        return out
    pre = body[:close_at]
    if not cont and not pre.strip():
        return out  # the record opens with a reporting verb: matn only
    if not cont and not (RE_CHAIN_ANY.search(pre) or RE_NAME_LED.match(pre)):
        return out
    attribution = RE_ATTRIBUTION.match(body[end:].lstrip())
    if attribution and body[end:end + 1] in (" ", ""):
        skip = len(body[end:]) - len(body[end:].lstrip())
        end = end + skip + attribution.end()
    matn_start = end + (len(body[end:]) - len(body[end:].lstrip()))
    out.update(sanad_end=lead + end, matn_start=lead + matn_start, confidence=confidence,
               kind="continuation_chain" if cont else "chain_and_matn")
    if len(text[lead + matn_start:].strip()) < 6:
        out.update(kind="chain_only")
    return out


# --------------------------------------------------------------------------- building a record's findings
def piece_char_starts(rec):
    """For each piece, the first character index of rec.text that came from it (None when none did)."""
    starts = [p.raw_start for p in rec.pieces]
    first = {}
    for i, off in enumerate(rec.offs):
        k = bisect.bisect_right(starts, off) - 1
        if k >= 0 and k not in first:
            first[k] = i
    return first


def evidence(text, a, b, rec=None):
    ev = {"excerpt": text[max(0, a):min(len(text), b)]}
    if rec is not None and rec.offs and a < len(rec.offs):
        span = eq.raw_span_of(rec, a, min(b, len(text)))
        if span:
            ev["raw_span"] = list(span)
    return ev


def tail_group(piece, previous):
    if piece.kind in ("rule", "footnote", "footnote_cont"):
        return "footnote"
    if piece.kind == "comment_cont":
        return "commentary"
    if piece.kind in ("heading_para", "heading_cont"):
        return "heading"
    if piece.kind == "para" and piece.body.strip() in EDITORIAL_HEADINGS:
        return "editorial"
    return previous


def cut_pieces(pieces):
    """Split rec.pieces into (kept, tail groups) where the tail starts at the first footnote/commentary/heading piece."""
    kept, tail, group = [], [], None
    for piece in pieces:
        label = tail_group(piece, group if tail else None)
        if label is None and not tail:
            if piece.kind in ("head", "cont", "para", "orphan_dropped"):
                kept.append(piece)
            continue
        if label is None:
            label = group
        group = label
        tail.append((label, piece))
    return kept, tail


def parts_of(pieces):
    out = []
    for piece in pieces:
        if piece.kind in ("rule",):
            continue
        out.append((piece.body, piece.body_off))
    return out


def tidy_prefix_suffix(text):
    """Strip leading markup and a trailing lone '*' (edition markers). Returns (cleaned, notes)."""
    notes = []
    lead = _skip_markup(text)
    if lead:
        notes.append(("leading_markup", text[:lead]))
    cleaned = text[lead:]
    stripped = re.sub(r"\s*\*+\s*$", "", cleaned)
    if stripped != cleaned:
        notes.append(("trailing_star", cleaned[len(stripped):]))
        cleaned = stripped
    return cleaned, notes


def analyse(rec, prod, replay, ctx):
    """Return (flags, proposal) for one record."""
    flags = []
    text = prod["text_ar"] or ""
    work = rec.work
    firsts = piece_char_starts(rec)

    def add(flag, severity, **ev):
        flags.append({"flag": flag, "severity": severity, "evidence": ev})

    hidden_at = next((i for i, p in enumerate(rec.pieces) if p.kind == "orphan_dropped" and RE_HIDDEN_HEADER.match(p.body)), None)
    main_pieces = rec.pieces if hidden_at is None else rec.pieces[:hidden_at]
    kept, tail = cut_pieces(main_pieces)
    groups = collections.OrderedDict()
    for label, piece in tail:
        groups.setdefault(label, []).append(piece)

    # ---- footnote_leak
    footnote_texts = []
    if "footnote" in groups or RE_RULE.search(text):
        idx = next((firsts[i] for i, p in enumerate(rec.pieces) if p.kind in ("rule", "footnote") and i in firsts), None)
        if idx is None:
            m = RE_RULE.search(text)
            idx = m.start() if m else 0
        add("footnote_leak", "defect", **evidence(text, idx, idx + 140, rec), kind="after_rule_line")
        for piece in groups.get("footnote", []):
            body = piece.body.strip()
            if RE_RULE.fullmatch(body) or re.fullmatch(r"(?:\(\d+\)\s*)?\*+", body):
                continue
            footnote_texts.append((body, piece.body_off))
    # ---- commentary_tail
    commentary_texts = []
    if "commentary" in groups or "editorial" in groups:
        first_i = next(i for i, p in enumerate(rec.pieces) if tail_group(p, None) in ("commentary", "editorial"))
        idx = firsts.get(first_i)
        kind = "continuation_of_rabi_comment_paragraph" if "commentary" in groups and "editorial" not in groups else "editorial_section"
        add("commentary_tail", "defect", **(evidence(text, idx, idx + 140, rec) if idx is not None else {}), kind=kind,
            chars=len(text) - (idx or 0))
    # ---- heading swallowed
    heading_groups = groups.get("heading", [])
    # ---- rabi: comment paragraphs the pipeline attached to the previous record
    true_comments = rec.meta.get("true_commentary", [])
    prev_misattributed = bool(true_comments)

    # ---- corrected text: the kept pieces, orphans included in place
    t_kept = eq.normalise_tracked(parts_of(kept)) if kept else eq.Tracked([], [])
    proposed = t_kept.s
    proposed_offs = t_kept.offs

    # ---- truncated: lines the pipeline dropped inside the record (or right after it, for zayd)
    orphan_pieces = [p for p in kept if p.kind == "orphan_dropped"]
    hidden_parts = None
    if hidden_at is not None:
        hp = rec.pieces[hidden_at]
        label = RE_HIDDEN_HEADER.match(hp.body).group(1)
        after = [(q.body, q.body_off) for q in rec.pieces[hidden_at + 1:] if q.in_text]
        head_off = hp.body_off + RE_HIDDEN_HEADER.match(hp.body).end()
        hidden_parts = {"label": label, "text": eq.normalise_tracked([(hp.body[RE_HIDDEN_HEADER.match(hp.body).end():], head_off)] + after).s}
    for line in ctx["orphans_after"].get(rec.id, []):
        orphan_pieces.append(line)
    if orphan_pieces:
        add("truncated", "defect", kind="pipeline_dropped_source_lines",
            dropped=[eq.normalise_plain(p.body if hasattr(p, "body") else p["text"]) for p in orphan_pieces])
    # ---- lost paragraph (misread as a juz/qism heading): next heading entry right after this record
    for h in ctx["lost_juz_after"].get(rec.id, []):
        add("truncated", "defect", kind="paragraph_misread_as_juz_heading", dropped=eq.normalise_plain(h["text"])[:200], length=h["length"])

    # ---- markup_leak
    lead = _skip_markup(proposed)
    marks = []
    if lead:
        marks.append({"kind": "leading_marker", "text": proposed[:lead]})
    if re.search(r"\s\*+\s*$", proposed) or re.search(r"(?:^|\s)\*(?:\s|$)", text):
        marks.append({"kind": "asterisk"})
    if RE_PAGEISH.search(proposed):
        marks.append({"kind": "page_or_milestone_residue", "text": RE_PAGEISH.search(proposed).group(0)})
    if work != "rabi" and re.search(r"\(¬?\d+\)", text):
        marks.append({"kind": "footnote_marker_residue"})
    if marks:
        add("markup_leak", "defect", markers=marks, excerpt=text[:60])

    cleaned, _notes = tidy_prefix_suffix(proposed)
    last_end = max(p.raw_end for p in rec.pieces)
    for dropped_line in ctx["orphans_after"].get(rec.id, []):  # zayd/rida lines the pipeline dropped right after the record
        if 0 <= dropped_line["raw_start"] - last_end < 160 and not groups:
            cleaned = cleaned + " " + eq.normalise_plain(dropped_line["text"])

    # ---- merged_records
    segments = None
    merged_kinds = []
    if heading_groups:
        merged_kinds.append("kitab_heading_inside")
    if work == "rida":
        heads = [m.start() for m in RE_ORDINAL_HEADING.finditer(cleaned)]
        openers = [m.start() for m in RE_RIDA_OPENER.finditer(cleaned)]
        if heads:
            merged_kinds.append("bab_heading_inside")
        if len(openers) > 1:
            merged_kinds.append("multiple_reports")
        if heads or len(openers) > 1:
            segments = split_rida(cleaned)
    elif work == "zayd":
        openers = [m.start() for m in RE_ZAYD_OPENER.finditer(cleaned)]
        # an opener at the very start does not count twice
        real = [o for o in openers if o > 2]
        if real:
            merged_kinds.append("multiple_reports")
            segments = split_at(cleaned, [0] + [o + (1 if cleaned[o].isspace() else 0) for o in real])
    if hidden_parts:
        merged_kinds.append("numbered_report_header_hidden_behind_page_marker")
    if merged_kinds:
        add("merged_records", "defect", kinds=merged_kinds, parts=len(segments) if segments else None,
            excerpt=[cleaned[a:a + 70] for a, _b, _k in (segments or [])][:6])
    sayings = len(RE_SAYING.findall(cleaned))
    if work == "zayd" and sayings >= 2:
        add("multiple_sayings", "advisory", count=sayings)

    # ---- sanad/matn
    sp = split_chain_matn(cleaned)
    base = cleaned
    matn_prod = prod["matn_ar"] or ""
    sanad_prod = prod["sanad"] or ""
    # fragment_only_chain
    is_fragment = sp["kind"] == "chain_only"
    if is_fragment:
        add("fragment_only_chain", "defect", excerpt=cleaned[:120], chars=len(cleaned))
    ends_in_chain = (not is_fragment) and bool(RE_ENDS_IN_CHAIN.search(cleaned[-90:])) and len(cleaned) > 30
    tail_move = None
    if ends_in_chain:
        add("truncated", "defect", kind="record_ends_inside_a_chain", tail=cleaned[-90:])
        m_end = RE_ENDS_IN_CHAIN.search(cleaned)
        cut = cleaned.rfind(". ", 0, m_end.start())
        if work != "rabi" and cut > 0 and len(cleaned) - cut <= 220:
            tail_move = (cleaned[:cut + 1], cleaned[cut + 2:])
    split_flags = []
    if matn_prod and RE_VERB_START.match(matn_prod.strip()):
        split_flags.append({"kind": "matn_starts_with_reporting_verb", "matn_head": matn_prod[:40]})
    if matn_prod.strip():
        head = matn_prod.strip()[:25]
        at = text.find(head)
        if at > 0 and not text[at - 1].isspace():
            split_flags.append({"kind": "matn_starts_mid_word", "matn_head": matn_prod.strip()[:30], "offset_in_text": at})
    if sp["confidence"] == "high" and sp["kind"] in ("chain_and_matn", "continuation_chain"):
        expected = cleaned[sp["matn_start"]:].strip()[:40]
        if matn_prod.strip()[:40] != expected:
            split_flags.append({"kind": "matn_differs_from_rule_split", "matn_in_production": matn_prod.strip()[:50],
                                "matn_by_rule": expected})
    if sp["kind"] == "continuation_chain" and not sanad_prod:
        split_flags.append({"kind": "continuation_chain_without_sanad", "chain_phrase": cleaned[sp["lead"]:sp["sanad_end"]][:80]})
    elif sp["kind"] in ("chain_and_matn",) and sp["confidence"] == "high" and not sanad_prod:
        split_flags.append({"kind": "chain_present_but_sanad_empty", "chain_phrase": cleaned[sp["lead"]:sp["sanad_end"]][:80]})
    if split_flags:
        add("sanad_matn_split_wrong", "defect", problems=split_flags)
    if sanad_prod and LATIN.search(sanad_prod):
        add("sanad_latin_not_arabic_span", "defect", sanad_in_production=sanad_prod[:100],
            arabic_chain=cleaned[sp["lead"]:sp["sanad_end"]][:160] if sp["kind"] != "no_chain" else None)

    # ---- tail glosses after the matn's closing quote (heuristic, advisory)
    gloss_at = None
    if "commentary" not in groups and work == "rabi":
        m = re.search(r"»\s*[.،]?\s+(?=\S)", cleaned)
        if m:
            last = list(re.finditer(r"»\s*[.،]?\s+(?=\S)", cleaned))[-1]
            tail_text = cleaned[last.end():]
            if len(tail_text) >= 12 and "«" not in tail_text and (GLOSS_CUE.match(tail_text) or last.end() > 0.5 * len(cleaned)):
                gloss_at = last.end()
    if gloss_at is not None and not any(f["flag"] == "commentary_tail" for f in flags):
        add("commentary_tail", "advisory", kind="text_after_closing_quote", **evidence(cleaned, gloss_at, gloss_at + 140, None))

    # ---- proposal
    proposal = None
    needs = {f["flag"] for f in flags if f["severity"] == "defect"}
    if tail_move:
        needs.add("tail_move")
    if needs or prev_misattributed or footnote_texts or commentary_texts:
        t_text = cleaned
        proposal = {"text_ar": t_text}
        if is_fragment:
            proposal["note"] = "chain opener only; merge with the next record"
        elif sp["kind"] in ("chain_and_matn", "continuation_chain") and sp["confidence"] == "high":
            proposal["sanad_ar"] = t_text[:sp["sanad_end"]].strip()
            proposal["matn_ar"] = t_text[sp["matn_start"]:].strip()
        elif sp["kind"] == "no_chain":
            proposal["sanad_ar"] = ""
            proposal["matn_ar"] = t_text
        if segments:
            proposal["split_into"] = [
                {"kind": k, "text_ar": cleaned[a:b].strip(), **({} if k == "heading" else split_fields(cleaned[a:b].strip()))}
                for a, b, k in segments]
            first_report = next((s for s in proposal["split_into"] if s["kind"] == "report"), None)
            if first_report:
                proposal["text_ar"] = first_report["text_ar"]
                for key in ("sanad_ar", "matn_ar"):
                    if key in first_report:
                        proposal[key] = first_report[key]
                    else:
                        proposal.pop(key, None)
        if hidden_parts:
            first = {"kind": "report", "text_ar": cleaned, **split_fields(cleaned)}
            proposal["split_into"] = [first, {"kind": "report", "suggested_label": hidden_parts["label"], "text_ar": hidden_parts["text"], **split_fields(hidden_parts["text"])}]
        if tail_move:
            proposal["text_ar"] = tail_move[0]
            proposal["move_tail_to_next_record"] = tail_move[1]
            for key in ("sanad_ar", "matn_ar"):
                proposal.pop(key, None)
            proposal.update({k: v for k, v in split_fields(tail_move[0]).items()})
        if footnote_texts:
            proposal["footnotes"] = [eq.normalise_plain(b) for b, _o in footnote_texts]
        proposal_comments = comment_groups(rec, groups)
        if proposal_comments and work == "rabi":
            proposal["commentary"] = proposal_comments
    if prev_misattributed:
        add("commentary_misattributed", "advisory", note="pipeline stored this record's «قال الربيع» paragraph on the previous record",
            commentary=eq.normalise_plain(" ".join(p.body for p in true_comments))[:140])
    return flags, proposal, sp


def comment_groups(rec, groups):
    """Comment paragraphs of this record as verbatim strings, one per run of adjacent comment pieces (raw order)."""
    tail_comment = set(id(p) for p in groups.get("commentary", []) + groups.get("editorial", []))
    items = [(p.raw_start, "comment", p) for p in rec.meta.get("true_commentary", [])]
    items += [(p.raw_start, "comment", p) for p in rec.pieces if id(p) in tail_comment]
    others = [(p.raw_start, "other", p) for p in rec.pieces if id(p) not in tail_comment and p.kind in ("rule", "footnote", "footnote_cont", "head", "cont", "para", "orphan_dropped", "heading_para")]
    seq = sorted(items + others, key=lambda x: x[0])
    out, run = [], []
    for _start, role, piece in seq:
        if role == "comment":
            run.append((piece.body, piece.body_off))
        elif run:
            out.append(eq.normalise_tracked(run).s)
            run = []
    if run:
        out.append(eq.normalise_tracked(run).s)
    return [c for c in out if c]


def split_fields(text):
    sp = split_chain_matn(text)
    out = {}
    if sp["kind"] in ("chain_and_matn", "continuation_chain") and sp["confidence"] == "high":
        lead = _skip_markup(text)
        out["sanad_ar"] = text[:sp["sanad_end"]].strip()
        out["matn_ar"] = text[sp["matn_start"]:].strip()
    elif sp["kind"] == "no_chain":
        out["sanad_ar"] = ""
        out["matn_ar"] = text
    return out


def split_at(text, starts):
    starts = sorted(set(starts))
    segs = []
    for i, a in enumerate(starts):
        b = starts[i + 1] if i + 1 < len(starts) else len(text)
        if text[a:b].strip():
            segs.append((a, b, "report"))
    return segs


def split_rida(text):
    bounds = []
    for m in RE_RIDA_OPENER.finditer(text):
        bounds.append((m.start(), "report"))
    for m in RE_ORDINAL_HEADING.finditer(text):
        bounds.append((m.start(), "heading"))
    bounds = sorted(set(bounds))
    if not bounds or bounds[0][0] > 0:
        bounds.insert(0, (0, "report"))
    segs = []
    for i, (a, kind) in enumerate(bounds):
        b = bounds[i + 1][0] if i + 1 < len(bounds) else len(text)
        if text[a:b].strip():
            segs.append((a, b, kind))
    return segs


# --------------------------------------------------------------------------- windows
def window_for(paras, starts, raw_a, raw_b, before=2, after=2, max_chars=7000):
    i = max(0, bisect.bisect_right(starts, raw_a) - 1 - before)
    j = min(len(paras) - 1, bisect.bisect_right(starts, raw_b) - 1 + after)
    texts = [p["text"] for p in paras[i:j + 1]]
    window = "\n".join(texts)
    if len(window) > max_chars:  # keep the record's own paragraphs; trim the far end
        window = window[:max_chars]
    return window, (paras[i]["raw_start"], paras[j]["raw_end"])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", default=eq.SNAPSHOT)
    ap.add_argument("--out", default=os.path.join(eq.HERE, "output"))
    args = ap.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)
    snap = eq.load_snapshot(args.snapshot)
    findings, windows, missed = [], [], []
    summary = {"works": {}, "replay": {}}
    for work in ("rabi", "zayd", "rida"):
        rep = eq.replay(work)
        raw = rep.raw
        paras = eq.paragraph_stream(raw)
        starts = [p["raw_start"] for p in paras]
        by_key = {r.meta["source_record_id"]: r for r in rep.records}
        rows = [v for v in snap.values() if v["work"] == work]
        rows.sort(key=lambda r: r["source_record_id"])
        # orphan lines (zayd/rida: 'unrecognised_line'; rabi outside a record) attach to the record that precedes them
        rec_starts = sorted((r.pieces[0].raw_start, r.id) for r in rep.records)
        rs = [x[0] for x in rec_starts]
        ctx = {"orphans_after": collections.defaultdict(list), "lost_juz_after": collections.defaultdict(list)}
        for d in rep.dropped:
            if d["reason"] in ("unrecognised_line", "unrecognised_line_outside_record") and RE_NOT_PAGE(d["text"]):
                k = bisect.bisect_right(rs, d["raw_start"]) - 1
                if k >= 0:
                    ctx["orphans_after"][rec_starts[k][1]].append(d)
        for h in rep.headings:
            if h["kind"] == "lost_juz_paragraph":
                k = bisect.bisect_right(rs, h["raw_start"]) - 1
                if k >= 0:
                    ctx["lost_juz_after"][rec_starts[k][1]].append(h)
        replay_ok = 0
        order = {r.meta["source_record_id"]: i for i, r in enumerate(rep.records)}
        for prod in rows:
            key = prod["source_record_id"]
            rec = by_key.get(key)
            row = {"id": prod["id"], "source_record_id": key, "work": work, "source_file": os.path.relpath(eq.SOURCES[work], eq.HADITH_DATA).replace("\\", "/"),
                   "production": {"text_chars": len(prod["text_ar"] or ""), "sanad": prod["sanad"], "matn_chars": len(prod["matn_ar"] or "")}}
            if rec is None or rec.text != (prod["text_ar"] or ""):
                row.update(located=False, source_span="not located", flags=[{"flag": "missing_from_source", "severity": "defect",
                           "evidence": {"reason": "replay does not reproduce the production text", "excerpt": (prod["text_ar"] or "")[:80]}}],
                           proposal=None, clean=False)
                findings.append(row)
                continue
            replay_ok += 1
            flags, proposal, sp = analyse(rec, prod, rep, ctx)
            raw_a = min(p.raw_start for p in rec.pieces)
            raw_b = max(p.raw_end for p in rec.pieces)
            row.update(located=True, source_span={"raw_start": raw_a, "raw_end": raw_b, "line_start": rec.pieces[0].line_no,
                       "line_end": max(p.line_no for p in rec.pieces), "text_raw_start": rec.offs[0], "text_raw_end": rec.offs[-1] + 1,
                       "offsets_are": "character offsets into the decoded source file (UTF-8, LF)"},
                       flags=flags, proposal=proposal)
            extra_next = None
            if work != "rabi" and is_fragment_flag(flags) and not (proposal or {}).get("move_tail_to_next_record"):  # rabi records are numbered: never merged
                nxt_i = order[key] + 1
                if nxt_i < len(rep.records):
                    nxt = rep.records[nxt_i]
                    between = [h for h in rep.headings if raw_b <= h["raw_start"] <= nxt.pieces[0].raw_start]
                    if not between and nxt.pieces[0].raw_start - raw_b < 400:
                        extra_next = nxt
                        merged = eq.normalise_tracked([(p.body, p.body_off) for p in rec.pieces + nxt.pieces if p.in_text]).s
                        row["proposal"] = row["proposal"] or {}
                        row["proposal"].update(merge_with_next=nxt.meta["source_record_id"], merged_text_ar=merged,
                                               **{"merged_" + k: v for k, v in split_fields(merged).items()})
                        if is_fragment_flag(flags, strict=True):
                            row["proposal"].pop("sanad_ar", None)
                            row["proposal"].pop("matn_ar", None)
            raw_b_win = max(p.raw_end for p in (extra_next.pieces if extra_next else rec.pieces))
            window, wspan = window_for(paras, starts, raw_a, raw_b_win)
            # validation: every proposed string must be a verbatim substring of the source window
            row["proposal_validation"] = validate_proposal(row["proposal"], window)
            row["clean"] = not any(f["severity"] == "defect" for f in flags)
            findings.append(row)
            windows.append({"id": prod["id"], "source_record_id": key, "work": work, "text_ar": prod["text_ar"], "sanad": prod["sanad"],
                            "matn_ar": prod["matn_ar"], "window_ar": window, "window_raw_span": list(wspan)})
        # source reports the extraction missed or shelved
        for d in rep.dropped:
            if RE_NOT_PAGE(d["text"]):
                missed.append({"work": work, **d})
        for h in rep.headings:
            if h["kind"] == "lost_juz_paragraph":
                missed.append({"work": work, "reason": "paragraph_misread_as_juz_heading", "raw_start": h["raw_start"], "line_no": h["line_no"], "text": eq.normalise_plain(h["text"])})
        for rec in rep.records:
            for p in rec.pieces:
                if p.kind == "orphan_dropped":
                    missed.append({"work": work, "reason": "orphan_line_dropped_inside_record", "record": rec.id, "raw_start": p.raw_start, "line_no": p.line_no, "text": eq.normalise_plain(p.body)})
            for p in rec.meta.get("true_commentary", []):
                missed.append({"work": work, "reason": "rabi_comment_not_loaded_to_production", "record": rec.id, "raw_start": p.raw_start, "line_no": p.line_no, "text": eq.normalise_plain(p.body)[:200]})
        summary["replay"][work] = {"records_replayed": len(rep.records), "production_rows": len(rows), "reproduced_exactly": replay_ok,
                                    "replay_only_ids": sorted(set(by_key) - {r["source_record_id"] for r in rows})}
    # --- summary
    for work in ("rabi", "zayd", "rida"):
        rows = [r for r in findings if r["work"] == work]
        flag_counts = collections.Counter()
        for r in rows:
            for fl in {f["flag"] for f in r["flags"]}:
                flag_counts[fl] += 1
        props = [r for r in rows if r.get("proposal")]
        validation = collections.Counter()
        for r in rows:
            for k, ok in (r.get("proposal_validation") or {}).items():
                validation["ok" if ok else "fail"] += 1
        kinds = collections.Counter()
        for r in rows:
            for f in r["flags"]:
                ev = f["evidence"]
                if f["flag"] == "sanad_matn_split_wrong":
                    kinds.update("sanad_matn_split_wrong:" + p["kind"] for p in ev["problems"])
                elif f["flag"] in ("markup_leak",):
                    kinds.update("markup_leak:" + p["kind"] for p in ev["markers"])
                elif f["flag"] in ("merged_records",):
                    kinds.update("merged_records:" + k for k in ev["kinds"])
                elif f["flag"] in ("commentary_tail", "truncated"):
                    kinds["%s:%s:%s" % (f["flag"], ev.get("kind"), f["severity"])] += 1
        text_flags = {"footnote_leak", "markup_leak", "fragment_only_chain", "merged_records", "commentary_tail", "truncated", "missing_from_source"}
        text_clean = sum(1 for r in rows if not any(f["flag"] in text_flags and f["severity"] == "defect" for f in r["flags"]))
        summary["works"][work] = {"records": len(rows), "clean": sum(1 for r in rows if r["clean"]),
                                   "text_level_clean": text_clean, "flag_kinds": dict(sorted(kinds.items())),
                                   "with_defect": sum(1 for r in rows if not r["clean"]),
                                   "flags": dict(sorted(flag_counts.items())), "records_with_proposal": len(props),
                                   "proposal_fields_validated": dict(validation),
                                   "proposal_failures": [r["id"] for r in rows if any(not v for v in (r.get("proposal_validation") or {}).values())]}
    summary["missed_source_reports"] = dict(collections.Counter((m["work"], m["reason"]) .__str__() for m in missed))
    write_gz(os.path.join(args.out, "extraction_findings.jsonl.gz"), findings)
    write_gz(os.path.join(args.out, "records_with_windows.jsonl.gz"), windows)
    write_gz(os.path.join(args.out, "missed_source_reports.jsonl.gz"), missed)
    with open(os.path.join(args.out, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def is_fragment_flag(flags, strict=False):
    for f in flags:
        if f["flag"] == "fragment_only_chain":
            return True
        if not strict and f["flag"] == "truncated" and f["evidence"].get("kind") == "record_ends_inside_a_chain":
            return True
    return False


def RE_NOT_PAGE(text):
    return bool(re.sub(r"PageV\d+P\d+|\[\s*\d+\s*\]|[\s#=~|]", "", text or "")) and bool(re.search(r"[ء-ي]", text or ""))


def write_gz(path, rows):
    with gzip.open(path, "wt", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def flatten_proposal(proposal):
    """Every string in a proposal that claims to be verbatim source text."""
    out = {}
    if not proposal:
        return out
    for key in ("text_ar", "sanad_ar", "matn_ar", "merged_text_ar", "merged_sanad_ar", "merged_matn_ar", "move_tail_to_next_record"):
        if proposal.get(key):
            out[key] = proposal[key]
    for i, c in enumerate(proposal.get("commentary", []) or []):
        out[f"commentary[{i}]"] = c
    for i, f in enumerate(proposal.get("footnotes", []) or []):
        out[f"footnotes[{i}]"] = f
    for i, part in enumerate(proposal.get("split_into", []) or []):
        for key in ("text_ar", "sanad_ar", "matn_ar"):
            if part.get(key):
                out[f"split_into[{i}].{key}"] = part[key]
    return out


def validate_proposal(proposal, window):
    haystack = eq.collapse_ws(window)
    return {k: eq.collapse_ws(v) in haystack for k, v in flatten_proposal(proposal).items()}


if __name__ == "__main__":
    main()
