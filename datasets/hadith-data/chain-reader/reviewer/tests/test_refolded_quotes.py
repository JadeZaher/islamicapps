"""Reviewer quote rule (validate_review_v1_1.py): vowel marks, tatweel and whitespace are folded out of QUOTES only; letters match exactly. Real failing quotes from review-applied-b001's pass-1 output.

    python -B -X utf8 -m unittest discover -s reviewer/tests -p "test_*.py"            (from chain-reader/)
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REVIEWER = HERE.parent
ROOT = REVIEWER.parent
for path in (str(ROOT), str(ROOT / "v3_2"), str(ROOT / "v3_4"), str(REVIEWER)):
    if path not in sys.path:
        sys.path.insert(0, path)
import review_io_v1_1 as io  # noqa: E402
import validate_review_v1_1 as v  # noqa: E402

BATCH = REVIEWER / "review-applied-b001"
# real pass-1 reviews (vocalised Imami reports) whose first text quote differs from the text in vowel marks only; the old exact rule recorded them invalid
REAL = ("cr1-df4e9a", "cr1-1c513a", "cr1-41a40f", "cr1-b4c202", "cr1-48afa7", "cr1-5e03b2", "cr1-a84010", "cr1-4f9811")


def pass_one() -> tuple[dict, dict]:
    """({item id: packet item}, {item id: review}) of review-applied-b001 pass 1, as the reviewer wrote them."""
    items, reviews = {}, {}
    for packet_path in sorted((BATCH / "packets").glob("packet-*.json")):
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        items.update({i["id"]: i for i in packet["items"]})
        output_path = io.outputs_dir(BATCH, "1") / packet_path.name.replace(".json", ".output.json")
        if output_path.is_file():
            output = json.loads(output_path.read_text(encoding="utf-8"))
            reviews.update({r["id"]: r for r in output["reviews"]})
    return items, reviews


def first_inexact(item: dict, review: dict) -> dict:
    return next(r for r in review["reasons"] if r["source"] == "text" and r["quote"] not in item["text"])


@unittest.skipUnless(BATCH.is_dir(), "review-applied-b001 is not in this checkout")
class QuoteRule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items, cls.reviews = pass_one()

    def test_real_quotes_that_differ_only_in_vowel_marks_are_found_as_the_texts_own_characters(self):
        for opaque in REAL:
            with self.subTest(opaque):
                item, reason = self.items[opaque], first_inexact(self.items[opaque], self.reviews[opaque])
                self.assertNotIn(reason["quote"], item["text"])                                       # the old rule rejected it
                found = v.find_quote(reason["quote"], [item["text"]])
                self.assertIn(found, item["text"])                                                    # the text's own characters
                self.assertEqual(v.MARKS.sub("", found), v.MARKS.sub("", reason["quote"]))            # the same letters, nothing else changed
                self.assertEqual(v.check_quote(item, "text", reason["quote"], "x"), [])

    def test_a_quote_that_is_not_the_text_stays_invalid(self):
        item = self.items[REAL[0]]
        quote = first_inexact(item, self.reviews[REAL[0]])["quote"]
        letters = [(i, c) for i, c in enumerate(quote) if not v.MARKS.match(c) and c != " "]
        i, c = letters[len(letters) // 2]
        two_places = item["text"][:30].strip() + " " + item["text"][-30:].strip()                    # both ends of the text, nothing between
        cases = {
            "one letter different": quote[:i] + ("ت" if c != "ت" else "ب") + quote[i + 1:],
            "hamza folded (a different word)": v.MARKS.sub("", item["text"]).replace("أ", "ا", 1) if "أ" in item["text"] else None,
            "two non-adjacent places": two_places,
            "marks only": "َّـ",
        }
        for label, bad in cases.items():
            if bad is None:
                continue
            with self.subTest(label):
                self.assertTrue(v.check_quote(item, "text", bad, "x"), label)

    def test_hamza_is_not_folded(self):
        self.assertIsNone(v.find_quote("اباه", ["قال أَبَاه"]))
        self.assertEqual(v.find_quote("أباه", ["قال أَبَاه"]), "أَبَاه")

    def test_a_valid_review_is_recorded_with_the_texts_characters_and_marked(self):
        packet = {"packet_id": "review-applied-b001-p1-01", "items": [self.items[o] for o in REAL[:3]]}
        output = {"format": "shura-chain-review-output/1", "specialist_id": "chain-reviewer", "prompt_version": "1.1.0", "packet_id": packet["packet_id"], "reviews": [self.reviews[o] for o in REAL[:3]]}
        result = v.validate_output(output, packet)
        self.assertEqual(result["invalid"], [])
        for opaque in REAL[:3]:
            review = result["reviews"][opaque]
            self.assertGreaterEqual(review["quote_refolded"], 1)
            self.assertEqual(result["refolded"][opaque], review["quote_refolded"])
            for reason in review["reasons"]:
                self.assertTrue(any(reason["quote"] in s for s in v.quote_pool(self.items[opaque], reason["source"])))     # every stored quote is exact now
        mutated = copy.deepcopy(output)
        quote = first_inexact(self.items[REAL[0]], mutated["reviews"][0])
        quote["quote"] = quote["quote"].replace("ب", "ت", 1) if "ب" in quote["quote"] else quote["quote"].replace("ن", "ب", 1)
        again = v.validate_output(mutated, packet)
        self.assertEqual(again["invalid"], [REAL[0]])                                                  # one item invalid, the rest of the packet stands
        self.assertIn("quote_not_exact", again["items"][REAL[0]][0])

    def test_every_quote_of_pass_one_and_its_requeue_is_exact_or_marks_only(self):
        """Over every reason quote of pass 1: whatever is accepted equals what the reviewer wrote letter for letter (marks and whitespace aside)."""
        checked = 0
        for opaque, review in self.reviews.items():
            if opaque not in self.items:
                continue
            for reason in review["reasons"]:
                pool = v.quote_pool(self.items[opaque], reason["source"])
                found = v.find_quote(reason["quote"], pool)
                if found is not None:
                    checked += 1
                    self.assertEqual(" ".join(v.MARKS.sub("", found).split()), " ".join(v.MARKS.sub("", reason["quote"]).split()))
        self.assertGreater(checked, 400)


if __name__ == "__main__":
    unittest.main()
