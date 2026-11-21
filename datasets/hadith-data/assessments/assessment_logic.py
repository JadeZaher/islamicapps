"""Pure rules for consolidating attributed report gradings and narrator verdicts (see README.md in this directory).

Standard library only; no I/O. Every function keeps the verbatim Arabic beside anything it derives, never merges two
scholars' rulings and never computes a grade. Canonical terms are set only by the exact-term tables below.
"""

from __future__ import annotations

import re
import unicodedata

# --- folding -----------------------------------------------------------------------------------------------------

_MARKS = re.compile("[ؐ-ًؚ-ٰٟۖ-ۭـ]")
_ALEF = re.compile(r"[آأإٱ]")
_LETTER = re.compile(r"[ء-ي]")
NOT_LETTER_BEFORE = r"(?<![ء-ي])"
NOT_LETTER_AFTER = r"(?![ء-ي])"


def fold(text: str) -> str:
    """Phrase-matching fold: NFKC, vocalization and tatweel removed, alef variants to ا, ى to ي, spaces collapsed.

    Persian ya/kaf are folded too. Never stored as a value; only compared.
    """
    text = unicodedata.normalize("NFKC", text or "")
    text = _ALEF.sub("ا", _MARKS.sub("", text)).replace("ى", "ي").replace("ی", "ي").replace("ک", "ك")
    for mark in ("‌", "‍", "‎", "‏", " "):
        text = text.replace(mark, " ")
    return " ".join(text.split())


# Blessing formulas removed before a letters-only comparison (editions differ in which they print).
_FORMULAS = [
    "صلياللهعليهوالهوسلم", "صلياللهعليهوعليالهوسلم", "صلياللهعليهوسلم", "صلياللهعليهواله", "صلياللهعليه",
    "رضياللهعنهما", "رضياللهعنهم", "رضياللهعنها", "رضياللهعنه", "رضياللهتعاليعنهما", "رضياللهتعاليعنه",
    "عليهمالسلام", "عليهماالسلام", "عليهالسلام", "عليهاالسلام", "عزوجل", "تباركوتعالي", "سبحانهوتعالي",
]


def comparison_letters(text: str) -> str:
    """Arabic base letters only after `fold`, ة as ه, with blessing formulas removed (letters-only join key)."""
    letters = "".join(_LETTER.findall(fold(text).replace("ﷺ", " صلي الله عليه وسلم ")))
    letters = letters.replace("ة", "ه")
    for formula in _FORMULAS:
        letters = letters.replace(formula, "")
    return letters


_TRANSMISSION_WORDS = {"حدثنا", "حدثني", "اخبرنا", "اخبرني", "انبانا", "انباني", "ثنا", "نا", "عن", "ان", "انه", "قال", "قالا",
                       "سمعت", "سمع", "يقول", "حدثه", "اخبره", "حدثهم", "قالت", "يحدث", "و", "ح", "جميعا", "كلاهما"}


def chain_name_letters(text: str) -> str:
    """Letters of the names in a chain: transmission words dropped, 'ابن' as 'بن' (editions differ in both)."""
    tokens = []
    for token in re.split(r"[^ء-ي]+", fold(text)):
        token = token[1:] if token.startswith("و") and token[1:] in _TRANSMISSION_WORDS else token
        if not token or token in _TRANSMISSION_WORDS:
            continue
        tokens.append("بن" if token == "ابن" else token)
    return comparison_letters(" ".join(tokens))


# --- report grading terms ----------------------------------------------------------------------------------------

# Non-rulings in the Imami gradings cell (fold without spaces). Same classes as diagnostics/grading-recovery.
IMAMI_NON_RULINGS = {
    "لميخرجه": "not_included_by_grader", "لميذكره": "not_included_by_grader",
    "لميذكرعندهشيء": "not_included_by_grader", "لميذكرالطريق": "chain_not_given", "لميحقق": "not_investigated",
    "لاواسطة": "chain_description_not_ruling", "سكتعنه": "grader_silent", "كالسابق": "back_reference_only",
    "كالسابقايضا": "back_reference_only", "مثلالسندالسابق": "back_reference_only", "بالسندالسابق": "back_reference_only",
}

# Exact single terms whose meaning in the Imami four-part scheme the glossary states (docs/glossary.md §Imami grading).
IMAMI_EXACT_CANONICAL = {
    "صحيح": "sahih", "حسن": "hasan", "موثق": "muwaththaq", "ضعيف": "da_if", "مجهول": "majhul", "مرسل": "mursal",
    "معتبر": "mu_tabar", "ضعيف علي المشهور": "da_if", "مختلف فيه": "mukhtalaf",
}
# Sunni compiler statements: only a single bare term is mapped; compounds (حسن صحيح, حسن غريب) stay null.
SUNNI_EXACT_CANONICAL = {"صحيح": "sahih", "حسن": "hasan", "ضعيف": "da_if", "مرسل": "mursal", "موضوع": "mawdu"}


def imami_non_ruling_reason(term_ar: str) -> str | None:
    key = fold(term_ar).replace(" ", "")
    return IMAMI_NON_RULINGS.get(key)


def imami_canonical(term_ar: str) -> tuple[str | None, str]:
    """(canonical or None, reason). Only an exact glossary-supported term maps; every compound stays null."""
    folded = fold(term_ar).strip(" .،")
    if folded in IMAMI_EXACT_CANONICAL:
        return IMAMI_EXACT_CANONICAL[folded], "exact_term_in_imami_scheme"
    if "كالصحيح" in folded:
        return None, "ka_al_sahih_qualifier_kept_verbatim"
    if folded in ("مرفوع", "مضمر"):
        return None, "transmission_form_not_a_grade"
    if "معتبر" in folded and folded != "معتبر":
        return None, "compound_with_mutabar_kept_verbatim"
    if re.search(NOT_LETTER_BEFORE + r"(او|و)" + NOT_LETTER_AFTER, folded):
        return None, "alternatives_or_several_chains_kept_verbatim"
    return None, "compound_or_qualified_term_kept_verbatim"


def sunni_statement_canonical(term_ar: str) -> tuple[str | None, str]:
    folded = fold(term_ar).strip(" .،")
    if folded in SUNNI_EXACT_CANONICAL:
        return SUNNI_EXACT_CANONICAL[folded], "single_term_in_sunni_scheme"
    return None, "compound_or_descriptive_term_kept_verbatim"


# --- compiler statements inside a report's own text --------------------------------------------------------------

# Who speaks as the compiler, per work. Kunyas are matched after `fold`.
COMPILER_VOICE = {
    "sunni:tirmidhi": {"kunyas": ("ابو عيسي",), "compiler": "Abu 'Isa Muhammad ibn 'Isa al-Tirmidhi (d. 279)",
                       "compiler_ar": "أبو عيسى الترمذي", "work": "al-Jami' (Sunan al-Tirmidhi)", "unmarked_is_compiler": True},
    "sunni:abudawud": {"kunyas": ("ابو داود",), "compiler": "Abu Dawud Sulayman ibn al-Ash'ath al-Sijistani (d. 275)",
                       "compiler_ar": "أبو داود السجستاني", "work": "Sunan Abi Dawud", "unmarked_is_compiler": False},
    "sunni:nasai": {"kunyas": ("ابو عبد الرحمن",), "compiler": "Abu 'Abd al-Rahman Ahmad ibn Shu'ayb al-Nasa'i (d. 303)",
                    "compiler_ar": "أبو عبد الرحمن النسائي", "work": "al-Sunan al-Sughra (al-Mujtaba)", "unmarked_is_compiler": False},
    "sunni:ibnmajah": {"kunyas": ("ابو عبد الله",), "compiler": "Abu 'Abd Allah Muhammad ibn Yazid Ibn Majah (d. 273)",
                       "compiler_ar": "أبو عبد الله ابن ماجه", "work": "Sunan Ibn Majah", "unmarked_is_compiler": False},
    "sunni:bukhari": {"kunyas": ("ابو عبد الله",), "compiler": "Abu 'Abd Allah Muhammad ibn Isma'il al-Bukhari (d. 256)",
                      "compiler_ar": "أبو عبد الله البخاري", "work": "al-Jami' al-Sahih (Sahih al-Bukhari)", "unmarked_is_compiler": False},
    "sunni:muslim": {"kunyas": ("ابو الحسين", "مسلم"), "compiler": "Abu al-Husayn Muslim ibn al-Hajjaj (d. 261)",
                     "compiler_ar": "مسلم بن الحجاج", "work": "al-Sahih (Sahih Muslim)", "unmarked_is_compiler": False},
    "sunni:darimi": {"kunyas": ("ابو محمد",), "compiler": "Abu Muhammad 'Abd Allah ibn 'Abd al-Rahman al-Darimi (d. 255)",
                     "compiler_ar": "أبو محمد الدارمي", "work": "al-Musnad (Sunan al-Darimi)", "unmarked_is_compiler": False},
    "sunni:muwatta": {"kunyas": ("مالك",), "compiler": "Malik ibn Anas (d. 179)", "compiler_ar": "مالك بن أنس",
                      "work": "al-Muwatta'", "unmarked_is_compiler": False},
    # Musnad Ahmad: 'قال عبد الله' is his son and transmitter, never the compiler; no compiler voice is assumed.
    "sunni:ahmad": {"kunyas": (), "compiler": "Ahmad ibn Hanbal (d. 241)", "compiler_ar": "أحمد بن حنبل",
                    "work": "al-Musnad", "unmarked_is_compiler": False},
    "ibadi:musnad-rabi": {"kunyas": ("الربيع",), "compiler": "al-Rabi' ibn Habib al-Farahidi", "compiler_ar": "الربيع بن حبيب",
                          "work": "al-Jami' al-Sahih (Musnad al-Rabi')", "unmarked_is_compiler": False},
    "zaydi:musnad-zayd": {"kunyas": ("زيد بن علي",), "compiler": "Zayd ibn 'Ali (as transmitted by Abu Khalid al-Wasiti)",
                          "compiler_ar": "زيد بن علي", "work": "Musnad al-Imam Zayd", "unmarked_is_compiler": False},
}

REPORT_TERMS = ("صحيح", "حسن", "غريب", "ضعيف", "شاذ", "منكر", "محفوظ", "مرسل", "موضوع", "باطل", "خطا", "وهم")
# 'وهم' is a term only as 'وهم من/في' or sentence-final ('وهم' is also 'and they'); no definite article on any term
# ('الحسن' is a name; 'والصحيح ما روى' grades a variant, not this report).
_RT = r"صحيح|حسن|غريب|ضعيف|شاذ|منكر|محفوظ|مرسل|موضوع|باطل|خطا|وهم(?=\s+(?:من|في)\s|\s*$)"
_TERM_TOKEN = re.compile(NOT_LETTER_BEFORE + r"(?:و|ف|ب)?(" + _RT + r")" + NOT_LETTER_AFTER)
_FILLER = r"(?:(?:عندي|عندنا|ليس|غير|اسناده|حديث|بصحيح|بمحفوظ|بالقوي|لا|يصح|و)\s+){0,3}"
# A report is the grammatical subject: this hadith / this chain / its chain / the hadith of X.
_SUBJECT_THIS = re.compile(r"(?:^|\s)(?:و?هذا|و?هذه)\s+(?:ال)?(?:حديث\s+|اسناد\s+|الاسناد\s+|رواية\s+)?" + _FILLER
                           + r"(?:و|ف|ب)?(?:" + _RT + r")" + NOT_LETTER_AFTER)
_SUBJECT_THIS_HADITH = re.compile(r"(?:^|\s)(?:و?هذا)\s+(?:ال)?حديث\s+" + _FILLER + r"(?:و|ف|ب)?(?:" + _RT + r")"
                                  + NOT_LETTER_AFTER)
_SUBJECT_ISNAD = re.compile(r"(?:^|\s)(?:و?اسناده|و?هذا\s+اسناد|اسناد\s+هذا\s+الحديث)\s+" + _FILLER + r"(?:و|ف|ب)?(?:"
                            + _RT + r")" + NOT_LETTER_AFTER)
_SUBJECT_NAMED = re.compile(r"(?:^|\s)و?حديث\s+((?:[ء-ي]+\s+){0,5}?[ء-ي]+)\s+(?:حديث|وهو\s+حديث)\s+" + _FILLER
                            + r"(?:و|ف|ب)?(?:" + _RT + r")" + NOT_LETTER_AFTER)
_SUBJECT_ANY = (_SUBJECT_THIS_HADITH, _SUBJECT_ISNAD, _SUBJECT_NAMED, _SUBJECT_THIS)
_SUBJECT_LEAD = re.compile(r"^(?:و?هذا\s+(?:ال)?(?:حديث|اسناد|رواية)?|و?هذه|و?اسناده|اسناد\s+هذا\s+الحديث|"
                           r"و?حديث\s+(?:[ء-ي]+\s+){0,6}?(?:وهو\s+)?حديث)\s*")
_SUPERLATIVE = re.compile(r"(?:اصح|احسن)\s+شيء")
_SENTENCE_SPLIT = re.compile("[‏‎]*\\.[‏‎]*")
_OTHER_SPEAKER = re.compile(NOT_LETTER_BEFORE + r"(?:سالت|سمعت|فقال|قال|وقال|يقول)\s+([ء-ي]+(?:\s+[ء-ي]+){0,3})")
_ASKED_BUKHARI = re.compile(r"(?:سالت|وسالت)\s+(?:محمدا|محمد\s+بن\s+اسماعيل)\s+عن\s+هذا\s+الحديث\s*،?\s*فقال\s+"
                            r"(?:هو\s+|هذا\s+)?(?:حديث\s+)?((?:(?:حسن|صحيح|غريب)\s*)+)$")


def _terms(folded: str) -> list:
    terms = []
    for match in _TERM_TOKEN.finditer(folded):
        if match.group(1) not in terms:
            terms.append(match.group(1))
    return terms


_MORE_TERMS = re.compile(r"\s+(?:و)?(?:" + _RT + r")" + NOT_LETTER_AFTER + r"|\s+\[(?:" + _RT + r")\]")


def report_clause(folded: str):
    """(start, end) in the folded sentence of the earliest report-subject grading clause, extended over a
    following run of grading terms ('هذا حديث حسن صحيح غريب'); None when there is no such clause."""
    best = None
    for pattern in _SUBJECT_ANY:
        match = pattern.search(folded)
        if match and (best is None or match.start() < best[0]):
            best = [match.start(), match.end()]
    if best is None:
        return None
    while True:
        more = _MORE_TERMS.match(folded, best[1])
        if not more:
            break
        best[1] = more.end()
    return best[0] + (1 if folded[best[0]:best[0] + 1] == " " else 0), best[1]


def verbatim_span(original: str, folded_start: int, folded_end: int) -> str:
    """The original words covering a span of `fold(original)` (word-aligned; marks and spelling kept)."""
    words_original = original.split()
    words_folded = fold(original).split(" ")
    if len(words_folded) != len(words_original):
        return fold(original)[folded_start:folded_end]
    position, first, last = 0, None, None
    for index, word in enumerate(words_folded):
        word_end = position + len(word)
        if first is None and word_end > folded_start:
            first = index
        if position < folded_end:
            last = index
        position = word_end + 1
    return " ".join(words_original[first:last + 1]).strip(" ،,.")


def clause_without_subject(clause_folded: str) -> str:
    return _SUBJECT_LEAD.sub("", clause_folded, count=1).strip()


def _speaker_at_start(folded: str, kunyas: tuple) -> str | None:
    """'compiler' when the sentence opens with قال + a compiler kunya; 'other' when it opens with another named
    speaker; None when unmarked (including a bare 'قال' followed by the statement)."""
    head = folded[:80]
    for kunya in kunyas:
        if re.match(r"^(?:قال\s+)?و?قال\s+" + re.escape(kunya) + NOT_LETTER_AFTER, head):
            return "compiler"
    if re.match(r"^و?قال\s+(?:و?هذا|حديث|اسناده|وفي|فذكر|وقد|وروي|وروى|ويروى)" + NOT_LETTER_AFTER, head):
        return None
    if re.match(r"^و?قال\s+[ء-ي]", head):
        return "other"
    return None


_CHAIN_OPENER_RAW = re.compile("(?<![ء-ي])(?:حدثنا|حدثني|[أاإ]خبرنا|[أاإ]خبرني|[أاإ]نبأنا)(?![ء-ي])")


def first_chain_opener(text: str) -> int:
    """Offset of the first transmission opener in an unvocalized text (len(text) when none): a closing column that
    opens a further chain carries statements about that next report too."""
    match = _CHAIN_OPENER_RAW.search(text or "")
    return match.start() if match else len(text or "")


_DIALOGUE = re.compile(NOT_LETTER_BEFORE + r"(?:سالت|وسالت|سمعت|وسمعت|يقول|سئل)" + NOT_LETTER_AFTER)
_STRIP = " ‏‎\"'"


def classify_report_statement(sentence: str, preceding: str, work_id: str) -> dict | None:
    """Classify one sentence of a report's text (or of a closing column) as a compiler statement about a report.

    Returns None when the sentence carries no report-subject grading clause. Otherwise a dict with `decision`
    ('compiler_statement', 'quoted_ruling' or 'held'), the verbatim `term_ar` clause and the basis or reason.
    `preceding` is the text before the sentence (speaker context and the named-subject check).
    """
    voice = COMPILER_VOICE.get(work_id)
    if voice is None:
        return None
    original = " ".join(sentence.strip(_STRIP).split())
    folded = fold(original)
    if not folded:
        return None
    asked = _ASKED_BUKHARI.search(folded) if work_id == "sunni:tirmidhi" else None
    clause = report_clause(folded)
    superlative = bool(_SUPERLATIVE.search(folded))
    if not (clause or superlative or asked):
        return None
    base = {"statement_ar": original}
    if asked:
        span = (asked.start(1), asked.end(1))
        return {**base, "decision": "quoted_ruling", "grader": "Muhammad ibn Isma'il al-Bukhari (d. 256)",
                "grader_ar": "محمد بن إسماعيل البخاري", "quoted_by": voice["compiler"],
                "attribution_basis": "al-Tirmidhi reports asking al-Bukhari about this hadith (سألت محمدا عن هذا الحديث فقال)",
                "term_ar": verbatim_span(original, *span), "term_folded": folded[span[0]:span[1]].strip(),
                "terms_in_order": _terms(folded[span[0]:span[1]])}
    if clause is None:
        return {**base, "decision": "held", "reason": "comparative_soundest_in_chapter_not_a_grade", "terms_in_order": []}
    clause_folded = folded[clause[0]:clause[1]]
    terms = _terms(clause_folded)
    base.update({"term_ar": verbatim_span(original, *clause), "term_folded": clause_folded, "terms_in_order": terms})
    if not terms:
        return {**base, "decision": "held", "reason": "no_grade_term_in_statement"}
    speaker = _speaker_at_start(folded, voice["kunyas"])
    preceding_folded = fold(preceding)[-60:]
    marked_just_before = any(re.search(r"قال\s+" + re.escape(k) + r"\s*[:،]?\s*$", preceding_folded) for k in voice["kunyas"])
    if speaker == "other" and not marked_just_before:
        return {**base, "decision": "held", "reason": "another_authority_speaks"}
    if _DIALOGUE.search(folded[:clause[0]]):
        return {**base, "decision": "held", "reason": "another_authority_quoted_in_statement"}
    if speaker == "compiler" or marked_just_before:
        basis = "statement opens with قال + the compiler's kunya"
    elif voice["unmarked_is_compiler"]:
        if _DIALOGUE.search(fold(after_report_proper(preceding, voice["kunyas"]))):
            return {**base, "decision": "held", "reason": "unmarked_voice_after_another_speaker"}
        basis = "unmarked statement in the compiler's voice (no other speaker in it or in the sentence before it)"
    else:
        return {**base, "decision": "held", "reason": "speaker_not_marked_as_compiler"}
    named = _SUBJECT_NAMED.search(folded)
    if named and named.start() <= clause[0] + 1:
        subject = named.group(1)
        if not named_subject_in_text(subject, preceding):
            return {**base, "decision": "held", "reason": "named_report_not_this_text", "named_subject": subject}
    return {**base, "decision": "compiler_statement", "grader": voice["compiler"], "grader_ar": voice["compiler_ar"],
            "attribution_basis": basis}


_SUBJECT_SKIP = {"ابن", "بن", "ابي", "ابو", "ام", "عبد", "عن", "النبي", "في", "وهو", "هذا"}
_REPORT_END_MARKERS = ("وفي الباب", "قال ابو عيسي")


def report_proper(text: str) -> str:
    """The report before the compiler's apparatus starts ('وفي الباب', 'قال أبو عيسى')."""
    folded = fold(text)
    cut = min((folded.find(m) for m in _REPORT_END_MARKERS if folded.find(m) >= 0), default=len(folded))
    return folded[:cut]


def after_report_proper(text: str, kunyas: tuple) -> str:
    """The apparatus between the end of the report and a statement: after the last compiler marker, else after
    'وفي الباب'; empty when the statement follows the report directly."""
    folded = fold(text)
    markers = [folded.rfind("قال " + k) for k in kunyas] + [folded.find("وفي الباب")]
    cut = max(markers)
    return folded[cut:] if cut >= 0 else ""


def named_subject_in_text(subject: str, preceding: str) -> bool:
    """True when the distinctive word(s) of 'حديث X' occur in the report text before the statement."""
    tokens = [t for t in subject.split() if t not in _SUBJECT_SKIP and len(t) > 2]
    if not tokens:
        return True
    words = {comparison_letters(w) for w in report_proper(preceding).split()}
    words |= {w[1:] for w in words if w[:1] in ("و", "ف", "ب")}
    return all(comparison_letters(t) in words for t in tokens[:2])   # whole words: 'عمر' never matches 'عمرو'


def split_sentences(text: str):
    """Yield (sentence, start, end) on the '.' boundary used by the sources (with optional RTL marks)."""
    position = 0
    for match in _SENTENCE_SPLIT.finditer(text or ""):
        yield text[position:match.start()], position, match.start()
        position = match.end()
    if position < len(text or ""):
        yield text[position:], position, len(text)


def report_statements(text: str, work_id: str) -> list:
    """Every report-subject grading sentence in a text, classified, with code-point offsets into the text."""
    out = []
    for sentence, start, end in split_sentences(text or ""):
        result = classify_report_statement(sentence, (text or "")[:start], work_id)
        if result is None:
            continue
        lead = len(sentence) - len(sentence.lstrip(_STRIP))
        trimmed = sentence.strip(_STRIP)
        result["char_start"] = start + lead
        result["char_end"] = start + lead + len(trimmed)
        result["source_span_verbatim"] = trimmed
        out.append(result)
    return out


def statement_canonical(term_folded: str) -> tuple[str | None, str]:
    """Canonical for a compiler statement: only when the clause minus its subject is one bare term."""
    return sunni_statement_canonical(clause_without_subject(term_folded or ""))


# --- narrator verdicts -------------------------------------------------------------------------------------------

# Exact verdicts mapped to narrator_verdict; everything else stays null (folded, whole statement must equal the key).
NARRATOR_EXACT_CANONICAL = {
    "ثقة": "thiqa", "ثقه": "thiqa", "ثقة ثبت": "thiqa_thabt", "صدوق": "saduq", "لا باس به": "la_basa_bihi",
    "ليس به باس": "la_basa_bihi", "مجهول": "majhul", "ضعيف": "daif", "متروك": "matruk", "كذاب": "kadhab",
}
NARRATOR_TERMS = [
    "ثقة ثقة", "ثقة ثبت", "ثقة", "ثقه", "ثقتين", "ثقات", "ثبت", "حجة", "مامون", "متقن", "حافظ", "صدوق", "لا باس به",
    "ليس به باس", "لا باس بحديثه", "صالح الحديث", "صالح", "شيخ", "مقبول", "مستور", "لين الحديث", "فيه لين", "لين",
    "مجهول الحال", "مجهول", "لا يعرف", "لا اعرفه", "ضعيف", "ضعيف الحديث", "ضعفه", "ضعفوه", "ليس بالقوي", "ليس بشيء",
    "ليس بثقة", "ليس بحجة", "ليس بذاك", "متروك", "متروك الحديث", "منكر الحديث", "واهي الحديث", "واه", "ساقط", "متهم",
    "كذاب", "كذبه", "كذبوه", "يكذب", "يضع الحديث", "وضاع", "وثقه", "وثق", "يكتب حديثه", "لا يحتج به", "يحتج به",
    "مضطرب الحديث", "صحيح الحديث", "مستقيم الحديث", "مقارب الحديث", "جليل", "عين", "ممدوح", "غال", "واقفي", "فطحي",
    "عامي", "مختلط", "اختلط", "يدلس", "مدلس", "فيه نظر", "وثقوه", "لا يتابع", "لم اعرفه", "لا يدري من هو", "اثني عليه",
    "محله الصدق", "جهله", "من الثقات", "احد الثقات", "ليس بقوي", "فيه ضعف", "لا شيء", "ذاهب الحديث", "اتهمه", "مقبولة",
    "فيه جهالة", "تركه", "تركوه", "لا تعرف", "تكلم فيه", "تكلموا فيه", "يتكلمون فيه", "مناكير", "لا يصح حديثه",
    "يعتبر به", "لا يكاد يعرف", "ضعف", "لم يكن به باس", "حسن الحديث", "سيء الحفظ", "يخطئ", "منكر", "سكتوا عنه",
    "يضعف", "لم يكن بالحافظ", "ليس بالمتين", "ليس بحافظ", "ليس بمعروف", "معروف", "مشهور",
]
_NT = "|".join(re.escape(t) for t in sorted(set(NARRATOR_TERMS), key=len, reverse=True))
_NARRATOR_TERM = re.compile(NOT_LETTER_BEFORE + r"(?:و|ف|ب)?(" + _NT + r")(?:ا)?" + NOT_LETTER_AFTER)  # accusative -ا
_COMPANION = re.compile(NOT_LETTER_BEFORE + r"(صحابي|صحابية|له صحبة|لها صحبة|له صحبه|له رؤية|مختلف في صحبته|شهد بدرا)"
                        + NOT_LETTER_AFTER)
_LISTED = re.compile(r"^ذكره\s+(?:[ء-ي]+\s+)?في\s+(?:كتاب\s+)?(.+)$")
_LISTING_VERDICT_WORKS = ("الثقات", "الضعفاء", "المجروحين", "الكامل", "الضعفاء والمتروكين", "الضعفاء الكبير")


def narrator_terms(text: str) -> list:
    folded = fold(text)
    out = []
    for match in _NARRATOR_TERM.finditer(folded):
        if match.group(1) not in out:
            out.append(match.group(1))
    return out


def narrator_canonical(verdict_text: str) -> tuple[str | None, str]:
    folded = fold(verdict_text).strip(" .،,:")
    folded = re.sub(r"^(?:هو|كان)\s+", "", folded)
    if folded in NARRATOR_EXACT_CANONICAL:
        return NARRATOR_EXACT_CANONICAL[folded], "exact_term"
    return None, "qualified_or_critic_specific_term_kept_verbatim"


def classify_critic_statement(text: str) -> tuple[str, str | None]:
    """(kind, listed_work) for one critic's statement: 'verdict', 'listed_in_work', 'companion_status',
    'silence' (a non-ruling), or 'mention_only' (biographical, no verdict)."""
    folded = fold(text).strip(" .،")
    if folded in ("سكت عنه", "سكت عليه"):
        return "silence", None
    listed = _LISTED.match(folded)
    if listed:
        work = listed.group(1).strip()
        if any(work.startswith(w) for w in _LISTING_VERDICT_WORKS) and not narrator_terms(work):
            return "listed_in_work", work
        if not narrator_terms(work):
            return "mention_only", work
    if narrator_terms(folded):
        return "verdict", None
    if _COMPANION.search(folded):
        return "companion_status", None
    return "mention_only", None


# hadith-kg critic register: entries that are not a named critic or named printed work.
HADITH_KG_NOT_A_CRITIC = {1472: "editorial_commentary_label_taliq"}
# Critics in hadith-kg's register who belong to the Imami tradition (by their own works); the rest default to Sunni.
HADITH_KG_IMAMI_CRITICS = {205: "al-Najashi", 2383: "al-Tusi (Muhammad ibn al-Hasan, d. 460)", 2565: "al-Kashshi"}
_BOOK_IN_QAWL = re.compile(r"^قال\s+في\s+([ء-ي]+(?:\s+[ء-ي]+){0,2}?)\s{1,3}(.+)$")


def qawl_book_and_text(qawl: str) -> tuple[str | None, str]:
    """hadith-kg often writes 'قال في التقريب  ثقة': return (book as written, the statement)."""
    match = _BOOK_IN_QAWL.match(fold(qawl))
    if match:
        return match.group(1), match.group(2).strip()
    return None, fold(qawl)


# --- Tahdhib al-Kamal: critics quoted by al-Mizzi ----------------------------------------------------------------

# Relational critics resolved only through a fixed table of reporter -> father (both named in the entry).
FATHER_OF = {
    "عبد الرحمن بن ابي حاتم": "ابو حاتم الرازي", "ابن ابي حاتم": "ابو حاتم الرازي",
    "عبد الله بن احمد بن حنبل": "احمد بن حنبل", "عبد الله بن احمد": "احمد بن حنبل", "صالح بن احمد بن حنبل": "احمد بن حنبل",
    "صالح بن احمد": "احمد بن حنبل", "عبد الله بن علي بن المديني": "علي بن المديني",
    "عبد الرحمن بن ابي حاتم الرازي": "ابو حاتم الرازي", "ابو محمد بن ابي حاتم": "ابو حاتم الرازي",
}
_RELATIONAL_CRITIC = {"ابيه", "ابي", "جده", "عمه", "اخيه"}
_SAME_CRITIC_AGAIN = {"في موضع اخر", "مرة", "ايضا", "في رواية", "مرة اخري", "في موضع"}
_NAME_STARTS = ("ابو", "ابي", "ابا", "ابن", "احمد", "محمد", "علي", "عبد", "يحيي", "يعقوب", "عثمان", "النسائي", "الترمذي",
                "البخاري", "العجلي", "الدارقطني", "الساجي", "ابراهيم", "اسحاق", "سفيان", "صالح", "الحاكم", "الخطيب")


def kunya_nominative(name: str) -> str:
    """'ابي زرعة' / 'ابا زرعة' (after عن / سألت) -> 'ابو زرعة'; 'ابيه' and a bare 'ابي' are left alone."""
    return re.sub(r"^اب[يا]\s+(?=[ء-ي])", "ابو ", name)


def split_critics(phrase: str) -> tuple[list, bool]:
    """Several critics named for one statement ('يحيى بن معين، وأبو زرعة، والنسائي'): their names, and whether an
    unnamed group ('غير واحد', 'جماعة') is also named."""
    names, unnamed = [], False
    for part in re.split(r"\s*،\s*|\s+(?=و[ء-ي])", phrase):
        part = part.strip(" ،")
        if part.startswith("و") and (part[1:] in CRITIC_ALIASES or part[1:].startswith(_NAME_STARTS)):
            part = part[1:]
        if not part:
            continue
        if part in ("غير واحد", "جماعة", "غيرهم", "غيره", "وغير واحد"):
            unnamed = True
            continue
        names.append(kunya_nominative(part))
    return names, unnamed
# Unambiguous critic spellings -> (key, display). A speaker not in this table keeps critic_key null.
CRITIC_ALIASES = {
    "يحيي بن معين": ("ibn_main", "Yahya ibn Ma'in (d. 233)"), "ابن معين": ("ibn_main", "Yahya ibn Ma'in (d. 233)"),
    "احمد بن حنبل": ("ahmad", "Ahmad ibn Hanbal (d. 241)"), "ابو حاتم": ("abu_hatim", "Abu Hatim al-Razi (d. 277)"),
    "ابو حاتم الرازي": ("abu_hatim", "Abu Hatim al-Razi (d. 277)"), "ابو زرعة": ("abu_zura", "Abu Zur'a al-Razi (d. 264)"),
    "ابو زرعة الرازي": ("abu_zura", "Abu Zur'a al-Razi (d. 264)"), "النسائي": ("nasai", "al-Nasa'i (d. 303)"),
    "ابو داود": ("abu_dawud", "Abu Dawud (d. 275)"), "البخاري": ("bukhari", "al-Bukhari (d. 256)"),
    "الترمذي": ("tirmidhi", "al-Tirmidhi (d. 279)"), "ابن حبان": ("ibn_hibban", "Ibn Hibban (d. 354)"),
    "العجلي": ("ijli", "al-'Ijli (d. 261)"), "احمد بن عبد الله العجلي": ("ijli", "al-'Ijli (d. 261)"),
    "ابن سعد": ("ibn_sad", "Ibn Sa'd (d. 230)"), "محمد بن سعد": ("ibn_sad", "Ibn Sa'd (d. 230)"),
    "يعقوب بن شيبة": ("yaqub_b_shayba", "Ya'qub ibn Shayba (d. 262)"),
    "علي بن المديني": ("ibn_al_madini", "'Ali ibn al-Madini (d. 234)"), "ابن المديني": ("ibn_al_madini", "'Ali ibn al-Madini (d. 234)"),
    "الدارقطني": ("daraqutni", "al-Daraqutni (d. 385)"), "ابو الحسن الدارقطني": ("daraqutni", "al-Daraqutni (d. 385)"),
    "ابن عدي": ("ibn_adi", "Ibn 'Adi (d. 365)"), "ابو احمد بن عدي": ("ibn_adi", "Ibn 'Adi (d. 365)"),
    "ابن خراش": ("ibn_khirash", "Ibn Khirash (d. 283)"), "الساجي": ("saji", "Zakariyya al-Saji (d. 307)"),
    "يعقوب بن سفيان": ("yaqub_b_sufyan", "Ya'qub ibn Sufyan al-Fasawi (d. 277)"),
    "محمد بن عبد الله بن عمار": ("ibn_ammar", "Muhammad ibn 'Abd Allah ibn 'Ammar (d. 242)"),
    "ابن نمير": ("ibn_numayr", "Muhammad ibn 'Abd Allah ibn Numayr (d. 234)"),
    "محمد بن عبد الله بن نمير": ("ibn_numayr", "Muhammad ibn 'Abd Allah ibn Numayr (d. 234)"),
    "ابو احمد الحاكم": ("abu_ahmad_hakim", "Abu Ahmad al-Hakim (d. 378)"),
    "الحاكم ابو عبد الله": ("hakim", "al-Hakim al-Naysaburi (d. 405)"), "ابن خزيمة": ("ibn_khuzayma", "Ibn Khuzayma (d. 311)"),
    "ابراهيم بن يعقوب الجوزجاني": ("juzajani", "al-Juzajani (d. 259)"), "الجوزجاني": ("juzajani", "al-Juzajani (d. 259)"),
    "ابن شاهين": ("ibn_shahin", "Ibn Shahin (d. 385)"), "البزار": ("bazzar", "al-Bazzar (d. 292)"),
    "عثمان بن ابي شيبة": ("uthman_b_abi_shayba", "'Uthman ibn Abi Shayba (d. 239)"),
    "الخطيب ابو بكر": ("khatib", "al-Khatib al-Baghdadi (d. 463)"), "ابو بكر الخطيب": ("khatib", "al-Khatib al-Baghdadi (d. 463)"),
    "مسلم": ("muslim", "Muslim ibn al-Hajjaj (d. 261)"),
}
_MIZZI_STATEMENT = re.compile(r"(?:^|[.؛]\s*|\)\s*\.?\s*)(و?قال)\s+([^:.]{2,120}?)\s*:\s*")
_ASKED = re.compile(r"^(?:و)?(?:سئل|سالت|سالنا)\s+([ء-ي]+(?:\s+[ء-ي]+){0,5}?)\s+عن(ه|ها)\s*،?\s*(?:ف)?(?:قال|فقال)\s*:\s*")
_ASKED_OTHER = re.compile(r"^(?:و)?(?:سئل|سالت|سالنا)\s+[ء-ي]+(?:\s+[ء-ي]+){0,5}?\s+عن\s+[ء-ي]")
_NOT_VERDICT_OPENERS = re.compile(r"^(?:مات|توفي|ولد|حدثنا|اخبرنا|حدثني|اخبرني|سمعت|كان\s+(?:مولده|ينزل|يسكن)|في\s+سنة|سنة)"
                                  + NOT_LETTER_AFTER)
VERDICT_WINDOW_WORDS = 12


def resolve_critic(speaker_folded: str) -> dict:
    """Critic from al-Mizzi's 'قال X، عن Y' phrase: Y when quoted through X; father table for 'عن ابيه'."""
    speaker = re.sub(r"\s*\(\d+\)\s*", " ", speaker_folded).strip(" ،,")
    speaker = re.sub(r"\s+(?:في\s+موضع\s+اخر|ايضا|مرة|في\s+رواية)$", "", speaker).strip(" ،,")
    reporter = None
    parts = re.split(r"\s*،?\s+عن\s+", speaker)
    if len(parts) > 1:
        reporter, critic = " عن ".join(parts[:-1]).strip(" ،"), parts[-1].strip(" ،")
    else:
        critic = speaker
    if critic in ("ابيه", "ابي"):
        father = FATHER_OF.get(reporter or "")
        if father is None:
            return {"critic_ar": None, "reporter_ar": reporter, "resolution": "relational_critic_unresolved"}
        critic = father
    if speaker in _SAME_CRITIC_AGAIN:
        return {"critic_ar": None, "reporter_ar": None, "resolution": "same_critic_as_previous_statement"}
    if "،" in critic or re.search(r"\s+و(?:ابو|ابي|ابن|احمد|محمد|علي|يحيي|النسائي|العجلي|الدارقطني)", critic):
        names, unnamed = split_critics(critic)
        return {"critic_ar": critic, "critics_ar": names, "unnamed_others": unnamed, "reporter_ar": reporter,
                "resolution": "several_critics_in_one_statement"}
    critic = kunya_nominative(critic)
    key = CRITIC_ALIASES.get(critic)
    return {"critic_ar": critic, "reporter_ar": reporter, "critic_key": key[0] if key else None,
            "critic_display": key[1] if key else None, "resolution": "named" if reporter is None else "quoted_through_reporter"}


def mizzi_statements(entry_text: str) -> list:
    """Critic statements quoted by al-Mizzi in one Tahdhib al-Kamal entry (verbatim), each with its resolution.

    `decision` is 'verdict' (attributable, a jarh/ta'dil term in the opening words) or 'held' with a reason.
    """
    out = []
    previous = None
    matches = list(_MIZZI_STATEMENT.finditer(entry_text))
    for index, match in enumerate(matches):
        body_end = matches[index + 1].start() if index + 1 < len(matches) else len(entry_text)
        body = entry_text[match.end():body_end].strip()
        sentence = re.split(r"(?<=[.])\s", body, maxsplit=1)[0].strip()
        speaker = fold(match.group(2))
        if not speaker or re.search(r"\d", speaker) and len(speaker) < 4:
            continue
        resolved = resolve_critic(speaker)
        if resolved["resolution"] == "same_critic_as_previous_statement":
            if previous is None:
                continue
            resolved = {**previous, "resolution": "same_critic_as_previous_statement"}
        elif resolved["resolution"] != "relational_critic_unresolved":
            previous = resolved
        folded_body = fold(sentence)
        asked = _ASKED.match(folded_body)
        record = {"speaker_ar_verbatim": match.group(2).strip(), "statement_ar": sentence[:600],
                  "char_start": match.start(), **resolved}
        if asked:
            asked_name = asked.group(1)
            folded_body = folded_body[asked.end():]
            if asked_name in ("ابي", "ابا") or asked_name.startswith("ابي "):
                father = FATHER_OF.get(resolved.get("critic_ar") or "")
                if asked_name == "ابي" and father:
                    record.update({"reporter_ar": resolved.get("critic_ar"), "critic_ar": father,
                                   "resolution": "asked_father_of_reporter"})
                else:
                    asked_name = re.sub(r"^ابا\s", "ابو ", re.sub(r"^ابي\s", "ابو ", asked_name))
                    record.update({"reporter_ar": resolved.get("critic_ar"), "critic_ar": asked_name,
                                   "resolution": "asked_named_critic"})
            else:
                record.update({"reporter_ar": resolved.get("critic_ar"), "critic_ar": asked_name, "resolution": "asked_named_critic"})
            key = CRITIC_ALIASES.get(record["critic_ar"] or "")
            record["critic_key"], record["critic_display"] = (key[0], key[1]) if key else (None, None)
        elif _ASKED_OTHER.match(folded_body):
            out.append({**record, "decision": "held", "reason": "question_about_someone_else"})
            continue
        record["verdict_ar_folded"] = folded_body[:300]
        opening = " ".join(folded_body.split()[:VERDICT_WINDOW_WORDS])
        if record["resolution"] == "relational_critic_unresolved":
            out.append({**record, "decision": "held", "reason": record["resolution"]})
            continue
        if _NOT_VERDICT_OPENERS.match(folded_body):
            continue
        terms = narrator_terms(opening)
        if not terms:
            continue
        if re.search(NOT_LETTER_BEFORE + r"(?:ابوه|ابنه|اخوه|جده|عمه)" + NOT_LETTER_AFTER, opening):
            out.append({**record, "decision": "held", "reason": "subject_may_be_a_relative", "terms": terms})
            continue
        if record.get("critic_ar") in _RELATIONAL_CRITIC or (record["resolution"] == "several_critics_in_one_statement"
                                                             and set(record["critics_ar"]) & _RELATIONAL_CRITIC):
            out.append({**record, "decision": "held", "reason": "relational_critic_unresolved"})
            continue
        if record["resolution"] == "several_critics_in_one_statement":
            for name in record["critics_ar"]:
                key = CRITIC_ALIASES.get(name)
                out.append({**record, "critic_ar": name, "critic_key": key[0] if key else None,
                            "critic_display": key[1] if key else None, "decision": "verdict", "terms": terms,
                            "shared_statement_named_critics": record["critics_ar"]})
            continue
        out.append({**record, "decision": "verdict", "terms": terms})
    for match in re.finditer(r"وذكره\s+ابن\s+حبان\s+في\s+كتاب\s+\"?الثقات", fold(entry_text)):
        out.append({"speaker_ar_verbatim": "ذكره ابن حبان في كتاب الثقات", "statement_ar": "وذكره ابن حبان في كتاب الثقات",
                    "critic_ar": "ابن حبان", "critic_key": "ibn_hibban", "critic_display": "Ibn Hibban (d. 354)",
                    "reporter_ar": None, "resolution": "named", "decision": "listed_in_work", "terms": [],
                    "listed_work": "الثقات", "char_start": None, "verdict_ar_folded": "ذكره في كتاب الثقات"})
    return out


# --- al-Najashi and al-Tusi: the author's own verdict words ------------------------------------------------------

IMAMI_RIJAL_TERMS = ["ثقة ثقة", "ثقة", "ثقه", "ضعيف جدا", "ضعيف", "عين", "وجه", "جليل", "غال", "واقفي", "واقف", "فطحي",
                     "عامي", "مجهول", "ممدوح", "صحيح الحديث", "صحيح الرواية", "مضطرب الحديث", "مضطرب", "ليس بذاك",
                     "لا باس به", "صالح الرواية", "مرتفع القول", "متهم", "كذاب", "مخلط"]
_IRT = re.compile(NOT_LETTER_BEFORE + r"(?:و|ف)?(" + "|".join(re.escape(t) for t in IMAMI_RIJAL_TERMS) + r")" + NOT_LETTER_AFTER)
_QUOTE_MARKERS = re.compile(NOT_LETTER_BEFORE + r"(?:قال|وقال|قاله|ذكره|ذكر|ذكرهم|حدثنا|اخبرنا|حدثني|اخبرني|وقيل|قيل|يقال)"
                            + NOT_LETTER_AFTER)
_OTHER_SUBJECT = re.compile(NOT_LETTER_BEFORE + r"(?:ابوه|ابنه|اخوه|جده|عمه|ابن عمه|وابنه|واخوه|وابوه|ابناه|اخواه|اخته|امه|بنته)"
                            + NOT_LETTER_AFTER)
# 'وجه' and 'عين' are verdicts only in their technical idioms.
_WAJH_IDIOM = re.compile(r"(?:وجه|عين)\s+(?:من\s+)?(?:وجوه\s+)?(?:في\s+)?(?:اصحابنا|الطائفة|الشيعة|من\s+عيون\s+اصحابنا)|"
                         r"(?:من\s+)?(?:وجوه|عيون)\s+(?:اصحابنا|الطائفة)|وجها\s+في\s+اصحابنا|وجه\s+من\s+وجوه")


def imami_rijal_verdicts(entry_text: str) -> list:
    """Verdict clauses in al-Najashi's or al-Tusi's own voice. Each clause is a 'verdict' or 'held' with a reason."""
    text = re.sub(r"\"[^\"]{0,600}\"", lambda m: " " * len(m.group(0)), entry_text)   # Imams' speech in quotes
    folded = fold(text)
    out = []
    for clause in re.split(r"[.،؛]", folded):
        clause = clause.strip()
        if not clause:
            continue
        terms = []
        for match in _IRT.finditer(clause):
            term = match.group(1)
            if term in ("وجه", "عين") and not _WAJH_IDIOM.search(clause):
                continue
            if term not in terms:
                terms.append(term)
        if not terms and _WAJH_IDIOM.search(clause):
            terms.append("وجه")
        if not terms:
            continue
        first = _IRT.search(clause)
        before = clause[: first.start()] if first else clause
        record = {"clause_ar_folded": clause, "terms": terms,
                  "verdict_ar_folded": clause[first.start():].strip() if first else clause}
        if _QUOTE_MARKERS.search(before) or re.search(r"(?:قال|ذكره|قاله)\s+(?:ابن|ابو|احمد|محمد|الحسين|علي)", clause):
            out.append({**record, "decision": "held", "reason": "quoted_or_reported_not_the_author"})
        elif _OTHER_SUBJECT.search(before):
            out.append({**record, "decision": "held", "reason": "subject_may_be_a_relative"})
        elif re.search(r"(?:ضعفه|وثقه|ضعفوه|وثقوه)\s+(?:اصحابنا|اصحاب|القميون|ابن)", clause):
            out.append({**record, "decision": "held", "reason": "reports_others_judgement"})
        else:
            out.append({**record, "decision": "verdict"})
    return out


# --- hadith-kg report grading: why it is excluded ----------------------------------------------------------------

HADITH_KG_COMPUTED_FIELDS = {
    "hadiths.matn / hadiths.matn_no": "hukm label per report, coded 0-8 on hadithdb's own scale; no grader is named",
    "sanads.matn / sanads.matn_no": "hukm label per chain; equals a function of the chain's weakest narrator rank (max_rank) and continuity",
    "sanads.hukum": "templated sentence assembled from narrator rank wording ('إسناد ضعيف فيه X وهو ضعيف الحديث'); no grader named",
    "sanads.max_rank": "weakest narrator's rank number in the chain, computed by the source",
    "meaning_groups.matn_no / tarafs.matn": "overall hukm per meaning group, computed across chains",
    "rawis.rank / rawis.rank_no": "one rank wording per narrator with no critic named (Taqrib-like wording, unattributed)",
}


def is_templated_hukum(hukum: str) -> bool:
    """True for hadith-kg's machine sentence shapes (all observed values start with one of these frames)."""
    folded = fold(hukum)
    return bool(re.match(r"^(?:اسناده|اسناد)\s", folded)) and not re.search(
        r"(?:قال|صححه|حسنه|ضعفه)\s+(?:الالباني|الارناووط|الترمذي|الحاكم|الذهبي|ابن\s+حجر)", folded)


# --- perspective matrix: aspects -----------------------------------------------------------------------------------
# Keys shared with the rijal lane (datasets/hadith-data/rijal/build_rijal_layer.py ASPECTS); `aspect_detail` adds the
# owner's finer distinction only where the passage's own words make it.

ASPECT_TERMS = {
    "doctrine": ["غال", "واقفي", "واقف", "فطحي", "عامي", "يتشيع", "شيعي", "رافضي", "قدري", "رمي بالقدر", "مرجئ", "ارجاء",
                 "ناصبي", "خارجي", "جهمي", "معتزلي", "رمي بالتشيع", "رمي بالارجاء", "مرتفع القول", "فاسد المذهب", "من اصحابنا"],
    "precision_memory": ["حافظ", "متقن", "ثبت", "ضابط", "سيء الحفظ", "يخطئ", "كثير الخطا", "يهم", "له اوهام", "وهم", "لين",
                         "لين الحديث", "فيه لين", "مضطرب", "مضطرب الحديث", "تغير", "تغير حفظه", "اختلط", "مختلط", "مخلط",
                         "لم يكن بالحافظ", "ليس بحافظ", "يغلط", "كثير الغلط", "الغلط"],
    "specific_defect": ["يدلس", "مدلس", "تدليس", "يرسل", "كثير الارسال", "مناكير", "له مناكير", "منكر الحديث",
                        "لا يتابع", "يتلقن", "يسرق الحديث", "يضع الحديث", "وضاع", "متهم"],
}
_ASPECT_RE = {aspect: re.compile(NOT_LETTER_BEFORE + r"(?:و|ف|ب)?(?:" + "|".join(re.escape(t) for t in sorted(terms, key=len, reverse=True))
                                 + r")(?:ا)?" + NOT_LETTER_AFTER) for aspect, terms in ASPECT_TERMS.items()}
_RELIABILITY_CORE = re.compile(NOT_LETTER_BEFORE + r"(?:و|ف|ب)?(?:ثقة|ثقه|ثقات|صدوق|لا باس|ليس به باس|ضعيف|ضعفه|متروك|كذاب|"
                               r"ليس بشيء|ليس بالقوي|ليس بثقة|مجهول|لا يعرف|مقبول|حجة|مامون|صالح|لا يحتج|يحتج|جليل|وجه|عين|"
                               r"صحيح الحديث|يكتب حديثه|فيه نظر|ذاهب|تركوه|وثقه|وثق)(?:ا)?" + NOT_LETTER_AFTER)


def aspects_of(text: str, kind: str) -> tuple[str, list]:
    """(rijal-lane aspect key, aspect_detail list) for one verdict passage. Companion status and listings have fixed
    keys; otherwise the detail lists each aspect the words themselves speak to, in a fixed order."""
    if kind in ("companion_status",):
        return "generation_or_imam", ["companion_status"]
    folded = fold(text)
    detail = []
    if _RELIABILITY_CORE.search(folded) or kind == "listed_in_work":
        detail.append("reliability")
    for aspect in ("precision_memory", "doctrine", "specific_defect"):
        if _ASPECT_RE[aspect].search(folded):
            detail.append(aspect)
    if not detail or detail[0] == "reliability":
        key = "verdict_term"
    elif "doctrine" in detail and len(detail) == 1:
        key = "doctrinal_or_other_note"
    else:
        key = "reliability_qualifier"
    return key, detail or ["not_distinguished"]
