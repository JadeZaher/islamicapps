"""The shipped pilot set keeps its promises: blind packets, one row per report, labelled, no prompt example inside."""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from score import fold_loose  # noqa: E402

PILOT = ROOT / "pilot"


def lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class PilotSetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reports = lines(PILOT / "reports.jsonl")
        cls.packets = {path.name: lines(path) for path in sorted((PILOT / "packets").glob("packet-*.jsonl"))}

    def test_packets_are_blind_complete_and_25_each(self):
        packed = [row for rows in self.packets.values() for row in rows]
        self.assertTrue(all(set(row) == {"id", "text"} for row in packed), "a packet row may carry only id and text")
        self.assertEqual(sorted(row["id"] for row in packed), sorted(r["id"] for r in self.reports))
        self.assertEqual({row["id"]: row["text"] for row in packed}, {r["id"]: r["text"] for r in self.reports})
        sizes = [len(rows) for rows in self.packets.values()]
        self.assertTrue(all(size == 25 for size in sizes[:-1]) and 1 <= sizes[-1] <= 25, sizes)
        self.assertTrue(all(re.fullmatch(r"cr-\d{4}", r["id"]) for r in self.reports), "ids are opaque: no work or verdict in them")

    def test_every_report_is_labelled_and_verdicts_are_consistent(self):
        for report in self.reports:
            labels = [c for c in report["stored_chains"] if c["verdict"] != "unlabelled"] + report["report_labels"]
            self.assertTrue(labels, report["id"])
            has_defect = any(label["verdict"] == "defective" and label["label_state"] != "stale_fixed" for label in labels)
            self.assertEqual(report["report_verdict"] == "defective", has_defect, report["id"])

    def test_no_prompt_example_is_in_the_pilot(self):
        examples = {e["hadith_id"] for e in json.loads((ROOT / "examples" / "examples.json").read_text(encoding="utf-8"))}
        self.assertFalse(examples & {r["hadith_id"] for r in self.reports})

    def test_lost_names_are_in_the_text_and_not_in_the_stored_chain(self):
        for report in self.reports:
            text = fold_loose(report["text"])
            stored = {fold_loose(s) for c in report["stored_chains"] for s in c["surfaces"]}
            for name in report["expected_names"]:
                self.assertIn(fold_loose(name), text)
                self.assertNotIn(fold_loose(name), stored)

    def test_chain_field_works_carry_their_chain_in_the_text(self):
        for report in self.reports:
            if report["work"] in ("ahmad", "darimi", "muwatta"):
                self.assertEqual(report["text_layout"], "chain_field_then_matn")
                self.assertIn("\n\n", report["text"])


if __name__ == "__main__":
    unittest.main()
