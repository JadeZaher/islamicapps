"""Name invariant for diagnostics: one key for spelling variants of the same Arabic name (pure logic).

The adopted rules live in the canonical pipeline (regen_unified_csvs.NARRATOR_FOLD_RULES, fold_kunya_case_forms,
strip_blessing_formulas) and are imported here, never re-implemented. Only the two rules that were NOT adopted
(hamza on waw/ya carriers, ta marbuta to ha) are defined locally, so their effect can still be measured.
A key is a lookup aid: equal keys are a PROPOSED match for review, never an identity.
Matching in this repository is Arabic-only, so there is no Latin invariant.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import diagnostic_common as common  # noqa: E402

_regen = common.load_regen()


def hamza_on_waw_and_ya_carriers(text: str) -> str:
    """Not adopted: hamza on waw/ya carriers to the bare carrier."""
    return text.replace("ؤ", "و").replace("ئ", "ي")


def ta_marbuta_to_ha(text: str) -> str:
    """Not adopted: ة to ه."""
    return text.replace("ة", "ه")


_canonical = dict(_regen.NARRATOR_FOLD_RULES)
INVARIANT_RULES = (
    ("persian_urdu_letter_variants", _canonical["persian_urdu_letter_variants"]),
    ("punctuation_and_whitespace", _canonical["punctuation_and_whitespace"]),
    ("hamza_on_waw_and_ya_carriers", hamza_on_waw_and_ya_carriers),
    ("honorific_formula_strip", _regen.strip_blessing_formulas),
    ("nasab_connector_forms", _canonical["nasab_connector_forms"]),
    ("theophoric_compound_spacing", _canonical["theophoric_compound_spacing"]),
    ("kunya_compound_spacing", _canonical["kunya_compound_spacing"]),
    ("kunya_case_forms", _regen.fold_kunya_case_forms),
    ("ta_marbuta_to_ha", ta_marbuta_to_ha),
)
RULE_NAMES = tuple(name for name, _ in INVARIANT_RULES)
DIAGNOSTIC_ONLY_RULE_NAMES = ("hamza_on_waw_and_ya_carriers", "ta_marbuta_to_ha")
ADOPTED_RULE_NAMES = tuple(name for name in RULE_NAMES if name not in DIAGNOSTIC_ONLY_RULE_NAMES)
_SPACES = re.compile(r"\s+")


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
    """Key identical for spelling variants of one name; '' when the text holds no letters."""
    return trace_name_invariant(name, disabled_rules, base_normalize)[0]
