"""Table-driven tests for the projection rules in export_postgres.py (pure logic with real branching)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import export_postgres as ep  # noqa: E402


class GradeRules(unittest.TestCase):
    def test_map_to_canonical_matches_grade_taxonomy(self):
        cases = [
            ("صحيح", "sahih"),
            ("  صحيح   ", "sahih"),
            ("حسن كالصحيح", "sahih"),          # exact compound
            ("ضعيف على المشهور معتبر عند ي", "mu_tabar"),
            ("ضعيف على المشهور وهو معتبر", "mu_tabar"),  # contains: معتبر wins over ضعيف
            ("مجهول", "majhul"),
            ("موثق", "muwaththaq"),
            ("لم يخرجه", "ungraded"),
            ("ثابت", "ungraded"),              # Pure Canon inclusion label is not a grade
            ("Sahih", "sahih"),
            ("مختلف فيه", "mukhtalaf"),
            ("موضوع", "mawdu"),
            ("حسن ی", "hasan"),                # Persian ya folded before matching
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(ep.map_to_canonical(raw), expected)

    def test_clean_grade_detail_fixes_ocr_splits(self):
        self.assertEqual(ep.clean_grade_detail("صحيح على الظاه ر"), "صحيح على الظاهر")
        self.assertEqual(ep.clean_grade_detail(""), "")

    def test_parse_gradings_full(self):
        value = ("Allamah Baqir al-Majlisi:  صحيح     (Mirʾāt al-ʿUqūl fī Sharḥ Akhbār Āl al-Rasūl (1/25)) | "
                 "Shaykh Baqir al-Behbudi: لم يخرجه (Sahih al-Kafi) | malformed segment")
        entries, skipped = ep.parse_gradings_full(value)
        self.assertEqual(skipped, 1)
        self.assertEqual([entry["scholar"] for entry in entries], ["Allamah Baqir al-Majlisi", "Shaykh Baqir al-Behbudi"])
        self.assertEqual(entries[0]["grade"], "صحيح")
        self.assertEqual(entries[0]["citation"], "Mirʾāt al-ʿUqūl fī Sharḥ Akhbār Āl al-Rasūl (1/25)")
        self.assertEqual(entries[1]["citation"], "Sahih al-Kafi")

    def test_split_citation(self):
        cases = [
            ("Mirʾāt al-ʿUqūl (1/25)", ("Mirʾāt al-ʿUqūl", "1", "25")),
            ("Sahih al-Kafi (1/ 1)", ("Sahih al-Kafi", "1", "1")),
            ("Sahih al-Kafi", ("Sahih al-Kafi", None, None)),
            ("", (None, None, None)),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(ep.split_citation(raw), expected)


class LexiconRules(unittest.TestCase):
    def test_parse_hijri_year_ports_io_ts(self):
        cases = [
            (("11", "11 AH/632 CE"), 11),
            (("53", "53 BH/570 CE (9th Rabi' awwal)"), -53),
            (("53", "53 BHمكة"), -53),          # ASCII boundary next to Arabic, as JS \b sees it
            (("53", "53 BHX"), 53),             # BH inside a Latin word is not Before Hijra
            (("c. 120", None), None),           # ranges and qualified tokens stay raw only
            (("١٢٠", None), None),              # Arabic-Indic digits are not an exact ASCII token
            (("", None), None),
        ]
        for (raw, context), expected in cases:
            with self.subTest(raw=raw, context=context):
                self.assertEqual(ep.parse_hijri_year(raw, context), expected)

    def test_english_name(self):
        cases = [
            ("Abu Bakr As-Siddique ( أبو بكر الصديق ( رضي الله عنه", "Abu Bakr As-Siddique"),
            ("Prophet Muhammad(saw) ( محمّد صلّی الله", "Prophet Muhammad(saw)"),
            ("Plain English Only", "Plain English Only"),
            ("محمد بن مسلم", None),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(ep.english_name(raw), expected)


class IsnadRules(unittest.TestCase):
    def test_shapes_match(self):
        cases = [
            ([[1, 2, 3]], [3], True),
            ([[1, 2], [3]], [2, 1], True),
            ([[1, 2], [3]], [1, 2], False),     # same total, different branch lengths
            ([[1, 2, 3]], [3, 1], False),       # branch count differs
            ([], [], False),
        ]
        for branches, lengths, expected in cases:
            with self.subTest(branches=branches, lengths=lengths):
                self.assertEqual(ep.shapes_match(branches, lengths), expected)

    def test_provider_ids_agree(self):
        cases = [
            ("522", "pc_9", "522", True),       # re-keyed work: legacy id is the hadith number
            ("522", "522", "1", True),
            ("523", "pc_9", "522", False),
            ("", "pc_9", "522", True),          # nothing to compare
            ("522", None, "522", True),
        ]
        for legacy, provider, number, expected in cases:
            with self.subTest(legacy=legacy, provider=provider):
                self.assertEqual(ep.provider_ids_agree(legacy, provider, number), expected)

    def test_review_unit_ids(self):
        coarse_a, fine_a = ep.review_unit_ids("سفيان", "الزهري", "الحميدي", "sunni:bukhari")
        coarse_b, fine_b = ep.review_unit_ids("سفيان", "الزهري", "علي", "sunni:bukhari")
        coarse_c, _ = ep.review_unit_ids("سفيان", "منصور", "الحميدي", "sunni:bukhari")
        self.assertEqual(coarse_a, coarse_b)    # coarse ignores the student
        self.assertNotEqual(fine_a, fine_b)     # fine does not
        self.assertNotEqual(coarse_a, coarse_c)  # teacher context separates units
        self.assertEqual(len(coarse_a), 64)

    def test_parse_chain_indx(self):
        self.assertEqual(ep.parse_chain_indx("[1, 2, 3]"), [[1, 2, 3]])
        self.assertEqual(ep.parse_chain_indx("1,2|3"), [[1, 2], [3]])
        self.assertEqual(ep.parse_chain_indx(""), [])
        with self.assertRaises(ValueError):
            ep.parse_chain_indx("1,,2")


class CsvCells(unittest.TestCase):
    def test_cells(self):
        cases = [(None, None), ("", None), (ep.Verbatim(""), ""), (True, "true"), (False, "false"), (3, "3"),
                 (1.0, "1.0"), ("نص", "نص")]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(ep.cell(value), expected)

    def test_blank_to_none_keeps_text_as_written(self):
        self.assertIsNone(ep.blank_to_none("   "))
        self.assertEqual(ep.blank_to_none(" 1 "), " 1 ")


class Refusals(unittest.TestCase):
    def test_bundle_without_import_ready_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "manifest.json").write_text(json.dumps({"content_sha256": "x", "files": []}), encoding="utf-8")
            (root / "validation_report.json").write_text(
                json.dumps({"import_ready": False, "content_sha256": "x"}), encoding="utf-8")
            with self.assertRaisesRegex(ep.ProjectionError, "import_ready"):
                ep.Bundle(root)

    def test_header_must_equal_live_catalog(self):
        catalog = {"sources": [{"name": "id", "role": "csv"}, {"name": "slug", "role": "csv"},
                               {"name": "updated_at", "role": "bookkeeping"}]}
        ep.check_header(catalog, "sources", ["slug", "id"])
        with self.assertRaisesRegex(ep.ProjectionError, "missing=\\['slug'\\]"):
            ep.check_header(catalog, "sources", ["id"])
        with self.assertRaisesRegex(ep.ProjectionError, "extra=\\['updated_at'\\]"):
            ep.check_header(catalog, "sources", ["id", "slug", "updated_at"])


if __name__ == "__main__":
    unittest.main()
