"""Table-driven tests for narrator_surface_logic (pure branching logic; inputs taken from the real corpus/registry).

Run: python -B -m unittest datasets/hadith-data/diagnostics/test_narrator_surface_logic.py
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from narrator_surface_logic import (  # noqa: E402
    categorize_surface, parse_components, parse_father_indx, parse_generation,
    parse_indx_list, score_candidate,
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
    def score(self, surface, registry_name):
        return score_candidate(parse_components(surface), parse_components(registry_name))

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


class RegistryCellParsers(unittest.TestCase):
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
