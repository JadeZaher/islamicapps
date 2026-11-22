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


# ─── Imami (Thaqalayn) chains: «جميعا» groups, non-narrators, suspended chains, anonymous gaps ─────────────────────

IMAMI_FOLD = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ی": "ي", "ک": "ك"})
# The previous report's chain, by a pronoun or a formula (taʿliq): a label, never a narrator.
BACK_REFERENCE = re.compile(rf"^(?:و\s?)?(?:عنه|عنهم|عنهما|به|بهذا|بهذه|باسناده|بالاسناد|بالاسانيد){END}")
# «وبهذا الإسناد», directly after a report of the same chapter: the antecedent is mechanically certain.
SAME_ISNAD = re.compile(rf"^(?:و\s?)?(?:بهذا|بهذه)\s+(?:الاسناد|الاسانيد|السند){END}")
VERB_PREFIX = re.compile(rf"^(?:و\s?)?(?:روي|وروي|روى|وروى|قال|وقال|سال|سئل|وسئل|ذكر|في\s+رواية|في\s+خبر){END}\s*")
# What follows a name in the text but is not part of it: a doubt («أو»), «مثله», a Qur'an cue, a reported clause.
IMAMI_TRAILING = re.compile(
    rf"\s+(?:او|أو|مثله|نحوه|زاد\s+فيه|في\s+قوله|في\s+قول\s+الله|انه|أنه|انها|أنها|انهما|قال|يقول|عنه"
    rf"|في\s+(?:ال)?(?:رجل|رجلين|امراة|مراة|متوفي|قوم|عبد|جارية)|رحمة\s+الله|رحمه\s+الله|رضي\s+الله){END}.*$")
# The al-Kafi compiler's own shaykhs (the audit lane's list): a group or a fused name that starts with one starts a route.
KULAYNI_SHAYKH = frozenset(["علي بن ابراهيم", "علي بن ابراهيم بن هاشم", "محمد بن يحيي", "عدة من اصحابنا", "الحسين بن محمد",
                            "الحسين بن محمد الاشعري", "ابو علي الاشعري", "حميد بن زياد", "محمد بن اسماعيل", "احمد بن ادريس"])
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
    rf"|بعض\s+من\s+رواه|رفعه|يرفعه|رجل\s+من\s+\S+|من\s+ذكره)(?:\s+(?:رفعه|يرفعه))?$")
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
    if at < 0 or not re.match(rf"^\s*عن{END}", plain[at + len("جميعا"):]):
        return None
    prefix, tail = plain[:at], original[at + len("جميعا"):]
    cuts, last = [], 0
    for match in re.finditer(r"\s+و\s*(?=[ء-ي])", prefix):
        left, right = prefix[last:match.start()], prefix[match.end():]
        previous = left.split()[-1] if left.split() else ""
        if previous in ("بن", "ابن", "ابي", "ابو", "ام") or not LINK_WORD.search(left) or not LINK_WORD.search(right):
            continue
        cuts.append((match.start(), match.end()))
        last = match.end()
    if not cuts:
        return None
    if re.search(r"\s+و\s*(?=[ء-ي])", prefix[last:]) and not LINK_WORD.search(prefix[last:].rsplit(" و", 1)[-1]):
        return []      # the last group ends in a co-transmitter level («عن صفوان و ابن أبي عمير جميعا»): ambiguous, left as read
    groups, start = [], 0
    for begin, end in cuts:
        groups.append(original[start:begin])
        start = end
    groups.append(original[start:at])
    first_name = re.split(LINK_WORD, groups[0].translate(IMAMI_FOLD), maxsplit=1)[0].strip()
    routes = [groups[0].strip()]
    for group in groups[1:]:
        opening = re.split(LINK_WORD, group.translate(IMAMI_FOLD), maxsplit=1)[0].strip()
        # A group that opens with one of the compiler's shaykhs is a route of its own; otherwise it hangs from the first
        # group's opening name («علي بن إبراهيم عن أبيه و محمد بن عيسى عن يونس»: both are ʿAli b. Ibrahim's shaykhs).
        routes.append(group.strip() if opening in KULAYNI_SHAYKH else f"{first_name} عن {group.strip()}")
    return [route + " " + tail.strip() for route in routes]


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


def clean_imami_mention(surface: str, position: int, after_imam: bool, work: str,
                        counts: Counter) -> tuple[list[BuiltMention], str | None]:
    """One stored surface as zero or more mentions, and the chain's suspension when this opening says so."""
    name = Written(surface)
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
    if tokens.count("بن") < 3 and ((len(tokens) >= 3 and any(token in CLAUSE_WORDS for token in tokens)) or len(tokens) >= 12):
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
    groups = jamian_groups(text_ar)
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
                        and imami_fold(alternatives[1].surface) in KULAYNI_SHAYKH):
                    # «... عن حنان بن سدير و محمد بن يحيى عن ...»: a second isnad starts with the compiler's shaykh.
                    counts["second_isnad_split_at_compiler_shaykh"] += 1
                    out.append(ImamiChain([m for level in levels for m in level[:1]] + [alternatives[0]], suspension))
                    restart = [[alternatives[1]]]
                    levels = restart
                    continue
                levels.append(alternatives)
            if mentions:
                after_imam = bool(IMAM_SURFACE.match(imami_fold(mentions[-1].surface)))
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
    return out


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


# ─── Sunni chains: flattened tahwil seams, formula surfaces, co-transmitters (audit `chain-audit/sunni/`) ───────────

SUNNI_DIACRITICS = re.compile(r"[ً-ْٰـۖ-ۭ]")
# A route break between two stored neighbours: a standalone «ح» or a new waw-led transmission verb (the audit's rule).
TAHWIL_H = re.compile(r"(?:^|\s)ح(?=[\s.،,]|$)")
NEW_ROUTE_VERB = re.compile(r"(?:^|\s)(?:قال\s+)?و(?:اخبرنا|حدثنا|اخبرني|حدثني|انبانا|انباني|سمعت|اخبرتنا|حدثتنا)(?=\s|$)")
# Two neighbours joined only by a waw or a comma: co-transmitters at one level.
WAW_GAP = re.compile(r"^[\s،,]*و?[\s،,]*$")
COMMON_ISM = frozenset(["عبد", "محمد", "احمد", "علي", "عمر", "عمرو", "يحيي", "ابراهيم", "اسماعيل", "سليمان", "سعيد",
                        "عثمان", "خالد", "يزيد", "الحسن", "الحسين", "حسن", "حسين", "موسي", "عيسي", "هشام", "جعفر", "يوسف",
                        "عبيد", "مسلم", "زيد", "سعد", "عبد الله"])
# Words that make a surface a formula, an aside or a verb rather than a name (the audit's high-confidence class).
FORMULA_HIGH = frozenset(["بهذا", "الاسناد", "باسناده", "كلاهما", "احدهما", "مثله", "نحوه", "بمثل", "بنحو", "بمعني",
                          "بمعناه", "معناه", "اللفظ", "لفظ", "كلهم", "سمعا", "فذكر", "الحديث", "حديثه", "تابعه", "جاءت",
                          "فنهاه", "هذا", "حدثتني", "حدثني", "حدثنا", "اخبرني", "اخبرنا", "سمعت"])


def sunni_norm(value: str) -> str:
    """The audit lane's `norm`: marks out, alef and final ya folded, direction marks dropped, spaces collapsed."""
    value = SUNNI_DIACRITICS.sub("", value or "")
    value = re.sub("[أإآٱ]", "ا", value).replace("ى", "ي")
    value = re.sub("[‏‎‫‬]", "", value)
    return re.sub(r"\s+", " ", value).strip()


def surface_gaps(text: str, surfaces: Sequence[str]) -> list[str | None]:
    """Each stored surface found in order in the text; the text between neighbours (None where one is not found)."""
    normal = sunni_norm(text)
    cursor, spans = 0, []
    for surface in surfaces:
        pattern = re.compile(rf"(?<![ء-ي])(?:و|ف)?{re.escape(sunni_norm(surface)).replace(chr(92) + ' ', chr(92) + 's+')}(?![ء-ي])")
        hit = pattern.search(normal, cursor)
        if not hit:
            spans.append(None)
            continue
        spans.append((hit.start(), hit.end()))
        cursor = hit.end()
    return [normal[a[1]:b[0]] if a and b and b[0] >= a[1] else None for a, b in zip(spans, spans[1:])]


def seam_positions(text: str, surfaces: Sequence[str]) -> list[int]:
    """Positions where a new route starts inside one stored chain (the next mention after the break)."""
    out = []
    for index, gap in enumerate(surface_gaps(text, surfaces)):
        if gap is None or not (TAHWIL_H.search(gap) or NEW_ROUTE_VERB.search(gap)):
            continue
        words = [w for w in sunni_norm(surfaces[index]).split() if w not in ("بن", "ابن", "ابو", "ابي")]
        take = 2 if words and (words[0] == "عبد" or words[0] in COMMON_ISM) else 1
        key = r"(?:\s+(?:بن|ابن))?\s+".join(words[:take])
        key = re.sub(r"(^|\s)ال(?=..)", r"\1", key)
        if len(words) >= take and len(key) > 2 and re.search(rf"(?<![ء-ي])(?:ال)?{key}(?![ء-ي])", sunni_norm(gap)):
            continue      # the text restates the previous shaykh after the break: the routes converge on him (benign)
        out.append(index + 1)
    return out


# A word that opens a remark on the wording («تقاربا في اللفظ»), never a name.
WORDING_REMARK = frozenset(["تقاربا", "تقاربوا", "واللفظ", "لفظه", "متقارب"])


def formula_trim(surface: str) -> tuple[str | None, bool]:
    """(the name left once formula words are cut, whether the surface had one). None: nothing of a name remains."""
    words = surface.split()
    folded = [sunni_norm(word) for word in words]
    if folded and folded[0] in WORDING_REMARK:
        return None, True
    hits = [index for index, word in enumerate(folded) if word in FORMULA_HIGH]
    if not hits:
        return surface, False
    first = hits[0]
    if first == 0:
        # A leading verb («حدثنا فلان») leaves the name after it; any other leading formula leaves nothing.
        rest = words[1:] if folded[0] in ("حدثني", "حدثنا", "اخبرني", "اخبرنا", "سمعت", "حدثتني") else []
        rest_folded = [sunni_norm(word) for word in rest]
        if not rest or any(word in FORMULA_HIGH for word in rest_folded):
            return None, True
        return " ".join(rest), True
    kept = " ".join(words[:first]).strip(" ،,.:")
    kept = re.sub(r"\s+(?:في|عن|و|قال|يعني|-)$", "", kept).strip(" ،,.:-")
    return (kept or None), True


@dataclass(frozen=True)
class SunniMention:
    surface: str
    origin: tuple[int, int] | None        # (branch, position) in the bundle's chain, for the source index and claims


@dataclass(frozen=True)
class SunniChain:
    mentions: list[SunniMention]
    split_from: int | None = None          # the bundle branch a seam split this route from


def build_sunni_chains(text: str, branches: list[list[str]], counts: Counter) -> list[SunniChain]:
    """Split flattened tahwil at its seam, cut formula words out of names, and put «A و B» neighbours on one level."""
    out: list[SunniChain] = []
    for branch_index, surfaces in enumerate(branches):
        mentions = [SunniMention(surface, (branch_index, position)) for position, surface in enumerate(surfaces)]
        gaps = surface_gaps(text, surfaces)
        # Co-transmitters stored as teacher then student: the second becomes an alternative at the first's level.
        levels: list[list[SunniMention]] = []
        for position, mention in enumerate(mentions):
            if position > 0 and gaps[position - 1] is not None and WAW_GAP.match(gaps[position - 1]) and levels:
                counts["co_transmitters_put_on_one_level"] += 1
                levels[-1].append(mention)
            else:
                levels.append([mention])
        routes: list[list[list[SunniMention]]] = [levels]
        seams = seam_positions(text, surfaces)
        if seams:
            routes = []
            starts = [0] + seams
            level_of = {}
            for level_index, level in enumerate(levels):
                for mention in level:
                    level_of[mention.origin[1]] = level_index
            cut_levels = sorted({level_of[position] for position in seams if position in level_of})
            bounds = [0] + cut_levels + [len(levels)]
            pieces = [levels[a:b] for a, b in zip(bounds, bounds[1:]) if b > a]
            counts["seam_chains_split"] += 1
            counts["seam_routes_made"] += len(pieces)
            # Each earlier route continues along the last route after the name it converges on (suffix alignment).
            last = pieces[-1]
            for piece in pieces[:-1]:
                tail: list[list[SunniMention]] = []
                end = sunni_norm(piece[-1][0].surface)
                for index, level in enumerate(last):
                    if any(sunni_norm(m.surface) == end for m in level):
                        tail = last[index + 1:]
                        break
                routes.append(piece + tail)
            routes.append(last)
            del starts
        for route_index, route in enumerate(routes):
            cleaned_levels = []
            aside_branch = False
            for level_index, level in enumerate(route):
                kept = []
                for mention in level:
                    name, had = formula_trim(mention.surface)
                    if had:
                        counts["formula_surfaces_trimmed" if name else "formula_surfaces_retired"] += 1
                    if name:
                        kept.append(SunniMention(name, mention.origin))
                if kept:
                    cleaned_levels.append(kept)
                elif len(branches) > 1 and level_index < len(route) - 1:
                    # «اللفظ لعمرو» read as a co-transmitter: its branch is an artefact; dropping only the aside would
                    # join its neighbours as teacher and student.
                    aside_branch = True
            if aside_branch:
                counts["aside_branches_dropped"] += 1
                continue
            paths: list[list[SunniMention]] = [[]]
            for level in cleaned_levels:
                if len(paths) * len(level) > 64:
                    level = level[:1]
                paths = [path + [mention] for path in paths for mention in level]
            for path in paths:
                if path and all([m.surface for m in path] != [m.surface for m in chain.mentions] for chain in out):
                    out.append(SunniChain(path, branch_index if len(routes) > 1 else None))
    return out


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
