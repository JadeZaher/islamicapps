"""v3.4 tool, prompt, jobs and re-read set, on the judges' real cases (v3_4/README.md §tests).

    python -B -X utf8 -m unittest discover -s v3_4/tests -p "test_*.py"            (from chain-reader/)
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
V34 = HERE.parent
ROOT = V34.parent
for path in (str(ROOT), str(ROOT / "v3_2"), str(V34), str(HERE)):
    if path not in sys.path:
        sys.path.insert(0, path)
from judge_cases_v3_4 import ENCOUNTERS, MUTABAA_1061E3, TWO_SAYINGS, packet  # noqa: E402
import expand_v3_4  # noqa: E402
from expand_v3_4 import expand, readings_agree, strip_sayings  # noqa: E402
from holds_v3_4 import compute_holds  # noqa: E402
from make_jobs_v3_4 import convert, prompt_chars  # noqa: E402
from to_submission_v3_4 import v1_shape  # noqa: E402
from triage_v3_4 import triage_one  # noqa: E402
from validate_v3_4 import validate_chain  # noqa: E402
import validate_v3_2  # noqa: E402
from validate import parse_output  # noqa: E402


def read(report_id: str, output: dict, tranche: str):
    row = packet(tranche, report_id)
    errors = validate_chain(output, row["text"], report_id, row["context"])
    reading, _ = expand(output, row["text"], row["context"]) if not errors else (None, None)
    return row, errors, reading


def codes(reading, output, row) -> list[str]:
    return [h["code"] for h in compute_holds(reading, output, row["text"], row["context"], None, output)]


class TwoSayings(unittest.TestCase):
    def test_judge_cases_store_both_sayings_labelled(self):
        for report_id, (tranche, output) in TWO_SAYINGS.items():
            with self.subTest(report_id):
                row, errors, reading = read(report_id, output, tranche)
                self.assertEqual(errors, [])
                self.assertEqual([s["saying"] for s in reading["sayings"]], [1, 2])
                self.assertEqual([s["label"] for s in reading["sayings"]], ["Chain of the first saying", "Chain of the second saying"])
                self.assertTrue(all(row["text"][s["start"]:s["end"]] == s["opens"] for s in reading["sayings"]))
                self.assertEqual({r["saying"] for r in reading["routes"]}, {1, 2})

    def test_023097_second_saying_ends_at_the_father_who_answers(self):
        row, _, reading = read("t02-023097", TWO_SAYINGS["t02-023097"][1], "02")
        ends = {r["saying"]: r["links"][-1]["surface"] for r in reading["routes"]}
        self.assertEqual(ends, {1: "جابر بن سمرة", 2: "أبي"})

    def test_102af2_second_saying_runs_through_yunus_only(self):
        _, _, reading = read("t02-102af2", TWO_SAYINGS["t02-102af2"][1], "02")
        second = [r for r in reading["routes"] if r["saying"] == 2]
        self.assertEqual(len(second), 1)
        self.assertEqual([l["surface"] for l in second[0]["links"][1:3]], ["يونس بن عبد الأعلى", "عبد الله بن وهب"])
        self.assertEqual(second[0]["links"][-2]["kind"], "unnamed")

    def test_routes_of_different_sayings_are_not_judged_as_sharing_a_tail(self):
        # unlabelled, saying 1 ends at جابر بن سمرة, who stands inside saying 2's route: v3.3's tail hold fires; labelled, it does not
        tranche, output = TWO_SAYINGS["t02-023097"]
        row = packet(tranche, "t02-023097")
        unlabelled = strip_sayings(output)
        self.assertIn("route_ends_inside_another_route", codes(expand(unlabelled, row["text"], row["context"])[0], unlabelled, row))
        held = codes(expand(output, row["text"], row["context"])[0], output, row)
        self.assertNotIn("route_ends_inside_another_route", held)
        self.assertEqual(held, ["two_sayings_not_supported"])

    def test_a_later_saying_that_drops_the_shared_head_is_held(self):
        tranche, output = TWO_SAYINGS["t02-102af2"]
        headless = copy.deepcopy(output)
        headless["groups"][1]["levels"] = headless["groups"][1]["levels"][3:]          # starts at «بكير بن الأشج»
        row = packet(tranche, "t02-102af2")
        reading, errors = expand(headless, row["text"], row["context"])
        self.assertEqual(errors, [])
        self.assertIn("saying_route_starts_inside_another_route", codes(reading, headless, row))
        self.assertNotIn("saying_route_starts_inside_another_route", codes(expand(output, row["text"], row["context"])[0], output, row))

    def test_label_errors(self):
        tranche, good = TWO_SAYINGS["t01-520f51"]
        row = packet(tranche, "t01-520f51")

        def changed(change):
            output = copy.deepcopy(good)
            change(output)
            return output
        table = [
            ("one group unlabelled", lambda o: [o["groups"][1].pop("saying"), o["groups"][1].pop("saying_opens")], "saying: g1 has no `saying`"),
            ("only one of the two keys", lambda o: o["groups"][1].pop("saying_opens"), "saying: g1 needs both"),
            ("a shared tail with labels", lambda o: o.update(shared_tail=[[{"surface": "عائشة", "kind": "narrator"}]]), "saying: `shared_tail` must be null"),
            ("an opening not in the text", lambda o: o["groups"][1].update(saying_opens="لم تكن تصلي في البيت"), "saying_opens_not_in_text"),
            ("numbers against the text's order", lambda o: [o["groups"][0].update(saying=2), o["groups"][1].update(saying=1)], "saying_order"),
            ("two sayings with one opening", lambda o: o["groups"][1].update(saying_opens=o["groups"][0]["saying_opens"]), "saying: sayings 1 and 2 name the same opening"),
            ("an opening of one word", lambda o: o["groups"][1].update(saying_opens="أنها"), "saying: g1 `saying_opens` must be"),
            ("saying zero", lambda o: o["groups"][1].update(saying=0), "saying: g1 `saying` must be a whole number"),
        ]
        self.assertEqual(validate_chain(good, row["text"], "t01-520f51", row["context"]), [])
        for name, change, expected in table:
            with self.subTest(name):
                errors = validate_chain(changed(change), row["text"], "t01-520f51", row["context"])
                self.assertTrue(any(e.startswith(expected) for e in errors), errors)

    def test_agreement_needs_the_same_sayings(self):
        tranche, output = TWO_SAYINGS["t01-520f51"]
        row = packet(tranche, "t01-520f51")
        labelled = expand(output, row["text"], row["context"])[0]
        unlabelled = expand(strip_sayings(output), row["text"], row["context"])[0]
        relabelled = copy.deepcopy(output)
        relabelled["groups"][1].update(saying_opens="أنها لم تكن تفعل ذلك وقالت")              # another span of the same saying: still one reading
        merged = copy.deepcopy(output)
        merged["groups"][1].update(saying=1, saying_opens=output["groups"][0]["saying_opens"])   # both routes under saying 1
        self.assertTrue(readings_agree(labelled, expand(relabelled, row["text"], row["context"])[0]))
        self.assertFalse(readings_agree(labelled, unlabelled))
        self.assertFalse(readings_agree(labelled, expand(merged, row["text"], row["context"])[0]))

    def test_triage_and_envelope_carry_the_label(self):
        tranche, output = TWO_SAYINGS["t01-520f51"]
        row = packet(tranche, "t01-520f51")
        held = triage_one("t01-520f51", row, {"a": copy.deepcopy(output), "b": copy.deepcopy(output)}, None)
        self.assertTrue(held["agree"])
        self.assertEqual(held["holds"], ["two_sayings_not_supported"])
        released = triage_one("t01-520f51", row, {"a": copy.deepcopy(output), "b": copy.deepcopy(output)}, None, sayings_supported=True)
        self.assertTrue(released["eligible"])
        self.assertEqual(released["suppressed"], ["two_sayings_not_supported"])
        shaped, sayings, _ = v1_shape(released["reading"]["expanded_a"])
        self.assertEqual([(s["saying"], s["label"], s["routes"]) for s in sayings], [(1, "Chain of the first saying", [0]), (2, "Chain of the second saying", [1])])
        self.assertEqual([l["surface"] for l in shaped["routes"][1]["links"]][-2:], ["عروة", "عائشة"])
        self.assertTrue(set(shaped["routes"][0]) == {"links", "shared_tail_from"})                # the routes stay plain v1 routes
        self.assertTrue(any(note.startswith("Chain of the second saying («أنها لم تكن تفعل ذلك»)") for note in shaped["notes"]))

    def test_openings_at_different_places_are_held(self):
        tranche, output = TWO_SAYINGS["t01-520f51"]
        row = packet(tranche, "t01-520f51")
        other = copy.deepcopy(output)
        other["groups"][1]["saying_opens"] = "وقالت إنما نزله رسول الله"
        result = triage_one("t01-520f51", row, {"a": copy.deepcopy(output), "b": other}, None, sayings_supported=True)
        self.assertTrue(result["agree"])
        self.assertIn("saying_openings_differ", result["holds"])


class Encounters(unittest.TestCase):
    def test_the_one_who_speaks_in_the_story_is_the_last_link(self):
        for report_id, (tranche, output, last) in ENCOUNTERS.items():
            with self.subTest(report_id):
                row, errors, reading = read(report_id, output, tranche)
                self.assertEqual(errors, [])
                self.assertEqual([r["links"][-1]["surface"] for r in reading["routes"]], [last])
                self.assertEqual(reading["sayings"], [])
                self.assertEqual(codes(reading, output, row), [])

    def test_8b818b_uthman_only_in_the_scene_is_no_link(self):
        _, _, reading = read("t02-8b818b", ENCOUNTERS["t02-8b818b"][1], "02")
        self.assertNotIn("عثمان", [l["surface"] for l in reading["routes"][0]["links"]])
        self.assertGreater(reading["routes"][0]["links"][-1]["start"], packet("02", "t02-8b818b")["text"].index("فقال علي"))


class Mutabaa(unittest.TestCase):
    def test_1061e3_mutabaa_is_a_variant_remark(self):
        tranche, output = MUTABAA_1061E3
        row, errors, reading = read("t02-1061e3", output, tranche)
        self.assertEqual(errors, [])
        self.assertEqual(len(reading["routes"]), 1)
        self.assertIn("تابعه قتيبة", reading["variant_remarks"][0]["quote"])


class UnlabelledOutputsUnchanged(unittest.TestCase):
    def test_real_v3_2_outputs_validate_alike(self):
        """Every pass-A output of tranche 02's first five packets: the v3.4 validator accepts exactly what v3.2's accepts (an unlabelled output is the same format)."""
        directory = ROOT / "tranches" / "tranche-02"
        checked = 0
        for name in ("packet-001.jsonl", "packet-002.jsonl", "packet-003.jsonl", "packet-004.jsonl", "packet-005.jsonl"):
            for line in (directory / "packets" / name).read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                output, _ = parse_output((directory / "outputs" / "pass-a" / f"{row['id']}.json").read_text(encoding="utf-8"))
                self.assertEqual(bool(validate_chain(output, row["text"], row["id"], row["context"])), bool(validate_v3_2.validate_chain(output, row["text"], row["id"], row["context"])), row["id"])
                checked += 1
        self.assertEqual(checked, 100)


class PromptAndJobs(unittest.TestCase):
    def test_prompt_hash_length_and_rules(self):
        record = json.loads((V34 / "prompt-v3_4.json").read_text(encoding="utf-8"))
        data = (V34 / "prompt-v3_4.md").read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), record["sha256"])
        text = data.decode("utf-8")
        self.assertLessEqual(len(text), len((ROOT / "v3_2" / "prompt-v3_2.md").read_text(encoding="utf-8")))
        for phrase in ("4a. **Two sayings", "**A narrated encounter**", "«علي ابنه» is no link", "**A mutabaʿa is such a remark**", '"saying": 1, "saying_opens"', "«روي عن الأئمة»"):
            self.assertIn(phrase, text)
        rule_11 = text.split("11. **`needs_ruling`")[1].split("12.")[0]
        self.assertNotIn("two sayings in one report, the second with its own isnad;", rule_11)

    def test_example_texts_are_prefixes_of_the_real_reports(self):
        for line in (V34 / "examples" / "example-packets.jsonl").read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if row.get("source", {}).get("packet", "").startswith("tranches/tranche-0") and row["id"][:3] in ("t01", "t02"):
                with self.subTest(row["id"]):
                    self.assertTrue(packet(row["id"][1:3], row["id"])["text"].startswith(row["text"]))

    def test_jobs_conversion_changes_only_the_prompt(self):
        jobs = json.loads((ROOT / "tranches" / "tranche-07" / "jobs.json").read_text(encoding="utf-8"))
        new = json.loads((V34 / "prompt-v3_4.json").read_text(encoding="utf-8"))
        converted = convert(jobs, new, prompt_chars(jobs["prompt"]["path"]), new["chars"])
        self.assertEqual(converted["prompt"]["sha256"], new["sha256"])
        self.assertTrue(converted["prompt"]["path"].endswith("prompt-v3_4.md"))
        for before, after in zip(jobs["jobs"], converted["jobs"]):
            self.assertEqual({k for k in before if before[k] != after[k]}, {"instruction", "input_chars"})
            self.assertIn(new["sha256"], after["instruction"])
        self.assertEqual({k for k in jobs if k not in ("jobs", "prompt_note") and jobs[k] != converted[k]}, {"prompt"})
        self.assertEqual(set(converted) - set(jobs), {"prompt_note"} - set(jobs))


class RereadSet(unittest.TestCase):
    def test_packets_reuse_their_source_text_and_context(self):
        base = V34 / "reread-001"
        id_map = json.loads((base / "private" / "id_map.json").read_text(encoding="utf-8"))["ids"]
        manifest = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
        jobs = json.loads((base / "jobs.json").read_text(encoding="utf-8"))
        sources: dict[str, dict] = {}
        seen = 0
        for name, info in manifest["packets"].items():
            lines = (base / "packets" / name).read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), info["reports"])
            self.assertLessEqual(len(lines), 20)
            for line in lines:
                row = json.loads(line)
                self.assertEqual(set(row), {"id", "text", "context"})
                origin = id_map[row["id"]]
                if origin["source_packet"] not in sources:
                    sources[origin["source_packet"]] = {json.loads(l)["id"]: json.loads(l) for l in (ROOT / origin["source_packet"]).read_text(encoding="utf-8").splitlines() if l.strip()}
                source = sources[origin["source_packet"]][origin["id"]]
                self.assertEqual((row["text"], row["context"]), (source["text"], source["context"]))
                self.assertTrue(row["id"].startswith("r4-") and origin["id"] not in line[:40])
                seen += 1
        self.assertEqual(seen, manifest["reports"])
        self.assertEqual(len(id_map), manifest["reports"])
        self.assertEqual(sum(j["expected_files"] for j in jobs["jobs"] if j["pass"] == "a"), manifest["reports"])
        self.assertEqual(sum(j["expected_files"] for j in jobs["jobs"] if j["pass"] == "b"), manifest["reports"])
        self.assertEqual(jobs["prompt"]["sha256"], json.loads((V34 / "prompt-v3_4.json").read_text(encoding="utf-8"))["sha256"])


if __name__ == "__main__":
    unittest.main()
