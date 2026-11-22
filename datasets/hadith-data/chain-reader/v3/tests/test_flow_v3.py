"""Flows of the batch tooling on real artifacts: triage and the submission converter over the second pilot's packets and outputs, and the fresh-sample draw over the live population file.

    python -B -X utf8 -m unittest discover -s v3/tests -p "test_flow_v3.py"        (from chain-reader/)

The draw test needs v3/batch-001/private/population.jsonl (written by draw_population.cjs); it is skipped when the file is absent.
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
V3 = HERE.parent
ROOT = V3.parent
for path in (str(ROOT), str(V3)):
    sys.path.insert(0, path)

import draw_batch  # noqa: E402
import to_submission  # noqa: E402
import triage_v3  # noqa: E402
import validate as v1  # noqa: E402

PACKETS = ROOT / "context" / "pilot-v2" / "packets"
RUN_A, RUN_B = ROOT / "context" / "outputs-v2" / "run-a", ROOT / "context" / "outputs-v2" / "run-b"
REPORTS = ROOT / "pilot" / "reports.jsonl"
POPULATION = V3 / "batch-001" / "private" / "population.jsonl"


class SubmissionFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)
        to_submission.main(["--packets", str(PACKETS), "--reports", str(REPORTS), "--pass-a", str(RUN_A), "--pass-b", str(RUN_B), "--out", str(cls.out)])
        cls.packets = triage_v3.load_packets(PACKETS)
        cls.envelopes = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(cls.out.glob("*.envelope.json"))]
        cls.skipped = dict(line.split("\t", 1) for line in (cls.out / "not_submitted.tsv").read_text(encoding="utf-8").splitlines()[1:])

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_every_submitted_reading_passes_the_submit_tools_own_validator(self):
        # the pipeline validates v1-shaped outputs (routes with offsets): the converter's output must pass v1's validate() against the packet text
        submitted = 0
        for envelope in self.envelopes:
            for fix in envelope["fixes"]:
                output = fix["output"]
                self.assertEqual(v1.validate(output, self.packets[output["id"]]["text"], output["id"]), [])
                self.assertIn(fix["evidence"][0]["quote"], self.packets[output["id"]]["text"])
                submitted += 1
        self.assertGreater(submitted, 100)

    def test_provenance_names_prompt_model_run_packet_and_both_readers(self):
        prompt = json.loads((V3 / "prompt-v3.json").read_text(encoding="utf-8"))
        for envelope in self.envelopes:
            run = envelope["run"]
            self.assertEqual(run["prompt_sha256"], prompt["sha256"])
            self.assertEqual(run["prompt_version"], "3.0.0")
            self.assertEqual(run["model_id"], "claude-haiku-5-5")
            self.assertRegex(run["started_at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
            self.assertTrue(run["packet_id"].startswith("packet-"))
            self.assertIn(run["packet_id"], envelope["packet"])
            self.assertTrue(run["second_reader"]["run_id"])

    def test_held_and_disagreeing_reports_are_not_submitted_with_their_reason(self):
        self.assertEqual(self.skipped["cr-0193"], "held: back_reference_only")          # previous report supplied, chain not taken
        self.assertEqual(self.skipped["cr-0133"], "held: routes_end_at_different_links")  # shared tail dropped from a route
        self.assertEqual(self.skipped["cr-0010"], "readings differ")
        submitted = {fix["output"]["id"] for envelope in self.envelopes for fix in envelope["fixes"]}
        self.assertFalse(submitted & set(self.skipped))
        self.assertNotIn("cr-0133", submitted)

    def test_a_reading_with_inherited_links_is_converted_without_them(self):
        reading = {"id": "x", "routes": [{"links": [{"surface": "أ", "start": None, "end": None, "kind": "inherited", "from": "prev1"}, {"surface": "ب", "start": 0, "end": 1, "kind": "narrator"}], "shared_tail_from": None}],
                   "matn_start": 1, "notes": []}
        shaped, reason = to_submission.v1_shape(reading)
        self.assertIsNone(reason)
        self.assertEqual([link["surface"] for link in shaped["routes"][0]["links"]], ["ب"])


@unittest.skipUnless(POPULATION.is_file(), "population.jsonl not built")
class FreshDraw(unittest.TestCase):
    def test_draw_excludes_every_earlier_sample_and_hits_the_strata(self):
        with tempfile.TemporaryDirectory() as tmp:
            with contextlib.redirect_stdout(io.StringIO()):
                draw_batch.main(["--population", str(POPULATION), "--out-dir", tmp, "--seed", "7"])
            sample = json.loads((Path(tmp) / "private" / "sample.json").read_text(encoding="utf-8"))
            draw = json.loads((Path(tmp) / "draw.json").read_text(encoding="utf-8"))
            excluded, _ = draw_batch.excluded_ids()
            ids = [row["hadith_id"] for row in sample]
            self.assertEqual(len(ids), 500)
            self.assertEqual(len(set(ids)), 500)
            self.assertFalse(set(ids) & excluded)
            self.assertEqual({k: v["drawn"] for k, v in draw["strata"].items()}, {"sunni_six_books": 250, "imami_faqih": 150, "imami_other_not_kafi": 100})
            self.assertEqual(sum(draw["sunni_quota_by_book"].values()), 250)
            self.assertNotIn("imami:al-kafi", draw["drawn_by_work"])
            self.assertTrue(all(row["id"].startswith("b1-") and "hadith" not in row["id"] for row in sample))
            again = Path(tmp) / "again"
            with contextlib.redirect_stdout(io.StringIO()):
                draw_batch.main(["--population", str(POPULATION), "--out-dir", str(again), "--seed", "7"])
            second = [row["hadith_id"] for row in json.loads((again / "private" / "sample.json").read_text(encoding="utf-8"))]
            self.assertEqual(sorted(second), sorted(ids), "same seed, same reports")

    def test_apportion_is_proportional_and_sums_to_the_total(self):
        seats = draw_batch.apportion(250, {"a": 1000, "b": 500, "c": 250, "d": 1})
        self.assertEqual(sum(seats.values()), 250)
        self.assertGreater(seats["a"], seats["b"])


if __name__ == "__main__":
    unittest.main()
