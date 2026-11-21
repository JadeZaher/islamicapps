"""Table-driven tests for name_invariant (names taken from the real corpus, registry and spot-check sample).

Run from this directory: python -B -m unittest test_name_invariant
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import diagnostic_common as common  # noqa: E402
from name_invariant import RULE_NAMES, compute_name_invariant, trace_name_invariant  # noqa: E402

BASE = common.load_regen().narrator_normalize     # the project's own normalization, reused unmodified


def key(name, disabled=frozenset()):
    return compute_name_invariant(name, disabled, BASE)


class VariantsShareAKey(unittest.TestCase):
    def test_each_rule_is_what_makes_the_pair_equal(self):
        # (variant spelling, canonical spelling, the one rule that must be responsible)
        table = [
            ("ضعیف", "ضعيف", "persian_urdu_letter_variants"),
            ("سعد بن عبد الله ( رضي الله عنه", "سعد بن عبد الله", "punctuation_and_whitespace"),
            ("رؤبة بن العجاج", "روبة بن العجاج", "hamza_on_waw_and_ya_carriers"),
            ("عائشة بنت قدامة بن مظعون الجمحي رضي الله عنها", "عائشة بنت قدامة بن مظعون الجمحي",
             "honorific_formula_strip"),
            ("مالك ابن أنس", "مالك بن أنس", "nasab_connector_forms"),
            ("عبدالله بن عباس", "عبد الله بن عباس", "theophoric_compound_spacing"),
            ("ابوالقاسم", "ابو القاسم", "kunya_compound_spacing"),
            ("أبي سلمة", "أبو سلمة", "kunya_case_forms"),
            ("زيد بن حارثه", "زيد بن حارثة", "ta_marbuta_to_ha"),
        ]
        for variant, canonical, rule in table:
            with self.subTest(variant=variant, rule=rule):
                self.assertEqual(key(variant), key(canonical))
                self.assertNotEqual(key(variant, frozenset({rule})), key(canonical, frozenset({rule})),
                                    "switching the responsible rule off must separate the pair")

    def test_base_normalization_already_handles_alef_carriers(self):
        self.assertEqual(key("إبراهيم بن أدهم"), key("ابراهيم بن ادهم"))
        self.assertEqual(key("أَبِي هُرَيْرَةَ"), key("ابو هريره"))     # diacritics, kunya case, ta marbuta


class DifferentNamesStayDifferent(unittest.TestCase):
    def test_pairs_that_must_not_merge(self):
        table = [
            ("عبد الله", "عبيد الله"),                          # Abd vs Ubayd
            ("ابو الحسن", "ابو حسن"),                           # definite article is never stripped
            ("محمد بن علي", "علي بن محمد"),                      # order matters
            ("ابي بن كعب", "ابو كعب"),                          # Ubayy (an ism) is not a kunya
            ("علي", "علي بن ابراهيم"),                          # no component dropped
            ("عمر", "عمرو"),
            ("محمد", "محمود"),
            ("ابنة", "ابنه"),                                  # daughter-of connector vs 'his son'
            ("ابي", "ابو"),                                    # bare 'my father' is not folded
            ("عبد الله بن ابي بكر", "عبد الله بن بكر"),          # nasab kunya keeps its ابو
            ("سفيان", "سفيان الثوري"),
        ]
        for left, right in table:
            with self.subTest(left=left, right=right):
                self.assertNotEqual(key(left), key(right))


class RuleSwitchesAndTrace(unittest.TestCase):
    def test_trace_lists_only_rules_that_changed_the_text(self):
        _, changes = trace_name_invariant("أبي سلمة", base_normalize=BASE)
        self.assertEqual([c[0] for c in changes], ["kunya_case_forms", "ta_marbuta_to_ha"])
        _, none = trace_name_invariant("سعيد بن جبير", base_normalize=BASE)
        self.assertEqual(none, [])

    def test_text_without_letters_gives_empty_key(self):
        self.assertEqual(key("( 123 ، )"), "")

    def test_all_rules_listed_in_documented_order(self):
        self.assertEqual(RULE_NAMES[0], "persian_urdu_letter_variants")
        self.assertEqual(RULE_NAMES[-1], "ta_marbuta_to_ha")
        self.assertLess(RULE_NAMES.index("nasab_connector_forms"), RULE_NAMES.index("ta_marbuta_to_ha"))


if __name__ == "__main__":
    unittest.main()
