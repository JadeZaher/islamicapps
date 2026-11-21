"""Name invariant: one key that is identical for spelling variants of the same Arabic name (pure logic).

An ordered list of small, individually named folding rules applied after the project's own normalization
(regen.narrator_normalize, passed in as `base_normalize`; this module never modifies it). Rules never strip the
definite article and never drop a name component, so two different names cannot become equal by omission.
A key is a lookup aid only: equal keys are a PROPOSED match for review, never an identity.
Matching in this repository is Arabic-only (see measure_tier0_resolver_delta.py), so there is no Latin invariant.
"""

import re

_LETTER = "ء-ي"
_NOT_LETTER_OR_SPACE = re.compile(rf"[^{_LETTER} ]")
_SPACES = re.compile(r"\s+")
_CONNECTORS = {"بن", "بنت"}

_PERSIAN_URDU = str.maketrans({"ی": "ي", "ے": "ي", "ک": "ك", "ھ": "ه", "ہ": "ه", "ە": "ه", "ۃ": "ة"})
_HONORIFIC = re.compile(
    rf"(?<![{_LETTER}])(?:"
    r"رضي الله عن(?:ه|ها|هما|هم|هن)|"
    r"عليه(?:ما|م)? السلام|عليها السلام|"
    r"صلي الله عليه(?: واله)?(?: وسلم)?|سلام الله عليه(?:ا|م)?|"
    r"رحمه(?:م|ا)? الله(?: تعالي)?"
    rf")(?![{_LETTER}])"
)
_THEOPHORIC_JOINED = re.compile(rf"^عبد(ال[{_LETTER}]{{2,}})$")
_KUNYA_JOINED = re.compile(rf"^(ابو|ابي|ابا)(ال[{_LETTER}]{{2,}})$")


def _tokens(text: str) -> list[str]:
    return text.split()


def persian_urdu_letter_variants(text: str) -> str:
    """Persian/Urdu yeh, kaf and heh forms to the Arabic letters (e.g. ضعیف)."""
    return text.translate(_PERSIAN_URDU)


def punctuation_and_whitespace(text: str) -> str:
    """Drop everything that is not an Arabic letter, turn it into a space, collapse spaces."""
    return _SPACES.sub(" ", _NOT_LETTER_OR_SPACE.sub(" ", text)).strip()


def hamza_on_waw_and_ya_carriers(text: str) -> str:
    """Hamza on waw/ya carriers to the bare carrier. (Alef carriers are already folded by the base.)"""
    return text.replace("ؤ", "و").replace("ئ", "ي")


def honorific_formula_strip(text: str) -> str:
    """Remove blessing/honorific formulas as whole phrases (never lone letters such as ع or ص)."""
    return _SPACES.sub(" ", _HONORIFIC.sub(" ", text)).strip()


def nasab_connector_forms(text: str) -> str:
    """ابن to بن and ابنة to بنت. The relational pronoun ابنه ('his son') is deliberately left alone."""
    mapping = {"ابن": "بن", "ابنة": "بنت"}
    return " ".join(mapping.get(token, token) for token in _tokens(text))


def theophoric_compound_spacing(text: str) -> str:
    """عبدالله and عبدالرحمن to 'عبد الله' / 'عبد الرحمن' (ال-names only; عبيد is a different name)."""
    out = []
    for token in _tokens(text):
        match = _THEOPHORIC_JOINED.match(token)
        out.extend(["عبد", match.group(1)] if match else [token])
    return " ".join(out)


def kunya_compound_spacing(text: str) -> str:
    """ابوالقاسم to 'ابو القاسم' (joined kunya head plus definite-article name)."""
    out = []
    for token in _tokens(text):
        match = _KUNYA_JOINED.match(token)
        out.extend([match.group(1), match.group(2)] if match else [token])
    return " ".join(out)


def kunya_case_forms(text: str) -> str:
    """ابي/ابا to ابو when a non-connector name token follows (keeps the name Ubayy in 'ابي بن كعب')."""
    tokens = _tokens(text)
    out = []
    for index, token in enumerate(tokens):
        follows = tokens[index + 1] if index + 1 < len(tokens) else None
        out.append("ابو" if token in ("ابي", "ابا") and follows and follows not in _CONNECTORS else token)
    return " ".join(out)


def ta_marbuta_to_ha(text: str) -> str:
    """ة to ه (طلحة / طلحه)."""
    return text.replace("ة", "ه")


# Ordered: later rules assume earlier ones ran (letters-only text first, ابنة to بنت before ta marbuta).
INVARIANT_RULES = (
    ("persian_urdu_letter_variants", persian_urdu_letter_variants),
    ("punctuation_and_whitespace", punctuation_and_whitespace),
    ("hamza_on_waw_and_ya_carriers", hamza_on_waw_and_ya_carriers),
    ("honorific_formula_strip", honorific_formula_strip),
    ("nasab_connector_forms", nasab_connector_forms),
    ("theophoric_compound_spacing", theophoric_compound_spacing),
    ("kunya_compound_spacing", kunya_compound_spacing),
    ("kunya_case_forms", kunya_case_forms),
    ("ta_marbuta_to_ha", ta_marbuta_to_ha),
)
RULE_NAMES = tuple(name for name, _ in INVARIANT_RULES)


def trace_name_invariant(name: str, disabled_rules=frozenset(), base_normalize=None) -> tuple[str, list]:
    """Return (key, [(rule, before, after), ...]) listing only the rules that changed the text."""
    text = base_normalize(name) if base_normalize else (name or "")
    changes = []
    for rule_name, rule in INVARIANT_RULES:
        if rule_name in disabled_rules:
            continue
        after = rule(text)
        if after != text:
            changes.append((rule_name, text, after))
        text = after
    return _SPACES.sub(" ", text).strip(), changes


def compute_name_invariant(name: str, disabled_rules=frozenset(), base_normalize=None) -> str:
    """Key identical for spelling variants of one name; '' when the text holds no Arabic letters."""
    return trace_name_invariant(name, disabled_rules, base_normalize)[0]
