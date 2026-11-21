"""Pure logic of the gap-fill runner: terminology selection, prompt choice, guards. No network. Run: python -B -m unittest test_translate_gap_fill (from this directory)."""

import importlib.util
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("translate_gap_fill_under_test", HERE / "translate_gap_fill.py")
run = importlib.util.module_from_spec(spec)
sys.modules["translate_gap_fill_under_test"] = run
spec.loader.exec_module(run)


def chosen(text):
    return [entry["ar"] for entry in run.select_terms(text)]


class TerminologySelectionTests(unittest.TestCase):
    def test_longest_match_wins_and_shorter_overlaps_are_dropped(self):
        # "يا رسول الله" must not also yield "رسول الله" or "الله" (the 'O the Messenger of Allah' regression).
        self.assertEqual(chosen("فقال يا رسول الله"), ["يا رسول الله"])

    def test_vocalized_and_alef_variants_match(self):
        self.assertEqual(chosen("قَالَ رَسُولُ اللَّهِ صَلَّى اللَّهُ عَلَيْهِ وَسَلَّمَ"), ["رسول الله", "صلى الله عليه وسلم"])
        self.assertIn("أبو هريرة", chosen("عن ابو هريرة"))

    def test_clitic_prefix_matches_but_a_longer_word_does_not(self):
        self.assertIn("الصلاة", chosen("بالصلاة"))
        self.assertEqual(chosen("الحجر الأسود"), [])  # al-Hajar is not al-Hajj

    def test_order_of_appearance_and_cap(self):
        text = " ".join(["الزكاة", "الحج", "الإيمان", "الإسلام"] * 5)
        self.assertEqual(chosen(text), ["الزكاة", "الحج", "الإيمان", "الإسلام"])
        self.assertLessEqual(len(run.select_terms(" ".join(t["ar"] for t in run.TERMS_BLOCK["terms"]))), run.TERMS_BLOCK["max_terms_per_request"])


class PromptChoiceTests(unittest.TestCase):
    def test_no_match_falls_back_to_the_base_prompt(self):
        prompt, version, terms = run.build_prompt("كتاب جميل", "terminology")
        self.assertEqual((version, terms), (run.BASE_VERSION, []))
        self.assertTrue(prompt.endswith("كتاب جميل"))

    def test_match_uses_the_terminology_prompt_with_reference_lines(self):
        prompt, version, terms = run.build_prompt("قال رسول الله", "terminology")
        self.assertEqual(version, run.TERMS_BLOCK["version"])
        self.assertIn("رسول الله translates to the Messenger of Allah", prompt)
        self.assertTrue(prompt.endswith("قال رسول الله"))

    def test_base_variant_never_adds_terms(self):
        self.assertEqual(run.build_prompt("قال رسول الله", "base")[1:], (run.BASE_VERSION, []))


class GuardTests(unittest.TestCase):
    def test_guards_reject_macron_transliteration_and_an_echoed_reference_list(self):
        self.assertEqual(run.extra_guards("ʿAli and Ibrāhīm", "علي وإبراهيم"), ["diacritic_transliteration"])
        self.assertEqual(run.extra_guards("رسول الله translates to the Messenger", "قال"), ["terminology_echo"])
        self.assertEqual(run.extra_guards("ʿAli said the Qurʾan is clear.", "قال علي"), [])

    def test_digit_groups_compare_arabic_indic_and_ascii(self):
        self.assertEqual(run.digit_groups("حديث ١٢٣ و 45"), run.digit_groups("hadith 123 and 45"))
        self.assertNotEqual(run.digit_groups("٣٠ يوما"), run.digit_groups("forty days"))


if __name__ == "__main__":
    unittest.main()
