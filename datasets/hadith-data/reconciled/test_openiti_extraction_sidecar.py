"""Flow tests for the OpenITI extraction sidecar, on the real parsed works.

Run: cd datasets/hadith-data/reconciled && python -B -m unittest test_openiti_extraction_sidecar
The unified CSV is replaced by the parsed texts themselves (the builder requires them to be byte-equal), so the test
needs no build output.
"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_openiti_extraction_sidecar as builder  # noqa: E402


def parsed_texts() -> dict[str, str]:
    texts = {}
    for path in builder.PARSED.values():
        for hadith in json.loads(path.read_text(encoding="utf-8"))["hadiths"]:
            texts[builder.record_id_of(hadith)[0]] = hadith["text_ar"]
    return texts


class OpenitiExtractionSidecar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.texts = parsed_texts()
        cls.rows, cls.counts = builder.build_rows(cls.texts)
        cls.by_record = {row["record_id"]: row for row in cls.rows}

    def test_one_row_per_report_bound_to_its_exact_text(self):
        self.assertEqual(len(self.rows), len(self.texts))
        for row in self.rows:
            self.assertEqual(row["text_ar_sha256"], builder.io_.sha256_text(self.texts[row["record_id"]]))

    def test_confident_split_keeps_the_span_and_a_low_one_keeps_none(self):
        niyyat = self.by_record["openiti:ibadi:rabi_0001|1|"]
        self.assertEqual(niyyat["split_confidence"], "high")
        self.assertTrue(self.texts[niyyat["record_id"]].startswith(niyyat["sanad_ar"]))
        low = self.by_record["openiti:zaydi:zayd_0010|10|V01P067"]
        self.assertEqual((low["split_confidence"], low["sanad_ar"]), ("low", None))

    def test_a_continuation_points_at_the_closest_earlier_report_with_that_id(self):
        self.assertEqual(
            self.by_record["openiti:ibadi:rabi_0001b|1|"]["sanad_inherits_from_record_id"],
            "openiti:ibadi:rabi_0001|1|",
        )
        # rabi_0387 is printed twice; the id alone is ambiguous, the record id is not.
        self.assertEqual(len([r for r in self.by_record if r.startswith("openiti:ibadi:rabi_0387|")]), 2)

    def test_notes_are_labelled_by_author_and_kept_out_of_the_text(self):
        row = self.by_record["openiti:ibadi:rabi_0225|225|V01P060"]
        self.assertEqual(sorted(note["kind"] for note in row["source_notes"]), ["compiler_comment", "editor_footnote"])
        text = " ".join(self.texts[row["record_id"]].split())
        for note in row["source_notes"]:
            self.assertNotIn(" ".join(note["text_ar"].split()), text)
        self.assertEqual(self.counts["ibadi:notes"], 149)

    def test_text_that_differs_from_the_unified_csv_is_refused(self):
        stale = dict(self.texts)
        stale["openiti:ibadi:rabi_0001|1|"] += " x"
        with self.assertRaises(ValueError):
            builder.build_rows(stale)


if __name__ == "__main__":
    unittest.main()
