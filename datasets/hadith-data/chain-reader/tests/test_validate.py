"""Table-driven tests of validate.py: one accepted output per shape, one rejected output per rule."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from validate import parse_output, repair_offsets, validate  # noqa: E402

TEXT = "حدثنا زهير، ح وحدثني بشر، قالا حدثنا شعبة، عن قتادة. قال كذا وكذا"


def link(plain: str, kind: str = "narrator") -> dict:
    start = TEXT.index(plain)
    return {"surface": plain, "start": start, "end": start + len(plain), "kind": kind}


GOOD = {
    "id": "cr-0001",
    "routes": [
        {"links": [link("زهير"), link("شعبة"), link("قتادة")], "shared_tail_from": 1},
        {"links": [link("بشر"), link("شعبة"), link("قتادة")], "shared_tail_from": 1},
    ],
    "matn_start": TEXT.index("قال كذا"),
    "notes": [],
}


def changed(mutate) -> dict:
    output = copy.deepcopy(GOOD)
    mutate(output)
    return output


def first_link(output: dict) -> dict:
    return output["routes"][0]["links"][0]


# (name, output, error code that must be reported)
REJECTED = [
    ("surface differs from the text", changed(lambda o: first_link(o).update(surface="زهيير")), "surface_mismatch"),
    ("end past the text", changed(lambda o: o["routes"][0]["links"][2].update(end=10_000)), "offsets"),
    ("empty span", changed(lambda o: first_link(o).update(end=first_link(o)["start"])), "offsets"),
    ("bool as offset", changed(lambda o: first_link(o).update(start=True)), "offsets"),
    ("unknown kind", changed(lambda o: first_link(o).update(kind="person")), "kind"),
    ("link inside the matn", changed(lambda o: o.update(matn_start=20)), "in_matn"),
    ("matn offset outside the text", changed(lambda o: o.update(matn_start=-1)), "matn_start"),
    ("wrong id", changed(lambda o: o.update(id="cr-0002")), "id"),
    ("notes not a list of strings", changed(lambda o: o.update(notes="none")), "notes"),
    ("tail index out of range", changed(lambda o: o["routes"][0].update(shared_tail_from=9)), "shared_tail"),
    ("extra key", changed(lambda o: o.update(verdict="ok")), "shape"),
    ("missing key", {key: value for key, value in GOOD.items() if key != "notes"}, "shape"),
    ("route without links", changed(lambda o: o["routes"][0].update(links=[])), "shape"),
    ("link with extra key", changed(lambda o: first_link(o).update(who="x")), "shape"),
]


class ValidateTests(unittest.TestCase):
    def test_good_output_passes(self):
        self.assertEqual(validate(GOOD, TEXT, "cr-0001"), [])

    def test_no_chain_passes(self):
        self.assertEqual(validate({"id": "cr-0001", "routes": [], "matn_start": 0, "notes": ["no chain"]}, TEXT, "cr-0001"), [])

    def test_rejections(self):
        for name, output, code in REJECTED:
            with self.subTest(name):
                errors = validate(output, TEXT, "cr-0001")
                self.assertTrue(any(error.startswith(code + ":") for error in errors), (name, errors))

    def test_not_an_object(self):
        self.assertTrue(validate([1], TEXT)[0].startswith("shape:"))

    def test_order_overlap_and_tail_rules(self):
        reversed_route = changed(lambda o: o["routes"][0].update(links=[link("شعبة"), link("زهير"), link("قتادة")], shared_tail_from=None))
        self.assertTrue(any(e.startswith("order:") for e in validate(reversed_route, TEXT, "cr-0001")))
        overlapping = changed(lambda o: o["routes"][0].update(
            links=[{"surface": TEXT[5:12], "start": 5, "end": 12, "kind": "narrator"}, {"surface": TEXT[9:14], "start": 9, "end": 14, "kind": "narrator"}],
            shared_tail_from=None))
        self.assertTrue(any(e.startswith("overlap:") for e in validate(overlapping, TEXT, "cr-0001")))

        def tail_first(output):
            output["routes"][0].update(links=[link("قتادة"), link("زهير")], shared_tail_from=1)
            output["routes"][1].update(links=[link("بشر"), link("زهير")], shared_tail_from=1)
        self.assertEqual(validate(changed(tail_first), TEXT, "cr-0001"), [], "a declared tail may lie before the route's own links")

        def lonely(output):
            output["routes"].pop(1)
        self.assertTrue(any(e.startswith("shared_tail:") for e in validate(changed(lonely), TEXT, "cr-0001")), "a tail nobody shares is refused")
        twin = changed(lambda o: o["routes"].append(copy.deepcopy(o["routes"][0])))
        self.assertTrue(any(e.startswith("duplicate_route:") for e in validate(twin, TEXT, "cr-0001")))

    def test_fence_is_stripped_and_reported(self):
        parsed, warnings = parse_output("```json\n" + json.dumps(GOOD, ensure_ascii=False) + "\n```")
        self.assertEqual((parsed, warnings), (GOOD, ["fenced"]))
        with self.assertRaises(ValueError):
            parse_output("here is the answer: {}")

    def test_repair_offsets_fixes_counting_not_reading(self):
        shifted = copy.deepcopy(GOOD)
        for route in shifted["routes"]:
            for item in route["links"]:
                item["start"] += 3
                item["end"] += 3
        self.assertTrue(validate(shifted, TEXT, "cr-0001"))
        self.assertEqual(validate(repair_offsets(shifted, TEXT), TEXT, "cr-0001"), [])
        invented = copy.deepcopy(GOOD)
        first_link(invented)["surface"] = "غير موجود"
        self.assertTrue(validate(repair_offsets(invented, TEXT), TEXT, "cr-0001"))

    def test_prompt_examples_pass(self):
        examples = json.loads((ROOT / "examples" / "examples.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(examples), 6)
        for example in examples:
            with self.subTest(example["number"]):
                self.assertEqual(validate(example["output"], example["input"]["text"], example["input"]["id"]), [])


if __name__ == "__main__":
    unittest.main()
