"""Table-driven tests for the lexicon free-text parsers (python -B -m unittest test_lexicon_raw_parsing)."""

import unittest

import lexicon_raw_parsing as parsing


class YearExpressionTable(unittest.TestCase):
    CASES = [
        # cell, calendar key, relation, year_min, year_max, qualifiers
        ("53 BH/570 CE (9th Rabi' awwal) (Makkah)", "BH", "single", -53, -53, []),
        ("~43 AH/664 CE or 51 AH (Egypt)[ Natural ]", "AH", "alternatives", 43, 51, ["circa"]),
        ("42-55 AH/662-74 CE (Medinah)[ Natural ]", "CE", "range", 662, 674, []),
        ("after 40 AH (Medinah)[ Natural ]", "AH", "single", 40, None, ["after"]),
        ("63 AH/683 CE or Before (Medina)[ Natural ]", "AH", "single", None, 63, ["before"]),
        ("before after  70 AH ()[ Natural ]", "AH", "single", None, None, ["unresolved_after_and_before"]),
        ("57 BH/566 CE (approx) (Makkah)", "BH", "single", -57, -57, ["estimated"]),
    ]

    def test_table(self):
        for cell, era, relation, low, high, qualifiers in self.CASES:
            with self.subTest(cell=cell):
                date = parsing.parse_place_cell(cell)["date"]
                span = date["calendars"][era]
                self.assertEqual((span["relation"], span["year_min"], span["year_max"]), (relation, low, high))
                self.assertEqual(date["qualifiers"], qualifiers)

    def test_default_cell_has_no_date_and_keeps_reason(self):
        parsed = parsing.parse_place_cell("()[ Natural ]")
        self.assertFalse(parsed["date"]["present"])
        self.assertEqual((parsed["places"], parsed["reason_text"]), ([], "Natural"))

    def test_place_is_not_an_estimate_marker(self):
        self.assertEqual(parsing.parse_place_cell("57 BH/566 CE (approx) (Makkah)")["places"], ["Makkah"])


class MarkerCells(unittest.TestCase):
    def test_generation_cell(self):
        marker = parsing.parse_generation_cell("Succ. (Taba' Tabi') [7th generation] [Maliki]")
        self.assertEqual((marker["category"], marker["generation_number"], marker["other_bracket_labels"]),
                         ("successor_of_followers", 7, ["Maliki"]))

    def test_assessment_cell(self):
        cell = parsing.parse_area_of_interest("Narrator[Grade:Thiqah] [ ع  -  ثقة ]")
        self.assertEqual((cell["english_grade_label"], cell["symbols_ar"], cell["term_ar"]), ("Thiqah", "ع", "ثقة"))
        symbols_only = parsing.parse_area_of_interest("Narrator[Grade:Undefined] [ د - ]")
        self.assertEqual((symbols_only["symbols_ar"], symbols_only["term_ar"]), ("د", None))


if __name__ == "__main__":
    unittest.main()
