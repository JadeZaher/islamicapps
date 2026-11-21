"""Pure parsing of rijal entries: Arabic year words, death statements, tabaqa, verdict span, headword.

See README.md in this directory for the rules and their limits. Standard library only; no I/O.
Phrase detection runs on a light letter fold (`fold_for_phrases`); name keys never use it (they use the
canonical `regen_unified_csvs` name folds, applied by the callers).
"""

import re

_DIACRITICS = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")
_ALEF = re.compile(r"[آأإٱ]")


def fold_for_phrases(text: str) -> str:
    """Strip vocalization and tatweel, alef variants to ا, ى to ي, collapse spaces (phrase matching only)."""
    text = _ALEF.sub("ا", _DIACRITICS.sub("", text or ""))
    return " ".join(text.replace("ى", "ي").split())


# --- Arabic year words -------------------------------------------------------------------------------------------

UNITS = {
    "احدي": 1, "احد": 1, "واحد": 1, "واحده": 1, "واحدة": 1,
    "اثنتين": 2, "اثنين": 2, "ثنتين": 2, "اثنتي": 2, "اثني": 2, "ثنتي": 2,
    "ثلاث": 3, "ثلاثة": 3, "ثلاثه": 3, "اربع": 4, "اربعة": 4, "اربعه": 4,
    "خمس": 5, "خمسة": 5, "خمسه": 5, "ست": 6, "ستة": 6, "سته": 6,
    "سبع": 7, "سبعة": 7, "سبعه": 7, "ثمان": 8, "ثماني": 8, "ثمانية": 8, "ثمانيه": 8,
    "تسع": 9, "تسعة": 9, "تسعه": 9,
}
TEENS_MARK = {"عشرة", "عشره", "عشر"}
TENS = {"عشرين": 20, "ثلاثين": 30, "اربعين": 40, "خمسين": 50, "ستين": 60, "سبعين": 70, "ثمانين": 80, "تسعين": 90}
HUNDREDS = {
    "مائة": 100, "مئة": 100, "ماية": 100, "مايه": 100, "مائه": 100, "مئه": 100,
    "مائتين": 200, "مئتين": 200, "مائتي": 200, "مئتي": 200, "مايتين": 200,
    "ثلاثمائة": 300, "ثلاثمئة": 300, "اربعمائة": 400, "اربعمئة": 400, "خمسمائة": 500, "خمسمئة": 500,
    "ستمائة": 600, "سبعمائة": 700, "ثمانمائة": 800,
}
HUNDRED_WORDS = {"مائة", "مئة", "ماية", "مايه", "مائه", "مئه"}
VAGUE_UNITS = {"بضع": (3, 9), "بضعة": (3, 9), "بضعه": (3, 9), "نيف": (1, 9), "ونيف": (1, 9)}
DEFINITE_TENS = {"ال" + word: value for word, value in TENS.items()}
DEFINITE_TENS.update({"العشرين": 20, "المائة": 100, "المئة": 100, "المائتين": 200, "المئتين": 200})


def _strip_conjunction(token: str) -> str:
    return token[1:] if token.startswith("و") and len(token) > 2 and token[1:] in _NUMBER_WORDS else token


_NUMBER_WORDS = set(UNITS) | TEENS_MARK | set(TENS) | set(HUNDREDS) | set(VAGUE_UNITS) | set(DEFINITE_TENS)


def parse_number_words(tokens: list) -> tuple:
    """Read one Arabic cardinal from the start of `tokens`.

    Returns (parts, consumed) where parts = {'units': (lo, hi) | None, 'tens': int | None, 'teen': bool,
    'hundreds': int | None}; consumed = 0 when no number starts here. ثلاث مائة (split hundreds) is handled.
    """
    parts = {"units": None, "tens": None, "teen": False, "hundreds": None}
    consumed = 0
    index = 0
    while index < len(tokens):
        token = _strip_conjunction(tokens[index])
        if token in UNITS and parts["units"] is None and parts["tens"] is None and parts["hundreds"] is None:
            following = tokens[index + 1] if index + 1 < len(tokens) else ""
            if following in HUNDRED_WORDS:  # ثلاث مائة
                parts["hundreds"] = UNITS[token] * 100
                index += 2
                consumed = index
                continue
            parts["units"] = (UNITS[token], UNITS[token])
        elif token in VAGUE_UNITS and parts["units"] is None and parts["tens"] is None:
            parts["units"] = VAGUE_UNITS[token]
        elif token in TEENS_MARK and parts["tens"] is None and parts["hundreds"] is None and not parts["teen"]:
            if parts["units"] is not None:
                parts["teen"] = True
            else:
                parts["tens"] = 10
        elif token in TENS and parts["tens"] is None and not parts["teen"] and parts["hundreds"] is None:
            parts["tens"] = TENS[token]
        elif token in HUNDREDS and parts["hundreds"] is None:
            parts["hundreds"] = HUNDREDS[token]
        else:
            break
        index += 1
        consumed = index
    return parts, consumed


def parts_to_range(parts: dict) -> tuple:
    """(min, max) for parsed parts, ignoring a missing century (caller adds it)."""
    low_units, high_units = parts["units"] or (0, 0)
    tens = parts["tens"] or 0
    if parts["teen"]:
        tens = 10
    hundreds = parts["hundreds"] or 0
    return hundreds + tens + low_units, hundreds + tens + high_units


# --- tabaqa, companions, verdict ---------------------------------------------------------------------------------

TABAQA_ORDINALS = [
    ("الحادية عشرة", 11), ("الحاديه عشره", 11), ("الثانية عشرة", 12), ("الثانيه عشره", 12),
    ("الاولي", 1), ("الثانية", 2), ("الثانيه", 2), ("الثالثة", 3), ("الثالثه", 3), ("الرابعة", 4), ("الرابعه", 4),
    ("الخامسة", 5), ("الخامسه", 5), ("السادسة", 6), ("السادسه", 6), ("السابعة", 7), ("السابعه", 7),
    ("الثامنة", 8), ("الثامنه", 8), ("التاسعة", 9), ("التاسعه", 9), ("العاشرة", 10), ("العاشره", 10),
]
_TABAQA = re.compile(
    r"(?<![ء-ي])من\s+(?:(كبار|اوساط|صغار)\s+)?(" + "|".join(re.escape(o) for o, _ in TABAQA_ORDINALS) + r")(?![ء-ي])"
)
_ORDINAL_VALUE = dict(TABAQA_ORDINALS)
_COMPANION = re.compile(r"(?<![ء-ي])(صحابي|صحابية|صحابيه|له صحبة|له صحبه|لها صحبة|لها صحبه|من كبار الصحابة|من صغار الصحابة)(?![ء-ي])")
_RUYA = re.compile(r"(?<![ء-ي])(له رؤية|له رؤيه|لها رؤية)(?![ء-ي])")
_MUKHADRAM = re.compile(r"(?<![ء-ي])مخضرم(?![ء-ي])")


def find_tabaqa(folded: str) -> dict:
    """Ibn Hajar's stated tabaqa: an explicit 'من ال<ordinal>' clause, else a companion statement (tabaqa 1)."""
    match = _TABAQA.search(folded)
    if match:
        return {"tabaqa": _ORDINAL_VALUE[match.group(2)], "qualifier": match.group(1), "basis": "explicit_ordinal",
                "verbatim": match.group(0)}
    match = _COMPANION.search(folded) or _RUYA.search(folded)
    if match:
        return {"tabaqa": 1, "qualifier": None, "basis": "companion_statement", "verbatim": match.group(0)}
    return {"tabaqa": None, "qualifier": None, "basis": None, "verbatim": None}


# Ibn Hajar's twelve maratib vocabulary (Taqrib introduction); the first match opens the verdict span.
VERDICT_TERMS = [
    "ثقة ثقة", "ثقة ثبت", "ثقة حافظ", "ثقة", "ثبت", "حافظ", "حجة", "امام", "متقن",
    "صدوق", "لا باس به", "ليس به باس", "مقبول", "لين الحديث", "فيه لين", "لين", "مستور", "مجهول الحال", "مجهول",
    "لا يعرف", "ضعيف", "متروك", "منكر الحديث", "واهي الحديث", "واه", "ساقط", "متهم", "كذاب", "كذبوه", "وضاع",
    "صحابي", "صحابية", "صحابيه", "له صحبة", "له صحبه", "لها صحبة", "له رؤية", "له رؤيه",
]
_VERDICT = re.compile(r"(?<![ء-ي])(" + "|".join(re.escape(t) for t in VERDICT_TERMS) + r")(?![ء-ي])")
_DEATH_VERB = re.compile(r"(?<![ء-ي])(مات|ماتت|توفي|توفيت|قتل|قتلت|استشهد|استشهدت)(?![ء-ي])")


def find_verdict(folded: str, headword_end: int) -> dict:
    """Verbatim span from the first verdict term after the headword to the tabaqa clause / death verb / end."""
    match = _VERDICT.search(folded, headword_end)
    if not match:
        return {"verdict_text": None, "first_term": None}
    end = len(folded)
    for stopper in (_TABAQA.search(folded, match.start()), _DEATH_VERB.search(folded, match.start())):
        if stopper and stopper.start() < end:
            end = stopper.start()
    return {"verdict_text": folded[match.start():end].strip(" ،,.") or match.group(1), "first_term": match.group(1)}


# --- headword ----------------------------------------------------------------------------------------------------

GLOSS_TRIGGER = re.compile(
    r"^(بفتح|بضم|بكسر|بسكون|بالفتح|بالضم|بالكسر|بالتصغير|مصغر|مصغرا|بالنون|بالمعجمة|بالمهملة|بالمثلثة|بالموحدة|"
    r"بالمثناة|بالتحتانية|بالفاء|بالقاف|بالمد|بالقصر|بلفظ|بوزن|بكسرتين|بفتحتين|بضمتين|بالتثقيل|بالتخفيف|بالتشديد|"
    r"بمعجمة|بمهملة|بمثلثة|بموحدة|بمثناة|بنون|بفاء|بقاف|بزاي|براء|بالزاي|بالراء|بالجيم|بالحاء|بالخاء|بالدال|بالذال|"
    r"بالسين|بالشين|بالصاد|بالضاد|بالطاء|بالظاء|بالعين|بالغين|بالكاف|باللام|بالميم|بالهاء|بالواو|بالياء|بالالف|بتحتانية|"
    r"بفوقانية|بجيم|بحاء|بخاء|بدال|بذال|بسين|بشين|بصاد|بضاد|بطاء|بظاء|بعين|بغين|بكاف|بلام|بميم|بهاء|بواو|بياء|"
    r"بمعجمتين|بمهملتين|بموحدتين|بنونين|بمثناتين|بمثلثتين|بتحتانيتين|بالمعجمتين|بالمهملتين|بالنونين|بالموحدتين)$"
)
HEADWORD_STOP = {
    "مات", "ماتت", "توفي", "قتل", "استشهد", "يقال", "ويقال", "قيل", "وقيل", "هو", "وهو", "نزيل", "يكني", "يلقب",
    "المعروف", "المعروفة", "والد", "والدة", "اخو", "اخت", "مولي", "قاضي", "صاحب", "اصله", "نشا", "عن", "لم", "كان",
    "ثم", "او", "من", "سكن", "نزل", "روي", "قال", "وكان", "زوج", "ابن", "جد", "خال", "عم", "عمة", "ام", "امير",
    "واسم", "اسمه", "واسمه", "ويكني", "ويلقب", "يعرف", "ويعرف", "لقبه", "كنيته",
    "ولد", "شهد", "وفد", "ولي", "تابعي", "استشهد", "قدم", "حليف", "ادرك", "راي", "مشهور", "صاحب",
}


def nisba_places(tokens) -> set:
    """Place ids from nisba tokens only (ال...ي), so narrative city mentions in an over-long headword are ignored."""
    return arabic_places([t for t in tokens if t.startswith("ال") and t.endswith("ي")])
_HEADWORD_ALLOWED_AFTER_START = {"ابن", "ام"}  # nasab/kunya tokens are allowed inside a name, not as stoppers there


_LETTER_NAMES = (
    "الف باء تاء ثاء جيم حاء خاء دال ذال راء زاي سين شين صاد ضاد طاء ظاء عين غين فاء قاف كاف لام ميم نون هاء واو ياء"
).split()
GLOSS_VOCABULARY = set(_LETTER_NAMES) | {"ال" + letter for letter in _LETTER_NAMES} | {
    "فتح", "ضم", "كسر", "سكون", "تشديد", "تخفيف", "التشديد", "التخفيف", "ثم", "بعدها", "بعده", "بينهما", "قبلها",
    "اخره", "اوله", "ثانيه", "ثالثه", "اخرها", "ساكنة", "ساكنه", "مفتوحة", "مفتوحه", "مكسورة", "مكسوره", "مضمومة",
    "مضمومه", "مشددة", "مشدده", "مثقلة", "مثقله", "مخففة", "مخففه", "الثقيلة", "الثقيله", "الخفيفة", "الخفيفه",
    "المعجمة", "المعجمه", "المهملة", "المهمله", "المثناة", "المثناه", "المثلثة", "المثلثه", "الموحدة", "الموحده",
    "التحتانية", "التحتانيه", "الفوقانية", "الفوقانيه", "تحتانية", "تحتانيه", "فوقانية", "فوقانيه", "موحدة", "موحده",
    "مثناة", "مثناه", "مثلثة", "مثلثه", "معجمة", "معجمه", "مهملة", "مهمله", "تحت", "فوق", "من", "اخيرة", "الاخيرة",
    "مصغر", "مصغرا", "مكبر", "مكبرا", "ممدود", "مقصور", "المد", "القصر", "حرف", "مثله", "مثلها", "الاولي", "الثانية",
    "وتحتانية", "وموحدة", "ومثناة", "ومعجمة", "ومهملة", "الموحدتين", "المعجمتين", "المهملتين", "اوله", "واخره",
    "خفيفة", "خفيفه", "ثقيلة", "ثقيله", "مفتوحتين", "مضمومة", "الاولي", "الثانيه",
}
_GLOSS_STOP_TRIGGERS = {"بلفظ", "بوزن"}  # followed by an exemplar word, not by the rest of the name


def _is_gloss_word(token: str) -> bool:
    if GLOSS_TRIGGER.match(token) or token in GLOSS_VOCABULARY:
        return True
    return token.startswith("و") and (GLOSS_TRIGGER.match(token[1:]) is not None or token[1:] in GLOSS_VOCABULARY)


def headword_tokens(folded: str, skip_glosses: bool = True) -> list:
    """Name tokens at the start of an entry: stop at a verdict term, tabaqa clause or narrative word.

    Vocalization glosses (بفتح المثناة وسكون المعجمة) are skipped when `skip_glosses`, else they end the headword.
    'ابن' and 'ام' are allowed after the first token (nasab chain, woman's kunya); the canonical fold turns ابن into
    بن before keying.
    """
    tokens = folded.split()
    out: list = []
    verdict_starts = {term.split()[0] for term in VERDICT_TERMS}
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if not re.fullmatch(r"[ء-ي]+", token):
            break
        if token in _GLOSS_STOP_TRIGGERS:
            break
        if GLOSS_TRIGGER.match(token) or (out and token in ("اخره", "اوله", "واخره")):
            if not skip_glosses:
                break
            index += 1
            while index < len(tokens) and _is_gloss_word(tokens[index]):
                index += 1
            continue
        if token in verdict_starts:
            break
        if token in HEADWORD_STOP and not (token in _HEADWORD_ALLOWED_AFTER_START and out):
            if not (token == "ام" and not out):  # a woman's kunya may open the entry: ام سلمة
                break
        out.append(token)
        index += 1
    return out


_COMPOUND_HEADS = {"عبد", "ابو", "ابي", "ابا", "ام", "ذو", "ذي"}
_CONNECTORS = {"بن", "بنت"}


def name_chain(key_tokens: list) -> tuple:
    """Split a folded key into (ism-nasab chain, remaining tokens).

    The chain is the leading name unit followed by every 'بن/بنت + name unit'; a name unit is one token or a
    compound head plus one token (عبد الله, ابو بكر). 'X بن Y الكوفي ابو بكر' -> ('X بن Y', ['الكوفي','ابو','بكر']).
    """
    def unit(position: int) -> int:
        if position >= len(key_tokens):
            return position
        if position + 1 < len(key_tokens) and (key_tokens[position] in _COMPOUND_HEADS
                                               or key_tokens[position + 1] in ("الله", "الرحمن")):  # عبيد الله
            return position + 2
        return position + 1

    end = unit(0)
    while end < len(key_tokens) and key_tokens[end] in _CONNECTORS and end + 1 < len(key_tokens):
        end = unit(end + 1)
    return " ".join(key_tokens[:end]), key_tokens[end:]


# --- death statements --------------------------------------------------------------------------------------------

_ALT_SPLIT = re.compile(r"(?<![ء-ي])(وقيل|ويقال|او|وقيل في|وقيل بعد|وقيل قبل)(?![ء-ي])")
# Age and lifespan phrases end a date clause: 'وقد قارب المائة' / 'وعاش مائة وثلاثين سنة' are ages, not years.
_CLAUSE_END = (r"(?=(?<![ء-ي])(?:وله|وهو ابن|وهو بن|وقد (?:جاز|جاوز|قارب|بلغ|نيف)|وعاش|عاش|وكان|روي له|وروي|قال|وقال|"
               r"حدثنا|اخبرنا|وعمره|عن)(?![ء-ي])|[.:؛]|$)")
_DEATH_CLAUSE = re.compile(
    r"(?<![ء-ي])(مات|ماتت|توفي|توفيت|قتل|قتلت|استشهد|استشهدت)(?![ء-ي])(.*?)" + _CLAUSE_END
)
_BIRTH_CLAUSE = re.compile(r"(?<![ء-ي])(ولد|ولدت|مولده|مولدها)(?![ء-ي])(.*?)" + _CLAUSE_END)
# First word after the verb that keeps the entry's subject as the one who died/was born (else subject_may_differ).
_SUBJECT_SAFE_OPENERS = {"سنة", "سنه", "عام", "في", "بعد", "قبل", "قريبا", "نحو", "علي", "على", "يوم", "ليلة", "ليله",
                         "اول", "اخر", "حدود", "قديما", "شابا", "شهيدا", "ظلما", "صبرا", "وهو", "زمن", "مقتولا",
                         "معه", "مع", "هو", "قريب", "اواخر"}
_BOUND_WORDS = {"بعد": "lower_bound", "قبل": "upper_bound"}
_CIRCA_WORDS = ("في حدود", "قريبا من", "نحو", "قرابة", "حدود", "على راس", "علي راس", "في اول", "في اخر", "اواخر")
_EVENT_WORDS = ("في خلافة", "في خلافه", "في ولاية", "في ولايه", "في زمن", "في ايام", "في امارة", "في اماره", "يوم")


def _scan_alternative(segment: str) -> dict:
    """Parse one alternative of a death clause: qualifier, number parts, or an event reference."""
    tokens = re.sub(r"[^\sء-ي]", " ", segment).split()  # punctuation and footnote digits are not words
    qualifier = None
    for index, token in enumerate(tokens):
        stripped = token[1:] if token.startswith("و") and token[1:] in _BOUND_WORDS else token
        if stripped in _BOUND_WORDS and qualifier is None:
            qualifier = _BOUND_WORDS[stripped]
        if token in DEFINITE_TENS:  # بعد الاربعين / قبل المائة
            value = DEFINITE_TENS[token]
            parts = {"units": None, "tens": value if value < 100 else None, "teen": False,
                     "hundreds": value if value >= 100 else None}
            following, consumed = parse_number_words(tokens[index + 1:])
            if consumed and following["hundreds"]:
                parts["hundreds"] = following["hundreds"]
            return {"parts": parts, "qualifier": qualifier, "definite": True}
        if token in ("سنة", "سنه", "عام"):
            parts, consumed = parse_number_words(tokens[index + 1:])
            if consumed:
                return {"parts": parts, "qualifier": qualifier, "definite": False}
        bare_parts, bare_consumed = parse_number_words(tokens[index:])
        if bare_consumed and index > 0:  # elided 'سنة' inside an alternative: 'وقيل ثلاث وتسعين'
            return {"parts": bare_parts, "qualifier": qualifier, "definite": False}
        if bare_consumed and index == 0:
            return {"parts": bare_parts, "qualifier": qualifier, "definite": False}
    return {"parts": None, "qualifier": qualifier, "definite": False}


def century_by_taqrib_convention(tabaqa) -> int | None:
    """Ibn Hajar's literal rule (Taqrib introduction): tabaqat 1-2 die before 100, 3-8 after 100, 9-12 after 200."""
    if tabaqa is None:
        return None
    if tabaqa <= 2:
        return 0
    if tabaqa <= 8:
        return 100
    return 200


# Median death year (AH) per tabaqa, hadith-kg `rawis` rows with a single death year (n = 157 to 958 per tabaqa;
# measured 2026-11-21, see README). Used only to pick the omitted century nearest the tabaqa's era.
TABAQA_MEDIAN_DEATH = {1: 48, 2: 77, 3: 100, 4: 121, 5: 132, 6: 136, 7: 162, 8: 188, 9: 214, 10: 241, 11: 267, 12: 292}


def infer_century(tabaqa, years_within_century: int) -> tuple:
    """(century, flag) for a year written without its hundreds. The century whose result lies nearest the tabaqa's
    median death year is chosen; the flag says whether that equals Ibn Hajar's literal rule. At the rule's
    boundaries (a 9th-tabaqa man 'died in 99' died in 199, not 299) the literal reading is wrong."""
    if tabaqa is None or tabaqa not in TABAQA_MEDIAN_DEATH:
        return None, None
    median = TABAQA_MEDIAN_DEATH[tabaqa]
    century = min((0, 100, 200, 300), key=lambda c: abs(c + years_within_century - median))
    literal = century_by_taqrib_convention(tabaqa)
    return century, ("century_by_author_convention" if century == literal else "century_by_tabaqa_era_not_literal_rule")


def parse_death_statements(folded: str, tabaqa=None, use_taqrib_century: bool = False) -> list:
    """Every death clause; see parse_year_statements."""
    return parse_year_statements(folded, "death", tabaqa, use_taqrib_century)


def parse_year_statements(folded: str, kind: str = "death", tabaqa=None, use_taqrib_century: bool = False) -> list:
    """Every death (or birth) clause, split into alternatives; each keeps its verbatim words and qualifiers.

    Elision: 'سنة احدي او اثنتين وعشرين' = 21 or 22; an earlier units-only alternative inherits the tens and
    hundreds of the next alternative that states them (flag elided_part_inherited). A missing century is taken
    from Ibn Hajar's stated convention only when `use_taqrib_century` (flag century_by_author_convention).
    A clause whose first word is not a date/place opener is flagged subject_may_differ ('مات ابوه سنة ...').
    """
    pattern = _DEATH_CLAUSE if kind == "death" else _BIRTH_CLAUSE
    results = []
    for clause_index, clause in enumerate(pattern.finditer(folded)):
        body = clause.group(2).strip()
        verbatim = (clause.group(1) + " " + body).strip()
        opener = body.split()[0] if body.split() else ""
        subject_flag = [] if (opener in _SUBJECT_SAFE_OPENERS or opener.startswith("ب")) else ["subject_may_differ"]
        start_count = len(results)
        pieces = _ALT_SPLIT.split(body)
        alternatives = [pieces[0]]
        markers = [None]
        for marker, text in zip(pieces[1::2], pieces[2::2]):
            alternatives.append(text)
            markers.append(marker)
        scanned = [_scan_alternative(text) for text in alternatives]
        for alt_index, (text, marker, scan) in enumerate(zip(alternatives, markers, scanned)):
            flags = []
            text_stripped = text.strip()
            if alt_index > 0 and marker in ("او",) and not text_stripped:
                continue
            parts = scan["parts"]
            qualifier = scan["qualifier"]
            if parts is None:
                if alt_index > 0 and text_stripped.split()[:1] in (["قبلها"], ["بعدها"], ["قبل", "ذلك"]):
                    reference = results[-1] if results else None
                    if reference and reference.get("year_min") is not None:
                        bound = "upper_bound" if text_stripped.startswith("قبل") else "lower_bound"
                        results.append(_row(clause_index, alt_index, verbatim, text_stripped, marker, bound,
                                            reference["year_min"] if bound == "lower_bound" else None,
                                            reference["year_max"] if bound == "upper_bound" else None,
                                            ["relative_to_previous_alternative"]))
                    continue
                if alt_index == 0:
                    precision = "event_reference" if any(w in text_stripped for w in _EVENT_WORDS) else "no_year_stated"
                    results.append(_row(clause_index, alt_index, verbatim, text_stripped, marker, precision, None,
                                        None, []))
                continue
            parts = dict(parts)
            if parts["tens"] is None and not parts["teen"] and parts["hundreds"] is None and parts["units"]:
                for later in scanned[alt_index + 1:]:
                    later_parts = later["parts"]
                    if later_parts and (later_parts["tens"] or later_parts["teen"] or later_parts["hundreds"]):
                        parts["tens"] = later_parts["tens"]
                        parts["teen"] = later_parts["teen"]
                        parts["hundreds"] = later_parts["hundreds"]
                        flags.append("elided_part_inherited")
                        break
                else:  # 'سنة ست وتسعين وقيل سنة سبع' = 96 or 97: the tens come from the earlier alternative
                    for earlier in reversed(scanned[:alt_index]):
                        earlier_parts = earlier["parts"]
                        if earlier_parts and (earlier_parts["tens"] or earlier_parts["teen"]):
                            parts["tens"] = earlier_parts["tens"]
                            parts["teen"] = earlier_parts["teen"]
                            parts["hundreds"] = parts["hundreds"] or earlier_parts["hundreds"]
                            flags.append("elided_part_inherited_from_earlier")
                            break
            if parts["hundreds"] is None:
                later_hundreds = next((s["parts"]["hundreds"] for s in scanned[alt_index + 1:]
                                       if s["parts"] and s["parts"]["hundreds"]), None)
                earlier_hundreds = next((s["parts"]["hundreds"] for s in reversed(scanned[:alt_index])
                                         if s["parts"] and s["parts"]["hundreds"]), None)
                if later_hundreds or earlier_hundreds:
                    parts["hundreds"] = later_hundreds or earlier_hundreds
                    flags.append("elided_century_inherited")
            low, high = parts_to_range(parts)
            if parts["hundreds"] is None:
                century, century_flag = infer_century(tabaqa, low) if use_taqrib_century else (None, None)
                if century is None:
                    results.append(_row(clause_index, alt_index, verbatim, text_stripped, marker,
                                        "century_not_stated", None, None, flags + ["year_within_century_only"],
                                        within_century=(low, high)))
                    continue
                flags.append(century_flag)
                low, high = low + century, high + century
            precision = qualifier or ("range" if low != high else "exact")
            if any(word in text_stripped for word in _CIRCA_WORDS) and precision == "exact":
                precision = "circa"
            if marker in ("وقيل", "ويقال", "وقيل في", "وقيل بعد", "وقيل قبل"):
                flags.append("it_is_said")
            if marker == "او":
                flags.append("or_alternative")
            year_min = None if precision == "upper_bound" else low
            year_max = None if precision == "lower_bound" else high
            results.append(_row(clause_index, alt_index, verbatim, text_stripped, marker, precision, year_min,
                                year_max, flags))
        for row in results[start_count:]:
            row["flags"] = row["flags"] + subject_flag
    return results


def _row(clause_index, alt_index, verbatim, text, marker, precision, year_min, year_max, flags, within_century=None):
    row = {"clause": clause_index, "alternative": alt_index, "clause_verbatim": verbatim,
           "alternative_verbatim": text, "alternative_marker": marker, "precision": precision,
           "year_min": year_min, "year_max": year_max, "flags": flags}
    if within_century is not None:
        row["within_century"] = list(within_century)
    return row


# --- places ------------------------------------------------------------------------------------------------------

# place id: (English spellings used by the lexicon, Arabic city forms, Arabic nisba forms), Arabic in folded form.
GAZETTEER = {
    "medina": (("medina", "medinah", "madinah", "al-medina", "madina", "medianh", "al-madinah"), ("المدينة",), ("المدني", "المديني")),
    "makkah": (("makkah", "mecca", "makka", "al-makkah"), ("مكة",), ("المكي",)),
    "taif": (("al-ta'if", "taif", "ta'if", "al-taif"), ("الطائف",), ("الطائفي",)),
    "basra": (("al-basra", "basra", "basrah", "al-basrah"), ("البصرة",), ("البصري",)),
    "kufa": (("kufa", "al-kufa", "kufah", "al-kufah"), ("الكوفة",), ("الكوفي",)),
    "baghdad": (("baghdad", "al-baghdad"), ("بغداد",), ("البغدادي",)),
    "wasit": (("al-wasit", "wasit"), ("واسط",), ("الواسطي",)),
    "madain": (("mada'in", "al-mada'in"), ("المدائن",), ("المدائني",)),
    "egypt": (("egypt", "misr"), ("مصر",), ("المصري",)),
    "alexandria": (("alexandria",), ("الاسكندرية",), ("الاسكندراني", "الاسكندري")),
    "syria": (("syria", "al-syria", "sham", "al-sham"), ("الشام",), ("الشامي",)),
    "damascus": (("damascus", "damasus", "damascus, syria"), ("دمشق",), ("الدمشقي",)),
    "hims": (("al-hims", "hims", "homs"), ("حمص",), ("الحمصي",)),
    "ramla": (("al-ramla", "ramla"), ("الرملة",), ("الرملي",)),
    "antioch": (("antioch",), ("انطاكية",), ("الانطاكي",)),
    "asqalan": (("'asqalan", "asqalan"), ("عسقلان",), ("العسقلاني",)),
    "palestine": (("palestine",), ("فلسطين",), ("الفلسطيني",)),
    "jordan": (("jordon", "jordan"), ("الاردن",), ("الاردني",)),
    "beirut": (("beruit", "beirut"), ("بيروت",), ("البيروتي",)),
    "jerusalem": (("jerusalem",), ("بيت المقدس", "القدس", "ايلياء"), ("المقدسي",)),
    "tarsus": (("tursus", "tarsus"), ("طرسوس",), ("الطرسوسي",)),
    "massisa": (("musaysa", "al-musaysa"), ("المصيصة",), ("المصيصي",)),
    "thughur": (("al-thaghar",), ("الثغر",), ("الثغري",)),
    "jazira": (("jazira",), ("الجزيرة",), ("الجزري",)),
    "harran": (("hiran", "harran"), ("حران",), ("الحراني",)),
    "raqqa": (("al-raqqa", "raqqa"), ("الرقة",), ("الرقي",)),
    "ruha": (("raha", "ruha", "al-ruha"), ("الرها",), ("الرهاوي",)),
    "mosul": (("musal", "mosul"), ("الموصل",), ("الموصلي",)),
    "yemen": (("yemen",), ("اليمن",), ("اليماني", "اليمني")),
    "sanaa": (("sana'",), ("صنعاء",), ("الصنعاني",)),
    "yamama": (("al-yamama", "yamama"), ("اليمامة",), ("اليمامي",)),
    "bahrain": (("bahrain",), ("البحرين",), ("البحراني",)),
    "hijaz": (("hijaz", "al-hijaz"), ("الحجاز",), ("الحجازي",)),
    "najd": (("nejd", "najd"), ("نجد",), ("النجدي",)),
    "iraq": (("iraq",), ("العراق",), ("العراقي",)),
    "khurasan": (("khurasan",), ("خراسان",), ("الخراساني",)),
    "merv": (("merv", "marw"), ("مرو",), ("المروزي",)),
    "balkh": (("bulkh", "balkh"), ("بلخ",), ("البلخي",)),
    "nishapur": (("nisapur", "nishapur"), ("نيسابور",), ("النيسابوري",)),
    "nasa": (("nisa'",), ("نسا",), ()),  # النسائي is the compiler's nisba in running text
    "herat": (("herat",), ("هراة",), ("الهروي",)),
    "rayy": (("al-ray", "ray'", "al-ray'", "rayy"), ("الري",), ("الرازي",)),
    "hamadhan": (("hamadan",), ("همذان",), ("الهمذاني",)),  # الهمداني (Yemeni tribe) deliberately not mapped
    "isfahan": (("asbahan", "isfahan"), ("اصبهان", "اصفهان"), ("الاصبهاني", "الاصفهاني")),
    "samarqand": (("samarqand",), ("سمرقند",), ("السمرقندي",)),
    "bukhara": (("bukhara",), ("بخاري",), ()),  # البخاري is the compiler's nisba in running text
    "sijistan": (("sajistan", "sijistan"), ("سجستان",), ("السجستاني",)),
    "persia": (("persia", "iran"), ("فارس",), ()),
    "abyssinia": (("abyssinia",), ("الحبشة",), ("الحبشي",)),
    "africa": (("africa",), ("افريقية",), ("الافريقي",)),
}
# Region containment, used only to label a comparison 'consistent_by_region' (never 'agree').
REGIONS = {
    "hijaz": {"medina", "makkah", "taif"},
    "iraq": {"kufa", "basra", "baghdad", "wasit", "madain"},
    "syria": {"damascus", "hims", "ramla", "antioch", "asqalan", "palestine", "jordan", "beirut", "jerusalem",
              "tarsus", "massisa", "thughur"},
    "jazira": {"harran", "raqqa", "mosul", "ruha"},
    "yemen": {"sanaa"},
    "egypt": {"alexandria"},
    "khurasan": {"merv", "balkh", "nishapur", "herat", "nasa"},
}
_ENGLISH_TO_PLACE = {spelling: place for place, (spellings, _, _) in GAZETTEER.items() for spelling in spellings}
_ARABIC_TO_PLACE = {}
for _place, (_, _cities, _nisbas) in GAZETTEER.items():
    for _form in _cities + _nisbas:
        _ARABIC_TO_PLACE[fold_for_phrases(_form)] = _place
        _ARABIC_TO_PLACE["ب" + fold_for_phrases(_form)] = _place  # بالكوفة, بمكة


def english_places(value: str) -> tuple:
    """(place ids, unmapped parts) for a lexicon place cell such as 'Medina/al-Ta'if' or 'Hijaz, Uhud'."""
    places, unmapped = set(), []
    for part in re.split(r"[/,]", value or ""):
        part = part.strip().lower()
        if not part:
            continue
        place = _ENGLISH_TO_PLACE.get(part)
        if place:
            places.add(place)
        else:
            unmapped.append(part)
    return places, unmapped


def arabic_places(tokens) -> set:
    """Place ids for folded Arabic tokens (city names, ب-prefixed city names, nisbas); two-word names too."""
    tokens = list(tokens)
    found = set()
    for index, token in enumerate(tokens):
        if token in _ARABIC_TO_PLACE:
            found.add(_ARABIC_TO_PLACE[token])
        if index + 1 < len(tokens) and (token + " " + tokens[index + 1]) in _ARABIC_TO_PLACE:
            found.add(_ARABIC_TO_PLACE[token + " " + tokens[index + 1]])
    return found


def compare_place_sets(lexicon: set, source: set) -> str:
    """agree / consistent_by_region / differ / lexicon_only / source_only / neither."""
    if not lexicon and not source:
        return "neither"
    if not source:
        return "lexicon_only"
    if not lexicon:
        return "source_only"
    if lexicon & source:
        return "agree"
    for region, members in REGIONS.items():
        if (region in lexicon and members & source) or (region in source and members & lexicon):
            return "consistent_by_region"
    return "differ"


_RESIDENCE = re.compile(r"(?<![ء-ي])(نزيل|نزل|سكن)\s+((?:[ء-ي]+\s*){1,3})")


def residence_phrases(folded: str) -> list:
    """'نزيل X' / 'سكن X' phrases with their place ids (explicit residence wording)."""
    out = []
    for match in _RESIDENCE.finditer(folded):
        words = match.group(2).split()
        # one word, or two when they form a known place name (بيت المقدس); never the following verdict word
        place_words = words[:2] if len(words) > 1 and " ".join(words[:2]) in _ARABIC_TO_PLACE else words[:1]
        out.append({"verbatim": (match.group(1) + " " + " ".join(place_words)).strip(),
                    "places": sorted(arabic_places(place_words))})
    return out


# --- Mizzi heading -----------------------------------------------------------------------------------------------

_MIZZI_PREFIX = re.compile(r"^\s*-?\s*(?:\(?تمييز\)?\s*(?:وأما|واما)?\s*:?\s*)?(?:[ء-ي ]{1,16}:\s*)?(?:\(?تمييز\)?\s*:?\s*)?")
_FOOTNOTE = re.compile(r"\(\s*\d+\s*\)")


def mizzi_heading(display: str) -> str:
    """First sentence of a Tahdhib al-Kamal entry, sigla prefix, تمييز marker and footnote numbers removed."""
    heading = _FOOTNOTE.sub(" ", display)
    heading = _MIZZI_PREFIX.sub("", heading, count=1)
    heading = re.split(r"[.]", heading, maxsplit=1)[0]
    return " ".join(heading.split())
