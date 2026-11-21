"""Source replay with provenance: which source line fed which character of which record.

Terse by design; the method and the pipeline path are in README.md (section "From source file to record").
The three replay_* functions mirror datasets/parse_openiti.py (parse_rabi, parse_zayd, parse_rida_appendix) line
for line, but keep raw character offsets and label every line with what the pipeline did with it.
"""
from __future__ import annotations

import bisect
import gzip
import json
import os
import re
import sys
import unicodedata
from dataclasses import dataclass, field

HERE = os.path.dirname(os.path.abspath(__file__))
HADITH_DATA = os.path.dirname(HERE)
DATASETS = os.path.dirname(HADITH_DATA)
sys.path.insert(0, DATASETS)
import parse_openiti as po  # noqa: E402  (read-only reuse of the pipeline's own regexes and normalisation)

SOURCES = {
    "rabi": os.path.join(HADITH_DATA, "openiti-sources", "rabi", "jamic_sahih_ibadiyya.txt"),
    "zayd": os.path.join(HADITH_DATA, "openiti-sources", "zayd", "musnad_zaydiyya_052.mARkdown"),
    "rida": os.path.join(HADITH_DATA, "openiti-sources", "zayd", "musnad_zaydiyya_052.mARkdown"),
}
SNAPSHOT = os.path.join(HERE, "output", "production_snapshot.jsonl.gz")
BIDI = set("‏‎‌​‍‬‫‪⁩⁨⁦⁧﻿")
RE_HIDDEN_HEADER = re.compile(r"^\s*(?:PageV\d+P\d+\s+)?(\d+(?:مكرر)?)\)\s*(?:\.\.\.)?\s*")
RE_ORPHAN_PAGE_NUMBER = re.compile(r"^\s*\[\s*\d+\s*\]\s*$")


# --------------------------------------------------------------------------- tracked normalisation
@dataclass
class Tracked:
    """A string whose every character remembers its raw-file offset."""
    chars: list
    offs: list

    @property
    def s(self) -> str:
        return "".join(self.chars)

    def remove(self, spans):
        keep = [True] * len(self.chars)
        for a, b in spans:
            for i in range(a, b):
                keep[i] = False
        return Tracked([c for c, k in zip(self.chars, keep) if k], [o for o, k in zip(self.offs, keep) if k])

    def sub(self, regex):
        return self.remove([m.span() for m in regex.finditer(self.s)])

    def collapse(self):
        out_c, out_o, prev_ws = [], [], False
        for c, o in zip(self.chars, self.offs):
            if c.isspace():
                if not prev_ws:
                    out_c.append(" ")
                    out_o.append(o)
                prev_ws = True
            else:
                out_c.append(c)
                out_o.append(o)
                prev_ws = False
        while out_c and out_c[0] == " ":
            out_c.pop(0)
            out_o.pop(0)
        while out_c and out_c[-1] == " ":
            out_c.pop()
            out_o.pop()
        return Tracked(out_c, out_o)


def track_join(parts):
    """parts: [(body, raw_offset_of_body)] joined by single spaces, as the pipeline does."""
    chars, offs = [], []
    prev_end = 0
    for k, (body, off) in enumerate(parts):
        if k:
            chars.append(" ")
            offs.append(prev_end)
        for i, ch in enumerate(body):
            chars.append(ch)
            offs.append(off + i)
        prev_end = off + len(body)
    return Tracked(chars, offs)


def normalise_tracked(parts) -> Tracked:
    """parse_openiti.normalize_arabic then strip_footnote_markers, with offsets carried through."""
    t = track_join(parts)
    chars, offs = [], []
    for c, o in zip(t.chars, t.offs):  # NFKC per character; whole-string equivalence is checked by the replay test
        for n in unicodedata.normalize("NFKC", c):
            chars.append(n)
            offs.append(o)
    t = Tracked(chars, offs)
    t = Tracked([c for c in t.chars if c not in BIDI], [o for c, o in zip(t.chars, t.offs) if c not in BIDI])
    t = t.sub(po.RE_PAGE).sub(po.RE_MILESTONE).collapse()
    return t.sub(re.compile(r"\(¬?\d+\)")).collapse()


def normalise_plain(text: str) -> str:
    return po.strip_footnote_markers(po.normalize_arabic(text))


def collapse_ws(text: str) -> str:
    return " ".join(text.split())


# --------------------------------------------------------------------------- replay
@dataclass
class Piece:
    kind: str          # head | cont | para | comment | comment_cont | rule | footnote | footnote_cont | heading_para
                       # | heading_cont | orphan_dropped | lost_juz | page_number
    raw_start: int
    raw_end: int
    line_no: int
    body: str
    body_off: int
    in_text: bool      # did the pipeline put this body into the record's text_ar?
    para_index: int = -1


@dataclass
class Record:
    work: str
    id: str
    label: str = ""
    pieces: list = field(default_factory=list)
    text: str = ""
    offs: list = field(default_factory=list)
    commentary_pieces: list = field(default_factory=list)  # comment paragraphs the pipeline attached to this record
    meta: dict = field(default_factory=dict)


@dataclass
class Replay:
    work: str
    path: str
    raw: str
    records: list
    dropped: list      # Piece-like dicts the pipeline discarded without any record
    headings: list     # structural headings (kitab/bab/juz) with offsets


def read_source(work):
    with open(SOURCES[work], "r", encoding="utf-8", newline="") as handle:
        return handle.read()


def iter_lines(raw):
    pos = 0
    for number, line in enumerate(raw.split("\n"), 1):
        yield number, pos, line.rstrip("\r")
        pos += len(line) + 1


def finish(rec: Record):
    parts = [(p.body, p.body_off) for p in rec.pieces if p.in_text]
    t = normalise_tracked(parts)
    rec.text, rec.offs = t.s, t.offs


def replay_rabi(raw):
    records, dropped, headings = [], [], []
    state = {"in_header": True, "num": "", "cur": None, "page": "", "para": 0, "last": "start"}
    cur_pieces = []

    def flush():
        cur = state["cur"]
        if cur is None:
            cur_pieces.clear()
            return
        finish(cur)
        text = cur.text
        num_str = state["num"].replace("مكرر", "").strip()
        try:
            n = int(num_str)
        except ValueError:
            n = 0
        if len(text) < 10:
            dropped.append({"reason": "shorter_than_10_chars", "id": cur.id, "text": text})
        else:
            cur.id = f"rabi_{n:04d}" + ("b" if "مكرر" in state["num"] else "")
            cur.label = state["num"]
            cur.meta["page_ref"] = state["page"]
            cur.meta["source_record_id"] = f"{cur.id}|{n}|{state['page']}"
            records.append(cur)
        state["cur"] = None
        state["num"] = ""

    for number, start, line in iter_lines(raw):
        end = start + len(line)
        if state["in_header"]:
            if line.strip() == "#META#Header#End#":
                state["in_header"] = False
            continue
        if not line.strip():
            continue
        pm = po.RE_PAGE.search(line)
        if pm:
            state["page"] = f"V{pm.group(1)}P{pm.group(2)}"
            if not po.RE_PAGE.sub("", line).strip():
                continue
        cur = state["cur"]
        m = po.RE_CONTINUATION.match(line)
        if m:
            kind = {"comment": "comment_cont", "rule": "footnote_cont", "footnote": "footnote_cont",
                    "heading": "heading_cont"}.get(state["last"], "cont")
            if cur is not None:
                cur.pieces.append(Piece(kind, start, end, number, m.group(1), start + m.start(1), True, state["para"]))
            elif state.get("hidden"):
                state["hidden"]["parts"].append((m.group(1), start + m.start(1)))
                state["hidden"]["raw_end"] = end
            continue
        state["hidden"] = None
        m = po.RE_RABI_BAB.match(line)
        if m:
            flush()
            headings.append({"kind": "bab", "line_no": number, "raw_start": start, "raw_end": end, "text": line})
            state["para"] += 1
            state["last"] = "bab"
            continue
        m = po.RE_RABI_HADITH.match(line)
        if m:
            flush()
            state["num"] = m.group(1)
            state["para"] += 1
            state["cur"] = Record("rabi", "?", pieces=[Piece("head", start, end, number, m.group(2), start + m.start(2), True, state["para"])])
            state["cur"].meta["page_at_start"] = state["page"]
            state["last"] = "head"
            continue
        m = po.RE_PARAGRAPH.match(line)
        if m:
            text = m.group(1)
            state["para"] += 1
            if "الجزء" in text or "القسم" in text:
                flush()
                is_heading = len(text) < 140
                headings.append({"kind": "juz" if is_heading else "lost_juz_paragraph", "line_no": number,
                                 "raw_start": start, "raw_end": end, "text": text, "length": len(text)})
                state["last"] = "heading"
                continue
            if text.startswith("قال الربيع"):
                piece = Piece("comment", start, end, number, text, start + m.start(1), False, state["para"])
                if records:  # pipeline bug: attaches to the previous *flushed* record, not the current one
                    records[-1].commentary_pieces.append(piece)
                if cur is not None:
                    cur.meta.setdefault("true_commentary", []).append(piece)
                state["last"] = "comment"
                continue
            if cur is not None:
                if re.match(r"^_{3,}\s*$", text):
                    kind = "rule"
                elif re.match(r"^\(\d+\)\s*\*", text):
                    kind = "footnote"
                elif state["last"] in ("rule", "footnote"):
                    kind = "footnote"
                elif state["last"] == "comment":  # page-break paragraph that continues the قال الربيع comment
                    kind = "comment_cont"
                elif text.startswith("كتاب") and len(text) < 80:
                    kind = "heading_para"
                else:
                    kind = "para"
                cur.pieces.append(Piece(kind, start, end, number, text, start + m.start(1), True, state["para"]))
                state["last"] = kind if kind in ("rule", "footnote") else ("comment" if kind == "comment_cont" else ("heading" if kind == "heading_para" else "para"))
            continue
        # a line that is none of the above (e.g. " PageV01P006 text") is silently dropped by the pipeline
        if po.RE_PAGE.sub("", line).strip():
            piece = Piece("orphan_dropped", start, end, number, line, start, False, state["para"])
            if cur is not None:
                cur.pieces.append(piece)
            else:
                hm = RE_HIDDEN_HEADER.match(line)
                item = {"reason": "numbered_report_dropped_whole" if hm else "unrecognised_line_outside_record", "text": line,
                        "raw_start": start, "raw_end": end, "line_no": number}
                if hm:  # «881) ...» behind a page marker: the pipeline saw no '#', so the whole report is lost
                    body_start = hm.end()
                    item.update(label=hm.group(1), parts=[(line[body_start:], start + body_start)])
                    state["hidden"] = item
                dropped.append(item)
    flush()
    for item in dropped:
        if "parts" in item:
            item["text"] = normalise_tracked(item.pop("parts")).s

    return Replay("rabi", SOURCES["rabi"], raw, records, dropped, headings)


def replay_zayd(raw):
    records, dropped, headings = [], [], []
    state = {"in_header": True, "pieces": [], "kitab": 0, "bab": 0, "hn": 0, "page": ""}

    def flush():
        pieces = state["pieces"]
        state["pieces"] = []
        if not pieces:
            return
        rec = Record("zayd", "?", pieces=pieces)
        finish(rec)
        text = rec.text
        if len(text) < 10:  # pipeline quirk: returns WITHOUT clearing, so this text is prefixed onto the next record
            dropped.append({"reason": "shorter_than_10_chars_kept_as_prefix_of_next", "text": text, "raw_start": pieces[0].raw_start})
            state["pieces"] = pieces
            return
        if text.startswith("بسم الله") or text.startswith("الحمدلله"):
            dropped.append({"reason": "preamble", "text": text[:80], "raw_start": pieces[0].raw_start})
            return
        state["hn"] += 1
        rec.id = f"zayd_{state['hn']:04d}"
        rec.label = str(state["hn"])
        rec.meta["page_ref"] = state["page"]
        rec.meta["source_record_id"] = f"{rec.id}|{state['hn']}|{state['page']}"
        records.append(rec)

    for number, start, line in iter_lines(raw):
        end = start + len(line)
        if state["in_header"]:
            if line.strip() == "#META#Header#End#":
                state["in_header"] = False
            continue
        if not line.strip():
            continue
        pm = po.RE_PAGE.search(line)
        if pm:
            state["page"] = f"V{pm.group(1)}P{pm.group(2)}"
            if not po.RE_PAGE.sub("", line).strip():
                continue
        m = po.RE_KITAB.match(line)
        if m:
            flush()
            headings.append({"kind": "kitab", "line_no": number, "raw_start": start, "raw_end": end, "text": line})
            continue
        m = po.RE_BAB.match(line)
        if m:
            flush()
            headings.append({"kind": "bab", "line_no": number, "raw_start": start, "raw_end": end, "text": line})
            continue
        m = po.RE_CONTINUATION.match(line)
        if m:
            state["pieces"].append(Piece("cont", start, end, number, m.group(1), start + m.start(1), True))
            continue
        m = po.RE_PARAGRAPH.match(line)
        if m:
            text = m.group(1)
            if po.ZAYD_APPENDIX_MARKER in text:
                flush()
                break
            if po.RE_ZAYD_HADITH_START.search(text[:30]) and "".join(p.body for p in state["pieces"]).strip():
                flush()
            state["pieces"].append(Piece("head" if not state["pieces"] else "para", start, end, number, text, start + m.start(1), True))
            continue
        if RE_ORPHAN_PAGE_NUMBER.match(po.RE_PAGE.sub("", line)):
            continue
        dropped.append({"reason": "unrecognised_line", "text": line, "raw_start": start, "line_no": number})
    flush()
    return Replay("zayd", SOURCES["zayd"], raw, records, dropped, headings)


def replay_rida(raw):
    records, dropped, headings = [], [], []
    state = {"in_header": True, "in_app": False, "pieces": [], "bab": 0, "hn": 0, "page": ""}

    def flush():
        pieces = state["pieces"]
        state["pieces"] = []
        if not pieces:
            return
        rec = Record("rida", "?", pieces=pieces)
        finish(rec)
        text = rec.text
        if len(text) < 15:
            dropped.append({"reason": "shorter_than_15_chars", "text": text, "raw_start": pieces[0].raw_start})
            return
        if text.startswith("بسم الله") or text.startswith("الحمد لله"):
            dropped.append({"reason": "preamble", "text": text[:80], "raw_start": pieces[0].raw_start})
            return
        if "أما بعد، فهذه صحيفة" in text or "هذه الصحيفة ويسمى" in text:
            dropped.append({"reason": "biographical_introduction", "text": text[:80], "raw_start": pieces[0].raw_start})
            return
        state["hn"] += 1
        rec.id = f"rida_{state['hn']:04d}"
        rec.label = str(state["hn"])
        rec.meta["page_ref"] = state["page"]
        rec.meta["source_record_id"] = f"{rec.id}|{state['hn']}|{state['page']}"
        records.append(rec)

    for number, start, line in iter_lines(raw):
        end = start + len(line)
        if state["in_header"]:
            if line.strip() == "#META#Header#End#":
                state["in_header"] = False
            continue
        if not state["in_app"]:
            if po.ZAYD_APPENDIX_MARKER in line:
                state["in_app"] = True
            continue
        if not line.strip():
            continue
        pm = po.RE_PAGE.search(line)
        if pm:
            state["page"] = f"V{pm.group(1)}P{pm.group(2)}"
            if not po.RE_PAGE.sub("", line).strip():
                continue
        m = po.RE_BAB.match(line) or po.RE_KITAB.match(line)
        if m:
            flush()
            headings.append({"kind": "bab", "line_no": number, "raw_start": start, "raw_end": end, "text": line})
            continue
        m = po.RE_CONTINUATION.match(line)
        if m:
            state["pieces"].append(Piece("cont", start, end, number, m.group(1), start + m.start(1), True))
            continue
        m = po.RE_PARAGRAPH.match(line)
        if m:
            text = m.group(1)
            starts_new = (po.RE_ZAYD_HADITH_START.search(text[:30]) or text.lstrip().startswith("وباسناده")
                          or text.lstrip().startswith("الباب "))
            if text.lstrip().startswith("الباب "):
                flush()
                headings.append({"kind": "bab_paragraph", "line_no": number, "raw_start": start, "raw_end": end, "text": text})
                continue
            if starts_new and "".join(p.body for p in state["pieces"]).strip():
                flush()
            state["pieces"].append(Piece("head" if not state["pieces"] else "para", start, end, number, text, start + m.start(1), True))
            continue
        dropped.append({"reason": "unrecognised_line", "text": line, "raw_start": start, "line_no": number})
    flush()
    return Replay("rida", SOURCES["rida"], raw, records, dropped, headings)


REPLAYS = {"rabi": replay_rabi, "zayd": replay_zayd, "rida": replay_rida}


def replay(work):
    return REPLAYS[work](read_source(work))


# --------------------------------------------------------------------------- production snapshot
def work_of(record_id: str) -> str:
    return record_id.split(":")[-1].split("_")[0]


def load_snapshot(path=SNAPSHOT):
    rows = {}
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            short = row["source_record_id"].split("|")[0]
            row["short_id"] = short
            row["work"] = short.split("_")[0]
            rows[row["source_record_id"]] = row
    return rows


# --------------------------------------------------------------------------- source paragraph stream
def paragraph_stream(raw):
    """Whole-document paragraphs (a '#'/'###' line plus its '~~' and orphan continuation lines), normalised.

    Each: {raw_start, raw_end, line_no, kind (para|heading), text}. Used for source windows and substring validation.
    """
    out, cur, in_header = [], None, True
    for number, start, line in iter_lines(raw):
        if in_header:
            if line.strip() == "#META#Header#End#":
                in_header = False
            continue
        stripped = po.RE_PAGE.sub("", line)
        if not stripped.strip():
            continue
        if line.startswith("#"):
            if cur is not None:
                out.append(cur)
            cur = {"raw_start": start, "raw_end": start + len(line), "line_no": number,
                   "kind": "heading" if line.startswith("###") else "para", "lines": [line]}
        elif cur is not None and not RE_ORPHAN_PAGE_NUMBER.match(stripped):
            cur["lines"].append(line)
            cur["raw_end"] = start + len(line)
    if cur is not None:
        out.append(cur)
    for p in out:
        body = " ".join(re.sub(r"^(###\s*\|*\s*|#\s*|~~\s*)", "", ln) for ln in p.pop("lines"))
        p["text"] = normalise_plain(body)
    return out


def locate(needle: str, haystack: str, start=0):
    i = haystack.find(needle, start)
    return i if i >= 0 else None


def raw_span_of(rec: Record, a: int, b: int):
    """Raw offsets of rec.text[a:b]."""
    if not rec.offs or a >= b:
        return None
    return rec.offs[a], rec.offs[b - 1] + 1
