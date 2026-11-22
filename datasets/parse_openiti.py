#!/usr/bin/env python3
"""
parse_openiti.py — Parse OpenITI mARkdown files into structured hadith JSON/CSV
================================================================================

This is the primary text source for Zaydi and Ibadi hadith collections.
The text comes from community-proofread Shamela libraries (not OCR).

Source:
  - Musnad Zayd: OpenITI 0122ZaydIbnCali.Musnad.Zaydiyya0000052-ara1.mARkdown
    From: Maktaba Shamila al-Zaydiyya (community-typed, not OCR)
  - Jami al-Sahih (Musnad al-Rabi): OpenITI 0170RabicIbnHabibAzdi.JamicSahih.ShamIbadiyya0000155-ara1
    From: Maktaba Shamila al-Ibadiyya (community-typed, not OCR)

OpenITI mARkdown format reference:
  ### |    = kitab (book) heading
  ### ||   = bab (chapter) heading
  #        = paragraph start (hadith text, commentary)
  ~~       = continuation of previous line
  PageV01P### = page marker (volume 1, page ###)
  ms###    = milestone marker (every ~300 words)

Usage:
    python parse_openiti.py                          # Parse both collections
    python parse_openiti.py --zayd-only              # Just Musnad Zayd
    python parse_openiti.py --rabi-only              # Just Musnad al-Rabi
    python parse_openiti.py --output-dir output/     # Custom output directory

Output per collection:
    parsed_hadiths.json  — structured hadith records with provenance
    hadiths_clean.csv    — minimal CSV (id, source, chapter, text_ar, tradition)
    hadiths_full.csv     — full schema CSV for unified dataset integration
    PROVENANCE.json      — transformation metadata (source URI, parse date, counts)

The extraction model (blocks, footnotes/commentary, splits, sanad/matn, id anchoring) is documented in
hadith-data/extraction-quality/fixed/AGENTS.md; the sections below only carry one-line "what" comments.
"""

import argparse
import bisect
import csv
import json
import os
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import cached_property

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OPENITI_DIR = os.path.join(SCRIPT_DIR, "hadith-data", "openiti-sources")


# ---------------------------------------------------------------------------
# mARkdown format patterns
# ---------------------------------------------------------------------------

# Structural headings
RE_KITAB = re.compile(r'^###\s*\|\s+(.+)')           # ### |  كتاب الطهارة
RE_BAB = re.compile(r'^###\s*\|\|\s+(.+)')            # ### || باب في ذكر الوضوء
RE_PARAGRAPH = re.compile(r'^#\s+(.+)')               # # paragraph text
RE_CONTINUATION = re.compile(r'^~~\s*(.*)')            # ~~ continuation
RE_PAGE = re.compile(r'PageV(\d+)P(\d+)')             # PageV01P049
RE_MILESTONE = re.compile(r'\bms(\d+)\b')             # ms001
RE_META = re.compile(r'^#META#')                      # metadata header
RE_OPENITI_HEADER = re.compile(r'^######OpenITI#')    # file header

# Rabi-specific: numbered hadiths like "# 1) ..." or "# 1مكرر) ..."
RE_RABI_HADITH = re.compile(r'^#\s*(\d+(?:مكرر)?)\)\s*\.{0,3}\s*(.*)')
RE_RABI_BAB = re.compile(r'^#\s*\[(\d+)\]\s+باب\s+(.*)')
RE_RABI_BAB_ANY = re.compile(r'^#\s*\[(\d+)\]\s*باب[\s:]*(.*)$')   # also '# [35] باب' (title lost) and '# [8] باب: ...'
# Rabi: a numbered header the edition printed behind a page marker (no leading '#'), e.g. " PageV01P247 881) ..."
RE_RABI_HIDDEN_HEADER = re.compile(r'^\s*(?:PageV\d+P\d+\s+)?(\d+(?:مكرر)?)\)\s*\.{0,3}\s*(.*)')

# Zayd-specific: hadith starts with حدثني or وحدثني or وقال or وسألت
RE_ZAYD_HADITH_START = re.compile(
    r'(?:حد[ثتئ](?:ني|نا)|وحد[ثتئ]|وقال\s+زيد|وسأل|سألت|قال\s+أبو\s*خالد)',
    re.UNICODE
)

# Cutoff: the reviewer noted page 434+ is a different text (Musnad Imam Ali al-Rida)
ZAYD_APPENDIX_MARKER = "مسند الإمام علي الرضا"

AR = "ء-ي"
NOT_AR_BEFORE = rf"(?<![{AR}])"


# ---------------------------------------------------------------------------
# Text normalization (minimal — preserve original, normalize for consistency)
# ---------------------------------------------------------------------------

def normalize_arabic(text: str) -> str:
    """Light normalization: NFKC + strip control chars. Does NOT strip tashkeel."""
    text = unicodedata.normalize('NFKC', text)
    # Remove zero-width and bidi control characters
    for ch in '‏‎‌​‍‬‫‪⁩⁨⁦⁧﻿':
        text = text.replace(ch, '')
    # Remove page markers and milestones from text body
    text = RE_PAGE.sub('', text)
    text = RE_MILESTONE.sub('', text)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def strip_footnote_markers(text: str) -> str:
    """Remove inline footnote markers like (1), (2), (¬1) from text."""
    text = re.sub(r'\(¬?\d+\)', '', text)
    return re.sub(r'\s+', ' ', text).strip()


RE_EDITION_EQUALS = re.compile(r'(?<!\S)و?=(?!\S)')       # zayd edition marker "=" (and the "و=" glue)
RE_EDITION_STAR = re.compile(r'(?<!\S)\*+(?![^\s.،:؛])')       # lone "*" footnote/edition marker (also before a full stop)
RE_LEADING_LATIN_V = re.compile(r'^V(?=[' + AR + r'])')     # "Vسألت": a stray Latin V glued to the first word


def normalise_block(raw: str) -> str:
    """The pipeline's existing normalisation (NFKC, controls, page/milestone markers, footnote markers)."""
    return strip_footnote_markers(normalize_arabic(raw))


def strip_edition_markers(text: str) -> str:
    """Remove edition markers that are not text: leading V, '=' and lone '*'. Never touches Arabic letters."""
    text = RE_LEADING_LATIN_V.sub('', text.strip())
    text = RE_EDITION_EQUALS.sub(' ', text)
    text = RE_EDITION_STAR.sub(' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def clean_text(raw: str) -> str:
    return strip_edition_markers(normalise_block(raw))


def collapse_ws(text: str) -> str:
    return " ".join(text.split())


def is_terminal(text: str) -> bool:
    """True when the text ends a sentence (so the next paragraph is a new one, not a page-break continuation)."""
    return bool(re.search(r'[.»؟!]["”)]*\s*$', text.strip()))


# ---------------------------------------------------------------------------
# Block reader: '#' paragraphs and '###' headings with their '~~' and orphan continuation lines
# ---------------------------------------------------------------------------

RE_ORPHAN_PAGE_NUMBER = re.compile(r'^\s*\[\s*\d+\s*\]\s*$')


@dataclass
class Block:
    kind: str                       # 'para' | 'heading'
    level: str                      # heading level: 'kitab' | 'bab' | '' for paragraphs
    parts: list                     # [(text_without_prefix, line_no)] for every source line of the block
    first_raw: str                  # the raw first source line (regexes of the legacy parser run on it)
    first_line: int
    last_line: int
    page: str                       # page marker in force after the first line
    page_break_before: bool         # a page-only marker line sat between the previous block and this one
    label: str = ""                 # rabi numbered header label ("140", "1مكرر"); "" otherwise
    hidden: bool = False            # numbered header recovered from a line without '#'

    @cached_property
    def text(self) -> str:
        return clean_text(" ".join(text for text, _line in self.parts))

    @property
    def first_text(self) -> str:
        """The first source line's text as the legacy parser saw it (before any cleaning)."""
        m = RE_PARAGRAPH.match(self.first_raw)
        return m.group(1) if m else self.parts[0][0]


def read_blocks(path, numbered_re=None, hidden_re=None, start_marker=None, stop_marker=None):
    """Read a mARkdown file into blocks. Orphan lines (no '#'/'~~') continue the current block instead of vanishing."""
    with open(path, 'r', encoding='utf-8') as handle:
        lines = handle.read().split('\n')
    blocks, current, page = [], None, ""
    in_header, started, pending_break = True, start_marker is None, False
    for number, raw in enumerate(lines, 1):
        raw = raw.rstrip('\r')
        if in_header:
            if raw.strip() == '#META#Header#End#':
                in_header = False
            continue
        page_match = RE_PAGE.search(raw)
        if page_match:
            page = f"V{page_match.group(1)}P{page_match.group(2)}"
        if not started:
            if start_marker in raw:
                started = True
            continue
        if not raw.strip():
            continue
        if page_match and not RE_PAGE.sub('', raw).strip():
            pending_break = True
            continue

        def open_block(kind, level, text, label="", hidden=False):
            nonlocal current, pending_break
            current = Block(kind, level, [(text, number)], raw, number, number, page, pending_break, label, hidden)
            blocks.append(current)
            pending_break = False

        m = RE_KITAB.match(raw)
        if m:
            open_block('heading', 'kitab', m.group(1))
            continue
        m = RE_BAB.match(raw)
        if m:
            open_block('heading', 'bab', m.group(1))
            continue
        m = RE_CONTINUATION.match(raw)
        if m:
            if current is not None:
                current.parts.append((m.group(1), number))
                current.last_line = number
            continue
        m = RE_PARAGRAPH.match(raw)
        if m:
            text = m.group(1)
            if stop_marker and stop_marker in text:
                break
            numbered = numbered_re.match(raw) if numbered_re else None
            if numbered:
                open_block('para', '', numbered.group(2), label=numbered.group(1))
            else:
                open_block('para', '', text)
            continue
        if raw.lstrip().startswith('#'):
            continue  # an empty '### |' line: nothing to keep
        stripped = RE_PAGE.sub('', raw).strip()
        if RE_ORPHAN_PAGE_NUMBER.match(stripped):
            continue
        hidden = hidden_re.match(raw) if hidden_re else None
        if hidden:
            open_block('para', '', hidden.group(2), label=hidden.group(1), hidden=True)
        elif current is not None:
            current.parts.append((stripped, number))
            current.last_line = number
    return blocks


def build_haystack(blocks) -> str:
    """The source after normalisation and marker stripping, one space between blocks: what every emitted string must be a substring of."""
    return collapse_ws(" ".join(block.text for block in blocks))


# ---------------------------------------------------------------------------
# Legacy segmentation: replayed only to keep ids and page_ref stable (see fixed/AGENTS.md "id anchoring")
# ---------------------------------------------------------------------------

@dataclass
class LegacySpan:
    id: str
    hadith_no: int
    page_ref: str
    first_line: int
    last_line: int


class LegacyIndex:
    def __init__(self, spans):
        self.spans = sorted(spans, key=lambda s: s.first_line)
        self._starts = [s.first_line for s in self.spans]

    def containing(self, line_no):
        k = bisect.bisect_right(self._starts, line_no) - 1
        if k >= 0 and self.spans[k].first_line <= line_no <= self.spans[k].last_line:
            return self.spans[k]
        return None

    def by_first_line(self, line_no):
        k = bisect.bisect_left(self._starts, line_no)
        if k < len(self.spans) and self.spans[k].first_line == line_no:
            return self.spans[k]
        return None


def legacy_spans(source_path: str, work: str) -> LegacyIndex:
    """Replay the pre-fix record boundaries of `work` ('rabi' | 'zayd' | 'rida'): id, hadith_no, page_ref (page at flush), line span."""
    with open(source_path, 'r', encoding='utf-8') as handle:
        lines = handle.read().split('\n')
    spans, state = [], {"text": "", "start": None, "num": "", "hn": 0, "page": ""}
    min_len = {"rabi": 10, "zayd": 10, "rida": 15}[work]
    in_header, in_appendix = True, work != "rida"

    def flush(trigger_line):
        text_raw = state["text"]
        if work == "rabi":
            num, state["num"] = state["num"], ""
            if not text_raw.strip() or not num:
                state["text"], state["start"] = "", None
                return
        elif not text_raw.strip():
            return
        text = normalise_block(text_raw)
        if len(text) < min_len:
            if work != "zayd":  # zayd legacy quirk: the short text stays and becomes a prefix of the next record
                state["text"], state["start"] = "", None
            return
        if work == "rabi":
            num_str = num.replace('مكرر', '').strip()
            try:
                value = int(num_str)
            except ValueError:
                value = 0
            spans.append(LegacySpan(f"rabi_{value:04d}" + ("b" if "مكرر" in num else ""), value, state["page"],
                                    state["start"], trigger_line - 1))
        else:
            if work == "zayd" and (text.startswith('بسم الله') or text.startswith('الحمدلله')):
                state["text"], state["start"] = "", None
                return
            if work == "rida" and (text.startswith('بسم الله') or text.startswith('الحمد لله')
                                   or 'أما بعد، فهذه صحيفة' in text or 'هذه الصحيفة ويسمى' in text):
                state["text"], state["start"] = "", None
                return
            state["hn"] += 1
            spans.append(LegacySpan(f"{work}_{state['hn']:04d}", state["hn"], state["page"], state["start"], trigger_line - 1))
        state["text"], state["start"] = "", None

    for number, raw in enumerate(lines, 1):
        raw = raw.rstrip('\r')
        if in_header:
            if raw.strip() == '#META#Header#End#':
                in_header = False
            continue
        if not in_appendix:
            if ZAYD_APPENDIX_MARKER in raw:
                in_appendix = True
            continue
        if not raw.strip():
            continue
        page_match = RE_PAGE.search(raw)
        if page_match:
            state["page"] = f"V{page_match.group(1)}P{page_match.group(2)}"
            if not RE_PAGE.sub('', raw).strip():
                continue
        if work == "rabi":
            m = RE_CONTINUATION.match(raw)
            if m:
                state["text"] += " " + m.group(1)
                continue
            if RE_RABI_BAB.match(raw):
                flush(number)
                continue
            m = RE_RABI_HADITH.match(raw)
            if m:
                flush(number)
                state["num"], state["text"], state["start"] = m.group(1), m.group(2), number
                continue
            m = RE_PARAGRAPH.match(raw)
            if m:
                text = m.group(1)
                if 'الجزء' in text or 'القسم' in text:
                    flush(number)
                    continue
                if text.startswith('قال الربيع'):
                    continue
                if state["num"]:
                    state["text"] += " " + text
            continue
        if RE_BAB.match(raw) or RE_KITAB.match(raw):
            flush(number)
            continue
        m = RE_CONTINUATION.match(raw)
        if m:
            if not state["text"]:
                state["start"] = number
            state["text"] += " " + m.group(1)
            continue
        m = RE_PARAGRAPH.match(raw)
        if m:
            text = m.group(1)
            if work == "zayd" and ZAYD_APPENDIX_MARKER in text:
                flush(number)
                break
            if work == "rida" and text.lstrip().startswith('الباب '):
                flush(number)
                continue
            starts_new = RE_ZAYD_HADITH_START.search(text[:30]) or (work == "rida" and text.lstrip().startswith('وباسناده'))
            if starts_new and state["text"].strip():
                flush(number)
            if state["text"]:
                state["text"] += " " + text
            else:
                state["text"], state["start"] = text, number
    flush(len(lines) + 1)
    return LegacyIndex(spans)


# ---------------------------------------------------------------------------
# Isnad / matn split (Arabic spans, verbatim)
# ---------------------------------------------------------------------------

CHAIN_VERB = r"(?:و?(?:حدثني|حدثنا|حدثتني|أخبرني|أخبرنا|أنبأنا|أنبأني|بلغني|بلغنا|سمعت|سمعنا|روى|رواه)|عن\b)"
RE_CHAIN_VERB_AT = re.compile(rf"^\s*{CHAIN_VERB}")
RE_SAID = re.compile(rf"{NOT_AR_BEFORE}(?:أنه\s+قال|أنها\s+قالت|فقال|وقال|قالت|قال|يقول)(?![{AR}])\s*(:)?")
RE_CONTINUATION_CHAIN = re.compile(
    rf"^(?:{NOT_AR_BEFORE}و?(?:بهذا|بنفس|بذلك)\s+(?:السند|الإسناد|الاسناد)|ومن\s+طريقه|وباسناده|وبإسناده|وبسنده|وباسنادهم)")
RE_ATTRIBUTION = re.compile(
    rf"^(?:قال|فقال|وقال)\s+(?:رسول\s+الله|النبيء?|النبي)\s*(?:صلى\s+الله\s+عليه(?:\s+و?(?:على\s+)?آله)?(?:\s+وسلم)?)?\s*:?\s*")
RE_ATTR_COLON = re.compile(
    rf"{NOT_AR_BEFORE}(?:عن|أن)\s+(?:رسول\s+الله|النبيء?|النبي)\s*(?:صلى\s+الله\s+عليه(?:\s+و?(?:على\s+)?آله)?(?:\s+وسلم)?)?\s*:")
RE_VERB_START = re.compile(rf"^(?:قال|فقال|وقال|قالت|يقول|قالوا)(?![{AR}])")
RE_CHAIN_ANY = re.compile(
    rf"{NOT_AR_BEFORE}عن\b|حدثني|حدثنا|أخبرنا|أخبرني|بلغني|بلغنا|سمعت|أنبأنا|السند|الإسناد|وباسناده|وبإسناده")
RE_NAME_LED = re.compile(r"^\s*(?:أبو|ابو|ابن)\s")
RE_ZAYD_FORMULA = re.compile(
    r"^(?:حدثني|حدثنا)\s+زيد\s+بن\s+علي\s+(?:عن|عليه\s+السلام\s+عن)\s+أبيه(?:\s+علي\s+بن\s+الحسين(?:\s+عليه\s+السلام)?)?"
    r"(?:\s+عن\s+جده(?:\s+الحسين(?:\s+بن\s+علي)?)?(?:\s+عن\s+(?:أمير\s+المؤمنين\s+)?علي(?:\s+بن\s+أبي\s+طالب)?)?)?"
    r"(?:\s*\(ع\s*م\)|\s+عليهم?\s+السلام)?")
RE_ENDS_IN_CHAIN = re.compile(
    rf"(?:{NOT_AR_BEFORE}قال\s*:?\s*$|{NOT_AR_BEFORE}(?:حدثني|حدثنا|أخبرنا|أخبرني)\s+[^.:«»]{{1,40}}$)")


def split_chain_matn(text: str) -> dict:
    """Deterministic isnad/matn split: the closing «قال:» (and a following «رسول الله ...» attribution) stays on the sanad side.

    Returns {sanad_end, matn_start, confidence, kind}; kind in no_chain | chain_only | continuation_chain | chain_and_matn.
    Confidence is "high" only when a colon, an opening quote or a prophetic attribution follows the closing verb.
    """
    out = {"sanad_end": 0, "matn_start": 0, "confidence": "none", "kind": "no_chain"}
    body = text
    if re.match(r"^\s*و?سأل", body):  # a question put to the imam: no isnad
        return out
    cont = RE_CONTINUATION_CHAIN.match(body)
    formula = RE_ZAYD_FORMULA.match(body)
    if formula and not re.match(rf"^[\s.،,:؛]*(?:أنه\s+)?(?:قال|فقال|وقال|يقول)(?![{AR}])", body[formula.end():]):
        rest = body[formula.end():]
        if len(rest.strip()) >= 6:
            end_at = formula.end() + len(rest) - len(rest.lstrip(" .،,:؛"))     # trailing punctuation stays on the sanad
            skip = len(body[end_at:]) - len(body[end_at:].lstrip())
            out.update(sanad_end=end_at, matn_start=end_at + skip, confidence="high", kind="chain_and_matn")
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
        internal = bool(RE_CHAIN_VERB_AT.match(after)) or after.lstrip().startswith("=") or bool(
            re.match(r"\s*(?:قال|فقال)\s+(?:حدثني|حدثنا|أخبرنا|أخبرني)", after))
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
    while end < len(body) and body[end] in ".،,:؛":
        end += 1                                                              # punctuation after the closing verb stays on the sanad
    matn_start = end + (len(body[end:]) - len(body[end:].lstrip()))
    out.update(sanad_end=end, matn_start=matn_start, confidence=confidence,
               kind="continuation_chain" if cont else "chain_and_matn")
    if len(text[matn_start:].strip()) < 6:
        out.update(kind="chain_only")
    return out


def sanad_matn_fields(text: str) -> dict:
    """sanad_ar / matn_ar (verbatim, never cut mid-word) plus split_confidence and split_kind; both null when not confident."""
    split = split_chain_matn(text)
    fields = {"sanad_ar": None, "matn_ar": None, "split_confidence": "low", "split_kind": split["kind"]}
    if split["kind"] in ("chain_and_matn", "continuation_chain") and split["confidence"] == "high":
        sanad, matn = text[:split["sanad_end"]].strip(), text[split["matn_start"]:].strip()
        if (sanad and matn and _cut_is_on_word_boundary(text, split["sanad_end"])
                and not RE_VERB_START.match(matn) and not re.match(r"^[.،,:؛]", matn)):
            fields.update(sanad_ar=sanad, matn_ar=matn, split_confidence="high")
    elif split["kind"] == "no_chain" and text.strip():
        if re.match(r"^\s*و?سأل", text) or not (RE_CHAIN_ANY.search(text[:300]) or RE_NAME_LED.match(text) or RE_VERB_START.match(text)):
            fields.update(sanad_ar="", matn_ar=text.strip(), split_confidence="high")   # no isnad at all
        else:
            fields["split_kind"] = "unsplit"                                              # a chain is there but no confident cut
    return fields


def _cut_is_on_word_boundary(text: str, cut: int) -> bool:
    left, right = text[cut - 1:cut], text[cut:cut + 1]
    return not (left and right and re.match(f'[{AR}]', left) and re.match(f'[{AR}]', right))


def continues_previous_chain(text: str) -> bool:
    return bool(RE_CONTINUATION_CHAIN.match(text))


def ends_inside_chain(text: str) -> bool:
    return len(text) > 30 and bool(RE_ENDS_IN_CHAIN.search(text[-90:]))


def chain_opener_tail(text: str):
    """(report_text, tail) when the text ends with the next report's chain opener («... فاغسله. (حدثني) أبو خالد قال:»), else None."""
    m_end = RE_ENDS_IN_CHAIN.search(text)
    if not m_end:
        return None
    cut = text.rfind(". ", 0, m_end.start())
    if cut > 0 and len(text) - cut <= 220:
        return text[:cut + 1], text[cut + 2:]
    return None


# ---------------------------------------------------------------------------
# Shared assembly: ids, merges, sanad/matn, verification
# ---------------------------------------------------------------------------

def empty_report(**kwargs) -> dict:
    report = {
        "kind": "report", "text": "", "anchor_line": 0, "label": "", "chunk": -1,
        "blk_first": -1, "blk_last": -1, "page_start": "", "contiguous": False,
        "footnotes": [], "commentary": [], "commentary_kinds": [], "footnote_marker_count": 0,
        "context": {}, "line_start": 0, "line_end": 0,
    }
    report.update(kwargs)
    return report


def assign_ids(work, reports, legacy: LegacyIndex):
    """First report of a legacy record keeps its id; later ones in the same legacy record get '#2', '#3' (rabi uses its own numbering)."""
    seen = {}
    for report in reports:
        if work == "rabi":
            num_str = report["label"].replace('مكرر', '').strip()
            number = int(num_str) if num_str.isdigit() else 0
            report["id"] = f"rabi_{number:04d}" + ("b" if "مكرر" in report["label"] else "")
            report["hadith_no"] = number
            span = legacy.by_first_line(report["anchor_line"])
            report["page_ref"] = span.page_ref if span and span.id == report["id"] else report["page_start"]
            report["legacy_id"] = span.id if span else None
            continue
        span = legacy.containing(report["anchor_line"])
        if span is None:
            report["id"], report["hadith_no"], report["page_ref"], report["legacy_id"] = None, None, report["page_start"], None
            continue
        count = seen.get(span.id, 0) + 1
        seen[span.id] = count
        report["id"] = span.id if count == 1 else f"{span.id}#{count}"
        report["hadith_no"], report["page_ref"], report["legacy_id"] = span.hadith_no, span.page_ref, span.id
        if count == 1 and report.get("chunk_lines"):
            first, last = report["chunk_lines"]
            report["absorbed_ids"] = [other.id for other in legacy.spans if first <= other.first_line <= last and other.id != span.id]
    alive = {report["legacy_id"] for report in reports}
    for report in reports:
        if report.get("absorbed_ids"):
            report["absorbed_ids"] = [legacy_id for legacy_id in report["absorbed_ids"] if legacy_id not in alive]


def merge_chain_fragments(reports):
    """Zayd/rida: a chain-only fragment (or a record ending inside a chain) opens the adjacent next report.

    chain_only: merged into the next report (first id kept, absorbed id recorded); a trailing chain opener glued to the end of a
    report moves to the next one as its prefix when a clean sentence boundary exists, otherwise the two reports are merged.
    """
    out, i = [], 0
    while i < len(reports):
        report = reports[i]
        nxt = reports[i + 1] if i + 1 < len(reports) else None
        # a next report that itself opens with a continuation chain («وباسناده ...») is a new report, never the body of this fragment
        adjacent = bool(nxt) and nxt["contiguous"] and not continues_previous_chain(nxt["text"])
        if nxt and adjacent:
            text = report["text"]
            fragment = split_chain_matn(text)["kind"] == "chain_only"
            if fragment or ends_inside_chain(text):
                moved = None if fragment else chain_opener_tail(text)
                if moved:
                    report["text"] = moved[0]
                    nxt["text"] = moved[1] + " " + nxt["text"]
                    nxt["prefix_from_id"] = report["id"]
                else:
                    report["text"] = text + " " + nxt["text"]
                    report.setdefault("absorbed_ids", []).append(nxt["id"])
                    report["absorbed_ids"] += nxt.get("absorbed_ids", [])
                    report["line_end"] = nxt["line_end"]
                    report["blk_last"] = nxt["blk_last"]
                    report["footnotes"] += nxt["footnotes"]
                    report["commentary"] += nxt["commentary"]
                    report["commentary_kinds"] += nxt["commentary_kinds"]
                    reports[i + 1] = report  # the merged report is re-examined against the one after it
                    i += 1
                    continue
        out.append(report)
        i += 1
    return out


def finish_records(work, reports, base_fields, haystack):
    """Turn internal reports into the output records and verify every emitted string against the source haystack."""
    records, failures, checked = [], [], 0
    previous_id = None
    for report in reports:
        text = report["text"]
        fields = sanad_matn_fields(text)
        inherits = previous_id if continues_previous_chain(text) else None
        record = {
            "id": report["id"],
            "hadith_no": report["hadith_no"],
            **base_fields,
            **report["context"],
            "text_ar": text,
            "sanad_ar": fields["sanad_ar"],
            "matn_ar": fields["matn_ar"],
            "sanad_inherits_from": inherits,
            "split_confidence": fields["split_confidence"],
            "split_kind": fields["split_kind"],
            "footnotes": report["footnotes"],
            "footnote_markers_without_text": report["footnote_marker_count"],
            "commentary": report["commentary"],
            "commentary_kinds": report["commentary_kinds"],
            "absorbed_ids": report.get("absorbed_ids", []),
            "prefix_from_id": report.get("prefix_from_id"),
            "split_from": report["id"].split("#")[0] if "#" in report["id"] else None,
            "page_ref": report["page_ref"],
            "page_start": report["page_start"],
            "line_start": report["line_start"],
            "line_end": report["line_end"],
            "legacy_id": report["legacy_id"],
        }
        if work == "rabi":
            record["hadith_label"] = report["label"]
        records.append(record)
        previous_id = report["id"]
        for key in ("text_ar", "sanad_ar", "matn_ar"):
            value = record[key]
            if value:
                checked += 1
                if collapse_ws(value) not in haystack:
                    failures.append({"id": record["id"], "field": key, "excerpt": value[:80]})
        for key in ("footnotes", "commentary"):
            for index, value in enumerate(record[key]):
                checked += 1
                if collapse_ws(value) not in haystack:
                    failures.append({"id": record["id"], "field": f"{key}[{index}]", "excerpt": value[:80]})
    return records, {"strings_checked": checked, "failures": failures}


# ---------------------------------------------------------------------------
# Parse Musnad al-Rabi / Jami al-Sahih (numbered hadiths with [N] bab markers)
# ---------------------------------------------------------------------------

RE_RABI_GLOSS = re.compile(r'(?<=[.»؟!])\s+و?قال\s+الربيع\s*:')           # «...». قال الربيع: ...  inside a report paragraph
RE_RABI_SECTION_HEADING = re.compile(r'^(?:كتاب|باب|ما جاء|ما ذكر|زيادة|تتمة|فصل|فائدة|خاتمة)(?![' + AR + r'])')
EDITORIAL_HEADINGS = {"تنبيه", "تتمة", "فصل", "فائدة", "خاتمة", "مسألة", "تنبيه:", "فصل:"}
RE_FOOTNOTE_STAR = re.compile(r'^\(\d+\)\s*\*')


def is_section_heading(text: str) -> bool:
    """A short stand-alone title paragraph («كتاب الصوم», «ما جاء في التقية»): no sentence punctuation, at most 80 characters."""
    return len(text) <= 80 and bool(RE_RABI_SECTION_HEADING.match(text)) and not re.search(r'[.:؟«»]', text)


class _RabiRecord:
    def __init__(self, block, idx, context):
        self.label, self.first_line, self.last_line = block.label, block.first_line, block.last_line
        self.blk_first = self.blk_last = idx
        self.page_start = block.page
        self.context = context
        self.body = [block.text]
        self.mode = "body"                      # body | footnote | tail | editorial
        self.footnotes, self.markers = [], 0
        self.tail = []                          # [{"kind", "text"}]
        self._gloss_check(block)

    def _gloss_check(self, block):
        text = self.body[-1]
        m = RE_RABI_GLOSS.search(text)
        if m:
            self.body[-1] = text[:m.start()].strip()
            self.tail.append({"kind": "gloss", "text": text[m.start():].strip()})
            self.mode = "tail"

    def touch(self, idx, block):
        self.blk_last, self.last_line = idx, block.last_line

    def add_tail(self, kind, text, continuation=False):
        if continuation and self.tail:
            self.tail[-1]["text"] = (self.tail[-1]["text"] + " " + text).strip()
        else:
            self.tail.append({"kind": kind, "text": text})


def parse_rabi(source_path: str) -> dict:
    """Parse Jami al-Sahih (Musnad al-Rabi) from OpenITI mARkdown.

    Numbered reports (# 1) ..., or a header behind a page marker). A report keeps only its own paragraphs; footnote blocks after
    «__________», «قال الربيع» comment paragraphs (with their page-break continuation), inline glosses and «تنبيه» sections
    go to `footnotes` / `commentary`; chapter headings become `kitab` / `section` titles.
    """
    blocks = read_blocks(source_path, numbered_re=RE_RABI_HADITH, hidden_re=RE_RABI_HIDDEN_HEADER)
    legacy = legacy_spans(source_path, "rabi")
    reports, unassigned = [], []
    state = {"juz": "", "bab": "", "bab_no": 0, "kitab": "", "section": ""}
    current, last_number = None, 0

    def context():
        return {"juz": state["juz"], "bab": state["bab"], "bab_no": state["bab_no"], "kitab": state["kitab"], "section": state["section"]}

    def close():
        nonlocal current
        if current is not None:
            text = " ".join(part for part in current.body if part).strip()
            if len(text) >= 10:
                reports.append(empty_report(
                    text=text, label=current.label, anchor_line=current.first_line, blk_first=current.blk_first,
                    blk_last=current.blk_last, page_start=current.page_start, context=current.context,
                    footnotes=current.footnotes, footnote_marker_count=current.markers,
                    commentary=[item["text"] for item in current.tail], commentary_kinds=[item["kind"] for item in current.tail],
                    line_start=current.first_line, line_end=current.last_line, contiguous=False))
        current = None

    for idx, block in enumerate(blocks):
        first = block.first_raw
        if block.kind == "heading":
            continue
        if block.label and (not block.hidden or last_number < int(re.sub(r'\D', '', block.label) or 0) <= last_number + 2):
            close()
            current = _RabiRecord(block, idx, context())
            last_number = max(last_number, int(re.sub(r'\D', '', block.label) or 0))
            continue
        if block.hidden:  # an orphan line that only looks like a header
            if current is not None:
                current.body.append(block.text)
            continue
        m = RE_RABI_BAB_ANY.match(first)
        if m:
            close()
            state["bab_no"], state["bab"] = int(m.group(1)), normalise_block(m.group(2))
            continue
        first_text = block.first_text
        if 'الجزء' in first_text or 'القسم' in first_text:
            close()
            state["juz"] = normalise_block(first_text)
            continue
        text = block.text
        if not text:
            if current is not None and RE_FOOTNOTE_STAR.match(block.parts[0][0].strip()):
                current.touch(idx, block)               # «(1) *»: a note number whose note text the edition left out
                current.mode, current.markers = "footnote", current.markers + 1
            continue
        in_editorial = current is not None and current.mode == "editorial"
        if is_section_heading(text):
            close()
            if text.startswith("كتاب"):
                state["kitab"], state["section"] = text, ""
            else:
                state["section"] = text
            continue
        if current is None:
            unassigned.append({"line": block.first_line, "text": text})
            continue
        current.touch(idx, block)
        raw_first = block.parts[0][0].strip()
        if re.fullmatch(r'_{3,}', text):
            current.mode = "footnote"
            continue
        if RE_FOOTNOTE_STAR.match(raw_first) or (current.mode == "footnote" and re.fullmatch(r'\*+', text)):
            current.mode = "footnote"
            if text:
                current.footnotes.append(text)
            else:
                current.markers += 1
            continue
        if text in EDITORIAL_HEADINGS and current.mode != "editorial":
            current.mode = "editorial"
            current.add_tail("arranger_note", text)
            continue
        if in_editorial:
            current.add_tail("arranger_note", text, continuation=True)
            continue
        if text.startswith('قال الربيع'):
            current.mode = "tail"
            current.add_tail("rabi_comment", text)
            continue
        if current.mode == "body":
            current.body.append(text)
            current._gloss_check(block)
            continue
        # tail / footnote mode, plain paragraph: the unfinished comment continues over the page break, else it is a note
        continuation = bool(current.tail) and not is_terminal(current.tail[-1]["text"]) and current.mode == "tail"
        current.mode = "tail"
        current.add_tail("note", text, continuation=continuation)
    close()

    assign_ids("rabi", reports, legacy)
    base = {
        "source": "al-Jami al-Sahih (Musnad al-Rabi ibn Habib)",
        "source_ar": "الجامع الصحيح مسند الإمام الربيع بن حبيب",
        "tradition": "Ibadi",
        "compiler": "al-Rabi ibn Habib al-Azdi",
        "compiler_ar": "الربيع بن حبيب بن عمرو الأزدي",
        "arranger": "Abu Yaqub al-Warjlani",
        "arranger_ar": "أبو يعقوب يوسف بن إبراهيم الوارجلاني",
    }
    hadiths, verification = finish_records("rabi", reports, base, build_haystack(blocks))
    return {
        "source_file": os.path.basename(source_path),
        "openiti_uri": "0170RabicIbnHabibAzdi.JamicSahih.ShamIbadiyya0000155-ara1",
        "tradition": "Ibadi",
        "bab_count": state["bab_no"],
        "hadith_count": len(hadiths),
        "hadiths": hadiths,
        "unassigned_blocks": unassigned,
        "verification": verification,
    }


# ---------------------------------------------------------------------------
# Chunked works (Musnad Zayd, Sahifat al-Rida): legacy chunk triggers, clean text, splits, merges
# ---------------------------------------------------------------------------

RE_ZAYD_MID_MARKER = re.compile(r'(?<=\.)\s+و?=\s+(?=حدثني)')    # "... وآله. و= حدثني زيد بن علي ...": a second report in one paragraph
RE_RIDA_OPENER = re.compile(rf"{NOT_AR_BEFORE}وباسناده")
RE_ORDINAL_HEADING = re.compile(
    rf"{NOT_AR_BEFORE}الباب\s+(?:الأول|الاول|الثاني|الثالث|الرابع|الخامس|السادس|السابع|الثامن|التاسع|العاشر|الحادي\s+عشر|\d+)"
    r"(?:\s*[:\-])?\s+(?:في|ذكر)\s+[^.:]{3,80}?(?=\s+(?:وباسناده|حدثني|عن)\b|$)")


@dataclass
class _Chunk:
    number: int = 0
    break_id: int = 0                                   # chunks with the same break_id have no heading or dropped chunk between them
    blocks: list = field(default_factory=list)          # [(idx, Block, parts_override or None)]
    anchor_line: int = 0
    page_start: str = ""

    def lines(self):
        used = [line for _idx, block, parts in self.blocks for _text, line in (parts if parts is not None else block.parts)]
        return min(used), max(used)

    def text_with_markers(self):
        pieces = []
        for _idx, block, parts in self.blocks:
            raw = " ".join(text for text, _line in (parts if parts is not None else block.parts))
            piece = normalise_block(raw)
            if piece:
                pieces.append(piece)
        return " ".join(pieces)


def _page_break_decision(block, first_text, trigger, previous_text):
    """A trigger verb at the top of a page-break paragraph may only be the tail of a sentence the page break cut.

    'new' (legacy: the verb opens a report), 'continue' (the whole paragraph continues the unfinished previous report) or
    ('split', p) (a sentence end sits before the verb: the head up to p continues the previous report, the rest is a new one).
    """
    if not block.page_break_before or not re.search(r'[' + AR + r'،)]$', previous_text) or not isinstance(trigger, re.Match):
        return 'new'
    p = first_text.rfind(' ', 0, trigger.start()) + 1
    if p <= 3:
        return 'new'
    if re.search(r'\.\s*$', first_text[:p]):
        return ('split', p)
    return 'continue'


def _segment_zayd(text):
    parts = RE_ZAYD_MID_MARKER.split(text)
    return [("report", part) for part in parts if part.strip()]


def _segment_rida(text):
    bounds = [(m.start(), "report", m.end()) for m in RE_RIDA_OPENER.finditer(text)]
    bounds += [(m.start(), "heading", m.end()) for m in RE_ORDINAL_HEADING.finditer(text)]
    bounds.sort()
    if not bounds or bounds[0][0] > 0:
        bounds.insert(0, (0, "report", 0))
    segments = []
    for i, (start, kind, _end) in enumerate(bounds):
        stop = bounds[i + 1][0] if i + 1 < len(bounds) else len(text)
        piece = text[start:stop]
        if kind == "heading":
            heading_end = bounds[i][2] - start
            heading, rest = piece[:heading_end], piece[heading_end:]
            segments.append(("heading", heading))
            if rest.strip():
                segments.append(("report", rest))
        elif piece.strip():
            segments.append(("report", piece))
    return segments


def _parse_chunked(source_path, work):
    is_rida = work == "rida"
    blocks = read_blocks(
        source_path,
        start_marker=ZAYD_APPENDIX_MARKER if is_rida else None,
        stop_marker=None if is_rida else ZAYD_APPENDIX_MARKER)
    legacy = legacy_spans(source_path, work)
    min_len = 15 if is_rida else 10
    reports, dropped, headings_seen = [], [], []
    state = {"kitab": "", "bab": "", "kitab_no": 0, "bab_no": 0, "breaks": 0, "previous_kept": None}
    chunk = None

    def context():
        if is_rida:
            return {"bab": state["bab"], "bab_no": state["bab_no"]}
        return {"kitab": state["kitab"], "bab": state["bab"], "kitab_no": state["kitab_no"], "bab_no": state["bab_no"]}

    def finalize(done):
        """Clean the chunk, segment it (rida headings / «وباسناده», zayd «و= حدثني») and emit its reports."""
        marked = done.text_with_markers()
        clean = strip_edition_markers(marked)
        if len(clean) < min_len:
            dropped.append({"reason": "shorter_than_%d_chars" % min_len, "line": done.anchor_line, "text": clean})
            state["breaks"] += 1
            return
        if (clean.startswith('بسم الله') or clean.startswith('الحمدلله') or clean.startswith('الحمد لله')
                or (is_rida and ('أما بعد، فهذه صحيفة' in clean or 'هذه الصحيفة ويسمى' in clean))):
            dropped.append({"reason": "preamble_or_introduction", "line": done.anchor_line, "text": clean[:80]})
            state["breaks"] += 1
            return
        first_idx, last_idx = done.blocks[0][0], done.blocks[-1][0]
        adjacent = state["previous_kept"] is not None and state["previous_kept"] == done.break_id
        segments = _segment_rida(marked) if is_rida else _segment_zayd(marked)
        bab_now, bab_no_now = state["bab"], state["bab_no"]
        for kind, text in segments:
            if kind == "heading":                       # an inline heading is a chapter title, not a report
                bab_no_now += 1
                bab_now = strip_edition_markers(text)
                adjacent = False
                continue
            cleaned = strip_edition_markers(text)
            if not cleaned:
                continue
            ctx = context()
            ctx["bab"], ctx["bab_no"] = bab_now, bab_no_now
            reports.append(empty_report(
                text=cleaned, anchor_line=done.anchor_line, chunk=done.number, blk_first=first_idx, blk_last=last_idx,
                page_start=done.page_start, context=ctx, line_start=done.lines()[0], line_end=done.lines()[1],
                contiguous=adjacent, chunk_lines=done.lines()))
            adjacent = True
        state["bab"], state["bab_no"] = bab_now, bab_no_now
        state["previous_kept"] = done.break_id

    def close_chunk():
        nonlocal chunk
        if chunk is not None:
            finalize(chunk)
        chunk = None

    chunk_counter = 0
    for idx, block in enumerate(blocks):
        if block.kind == "heading":
            close_chunk()
            state["breaks"] += 1
            title = clean_text(" ".join(t for t, _ in block.parts))
            headings_seen.append({"line": block.first_line, "level": block.level, "text": title})
            if block.level == "kitab" and not is_rida:
                state["kitab_no"] += 1
                state["kitab"], state["bab"], state["bab_no"] = title, "", 0
            else:
                state["bab_no"] += 1
                state["bab"] = title
            continue
        first_text = block.first_text
        parts_override, anchor = None, None
        if is_rida and first_text.lstrip().startswith('الباب '):
            close_chunk()
            state["breaks"] += 1
            state["bab_no"] += 1
            state["bab"] = clean_text(block.parts[0][0])
            headings_seen.append({"line": block.first_line, "level": "bab_paragraph", "text": state["bab"]})
            if len(block.parts) < 2:
                continue
            parts_override, anchor = block.parts[1:], block.parts[1][1]
        trigger = RE_ZAYD_HADITH_START.search(first_text[:30]) or (is_rida and first_text.lstrip().startswith('وباسناده'))
        if chunk is not None and trigger and chunk.text_with_markers().strip():
            decision = 'new' if parts_override is not None else _page_break_decision(
                block, first_text, trigger, strip_edition_markers(chunk.text_with_markers()))
            if decision == 'new':
                close_chunk()
            elif decision != 'continue':                     # ('split', p): the head of this paragraph ends the previous report
                cut = decision[1]
                chunk.blocks.append((idx, block, [(first_text[:cut], block.first_line)]))
                close_chunk()
                parts_override, anchor = [(first_text[cut:], block.first_line)] + block.parts[1:], block.first_line
        if not block.text and parts_override is None:
            continue
        if chunk is None:
            chunk_counter += 1
            chunk = _Chunk(number=chunk_counter, break_id=state["breaks"],
                           anchor_line=anchor if anchor is not None else block.first_line, page_start=block.page)
        chunk.blocks.append((idx, block, parts_override))
    close_chunk()
    assign_ids(work, reports, legacy)
    reports = merge_chain_fragments(reports)

    if is_rida:
        base = {"source": "Sahifat al-Imam Ali al-Rida", "source_ar": "صحيفة الإمام علي الرضا", "tradition": "Imami",
                "compiler": "Abd al-Wasit ibn Yahya al-Wasiti (arranger)", "compiler_ar": "عبد الواسع بن يحيى الواسعي (مرتب)"}
        uri = "0122ZaydIbnCali.Musnad.Zaydiyya0000052-ara1 (appendix)"
    else:
        base = {"source": "Musnad al-Imam Zayd ibn Ali", "source_ar": "مسند الإمام زيد بن علي", "tradition": "Zaydi",
                "compiler": "Abd al-Aziz ibn Ishaq al-Baghdadi", "compiler_ar": "عبد العزيز بن إسحاق البغدادي"}
        uri = "0122ZaydIbnCali.Musnad.Zaydiyya0000052-ara1"
    hadiths, verification = finish_records(work, reports, base, build_haystack(blocks))
    result = {
        "source_file": os.path.basename(source_path),
        "openiti_uri": uri,
        "tradition": base["tradition"],
        "bab_count": state["bab_no"],
        "hadith_count": len(hadiths),
        "hadiths": hadiths,
        "dropped_chunks": dropped,
        "headings": headings_seen,
        "verification": verification,
    }
    if not is_rida:
        result["kitab_count"] = state["kitab_no"]
    return result


def parse_zayd(source_path: str) -> dict:
    """Parse Musnad Zayd from OpenITI mARkdown into structured records.

    Paragraph triggers keep the original record boundaries (so ids stay stable); '=' / 'V' edition markers are stripped, headings own
    their '~~' lines, orphan lines continue their paragraph, chain-only fragments merge into the report they open, and a second report
    inside one paragraph («و= حدثني زيد ...») becomes '<id>#2'.
    """
    return _parse_chunked(source_path, "zayd")


def parse_rida_appendix(source_path: str) -> dict:
    """Parse the Sahifa of Imam Ali al-Rida from the appendix of the Zayd file.

    Each «وباسناده» starts its own report ('<id>#2', ...); «الباب <ordinal> ...» headings become chapter titles, not reports.
    """
    return _parse_chunked(source_path, "rida")


# ---------------------------------------------------------------------------
# Output: JSON, CSV, provenance
# ---------------------------------------------------------------------------

def write_json(data: dict, path: str):
    """Write parsed data to JSON with UTF-8 encoding."""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  JSON: {path} ({data['hadith_count']} hadiths)")


def write_csv_clean(hadiths: list, path: str):
    """Write minimal CSV for quick inspection."""
    fields = ["id", "hadith_no", "source", "tradition", "bab", "text_ar"]
    with open(path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_ALL,
                                extrasaction='ignore')
        writer.writeheader()
        writer.writerows(hadiths)
    print(f"  CSV (clean): {path} ({len(hadiths)} rows)")


def write_csv_full(hadiths: list, path: str):
    """Write full-schema CSV matching unified dataset format."""
    fields = [
        "id", "hadith_id", "source", "tradition", "volume", "chapter_no",
        "hadith_no", "chapter", "category", "chain_indx", "text_ar", "text_en",
        "sanad", "matn_en", "grade_tradition", "grade_source", "grade_value",
        "gradings_full", "url", "page_ref",
    ]
    with open(path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_ALL,
                                extrasaction='ignore')
        writer.writeheader()
        for h in hadiths:
            writer.writerow({
                "id": h["id"],
                "hadith_id": h["hadith_no"],
                "source": h["source"],
                "tradition": h["tradition"],
                "volume": 1,
                "chapter_no": h.get("bab_no", h.get("kitab_no", "")),
                "hadith_no": h["hadith_no"],
                "chapter": h.get("bab", h.get("kitab", "")),
                "category": h.get("kitab", h.get("bab", "")),
                "chain_indx": "",
                "text_ar": h["text_ar"],
                "text_en": "",
                "sanad": "",
                "matn_en": "",
                "grade_tradition": h["tradition"],
                "grade_source": "",
                "grade_value": "",
                "gradings_full": "",
                "url": "",
                "page_ref": h.get("page_ref", ""),
            })
    print(f"  CSV (full): {path} ({len(hadiths)} rows)")


def write_provenance(data: dict, output_dir: str):
    """Write provenance metadata for this parse run."""
    prov = {
        "parsed_at": datetime.now(timezone.utc).isoformat(),
        "parser": "parse_openiti.py",
        "source_uri": data["openiti_uri"],
        "source_file": data["source_file"],
        "source_type": "OpenITI mARkdown (community-typed, Shamela)",
        "tradition": data["tradition"],
        "hadith_count": data["hadith_count"],
        "transformations": [
            "NFKC Unicode normalization",
            "Zero-width/bidi control character removal",
            "Footnote marker removal (inline parenthetical numbers)",
            "Page marker and milestone extraction (stored in page_ref, removed from text)",
            "Whitespace normalization",
            "Edition markers removed (zayd '=', stray leading 'V', lone '*')",
            "Footnote blocks, Rabi comment paragraphs, glosses and the editorial section moved to footnotes/commentary fields",
            "Chapter headings kept as titles, not reports; merged reports split (id#2...); chain-only fragments merged",
            "sanad_ar / matn_ar cut from text_ar (verbatim substrings; null when the split is not confident)",
        ],
        "what_was_NOT_changed": [
            "Tashkeel (diacritics) preserved as-is",
            "Original Arabic word order preserved",
            "No spelling correction applied",
            "Every emitted string is a verbatim substring of the normalised source (asserted at parse time, see 'verification')",
        ],
        "notes": [
            "Text is community-proofread from Shamela, NOT from OCR",
            "Grade fields are empty — these traditions use different grading systems",
            "Translation (text_en) is empty — to be filled by translation pipeline",
        ],
    }
    if "kitab_count" in data:
        prov["kitab_count"] = data["kitab_count"]
    if "bab_count" in data:
        prov["bab_count"] = data["bab_count"]

    path = os.path.join(output_dir, "PROVENANCE.json")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(prov, f, ensure_ascii=False, indent=2)
    print(f"  Provenance: {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_zayd(output_dir: str = None):
    """Parse Musnad Zayd and write outputs."""
    source = os.path.join(OPENITI_DIR, "zayd", "musnad_zaydiyya_052.mARkdown")
    if not os.path.exists(source):
        print(f"ERROR: {source} not found. Run download first.")
        return None

    if output_dir is None:
        output_dir = os.path.join(SCRIPT_DIR, "hadith-data", "zaydi-hadith")

    print(f"\nParsing Musnad Zayd from OpenITI...")
    print(f"  Source: {source}")
    data = parse_zayd(source)
    print(f"  Found: {data['kitab_count']} kitab, {data['bab_count']} bab, "
          f"{data['hadith_count']} hadiths")

    write_json(data, os.path.join(output_dir, "parsed_hadiths.json"))
    write_csv_clean(data["hadiths"], os.path.join(output_dir, "zaydi_hadiths_clean.csv"))
    write_csv_full(data["hadiths"], os.path.join(output_dir, "zaydi_hadiths_full.csv"))
    write_provenance(data, output_dir)
    return data


def run_rida(output_dir: str = None):
    """Parse Sahifat al-Imam Ali al-Rida (appendix of the Zayd file)."""
    source = os.path.join(OPENITI_DIR, "zayd", "musnad_zaydiyya_052.mARkdown")
    if not os.path.exists(source):
        print(f"ERROR: {source} not found.")
        return None

    if output_dir is None:
        output_dir = os.path.join(SCRIPT_DIR, "hadith-data", "rida-hadith")
    os.makedirs(output_dir, exist_ok=True)

    print(f"\nParsing Sahifat al-Imam Ali al-Rida (appendix)...")
    print(f"  Source: {source}")
    data = parse_rida_appendix(source)
    print(f"  Found: {data['bab_count']} bab, {data['hadith_count']} hadiths")

    write_json(data, os.path.join(output_dir, "parsed_hadiths.json"))
    write_csv_clean(data["hadiths"], os.path.join(output_dir, "rida_hadiths_clean.csv"))
    write_csv_full(data["hadiths"], os.path.join(output_dir, "rida_hadiths_full.csv"))
    write_provenance(data, output_dir)
    return data


def run_rabi(output_dir: str = None):
    """Parse Musnad al-Rabi and write outputs."""
    source = os.path.join(OPENITI_DIR, "rabi", "jamic_sahih_ibadiyya.txt")
    if not os.path.exists(source):
        print(f"ERROR: {source} not found. Run download first.")
        return None

    if output_dir is None:
        output_dir = os.path.join(SCRIPT_DIR, "hadith-data", "ibadi-hadith")
    os.makedirs(output_dir, exist_ok=True)

    print(f"\nParsing Jami al-Sahih (Musnad al-Rabi) from OpenITI...")
    print(f"  Source: {source}")
    data = parse_rabi(source)
    print(f"  Found: {data['bab_count']} bab, {data['hadith_count']} hadiths")

    write_json(data, os.path.join(output_dir, "parsed_hadiths.json"))
    write_csv_clean(data["hadiths"], os.path.join(output_dir, "ibadi_hadiths_clean.csv"))
    write_csv_full(data["hadiths"], os.path.join(output_dir, "ibadi_hadiths_full.csv"))
    write_provenance(data, output_dir)
    return data


def main():
    parser = argparse.ArgumentParser(
        description='Parse OpenITI mARkdown files into structured hadith datasets')
    parser.add_argument('--zayd-only', action='store_true',
                        help='Parse only Musnad Zayd')
    parser.add_argument('--rabi-only', action='store_true',
                        help='Parse only Musnad al-Rabi')
    parser.add_argument('--rida-only', action='store_true',
                        help='Parse only Sahifat al-Imam Ali al-Rida')
    parser.add_argument('--output-dir', type=str, default=None,
                        help='Override output directory')
    args = parser.parse_args()

    if args.zayd_only:
        run_zayd(args.output_dir)
    elif args.rabi_only:
        run_rabi(args.output_dir)
    elif args.rida_only:
        run_rida(args.output_dir)
    else:
        run_zayd()
        run_rabi()
        run_rida()

    print("\nDone.")


if __name__ == '__main__':
    main()
