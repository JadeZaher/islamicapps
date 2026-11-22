"""v3.2 prompt draft, example packets, job conversion and the submission envelope (variant remarks as notes).

    python -B -X utf8 -m unittest discover -s v3_2/tests -p "test_*.py"        (from chain-reader/)
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
V32 = HERE.parent
ROOT = V32.parent
for path in (str(ROOT), str(V32), str(V32 / "tools")):
    sys.path.insert(0, path)

import make_jobs_v3_2  # noqa: E402
import make_prompt_v3_2  # noqa: E402
import to_submission_v3_2 as submission  # noqa: E402

TRANCHE = ROOT / "tranches" / "tranche-01"


class PromptDraft(unittest.TestCase):
    def test_the_recorded_hash_is_the_file_and_the_file_is_what_the_builder_makes(self):
        record = json.loads((V32 / "prompt-v3_2.json").read_text(encoding="utf-8"))
        data = (V32 / "prompt-v3_2.md").read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), record["sha256"])
        body = (V32 / "tools" / "chain_body_v3_2.md").read_text(encoding="utf-8")
        v1_body = (ROOT / "tools" / "prompt_body.md").read_text(encoding="utf-8")
        conventions = v1_body.split("## How each tradition writes its chains")[1].split("## Worked examples")[0].strip()
        rebuilt = body.replace("{{CONVENTIONS}}", conventions).replace("{{EXAMPLES}}", "\n".join(make_prompt_v3_2.chain_examples()).rstrip("\n"))   # every example is validated while it is built
        self.assertEqual(hashlib.sha256(rebuilt.replace("\r\n", "\n").encode("utf-8")).hexdigest(), record["sha256"])

    def test_length_budget_and_what_the_examples_teach(self):
        text = (V32 / "prompt-v3_2.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(text), len((ROOT / "v3_1" / "prompt-v3_1.md").read_text(encoding="utf-8")))
        self.assertIn("version: 3.2.0", text)
        for marker in ('"variant": true}', "بمثل حديث سليمان بن بلال", "قال وحدثني واصل", "أبو الطاهر، أحمد بن عمرو بن سرح", "فأخبرني ابن أبي مليكة"):
            self.assertIn(marker, text)
        self.assertEqual(text.count("### Example "), 8)

    def test_example_texts_are_prefixes_of_the_real_reports(self):
        if not TRANCHE.is_dir():
            self.skipTest("tranche 01 is not in this checkout")
        real = {}
        for path in sorted((TRANCHE / "packets").glob("packet-*.jsonl")):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    row = json.loads(line)
                    real[row["id"]] = row["text"]
        shown = [json.loads(line) for line in (V32 / "examples" / "example-packets.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        tranche_examples = [row for row in shown if row["id"].startswith("t01-")]
        self.assertEqual(len(tranche_examples), 4)
        for row in tranche_examples:
            self.assertTrue(real[row["id"]].startswith(row["text"]), row["id"])


class JobsConversion(unittest.TestCase):
    def test_only_the_prompt_changes(self):
        source = ROOT / "tranches" / "tranche-02" / "jobs.json"
        if not source.is_file():
            self.skipTest("tranche 02 is not in this checkout")
        jobs = json.loads(source.read_text(encoding="utf-8"))
        old, new = json.loads((ROOT / "v3_1" / "prompt-v3_1.json").read_text(encoding="utf-8")), json.loads((V32 / "prompt-v3_2.json").read_text(encoding="utf-8"))
        converted = make_jobs_v3_2.convert(jobs, old, new, old["chars"], new["chars"])
        self.assertEqual(converted["prompt"]["sha256"], new["sha256"])
        for before, after in zip(jobs["jobs"], converted["jobs"]):
            changed = {key for key in before if before[key] != after[key]}
            self.assertEqual(changed, {"instruction", "input_chars"})
            self.assertIn(new["sha256"], after["instruction"])
            self.assertNotIn(old["sha256"], after["instruction"])
            self.assertEqual(after["input_chars"] - before["input_chars"], new["chars"] - old["chars"])
        self.assertIn("v3_1", json.dumps(jobs))                                              # the source object is untouched

    def test_jobs_of_another_prompt_are_refused(self):
        old, new = json.loads((ROOT / "v3_1" / "prompt-v3_1.json").read_text(encoding="utf-8")), json.loads((V32 / "prompt-v3_2.json").read_text(encoding="utf-8"))
        with self.assertRaises(AssertionError):
            make_jobs_v3_2.convert({"prompt": {"path": "x\\v3_1\\prompt-v3_1.md", "version": "9", "sha256": "0"}, "jobs": []}, old, new, 1, 1)


class SubmissionEnvelope(unittest.TestCase):
    def test_variant_remark_travels_as_a_note_and_never_as_a_route(self):
        if not (TRANCHE / "outputs" / "pass-a").is_dir():
            self.skipTest("tranche 01 is not in this checkout")
        with tempfile.TemporaryDirectory() as scratch:
            only = Path(scratch) / "only.txt"
            only.write_text("t01-30fa50\nt01-05c2d0\n", encoding="utf-8")
            argv = ["--packets", str(TRANCHE / "packets"), "--reports", str(TRANCHE / "private" / "reports.jsonl"), "--pass-a", str(TRANCHE / "outputs" / "pass-a"),
                    "--pass-b", str(TRANCHE / "outputs" / "pass-b"), "--out", scratch, "--only", str(only), "--reader-prompt", "v3_1"]
            submission.main(argv)                                                            # without the flag: held, nothing submittable
            held = (Path(scratch) / "not_submitted.tsv").read_text(encoding="utf-8")
            self.assertIn("t01-30fa50\theld: has_variant_group", held)
            self.assertFalse(list(Path(scratch).glob("packet-*.envelope.json")))
            submission.main(argv + ["--variant-notes-supported"])                            # with it: the main route goes, the remark as a note; the comma-split reading stays held
            held = (Path(scratch) / "not_submitted.tsv").read_text(encoding="utf-8")
            self.assertIn("t01-05c2d0\theld: first_links_split_by_comma", held)
            envelopes = list(Path(scratch).glob("packet-*.envelope.json"))
            self.assertEqual(len(envelopes), 1)
            envelope = json.loads(envelopes[0].read_text(encoding="utf-8"))
            self.assertEqual(envelope["run"]["tool_version"], "v3_2")
            self.assertEqual(envelope["run"]["prompt_version"], "3.1.0")                     # the prompt the outputs were read under
            fix = envelope["fixes"][0]
            self.assertEqual(len(fix["output"]["routes"]), 1)
            self.assertEqual([r["surfaces"] for r in fix["variant_remarks"]], [[["سليمان بن بلال"]]])
            self.assertTrue(any("variant remark" in note for note in fix["output"]["notes"]))
            self.assertFalse(any("سليمان بن بلال" in link["surface"] for route in fix["output"]["routes"] for link in route["links"]))


if __name__ == "__main__":
    unittest.main()
