"""Table-driven tests for structure_logic on real rows, plus checks of the built sidecar.

    cd datasets/hadith-data/reconciled/structure && python -B -m unittest test_structure_logic

The sidecar tests skip when the outputs have not been built. Rows quoted below were read from the source files named in
each case (provider JSON, pure_canon.jsonl, K6 labels), not invented.
"""

import gzip
import json
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import structure_logic as logic  # noqa: E402
import structure_provenance as provenance  # noqa: E402

HADITH_DATA = HERE.parent.parent


def parsed(raw):
    return logic.parse_number(raw)


class ParseNumber(unittest.TestCase):
    # (raw cell, value, sub, series, letter, a flag that must be present)
    CASES = [
        (" 1 ", 1, None, None, None, None),                       # K6 Bukhari cell, padded
        ("1]", None, None, None, None, "section_opener_marker_not_a_number"),  # 463 Musnad Ahmad rows (shelf 3524, 3548, 3640 ...)
        ("1×2", 1, None, 2, None, "second_numbering_series"),     # Ahmad shelf 19972, 20119
        ("8.1999999999999993", 8, "2", None, None, "float_noise_cleaned"),  # Ahmad: spreadsheet float for 8.2
        ("2171.1", 2171, "1", None, None, "decimal_sub_number"),  # Ahmad shelf 10950
        ("3604b", 3604, None, None, "b", "letter_suffix"),        # Tirmidhi K6 cell
        ("Grade", None, None, None, None, "non_numeric_text"),    # 68 K6 rows hold the word Grade
        ("0", None, None, None, None, "zero_means_unnumbered"),   # 31 K6 rows; reference.ts treats 0 as unnumbered too
        ("", None, None, None, None, "empty"),                    # Musnad al-Shafi'i has no numbers
        ("٤٧٨", 478, None, None, None, None),                     # Nahj al-Balagha Arabic-Indic digits
    ]

    def test_cells(self):
        for raw, value, sub, series, letter, flag in self.CASES:
            with self.subTest(raw=raw):
                result = parsed(raw)
                self.assertEqual((result["value"], result["sub"], result["series"], result["letter"]),
                                 (value, sub, series, letter))
                if flag:
                    self.assertIn(flag, result["flags"])

    def test_display_round_trip(self):
        self.assertEqual(logic.display_number(parsed("8.1999999999999993")), "8.2")
        self.assertEqual(logic.display_number(parsed("3604b")), "3604b")
        self.assertEqual(logic.display_number(parsed("1×2")), "1×2")
        self.assertIsNone(logic.display_number(parsed("1]")))


class ProviderNumbers(unittest.TestCase):
    def test_url_segments(self):
        # Faqih volume 1 record 2 and an Al-Kafi record: the last segment is the hadith, not the chapter
        self.assertEqual(logic.parse_thaqalayn_url("https://thaqalayn.net/hadith/34/1/2/0"), (34, 1, 2, 0))
        self.assertEqual(logic.parse_thaqalayn_url("https://thaqalayn.net/hadith/1/4/10/3"), (1, 4, 10, 3))
        self.assertIsNone(logic.parse_thaqalayn_url(""))

    def test_leading_numbers_on_real_provider_rows(self):
        with open(HADITH_DATA / "shia-hadith" / "v2_books" / "1.json", encoding="utf-8") as handle:
            records = json.load(handle)
        record = next(r for r in records if str(r["id"]) == "2")  # Al-Kafi vol. 1, chapter 0, hadith 1
        self.assertEqual(logic.printed_lead_number(record["arabicText"], "ar"), 1)
        self.assertEqual(logic.printed_lead_number(record["englishText"], "en"), 1)
        self.assertEqual(record["URL"].rsplit("/", 1)[1], "1")
        self.assertIsNone(logic.printed_lead_number("بسم الله الرحمن الرحيم", "ar"))
        self.assertEqual(logic.printed_lead_number("٤٧٨ - قال", "ar"), 478)  # Nahj saying 478


class AhmadSections(unittest.TestCase):
    def sections(self, cells):
        return logic.ahmad_section_ordinals([parsed(c) for c in cells])

    def test_opener_starts_a_section(self):
        # shelf 3522-3526 of pure_canon.jsonl: 11, 12, then the opener `1]`, then 1, 2
        self.assertEqual(self.sections(["11", "12", "1]", "1", "2"]), [1, 1, 2, 2, 2])

    def test_restart_without_a_one(self):
        # shelf 2278-2288: a section whose first hadith is missing restarts at 2
        self.assertEqual(self.sections(["2", "3", "4", "5", "7", "8", "2", "3", "4"]), [1, 1, 1, 1, 1, 1, 2, 2, 2])

    def test_sub_numbers_and_second_series_do_not_split(self):
        # shelf 17389-17394: 8, 8.1, 8.2, 8.3, 11 ; shelf 19972-19973: 1x2, 2x2 inside a running section
        self.assertEqual(self.sections(["1", "8", "8.1", "8.2", "8.3", "11"]), [1] * 6)
        self.assertEqual(self.sections(["2", "1", "1×2", "2×2", "1", "2"]), [1, 2, 2, 2, 2, 2])


class SourceOrder(unittest.TestCase):
    def test_natural_key_places_a_variant_after_its_base(self):
        ids = ["rabi_0010", "rabi_0002", "rabi_0001b", "rabi_0001"]
        self.assertEqual(sorted(ids, key=logic.natural_key), ["rabi_0001", "rabi_0001b", "rabi_0002", "rabi_0010"])

    def test_ranks_are_dense_and_stable_on_ties(self):
        self.assertEqual(logic.assign_source_order([5, 3, 5, 1]), [3, 2, 4, 1])


class Labels(unittest.TestCase):
    def test_kitab_labels(self):
        self.assertEqual(logic.split_kitab_title("Revelation - كتاب بدء الوحى"), ("Revelation", "كتاب بدء الوحى"))
        self.assertEqual(logic.split_kitab_title("Hunting; Slaughtering - كتاب الذبائح والصيد"),
                         ("Hunting; Slaughtering", "كتاب الذبائح والصيد"))

    def test_page_refs(self):
        self.assertEqual(logic.parse_page_ref("V01P059"), (1, 59))
        self.assertIsNone(logic.parse_page_ref(""))


class SiteReferenceToday(unittest.TestCase):
    def test_kafi_row_cites_the_provider_path_but_stores_the_chapter(self):
        text = logic.site_reference_today("hadith:thaqalayn:fa95c5a87820c4100dc789b2", "1", "https://thaqalayn.net/hadith/1/0/1/1", "1", "", "1")
        self.assertEqual(text, "Volume 1, Book 0, Chapter 1, Hadith 1")

    def test_unnumbered_k6_row_falls_back_to_the_record_id(self):
        self.assertIn("unnumbered", logic.site_reference_today("hadith:k6:15245", "0", "", "", "", "1"))


class Uniqueness(unittest.TestCase):
    def test_counts(self):
        self.assertEqual(logic.unique_rows(["a", "b", "b", None]), (3, 1, 1))
        self.assertEqual(logic.rows_in_unique_groups(["a", "b", "b", None]), [True, False, False, False])


SIDECAR = HERE / "report_structure.jsonl.gz"


@unittest.skipUnless(SIDECAR.exists(), "sidecar not built")
class BuiltSidecar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with gzip.open(SIDECAR, "rt", encoding="utf-8") as handle:
            cls.rows = [json.loads(line) for line in handle]
        cls.by_id = {row["record_id"]: row for row in cls.rows}

    def test_every_report_once_and_source_order_is_a_permutation_per_work(self):
        self.assertEqual(len(self.rows), len(self.by_id))
        orders = {}
        for row in self.rows:
            orders.setdefault(row["work_id"], []).append(row["source_order"])
        for work, values in orders.items():
            self.assertEqual(sorted(values), list(range(1, len(values) + 1)), work)

    def test_kafi_references_are_unique_though_stored_numbers_are_not(self):
        kafi = [r for r in self.rows if r["work_id"] == "imami:al-kafi"]
        self.assertEqual(len({r["reference_key"] for r in kafi}), len(kafi))
        self.assertTrue(all(r["reference_unique"] for r in kafi))

    def test_ahmad_bracket_opener_rows_get_no_number_and_no_reference(self):
        row = self.by_id["pure-canon:pc_" + self._first_opener_id()]
        self.assertIsNone(row["report_number"])
        self.assertIsNone(row["reference_key"])
        self.assertIn("trailing_bracket", row["number_flags"])

    def _first_opener_id(self):
        for row in self.rows:
            if row["work_id"] == "sunni:ahmad" and "trailing_bracket" in row["number_flags"]:
                return row["record_id"].split("pc_", 1)[1]
        self.fail("no opener row")

    def test_ibadi_variant_and_source_bab(self):
        variant = self.by_id["openiti:ibadi:rabi_0001b|1|"] if "openiti:ibadi:rabi_0001b|1|" in self.by_id else None
        self.assertIsNotNone(variant)
        self.assertEqual(variant["report_number_display"], "1b")
        # report 588 sits under the source's heading `# [35] باب`; the loaded chapter said 34
        row = next(r for r in self.rows if r["work_id"] == "ibadi:musnad-rabi" and r["report_number"] == 588)
        self.assertEqual(row["chapter_number"], "35")
        self.assertEqual(row["loaded_chapter_number"], "34")

    def test_shafii_cannot_be_cited_by_number(self):
        shafii = [r for r in self.rows if r["work_id"] == "sunni:shafii"]
        self.assertTrue(shafii)
        self.assertTrue(all(r["reference_key"] is None for r in shafii))


PROVENANCE = HERE / "reference_provenance.jsonl.gz"
REGISTRY = HERE.parent.parent.parent.parent / "src" / "lib" / "sources" / "registry.ts"


class ProvenanceGate(unittest.TestCase):
    GOOD = {"record_id": "k6:1", "field": "number", "value": "1", "claim_by": "project_source_file", "kind": "source_value",
            "derivation": None, "source_code": "SUN", "source_name": "x", "licence": "Permission (owner, 2026-11-21)",
            "source_file": "datasets/archive/datasets.7z:all_hadiths_clean.csv", "source_sha256": "a" * 64,
            "source_record_id": "row 1", "source_field": "hadith_no", "edition": None}

    def check(self, **change):
        registry = provenance.load_registry(REGISTRY)
        return provenance.validate_record({**self.GOOD, **change}, registry, {"a" * 64})

    def test_registry_is_read_from_the_typescript_source(self):
        registry = provenance.load_registry(REGISTRY)
        for code in ("THQ", "OITI", "SUN", "NMC", "HKG", "RWY"):
            self.assertIn(code, registry)

    def test_a_complete_record_passes_and_each_defect_is_refused(self):
        self.assertEqual(self.check(), [])
        self.assertIn("unregistered_source_code", self.check(source_code="ZZZ"))
        self.assertIn("licence_differs_from_registry", self.check(licence="CC0"))
        self.assertIn("sha256_not_a_hash_of_an_input_file", self.check(source_sha256="b" * 64))
        self.assertIn("missing:source_record_id", self.check(source_record_id=None))
        self.assertIn("derived_without_derivation", self.check(kind="derived"))
        self.assertIn("edition_locator_without_edition_as_named", self.check(field="edition_page", value="6"))
        self.assertIn("external_claim_must_cite_the_external_dataset", self.check(claim_by="external_dataset", source_version="v"))


@unittest.skipUnless(PROVENANCE.exists(), "provenance not built")
class BuiltProvenance(unittest.TestCase):
    def test_every_record_is_complete_and_external_claims_are_labelled(self):
        registry = provenance.load_registry(REGISTRY)
        count = 0
        with gzip.open(PROVENANCE, "rt", encoding="utf-8") as handle:
            for line in handle:
                record = json.loads(line)
                count += 1
                self.assertIn(record["source_code"], registry)
                self.assertEqual(record["licence"], registry[record["source_code"]]["licence"])
                self.assertRegex(record["source_sha256"], "^[0-9a-f]{64}$")
                if record["claim_by"] == "external_dataset":
                    self.assertIn(record["source_code"], ("HKG", "RWY"))
                    self.assertTrue(record["source_version"])
        self.assertGreater(count, 500000)

    def test_zaydi_and_rida_emit_no_number_because_their_source_has_none(self):
        with gzip.open(SIDECAR, "rt", encoding="utf-8") as handle:
            rows = [json.loads(line) for line in handle]
        for row in rows:
            if row["work_id"] in ("zaydi:musnad-zayd", "imami:sahifat-al-imam-ali-al-rida"):
                self.assertIsNone(row["report_number"])
                self.assertIsNone(row["reference_key"])


if __name__ == "__main__":
    unittest.main()
