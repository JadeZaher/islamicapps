"""Chain cutting for every tradition (OpenITI works, Thaqalayn, Sunni); see pg_export/AGENTS.md §Chain builder.

Pure and standard library apart from the canonical extractor, which is reused unchanged (re-run only on a copy of a text).
OpenITI: the chain is the parser's `sanad_ar`, or a low-confidence report's fixed-shape opening; a continuation carries its
parent's mentions, marked inherited, up to the speaker it names; the work's compiler is its attribution, never a mention.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

from extract_isnad_unified import _strip_arabic_marks, extract_isnad_branches

RULES_PATH = Path(__file__).resolve().parent / "opening_isnad_rules.json"
OPENITI_WORKS = frozenset({"ibadi:musnad-rabi", "zaydi:musnad-zayd", "imami:sahifat-al-imam-ali-al-rida"})
AR = "ء-ي"
END = rf"(?![{AR}])"
START = rf"(?<![{AR}])"

# Continuation openers (the parser's RE_CONTINUATION_CHAIN plus the named «ومن طريق X»), never a mention.
OPENER = re.compile(
    rf"^\s*(?:و?(?:بهذا|بنفس|بذلك)\s+(?:السند|الإسناد|الاسناد)(?:\s+المذكور)?|ومن\s+طريق(?:ه|ها){END}(?:\s+أيضا)?"
    rf"|و?بإسناده|و?باسناده|و?باسنادة|وبسنده|وباسنادهم)(?:\s+المذكور)?(?:\s+في\s+رواية\s+أخرى)?\s*")
NAMED_ROUTE = re.compile(rf"^\s*ومن\s+طريق\s+(?=[{AR}])")
# Honorifics and blessings removed before splitting (so «كرم الله وجهه» never splits on its waw).
HONORIFIC = re.compile(
    rf"{START}(?:كرم\s+الله\s+وجهه(?:\s+و?رضي\s+عنه)?|رض[يى]\s+الله\s+(?:تعالى\s+)?عن(?:ه|ها|هما|هم|هن){END}"
    rf"|رحم(?:ه|ها|هما|هم){END}\s+الله(?:\s+تعالى)?|عليه(?:ا|ما|م)?\s+(?:الصلاة\s+و)?السلام"
    rf"|صلوات\s+الله\s+(?:وسلامه\s+)?عليه(?:ما|م)?|سلام\s+الله\s+عليه(?:ما|م)?(?:\s+أجمعين(?:\s+آمين\s+إلى\s+يوم\s+الدين)?)?"
    rf"|صل[ىي]\s+الله\s+عليه(?:\s+و?(?:على\s+)?آله)?(?:\s+وسلم)?|\(\s*ع\s*م?\s*\)|{START}ع\s*م{END})")
# A date or year phrase inside a chain («سنة مائة واربع وتسعين»): not a name.
YEAR_PHRASE = re.compile(rf"{START}سنة\s+[^،,:.]*")
# Leading connector or frame word kept in a surface by the extractor.
LEADING_NOISE = re.compile(rf"^(?:وعن|وكان|كان|قال|وقال|فقال|حدثن[يى]|حدثنا|أن|ان){END}\s*")
# A name followed by a frame word: the name ends there («علي انه كان يستحب ...», «عائشة أنها»).
TRAILING_FRAME = re.compile(
    rf"\s+(?:أنه|انه|أنها|انها|أنهما|انهما|أن|ان|بلغني|بلغنا|سئل|وسئل|سألت|وسألت|سأل|في\s+قوله|قوله|عنه|أيضا|ايضا"
    rf"|فقال|يقول|يذكر|يروون|حكاية|حين|كان|صاحب|زوج|فقيه|يكنى){END}.*$")
# A frame verb inside what the extractor kept: what is left is a name only when it has a nasab or is one bare name.
MATN_VERB = re.compile(rf"{START}(?:فقال|وسئل|سئل|فطرح|رقى){END}")
# «من طريق X» inside a chain is a link; «X أمير المؤمنين علي» (no «عن», zayd_0001) is two links.
INNER_ROUTE = re.compile(rf"\s+من\s+طريق\s+")
COMMANDER_OF_FAITHFUL = re.compile(rf"(?<=[{AR}])\s+(?=(?:أمير|امير)\s+المؤمنين\s+علي{END})")
FRAME_ONLY = re.compile(rf"^(?:قال|قالت|قالا|قلت|وقال|فقال|حدثني|حدثنا|أخبرني|عنه|عن|المذكور|يقول|أيضا|ايضا){END}")
FUNCTION_WORD = re.compile(rf"^(?:لو|ان|أن|ما|لا|من|في|إلى|الى|هو|هذا|هذه|كان|ثم|قد|إذا|اذا|فإن|فان|إني|اني|أنا|انا){END}$")
NASAB = re.compile(rf"{START}(?:بن|ابن|بنت|أبو|ابو|أبي|ابي|أبا|ابا|أم|ام|عبد){END}")
PROPHET = re.compile(rf"^(?:النبيء?|النبي|رسول\s+الله|محمد\s+رسول\s+الله){END}")
# Balagh: «بلغني عن X» names a source the narrator did not hear (a gap, marked, never repaired).
BALAGH = re.compile(rf"{START}(?:قال\s*:?\s*)?(?P<verb>بلغني|بلغنا){END}\s+(?:أن\s+)?عن\s+")

# Work rules (pg_export/AGENTS.md §Chain builder).
# al-Rabi (and a later transmitter of his book before him) up to the link that follows him.
RABI_COMPILER = re.compile(
    rf"^[^:«»]{{0,40}}?{START}(?:أبو\s+عمرو\s+)?الربيع(?:\s+بن\s+حبيب)?{END}[^:«»]{{0,30}}?(?::|\s+عن{END})\s*"
    rf"(?:حدثني|حدثنا|أخبرني)?\s*")
ZAYD_COMPILER = re.compile(rf"(?:^|[\s(])(?:أبو\s+خالد(?:\s+عمرو\s+بن\s+خالد)?|عمرو\s+بن\s+خالد)(?:\s+الواسطي)?{END}")
ZAYD_AFTER_COMPILER = re.compile(
    rf"^[\s)]*(?:رحم(?:ه|هم){END}\s+الله(?:\s+تعالى)?)?[\s:،]*(?:قال{END})?[\s:،]*")
RIDA_IMAM_CHAIN = re.compile(rf"(?:حدثني|حدثنا)\s+(?=علي\s+بن\s+موسى)")
RIDA_IMAM_CHAIN_END = re.compile(rf"{START}قال\s*:\s*قال\s+رسول\s+الله")
# The parser's span stops before «عن علي ...» at the head of the matn (Musnad Zayd, «عن جده (ع م) عن علي»).
MATN_HEAD_LINK = re.compile(
    rf"^\s*(?P<link>عن\s+(?:علي|على|أبيه|ابيه|جده){END}[^:«»]{{0,60}}?)\s*(?=(?:أنه|انه|قال|يقول|في){END}|[:«،,]|$)")
# A descriptor after a name («صاحب رسول الله»), never part of it.
DESCRIPTOR = re.compile(rf"{START}(?:صاحب|زوج)\s+(?:رسول\s+الله|النبيء?|النبي){END}")
# A title before a name («أمير المؤمنين علي»).
TITLE = re.compile(rf"^(?:أمير|امير)\s+المؤمنين\s+(?=\S)")
# A Companion named after «قال:» at the head of the matn («... قال: قال جابر بن عبد الله: ...»).
MATN_HEAD_SOURCE = re.compile(
    rf"^\s*قال\s+(?P<name>(?:أبو|أبي|ابن|عبد|أم|جابر|أنس|عمر|علي|عثمان|سعد|معاذ|عائشة|عمران)[{AR}\s]{{0,40}}?)"
    rf"\s*(?:{HONORIFIC.pattern})?\s*:")


# A low-confidence split's opening read through the work's fixed isnad shape (round 3): the span stops at the first word
# the shape cannot explain. al-Rabi: «[قال الربيع:] أبو عبيدة [عن|قال: قال] جابر بن زيد [عن|قال: قال|قال: سمعت] <Companion>»
# or «… قال: بلغني عن X» (the balagh gap); Musnad Zayd: «[حدثني] زيد بن علي عن أبيه عن جده عن علي».
COMPANION_RUN = (rf"(?!رسول|النبي|جملة|قوم|رجل|بعض|ناس|أناس|بلغ|سمع|سئل|جاء|كان|أتى|أتي|قال|رأ|أن{END}|أنه{END}|أنها{END})(?:(?:أبو|أبي|أبا|ابن|أم|عبد|بنت)\s+)?[{AR}]+"
                 rf"(?:\s+(?:بن|ابن|بنت)\s+(?:(?:أبي|عبد)\s+)?[{AR}]+){{0,3}}(?:\s+(?:الخطاب|الأنصاري|الخدري|الأشعري|الغفاري"
                 rf"|أم\s+المؤمنين)){{0,2}}")
RABI_LINK = r"\s*[:،,]?\s*(?:عن|قال\s*:\s*(?:قال|حدثني|سمعت)?|قال\s+(?:قال|حدثني|سمعت))\s*:?\s*"
# «بلغني عن X» (X may be the Prophet: the balagh gap ends the chain) or a named Companion.
RABI_BALAGH = rf"و?(?:بلغني|بلغنا)\s+عن\s+(?:{COMPANION_RUN}|رسول\s+الله|النبيء?)(?={END})"
RABI_SOURCE = rf"(?:{RABI_BALAGH}|{COMPANION_RUN}(?={END}))"
RABI_SHAPE = re.compile(
    rf"^\s*(?:قال\s+)?(?P<span>أبو\s+عبيدة(?:\s+مسلم\s+بن\s+أبي\s+كريمة(?:\s+التميمي)?)?"
    rf"(?:{RABI_LINK}جابر(?:\s+بن\s+زيد(?:\s+الأزدي)?)?(?:{RABI_LINK}{RABI_SOURCE})?|{RABI_LINK}{RABI_SOURCE})?)")
IMAM_MARK = r"(?:\s+(?:عليهم?(?:ا|ما)?\s+السلام|\(\s*ع\s*م?\s*\)))?"
ZAYD_SHAPE = re.compile(
    rf"^\s*(?:حدثني\s+)?(?P<span>زيد\s+بن\s+علي{IMAM_MARK}(?:\s+عن\s+(?:أبيه|ابيه){IMAM_MARK}(?:\s+عن\s+جده{IMAM_MARK}(?:\s+عن\s+"
    rf"(?:علي|على)(?:\s+بن\s+أبي\s+طالب)?(?={END}))?)?|\s+عن\s+آبائه{IMAM_MARK}\s+عن\s+(?:علي|على)(?:\s+بن\s+أبي\s+طالب)?(?={END})"
    rf"|(?=\s+قال{END}))?)")
# Inside an al-Rabi span «قال: قال X» and «قال: حدثني X» are links («بلغني» stays: it is the balagh gap).
RABI_SPAN_LINK = re.compile(rf"\s*[:،,]?\s*قال\s*:?\s*(?:(?:قال|حدثني|سمعت)\s*:?\s*|(?!و?بلغني))")


def _spelling_tolerant(pattern: re.Pattern) -> re.Pattern:
    """The pattern with hamza-less alef and ha for ta marbuta accepted («ابو عبيده»)."""
    return re.compile(pattern.pattern.replace("أ", "[أاإ]").replace("ة", "[ةه]"))


RABI_SHAPE, ZAYD_SHAPE = _spelling_tolerant(RABI_SHAPE), _spelling_tolerant(ZAYD_SHAPE)


def fixed_shape_span(work: str, text: str) -> str | None:
    """The opening of a low-confidence report read through its work's fixed isnad shape, or None (pg_export/AGENTS.md)."""
    plain, _ = strip_compiler(work, _strip_arabic_marks(text))
    shape = RABI_SHAPE if work == "rabi" else ZAYD_SHAPE if work == "zayd" else None
    hit = shape.match(plain) if shape else None
    if not hit:
        return None
    span = hit.group("span").strip()
    return RABI_SPAN_LINK.sub(" عن ", span) if work == "rabi" else span


@dataclass(frozen=True)
class OpenitiReport:
    record_id: str
    work: str                       # rabi | zayd | rida
    text_ar: str
    sanad_ar: str | None
    matn_ar: str | None
    split_confidence: str
    inherits_from: str | None       # record id of the report whose chain this one continues


@dataclass(frozen=True)
class BuiltMention:
    surface: str
    link_kind: str | None = None                 # anonymous | derived_relation; None: decided by the identity
    inherited_from: tuple[str, int, int] | None = None   # (record id, branch, position) of the written mention
    rule_identity: tuple[str, str] | None = None         # (narrator id, detail) given by a work rule


@dataclass
class BuildResult:
    branches: dict[str, list[list[BuiltMention]]] = field(default_factory=dict)   # parents before continuations
    counts: Counter = field(default_factory=Counter)


def fold(value: str) -> str:
    """Comparison form: hamza and alef variants, ya and ta marbuta folded, marks dropped."""
    value = re.sub(r"[ً-ٰٟـ]", "", value or "")
    value = re.sub("[أإآٱ]", "ا", value).replace("ى", "ي").replace("ة", "ه")
    return re.sub(r"\s+", " ", value).strip()


def work_of(record_id: str) -> str:
    return record_id.split(":")[2].split("_")[0]


def clean_chain_text(text: str) -> str:
    """Honorifics and year phrases out, inner links made explicit; the text is otherwise the source's."""
    text = HONORIFIC.sub(" ", text)
    text = YEAR_PHRASE.sub(" ", text)
    text = DESCRIPTOR.sub(" ", text)
    text = INNER_ROUTE.sub(" عن ", text)
    text = re.sub(r"\s+", " ", text)
    text = COMMANDER_OF_FAITHFUL.sub(
        lambda m: m.group(0) if re.search(rf"(?:قال|عن|حدثني|حدثنا|و){END}\s*$", text[:m.start()]) else " عن ", text)
    return re.sub(r"\s+", " ", text).strip()


def clean_surface(surface: str) -> str | None:
    """A name, or None when what the extractor kept is a frame word, a function word or the Prophet."""
    surface = re.sub(r"\s+", " ", HONORIFIC.sub(" ", surface)).strip(" :،,.()")
    surface = TITLE.sub("", surface)
    while True:
        stripped = LEADING_NOISE.sub("", surface)
        if stripped == surface:
            break
        surface = stripped.strip()
    had_matn_verb = bool(MATN_VERB.search(surface))
    surface = TRAILING_FRAME.sub("", surface).strip(" :،,.")
    if had_matn_verb and not NASAB.search(surface) and (len(surface.split()) > 1 or surface.startswith("ال")):
        return None
    if not surface or FRAME_ONLY.match(surface) or FUNCTION_WORD.match(surface) or PROPHET.match(surface):
        return None
    words = surface.split()
    if len(words) >= 5 and not NASAB.search(surface):
        return None          # a clause, not a name
    return surface


def extract_names(text: str) -> list[list[BuiltMention]]:
    """Branches of names from a chain span, with balagh gaps marked as anonymous mentions."""
    text = clean_chain_text(text)
    pieces = []
    cursor = 0
    for match in BALAGH.finditer(text):
        pieces.append((text[cursor:match.start()], None))
        pieces.append(("", match.group("verb")))
        cursor = match.end()
    pieces.append((text[cursor:], None))
    branches: list[list[BuiltMention]] = [[]]
    for piece, gap in pieces:
        if gap:
            branches = [branch + [BuiltMention(gap, link_kind="anonymous")] for branch in branches]
            continue
        if not piece.strip():
            continue
        # A piece after a balagh starts with the named source, so it is read as a link.
        found = extract_isnad_branches(("عن " + piece) if branches[0] and branches[0][-1].link_kind == "anonymous"
                                       else piece)
        cleaned = []
        for branch in found or [[]]:
            names = [name for surface in branch if (name := clean_surface(surface))]
            cleaned.append([BuiltMention(name) for name in names])
        branches = [left + right for left in branches for right in cleaned]
    return [branch for branch in branches if any(m.link_kind is None for m in branch)]


def strip_compiler(work: str, text: str) -> tuple[str, bool]:
    """The work's compiler (al-Rabi, Abu Khalid) and the book transmitters before him are its attribution."""
    if work == "rabi":
        match = RABI_COMPILER.match(text)
        if match:
            return text[match.end():], True
    elif work == "zayd":
        match = ZAYD_COMPILER.search(text)
        zayd_at = text.find("زيد")
        if match and (zayd_at < 0 or match.start() < zayd_at):
            rest = text[match.end():]
            rest = rest[ZAYD_AFTER_COMPILER.match(rest).end():]
            return re.sub(rf"^\s*عن{END}\s*", "", rest), True
    return text, False


def matn_head_source(matn: str | None) -> str | None:
    """«قال: قال X:» at the head of the matn names one more link (al-Rabi)."""
    if not matn:
        return None
    match = MATN_HEAD_SOURCE.match(matn)
    if not match:
        return None
    return clean_surface(match.group("name"))


def rida_imam_chain(text: str) -> str | None:
    """The Imam chain of the Sahifa (rida_0001): from «علي بن موسى الرضا» to «علي بن أبي طالب»."""
    start = RIDA_IMAM_CHAIN.search(text)
    if not start:
        return None
    end = RIDA_IMAM_CHAIN_END.search(text, start.end())
    return text[start.end():end.start() if end else None]


def own_branches(report: OpenitiReport, counts: Counter) -> list[list[BuiltMention]]:
    """The chain written in the report itself (never for a low-confidence split)."""
    if report.work == "rida" and report.inherits_from is None:
        span = rida_imam_chain(report.text_ar)
        if span is None:
            counts["rida_imam_chain_not_found"] += 1
            return []
        counts["rida_imam_chain_stored"] += 1
        return extract_names(span)
    if report.split_confidence != "high" or not report.sanad_ar:
        # Low confidence about where the matn starts is not low confidence about the opening: a fixed-shape opening is read.
        span = fixed_shape_span(report.work, report.text_ar) if report.inherits_from is None else None
        if span:
            counts["low_confidence:chain_from_fixed_shape" if report.split_confidence != "high" else
                   "no_sanad_span:chain_from_fixed_shape"] += 1
            return extract_names(span)
        counts["no_chain:low_confidence_split" if report.split_confidence != "high" else "no_chain:no_chain_in_text"] += 1
        return []
    text, stripped = strip_compiler(report.work, report.sanad_ar)
    counts[f"compiler_not_a_mention:{report.work}"] += stripped
    head_link = MATN_HEAD_LINK.match(report.matn_ar or "") if report.work == "zayd" else None
    if head_link:
        counts["matn_head_link_added"] += 1
        text = f"{text} {head_link.group('link')}"
    branches = extract_names(text)
    extra = matn_head_source(report.matn_ar) if report.work == "rabi" else None
    if extra and branches:
        counts["matn_head_source_added"] += 1
        branches = [branch + [BuiltMention(extra)] for branch in branches]
    return branches


def _name_key(surface: str) -> str:
    """Name for matching a continuation's named link with its parent's mentions («أبي محمد بن علي» = my father M. b. A.)."""
    key = fold(surface).replace("ابن ", "بن ")
    words = key.split()
    if len(words) >= 3 and words[0] in ("ابي", "ابو") and "بن" in words:
        key = " ".join(words[1:])
    return key


def names_match(own: str, parent: str) -> bool:
    a, b = _name_key(own), _name_key(parent)
    if a == b:
        return True
    a_words, b_words = a.split(), b.split()
    if len(a_words) == 1:
        return b_words[0] == a_words[0] if b_words else False
    shorter, longer = (a_words, b_words) if len(a_words) <= len(b_words) else (b_words, a_words)
    return longer[:len(shorter)] == shorter


RELATION_ONLY = frozenset(["ابي", "ابيه", "جده", "جدي", "ابائه"])


def continuation_names_match(own: str, parent: str) -> bool:
    """`names_match` for a continuation's named link: the written form is tried too («أبي جعفر» = «أبي جعفر بن محمد»), and a
    bare relation in the parent chain («أبي») never stands for a longer name (rida_0031#13)."""
    own_raw, parent_raw = fold(own).replace("ابن ", "بن "), fold(parent).replace("ابن ", "بن ")
    if parent_raw in RELATION_ONLY and own_raw != parent_raw:
        return False
    if names_match(own, parent):
        return True
    a, b = own_raw.split(), parent_raw.split()
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    return len(shorter) >= 2 and longer[:len(shorter)] == shorter


# The speaker a continuation names before his words: «قال: قال علي بن الحسين», «سئل محمد بن علي», «حدثني أبي جعفر».
SPEAKER_LEAD = re.compile(rf"^\s*(?:(?:قال|قالت|وقال|سئل|وسئل|حدثني|حدثنا)\s*[:.]?\s*)+")


def continuation_own_names(report: OpenitiReport) -> tuple[list[BuiltMention], str]:
    """Names a continuation writes after its opener, and how they were read."""
    if report.split_confidence == "high" and report.sanad_ar is not None:
        text, how = report.sanad_ar, "sanad"
    else:
        # Low-confidence split: the words after the opener and its «قال:», up to the next colon or 80 letters; they
        # can only shorten the parent's chain, never extend it.
        text, how = report.text_ar[:240], "head"
    own, how = _names_after_opener(text, how)
    if not own and how == "sanad":
        # The span holds only the opener («وباسناده قال:»): the speaker the matn names first can only shorten the chain.
        own, _ = _names_after_opener(report.text_ar[:240], "head")
        how = "head" if own else how
    return own, how


def _names_after_opener(text: str, how: str) -> tuple[list[BuiltMention], str]:
    opener = OPENER.match(text) or NAMED_ROUTE.match(text)
    rest = text[opener.end():] if opener else text
    rest = re.sub(rf"^\s*(?:قال(?:ت|ا|وا)?{END}\s*[:.]?\s*)", "", rest)
    if how == "head":
        rest = SPEAKER_LEAD.sub("", rest)
        rest = re.split(r"[:«]", rest[:80], maxsplit=1)[0]
        rest = re.split(HONORIFIC, rest, maxsplit=1)[0]          # the speaker's words start after his blessing
    if re.match(rf"^\s*(?:عن|عنه){END}", rest) and not re.match(rf"^\s*عن\s+(?!النبي|رسول)", rest):
        rest = ""
    if re.match(rf"^\s*(?:قال\s+)?(?:رسول\s+الله|النبيء?|النبي){END}", rest) or re.match(rf"^\s*عنه{END}", rest):
        rest = ""
    branches = extract_names("عن " + rest) if rest.strip() else []
    return (branches[0] if branches else []), how


# al-Rabi's fixed transmitters: a route ending at one of them has no Companion for «ومن طريق X» to replace.
RABI_FIXED_LINKS = ("أبو عبيدة", "جابر بن زيد", "جابر")


def inherit(report: OpenitiReport, parent: list[list[BuiltMention]], parent_id: str,
            counts: Counter) -> tuple[list[list[BuiltMention]], bool]:
    """The parent's mentions, marked inherited, up to the link the continuation names; then its own links.

    Returns the branches and whether they replace the route for the reports that continue this one («ومن طريق X»).
    """
    own, how = continuation_own_names(report)
    if how == "head":
        # A head read from the text can only shorten: a word that names no link of the route («رسول اله», «رأيت النبي»)
        # is not a narrator of this report (round 3; round 2 dropped the whole chain for it).
        kept = [m for m in own if m.link_kind or any(continuation_names_match(m.surface, p.surface)
                                                     for branch in parent for p in branch if p.link_kind is None)]
        counts["inherited:head_words_outside_route_ignored"] += len(own) - len(kept)
        own = kept
    named_route = bool(NAMED_ROUTE.match(report.text_ar)) and not OPENER.match(report.text_ar)
    result = []
    for branch_index, branch in enumerate(parent):
        copied = list(branch)       # a route's mentions already name the written mention they repeat
        cut, own_start = None, None
        for own_index, mention in enumerate(own):
            if mention.link_kind:
                continue
            hits = [p for p, m in enumerate(branch) if m.link_kind is None and continuation_names_match(mention.surface, m.surface)]
            if hits:
                cut, own_start = hits[-1], own_index
                break
        if cut is not None and how == "head":
            counts["inherited:truncated_at_named_link:low_confidence_head"] += 1
            result.append(copied[:cut + 1])          # a low-confidence head only shortens the parent's chain
        elif cut is not None:
            counts["inherited:truncated_at_named_link"] += 1
            result.append(copied[:cut] + own[own_start:])
        elif own and how == "head":
            counts["inherited:low_confidence_names_outside_parent"] += 1
            return [], False
        elif own and named_route and not any(names_match(copied[-1].surface, fixed) for fixed in RABI_FIXED_LINKS):
            counts["inherited:named_route_replaces_last_link"] += 1
            result.append(copied[:-1] + own)
        elif own and named_route:
            # The route ends at the work's own transmitter (no Companion written): «ومن طريق X» adds X after him.
            counts["inherited:named_route_after_fixed_transmitter"] += 1
            result.append(copied + own)
        elif own:
            counts["inherited:extended_with_own_links"] += 1
            result.append(copied + own)
        else:
            counts["inherited:whole_parent_chain"] += 1
            result.append(copied)
    return result, named_route


def as_route(record_id: str, branches: list[list[BuiltMention]]) -> list[list[BuiltMention]]:
    """Branches as a continuation repeats them: every mention names the written mention it comes from."""
    return [[mention if mention.inherited_from else BuiltMention(mention.surface, mention.link_kind,
                                                                  (record_id, index, position), mention.rule_identity)
             for position, mention in enumerate(branch)] for index, branch in enumerate(branches)]


def build_openiti_chains(reports: Iterable[OpenitiReport], zayd_rule: "ZaydOpeningIsnad | None" = None) -> BuildResult:
    """Branches for every OpenITI report, in work order (parents before the continuations that name them)."""
    result = BuildResult()
    by_id = {report.record_id: report for report in reports}
    # route[r]: the chain a continuation of r repeats. «وباسناده» names the work's isnad, so a report that only
    # shortens or extends it passes its parent's route on unchanged; «ومن طريق X» makes X's route the new one.
    route: dict[str, list[list[BuiltMention]]] = {}

    def build(record_id: str, depth: int = 0) -> list[list[BuiltMention]]:
        if record_id in route:
            return route[record_id]
        if depth > 1000:
            raise ValueError(f"{record_id}: continuation pointers form a cycle")
        report = by_id[record_id]
        if report.inherits_from:
            parent_route = build(report.inherits_from, depth + 1)
            if parent_route:
                branches, replaces_route = inherit(report, parent_route, report.inherits_from, result.counts)
            else:
                result.counts["inherited:parent_route_has_no_chain"] += 1
                branches, replaces_route = [], False
            route[record_id] = as_route(record_id, branches) if replaces_route else parent_route
        else:
            branches = own_branches(report, result.counts)
            route[record_id] = as_route(record_id, branches)
        if zayd_rule and report.work == "zayd":
            branches = [zayd_rule.apply(branch, result.counts) for branch in branches]
        result.branches[record_id] = branches
        return route[record_id]

    for record_id in by_id:
        build(record_id)
        branches = result.branches[record_id]
        result.counts[f"reports_with_chain:{by_id[record_id].work}"] += bool(branches)
        result.counts[f"reports:{by_id[record_id].work}"] += 1
    return result


@dataclass(frozen=True)
class ZaydOpeningIsnad:
    """«زيد بن علي عن أبيه عن جده عن علي» read through the Musnad's own opening isnad (zayd_0001); exact shape only."""
    opening_record_id: str
    persons: Sequence[tuple[str, str, str]]   # (surface pattern, narrator id, what the opening isnad writes)

    def apply(self, branch: list[BuiltMention], counts: Counter) -> list[BuiltMention]:
        surfaces = [fold(m.surface) for m in branch]
        size = 0
        for index, (pattern, _, _) in enumerate(self.persons):
            if index < len(surfaces) and re.fullmatch(pattern, surfaces[index]):
                size = index + 1
            else:
                break
        # The shape must open with Zayd and include at least «أبيه»; a longer chain must continue the shape exactly.
        if size < 2 or (size < len(surfaces) and size < len(self.persons)):
            return branch
        counts[f"zayd_opening_isnad:shape_length_{size}"] += 1
        out = list(branch)
        for index in range(size):
            pattern, narrator_id, written = self.persons[index]
            detail = f"Musnad Zayd No. 1 ({self.opening_record_id.split(':')[2].split('|')[0]}): {written}"
            kind = "derived_relation" if index in (1, 2) else None
            out[index] = BuiltMention(branch[index].surface, kind or branch[index].link_kind,
                                      branch[index].inherited_from, (narrator_id, detail))
        return out


def load_zayd_rule(path: Path = RULES_PATH) -> tuple[ZaydOpeningIsnad, list[dict]]:
    """The Musnad Zayd opening-isnad rule and the register rows it needs (opening_isnad_rules.json)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    work = data["works"]["zaydi:musnad-zayd"]
    persons = [(fold(item["pattern"]), item["narrator_id"], item["written"]) for item in work["shape"]]
    return ZaydOpeningIsnad(work["opening_record_id"], persons), data["register_additions"]


# «غير واحد» (an unnamed collective) split by the extractor at the waw of «واحد» into sibling branches «غير» / «احد ...».
GHAYR = re.compile(r"^و?\s?غير$")
WAHID = re.compile(r"^و?احد(?:\s|$)")


def merge_ghayr_wahid(branches: list[list], surface=lambda item: item) -> tuple[list[list], int]:
    """Siblings equal except «غير» / «احد ...» at one position become one branch carrying «غير واحد ...»; the other is
    emptied (indices kept, so a branch's origin still names its bundle branch). Returns the branches and the merges."""
    out = [list(branch) for branch in branches]
    merged = 0
    for i, branch in enumerate(out):
        for j, other in enumerate(out):
            if i == j or not branch or len(branch) != len(other):
                continue
            keys_i = [_plain(surface(item)) for item in branch]
            keys_j = [_plain(surface(item)) for item in other]
            differ = [p for p, (a, b) in enumerate(zip(keys_i, keys_j)) if a != b]
            if len(differ) == 1 and GHAYR.match(keys_i[differ[0]]) and WAHID.match(keys_j[differ[0]]):
                p = differ[0]
                wahid = surface(other[p]).strip()
                text = surface(branch[p]).strip() + (" " if wahid.startswith("و") else " و") + wahid
                branch[p] = (text,) + tuple(branch[p][1:]) if isinstance(branch[p], tuple) else text
                out[j] = []
                merged += 1
    return out, merged


def _plain(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[ً-ٰٟـ]", "", value)).strip()


# ─── Imami (Thaqalayn) chains: «جميعا» groups, non-narrators, suspended chains, anonymous gaps ─────────────────────

IMAMI_FOLD = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ی": "ي", "ک": "ك"})
# The previous report's chain, by a pronoun or a formula (taʿliq): a label, never a narrator.
BACK_REFERENCE = re.compile(rf"^(?:و\s?)?(?:عنه|عنهم|عنهما|به|بهذا|بهذه|باسناده|بالاسناد|بالاسانيد){END}")
# «وبهذا الإسناد», directly after a report of the same chapter: the antecedent is mechanically certain.
SAME_ISNAD = re.compile(rf"^(?:و\s?)?(?:بهذا|بهذه)\s+(?:الاسناد|الاسانيد|السند){END}")
VERB_PREFIX = re.compile(rf"^(?:و\s?)?(?:قد\s+)?(?:روي|وروي|روى|وروى|قال|وقال|سال|سئل|وسئل|ذكر|في\s+رواية|في\s+خبر"
                         rf"|حدثنا|حدثني|اخبرنا|اخبرني){END}\s*")
# «ره» (رحمه الله) after a name; a lone conjunction the extractor kept as a mention («وَ حَدَّثَنِي»: «و»).
RAHIMAHU = re.compile(rf"\s+ره$")
# Thawab al-Aʿmal writes Persian ya and kaf («حَدَّثَنِی»): the extractor's verbs do not match them, so names after them are lost.
PERSIAN_LETTERS = str.maketrans({"ی": "ي", "ک": "ك"})
# What follows a name in the text but is not part of it: a doubt («أو»), «مثله», a Qur'an cue, a reported clause.
IMAMI_TRAILING = re.compile(
    rf"\s+(?:او|أو|مثله|نحوه|زاد\s+فيه|في\s+قوله|في\s+قول\s+الله|انه|أنه|انها|أنها|انهما|قال|يقول|عنه"
    rf"|في\s+(?:ال)?(?:رجل|رجلين|امراة|مراة|متوفي|قوم|عبد|جارية)|رحمة\s+الله|رحمه\s+الله|رضي\s+الله){END}.*$")
# The al-Kafi compiler's own shaykhs (the audit lane's list): a group or a fused name that starts with one starts a route.
KULAYNI_SHAYKH = frozenset(["علي بن ابراهيم", "علي بن ابراهيم بن هاشم", "محمد بن يحيي", "عدة من اصحابنا", "الحسين بن محمد",
                            "الحسين بن محمد الاشعري", "ابو علي الاشعري", "حميد بن زياد", "محمد بن اسماعيل", "احمد بن ادريس"])
KULAYNI_SHAYKH_UNSPACED = frozenset(name.replace(" ", "") for name in KULAYNI_SHAYKH)
def is_kulayni_shaykh(folded: str) -> bool:
    """One of al-Kulayni's shaykhs, however the edition spaces the kunya («أبوعلي الاشعري»)."""
    return folded.replace(" ", "") in KULAYNI_SHAYKH_UNSPACED


SADUQ_WORKS = frozenset(["al-amali-saduq", "al-khisal", "al-tawhid-saduq", "kamal-al-din", "maani-al-akhbar", "thawab-al-amal",
                         "uyun-akhbar-al-rida", "fadail-al-shia", "sifat-al-shia", "man-la-yahduruhu-al-faqih"])
ASKED_OBJECT = re.compile(r"\s+(?=ابا\s+\S)")
CLAUSE_WORDS = frozenset("ولا ليس الا لان فقد هذا ذلك اذا فان لم ما كان كانت كانوا الذي التي ان انه انها اي حيث ثم او هو هي".split())
NUMBER_WORDS = frozenset(
    "واحد اثنين اثنتين ثلاث ثلاثة اربع اربعة خمس خمسة ست ستة سبع سبعة ثمان ثماني ثمانية تسع تسعة عشر عشرة عشرين "
    "ثلاثين اربعين خمسين ستين سبعين ثمانين تسعين مائة ماية مائتين مئتين ثلاثمائة اربعمائة خمسمائة الف سنة شهر رمضان "
    "محرم صفر ربيع الاول الاخر جمادي رجب شعبان شوال القعدة الحجة في".split())
# A volume/page citation of the Mujam and the book it cites («3/45 معاني الاخبار»): not part of a name.
CITATION_PREFIX = re.compile(
    r"^/?[0-9]+(?:/[0-9]+)*\s+(?:(?:اصول\s+)?الكافي|رجال\s+الكشي|توحيد\s+الصدوق|التوحيد|الخصال|تهذيب\s+الاحكام|التهذيب"
    r"|علل\s+الشرائع|غيبة\s+الطوسي|غيبة\s+النعماني|معاني\s+الاخبار|الفقيه|العيون|عيون\s+اخبار\s+الرضا|ارشاد\s+المفيد|الارشاد"
    r"|امالي\s+\S+|الامالي|كمال\s+الدين|ثواب\s+الاعمال|بصائر\s+الدرجات|المحاسن|الاحتجاج|الاستبصار)?\s*")
FOOTNOTE_DIGIT = re.compile(r"(?:^|\s)[0-9]+(?=\s|$)")
# Gap markers after a name: he did not hear from the next name; the words become an unnamed-transmitter mention.
GAP_SUFFIX = re.compile(
    rf"\s+(?P<gap>رفعه|يرفعه|عمن\s+ذكره|عمن\s+رواه|عمن\s+حدثه|يبلغ\s+به|مرسلا|عن\s+رجل(?:\s+.*)?|عن\s+بعض(?:\s+\S+)?)$")
ANONYMOUS = re.compile(
    rf"^(?:و\s?)?(?:رجل|رجلا|الرجل|بعض\s+اصحابه|بعض\s+اصحابنا|بعض\s+رجاله|بعضهم|عمن\s+ذكره|عمن\s+رواه|عمن\s+حدثه"
    rf"|بعض\s+من\s+رواه|رفعه|يرفعه|رجل\s+من\s+\S+|من\s+ذكره|غير\s+واحد(?:\s+من\s+\S+)?)(?:\s+(?:رفعه|يرفعه))?$")
IMAM_SURFACE = re.compile(
    rf"^(?:و\s?)?(?:(?:ابي|ابا|ابو)\s+(?:عبد\s+الله|جعفر|الحسن|ابراهيم)|الصادق|الباقر|الكاظم|الرضا|الجواد|الهادي|العسكري"
    rf"|السجاد|امير\s+المومنين|امير\s+المؤمنين){END}")
MATN_HEAD = re.compile(rf"^(?:الرجل|رجل|المراة|امراة|الميت|ما|هل|في|ان|لو|اذا){END}")
FUSED_PAIR = re.compile(
    rf"^(?P<left>ابي|\S+(?:\s+\S+){{0,7}}?)(?<!\sبن)(?<!\sابن)(?<!\sابي)(?<!\sابو)\s+و\s*(?P<right>(?:محمد|احمد|علي|الحسين|الحسن|ابراهيم|عبد"
    rf"|سعد|عمر|يحيي|جعفر|موسي|هارون|ابي|ابن|الفضل|سهل|صفوان|حماد|جميل|عثمان|القاسم){END}.*)$")
LINK_WORD = re.compile(rf"(?<![ء-ي])(?:عن|حدثنا|حدثني|اخبرنا|اخبرني){END}")


def imami_fold(surface: str) -> str:
    """Marks dropped, alef, ya and Persian letters folded (the audit lane's `fold`)."""
    return re.sub(r"\s+", " ", re.sub(r"[ً-ٰٟـ]", "", surface).translate(IMAMI_FOLD)).strip()


def jamian_groups(text: str) -> list[str] | None:
    """«A عن B و C عن D جميعا عن E»: each group with its own inner «عن» is its own route to E; else None.

    «A عن B و C جميعا عن E» (no inner link after the waw) is a plain co-transmitter level and stays as the extractor reads it.
    """
    original = _strip_arabic_marks(text)
    plain = original.translate(IMAMI_FOLD)          # same length: slices of the folded text are slices of the original
    at = plain[:900].find("جميعا")
    # Commas are allowed around the links («عن أبيه، ومحمد بن إسماعيل، عن الفضل بن شاذان جميعا، عن ابن أبي عمير»).
    if at < 0 or not re.match(rf"^[\s،,]*عن{END}", plain[at + len("جميعا"):]):
        return None
    prefix, tail = plain[:at], original[at + len("جميعا"):]
    cuts, last = [], 0
    for match in re.finditer(r"[\s،,؛]+و\s*(?=[ء-ي])", prefix):
        left, right = prefix[last:match.start()], prefix[match.end():]
        previous = left.split()[-1] if left.split() else ""
        if previous in ("بن", "ابن", "ابي", "ابو", "ام") or not LINK_WORD.search(left) or not LINK_WORD.search(right):
            continue
        cuts.append((match.start(), match.end()))
        last = match.end()
    if not cuts:
        return None
    if re.search(r"[\s،,]+و\s*(?=[ء-ي])", prefix[last:]) and not LINK_WORD.search(prefix[last:].rsplit(" و", 1)[-1]):
        return []      # the last group ends in a co-transmitter level («عن صفوان و ابن أبي عمير جميعا»): ambiguous, left as read
    groups, start = [], 0
    for begin, end in cuts:
        groups.append(original[start:begin])
        start = end
    groups.append(original[start:at])
    # The opening name as written (cut where the folded copy finds the first link: the two have the same length).
    first_link = LINK_WORD.search(groups[0].translate(IMAMI_FOLD))
    first_name = groups[0][:first_link.start() if first_link else None].strip(" ،,")
    routes = [groups[0].strip()]
    for group in groups[1:]:
        opening = re.split(LINK_WORD, group.translate(IMAMI_FOLD), maxsplit=1)[0].strip(" ،,")
        # A group that opens with one of the compiler's shaykhs is a route of its own; otherwise it hangs from the first
        # group's opening name («علي بن إبراهيم عن أبيه و محمد بن عيسى عن يونس»: both are ʿAli b. Ibrahim's shaykhs).
        routes.append(group.strip() if is_kulayni_shaykh(opening) else f"{first_name} عن {group.strip()}")
    return [route + " " + tail.strip() for route in routes]


def kulayni_parallel_groups(text: str) -> list[str] | None:
    """al-Kafi «A عن B و C عن D عن E ...» with no «جميعا», A and C both al-Kulayni's shaykhs: two routes meeting at E
    (Kafi 19, Noor 118532: «علي بن إبراهيم عن أبيه» and «عدة من أصحابنا عن سهل بن زياد», both to «ابن محبوب»)."""
    original = _strip_arabic_marks(text)
    plain = original.translate(IMAMI_FOLD)
    if "جميعا" in plain[:900]:
        return None
    links = list(re.finditer(r"[\s،,]+عن\s+", plain[:900]))
    if len(links) < 3:
        return None
    head = re.sub(r"^\s*[0-9]+\s*[ـ-]?\s*", "", plain[:links[0].start()]).strip(" ،,")
    middle = plain[links[0].end():links[1].start()]
    waw = re.search(r"[\s،,]+و\s*(?=[ء-ي])", middle)
    if not is_kulayni_shaykh(head) or not waw or not is_kulayni_shaykh(middle[waw.end():].strip(" ،,")):
        return None
    first_end, second_start = links[0].end() + waw.start(), links[0].end() + waw.end()
    return [original[:first_end] + original[links[2].start():], original[second_start:]]


@dataclass(frozen=True)
class ImamiChain:
    mentions: list[BuiltMention]
    suspension: str | None = None     # back_reference | mid_chain_start | route_given_elsewhere


class Written:
    """A surface as written (marks already stripped) and its folded twin of the same length, cut together."""

    def __init__(self, surface: str):
        self.text = re.sub(r"\s+", " ", surface).strip()
        self.folded = self.text.translate(IMAMI_FOLD)

    def cut(self, start: int, end: int | None = None) -> "Written":
        return Written(self.text[start:end])

    def drop_digits(self) -> "Written":
        return Written(FOOTNOTE_DIGIT.sub(" ", self.text))


# Words that open an Imam's speech or blessing right after his name in one surface («أمير المؤمنين نعم البيت …», «الصادق إذا …»);
# a name after the kunya («أبو عبد الله أحمد بن عمار») or a qualifier («أبي الحسن الرضا») never does.
IMAM_SPEECH_START = frozenset(["في", "لا", "من", "ما", "اذا", "ان", "انه", "انها", "نعم", "قد", "لو", "كان", "يقول", "قال",
                               "فقال", "صلوات", "صلي", "عليه", "عليهم", "لم", "ليس", "هو", "هذا", "انما", "كل"])


def is_clause(tokens: list[str]) -> bool:
    """A run of folded words that is a sentence, not a name (few nasab words, a function word or twelve words)."""
    return tokens.count("بن") < 3 and ((len(tokens) >= 3 and any(token in CLAUSE_WORDS for token in tokens)) or len(tokens) >= 12)


def is_prose_opening(branch: list[str]) -> bool:
    """A branch that opens with a sentence and names nobody: no report verb or back-reference opens it, and no surface has a
    nasab or is an Imam («ولا يجوز في الأضاحي …»; never «وقال أمير المؤمنين: …» or «وبهذا الإسناد في الرجل …»)."""
    first = imami_fold(_strip_arabic_marks(branch[0]))
    if not is_clause(first.split()) or VERB_PREFIX.match(first) or BACK_REFERENCE.match(first):
        return False
    return not any(NASAB.search(imami_fold(surface)) or IMAM_SURFACE.match(imami_fold(surface)) for surface in branch)


def persian_safe_branches(text_ar: str, extract=extract_isnad_branches) -> list[list[str]] | None:
    """The extractor's branches of a text written with Persian ya/kaf, read on a copy with the Arabic letters (matching only):
    each surface is cut back out of the original text, so its letters stay as written. None if one cannot be located."""
    original = _strip_arabic_marks(text_ar)
    folded = original.translate(PERSIAN_LETTERS)          # one letter for one: offsets agree
    out = []
    for branch in extract(text_ar.translate(PERSIAN_LETTERS)):
        written, cursor = [], 0
        for surface in branch:
            pattern = re.escape(surface).replace(r"\ ", r"\s+")
            hit = re.compile(rf"(?<![ء-ي]){pattern}(?![ء-ي])").search(folded, cursor) or re.compile(pattern).search(folded)
            if not hit:
                return None
            written.append(re.sub(r"\s+", " ", original[hit.start():hit.end()]).strip())
            cursor = hit.end()
        out.append(written)
    return out


def clean_imami_mention(surface: str, position: int, after_imam: bool, work: str,
                        counts: Counter) -> tuple[list[BuiltMention], str | None]:
    """One stored surface as zero or more mentions, and the chain's suspension when this opening says so."""
    name = Written(surface)
    if name.folded in ("و", ""):
        counts["bare_conjunction_dropped"] += 1
        return [], None
    if RAHIMAHU.search(name.folded) and len(name.folded.split()) > 1:
        counts["rahimahu_removed"] += 1
        name = name.cut(0, RAHIMAHU.search(name.folded).start())
    if position == 0 and BACK_REFERENCE.match(name.folded):
        counts["back_reference_label"] += 1
        return [BuiltMention(name.text, link_kind="not_a_narrator")], "back_reference"
    suspension = None
    if re.match(r"^(?:/[0-9]+|[0-9]+/[0-9]+)\s", name.folded):
        counts["citation_prefix_removed"] += 1
        name = name.cut(CITATION_PREFIX.match(name.folded).end())
        if not name.text:
            return [], None
    if FOOTNOTE_DIGIT.search(name.folded) and len(name.folded.split()) > 1:
        counts["footnote_digit_removed"] += 1
        name = name.drop_digits()
    verb = VERB_PREFIX.match(name.folded)
    if verb:
        counts[f"verb_prefix_removed:{work}"] += 1
        name = name.cut(verb.end())
        if position == 0 and work == "man-la-yahduruhu-al-faqih":
            suspension = "route_given_elsewhere"
        pronoun = re.match(rf"^عنه{END}\s*", name.folded)
        if pronoun:
            name = name.cut(pronoun.end())
            suspension = "back_reference"
        if not name.text:
            return [], suspension
    if re.search(r"\s+و$", name.folded):
        name = name.cut(0, re.search(r"\s+و$", name.folded).start())      # a waw left by the next co-transmitter's split
    trailing = IMAMI_TRAILING.search(name.folded)
    if trailing and name.folded[:trailing.start()].strip():
        counts["trailing_words_removed"] += 1
        name = name.cut(0, trailing.start())
    if position == 0 and work in SADUQ_WORKS and "بابويه" in name.folded:
        counts["compiler_not_a_mention"] += 1
        return [], suspension
    tokens = name.folded.split()
    if tokens and all(token.removeprefix("و") in NUMBER_WORDS for token in tokens) and any(
            token.removeprefix("و") not in ("سنة", "شهر", "في", "رمضان") for token in tokens):
        counts["numeral_dropped"] += 1
        return [], suspension
    if after_imam and (MATN_HEAD.match(name.folded) or (len(tokens) >= 4 and "بن" not in tokens)):
        counts["matn_after_imam_dropped"] += 1
        return [], suspension
    imam = IMAM_SURFACE.match(name.folded)
    after = name.folded[imam.end():].split() if imam else []
    if imam and after and (after[0] in IMAM_SPEECH_START or (len(after) >= 3 and not NASAB.search(" ".join(after)))):
        counts["imam_then_matn_cut"] += 1          # «أمير المؤمنين نعم البيت الحمام …»: the speaker, then his words
        return [BuiltMention(name.cut(0, imam.end()).text)], suspension
    if is_clause(tokens):
        counts["clause_dropped"] += 1
        return [], suspension
    if ANONYMOUS.match(name.folded):
        counts["anonymous_marked"] += 1
        return [BuiltMention(name.text, link_kind="anonymous")], suspension
    gap = GAP_SUFFIX.search(name.folded)
    if gap and name.folded[:gap.start()].strip():
        counts["gap_split_from_name"] += 1
        return [BuiltMention(name.cut(0, gap.start()).text),
                BuiltMention(name.cut(gap.start("gap")).text, link_kind="anonymous")], suspension
    asked = ASKED_OBJECT.search(name.folded) if verb else None
    if asked:
        counts["asked_imam_split"] += 1                 # «سأل صفوان بن يحيى أبا الحسن»: the asker, then the Imam
        return [BuiltMention(name.cut(0, asked.start()).text), BuiltMention(name.cut(asked.end()).text)], suspension
    return [BuiltMention(name.text)], suspension


def split_fused(mention: BuiltMention, counts: Counter) -> list[BuiltMention]:
    """«أبي و محمد بن الحسن» in one surface: two co-transmitters at one position (each on its own branch)."""
    if mention.link_kind:
        return [mention]
    name = Written(mention.surface)
    match = FUSED_PAIR.match(name.folded)
    if not match:
        return [mention]
    counts["fused_cotransmitters_split"] += 1
    return [BuiltMention(name.cut(0, match.end("left")).text), BuiltMention(name.cut(match.start("right")).text)]


def build_imami_chains(text_ar: str, branches: list[list[str]], work: str, counts: Counter,
                       extract=extract_isnad_branches) -> list[ImamiChain]:
    """Re-cut one Thaqalayn report: «جميعا» groups as separate routes, then each surface cleaned (see above)."""
    if any(letter in text_ar for letter in "یک"):
        refolded = persian_safe_branches(text_ar, extract)
        if refolded is None:
            counts["persian_letters_kept_bundle_branches"] += 1
        elif refolded != branches:
            counts["persian_letters_reextracted"] += 1
            branches = refolded
    branches, merged = merge_ghayr_wahid(branches)
    counts["ghayr_wahid_merged"] += merged
    # A branch that opens with a sentence is matn, not an isnad (Amali al-Saduq 93: 192 "chains" of a ruling's nouns).
    prose = [branch for branch in branches if branch and is_prose_opening(branch)]
    counts["prose_opening_dropped"] += len(prose)
    branches = [branch for branch in branches if branch and branch not in prose]
    groups = jamian_groups(text_ar)
    if groups is None and work == "al-kafi":
        groups = kulayni_parallel_groups(text_ar)
        counts["kulayni_parallel_groups"] += bool(groups)
    if groups == []:
        counts["jamian_ambiguous_left_as_read"] += 1
    if groups:
        regrouped: list[list[str]] = []
        for group in groups:
            for branch in extract(group):
                if branch and branch not in regrouped:
                    regrouped.append(branch)
        if regrouped:
            counts["jamian_regrouped_reports"] += 1
            branches = regrouped
    out: list[ImamiChain] = []
    for branch in branches:
        first_isnad = -1
        levels: list[list[BuiltMention]] = []
        suspension = None
        after_imam = False
        restart: list[list[BuiltMention]] | None = None
        for position, surface in enumerate(branch):
            mentions, opening = clean_imami_mention(surface, len(levels), after_imam, work, counts)
            suspension = suspension or opening
            for mention in mentions:
                alternatives = split_fused(mention, counts)
                if (restart is None and work == "al-kafi" and len(alternatives) == 2 and levels
                        and is_kulayni_shaykh(imami_fold(alternatives[1].surface))):
                    # «... عن حنان بن سدير و محمد بن يحيى عن ...»: a second isnad starts with the compiler's shaykh.
                    counts["second_isnad_split_at_compiler_shaykh"] += 1
                    out.append(ImamiChain([m for level in levels for m in level[:1]] + [alternatives[0]], suspension))
                    first_isnad = len(out) - 1
                    restart = [[alternatives[1]]]
                    levels = restart
                    continue
                levels.append(alternatives)
            if mentions:
                after_imam = bool(IMAM_SURFACE.match(imami_fold(mentions[-1].surface)))
        if restart is not None and len(levels) >= 3:
            # The second isnad is the shaykh and his teacher («و علي بن إبراهيم عن أبيه»); both meet at the next name
            # (k6 re-check row thaqalayn:4087da29: «… عن محمد بن إسماعيل و علي بن إبراهيم عن أبيه عن حنان بن سدير»).
            counts["first_isnad_given_shared_tail"] += 1
            out[first_isnad] = ImamiChain(out[first_isnad].mentions + [level[0] for level in levels[2:]], suspension)
        expanded: list[list[BuiltMention]] = [[]]
        for alternatives in levels:
            if len(expanded) * len(alternatives) > 64:
                alternatives = alternatives[:1]
            expanded = [path + [mention] for path in expanded for mention in alternatives]
        for path in expanded:
            surfaces = [mention.surface for mention in path]
            # A chain of the formula alone («وبهذا الإسناد») stays: it says the report relies on the previous one.
            if path and (suspension or any(mention.link_kind is None for mention in path)) and all(
                    surfaces != [mention.surface for mention in chain.mentions] for chain in out):
                out.append(ImamiChain(path, suspension))
    chains = [with_imam_tail(text_ar, chain, counts) for chain in drop_matn_beside_imam(out, counts)]
    # A chain that is exactly the start of another of the report adds no link (a fused matn split off after the Imam).
    surfaces = [[m.surface for m in chain.mentions] for chain in chains]
    prefixes = [index for index, own in enumerate(surfaces) if not chains[index].suspension and any(
        len(other) > len(own) and other[:len(own)] == own for other in surfaces)]
    counts["prefix_duplicate_dropped"] += len(prefixes)
    chains = [chain for index, chain in enumerate(chains) if index not in prefixes
              and surfaces[index] not in surfaces[:index]]          # and a twin the tail rules made identical
    tailed = [with_jamian_tail(text_ar, chain, counts) for chain in chains]
    # Co-transmitters at the last level («ابن أبي عمير؛ و الحسن بن محبوب جميعا عن X») share the name the last one reached.
    shared = {tuple(m.surface for m in old.mentions[:-1]): new.mentions[-1]
              for old, new in zip(chains, tailed) if len(new.mentions) > len(old.mentions)}
    return [new if len(new.mentions) > len(old.mentions) or tuple(m.surface for m in old.mentions[:-1]) not in shared
            else ImamiChain(old.mentions + [shared[tuple(m.surface for m in old.mentions[:-1])]], old.suspension)
            for old, new in zip(chains, tailed)]


# «… ابن أبي عمير؛ و الحسن بن محبوب جميعا عن عبد الرحمن بن الحجاج» at the end of a text: the extractor drops the shared name.
JAMIAN_TAIL = re.compile(rf"^[\s،,؛]*جميعا[\s،,]*عن\s+(?P<name>[ء-ي]+(?:\s+[ء-ي]+){{0,5}}?)\s*(?=[.،,:؛]|$|\s+(?:قال|انه|و){END})")


# «… عن مسمع بن عبد الملك عن أبي عبد الله عليه السلام :»: the Imam the extractor stopped short of.
IMAM_TAIL = re.compile(rf"^[\s،,]*عن\s+(?P<imam>(?:ابي|ابا|ابو)\s+(?:عبد\s+الله|جعفر|الحسن|ابراهيم)|الصادق|الباقر|الكاظم|الرضا"
                       rf"|امير\s+المومنين|امير\s+المؤمنين){END}\s*(?:\(?\s*(?:ع|عليه(?:ما)?\s+السلام|صلوات\s+الله\s+عليه)\s*\)?)")


def with_imam_tail(text_ar: str, chain: ImamiChain, counts: Counter) -> ImamiChain:
    """The chain with the Imam the text names right after its last link («عن أبي عبد الله عليه السلام»), when it lacks one."""
    if (not chain.mentions or chain.mentions[-1].link_kind == "not_a_narrator"
            or IMAM_SURFACE.match(imami_fold(chain.mentions[-1].surface))):
        return chain
    original = _strip_arabic_marks(text_ar)
    folded = original.translate(IMAMI_FOLD)
    last = re.escape(imami_fold(chain.mentions[-1].surface)).replace(r"\ ", r"\s+")
    hit = re.search(rf"(?<![ء-ي]){last}(?![ء-ي])", folded)
    tail = IMAM_TAIL.match(folded[hit.end():]) if hit else None
    if not tail:
        return chain
    counts["imam_tail_added"] += 1
    imam = original[hit.end() + tail.start("imam"):hit.end() + tail.end("imam")]
    return ImamiChain(chain.mentions + [BuiltMention(re.sub(r"\s+", " ", imam).strip())], chain.suspension)


def with_jamian_tail(text_ar: str, chain: ImamiChain, counts: Counter) -> ImamiChain:
    """The chain with the name its last link shares through a closing «جميعا عن X», when the text gives one."""
    if not chain.mentions or chain.mentions[-1].link_kind:
        return chain
    original = _strip_arabic_marks(text_ar)
    folded = original.translate(IMAMI_FOLD)
    last = re.escape(imami_fold(chain.mentions[-1].surface)).replace(r"\ ", r"\s+")
    hits = list(re.finditer(rf"(?<![ء-ي]){last}(?![ء-ي])", folded))
    tail = JAMIAN_TAIL.match(folded[hits[-1].end():]) if hits else None
    if not tail:
        return chain
    start = hits[-1].end() + tail.start("name")
    name = re.sub(r"\s+", " ", original[start:hits[-1].end() + tail.end("name")]).strip()
    if any(imami_fold(m.surface) == imami_fold(name) for m in chain.mentions):
        return chain
    counts["jamian_tail_added"] += 1
    return ImamiChain(chain.mentions + [BuiltMention(name)], chain.suspension)


def drop_matn_beside_imam(chains: list[ImamiChain], counts: Counter) -> list[ImamiChain]:
    """A chain equal to another but for its last name, where the other ends at an Imam and this one at no name the Imam
    could stand beside, is the matn read as a co-transmitter («عن أبي الحسن في الرجل يطلي ويتدلك بالزيت والدقيق»)."""
    imam_ends = {tuple(m.surface for m in chain.mentions[:-1]) for chain in chains
                 if chain.mentions and IMAM_SURFACE.match(imami_fold(chain.mentions[-1].surface))}
    kept = []
    for chain in chains:
        last = chain.mentions[-1] if chain.mentions else None
        if (last is not None and last.link_kind is None and tuple(m.surface for m in chain.mentions[:-1]) in imam_ends
                and not IMAM_SURFACE.match(imami_fold(last.surface)) and not NASAB.search(last.surface)):
            counts["matn_beside_imam_dropped"] += 1
            continue
        kept.append(chain)
    return kept


def mark_mid_chain_starts(reports: dict[str, tuple[str, str]], built: dict[str, list[ImamiChain]],
                          counts: Counter) -> dict[tuple[str, int], str]:
    """al-Kafi chains that open mid-isnad (the audit's D02b): the opening name is not one of the compiler's shaykhs,
    stands first in under a fifth of its 20 or more appearances, and the report's text starts with it."""
    seen: dict[str, list[int]] = {}
    for hadith_id, chains in built.items():
        if reports[hadith_id][0] != "imami:al-kafi":
            continue
        for chain in chains:
            for position, mention in enumerate(chain.mentions):
                tally = seen.setdefault(imami_fold(mention.surface), [0, 0])
                tally[0 if position == 0 else 1] += 1
    marked: dict[tuple[str, int], str] = {}
    for hadith_id, chains in built.items():
        work, text = reports[hadith_id]
        if work != "imami:al-kafi":
            continue
        opening_text = re.sub(r"^\s*[0-9]+\s*[ـ-]?\s*", "", imami_fold(_strip_arabic_marks(text)))
        for index, chain in enumerate(chains):
            if chain.suspension or not chain.mentions or chain.mentions[0].link_kind:
                continue
            first = imami_fold(chain.mentions[0].surface)
            first_count, middle_count = seen.get(first, (0, 0))
            if (first not in KULAYNI_SHAYKH and middle_count >= 20 and first_count / (first_count + middle_count) < 0.2
                    and opening_text.startswith(first)):
                marked[(hadith_id, index)] = "mid_chain_start"
                counts["mid_chain_start_marked"] += 1
    return marked


def resolve_same_isnad(built: dict[str, list[ImamiChain]], previous: dict[str, str], record_ids: dict[str, str],
                       counts: Counter) -> dict[str, int]:
    """«وبهذا الإسناد ...» right after a report of the same chapter takes that report's chain (marked inherited), up to the
    link it names; every other back-reference stays marked and unfilled. Returns the inheriting reports' depth."""
    depth: dict[str, int] = {}
    settled: dict[str, int] = {}

    def resolve(hadith_id: str, guard: int = 0) -> int:
        if hadith_id not in settled:
            settled[hadith_id] = attempt(hadith_id, guard)
        return settled[hadith_id]

    def attempt(hadith_id: str, guard: int) -> int:
        chains = built[hadith_id]
        opening = chains[0].mentions[0] if chains and chains[0].mentions else None
        parent = previous.get(hadith_id)
        if (opening is None or opening.link_kind != "not_a_narrator" or not SAME_ISNAD.match(imami_fold(opening.surface))
                or parent is None or guard > 200):
            return 0
        counts["same_isnad_after_previous_report"] += 1
        parent_depth = resolve(parent, guard + 1)
        usable = [(index, chain) for index, chain in enumerate(built[parent]) if chain.suspension is None]
        if not usable:
            counts["same_isnad_previous_report_has_no_usable_chain"] += 1
            return 0
        own = list(chains[0].mentions[1:])
        route = [[mention if mention.inherited_from else BuiltMention(
                      mention.surface, mention.link_kind, (record_ids[parent], index, position), mention.rule_identity)
                  for position, mention in enumerate(chain.mentions)] for index, chain in usable]
        resolved = []
        for branch in route:
            cut = None
            if own and own[0].link_kind is None:
                hits = [p for p, m in enumerate(branch) if m.link_kind is None and names_match(own[0].surface, m.surface)]
                cut = hits[-1] if hits else None
            if own and cut is None:
                continue          # «وبهذا الإسناد عن X» with X not in the previous chain: where it joins is not certain
            resolved.append(ImamiChain(branch[:cut] + own if cut is not None else branch, None))
        if not resolved:
            counts["same_isnad_named_link_not_in_previous_chain"] += 1
            return 0
        built[hadith_id] = resolved + chains[1:]
        counts["same_isnad_resolved"] += 1
        depth[hadith_id] = parent_depth + 1
        return depth[hadith_id]

    for hadith_id in list(built):
        resolve(hadith_id)
    return depth


# ─── Sunni chains: tahwil routes with their shared tail, names after link verbs, formula surfaces (rounds 2-3) ─────────

SUNNI_DIACRITICS = re.compile(r"[ً-ْٰـۖ-ۭ]")
SUNNI_INVISIBLE = frozenset("‏‎‫‬")
# A route break between two stored neighbours: a standalone «ح» or a new waw-led transmission verb.
TAHWIL_H = re.compile(r"(?:^|\s)ح(?=[\s.،,]|$)")
NEW_ROUTE_VERB = re.compile(r"(?:^|\s)(?:قال\s+)?و(?:اخبرنا|حدثنا|اخبرني|حدثني|انبانا|انباني|سمعت|اخبرتنا|حدثتنا)(?=\s|$)")
# After the last route break only a verb may stand before the next stored name: that name heads the new route.
ROUTE_HEAD_GAP = re.compile(r"^[\s.،,:\-]*(?:قال\s+)?و?\s*(?:(?:حدثنا|حدثني|اخبرنا|اخبرني|انبانا|انباني|ثنا|نا|سمعت|حدثناه"
                            r"|حدثنيه|اخبرناه|اخبرنيه)(?:\s+به)?)?[\s.،,:\-]*$")
# Routes converge on one narrator: «كلاهما عن», «كلهم عن», «جميعا عن».
CONVERGENCE_WORD = re.compile(r"(?<![ء-ي])(?:كلاهما|كلتاهما|كلهم|جميعا|ثلاثتهم|اربعتهم|كل\s+هؤلاء)(?![ء-ي])")
PROPHET_IN_TEXT = re.compile(r"(?<![ء-ي])(?:رسول\s+الله|النبي)(?![ء-ي])")
# What may stand between a name and the next route break or convergence word: punctuation, «وهو ابن زيد», «يعني ابن
# عيينة», «واللفظ له». Consumed from the left until none applies.
LEADING_ASIDE = re.compile(r"^(?:[\s.،,:\-]+|و?هو\s+(?:ابن\s+)?[ء-ي]+(?:\s+(?:بن|ابن)\s+[ء-ي]+)?|يعني\s+(?:ابن\s+)?[ء-ي]+"
                           r"(?:\s+(?:بن|ابن)\s+[ء-ي]+)?|و?اللفظ\s+(?:له|ل[ء-ي]+(?:\s+[ء-ي]+)?))")
# Two neighbours joined only by a waw or a comma: co-transmitters at one level.
WAW_GAP = re.compile(r"^[\s،,]*و?[\s،,]*$")
# A wording attribution after a co-transmitter level («قال ابن المثنى حدثنا»): the extractor stops there.
# Also the double form «قال عبد أخبرنا وقال ابن رافع حدثنا» (each co-transmitter's verb): both attributions go.
WORDING_ATTRIBUTION = re.compile(
    r"^قال[\s،,]+(?P<name>(?!رسول|النبي)[ء-ي]+(?:\s+[ء-ي]+){0,3}?)[\s،,]+(?:(?:حدثنا|حدثني|اخبرنا|اخبرني|انبانا)[\s،,]+"
    r"و?قال[\s،,]+(?:[ء-ي]+(?:\s+[ء-ي]+){0,3}?)[\s،,]+)?(?=(?:حدثنا|حدثني|اخبرنا|اخبرني|انبانا)(?![ء-ي]))")
CONVERGENCE_LINK = re.compile(r"^(?:كلاهما|كلتاهما|كلهم|جميعا|ثلاثتهم|اربعتهم)[\s،,]+(?=عن(?![ء-ي]))")
# «كلاهما عن عبد الله بن دينار، بهذا الإسناد»: the one name before a back-reference (the extractor drops it).
CONVERGENCE_THEN_REFERENCE = re.compile(
    r"^عن\s+(?P<name>[ء-ي]+(?:\s+[ء-ي]+){0,5}?)[\s،,]*(?=(?:بهذا|بهذه|باسناد[ء-ي]*|بمثل[ء-ي]*|بمعني|بنحو|نحوه|مثله)(?![ء-ي]))")
# A narrator the text names after the stored chain ends, through a transmission verb («، أن عائشة، أخبرته»).
TEXT_LINK_AFTER = re.compile(
    r"^[\s،,]*(?:قال\s+)?(?:انه|انها|انهما|انهم)?\s*(?:سمع|سمعا|سمعوا)\s+(?P<heard>(?!رسول|النبي|رجل)[ء-ي]+(?:\s+[ء-ي]+){0,4}?)"
    r"(?=[\s،,.]+(?:يقول|يحدث|يخبر|قال|عن|ان)(?![ء-ي])|\s*[،,.])"
    r"|^[\s،,]*ان\s+(?P<told>(?!رسول|النبي|رجل)[ء-ي]+(?:\s+[ء-ي]+){0,4}?)[\s،,]+(?:اخبرته|اخبره|اخبرها|اخبرهم|حدثته|حدثه"
    r"|حدثها|حدثهم|اخبرتها|اخبرتهم|حدثتها|حدثتهم)(?![ء-ي])")
# Words that make a surface a formula or an aside rather than a name (the audit's high-confidence class).
FORMULA_HIGH = frozenset(["بهذا", "الاسناد", "باسناده", "كلاهما", "احدهما", "مثله", "نحوه", "بمثل", "بنحو", "بمعني",
                          "بمعناه", "معناه", "اللفظ", "لفظ", "كلهم", "فذكر", "الحديث", "حديثه", "تابعه", "جاءت",
                          "فنهاه", "هذا", "انما", "كل", "هؤلاء", "الاخران", "الاخرون", "الباقون"])
# A transmission verb inside a surface is a link: the name after it is the next narrator («الشعبي» in «X سمعا الشعبي»).
LINK_VERB = frozenset(["سمعا", "سمعوا", "سمع", "سمعت", "حدثتني", "حدثني", "حدثنا", "حدثتنا", "اخبرني", "اخبرنا", "اخبرتني",
                       "اخبرته", "اخبره", "اخبراه", "اخبروه", "حدثه", "حدثته", "حدثاه", "انبانا", "انباني",
                       "فاخبرني", "فحدثني", "فاخبرنا", "فحدثنا"])
# «أبي ومحمد بن بشر» stored as one surface: two co-transmitters (the waw-led word opens a name).
FUSED_NAME_START = frozenset(["محمد", "احمد", "علي", "عبد", "عبيد", "ابي", "ابو", "ابن", "يحيي", "اسحاق", "ابراهيم", "سفيان",
                              "شعبة", "حماد", "عمرو", "عمر", "زهير", "قتيبة", "هشام", "سعيد", "يزيد", "وكيع", "حجاج", "الليث"])
# Words that frame a name without being part of it («أنهما», «يحدث», «يخبر», «زوج النبي»).
NAME_FRAME = frozenset(["انه", "انها", "انهما", "انهم", "قال", "قالا", "قالت", "قالوا", "يقول", "يقولان", "يحدث", "يحدثان",
                        "يحدثه", "يحدثون", "يخبر", "يخبره", "يخبران", "يذكر", "يرفعه", "زوج", "لقد", "قد"])
# A word that never stands inside a name split off a verb (a clause, not a narrator).
NAME_STOP = frozenset(["من", "في", "الي", "ما", "لا", "كان", "كانت", "هي", "ذلك", "له", "لها", "عنه", "عنها", "رسول", "النبي"])
# A person named by a relation to the Prophet («ربيبة النبي», «مولى النبي»): a narrator, not the Prophet.
RELATION_TO_PROPHET = re.compile(r"(?:ربيبه|ربيبة|مولي|مولاة|مولاه|خادم|ابنة|بنت)\s+(?:النبي|رسول\s+الله)$")


def sunni_norm(value: str) -> str:
    """The audit lane's `norm`: marks out, alef and final ya folded, direction marks dropped, spaces collapsed."""
    return sunni_norm_with_map(value)[0]


def sunni_norm_with_map(value: str) -> tuple[str, list[int]]:
    """`sunni_norm` and, per output letter, its index in the input (to cut the original text where the normal one matched)."""
    out: list[str] = []
    where: list[int] = []
    for index, char in enumerate(value or ""):
        if SUNNI_DIACRITICS.match(char) or char in SUNNI_INVISIBLE:
            continue
        if char.isspace():
            if out and out[-1] != " ":
                out.append(" ")
                where.append(index)
            continue
        out.append("ا" if char in "أإآٱ" else "ي" if char == "ى" else char)
        where.append(index)
    if out and out[-1] == " ":
        out.pop()
        where.pop()
    return "".join(out), where


def name_key(surface: str) -> str:
    """Comparison key of a name: «ابن» as «بن», ta marbuta folded, the kunya's case endings («أبا/أبي/أبو») as «ابو»."""
    words = ["بن" if word == "ابن" else word for word in sunni_norm(surface).replace("ة", "ه").split()]
    if words and words[0] in ("ابا", "ابي"):
        words[0] = "ابو"
    if len(words) == 1 and words[0].startswith("ال") and len(words[0]) > 4:
        words[0] = words[0][2:]          # «الليث» = «ليث»: one bare name with or without the article
    return " ".join(words)


def same_name(a: str, b: str) -> bool:
    """One written name, allowing the accusative alif («جابرا» = «جابر»)."""
    a, b = name_key(a), name_key(b)
    return bool(a) and (a == b or a == b + "ا" or b == a + "ا")


def locate(normal: str, surface: str, cursor: int = 0) -> tuple[int, int] | None:
    """The first span of a stored surface in the normalized text at or after `cursor` (a leading «و/ف», an accusative alif)."""
    body = re.escape(sunni_norm(surface)).replace("\\ ", "[\\s،,]+")
    if not body:
        return None
    hit = re.compile(rf"(?<![ء-ي])(?:و|ف)?{body}ا?(?![ء-ي])").search(normal, cursor)
    return (hit.start(), hit.end()) if hit else None


def locate_all(normal: str, surfaces: Sequence[str]) -> list[tuple[int, int] | None]:
    """Each surface located in order, each search starting after the previous hit."""
    cursor, spans = 0, []
    for surface in surfaces:
        span = locate(normal, surface, cursor)
        spans.append(span)
        if span:
            cursor = span[1]
    return spans


def ordered_spans(normal: str, chains: Sequence[Sequence[str]]) -> list[list[tuple[int, int] | None]]:
    """Each chain located in the text, chains taken in their stored (text) order: a chain's first name is searched from the
    previous chain's first name on, and past it unless the two chains are co-transmitter variants of one occurrence
    (same head, their next names waw-joined). A repeated head («قتيبة بن سعيد» twice, k6:9600) is found where it stands."""
    out: list[list[tuple[int, int] | None]] = []
    floor = 0
    previous: Sequence[str] | None = None
    for chain in chains:
        if not chain:
            out.append([])
            continue
        start = floor
        if previous and out and out[-1] and out[-1][0]:
            head = out[-1][0]
            same_occurrence = same_name(chain[0], previous[0]) and (
                len(chain) < 2 or len(previous) < 2 or same_name(chain[1], previous[1]) or _waw_joined(normal, previous, out[-1], chain[1]))
            start = head[0] if same_occurrence or not same_name(chain[0], previous[0]) else head[1]
        first = locate(normal, chain[0], start) or locate(normal, chain[0], floor)
        spans = [first] + (locate_all_from(normal, chain[1:], first[1]) if first else [None] * (len(chain) - 1))
        out.append(spans)
        if first:
            floor = first[0]
        previous = chain
    return out


def _waw_joined(normal: str, previous: Sequence[str], spans, name: str) -> bool:
    """`name` stands right after the previous chain's second name, joined by a waw (one level, two co-transmitters)."""
    if len(spans) < 2 or not spans[1]:
        return False
    hit = locate(normal, name, spans[1][1])
    return bool(hit) and bool(WAW_GAP.match(normal[spans[1][1]:hit[0]]))


def locate_all_from(normal: str, surfaces: Sequence[str], cursor: int) -> list[tuple[int, int] | None]:
    """`locate_all` from a given offset."""
    spans = []
    for surface in surfaces:
        span = locate(normal, surface, cursor)
        spans.append(span)
        if span:
            cursor = span[1]
    return spans


def surface_gaps(text: str, surfaces: Sequence[str]) -> list[str | None]:
    """The text between stored neighbours (None where one of them is not found in order)."""
    normal = sunni_norm(text)
    spans = locate_all(normal, surfaces)
    return [normal[a[1]:b[0]] if a and b and b[0] >= a[1] else None for a, b in zip(spans, spans[1:])]


def skip_asides(rest: str) -> str:
    """The text after a name with leading punctuation and asides («وهو ابن زيد», «واللفظ له») removed."""
    while True:
        match = LEADING_ASIDE.match(rest)
        if not match or not match.group(0):
            return rest
        rest = rest[match.end():]


def split_link_verbs(surface: str) -> list[str]:
    """A surface split at its transmission verbs («عبد الملك بن سعيد سمعا الشعبي يخبر» -> the two names; «عروة أن عائشة
    أخبرته» likewise); frame words around a name are dropped, a piece that is not a name is dropped."""
    words = surface.split()
    folded = [sunni_norm(word) for word in words]
    if not any(word in LINK_VERB for word in folded):
        return [surface]
    pieces: list[list[str]] = [[]]
    for word, key in zip(words, folded):
        if key in LINK_VERB:
            pieces.append([])
        else:
            pieces[-1].append(word)
    names = []
    for piece in pieces:
        keys = [sunni_norm(word) for word in piece]
        # «عروة بن الزبير أن عائشة»: a «أن» between two names is a link too.
        cut = next((k for k in range(1, len(keys) - 1) if keys[k] == "ان"), None)
        for part in ([piece[:cut], piece[cut + 1:]] if cut is not None else [piece]):
            name = frame_trimmed(part)
            if name:
                names.append(name)
    return names


def frame_trimmed(words: list[str]) -> str | None:
    """A run of words as a name: frame words off its start, cut at the first frame or formula word; None if not a name."""
    keys = [sunni_norm(word) for word in words]
    while keys and (keys[0] in NAME_FRAME or keys[0] == "ان"):
        words, keys = words[1:], keys[1:]
    stop = next((k for k, key in enumerate(keys) if key in NAME_FRAME or key in FORMULA_HIGH
                 or (key == "يزيد" and k + 1 < len(keys) and keys[k + 1] == "احدهما")), len(keys))
    words, keys = words[:stop], keys[:stop]
    name = " ".join(words).strip(" ،,.:-")
    relation = RELATION_TO_PROPHET.search(" ".join(keys))
    stops = [key for key in (keys[:-1] if relation else keys) if key in NAME_STOP]
    if not name or len(keys) > 10 or stops or not re.search("[ء-ي]", name):
        return None
    return name


# «وأنا أسمع» of «قراءة عليه وأنا أسمع» (the compiler heard it read), read as a co-transmitter: never a name.
HEARING_ASIDE = re.compile(r"و?انا\s+اسمع")
# A word that opens a remark on the wording («تقاربا في اللفظ»), never a name.
WORDING_REMARK = frozenset(["تقاربا", "تقاربوا", "واللفظ", "لفظه", "متقارب"])


def formula_trim(surface: str) -> tuple[str | None, bool]:
    """(the name left once formula words are cut, whether the surface had one). None: nothing of a name remains."""
    words = surface.split()
    folded = [sunni_norm(word) for word in words]
    if (folded and folded[0] in WORDING_REMARK) or folded[:2] in (["في", "حديث"], ["في", "رواية"]) or HEARING_ASIDE.fullmatch(
            " ".join(folded)):
        return None, True
    hits = [index for index, word in enumerate(folded) if word in FORMULA_HIGH]
    if not hits:
        return surface, False
    if hits[0] == 0:
        return None, True
    kept = " ".join(words[:hits[0]]).strip(" ،,.:")
    kept = re.sub(r"\s+(?:في|عن|و|قال|يعني|-)$", "", kept).strip(" ،,.:-")
    return (kept or None), True


# A clause after a name (round 3, re-check pattern 3: «زرارة بن أوفى يحدث», «الحارث بن مسكين قراءة عليه», «عائشة أنها»,
# «الزهري أما ابن منصور فقال»): the name ends before the first word that never stands in one. A surface that opens with
# one is no name, except «قال X» / «قالت X» (X's own attribution: «وقال زهير عن سعيد», «قالت زينب»). «مرة» is also a name («مرة الهمداني», «عمرو بن
# مرة»): it cuts only after a name word.
CLAUSE_WORD = frozenset(["يحدث", "يحدثه", "يحدثان", "يحدثون", "يخبر", "يخبره", "يخبران", "يقول", "يقولان", "قال", "قالت",
                         "قالا", "قالوا", "فقال", "وقال", "انه", "انها", "انهما", "انهم", "قراءة", "اما", "واما", "كنت",
                         "كانت", "كان", "اذا", "في", "وفي", "يرفعه", "رفعه", "مرفوعا", "موقوفا", "يذكر", "نحو", "لم",
                         "ثم", "حتى", "ذلك", "زاد", "وزاد", "باب"])
NAME_CONNECTOR = frozenset(["بن", "ابن", "ابي", "ابو", "ابا", "ام", "عبد", "بنت", "و"])


def clause_trim(surface: str) -> str | None:
    """The name before a trailing clause, or None when the surface opens with one (see CLAUSE_WORD)."""
    words = surface.strip(" -،,").split()
    keys = [sunni_norm(word) for word in words]
    if keys and keys[0] in ("قال", "وقال", "فقال", "قالت", "وقالت") and len(keys) > 1:
        words, keys = words[1:], keys[1:]
    cut = next((k for k, key in enumerate(keys) if key in CLAUSE_WORD
                or (key == "مرة" and k > 0 and keys[k - 1] not in NAME_CONNECTOR)), None)
    if cut is None:
        return " ".join(words) or None
    if cut == 0:
        return None
    if keys[cut - 1] in NAME_CONNECTOR:
        return surface          # the cut would fall inside a name: left as written
    return " ".join(words[:cut]).strip(" -،,") or None


@dataclass(frozen=True)
class SunniMention:
    surface: str
    origin: tuple[int, int] | None        # (branch, position) in the bundle's chain, for the source index and claims


@dataclass(frozen=True)
class SunniChain:
    mentions: list[SunniMention]
    split_from: int | None = None          # the bundle branch a seam split this route from


class ReportText:
    """A report's text, normalized once, with the map back to the original letters."""

    def __init__(self, text: str):
        self.original = text
        self.normal, self.where = sunni_norm_with_map(text)

    def original_slice(self, start: int, end: int) -> str:
        return self.original[self.where[start]:self.where[end - 1] + 1]

    def without(self, start: int, end: int) -> str:
        """The original text with the normal span [start, end) removed."""
        return self.original[:self.where[start]] + " " + self.original[self.where[end - 1] + 1:]

    def after(self, span: tuple[int, int] | None) -> str | None:
        return skip_asides(self.normal[span[1]:]) if span else None


def prefix_extension(old: list[str], found: list[list[str]]) -> list[str] | None:
    """The names a re-extraction adds after `old`, when a re-extracted branch starts with exactly `old` (its last name may
    now be shorter: «شعبة كلاهما» -> «شعبة»)."""
    for branch in found:
        if len(branch) <= len(old) or branch[:len(old) - 1] != old[:-1]:
            continue
        last_old, last_new = sunni_norm(old[-1]).split(), sunni_norm(branch[len(old) - 1]).split()
        if last_new and last_old[:len(last_new)] == last_new:
            return branch[len(old):]
    return None


def attributed_to(name: str, surface: str) -> bool:
    """«قال ابن المثنى» names «محمد بن المثنى»; «قال أبو بكر» names «أبو بكر بن أبي شيبة»."""
    a, b = name_key(name).split(), name_key(surface).split()
    if not a or not b:
        return False
    return a == b[:len(a)] or (len(a) >= 2 and a[-2] == "بن" and len(b) >= 2 and b[-2:] == a[-2:])


def extend_stopped_branches(report: ReportText, branches: list[list[str]], counts: Counter,
                            extract=extract_isnad_branches) -> list[list[tuple[str, tuple[int, int] | None]]]:
    """Bundle branches as (surface, origin = bundle position), plus the names the extractor stopped short of: after a wording
    attribution («قال ابن المثنى حدثنا»), after a convergence word («شعبة، كلاهما عن ...»), and a name the text gives
    through a verb after the last stored one («، أن عائشة، أخبرته»). Added names have no origin."""
    out = [[(surface, (index, position)) for position, surface in enumerate(branch)] for index, branch in enumerate(branches)]
    every = [surface for branch in branches for surface in branch]
    removals: dict[tuple[int, int], str] = {}
    for index, branch in enumerate(branches):
        if not branch:
            continue
        spans = locate_all(report.normal, [formula_trim(surface)[0] or surface for surface in branch])
        if spans[-1] is None:
            continue
        rest = report.after(spans[-1])
        at = len(report.normal) - len(rest)
        attribution = WORDING_ATTRIBUTION.match(rest)
        if attribution and any(attributed_to(attribution.group("name"), surface) for surface in every):
            removals[(at, at + attribution.end())] = "wording_attribution"
            continue
        convergence = CONVERGENCE_LINK.match(rest)
        if convergence:
            reference = CONVERGENCE_THEN_REFERENCE.match(rest[convergence.end():])
            if reference:
                offset = at + convergence.end()
                name = frame_trimmed(report.original_slice(offset + reference.start("name"), offset + reference.end("name")).split())
                if name:
                    counts["sunni_extended_after_convergence_word_before_reference"] += 1
                    out[index].append((name, None))
                continue
            removals[(at, at + convergence.end())] = "convergence_word"
            continue
        # «عن عطاء بن يسار، أن زيد بن خالد أخبره ...»: followed link by link (at most three).
        last = branch[-1]
        for _ in range(3):
            link = TEXT_LINK_AFTER.match(rest)
            if not link:
                break
            group = "heard" if link.group("heard") else "told"
            name = frame_trimmed(report.original_slice(at + link.start(group), at + link.end(group)).split())
            if not name or same_name(name, last):
                break
            counts["sunni_name_after_link_verb_in_text"] += 1
            out[index].append((name, None))
            last = name
            consumed = link.end(group)
            rest = skip_asides(rest[consumed:])
            at = len(report.normal) - len(rest)
            rest = re.sub(r"^(?:اخبرته|اخبره|اخبرها|اخبرهم|حدثته|حدثه|حدثها|حدثهم|اخبرتها|اخبرتهم|حدثتها|حدثتهم|يقول|يحدث|يخبر)"
                          r"(?![ء-ي])", "", rest)
            at = len(report.normal) - len(rest)
    for (start, end), kind in sorted(removals.items()):
        found = extract(report.without(start, end))
        for index, branch in enumerate(branches):
            if len(out[index]) != len(branch) or not branch:
                continue
            tail = prefix_extension(branch, found)
            if tail:
                counts[f"sunni_extended_after_{kind}"] += 1
                out[index] = out[index] + [(surface, None) for surface in tail]
    return out


def split_fused_names(surface: str) -> list[str]:
    """«أبي ومحمد بن بشر» -> «أبي», «محمد بن بشر» (they fall on one level: only a waw stands between them in the text)."""
    words = surface.split()
    keys = [sunni_norm(word) for word in words]
    for k in range(1, len(words)):
        right = keys[k][1:] if keys[k].startswith("و") and len(keys[k]) > 2 else None
        if right in FUSED_NAME_START and keys[k - 1] not in ("بن", "ابن", "عبد", "بنت", "ام"):
            return [" ".join(words[:k]), " ".join([words[k][1:]] + words[k + 1:])]
    return [surface]


def clean_branch(branch: list[tuple[str, tuple[int, int] | None]], counts: Counter) -> list[SunniMention | None]:
    """Each stored surface as names: link verbs split it, formula words are cut. None marks a surface with no name left."""
    out: list[SunniMention | None] = []
    for position, (surface, origin) in enumerate(branch):
        names = [part for name in split_link_verbs(surface) for part in split_fused_names(name)]
        if names != [surface]:
            counts["sunni_link_verb_surfaces_split"] += 1
        kept = []
        for name in names:
            trimmed, had = formula_trim(name)
            if had:
                counts["formula_surfaces_trimmed" if trimmed else "formula_surfaces_retired"] += 1
            if trimmed:
                cleaned = clause_trim(trimmed)
                if cleaned != trimmed:
                    counts["clause_surfaces_trimmed" if cleaned else "clause_surfaces_retired"] += 1
                if cleaned:
                    kept.append(cleaned)
        if not kept:
            out.append(None)
            continue
        following = branch[position + 1][0] if position + 1 < len(branch) else None
        for index, name in enumerate(kept):
            # A name split off a surface that the bundle already stores next is not repeated («سمعا جابرا» > «جابر»).
            if index and following is not None and same_name(name, following):
                counts["sunni_link_verb_name_already_stored"] += 1
                continue
            out.append(SunniMention(name, origin if index == 0 else None))
            counts["sunni_link_verb_names_added"] += 1 if index else 0
    return out


def levels_of(report: ReportText, mentions: list[SunniMention], spans) -> list[list[SunniMention]]:
    """Mentions grouped into transmission levels (waw-joined neighbours share one), given each mention's span."""
    levels: list[list[SunniMention]] = []
    for position, mention in enumerate(mentions):
        a, b = (spans[position - 1], spans[position]) if position else (None, None)
        if a and b and b[0] >= a[1] and WAW_GAP.match(report.normal[a[1]:b[0]]) and levels:
            levels[-1].append(mention)
        else:
            levels.append([mention])
    return levels


@dataclass(frozen=True)
class RouteBreak:
    """A route break inside one stored chain, before mention `index`."""
    index: int
    kind: str              # 'h' (a standalone «ح», in the text or at the end of a stored surface) | 'verb' (a waw-led verb)
    earlier_ends: bool     # the earlier route's last name stands right before the break (only asides between)
    later_is_head: bool    # only a verb stands between the break and the next stored name


TRAILING_H = re.compile(r"\s+ح$")


def strip_trailing_h(mentions: list[SunniMention]) -> tuple[list[SunniMention], set[int]]:
    """«ابن شهاب ح» stored as one surface: the name, and a break before the next mention (its index in the result)."""
    out: list[SunniMention] = []
    after: set[int] = set()
    for mention in mentions:
        if len(out) in after and same_name(mention.surface, out[-1].surface):
            continue          # «ابن جريج ح» then «ابن جريج»: one name, the second route reaches him too
        if TRAILING_H.search(sunni_norm(mention.surface)) and len(mention.surface.split()) > 1:
            out.append(SunniMention(TRAILING_H.sub("", mention.surface.rstrip(" ،,.")).strip(" ،,.-"), mention.origin))
            after.add(len(out))
        else:
            out.append(mention)
    return out, {index for index in after if index < len(out)}


def route_breaks(report: ReportText, mentions: list[SunniMention], spans, h_after: set[int]) -> list[RouteBreak]:
    """Every break between stored neighbours, with where it stands relative to them."""
    out = []
    for index in range(1, len(mentions)):
        a, b = spans[index - 1], spans[index]
        if not a or not b or b[0] < a[1]:
            continue
        gap = report.normal[a[1]:b[0]]
        breaks = list(TAHWIL_H.finditer(gap))
        if index in h_after and not breaks:
            out.append(RouteBreak(index, "h", True, bool(ROUTE_HEAD_GAP.match(gap))))
        elif breaks:
            before, after = gap[:breaks[0].start()], gap[breaks[-1].end():]
            out.append(RouteBreak(index, "h", not skip_asides(before).strip(), bool(ROUTE_HEAD_GAP.match(after))))
        else:
            verbs = list(NEW_ROUTE_VERB.finditer(gap))
            if verbs and re.match(r"^[\s.،,:\-]*$", gap[verbs[-1].end():]):
                out.append(RouteBreak(index, "verb", not skip_asides(gap[:verbs[0].start()]).strip(), True))
    return out


# One man under two customary names, for convergence only (never an identity): Muhammad b. Muslim b. Shihab al-Zuhri.
SAME_MAN = [frozenset(["الزهري", "ابن شهاب", "محمد بن مسلم بن شهاب", "محمد بن مسلم الزهري", "ابن شهاب الزهري"])]


SAME_MAN_KEYS = [frozenset(name_key(name) for name in group) for group in SAME_MAN]


def converges(a: str, b: str) -> bool:
    """Two surfaces a tahwil may converge on: one written name, or the two names of al-Zuhri."""
    if same_name(a, b):
        return True
    a_key, b_key = name_key(a), name_key(b)
    return any(a_key in group_keys and b_key in group_keys for group_keys in SAME_MAN_KEYS)


@dataclass
class Candidate:
    """A route of the report as levels, with each mention's span, offered as a possible shared tail."""
    levels: list[list[SunniMention]]
    spans: dict[int, tuple[int, int] | None]

    def after(self, end: int) -> list[list[SunniMention]]:
        """Its levels the text gives after `end`."""
        for k, level in enumerate(self.levels):
            if any((self.spans.get(id(m)) or (-1, -1))[0] > end for m in level):
                return self.levels[k:]
        return []


def shared_tail(report: ReportText, route: list[list[SunniMention]], end: tuple[int, int] | None, candidates: list[Candidate],
                allow_convergence_word: bool) -> list[list[SunniMention]] | None:
    """What a route that stops at a break continues with; None when no tested rule establishes it.
    (a) a later route repeats one of this route's last two names (suffix alignment, as the extractor stitches tahwil);
    (b) after a «ح», the first convergence word («كلاهما/كلهم/جميعا») directly after a later route's name."""
    if end is None:
        return None
    later = [candidate.after(end[1]) for candidate in candidates]
    for back in (0, 1):
        if back >= len(route):
            break
        names = route[len(route) - 1 - back]
        for candidate, other in zip(candidates, later):
            for k, level in enumerate(other):
                # A route's head is never where another route converges (k6:11239: «زهير بن حرب» heads two routes).
                if k == 0 and len(other) == len(candidate.levels):
                    continue
                if any(converges(m.surface, n.surface) for m in level for n in names):
                    position = k + 1 + back
                    if position < len(other):
                        return other[position:]
    if not allow_convergence_word:
        return None
    word = CONVERGENCE_WORD.search(report.normal, end[1])
    if not word or PROPHET_IN_TEXT.search(report.normal[end[1]:word.start()]):
        return None
    for candidate, other in zip(candidates, later):
        for k, level in enumerate(other[:-1]):
            for mention in level:
                span = candidate.spans.get(id(mention))
                if span and span[1] <= word.start() and not skip_asides(report.normal[span[1]:word.start()]).strip():
                    return other[k + 1:]
    return None


def contained(levels: list[list[SunniMention]], routes: list[list[list[SunniMention]]], at_start: bool) -> bool:
    """`levels` is the start (or a run ending at the end) of another route, name by name."""
    names = [level[0].surface for level in levels]
    for other in routes:
        surfaces = [level[0].surface for level in other]
        if other is levels or len(surfaces) <= len(names):
            continue
        window = surfaces[:len(names)] if at_start else surfaces[-len(names):]
        if all(same_name(a, b) for a, b in zip(names, window)):
            return True
    return False


@dataclass
class PendingBranch:
    """A stored chain with route breaks inside it, resolved once every route of the report is known."""
    index: int
    levels: list[list[SunniMention]]
    pieces: list[list[list[SunniMention]]]
    breaks: list[RouteBreak]          # breaks[k] separates pieces[k] and pieces[k + 1]
    spans: dict[int, tuple[int, int] | None]


def build_sunni_chains(text: str, branches: list[list[str]], counts: Counter, extract=extract_isnad_branches) -> list[SunniChain]:
    """Re-cut one Sunni report (pg_export/AGENTS.md §Sunni chains, rounds 2-3)."""
    report = ReportText(text)
    extended, merged = merge_ghayr_wahid(extend_stopped_branches(report, branches, counts, extract), lambda item: item[0])
    counts["ghayr_wahid_merged"] += merged
    cleaned = [clean_branch(branch, counts) for branch in extended]
    settled: list[tuple[int, list[list[SunniMention]], bool]] = []      # (bundle branch, levels, split from it)
    pending: list[PendingBranch] = []
    kept: list[tuple[int, list[SunniMention], set[int]]] = []
    span_of: dict[int, tuple[int, int] | None] = {}
    for branch_index, branch in enumerate(cleaned):
        empty = [p for p, m in enumerate(branch) if m is None]
        # A position with no name left was an aside read as a co-transmitter («اللفظ لعمرو») when a sibling branch
        # differs from this one only there: this branch is the artefact. Otherwise only the position goes (k6:21409).
        # The sibling must hold a name where this one has none (two branches emptied at one position are both kept).
        if empty and any(j != branch_index and len(branches[j]) == len(branches[branch_index])
                         and len(cleaned[j]) == len(branch) and any(cleaned[j][p] is not None for p in empty) and all(
                branches[j][p] == branches[branch_index][p] for p in range(len(branches[j])) if p not in empty)
                for j in range(len(branches))):
            counts["aside_branches_dropped"] += 1
            continue
        mentions, h_after = strip_trailing_h([m for m in branch if m is not None])
        if mentions:
            kept.append((branch_index, mentions, h_after))
    all_spans = ordered_spans(report.normal, [[m.surface for m in mentions] for _, mentions, _ in kept])
    for (branch_index, mentions, h_after), spans in zip(kept, all_spans):
        levels = levels_of(report, mentions, spans)
        counts["co_transmitters_put_on_one_level"] += len(mentions) - len(levels)
        span_by_id = {id(m): s for m, s in zip(mentions, spans)}
        span_of.update(span_by_id)
        breaks = route_breaks(report, mentions, spans, h_after)
        level_of = {id(m): i for i, level in enumerate(levels) for m in level}
        by_level = {}
        for item in breaks:
            if level_of[id(mentions[item.index])] > 0:
                by_level.setdefault(level_of[id(mentions[item.index])], item)
        if not by_level:
            settled.append((branch_index, levels, False))
            continue
        bounds = [0] + sorted(by_level) + [len(levels)]
        pending.append(PendingBranch(branch_index, levels, [levels[a:b] for a, b in zip(bounds, bounds[1:])],
                                     [by_level[k] for k in sorted(by_level)], span_by_id))
    candidates = [Candidate(levels, {id(m): span_of.get(id(m)) for level in levels for m in level}) for _, levels, _ in settled]
    candidates += [Candidate(piece, item.spans) for item in pending for piece in item.pieces]
    every = [candidate.levels for candidate in candidates]
    for item in pending:
        routes = resolve_pending(report, item, candidates, every, counts)
        if routes is None:
            counts["seam_not_split:no_shared_tail"] += 1
            settled.append((item.index, item.levels, False))
        else:
            counts["seam_chains_split"] += 1
            counts["seam_routes_made"] += len(routes)
            settled.extend((item.index, route, True) for route in routes)
    out: list[SunniChain] = []
    for branch_index, route, split in sorted(settled, key=lambda entry: entry[0]):
        paths: list[list[SunniMention]] = [[]]
        for level in route:
            if len(paths) * len(level) > 64:
                level = level[:1]
            paths = [path + [mention] for path in paths for mention in level]
        for path in paths:
            if path and all([m.surface for m in path] != [m.surface for m in chain.mentions] for chain in out):
                out.append(SunniChain(path, branch_index if split else None))
    return complete_short_routes(report, out, counts)


def resolve_pending(report: ReportText, item: PendingBranch, candidates: list[Candidate], every, counts: Counter):
    """The routes a stored chain with breaks becomes, or None to leave it whole (no tested rule settles every piece).
    Each earlier piece that ends at its break takes its shared tail; one that does not, or a later piece that does not start
    at a route head, is dropped only when another route of the report already holds it."""
    routes = []
    for number, piece in enumerate(item.pieces):
        before = item.breaks[number - 1] if number else None
        after = item.breaks[number] if number < len(item.breaks) else None
        if before is not None and not before.later_is_head:
            if contained(piece, every, at_start=False):
                counts["seam_piece_dropped:continues_another_route"] += 1
                continue
            return None
        if after is None:
            routes.append(piece)
            continue
        if not after.earlier_ends:
            if contained(piece, every, at_start=True):
                counts["seam_piece_dropped:start_of_another_route"] += 1
                continue
            return None
        others = [candidate for candidate in candidates if candidate.levels is not piece]
        tail = shared_tail(report, piece, item.spans.get(id(piece[-1][-1])), others, after.kind == "h")
        if tail is None:
            return None
        routes.append(piece + tail)
    return routes or None


def complete_short_routes(report: ReportText, chains: list[SunniChain], counts: Counter) -> list[SunniChain]:
    """A route that stops at a «ح» continues along the route it converges with (rules (a) and (b) of `shared_tail`)."""
    for _ in range(3):
        changed = False
        spans = ordered_spans(report.normal, [[m.surface for m in chain.mentions] for chain in chains])
        candidates = [Candidate([[m] for m in chain.mentions], {id(m): s for m, s in zip(chain.mentions, spans[k])})
                      for k, chain in enumerate(chains)]
        for index, chain in enumerate(chains):
            end = spans[index][-1]
            rest = report.after(end)
            if rest is None or not re.match(r"^ح(?![ء-ي])", rest):
                continue
            others = [candidate for k, candidate in enumerate(candidates) if k != index]
            tail = shared_tail(report, [[m] for m in chain.mentions], end, others, True)
            if tail:
                counts["short_routes_given_shared_tail"] += 1
                chains[index] = SunniChain(chain.mentions + [level[0] for level in tail], chain.split_from)
                changed = True
        if not changed:
            break
    share_co_transmitter_continuations(report, chains, counts)
    # A narrator never transmits from himself: one written name twice in a row is one mention (k6:18840 «ابن السرح»).
    for index, chain in enumerate(chains):
        kept = [m for k, m in enumerate(chain.mentions) if not (k and same_name(m.surface, chain.mentions[k - 1].surface)
                                                                and name_key(m.surface) not in RELATION_WORDS)]
        if len(kept) < len(chain.mentions):
            counts["adjacent_repeat_collapsed"] += 1
            chains[index] = SunniChain(kept, chain.split_from)
    unique: list[SunniChain] = []
    for chain in chains:
        if not any(len(chain.mentions) == len(kept.mentions) and all(
                same_name(a.surface, b.surface) for a, b in zip(chain.mentions, kept.mentions)) for kept in unique):
            unique.append(chain)
    return unique


# A relation can repeat («عن أبيه عن أبيه» walks up a family line); never collapsed.
RELATION_WORDS = frozenset(["ابيه", "ابي", "ابوه", "جده", "جدي", "امه", "امي", "عمه", "عمي", "خاله", "خالي", "اخيه", "اخي"])


def share_co_transmitter_continuations(report: ReportText, chains: list[SunniChain], counts: Counter) -> None:
    """Co-transmitters joined by a waw at one position share what follows them («مطرف بن طريف، وعبد الملك بن سعيد، سمعا
    الشعبي»): a route that stops there, or skips a name its partner carries split off a verb, takes the partner's continuation."""
    spans = ordered_spans(report.normal, [[m.surface for m in chain.mentions] for chain in chains])
    for index, chain in enumerate(chains):
        for other_index, other in enumerate(chains):
            if other is chain:
                continue
            p = next((k for k, (a, b) in enumerate(zip(chain.mentions, other.mentions)) if a.surface != b.surface), None)
            if p is None or p >= len(other.mentions) - 1 or p >= len(chain.mentions):
                continue
            # Each name where its own chain stands in the text (k6:14609: «أبي» of «حدثنا أبي ومحمد بن بشر», never the
            # «أبي» of «أبو بكر بن أبي شيبة» earlier on).
            first = spans[index][p] if p < len(spans[index]) else None
            second = spans[other_index][p] if p < len(spans[other_index]) else None
            if not first or not second:
                continue
            a, b = sorted([first, second])
            if b[0] < a[1] or not WAW_GAP.match(report.normal[a[1]:b[0]]):
                continue
            mine, theirs = chain.mentions[p + 1:], other.mentions[p + 1:]
            added = [m for m in theirs if m.origin is None]
            if not mine or (added and is_subsequence([m.surface for m in mine], [m.surface for m in theirs])):
                counts["co_transmitter_continuation_shared"] += 1
                chains[index] = chain = SunniChain(chain.mentions[:p + 1] + list(theirs), chain.split_from)


def is_subsequence(short: list[str], long: list[str]) -> bool:
    """`short` is `long` with names left out, in order."""
    iterator = iter(long)
    return len(short) < len(long) and all(any(same_name(name, candidate) for candidate in iterator) for name in short)


EDITION_PATH = Path(__file__).resolve().parent / "edition_identifications.json"


def load_edition_identifications(path: Path = EDITION_PATH) -> dict[tuple[str, tuple[int, int]], dict]:
    """{(hadith id, (bundle branch, position)): identification} from edition_identifications.json."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return {(item["hadith_id"], (item["bundle_branch"], item["bundle_position"])): item for item in data["identifications"]}


MISSING_LINK_YEARS = 120


def missing_link_after(identities: Sequence[str | None], deaths: dict[str, int | None], surfaces: Sequence[str]) -> int | None:
    """The position after which a link is missing (the Sunni audit's `missing_link`): the last name is a person who died more
    than 120 years before the fully named student beside him. Flagged on the chain; no name is invented."""
    if len(identities) < 2 or not identities[-1] or not identities[-2] or len(surfaces[-2].split()) < 2:
        return None
    teacher, student = deaths.get(identities[-1]), deaths.get(identities[-2])
    if teacher and student and student - teacher > MISSING_LINK_YEARS:
        return len(identities) - 2
    return None
