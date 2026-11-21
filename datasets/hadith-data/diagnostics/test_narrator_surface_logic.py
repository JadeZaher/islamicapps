"""Table-driven tests for narrator_surface_logic (pure branching logic; inputs taken from the real corpus/registry).

Run: python -B -m unittest datasets/hadith-data/diagnostics/test_narrator_surface_logic.py
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from narrator_surface_logic import (  # noqa: E402
    categorize_surface, fold_kunya_head, parse_components, parse_father_indx, parse_generation,
    parse_indx_list, registry_alias_segments, score_candidate, strip_trailing_honorific,
)


class CategorizeSurface(unittest.TestCase):
    def test_real_top_surfaces(self):
        table = [
            ("ابيه", "relational_or_fragment"),          # 14,101 occurrences: never a registry identity
            ("و", "relational_or_fragment"),             # extractor artefact
            ("عنه", "relational_or_fragment"),
            ("عدة من اصحابنا", "collective_or_anonymous"),
            ("ابي عبد الله", "kunya_only"),              # context-dependent Imam / other narrators
            ("ابي هريرة", "kunya_only"),
            ("ابن شهاب", "ibn_nasab_only"),
            ("سفيان", "single_ism_or_laqab"),
            ("علي بن ابراهيم", "ism_nasab"),
            ("ابو بكر بن ابي شيبة", "ism_nasab"),        # kunya head but carries a nasab: not kunya_only
            ("الحميدي عبد الله بن الزبير", "ism_nasab"),
        ]
        for surface, expected in table:
            with self.subTest(surface=surface):
                self.assertEqual(categorize_surface(surface), expected)


class ParseComponents(unittest.TestCase):
    def test_component_split(self):
        table = [
            # reordered Sunni surface: nisba first, compound ism 'عبد الله' stays one unit
            ("الحميدي عبد الله بن الزبير", dict(ism="عبد الله", kunya=None, nasab=["الزبير"], nisbas=["الحميدي"])),
            ("ابو بكر بن ابي شيبة", dict(ism=None, kunya="ابو بكر", nasab=["ابو شيبه"], nisbas=[])),
            ("ابن ابي عمير", dict(ism=None, kunya=None, nasab=["ابو عمير"], nisbas=[])),
            ("سلمان ابو عبد الله الفارسي", dict(ism="سلمان", kunya="ابو عبد الله", nasab=[], nisbas=["الفارسي"])),
        ]
        for surface, expected in table:
            with self.subTest(surface=surface):
                parsed = parse_components(surface)
                self.assertEqual(
                    dict(ism=parsed.ism, kunya=parsed.kunya, nasab=parsed.nasab, nisbas=parsed.nisbas), expected)


class ScoreCandidate(unittest.TestCase):
    def score(self, surface, registry_name, alias=None):
        return score_candidate(parse_components(surface), parse_components(registry_name), alias)

    def test_ranking_table(self):
        table = [
            # (surface, registry Arabic name, expected score, must-have evidence, must-have conflict)
            ("ابي هريرة", "ابو هريرة", 1.0, "exact_normalized_equal", None),       # kunya case fold equal
            ("محمد بن يحيي", "محمد بن يحيي الذهلي", 0.7, "father=يحيي", None),
            ("محمد بن يحيي", "محمد بن خالد", 0.05, None, "father_conflict:يحيي!=خالد"),
            ("سفيان", "سفيان بن نسر بن عمرو", 0.45, "registry_name_starts_with_surface", None),
            ("سفيان", "احمد بن سفيان", 0.1, "surface_contiguous_in_registry_name", None),  # containment only: no ism credit
        ]
        for surface, registry_name, expected, evidence, conflict in table:
            with self.subTest(surface=surface, registry=registry_name):
                score, found_evidence, found_conflicts = self.score(surface, registry_name)
                self.assertAlmostEqual(score, expected, places=2)
                if evidence:
                    self.assertTrue(any(evidence in item for item in found_evidence), found_evidence)
                if conflict:
                    self.assertIn(conflict, found_conflicts)

    def test_declared_alias_outranks_partial_name(self):
        alias_score, alias_evidence, _ = self.score("ابو هريرة", "عبد الرحمن بن صخر الدوسي", [])
        self.assertEqual(alias_score, 0.0)
        declared, evidence, _ = score_candidate(
            parse_components("ابو هريرة"), parse_components("عبد الرحمن بن صخر الدوسي"),
            parse_components("ابو هريرة").units)
        self.assertEqual((declared, evidence), (0.9, ["registry_declared_alias_segment_equal"]))


class RegistryNameHelpers(unittest.TestCase):
    def test_alias_segments_from_real_registry_names(self):
        table = [
            ("Abu Hurairah ( أبو هريرة - عبد الرحمن بن صخر الدوسي  ( رضي الله عنه",
             ["أبو هريرة", "عبد الرحمن بن صخر الدوسي رضي الله عنه"]),
            ("Sulaiman al-A'mash الأعمش / سليمان بن مهران", ["الأعمش", "سليمان بن مهران"]),
            ("Salman Farsi ( سلمان أبو عبد الله الفارسي ( رضي الله عنه", []),  # no separator: single segment
        ]
        for name, expected in table:
            with self.subTest(name=name):
                self.assertEqual(registry_alias_segments(name), expected)

    def test_fold_and_honorific_rules(self):
        self.assertEqual(fold_kunya_head("ابي هريرة"), "ابو هريرة")
        self.assertEqual(fold_kunya_head("ابي"), "ابي")                 # bare 'my father' is excluded
        self.assertEqual(fold_kunya_head("عمرو بن ابي"), "عمرو بن ابي")  # head fold only
        self.assertEqual(strip_trailing_honorific("ابو بكر رضي الله عنه"), "ابو بكر")
        self.assertEqual(strip_trailing_honorific("عمرو"), "عمرو")      # never deletes letters inside names
        self.assertEqual(strip_trailing_honorific("ع"), "ع")            # never empties a surface

    def test_registry_cell_parsers(self):
        self.assertEqual(parse_indx_list("1, 2, 3, 135"), {"1", "2", "3", "135"})
        self.assertEqual(parse_indx_list("NA"), set())
        self.assertEqual(parse_generation("Follower(Tabi') [6th generation]"), 6)
        self.assertEqual(parse_generation("Comp.(RA)"), 1)
        self.assertIsNone(parse_generation("3rd Century AH"))
        self.assertEqual(parse_father_indx("Abu Quhafa Uthman bin 'Amir [500] / Salma Umm-ul-Khair [501]"), "500")
        self.assertIsNone(parse_father_indx("/ Umaima/Maymuna"))


if __name__ == "__main__":
    unittest.main()
