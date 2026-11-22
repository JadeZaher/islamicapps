"""Chain structure trust: which stored chains a tested rule can stand behind (see pg_export/AGENTS.md §Chain structure gate).

A chain is `checked_by_rule` when no detector fires, else `uncertain` with stable reason codes. Detectors are ported from the
audit lanes (`chain-audit/{sunni,imami,ibadi-zaydi,round2,round3}/`) and measured on the re-checks' read verdicts. Pure and
standard library apart from the shared Sunni normalizer and name keys in `chain_builder`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

from chain_builder import (CONVERGENCE_WORD, FORMULA_HIGH, LINK_VERB, NUMBER_WORDS, ROUTE_HEAD_GAP, TAHWIL_H, name_key,
                           ordered_spans, sunni_norm)

CHECKED = "checked_by_rule"
UNCERTAIN = "uncertain"

# Reader-facing wording of every reason code (the page and /method read these; codes are stable, wording may change).
REASON_TEXT = {
    "repeated_name": "the same name stands twice in this chain",
    "duplicated_link": "one person appears to be stored as two neighbouring links",
    "short_beside_long": "this route is much shorter than another route of the same report",
    "not_a_name": "a stored link contains words that are not a name (a verb, a clause, digits or the report's text)",
    "joined_names": "a stored link holds two names joined by «و»",
    "route_break_inside": "the text starts a new route («ح» or «وحدثنا») between two links stored in one chain",
    "text_between_links": "the text names more between two stored links than the chain holds",
    "text_names_more_after": "the text names a further transmitter after the last stored link",
    "order_not_in_text": "the stored names cannot be found in the text in the stored order",
    "unaccounted_route_marker": "the text marks more routes («ح», «جميعا», «كلهم») than were stored",
    "long_chain": "the chain is unusually long for one route",
    "ghayr_wahid_half": "half of «غير واحد» is stored as a link",
    "crossed_routes": "two of al-Kulayni's routes appear joined in one chain",
    "many_routes": "the report has three or more routes, which the rules read wrong too often to rely on",
    "work_not_checked": "chains in this work were read wrong too often to rely on without review",
}

# Detectors that set a chain `uncertain` (the operating point measured on the labelled set; AGENTS.md §Chain structure
# gate). `route_break_inside`, `order_not_in_text` and `long_chain` are computed for measurement only: on the labelled set
# they flagged no defect the gate's detectors had not already flagged, at a cost of correct chains.
GATE_REASONS = frozenset(["duplicated_link", "joined_names", "ghayr_wahid_half", "short_beside_long", "repeated_name",
                          "text_between_links", "text_names_more_after", "not_a_name", "unaccounted_route_marker",
                          "crossed_routes", "many_routes", "work_not_checked"])

# Imami works whose chains the re-check found defective in 11 of 32 sampled (round 3): every chain is uncertain.
# al-Kafi (3/50), Man la Yahduruhu al-Faqih and Thawab al-Aʿmal are not in the list.
UNCHECKED_WORKS = frozenset(f"imami:{work}" for work in [
    "al-khisal", "al-amali-saduq", "uyun-akhbar-al-rida", "maani-al-akhbar", "kitab-al-ghayba-tusi", "kamil-al-ziyarat",
    "kamal-al-din", "al-tawhid-saduq", "mujam-al-ahadith-al-mutabara", "kitab-al-ghayba-numani", "al-amali-mufid",
    "kitab-al-zuhd", "kitab-al-mumin", "sifat-al-shia", "fadail-al-shia"])
MANY_ROUTES = 3

# Works whose text is prose or rijal entries: no chain is stored for them at all (retired).
PROSE_WORKS = frozenset(["imami:kitab-al-duafa", "imami:risalat-al-huquq"])

PERSIAN = str.maketrans({"ی": "ي", "ک": "ك", "ي": "ي"})
RELATION = frozenset(["ابيه", "ابي", "جده", "جدي", "عمه", "عمي", "امه", "امي", "ابائه", "اخيه", "خاله", "ابوه", "اباه"])
CONNECTOR = frozenset(["بن", "ابن", "ابو", "ابي", "ابا", "ام", "عبد", "بنت", "ال"])
LABEL = re.compile(r"^(?:و\s?)?(?:رجل|رجلا|الرجل|بعض\s+|عمن\s+|رفعه|يرفعه|غير\s+واحد|عدة\s+من|جماعة|من\s+ذكره|بلغني|بلغنا"
                   r"|عنه|عنهم|عنهما|بهذا|وبهذا|و\s+بهذا)")
NASAB_WORD = frozenset(["بن", "ابن", "بنت", "ابو", "ابي", "ابا", "ام", "عبد", "مولي", "مولاة"])
# Words that never stand inside a narrator's name: verbs and clause words (the audit's R3/R3b lists, chain_builder's).
NOT_NAME_WORD = frozenset(LINK_VERB) | FORMULA_HIGH | frozenset([
    "قال", "قالت", "قالا", "قالوا", "فقال", "فقالت", "فقالا", "وقال", "يقول", "يقولان", "تقول", "سئل", "وسئل", "سالت", "سالت",
    "نهي", "امر", "انه", "انها", "انهما", "انهم", "يحدث", "يحدثه", "يخبر", "قراءة", "اذا", "في", "وفي", "كان", "كانت", "كنت",
    "لم", "ثم", "حتي", "ذلك", "زاد", "وزاد", "باب", "روي", "وروي", "رويته", "ورويته", "حديث", "بحديث", "باسناد", "بإسناد",
    "بمثل", "كمعني", "الزيادة", "عليه", "لا", "ما", "هل", "ان", "اي", "يعني", "ينكر", "يكني", "يلقب", "كذاب", "غال", "ثقة",
    "ضعيف", "عاش", "ساق", "بطوله", "اخر", "يصلي", "اكل", "اهدي", "هو", "انا", "نحن", "عند", "له", "لها", "الي",
    "المعني",
])
LINK_GAP_WORD = frozenset([
    "عن", "حدثنا", "حدثني", "اخبرنا", "اخبرني", "انبانا", "انباني", "ثنا", "نا", "انا", "سمعت", "سمع", "سمعا", "قال", "قالت",
    "قالا", "يقول", "تقول", "حدثه", "حدثته", "اخبره", "اخبرته", "ان", "انه", "انها", "انهما", "قراءة", "عليه", "عليها",
    "وانا", "اسمع", "حدثتني", "حدثتنا", "اخبرتني", "اخبرتنا", "يحدث", "يخبر", "يرفعه", "رفعه", "به", "حدثناه", "حدثنيه",
    "السلام", "عليهم", "عليهما", "صلي", "الله", "وسلم", "واله", "وآله", "رضي", "عنه", "عنها", "عنهما", "رحمه", "ع", "ص", "ره",
    "تعالي", "عز", "وجل", "كلاهما", "جميعا", "كلهم", "قالوا", "فقال", "وقال", "سالت", "سالنا", "قلت", "يعني", "هو", "ابن", "بن",
    "واللفظ", "اللفظ", "لفظ", "له", "لفظه", "و", "يذكر", "قد", "لقد", "زوج", "النبي", "رسول", "مولي", "المعني", "معناه",
    "بمعناه", "مرفوعا", "موقوفا", "مثله", "نحوه", "بنحوه", "بمثله", "بهذا", "الاسناد", "الحديث", "ح", "أيضا", "ايضا", "الا",
    "ما", "كنت", "كان", "كانت", "احدهما", "وحدثنا", "وحدثني", "واخبرنا", "واخبرني", "عليهما", "عليهم", "الصلاة", "الي", "رحمهما", "رحمهم", "قالوا", "الاخرون", "الاخران",
])
ROUTE_VERB = re.compile(r"(?:^|\s)(?:قال\s+)?و(?:اخبرنا|حدثنا|اخبرني|حدثني|انبانا|حدثناه|حدثنيه)(?=\s|$)")
# After the last stored link, before the matn reaches the Prophet: a link word or a «قال/سألت/سمعت» naming someone.
AFTER_LAST = re.compile(
    r"(?<![ء-ي])(?:عن|حدثنا|حدثني|فحدثنا|فحدثني|اخبرنا|اخبرني|فاخبرني|فاخبرنا|حدثتني|حدثتنا|اخبرتني)\s+(?P<name>[ء-ي]+(?:\s+[ء-ي]+)?)"
    r"|(?<![ء-ي])(?:سالت|سمعت)\s+(?P<named>(?:ابا|ابو|ابي|ابن|ام|عبد)\s*[ء-ي]+|[ء-ي]+\s+بن\s+[ء-ي]+)")
MATN_REACHED = re.compile(r"(?<![ء-ي])(?:رسول\s+الله|النبي|نبي\s+الله)(?![ء-ي])|[\"“]")
PROPHET_OR_IMAM = re.compile(r"^(?:رسول|النبي|نبي|الله|امير|احدهما|احدهم|ابيه|جده|رجل|الرجل|امراة|المراة|قول|ذلك|شيء|هذا|ابي\s+عبد\s+الله|ابي\s+جعفر|ابي\s+الحسن|ابا\s+عبد\s+الله"
                             r"|ابا\s+جعفر|ابا\s+الحسن|ابو\s+عبد\s+الله|ابو\s+جعفر|ابو\s+الحسن|الرضا|الصادق|الباقر|عليا|علي)")
DIGIT = re.compile(r"[0-9٠-٩]")


@dataclass(frozen=True)
class ReportChains:
    """One report: its detection text, its stored chains (surfaces in order) and which chains are not written in it."""
    text: str
    chains: Sequence[Sequence[str]]
    tradition: str                                  # Sunni | Imami | Ibadi | Zaydi
    inherited: Sequence[bool] = ()                  # a continuation's names stand in its parent's text, not this one
    thaqalayn: bool = False                         # Thaqalayn's Imami works: «قال سألت أبا عبد الله» is not read as a link
    work: str = ""                                  # source_work_id without the "work:" prefix, e.g. "imami:al-kafi"
    routes_from_text: bool = True                   # False for Pure Canon, whose chains come from the source's chain field


def fold(value: str) -> str:
    """`sunni_norm` with the Persian ya and kaf read as Arabic (detection only; stored letters never change)."""
    return sunni_norm((value or "").translate(PERSIAN))


def _words(surface: str) -> list[str]:
    return fold(surface).split()


def _is_label(surface: str) -> bool:
    return bool(LABEL.match(fold(surface)))


def not_a_name(surface: str) -> bool:
    """A stored link that is no name: a verb, clause or formula word, digits, a fragment of one letter, a long clause."""
    words = _words(surface)
    if not words:
        return False
    if _is_label(surface):
        return any(word in NOT_NAME_WORD for word in words[1:]) or bool(DIGIT.search(surface))
    if DIGIT.search(surface) or (len(words) == 1 and len(words[0]) <= 1):
        return True
    if any(word in NOT_NAME_WORD for word in words[1:]) or (words[0] in NOT_NAME_WORD and len(words) > 1):
        return True
    return len(words) >= 6 and not any(word in NASAB_WORD for word in words)


def joined_names(surface: str) -> bool:
    """«الحلبي و زرارة», «أبي وأم عبد الملك»: two people in one link."""
    words = _words(surface)
    if _is_label(surface) or len(words) < 2:
        return False
    for index, word in enumerate(words[1:], 1):
        if word == "و" and index < len(words) - 1:
            return True
        if word.startswith("و") and word[1:] in ("ام", "ابي", "ابو", "ابن", "محمد", "احمد", "علي", "عبد", "الحسن",
                                                 "الحسين", "حمران", "زرارة", "زراره", "الحلبي", "محمد"):
            return True
    return False


def _key_words(surface: str) -> list[str]:
    return name_key(fold(surface).translate(PERSIAN)).split()


def duplicated_link(a: str, b: str) -> bool:
    """Neighbours naming one man: «حماد > حماد بن زيد», «إسماعيل بن جعفر > إسماعيل», «محمد بن رافع > ابن رافع»."""
    if _is_label(a) or _is_label(b):
        return False
    ka, kb = _key_words(a), _key_words(b)
    if not ka or not kb or ka[0] in RELATION or kb[0] in RELATION:
        return False
    if ka == kb:
        return True
    short, long_ = (ka, kb) if len(ka) < len(kb) else (kb, ka)
    # «أحمد بن محمد > أحمد بن محمد بن أبي نصر» are two men (al-Kafi); only a bare name or «ابن X» repeats one.
    if len(short) > 2 or not any(word not in CONNECTOR for word in short):
        return False
    return long_[:len(short)] == short or (short[0] == "بن" and long_[-len(short):] == short)


# al-Kafi's parallel routes read as one (the re-check's R9): al-Kulayni's own shaykh after «أبيه», or Ibn Abi ʿUmayr
# before al-Fadl b. Shadhan, who transmits from him only in the other route.
CROSSED_PAIRS = frozenset([("ابيه", "محمد بن اسماعيل"), ("ابيه", "محمد بن يحيي"), ("ابن ابي عمير", "الفضل بن شاذان"),
                           ("محمد بن ابي عمير", "الفضل بن شاذان")])


def crossed_routes(chain: Sequence[str]) -> bool:
    """A neighbour pair that only arises when two of al-Kafi's routes are read as one."""
    keys = [fold(surface) for surface in chain]
    return any((a, b) in CROSSED_PAIRS for a, b in zip(keys, keys[1:]))


def _repeated(chain: Sequence[str]) -> bool:
    keys = []
    for surface in chain:
        key = " ".join(_key_words(surface))
        keys.append(None if not key or key.split()[0] in RELATION or _is_label(surface) or len(key) < 3 else key)
    for i, key in enumerate(keys):
        if key and any(keys[j] == key for j in range(i + 2, len(keys))):
            return True
    return False


ASIDE = re.compile(r"(?<![ء-ي])(?:و?هو|يعني|يعنون|و?اللفظ|لفظ[ء-ي]*|و?قال\s+الاخر[ء-ي]*)(?![ء-ي])[^،,\-]*")
WORDING = re.compile(r"(?<![ء-ي])و?قال[\s،,]+(?P<name>[ء-ي]+(?:\s+[ء-ي]+){0,3}?)[\s،,]+(?=(?:حدثنا|حدثني|اخبرنا|اخبرني|انبانا)(?![ء-ي]))")


def _gap_says_more(gap: str, report_names: Sequence[str] = ()) -> bool:
    """Words between two stored neighbours that are neither link words, asides, a wording attribution, a year phrase nor a
    name the report stores elsewhere (a co-transmitter or a «جميعا» group held by a sibling route)."""
    gap = WORDING.sub(" ", ASIDE.sub(" ", gap))
    for name in report_names:
        if name.split()[0] in gap:
            body = r"[\s،,]+".join(re.escape(word) for word in name.split())
            gap = re.sub(rf"(?<![ء-ي])و?{body}ا?(?![ء-ي])", " ", gap)
    words = [word for word in re.split(r"[\s،,:.؛\-()«»\"]+", gap) if word]
    return any(word not in LINK_GAP_WORD and not word.startswith(("وحدث", "واخبر", "حدث", "اخبر"))
               and (word[1:] if word.startswith("و") else word) not in NUMBER_WORDS | {"غير", "واحد", "سنة"} for word in words)


def _break_at_route_head(gap: str) -> bool:
    """A route break («ح», «وحدثنا») with only a verb after it: the right neighbour heads a new route (a flattened tahwil)."""
    ends = [match.end() for pattern in (TAHWIL_H, ROUTE_VERB) for match in pattern.finditer(gap)]
    if not ends:
        return False
    rest = gap[max(ends):]
    head = ROUTE_VERB.search(gap)
    if head and head.end() == max(ends):
        rest = gap[head.start():]
    return bool(ROUTE_HEAD_GAP.match(rest.replace("ح ", " ", 1) if rest.lstrip().startswith("ح ") else rest))


def assess(report: ReportChains, evidence: list | None = None, measure_all: bool = False) -> list[list[str]]:
    """Sorted gate reason codes per stored chain (empty: checked by rule); `evidence` collects (chain, code, text) when
    given; `measure_all` also returns the measured-only codes."""
    chains = [list(chain) for chain in report.chains]
    reasons: list[set[str]] = [set() for _ in chains]
    inherited = list(report.inherited) + [False] * (len(chains) - len(report.inherited))
    longest = max((len(chain) for chain in chains), default=0)
    for index, chain in enumerate(chains):
        found = reasons[index]
        if any(not_a_name(surface) for surface in chain):
            found.add("not_a_name")
        if any(joined_names(surface) for surface in chain):
            found.add("joined_names")
        if any(duplicated_link(a, b) for a, b in zip(chain, chain[1:])):
            found.add("duplicated_link")
        if report.thaqalayn and crossed_routes(chain):
            found.add("crossed_routes")
        if _repeated(chain):
            found.add("repeated_name")
        if len(chain) <= 3 and longest >= 5 and len(chains) > 1:
            found.add("short_beside_long")
        if report.work in UNCHECKED_WORKS:
            found.add("work_not_checked")
        if report.tradition == "Sunni" and report.routes_from_text and len(chains) >= MANY_ROUTES:
            found.add("many_routes")
        if len(chain) >= 12:
            found.add("long_chain")
        if any(re.fullmatch(r"(?:عن\s)?و?\s?غير|و?احد(?:\s.*)?", fold(surface)) for surface in chain):
            found.add("ghayr_wahid_half")
    normal = fold(report.text)
    written = [chain if not inherited[index] else [] for index, chain in enumerate(chains)]
    spans = ordered_spans(normal, [[surface.translate(PERSIAN) for surface in chain] for chain in written]) if normal else []
    report_names = sorted({fold(surface) for chain in chains for surface in chain if len(fold(surface)) >= 2}, key=len,
                          reverse=True)
    for index, chain_spans in enumerate(spans):
        if not written[index]:
            continue
        found = reasons[index]
        if any(span is None for span in chain_spans):
            found.add("order_not_in_text")
            continue
        for left, right in zip(chain_spans, chain_spans[1:]):
            gap = normal[left[1]:right[0]]
            if _break_at_route_head(gap):
                code = "route_break_inside"
            elif _gap_says_more(gap, report_names):
                code = "text_between_links"
            else:
                continue
            found.add(code)
            if evidence is not None:
                evidence.append((index, code, gap))
        if report.thaqalayn:
            continue          # «قال سألت أبا عبد الله ... عن الرجل»: the Imam convention gap, not a lost name (owner, not ruled)
        tail = normal[chain_spans[-1][1]:chain_spans[-1][1] + 120]
        stop = MATN_REACHED.search(tail)
        tail = WORDING.sub(" ", ASIDE.sub(" ", tail[:stop.start()] if stop else tail))
        for hit in AFTER_LAST.finditer(tail):
            named = (hit.group("name") or hit.group("named")).strip()
            if PROPHET_OR_IMAM.match(named) or any(named.startswith(name) for name in report_names):
                continue
            found.add("text_names_more_after")
            if evidence is not None:
                evidence.append((index, "text_names_more_after", tail))
            break
    if normal and chains:
        breaks = len(TAHWIL_H.findall(normal))
        convergence = len(CONVERGENCE_WORD.findall(normal))
        if (breaks and len(chains) < breaks + 1) or (convergence and len(chains) < 2):
            for found in reasons:
                found.add("unaccounted_route_marker")
    return [sorted(found if measure_all else found & GATE_REASONS) for found in reasons]


def retire_reason(work: str, tradition: str, text: str, routes_from_text: bool = True) -> str | None:
    """A report whose stored chains are retired whole: prose or rijal works, and a chapter heading read as a chain (only
    where chains are read from the text: a Pure Canon report keeps the chain its source's own chain field gives)."""
    if work in PROSE_WORKS:
        return "prose_work"
    if tradition == "Sunni" and routes_from_text and fold(text).startswith("باب "):
        return "chapter_heading"
    return None
