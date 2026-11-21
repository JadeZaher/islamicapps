"""Table-driven tests for rijal_parsing (pure logic). Run: python -B -m unittest test_rijal_parsing (this directory)."""

import unittest

import rijal_parsing as rp


def deaths(text, tabaqa=None, convention=True):
    rows = rp.parse_death_statements(rp.fold_for_phrases(text), tabaqa, convention)
    return [(r["year_min"], r["year_max"], r["precision"]) for r in rows]


class DeathYearTest(unittest.TestCase):
    CASES = [
        # (Taqrib wording, tabaqa, expected (min, max, precision) per alternative)
        ("ثقة من الحادية عشرة مات سنة أربع وستين س", 11, [(264, 264, "exact")]),
        ("صدوق من الثامنة مات سنة خمس وثمانين", 8, [(185, 185, "exact")]),
        ("صحابي مات سنة أربع وخمسين", 1, [(54, 54, "exact")]),
        ("ثقة من التاسعة مات سنة بضع عشرة خ", 9, [(213, 219, "range")]),
        ("ثقة من الثالثة مات على رأس المائة خ", 3, [(100, 100, "circa")]),
        ("من الثامنة مات قبل المائتين د س ق", 8, [(None, 200, "upper_bound")]),
        ("من السادسة مات بعد الأربعين", 6, [(140, None, "lower_bound")]),
        ("مات سنة اثنتين وقيل ثلاث وتسعين", 1, [(92, 92, "exact"), (93, 93, "exact")]),
        ("من السابعة مات سنة إحدى أو اثنتين وعشرين ومائة", 7, [(121, 121, "exact"), (122, 122, "exact")]),
        ("من العاشرة مات سنة إحدى ومائتين", 10, [(201, 201, "exact")]),
        ("مات سنة عشر ومائة", 4, [(110, 110, "exact")]),
        ("مات في خلافة عمر", 1, [(None, None, "event_reference")]),
        # rule boundary: Ibn Numayr, 'من كبار التاسعة', died 199 (the literal 'after 200' reading gives 299)
        ("ثقة من كبار التاسعة مات سنة تسع وتسعين", 9, [(199, 199, "exact")]),
        ("ثقة من الثالثة مات سنة سبع وتسعين", 3, [(97, 97, "exact")]),
        ("مات سنة تسع وستين ومئتين، وقيل سنة سبعين", None, [(269, 269, "exact"), (270, 270, "exact")]),
        # Mahmud b. Labid: 'died 96, and it is said 97' (tens elided in the second alternative)
        ("صحابي صغير مات سنة ست وتسعين وقيل سنة سبع", 1, [(96, 96, "exact"), (97, 97, "exact")]),
        # an age is not a year and must not lend its 'hundred' to the date (Abu Uthman al-Nahdi, d. 95)
        ("مخضرم من كبار الثانية مات سنة خمس وتسعين وقيل بعدها وعاش مائة وثلاثين سنة", 2,
         [(95, 95, "exact"), (95, None, "lower_bound")]),
    ]

    def test_boundary_reading_is_flagged(self):
        rows = rp.parse_death_statements(rp.fold_for_phrases("من كبار التاسعة مات سنة تسع وتسعين"), 9, True)
        self.assertIn("century_by_tabaqa_era_not_literal_rule", rows[0]["flags"])

    def test_cases(self):
        for text, tabaqa, expected in self.CASES:
            with self.subTest(text=text):
                self.assertEqual(deaths(text, tabaqa), expected)

    def test_century_left_open_without_convention(self):
        rows = rp.parse_death_statements(rp.fold_for_phrases("مات سنة أربع وستين"), None, False)
        self.assertEqual(rows[0]["precision"], "century_not_stated")
        self.assertEqual(rows[0]["within_century"], [64, 64])

    def test_flags_record_inference(self):
        rows = rp.parse_death_statements(rp.fold_for_phrases("من السابعة مات سنة إحدى أو اثنتين وعشرين"), 7, True)
        self.assertIn("elided_part_inherited", rows[0]["flags"])
        self.assertIn("century_by_author_convention", rows[0]["flags"])
        self.assertIn("or_alternative", rows[1]["flags"])

    def test_relative_death_flagged(self):
        rows = rp.parse_death_statements(rp.fold_for_phrases("قال ابن سعد مات ابوه سنة ثلاث ومئة"), None, False)
        self.assertIn("subject_may_differ", rows[0]["flags"])


class TabaqaAndHeadwordTest(unittest.TestCase):
    def test_tabaqa(self):
        for text, expected in [("ثقة من الحادية عشرة", 11), ("صدوق من كبار العاشرة", 10), ("صحابي له حديث", 1),
                               ("مقبول", None)]:
            with self.subTest(text=text):
                self.assertEqual(rp.find_tabaqa(rp.fold_for_phrases(text))["tabaqa"], expected)

    def test_headword_skips_vocalization_gloss(self):
        text = rp.fold_for_phrases("أبان بن تغلب بفتح المثناة وسكون المعجمة وكسر اللام أبو سعد الكوفي ثقة تكلم فيه")
        self.assertEqual(" ".join(rp.headword_tokens(text)), "ابان بن تغلب ابو سعد الكوفي")
        self.assertEqual(" ".join(rp.headword_tokens(text, skip_glosses=False)), "ابان بن تغلب")

    def test_name_chain(self):
        self.assertEqual(rp.name_chain("عبد الله بن عمر بن الخطاب العدوي ابو عبد الرحمن".split()),
                         ("عبد الله بن عمر بن الخطاب", ["العدوي", "ابو", "عبد", "الرحمن"]))
        # a name truncated at 'بن عبيد' must not equal the chain ending 'بن عبيد الله'
        self.assertEqual(rp.name_chain("معاوية بن اسحاق بن طلحة بن عبيد الله التيمي".split())[0],
                         "معاوية بن اسحاق بن طلحة بن عبيد الله")

    def test_places(self):
        self.assertEqual(rp.english_places("Medina/al-Ta'if")[0], {"medina", "taif"})
        self.assertEqual(rp.compare_place_sets({"hijaz"}, {"medina"}), "consistent_by_region")
        self.assertEqual(rp.compare_place_sets({"kufa"}, {"basra"}), "differ")
        self.assertEqual(rp.arabic_places(["الكوفي", "نزيل", "بغداد"]), {"kufa", "baghdad"})
        # a city named in narrative ('his father was martyred at al-Yamama') is not the narrator's nisba
        self.assertEqual(rp.nisba_places(["العدوي", "باليمامة", "الكوفي"]), {"kufa"})
        self.assertEqual([p["verbatim"] for p in rp.residence_phrases("المدني نزيل الكوفة ثقة جليل")], ["نزيل الكوفة"])


if __name__ == "__main__":
    unittest.main()
