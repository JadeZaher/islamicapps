"""Pure extraction for the author-rooted rijal layer: verdict terms per author, Imams, teachers/students, books,
Kashshi sections, link evidence. Standard library only; no I/O. Rules and limits: README.md in this directory.

Extends (imports, never copies) `diagnostics/biography-verification/rijal_parsing.py`.
"""

import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "diagnostics" / "biography-verification"))
sys.path.insert(0, str(_HERE.parent / "reconciled"))
import rijal_parsing as rp  # noqa: E402
from external_source_logic import external_name_placeholder  # noqa: E402,F401  (re-exported for callers)

_LETTER = r"[ء-ي]"
_NOT_LETTER_BEFORE = r"(?<![ء-ي])"
_NOT_LETTER_AFTER = r"(?![ء-ي])"


def phrase_fold(text: str) -> str:
    """rp.fold_for_phrases plus the Persian ya/kaf letters (Thaqalayn surfaces write أبی)."""
    return rp.fold_for_phrases((text or "").replace("ی", "ي").replace("ک", "ك"))


def fold_with_offsets(text: str) -> tuple:
    """(folded, offsets): the same string `phrase_fold` gives, plus the source index of every folded char."""
    out, offsets = [], []
    pending_space = False
    for index, char in enumerate(text or ""):
        if char.isspace():
            pending_space = bool(out)
            continue
        folded = rp.fold_for_phrases(char.replace("ی", "ي").replace("ک", "ك"))
        if not folded:
            continue
        if pending_space:
            out.append(" ")
            offsets.append(index - 1)
            pending_space = False
        for piece in folded:
            out.append(piece)
            offsets.append(index)
    return "".join(out), offsets


def verbatim_span(text: str, offsets: list, start: int, end: int) -> str:
    """Original characters behind folded[start:end], trailing vocalization of the last letter included."""
    if start >= end or not offsets:
        return ""
    first, last = offsets[start], offsets[end - 1] + 1
    while last < len(text) and rp._DIACRITICS.match(text[last]):
        last += 1
    return text[first:last]


# --- verdict terms, per author scheme ----------------------------------------------------------------------------

# Imami rijal vocabulary (al-Najashi, al-Tusi, al-Kashshi). term id -> folded patterns, longest first at match time.
# Ids name the WORDS, not a normalised grade: 'thiqa' means the word ثقة is written there.
IMAMI_TERMS = {
    "thiqa_thiqa": ["ثقة ثقة"],
    "thiqa_ayn": ["ثقة عين", "ثقة عينا"],
    "thiqa_fi_al_hadith": ["ثقة في الحديث", "ثقة في حديثه", "ثقة في روايته"],
    "thiqa": ["ثقة", "ثقه"],
    "thiqat_plural": ["ثقات"],
    "jalil": ["جليل القدر", "جليل", "جليلا"],
    "wajh": ["وجه من وجوه", "وجها من وجوه", "وجه اصحابنا", "وجه في اصحابنا", "وجها في اصحابنا"],
    "ayn": ["عين من عيون", "عينا من عيون"],
    "shaykh_ashabina": ["شيخ من اصحابنا", "شيخ اصحابنا", "شيخ الطائفة"],
    "sahih_al_hadith": ["صحيح الحديث", "صحيح الرواية"],
    "naqi_al_hadith": ["نقي الحديث"],
    "la_basa_bihi": ["لا باس به"],
    "mamduh": ["ممدوح"],
    "daif_jiddan": ["ضعيف جدا"],
    "daif_fi_al_hadith": ["ضعيف في الحديث"],
    "daif": ["ضعيف", "ضعيفا"],
    "mudtarib": ["مضطرب الحديث", "مضطرب الرواية", "مضطرب"],
    "majhul": ["مجهول"],
    "ghali": ["غال", "غاليا", "من الغلاة", "يرمي بالغلو", "في مذهبه غلو"],
    "waqifi": ["واقفي", "واقفيا", "من الواقفة", "وقف علي"],
    "fathi": ["فطحي", "فطحيا", "من الفطحية"],
    "ammi": ["عامي المذهب", "عامي", "عاميا"],
    "zaydi": ["زيدي", "زيديا"],
    "fasid_al_madhhab": ["فاسد المذهب"],
    "murtafi_al_qawl": ["مرتفع القول"],
    "yuraf_wa_yunkar": ["يعرف وينكر", "يعرف حديثه وينكر"],
    "mukhallit": ["مختلط الامر", "مختلط", "مخلط"],
    "kadhdhab": ["كذاب", "كذابا"],
    "muttaham": ["متهم"],
    "imami_al_madhhab": ["امامي المذهب"],
    "min_ashabina": ["من اصحابنا"],
    "asnada_anhu": ["اسند عنه"],
    "laysa_bi_dhaka": ["ليس بذاك", "ليس بذلك"],
}

# Sunni critics' vocabulary as Ibn Hajar lists it (rp.VERDICT_TERMS); used for al-Mizzi's reported statements.
SUNNI_TERM_IDS = {
    "ثقة ثقة": "thiqa_thiqa", "ثقة ثبت": "thiqa_thabt", "ثقة حافظ": "thiqa_hafiz", "ثقة": "thiqa", "ثبت": "thabt",
    "حافظ": "hafiz", "حجة": "hujja", "امام": "imam", "متقن": "mutqin", "صدوق": "saduq", "لا باس به": "la_basa_bihi",
    "ليس به باس": "laysa_bihi_bas", "مقبول": "maqbul", "لين الحديث": "layyin_al_hadith", "فيه لين": "fihi_lin",
    "لين": "layyin", "مستور": "mastur", "مجهول الحال": "majhul_al_hal", "مجهول": "majhul", "لا يعرف": "la_yuraf",
    "ضعيف": "daif", "متروك": "matruk", "منكر الحديث": "munkar_al_hadith", "واهي الحديث": "wahi_al_hadith",
    "واه": "wah", "ساقط": "saqit", "متهم": "muttaham", "كذاب": "kadhdhab", "كذبوه": "kadhdhabuhu", "وضاع": "waddaa",
    "صحابي": "sahabi", "صحابية": "sahabiyya", "صحابيه": "sahabiyya", "له صحبة": "lahu_suhba", "له صحبه": "lahu_suhba",
    "لها صحبة": "laha_suhba", "له رؤية": "lahu_ruya", "له رؤيه": "lahu_ruya",
}
SUNNI_TERMS: dict = {}
for _term in rp.VERDICT_TERMS:  # Ibn Hajar's vocabulary as the existing parser defines it; ids are labels only
    SUNNI_TERMS.setdefault(SUNNI_TERM_IDS.get(_term, re.sub(r"\s+", "_", _term)), []).append(_term)
COMPANION_TERM_IDS = {"sahabi", "sahabiyya", "lahu_suhba", "laha_suhba", "lahu_ruya"}

NEGATORS = ("ليس", "ليست", "غير", "لم يكن", "ما كان", "لا يكون", "ليسا", "ليسوا")
# A preceding word that makes the clause a report or hearsay, not the author's own statement.
HEARSAY = ("قيل", "وقيل", "يقال", "ويقال", "ذكر", "وذكر", "زعم", "وزعم", "قالوا", "يزعمون", "ذكروا", "يذكر", "رمي",
           "ورمي", "يرمي", "ضعفه", "ضعفوه", "غمز", "غمزوا", "ذكره", "وذكره")
# A kinship or other-person word before the term in the same clause: the term may describe someone else.
OTHER_SUBJECT = ("ابوه", "وابوه", "اخوه", "واخوه", "ابنه", "وابنه", "جده", "وجده", "عمه", "وعمه", "ابناه", "اخواه",
                 "اخوته", "واخوته", "ولده", "وولده", "بنوه", "وبنوه", "خاله", "ابن عمه", "ابوهم", "اهل بيته",
                 "ابنا", "وابنا", "اخواه", "ابيه", "اخيه", "صاحبه")
GROUP_LEADS = {"عدة", "عده", "جماعة", "جماعه", "بعض", "رجل", "احد", "واحد", "كثيرا", "كثير", "شيوخ", "عن", "جميع",
               "مشايخ", "اصحاب", "قوم", "نفر", "غير", "رجال", "عامة", "اكثر", "لبعض", "وعدة", "وجماعة"}
_SPEAKER = re.compile(_NOT_LETTER_BEFORE + r"و?قال\s+([^:،.]{2,70}?)\s*:")


def _term_regex(vocabulary: dict) -> re.Pattern:
    alternatives = sorted(((pattern, term_id) for term_id, patterns in vocabulary.items() for pattern in patterns),
                          key=lambda item: -len(item[0]))
    body = "|".join(f"(?P<t{index}>{re.escape(pattern)})" for index, (pattern, _) in enumerate(alternatives))
    # optional proclitic: و (and), ب (after ليس: ليس بثقة), ف, ل
    return re.compile(_NOT_LETTER_BEFORE + r"(?P<proclitic>[وبفل]?)(?:" + body + ")" + _NOT_LETTER_AFTER), \
        [term_id for _, term_id in alternatives]


_IMAMI_RE, _IMAMI_IDS = _term_regex(IMAMI_TERMS)
_SUNNI_RE, _SUNNI_IDS = _term_regex(SUNNI_TERMS)


_CLAUSE_MARKS = ("،", ".", ":", "؛", ",")


def _clause_before(folded: str, position: int) -> str:
    """The clause before `position`, back to the last clause mark. A clause opened by 'إنه/أن' or following a
    colon reaches back over that mark (يقال: إنه كان فطحيا), so the reporting verb stays in view."""
    start = max(folded.rfind(mark, 0, position) for mark in _CLAUSE_MARKS)
    clause = folded[start + 1:position]
    first = clause.split()[:1]
    if start > 0 and (folded[start] == ":" or first and first[0] in ("انه", "انها", "ان", "بانه", "بان", "لانه")):
        previous = max(folded.rfind(mark, 0, start) for mark in _CLAUSE_MARKS)
        clause = folded[previous + 1:position]
    return clause


def find_terms(text: str, scheme: str, vocabulary: str = "imami", skip_spans: tuple = ()) -> list:
    """Every verdict-vocabulary occurrence in `text`, as written, with flags; nothing is normalised to a grade.

    flags: negated (ليس بثقة), hearsay_or_reported (قيل: ضعيف), subject_may_differ (أخوه ثقة), speaker_quoted.
    A term with any of the first three flags is never a verdict on the entry's subject (`is_verdict_on_subject`).
    """
    regex, ids = (_IMAMI_RE, _IMAMI_IDS) if vocabulary == "imami" else (_SUNNI_RE, _SUNNI_IDS)
    folded, offsets = fold_with_offsets(text)
    rows = []
    for match in regex.finditer(folded):
        if any(start <= match.start() < end for start, end in skip_spans):
            continue
        group = next(name for name, value in match.groupdict().items() if value and name.startswith("t"))
        term_id = ids[int(group[1:])]
        clause = _clause_before(folded, match.start())
        clause_tokens = clause.split()
        flags = []
        tail = " ".join(clause_tokens[-3:])
        if any(re.search(_NOT_LETTER_BEFORE + re.escape(neg) + _NOT_LETTER_AFTER, tail) for neg in NEGATORS) \
                or (match.group("proclitic") == "ب" and clause_tokens and clause_tokens[-1] in ("ليس", "ليست")):
            flags.append("negated")
        elif match.group("proclitic") == "ب":
            continue  # بثقة without a negator is not a term use (e.g. بثقة من = 'with a trusted man')
        if term_id in ("min_ashabina", "shaykh_ashabina") and clause_tokens and clause_tokens[-1] in GROUP_LEADS:
            continue  # 'عدة من أصحابنا' / 'عن شيخ من أصحابنا' name transmitters in a route, not a description
        if any(token in HEARSAY for token in clause_tokens):
            flags.append("hearsay_or_reported")
        if any(re.search(_NOT_LETTER_BEFORE + re.escape(word) + _NOT_LETTER_AFTER, clause) for word in OTHER_SUBJECT):
            flags.append("subject_may_differ")
        speaker = None
        for speaker_match in _SPEAKER.finditer(folded, 0, match.start()):
            speaker = speaker_match.group(1).strip()
        if speaker:
            flags.append("speaker_quoted")
        start = match.start() + len(match.group("proclitic"))
        rows.append({
            "scheme": scheme, "term_id": term_id,
            "term_verbatim": verbatim_span(text, offsets, start, match.end()),
            "clause_verbatim": verbatim_span(text, offsets, max(0, match.start() - len(clause)),
                                             min(len(folded), match.end() + 40)).strip(" ،,."),
            "speaker_verbatim": speaker, "flags": flags,
            "is_verdict_on_subject": not ({"negated", "hearsay_or_reported", "subject_may_differ"} & set(flags)),
            "folded_offset": match.start(),
        })
    return rows


# --- Imams -------------------------------------------------------------------------------------------------------

IMAMS = ("prophet", "ali", "hasan", "husayn", "sajjad", "baqir", "sadiq", "kazim", "rida", "jawad", "hadi", "askari",
         "qaim")
# Readings that need no honorific and no position: the name or title is the Imam's alone.
_IMAM_EXPLICIT = {
    "prophet": ["رسول الله", "النبي", "نبي الله"],
    "ali": ["امير المؤمنين", "امير المومنين", "علي بن ابي طالب", "علي بن ابي طالب امير المؤمنين"],
    "hasan": ["الحسن بن علي بن ابي طالب", "الحسن المجتبي"],
    "husayn": ["الحسين بن علي بن ابي طالب", "ابي عبد الله الحسين", "ابي عبد الله الحسين بن علي", "سيد الشهداء"],
    "sajjad": ["زين العابدين", "علي بن الحسين زين العابدين", "السجاد", "ابي محمد علي بن الحسين"],
    "baqir": ["الباقر", "ابي جعفر الباقر", "ابي جعفر محمد بن علي الباقر", "محمد بن علي الباقر",
              "ابي جعفر محمد بن علي بن الحسين", "ابي جعفر الاول"],
    "sadiq": ["الصادق", "ابي عبد الله الصادق", "ابي عبد الله جعفر بن محمد", "ابي عبد الله جعفر بن محمد الصادق",
              "الصادق جعفر بن محمد", "جعفر بن محمد الصادق", "ابي عبد الله جعفر"],
    "kazim": ["الكاظم", "ابي الحسن الاول", "ابي ابراهيم", "العبد الصالح", "ابي الحسن موسي", "ابي الحسن موسي بن جعفر",
              "موسي بن جعفر الكاظم", "ابي الحسن الماضي"],
    "rida": ["الرضا", "ابي الحسن الرضا", "علي بن موسي الرضا", "ابي الحسن الثاني", "ابي الحسن علي بن موسي الرضا",
             "ابي الحسن علي بن موسي"],
    "jawad": ["الجواد", "ابي جعفر الثاني", "ابي جعفر محمد بن علي الثاني", "محمد بن علي الثاني", "ابي جعفر الجواد"],
    "hadi": ["الهادي", "ابي الحسن الثالث", "ابي الحسن العسكري", "علي بن محمد الهادي", "ابي الحسن علي بن محمد"],
    "askari": ["ابي محمد العسكري", "الحسن بن علي العسكري", "ابي محمد الحسن العسكري", "ابي محمد الحسن بن علي"],
    "qaim": ["صاحب الزمان", "القائم", "صاحب الامر"],
}
# Readings that name an Imam only with an honorific marker or by convention (chain end, rijal 'روى عن' clause);
# several are shared by more than one Imam and stay a set.
_IMAM_CONDITIONAL = {
    "ابي عبد الله": ("sadiq", "husayn"), "جعفر بن محمد": ("sadiq",), "ابي جعفر": ("baqir", "jawad"),
    "محمد بن علي": ("baqir", "jawad"), "ابي الحسن": ("ali", "kazim", "rida", "hadi"),
    "ابي محمد": ("hasan", "sajjad", "askari"), "علي بن الحسين": ("sajjad",), "علي": ("ali",),
    "الحسن بن علي": ("hasan", "askari"), "الحسين بن علي": ("husayn",), "الحسين": ("husayn",), "الحسن": ("hasan",),
    "موسي بن جعفر": ("kazim",), "علي بن موسي": ("rida",), "علي بن محمد": ("hadi",), "احدهما": ("baqir", "sadiq"),
    "العسكري": ("hadi", "askari"), "الحجة": ("qaim",), "ابي الحسن موسي بن جعفر": ("kazim",),
}
_HONORIFIC = re.compile(r"(?:عليه|عليها|عليهما|عليهم)\s*(?:ال)?سلام|صلي الله عليه|صلوات الله|(?<![ء-ي])[عص](?![ء-ي])|\(ع\)")
_HONORIFIC_STRIP = re.compile(r"(?:عليه|عليها|عليهما|عليهم)\s*(?:ال)?سلام|صلي الله عليه(?:\s*و\s*اله)?(?:\s*وسلم)?|"
                              r"صلوات الله عليه(?:م)?|(?<![ء-ي])(?:ع|ص|عج)(?![ء-ي])|[()]")
_TRAILING_NOISE = re.compile(r"\s(?:في|قال|انه|ان|يقول|قالا|انهما|حين|وهو)(?:\s.*)?$")


def _imam_key(surface: str) -> str:
    text = phrase_fold(surface)
    text = _HONORIFIC_STRIP.sub(" ", text)
    text = re.sub(r"[^\sء-ي]", " ", text)
    tokens = text.split()
    while tokens and tokens[0] in ("و", "عن", "سمعت", "سالت", "قال"):
        tokens = tokens[1:]
    if tokens and tokens[0].startswith("و") and len(tokens[0]) > 3 and tokens[0][1:3] == "اب":
        tokens[0] = tokens[0][1:]
    tokens = ["ابي" if token in ("ابا", "ابو") else token for token in tokens]
    return _TRAILING_NOISE.sub("", " ".join(tokens))


_EXPLICIT_LOOKUP = {}
for _imam, _forms in _IMAM_EXPLICIT.items():
    for _form in _forms:
        _EXPLICIT_LOOKUP.setdefault(_form, set()).add(_imam)


def imam_reading(surface: str, at_chain_end: bool = False, rijal_clause: bool = False) -> dict | None:
    """Which Imam(s) a name may denote, and on what basis; None when it is not an Imam reading.

    basis: explicit_name (title or full name), honorific_marker (a shared kunya/name written with عليه السلام or ع),
    conventional_kunya_at_chain_end (Imami chain convention), conventional_kunya_in_rijal_clause ('روى عن أبي عبد
    الله' in an Imami rijal entry). `imams` is a set when the reading is shared (أبي الحسن: four Imams).
    """
    key = _imam_key(surface)
    if not key:
        return None
    if key in _EXPLICIT_LOOKUP:
        return {"imams": sorted(_EXPLICIT_LOOKUP[key], key=IMAMS.index), "basis": "explicit_name", "key": key}
    if key in _IMAM_CONDITIONAL:
        imams = sorted(_IMAM_CONDITIONAL[key], key=IMAMS.index)
        if _HONORIFIC.search(phrase_fold(surface)):
            return {"imams": imams, "basis": "honorific_marker", "key": key}
        if at_chain_end and key not in ("علي", "الحسن", "الحسين", "محمد بن علي", "الحسن بن علي", "علي بن محمد"):
            return {"imams": imams, "basis": "conventional_kunya_at_chain_end", "key": key}
        if rijal_clause and key.startswith("ابي") or rijal_clause and key == "احدهما":
            return {"imams": imams, "basis": "conventional_kunya_in_rijal_clause", "key": key}
    return None


# al-Tusi, Rijal: top-level chapter heading -> the Imam whose companions it lists.
TUSI_SECTION_IMAM = [
    ("من روي عن النبي", "prophet"), ("من روى عن النبي", "prophet"), ("امير المؤمنين", "ali"),
    ("اصحاب ابي محمد الحسن بن علي عليهما", "hasan"), ("اصحاب ابي عبد الله الحسين", "husayn"),
    ("اصحاب ابي محمد علي بن الحسين", "sajjad"), ("اصحاب ابي جعفر محمد بن علي بن الحسين", "baqir"),
    ("جعفر بن محمد الصادق", "sadiq"), ("موسي بن جعفر الكاظم", "kazim"), ("علي بن موسي الرضا", "rida"),
    ("اصحاب ابي جعفر محمد بن علي الثاني", "jawad"), ("ابي الحسن الثالث", "hadi"),
    ("الحسن بن علي بن محمد بن علي الرضا", "askari"), ("من لم يرو عن واحد من الائمة", "none"),
]


def tusi_section_imam(heading: str) -> str | None:
    folded = phrase_fold(heading)
    for needle, imam in TUSI_SECTION_IMAM:
        if phrase_fold(needle) in folded:
            return imam
    return None


# --- names named in an entry --------------------------------------------------------------------------------------

_WAW_NAMES = {"وهب", "وهيب", "وليد", "واصل", "وائل", "وكيع", "وردان", "ورد", "وضاح", "ورقاء", "وثيمة", "ولاد",
              "وابصة", "وحشي", "وداعة", "وبرة", "وراد", "واقد", "وازع", "وشاء", "وهبان"}
_RAWA_AN = re.compile(_NOT_LETTER_BEFORE + r"(?:روي|يروي|وروي|ويروي|سمع|وسمع)\s+عن\s+([^.:؛]*?)(?=[.:؛،]|"
                      r"(?<![ء-ي])(?:له|وله|ثقة|قال|وقال|روي|وروي|و?كان)(?![ء-ي])|$)")
_RAWA_ANHU = re.compile(_NOT_LETTER_BEFORE + r"(?:روي|يروي|وروي|ويروي)\s+عنه\s+([^.:؛]*?)(?=[.:؛،]|"
                        r"(?<![ء-ي])(?:له|وله|ثقة|قال|وقال|روي|وروي|و?كان)(?![ء-ي])|$)")
_ROUTE = re.compile(_NOT_LETTER_BEFORE + r"(?:اخبرنا|اخبرني|حدثنا|حدثني|رويناه|رويناها|نرويه|ورواه|واخبرنا|وحدثنا|"
                    r"واخبرني|وحدثني)(?:\s+به|\s+بها|\s+بكتبه|\s+بجميع كتبه|\s+بكتابه)?(?![ء-ي])\s*([^.]*)")
_ROUTE_END = re.compile(r"\s*(?:جميعا\s+)?(?:عنه|عنهما|عنهم|به|بها|بكتبه|بكتابه|بجميع كتبه|بجميع رواياته)\s*$")


def route_spans(text: str) -> list:
    """(start, end) of transmission routes (أخبرنا ... .) in `phrase_fold(text)` coordinates; terms there are skipped."""
    folded = phrase_fold(text)
    return [(match.start(), match.end()) for match in _ROUTE.finditer(folded)]


def clause_names_subject(clause_verbatim: str, subject_keys: list) -> bool:
    """The clause writes the section subject's ism-nasab chain (or whole one-unit name), e.g. 'حمران بن أعين ثقة'."""
    clause = " ".join(re.sub(r"[^\sء-ي]", " ", phrase_fold(clause_verbatim)).split())
    clause = re.sub(r"(?<![ء-ي])ابن(?![ء-ي])", "بن", clause)
    for key in subject_keys:
        chain = rp.name_chain(key.split())[0]
        if len(chain.split()) >= 3 and re.search(_NOT_LETTER_BEFORE + re.escape(chain) + _NOT_LETTER_AFTER, clause):
            return True
    return False


def clean_name(fragment: str) -> str:
    """A name item as written, honorifics and sigla parentheses removed (folded text)."""
    text = re.sub(r"\(\s*[^)]*\)|\[[^\]]*\]|\d+|[\"«»]", " ", fragment)  # sigla, footnotes first
    text = _HONORIFIC_STRIP.sub(" ", text)
    tokens = text.split()
    if tokens and tokens[0] in ("عن", "وعن"):
        tokens = tokens[1:]
    return " ".join(tokens).strip(" ،,")


def split_conjoined_names(span: str) -> list:
    """'أبي عبد الله وأبي الحسن' -> two names; و-initial names (وهب, وكيع) are kept whole."""
    names, current = [], []
    for token in span.replace("،", " ، ").split():
        starts_new = token == "،" or (token.startswith("و") and len(token) > 2 and token not in _WAW_NAMES
                                      and current)
        if starts_new:
            if current:
                names.append(" ".join(current))
            current = [] if token == "،" else [token[1:]]
            continue
        current.append(token)
    if current:
        names.append(" ".join(current))
    return [clean for clean in (clean_name(name) for name in names) if clean]


_KIN_PREFIX = re.compile(r"^(?:جده|ابيه|عمه|خاله|اخيه|ابي|جدي|عمي)\s+")


def named_people(text: str, is_subject=None) -> dict:
    """Teachers ('روى عن X'), students ('روى عنه X') and transmission routes (أخبرنا ... عن ... عنه) in an entry.

    The last name of a route that ends in عنه/به, or the name before a final item naming the subject
    (`is_subject(folded_name) -> bool`, e.g. 'عن جده الحسن بن راشد'), is the subject's direct student
    (`route_students`); other route names are kept in order but are not neighbours of the subject.
    """
    folded = phrase_fold(text)
    teachers, students, routes, route_students = [], [], [], []
    for match in _RAWA_AN.finditer(folded):
        teachers.extend(split_conjoined_names(match.group(1)))
    for match in _RAWA_ANHU.finditer(folded):
        students.extend(split_conjoined_names(match.group(1)))
    for match in _ROUTE.finditer(folded):
        body = match.group(1)
        ends_with_subject_pronoun = bool(_ROUTE_END.search(body))
        body = _ROUTE_END.sub("", body)
        items = [clean_name(item) for item in re.split(r"(?<![ء-ي])(?:عن|وعن)(?![ء-ي])|،", body)]
        items = [item for item in items if item and len(item.split()) <= 9]
        if not items:
            continue
        routes.append(items)
        if ends_with_subject_pronoun:
            route_students.append(items[-1])
        elif is_subject is not None and len(items) >= 2 and is_subject(_KIN_PREFIX.sub("", items[-1])):
            route_students.append(items[-2])
    return {"teachers": teachers, "students": students, "routes": routes, "route_students": route_students}


# --- books (Fihrist, Najashi) -------------------------------------------------------------------------------------

_BOOK = re.compile(_NOT_LETTER_BEFORE + r"(كتاب|كتب|اصل|نوادر|مسائل|رسالة)(?![ء-ي])\s*([^،.:؛]*)")
_BOOK_STOP = re.compile(_NOT_LETTER_BEFORE + r"(?:اخبرنا|اخبرني|حدثنا|حدثني|رواه|يرويه|قراته|رويناه|نرويه)(?![ء-ي])")


def books_named(text: str) -> list:
    """Works the entry attributes to its subject, as written: 'له كتاب X', 'له كتب، منها: كتاب A، كتاب B', 'له أصل'.

    Only clauses that open with له/وله/صنف/منها or continue a book list are read, so 'رواه عن كتاب' is not a book.
    """
    folded, offsets = fold_with_offsets(text)
    out = []
    for clause in re.finditer(r"(?<![ء-ي])(?:و?له|صنف|وصنف|منها|ومنها)(?![ء-ي])([^.]*)", folded):
        body_start = clause.start(1)
        body = clause.group(1)
        stop = _BOOK_STOP.search(body)
        body = body[:stop.start()] if stop else body
        for match in _BOOK.finditer(body):
            kind, title = match.group(1), match.group(2).strip()
            title = re.split(r"(?<![ء-ي])(?:منها|و?قد|و?هو|و?كان)(?![ء-ي])", title)[0].strip()
            start = body_start + match.start()
            end = body_start + match.start(2) + len(title) if title else body_start + match.end(1)
            out.append({"kind": {"كتاب": "kitab", "كتب": "kutub", "اصل": "asl", "نوادر": "nawadir",
                                 "مسائل": "masail", "رسالة": "risala"}[kind],
                        "verbatim": verbatim_span(text, offsets, start, end).strip(" ،,:")})
    seen, unique = set(), []
    for book in out:
        if book["verbatim"] not in seen:
            seen.add(book["verbatim"])
            unique.append(book)
    return unique


# --- al-Kashshi (Ikhtiyar Ma'rifat al-Rijal) -----------------------------------------------------------------------

_KASHSHI_TITLE_PREFIX = re.compile(r"^(?:ما\s+روي?\s+في|ما\s+روى\s+في|ما\s+جاء\s+في|في)\s+")
_GROUP_WORDS = {"الزيدية", "الواقفة", "الغلاة", "الفطحية", "بنو", "بني", "الزهاد", "ابنا", "اصحاب", "جماعة", "قوم",
                "الحواريين", "الشرطة", "المطعونين", "رجال", "اهل", "النفر", "السبعة", "الثمانية", "المخلطين"}


def kashshi_subjects(title: str) -> dict:
    """Section title -> subject names as written. 'في حمران بن أعين' -> ['حمران بن أعين'];
    'حذيفة وعبد الله بن مسعود' -> two; descriptive tails after '،' are kept apart. Group titles (في الزيدية) give none."""
    folded = phrase_fold(re.sub(r"\bms\d+\b", " ", title or ""))
    folded = _KASHSHI_TITLE_PREFIX.sub("", folded).strip(" .")
    head, _, tail = folded.partition("،")
    tokens = head.split()
    if not tokens:
        return {"subjects": [], "kind": "no_named_subject", "tail": tail.strip()}
    if tokens[0] in _GROUP_WORDS or (tokens[0].startswith("و") and tokens[0][1:] in _GROUP_WORDS):
        return {"subjects": [], "kind": "group", "tail": tail.strip()}
    head = re.split(r"(?<![ء-ي])(?:ودعوة|وكلامه|وما|وكم|وهو|من اصحاب|ايضا|موليان|مولي|وشجرة|ودعائه)(?![ء-ي])",
                    head)[0]
    subjects = [name for name in split_conjoined_names(head) if name and name not in _GROUP_WORDS]
    return {"subjects": subjects, "kind": "person" if subjects else "no_named_subject", "tail": tail.strip()}


_KASHSHI_REPORT = re.compile(r"^\s*(\d+)\s*-\s*")


def split_kashshi_reports(paragraphs: list) -> list:
    """Numbered reports ('# 12 - ...'); an unnumbered paragraph continues the report before it."""
    reports = []
    for paragraph in paragraphs:
        match = _KASHSHI_REPORT.match(paragraph["text"])
        if match or not reports:
            reports.append({"number": match.group(1) if match else None, "page": paragraph["page"],
                            "text": paragraph["text"][match.end():] if match else paragraph["text"]})
        else:
            reports[-1]["text"] += " " + paragraph["text"]
    return reports


# --- Mizzi teacher and student lists -------------------------------------------------------------------------------

_MIZZI_LIST = re.compile(_NOT_LETTER_BEFORE + r"(روي عنه|روي عن)\s*:\s*")
_MIZZI_LIST_END = re.compile(r"\.\s*(?=(?:قال|وقال|ذكره|وذكره|قلت|مات|وروي له|روي له|وقال|كان|وكان|ولد|حدثنا|"
                             r"اخبرنا|روي عنه|روي عن)(?![ء-ي]))|$")


def mizzi_lists(display: str) -> dict:
    """al-Mizzi's 'روى عن:' (teachers) and 'روى عنه:' (students) lists, item by item as written (sigla removed)."""
    folded = phrase_fold(display)
    out = {"teachers": [], "students": [], "spans": [], "teachers_verbatim": [], "students_verbatim": []}
    for match in _MIZZI_LIST.finditer(folded):
        end_match = _MIZZI_LIST_END.search(folded, match.end())
        end = end_match.start() if end_match else len(folded)
        body = folded[match.end():end]
        items = []
        for item in re.split(r"،", body):
            name = clean_name(item)
            name = re.split(r"(?<![ء-ي])(?:وقرا عليه|وهو من|وهو اكبر|وقيل|والصحيح|ولم يدركه|مرسل|وكان)(?![ء-ي])",
                            name)[0].strip()
            if name.startswith("و") and name[1:2] and name.split()[0] not in _WAW_NAMES:
                name = name[1:]
            if name and len(name.split()) <= 10:
                items.append((name, " ".join(item.split()).strip(" ،,")))
        role = "teachers" if match.group(1) == "روي عن" else "students"
        out[role].extend(name for name, _ in items)
        out[role + "_verbatim"].extend(raw for _, raw in items)  # the item as printed (folded), for citation
        out["spans"].append((match.start(), end))
    return out


# --- link evidence -----------------------------------------------------------------------------------------------

def case_fold_tokens(tokens: list) -> list:
    """ابي/ابا to ابو everywhere (matching only; never an identity key)."""
    return ["ابو" if token in ("ابي", "ابا") else token for token in tokens]


def name_shape(name_key: str) -> str:
    """full | single (one token) | kunya (a kunya alone) | ibn (ابن فلان, a nasab alone) | <placeholder reason>."""
    placeholder = external_name_placeholder(name_key)
    if placeholder in ("relational_name", "collective_or_anonymous_name", "no_arabic_name"):
        return placeholder
    tokens = name_key.split()
    if placeholder == "bare_single_token_name" or (len(tokens) == 2 and tokens[0] in ("عبد", "عبيد")):
        return "single"  # a theophoric ism alone (عبد العزيز) is one name, not a full name
    if placeholder == "kunya_only_name":
        return "kunya"
    if tokens and tokens[0] in ("بن", "بنت") and len(tokens) <= 4:
        return "ibn"
    return "full"


def short_name_occurs(shape: str, tokens: list, key_tokens: list) -> bool:
    """Where a short name may sit in a headword: a single token as the ism (first token) or as a nisba/laqab (ال...)
    not following بن; a kunya anywhere not following بن (أبو بصير, not بن أبي بصير); ابن فلان right after the ism."""
    tokens, key_tokens = case_fold_tokens(tokens), case_fold_tokens(key_tokens)
    size = len(tokens)
    if shape == "ibn":
        return key_tokens[1:1 + size] == tokens
    for index in range(len(key_tokens) - size + 1):
        if key_tokens[index:index + size] != tokens:
            continue
        if index > 0 and key_tokens[index - 1] in ("بن", "بنت"):
            continue
        if shape == "single" and index > 0 and not tokens[0].startswith("ال"):
            continue
        return True
    return False


def name_match_basis(name_key: str, entry_keys: list, entry_tokens: set, shape: str) -> str | None:
    """How a chain/label name matches an entry by name alone (before any corroboration).

    exact_full_name: the canonical key equals a headword key.
    nasab_prefix_and_tokens: the name has a nasab (بن) and its ism-nasab chain is the start of the entry's chain,
      and every other token of the name occurs in the entry headword (محمد بن مسلم -> محمد بن مسلم بن رباح ...).
    short_name_in_headword: a single name, a kunya alone or ابن فلان at its place in the headword
      (`short_name_occurs`); usable only with corroboration (caller enforces).
    """
    if not name_key:
        return None
    short = shape in ("single", "kunya", "ibn")
    if name_key in entry_keys:
        return "short_name_in_headword" if short else "exact_full_name"
    tokens = name_key.split()
    if short:
        if any(short_name_occurs(shape, tokens, key.split()) for key in entry_keys):
            return "short_name_in_headword"
        return None
    if not any(token in ("بن", "بنت") for token in tokens):
        return None
    chain, rest = rp.name_chain(tokens)
    for key in entry_keys:
        entry_chain, _ = rp.name_chain(key.split())
        if entry_chain == chain or entry_chain.startswith(chain + " "):
            if set(rest) <= entry_tokens:
                return "nasab_prefix_and_tokens"
    return None


def names_agree(left_key: str, right_key: str) -> str | None:
    """Two people-name keys denote the same written name: equal keys, or equal ism-nasab chains with a بن."""
    if not left_key or not right_key:
        return None
    if left_key == right_key:
        return "equal_key"
    left_tokens, right_tokens = left_key.split(), right_key.split()
    if "بن" in left_tokens and "بن" in right_tokens:
        left_chain, _ = rp.name_chain(left_tokens)
        right_chain, _ = rp.name_chain(right_tokens)
        if left_chain == right_chain and len(left_chain.split()) >= 3:
            return "equal_nasab_chain"
    return None


EVIDENCE_WEIGHT = {
    "exact_full_name": 4, "nasab_prefix_and_tokens": 3, "short_name_in_headword": 1,
    "tusi_section_imam_is_imam_narrated_from": 3, "entry_imam_is_imam_narrated_from": 3,
    "tusi_section_imam_is_chain_head_imam": 1, "entry_imam_is_chain_head_imam": 1,
    "entry_teacher_is_chain_teacher": 2, "entry_student_is_chain_student": 2,
}


# --- life facts: timelines, places, events ------------------------------------------------------------------------

# Proposed gazetteer additions to rp.GAZETTEER (forms in letter-folded spelling; city forms, nisba forms).
# 'عمان' is left out on purpose: unvocalised it is both Oman and Amman.
GAZETTEER_ADDITIONS = {
    "qum": (("قم",), ("القمي",)), "samarra": (("سر من راي", "سامراء", "سامرا"), ()),
    "karbala": (("كربلاء", "كربلا", "الحائر"), ()), "fustat": (("الفسطاط",), ()), "oman": ((), ("العماني",)),
    "hira": (("الحيرة",), ("الحيري",)), "ahwaz": (("الاهواز",), ("الاهوازي",)), "tus": (("طوس",), ("الطوسي",)),
    "jurjan": (("جرجان",), ("الجرجاني",)), "qazwin": (("قزوين",), ("القزويني",)),
    "kashan": (("قاشان", "كاشان"), ("القاشاني", "الكاشاني")), "najaf": (("الغري", "النجف"), ()),
    "kish": (("كش",), ("الكشي",)),
}


def gazetteer() -> dict:
    """place id -> {'cities': [...], 'nisbas': [...], 'source': ...} (existing rp.GAZETTEER plus the additions)."""
    out = {}
    for place, (_, cities, nisbas) in rp.GAZETTEER.items():
        out[place] = {"cities": [phrase_fold(c) for c in cities], "nisbas": [phrase_fold(n) for n in nisbas],
                      "source": "biography-verification rijal_parsing.GAZETTEER"}
    for place, (cities, nisbas) in GAZETTEER_ADDITIONS.items():
        entry = out.setdefault(place, {"cities": [], "nisbas": [], "source": "rijal layer proposal"})
        entry["cities"] = sorted(set(entry["cities"]) | set(cities))
        entry["nisbas"] = sorted(set(entry["nisbas"]) | set(nisbas))
    return out


_PLACE_FORMS = {}
for _place, _forms in gazetteer().items():
    for _form in _forms["cities"] + _forms["nisbas"]:
        _PLACE_FORMS[_form] = _place


def place_of(word_run: str) -> str | None:
    """Gazetteer id for a written place (بالكوفة, الكوفة, سر من رأى), None when not unambiguously known."""
    words = phrase_fold(word_run).split()
    for size in (3, 2, 1):
        candidate = " ".join(words[:size])
        for form in (candidate, candidate[1:] if candidate[:1] in ("ب", "و", "ل") else None,
                     candidate[2:] if candidate[:2] in ("وب", "فب") else None):
            if form and form in _PLACE_FORMS:
                return _PLACE_FORMS[form]
    return None


# Named events -> the history lane's event title or key (datasets/hadith-data/history/claims_spec.py), else None.
EVENTS = [
    (r"بدر|بدرا", "Battle of Badr"), (r"احد|احدا", "Battle of Uhud"), (r"الخندق", "Battle of the Trench (Khandaq)"),
    (r"صفين", "Battle of Siffin"), (r"الجمل", "Battle of the Camel"), (r"اليرموك", "Battle of Yarmouk"),
    (r"اليمامة", "battle-of-yamama"), (r"الحرة", "battle-of-al-harra"),
    (r"الطف|كربلاء|كربلا", "Martyrdom of Husayn at Karbala"), (r"الحديبية", "Treaty of Hudaybiyyah"),
    (r"فتح مكة", "Conquest of Makkah"), (r"القادسية", "Conquest of Persia (Battle of Qadisiyyah)"),
    (r"النهروان|النهر", None), (r"حنين|حنينا", None), (r"خيبر", None), (r"تبوك", None), (r"العقبة", None),
    (r"بيعة الرضوان", None), (r"الفتح", None), (r"المشاهد", None),
]
_EVENT_TRIGGER = r"(?:شهد|وشهد|شهدا|شهدها|حضر|وحضر|قتل|وقتل|استشهد|واستشهد|يوم|ويوم|وقعة|غزوة|غزا|وغزا)"
_EVENT_RE = re.compile(_NOT_LETTER_BEFORE + r"(" + _EVENT_TRIGGER + r")(?![ء-ي])((?:\s+(?:مع|في|ب)?\s*[ء-ي]+){0,4}?)\s+"
                       r"(?:ب|يوم\s+)?(" + "|".join(p for p, _ in EVENTS) + r")" + _NOT_LETTER_AFTER)
_REGNAL_RE = re.compile(_NOT_LETTER_BEFORE + r"(?:في|و?في)\s+(خلافة|ولاية|امارة|امرة|زمن|ايام|ملك|دولة|ايام)\s+"
                        r"((?:[ء-ي]+)(?:\s+(?:بن|ابن)\s+[ء-ي]+)?)")
_MOVE_RE = re.compile(_NOT_LETTER_BEFORE + r"(قدم|وقدم|دخل|ودخل|ورد|وورد|رحل الي|ورحل الي|خرج الي|وخرج الي|"
                      r"انتقل الي|وانتقل الي|سافر الي|نزل|ونزل|سكن|وسكن|نزيل|اقام ب|واقام ب|حج|وحج)(?![ء-ي])\s*"
                      r"((?:[ء-ي]+\s*){1,3})")
_OFFICE_RE = re.compile(_NOT_LETTER_BEFORE + r"(ولي|وولي|تولي|استقضي|واستقضي|قاضي|قاضيا|وكان قاضيا)(?![ء-ي])\s+"
                        r"((?:[ء-ي]+\s*){1,3})")
_YEAR_AFTER = re.compile(_NOT_LETTER_BEFORE + r"(?:سنة|سنه|عام)\s+((?:[ء-ي]+\s*){1,6})")
_MOVE_KIND = {"قدم": "travelled_or_arrived", "دخل": "travelled_or_arrived", "ورد": "travelled_or_arrived",
              "رحل الي": "travelled_or_arrived", "خرج الي": "travelled_or_arrived", "سافر الي": "travelled_or_arrived",
              "حج": "travelled_or_arrived", "انتقل الي": "resided", "نزل": "resided", "سكن": "resided",
              "نزيل": "resided", "اقام ب": "resided"}


def _date_in(clause: str) -> dict:
    """The first 'سنة <number>' in a clause: as written, and a Hijri range only when the century is written."""
    match = _YEAR_AFTER.search(clause)
    if not match:
        return {"date_as_written": None, "year_min": None, "year_max": None, "precision": None}
    words = re.sub(r"(?<![ء-ي])و\s+(?=[ء-ي])", "و", match.group(1)).split()  # 'ثلاث و خمسين' as printed
    parts, consumed = rp.parse_number_words(words)
    if not consumed:
        return {"date_as_written": None, "year_min": None, "year_max": None, "precision": None}
    low, high = rp.parts_to_range(parts)
    written = " ".join(match.group(0).split()[:consumed + 1])
    if parts["hundreds"] is None:
        return {"date_as_written": written, "year_min": None, "year_max": None, "precision": "century_not_stated",
                "within_century": [low, high]}
    return {"date_as_written": written, "year_min": low, "year_max": high,
            "precision": "exact" if low == high else "range"}


def life_facts(text: str, skip_spans: tuple = ()) -> list:
    """Dated or placed statements in a passage, each as written: moves and residence, offices, named events, regnal
    datings. Deaths and births come from rp.parse_year_statements (callers add them). Nothing is inferred from dates.
    `verbatim` is letter-folded; the caller maps it to the source letters for the citation."""
    folded = phrase_fold(text)
    facts = []

    def skipped(position):
        return any(start <= position < end for start, end in skip_spans)

    for match in _MOVE_RE.finditer(folded):
        if skipped(match.start()):
            continue
        verb = match.group(1).removeprefix("و") if match.group(1) not in ("ورد",) else "ورد"
        words = match.group(2).split()
        place_written = " ".join(words[:2] if place_of(" ".join(words[:2])) and not place_of(words[0]) else words[:1])
        clause_end = min([folded.find(mark, match.end()) for mark in "،.:" if folded.find(mark, match.end()) >= 0]
                         or [len(folded)])
        clause = folded[match.start():clause_end]
        facts.append({"kind": _MOVE_KIND.get(verb, "travelled_or_arrived"), "verb": verb,
                      "verbatim": " ".join(clause.split()[:12]), "place_as_written": place_written,
                      "place_id": place_of(place_written), **_date_in(clause), "offset": match.start()})
    for match in _OFFICE_RE.finditer(folded):
        if skipped(match.start()):
            continue
        clause_end = min([folded.find(mark, match.end()) for mark in "،.:" if folded.find(mark, match.end()) >= 0]
                         or [len(folded)])
        clause = folded[match.start():clause_end]
        words = match.group(2).split()
        facts.append({"kind": "held_office", "verb": match.group(1), "verbatim": " ".join(clause.split()[:10]),
                      "office_as_written": " ".join(words[:3]), "place_as_written": None,
                      "place_id": next((p for p in (place_of(w) for w in words[:3]) if p), None),
                      **_date_in(clause), "offset": match.start()})
    for match in _EVENT_RE.finditer(folded):
        if skipped(match.start()):
            continue
        written = match.group(3)
        history = next((title for pattern, title in EVENTS if re.fullmatch(pattern, written)), None)
        if written in ("احد", "احدا") and match.group(1).removeprefix("و") not in ("شهد", "يوم", "شهدا", "قتل"):
            continue  # احد is also 'one'
        facts.append({"kind": "present_at_event", "verb": match.group(1), "verbatim": match.group(0).strip(),
                      "event_as_written": written, "history_event_ref": history,
                      "killed_there": match.group(1).removeprefix("و") in ("قتل", "استشهد"),
                      "date_as_written": None, "year_min": None, "year_max": None, "precision": "event_reference",
                      "place_as_written": None, "place_id": None, "offset": match.start()})
    for match in _REGNAL_RE.finditer(folded):
        if skipped(match.start()):
            continue
        facts.append({"kind": "regnal_dating", "verb": None, "verbatim": match.group(0).strip(),
                      "date_as_written": match.group(0).strip(), "ruler_or_period_as_written": match.group(2),
                      "year_min": None, "year_max": None, "precision": "regnal_or_relative_not_normalised",
                      "place_as_written": None, "place_id": None, "offset": match.start()})
    facts.sort(key=lambda fact: fact["offset"])
    return facts


def death_or_birth_fact(statement: dict, kind: str) -> dict:
    """A parsed death/birth alternative as a timeline fact; place only when the clause writes a known place."""
    clause = statement["clause_verbatim"]
    place_written, place_id = None, None
    for token_index, token in enumerate(clause.split()):
        place = place_of(" ".join(clause.split()[token_index:token_index + 3]))
        if place and (token.startswith("ب") or token_index and clause.split()[token_index - 1] in ("في", "الي")):
            place_written, place_id = token, place
            break
    verb = clause.split()[0] if clause.split() else None
    manner = {"قتل": "killed", "قتلت": "killed", "استشهد": "martyred", "استشهدت": "martyred"}.get(verb)
    return {"kind": kind, "verb": verb, "verbatim": clause, "date_as_written": statement["alternative_verbatim"] or None,
            "alternative": statement["alternative"], "alternative_marker": statement["alternative_marker"],
            "year_min": statement["year_min"], "year_max": statement["year_max"], "precision": statement["precision"],
            "within_century": statement.get("within_century"), "date_flags": statement["flags"],
            "place_as_written": place_written, "place_id": place_id, "manner": manner}


_LONE_HASH = re.compile(r"(?<!\S)#(?!\S)")


def citable_text(raw_span: str) -> str:
    """What a reader sees of a source span: OpenITI markup removed (rijal_sources.display_text), lone '#' dropped."""
    import rijal_sources  # noqa: PLC0415  (its display_text is pure; importing has no side effects beyond paths)
    return " ".join(_LONE_HASH.sub(" ", rijal_sources.display_text(raw_span)).split())


def locate_verbatim(citable: str, candidate: str, folded_with_offsets: tuple | None = None) -> tuple:
    """(verbatim as written in the source, reason). A letter-folded candidate is mapped back to the source letters.
    `folded_with_offsets` is fold_with_offsets(citable), passed by callers that cite one span many times."""
    if not candidate:
        return None, "no verbatim text for this value"
    if candidate in citable:
        return candidate, None
    folded, offsets = folded_with_offsets or fold_with_offsets(citable)
    target = phrase_fold(candidate)
    position = folded.find(target) if target else -1
    if position < 0:
        return None, "verbatim text not found in the cited source span"
    return verbatim_span(citable, offsets, position, position + len(target)), None


CITATION_REQUIRED = (("work", "author"), ("work", "title"), ("work", "tradition"), ("edition", "openiti_uri"),
                     ("locator", "page"), ("locator", "entry_number"), ("passage_ar",), ("source_span", "start"),
                     ("source_span", "end"), ("source_ref",), ("licence",), ("source_sha256",), ("source_file",))


def citation_problems(citation: dict, source_text: str | None = None, source_sha256: str | None = None) -> list:
    """Why a citation is incomplete or does not check out against its source (empty list = it passes)."""
    problems = []
    for path in CITATION_REQUIRED:
        value = citation
        for part in path:
            value = value.get(part) if isinstance(value, dict) else None
        if value in (None, ""):
            problems.append("missing " + ".".join(path))
    if source_sha256 is not None and citation.get("source_sha256") != source_sha256:
        problems.append("source file hash differs")
    if source_text is not None and not problems:
        span = citation["source_span"]
        if citation["passage_ar"] not in citable_text(source_text[span["start"]:span["end"]]):
            problems.append("passage not found in the cited span")
    return problems


def rank_candidates(candidates: list) -> list:
    """Dense rank by summed evidence weight (higher first), then entry id; ties share a rank. Nothing is picked."""
    for candidate in candidates:
        candidate["evidence_score"] = sum(EVIDENCE_WEIGHT[item["evidence"]] for item in candidate["evidence"])
    candidates.sort(key=lambda c: (-c["evidence_score"], c["entry_id"]))
    rank, previous = 0, None
    for candidate in candidates:
        if candidate["evidence_score"] != previous:
            rank += 1
            previous = candidate["evidence_score"]
        candidate["rank"] = rank
    return candidates
