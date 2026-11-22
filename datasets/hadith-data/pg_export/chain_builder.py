"""Chain cutting for the OpenITI works (al-Rabi, Musnad Zayd, Sahifat al-Rida); see pg_export/AGENTS.md §Chain builder.

Pure and standard library apart from the canonical extractor, which is reused unchanged (Sunni output cannot move).
One definition of the chain span: the parser's `sanad_ar`. A low-confidence split has no own chain; a continuation
carries its parent's mentions, marked inherited; the work's compiler is its attribution, never a mention.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

from extract_isnad_unified import extract_isnad_branches

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


def continuation_own_names(report: OpenitiReport) -> tuple[list[BuiltMention], str]:
    """Names a continuation writes after its opener, and how they were read."""
    if report.split_confidence == "high" and report.sanad_ar is not None:
        text, how = report.sanad_ar, "sanad"
    else:
        # Low-confidence split: the words after the opener and its «قال:», up to the next colon or 80 letters; they
        # can only shorten the parent's chain, never extend it.
        text, how = report.text_ar[:240], "head"
    opener = OPENER.match(text) or NAMED_ROUTE.match(text)
    rest = text[opener.end():] if opener else text
    rest = re.sub(rf"^\s*(?:قال\s*[:.]?\s*)", "", rest)
    if how == "head":
        rest = re.split(r"[:«]", rest[:80], maxsplit=1)[0]
    if re.match(rf"^\s*(?:عن|عنه){END}", rest) and not re.match(rf"^\s*عن\s+(?!النبي|رسول)", rest):
        rest = ""
    if re.match(rf"^\s*(?:قال\s+)?(?:رسول\s+الله|النبيء?|النبي){END}", rest) or re.match(rf"^\s*عنه{END}", rest):
        rest = ""
    branches = extract_names("عن " + rest) if rest.strip() else []
    return (branches[0] if branches else []), how


def inherit(report: OpenitiReport, parent: list[list[BuiltMention]], parent_id: str,
            counts: Counter) -> tuple[list[list[BuiltMention]], bool]:
    """The parent's mentions, marked inherited, up to the link the continuation names; then its own links.

    Returns the branches and whether they replace the route for the reports that continue this one («ومن طريق X»).
    """
    own, how = continuation_own_names(report)
    named_route = bool(NAMED_ROUTE.match(report.text_ar)) and not OPENER.match(report.text_ar)
    result = []
    for branch_index, branch in enumerate(parent):
        copied = list(branch)       # a route's mentions already name the written mention they repeat
        cut, own_start = None, None
        for own_index, mention in enumerate(own):
            if mention.link_kind:
                continue
            hits = [p for p, m in enumerate(branch) if m.link_kind is None and names_match(mention.surface, m.surface)]
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
        elif own and named_route:
            counts["inherited:named_route_replaces_last_link"] += 1
            result.append(copied[:-1] + own)
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
            detail = f"{self.opening_record_id}: {written}"
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
