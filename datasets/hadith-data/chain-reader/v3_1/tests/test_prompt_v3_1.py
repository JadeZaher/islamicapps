"""The v3.1 prompt is the file the hash names, no longer than v3's, and says what the three owner rulings say.

    python -B -X utf8 -m unittest discover -s v3_1/tests -p "test_prompt_v3_1.py"        (from chain-reader/)
"""

from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
V31 = Path(__file__).resolve().parent.parent
ROOT = V31.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(V31))

import expand_v3_1  # noqa: E402
import validate_v3_1  # noqa: E402

PROMPT = (V31 / "prompt-v3_1.md").read_text(encoding="utf-8")
RECORD = json.loads((V31 / "prompt-v3_1.json").read_text(encoding="utf-8"))


class PromptV31(unittest.TestCase):
    def test_hash_and_length(self):
        self.assertEqual(hashlib.sha256((V31 / "prompt-v3_1.md").read_bytes()).hexdigest(), RECORD["sha256"])
        self.assertEqual(RECORD["version"], "3.1.0")
        self.assertLessEqual(len(PROMPT), len((ROOT / "v3" / "prompt-v3.md").read_text(encoding="utf-8")), "v3.1 replaces, it does not append")
        self.assertIn("version: 3.1.0", PROMPT)

    def test_the_rulings_are_in_the_prompt(self):
        for fragment in ("The asker is a link", "«و كتب البزنطي إلى أبي الحسن»", "الصادق", "`supplies: \"speaker\"`", "the report has no isnad", "قضى أمير المؤمنين … في", "في نوادر إبراهيم بن هاشم",
                         "«روي عن الأئمة»", "a first-person narrative with implicit transmission"):
            self.assertIn(fragment, PROMPT, fragment)
        self.assertNotIn("does NOT make the asker a transmitter", PROMPT, "the v3 asker rule is gone")

    def test_the_example_outputs_in_the_prompt_validate_against_their_own_input(self):
        """Every `Input` / `Output` pair printed in the prompt is parsed back and validated by the v3.1 validator (the build checks this too; this catches a hand edit of the file)."""
        blocks = PROMPT.split("### Example ")[1:]
        self.assertGreaterEqual(len(blocks), 7)
        for block in blocks:
            body = block.split("Input:\n```\n", 1)[1]
            raw_input, rest = body.split("\n```\n\nOutput:\n```\n", 1)
            raw_output = rest.split("\n```", 1)[0]
            packet, output = json.loads(raw_input), json.loads(raw_output)
            context = packet["context"]
            errors = validate_v3_1.validate_chain(output, packet["text"], packet["id"], context)
            self.assertEqual(errors, [], (packet["id"], errors))
            if output["status"] == "read" and output["groups"]:
                reading, _ = expand_v3_1.expand(output, packet["text"], context)
                self.assertTrue(reading["routes"], packet["id"])


if __name__ == "__main__":
    unittest.main()
