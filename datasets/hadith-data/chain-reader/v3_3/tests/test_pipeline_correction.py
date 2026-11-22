"""The pipeline's correction of v3.3 (holds_v3_3_pipeline): the half-route hold is v3.2's again. Real readings: 6d7565 (tranche 01, judged wrong), 2c5437 and cb35a4 (batch 001,
read as the 6d7565 class) are held; 1552aa (tranche 02, judged right) is held again, the known cost. Every other v3.3 hold is unchanged.

    python -B -X utf8 -m unittest discover -s v3_3/tests -p "test_*.py"        (from chain-reader/)
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
V33 = HERE.parent
ROOT = V33.parent
for path in (str(ROOT), str(ROOT / "v3_2"), str(V33)):
    if path not in sys.path:
        sys.path.insert(0, path)

import holds_v3_3  # noqa: E402
import holds_v3_3_pipeline  # noqa: E402
import triage_v3_3 as triage_module  # noqa: E402

CASES = {  # reading id: (tranche folder, under v3.3 narrowed: held by the half-route hold?)
    "t01-6d7565": (ROOT / "tranches" / "tranche-01", False),
    "b1-2c5437": (ROOT / "v3" / "batch-001", False),
    "b1-cb35a4": (ROOT / "v3" / "batch-001", False),
    "t02-1552aa": (ROOT / "tranches" / "tranche-02", False),
}
CODE = "route_at_most_half_the_longest"


def reading_of(report_id: str, folder: Path) -> tuple[dict, dict, dict, dict]:
    """(expanded agreed reading, output a, output b, packet line) through the v3.3 triage's own expansion."""
    packets = triage_module.load_packets(folder / "packets")
    row = triage_module.triage({report_id: packets[report_id]}, folder / "outputs" / "pass-a", folder / "outputs" / "pass-b", None)[0]
    return row["reading"]["expanded_a"], row["reading"]["output_a"], row["reading"]["output_b"], packets[report_id]


@unittest.skipUnless(all((folder / "outputs" / "pass-a").is_dir() for folder, _ in CASES.values()), "tranche outputs are not in this checkout")
class HalfRouteCorrection(unittest.TestCase):
    def test_the_four_short_route_readings_are_held_again(self):
        for report_id, (folder, narrowed_holds) in CASES.items():
            with self.subTest(report_id=report_id):
                reading, output_a, output_b, packet = reading_of(report_id, folder)
                narrowed = [hold["code"] for hold in holds_v3_3.compute_holds(reading, output_a, packet["text"], packet.get("context"), None, output_b)]
                corrected = [hold["code"] for hold in holds_v3_3_pipeline.compute_holds(reading, output_a, packet["text"], packet.get("context"), None, output_b)]
                self.assertEqual(CODE in narrowed, narrowed_holds)
                self.assertIn(CODE, corrected)
                self.assertEqual(sorted(c for c in corrected if c != CODE), sorted(c for c in narrowed if c != CODE))

    def test_a_reading_without_a_short_route_is_unchanged(self):
        folder = ROOT / "tranches" / "tranche-02"
        reading, output_a, output_b, packet = reading_of("t02-89130e", folder)          # judged right, eligible under v3.3
        args = (reading, output_a, packet["text"], packet.get("context"), None, output_b)
        self.assertEqual(holds_v3_3_pipeline.compute_holds(*args), holds_v3_3.compute_holds(*args))


if __name__ == "__main__":
    unittest.main()
