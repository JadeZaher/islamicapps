"""Pure rules for the hadith-kg and Riwayat sidecars (README.md §External sources). No I/O, no database.

Everything here decides how a source's claim is carried, never whether it is true: a source id is that source's
claim, and the text checks only say whether our Arabic is consistent with it.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter

DATASET_HADITH_KG = "hadith_kg"
DATASET_RIWAYAT = "riwayat"
DATASETS = (DATASET_HADITH_KG, DATASET_RIWAYAT)
ID_PREFIX = {DATASET_HADITH_KG: "hadith-kg:rawi:", DATASET_RIWAYAT: "riwayat:"}

# --- 1. report crosswalk -------------------------------------------------------------------------------------------

MATCH_WHOLE = "whole_text_equal"
MATCH_MATN = "our_matn_contained"
MATCH_AMBIGUOUS = "ambiguous"
MATN_MIN_LETTERS = 40          # same floor as diagnostics/biography-verification (a shorter matn is formulaic)
KEY_LETTERS = 30               # first letters of our matn used as the lookup key, verified by full comparison

# Our source_work_id -> the same work in each dataset (hadith-kg books.id; Riwayat hadith.book). A work that is not
# listed has no counterpart and is never matched: a parallel in another book is another report with another chain.
WORK_MAP = {
    "sunni:bukhari": {DATASET_HADITH_KG: (1,), DATASET_RIWAYAT: ("صحيح البخاري",)},
    "sunni:muslim": {DATASET_HADITH_KG: (2,), DATASET_RIWAYAT: ("صحيح مسلم",)},
    "sunni:tirmidhi": {DATASET_HADITH_KG: (3,), DATASET_RIWAYAT: ("جامع الترمذي",)},
    "sunni:abudawud": {DATASET_HADITH_KG: (4,), DATASET_RIWAYAT: ("سنن أبي داود",)},
    "sunni:nasai": {DATASET_HADITH_KG: (5,), DATASET_RIWAYAT: ("سنن النسائى الصغرى",)},
    "sunni:ibnmajah": {DATASET_HADITH_KG: (6,), DATASET_RIWAYAT: ("سنن ابن ماجه",)},
    "sunni:darimi": {DATASET_HADITH_KG: (7,), DATASET_RIWAYAT: ("سنن الدارمي",)},
    "sunni:muwatta": {DATASET_HADITH_KG: (8,), DATASET_RIWAYAT: ("موطأ مالك رواية يحيى الليثي",)},
    "sunni:ahmad": {DATASET_HADITH_KG: (9,), DATASET_RIWAYAT: ("مسند أحمد بن حنبل",)},
    "sunni:shafii": {DATASET_HADITH_KG: (33,), DATASET_RIWAYAT: ("مسند الشافعي",)},
    "zaydi:musnad-zayd": {DATASET_HADITH_KG: (55,), DATASET_RIWAYAT: ("مسند زيد",)},
    "ibadi:musnad-rabi": {DATASET_HADITH_KG: (56,), DATASET_RIWAYAT: ("مسند الربيع بن حبيب",)},
    **{f"imami:{slug}": {DATASET_RIWAYAT: (slug,)} for slug in (
        "al-kafi", "man-la-yahduruhu-al-faqih", "al-amali-saduq", "al-amali-mufid", "al-khisal",
        "kitab-al-ghayba-tusi", "kitab-al-ghayba-numani", "thawab-al-amal", "uyun-akhbar-al-rida", "maani-al-akhbar",
        "kamil-al-ziyarat", "mujam-al-ahadith-al-mutabara", "kitab-al-zuhd", "kitab-al-duafa", "kitab-al-mumin",
        "sifat-al-shia", "fadail-al-shia", "nahj-al-balagha")},
    "imami:al-tawhid-saduq": {DATASET_RIWAYAT: ("al-tawhid",)},
}


def external_books(dataset: str) -> dict:
    """{external book key: our source_work_id} for one dataset (each external book belongs to exactly one work)."""
    out = {}
    for work_id, targets in WORK_MAP.items():
        for book in targets.get(dataset, ()):
            if book in out:
                raise ValueError(f"{dataset} book {book!r} mapped to two works")
            out[book] = work_id
    return out


def skeleton_words(normalized: str) -> tuple[str, list[int]]:
    """Letters-only text (Arabic base letters U+0621..U+064A) of an already normalized string, and word starts."""
    words = re.findall(r"[ء-ي]+", normalized or "")
    starts, total = [], 0
    for word in words:
        starts.append(total)
        total += len(word)
    return "".join(words), starts


def select_match(whole_hits, matn_hits) -> tuple[str, list]:
    """(class, candidates) for one of our reports: whole-text equality first, then our matn contained.

    A class with several same-work candidates is ambiguous; containment is not consulted when whole-text equality
    is ambiguous, because the duplicate is then the same text and containment cannot separate it.
    """
    whole, matn = sorted(set(whole_hits)), sorted(set(matn_hits))
    if len(whole) == 1:
        return MATCH_WHOLE, whole
    if len(whole) > 1:
        return MATCH_AMBIGUOUS, whole
    if len(matn) == 1:
        return MATCH_MATN, matn
    if len(matn) > 1:
        return MATCH_AMBIGUOUS, matn
    return "", []


def enforce_reverse_uniqueness(selected: dict) -> dict:
    """{our key: (class, [external])} -> same, with every unique pick that several of our reports share demoted.

    Unique on both sides: an external report picked by two of our reports identifies neither.
    """
    claimed = Counter(candidates[0] for match_class, candidates in selected.values()
                      if match_class in (MATCH_WHOLE, MATCH_MATN))
    out = {}
    for key, (match_class, candidates) in selected.items():
        if match_class in (MATCH_WHOLE, MATCH_MATN) and claimed[candidates[0]] > 1:
            out[key] = (MATCH_AMBIGUOUS, candidates, "external_report_claimed_by_several_of_ours")
        elif match_class == MATCH_AMBIGUOUS:
            out[key] = (MATCH_AMBIGUOUS, candidates, "several_external_reports_in_the_same_work")
        else:
            out[key] = (match_class, candidates, "")
    return out


# --- 2. external narrators -----------------------------------------------------------------------------------------

# A whole name that is a kinship word ("my father", "his grandfather") or a pronoun.
RELATIONAL_WORDS = {"ابيه", "ابوه", "ابي", "ابيها", "ابيهما", "جده", "جدي", "جدها", "عمه", "عمي", "امه", "امي",
                    "اخيه", "خاله", "خالي", "جدته", "عنه", "اخوه", "اخته", "ابنه", "ابن اخيه", "ابن عمه", "ابن اخته"}
# A leading kinship word with a third-person pronoun (أبيه عن جده); the bare first-person forms (أبي, جدي) open a
# kunya when more tokens follow (أبي عبد الله) and are therefore not listed here.
RELATIONAL_LEADS = {"ابيه", "ابوه", "ابيها", "ابيهما", "جده", "جدها", "عمه", "امه", "اخيه", "خاله", "جدته", "اخوه",
                    "ابنه"}
COLLECTIVE_PATTERNS = re.compile(
    r"^(?:(?:عد|جماع)[ةه](?: .*)?|بعض(?: .*)?|غير واحد(?: .*)?|رجل(?: .*)?|عن رجل|اصحابنا|من اخبره|من حدثه|"
    r"شيخ(?: من .*)?|امرا[ةه](?: .*)?|ابائه|اباءه|ابائهم|ابائي|اهل بيته|مولي لهم)$")
KUNYA_HEADS = ("ابو", "ابي", "ابا", "ام")
BLESSING_ABBREVIATIONS = {"ع", "ص", "صلعم", "رض", "ره", "عج"}
CONNECTORS = ("بن", "بنت", "ابن", "ابنه")


def external_name_placeholder(name_key: str) -> str:
    """Why an external narrator's name cannot carry a person identity ('' for a person-like name).

    `name_key` is the canonical comparison key (folded, formulas stripped). Mirrors the lexicon placeholder rule
    (AGENTS.md "Placeholder rows are never targets") plus relational and collective labels, which some datasets use
    as narrator records (Thaqalayn: أبيه, عدة من أصحابنا).
    """
    # one-letter blessing abbreviations (أبي عبد الله ع) are not name components
    tokens = [token for token in (name_key or "").split() if token not in BLESSING_ABBREVIATIONS]
    key = " ".join(tokens)
    if not tokens:
        return "no_arabic_name"
    if key in RELATIONAL_WORDS or (len(tokens) <= 3 and tokens[0] in RELATIONAL_LEADS):
        return "relational_name"
    if COLLECTIVE_PATTERNS.match(key):
        return "collective_or_anonymous_name"
    if len(tokens) == 1:
        return "bare_single_token_name"
    # a kunya alone; a theophoric `عبد X` is one name (ابو عبد الله), which the lexicon's two-token rule misses
    if tokens[0] in KUNYA_HEADS and (len(tokens) == 2 or (len(tokens) == 3 and tokens[1] == "عبد")):
        return "kunya_only_name"
    return ""


# Placeholder reasons under which a source claim is dropped (counted) rather than carried.
DROPPED_PLACEHOLDERS = frozenset({"no_arabic_name", "relational_name", "collective_or_anonymous_name",
                                  "bare_single_token_name"})
# Carried, but never confirmed by text: kunya-only (owner: shown marked, excluded from verified), and hadith-kg stubs,
# whose name was harvested from the hadith text itself, so agreeing with our text proves nothing.
KG_STUB = "hadith_kg_stub_narrator"
FLAGGED_PLACEHOLDERS = frozenset({"kunya_only_name", KG_STUB})

RIWAYAT_UPSTREAM_METHODS = frozenset({"source_annotation_kg", "source_annotation_thaqalayn",
                                      "thaqalayn_id_on_reparsed_span"})
RIWAYAT_MANUAL_METHODS = frozenset({"manual_gold", "manual_gold_unverified_id"})


def riwayat_id_origin(id_method: str) -> str:
    """Who asserted a Riwayat mention id: the upstream annotation it inherited, a hand check, or Riwayat's linker."""
    if id_method in RIWAYAT_UPSTREAM_METHODS:
        return "upstream_annotation"
    if id_method in RIWAYAT_MANUAL_METHODS:
        return "riwayat_manual_gold"
    return "riwayat_automatic_linking"


class ExternalNames:
    """Duck-typed stand-in for reconcile_common.Canon so the K6 `classify`/`align` run unchanged on external ids.

    `registry[id]["forms"]` holds the dataset's own names for the narrator (comparison keys); there are no parent
    links, so a relational surface (أبيه) is never corroborated. `resolve` returns None: the lexicon resolver is not
    consulted, the comparison is the source's name against our surface only.
    """

    def __init__(self, comparison_key, forms_by_id: dict):
        self.comparison_key = comparison_key
        self.registry = {}
        for external_id, names in forms_by_id.items():
            keys = []
            for name in names:
                key = comparison_key(name)
                if key and key not in keys:
                    keys.append(key)
            self.registry[external_id] = {"forms": keys, "parents": [], "teachers": set(), "students": set()}

    def resolve(self, surface):  # noqa: ARG002 - interface of Canon
        return None


CORROBORATED_CLASSES = ("full_agreement", "multi_branch_all_source_ids_aligned")


def mention_basis(dataset: str, agreement_class: str, placeholder: str) -> str:
    """`source_<dataset>` with `_confirmed_by_text` only for a corroborated report and a person-like name."""
    base = f"source_{dataset}"
    if agreement_class in CORROBORATED_CLASSES and placeholder not in FLAGGED_PLACEHOLDERS:
        return base + "_confirmed_by_text"
    return base


# --- lexicon links -------------------------------------------------------------------------------------------------

LINK_YEAR = "unique_full_name_plus_death_year"
LINK_K6 = "unique_full_name_plus_k6_position_agreement"
LINK_BOTH = "unique_full_name_plus_death_year_and_k6_position_agreement"
LINK_CROSSWALK = "riwayat_kg_crosswalk_to_linked_hadith_kg_narrator"


def years_overlap(a_min, a_max, b_min, b_max) -> bool:
    """Closed intervals with open (None) bounds overlap; an interval with both bounds None never agrees."""
    if (a_min is None and a_max is None) or (b_min is None and b_max is None):
        return False
    low_a = a_min if a_min is not None else -10 ** 6
    high_a = a_max if a_max is not None else 10 ** 6
    low_b = b_min if b_min is not None else -10 ** 6
    high_b = b_max if b_max is not None else 10 ** 6
    return max(low_a, low_b) <= min(high_a, high_b)


def k6_agrees(pair_count: int, external_total: int, lexicon_total: int) -> bool:
    """The K6 source index names this lexicon id at the same mentions as the external id, as the clear majority
    for both: at least one shared mention, and more than half of each side's co-claimed mentions."""
    return pair_count >= 1 and 2 * pair_count > external_total and 2 * pair_count > lexicon_total


def link_decision(name_unique: bool, sunni_context: bool, year_agrees: bool, k6_agreement: bool,
                  year_conflicts: bool) -> str:
    """Lexicon link basis, or '' (no link). Name alone never links, and nothing links outside a Sunni context:
    the rawi lexicon is the Sunni-centred muslimscholars register and identities are not merged across traditions."""
    if not (name_unique and sunni_context):
        return ""
    if year_conflicts and not k6_agreement:
        return ""
    if year_agrees and k6_agreement:
        return LINK_BOTH
    if year_agrees:
        return LINK_YEAR
    if k6_agreement:
        return LINK_K6
    return ""


# --- 5. Qur'an quotations ------------------------------------------------------------------------------------------

SURA_NAMES = (
    "الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف", "الأنفال", "التوبة", "يونس", "هود",
    "يوسف", "الرعد", "إبراهيم", "الحجر", "النحل", "الإسراء", "الكهف", "مريم", "طه", "الأنبياء", "الحج", "المؤمنون",
    "النور", "الفرقان", "الشعراء", "النمل", "القصص", "العنكبوت", "الروم", "لقمان", "السجدة", "الأحزاب", "سبأ", "فاطر",
    "يس", "الصافات", "ص", "الزمر", "غافر", "فصلت", "الشورى", "الزخرف", "الدخان", "الجاثية", "الأحقاف", "محمد", "الفتح",
    "الحجرات", "ق", "الذاريات", "الطور", "النجم", "القمر", "الرحمن", "الواقعة", "الحديد", "المجادلة", "الحشر",
    "الممتحنة", "الصف", "الجمعة", "المنافقون", "التغابن", "الطلاق", "التحريم", "الملك", "القلم", "الحاقة", "المعارج",
    "نوح", "الجن", "المزمل", "المدثر", "القيامة", "الإنسان", "المرسلات", "النبأ", "النازعات", "عبس", "التكوير",
    "الانفطار", "المطففين", "الانشقاق", "البروج", "الطارق", "الأعلى", "الغاشية", "الفجر", "البلد", "الشمس", "الليل",
    "الضحى", "الشرح", "التين", "العلق", "القدر", "البينة", "الزلزلة", "العاديات", "القارعة", "التكاثر", "العصر",
    "الهمزة", "الفيل", "قريش", "الماعون", "الكوثر", "الكافرون", "النصر", "المسد", "الإخلاص", "الفلق", "الناس",
)
_MARKS = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")
_ALEFS = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي"})


def _sura_key(name: str) -> str:
    return " ".join(_MARKS.sub("", name or "").translate(_ALEFS).split())


SURA_NUMBER = {_sura_key(name): number for number, name in enumerate(SURA_NAMES, 1)}
# hadith-kg appends `سورة <name> آية <n>[ ـ <m>]` after each quotation; the name is one word or آل + one word.
QURAN_LABEL = re.compile(r"سورة\s+((?:آل|ال)\s+\S+|\S+)\s+آية\s+(\d+)(?:\s*[-ـ–]\s*(\d+))?")


def strip_quran_labels(text: str) -> str:
    """External text without hadith-kg's inline verse labels (`سورة العلق آية 1-3`), for comparison only: the labels
    are editorial insertions, so a report quoting a verse would otherwise never equal or contain our text."""
    return QURAN_LABEL.sub(" ", text or "")


def parse_quran_span(span: str) -> tuple[str, list[dict]]:
    """(quoted text with hadith-kg's verse labels removed, the labels as written with the sura number they name).

    The labels are hadith-kg's own references; a name that is not one of the 114 sura names gets no number.
    """
    references = []
    for match in QURAN_LABEL.finditer(span or ""):
        name = match.group(1)
        first, last = int(match.group(2)), int(match.group(3) or match.group(2))
        references.append({"label_verbatim": match.group(0), "sura_name": name,
                           "sura_number": SURA_NUMBER.get(_sura_key(name)), "aya_from": first, "aya_to": last})
    quote = QURAN_LABEL.sub(" ", span or "")
    return " ".join(quote.split()), references


def letters_with_origins(text: str, normalize_char) -> tuple[str, list[int], set[int], set[int]]:
    """Letters-only skeleton of `text` built character by character, with each letter's offset in `text`, and the
    skeleton offsets where a word starts and where one ends (exclusive)."""
    letters, origins, starts, ends = [], [], set(), set()
    in_word = False
    for offset, char in enumerate(text or ""):
        produced = [c for c in normalize_char(char) if "ء" <= c <= "ي"]
        if produced:
            if not in_word:
                starts.add(len(letters))
                in_word = True
            letters.extend(produced)
            origins.extend([offset] * len(produced))
        elif not is_inside_word(char):
            if in_word:
                ends.add(len(letters))
            in_word = False
    if in_word:
        ends.add(len(letters))
    return "".join(letters), origins, starts, ends


def is_inside_word(char: str) -> bool:
    """A character that never ends a word: vocalization and other marks, tatweel, format controls."""
    return unicodedata.category(char) in ("Mn", "Me", "Mc", "Cf") or char == "ـ"


def relocate_unique(needle: str, haystack: str, starts: set, ends: set):
    """Start of the only word-aligned occurrence of `needle` in `haystack`, or None (absent or repeated)."""
    if not needle:
        return None
    found = []
    position = haystack.find(needle)
    while position != -1:
        if position in starts and position + len(needle) in ends:
            found.append(position)
            if len(found) > 1:
                return None
        position = haystack.find(needle, position + 1)
    return found[0] if found else None


def original_span(text: str, origins: list[int], start: int, length: int) -> tuple[int, int]:
    """[start, end) in the original text for skeleton letters [start, start+length), extended over trailing marks."""
    begin = origins[start]
    end = origins[start + length - 1] + 1
    while end < len(text) and is_inside_word(text[end]):
        end += 1
    return begin, end
