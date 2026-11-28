"""Chain reviewer v1.1: per-item validation, the decision rule, the out-of-order format extension, the built review sets, and the second-pass / re-queue / record flows on the pilot's real packets.

    python -B -X utf8 -m unittest discover -s reviewer/tests -p "test_*.py"            (from chain-reader/)
"""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REVIEWER = HERE.parent
ROOT = REVIEWER.parent
for path in (str(ROOT), str(ROOT / "v3_2"), str(ROOT / "v3_4"), str(REVIEWER)):
    if path not in sys.path:
        sys.path.insert(0, path)
import build_review_packets_v1_1 as builder  # noqa: E402
import out_of_order_validator  # noqa: E402
import record_reviews_v1_1  # noqa: E402
import review_rules_v1_1 as rules  # noqa: E402
import validate_v3_4  # noqa: E402
from validate_review_v1_1 import validate_output, validate_review  # noqa: E402

PILOT = REVIEWER / "pilot-001"
OLD = "1.0.0"                                                       # the pilot ran under prompt v1.0.0
SPAN = "حدثنا بذلك إسحاق بن منصور حدثنا عبد الرحمن بن مهدي"


def pilot_items() -> dict:
    return {i["id"]: i for p in sorted((PILOT / "packets").glob("packet-*.json")) for i in json.loads(p.read_text(encoding="utf-8"))["items"]}


def pilot_reviews() -> dict:
    return {r["id"]: r for p in sorted((PILOT / "outputs" / "pass-1").glob("packet-*.output.json")) for r in json.loads(p.read_text(encoding="utf-8"))["reviews"]}


class PerItemValidation(unittest.TestCase):
    def test_one_invalid_review_does_not_void_the_packet(self):
        packet = json.loads((PILOT / "packets" / "packet-04.json").read_text(encoding="utf-8"))
        output = json.loads((PILOT / "outputs" / "pass-1" / "packet-04.output.json").read_text(encoding="utf-8"))
        result = validate_output(output, packet, OLD)
        self.assertEqual(result["invalid"], ["cr1-750b73"])                      # the pilot lost all 10 of these; now 9 stand
        self.assertEqual(len(result["valid"]), 9)
        self.assertIn("order:", result["items"]["cr1-750b73"][0])
        self.assertEqual(set(result["reviews"]), set(result["valid"]))
        # a header problem makes the whole output unusable: every item is invalid, with the packet-level reason
        wrong = validate_output({**output, "packet_id": "someone-elses"}, packet, OLD)
        self.assertEqual(len(wrong["invalid"]), 10)
        self.assertTrue(all(e[0].startswith("packet:") for e in wrong["items"].values()))
        # a missing and a doubled review are per item
        partial = validate_output({**output, "reviews": output["reviews"][1:] + output["reviews"][2:3]}, packet, OLD)
        self.assertIn("has no review", partial["items"][output["reviews"][0]["id"]][0])
        self.assertIn("reviewed 2 times", partial["items"][output["reviews"][2]["id"]][0])

    def test_v1_1_vocabulary(self):
        items, reviews = pilot_items(), pilot_reviews()
        agreed = next(i for i in items.values() if i["readers_agree"] and not i["readers"]["A"].get("variant_groups"))
        base = {"id": agreed["id"], "decision": "confirm_reading", "question": None, "reasons": [{"claim": "as written", "source": "text", "quote": agreed["text"][:25]}], "variant_verdicts": [],
                "corrected_reading": None, "uncertainty": "low", "uncertainty_note": ""}
        reading = {"id": agreed["id"], "status": "read", "groups": copy.deepcopy(agreed["readers"]["A"]["groups"]), "shared_tail": None, "needs_ruling": False, "notes": [], "fixes": []}
        self.assertEqual(validate_review(base, agreed), [])
        self.assertEqual(validate_review({**base, "question": "unruled: a chain ending «مثله» (working rule 11)"}, agreed), [])           # a note on a confirmation
        self.assertEqual(validate_review({**base, "decision": "refer_to_human", "question": "the open question", "corrected_reading": reading}, agreed), [])  # a partial correction with a referral
        self.assertTrue(validate_review({**base, "decision": "refer_to_human", "question": None}, agreed)[0].startswith("question:"))
        self.assertTrue(validate_review({**base, "corrected_reading": reading}, agreed)[0].startswith("corrected_reading:"))                   # still only with a correction or referral
        self.assertTrue(any(e.startswith("corrected_reading:") for e in validate_review({**base, "decision": "confirm_with_correction"}, agreed)))
        self.assertEqual(reviews[agreed["id"]]["id"], agreed["id"])


class DecisionRule(unittest.TestCase):
    def test_rule_table(self):
        T, F, N = True, False, None
        table = [
            # (name, kwargs..., expected)
            ("a: a correction equal to the agreed reading confirms (held)", ("held", "confirm_with_correction", ["has_variant_group"], T, F, N, {"correction_is": "reading"}), "apply_reading"),
            ("a: ... and on an applied reading it only labels AI reviewed", ("applied", "confirm_with_correction", [], T, F, N, {"correction_is": "reading"}), "label_ai_reviewed"),
            ("a: a correction equal to reader B's reading prefers B", ("held", "confirm_with_correction", ["readers_differ"], F, F, N, {"correction_is": "reader_b"}), "apply_reader_b"),
            ("b: applied + correction, one run: stays applied, disputed", ("applied", "confirm_with_correction", [], T, F, N, {}), "label_disputed"),
            ("b: applied + referral: stays applied, disputed", ("applied", "refer_to_human", [], T, F, N, {}), "label_disputed"),
            ("b: applied + correction, second run agrees: the correction replaces it", ("applied", "confirm_with_correction", [], T, F, True, {}), "apply_correction"),
            ("b: applied + correction, second run differs: still disputed", ("applied", "confirm_with_correction", [], T, F, F, {}), "label_disputed"),
            ("b: applied + no_chain against routes, second run agrees", ("applied", "no_chain", [], T, F, True, {}), "apply_no_chain"),
            ("c: held + confirm applies", ("held", "confirm_reading", ["route_at_most_half_the_longest"], T, F, N, {}), "apply_reading"),
            ("c: pending is held without holds", ("pending", "confirm_reading", [], T, F, N, {}), "apply_reading"),
            ("c: held + correction needs a second matching review", ("held", "confirm_with_correction", ["has_variant_group"], T, F, N, {}), "queue_for_human"),
            ("c: held + correction + second run agrees", ("held", "confirm_with_correction", ["has_variant_group"], T, F, True, {}), "apply_correction"),
            ("c: a non-clearable hold stands whatever is said", ("held", "confirm_reading", ["needs_ruling"], T, F, N, {}), "keep_held"),
            ("c: referral with a partial correction is queued for a human, never applied", ("held", "refer_to_human", ["has_variant_group"], T, F, True, {"has_correction": True}), "queue_for_human"),
            ("c: referral alone stays held", ("held", "refer_to_human", ["has_variant_group"], T, F, N, {}), "keep_held"),
            ("d: keep_stored on an applied reading reverts only when the stored chain differs", ("applied", "keep_stored", [], T, F, N, {"stored_equals_reading": False}), "revert_to_stored"),
            ("d: ... and not when the stored chain equals the reading", ("applied", "keep_stored", [], T, F, N, {"stored_equals_reading": True}), "label_disputed"),
            ("d: ... nor when that is unknown", ("applied", "keep_stored", [], T, F, N, {}), "label_disputed"),
            ("e: a human decision always wins (applied)", ("applied", "confirm_with_correction", [], T, F, True, {"human": "confirmed"}), "human_decides"),
            ("e: a human decision always wins (held)", ("held", "confirm_reading", [], T, F, N, {"human": "rejected"}), "human_decides"),
            ("the hold added by v1.1 is clearable", ("held", "confirm_reading", ["withheld_by_earlier_check"], T, F, N, {}), "apply_reading"),
        ]
        for name, (status, decision, codes, agree, empty, second, extra), expected in table:
            with self.subTest(name):
                self.assertEqual(rules.outcome(status, decision, codes, agree, empty, second, **extra), expected)

    def test_correction_equal_to_the_reading_is_found_on_real_corrections(self):
        items, reviews = pilot_items(), pilot_reviews()
        for opaque in ("cr1-e87ace", "cr1-593d35", "cr1-cd74d5"):                  # the adjudicator's three cosmetic corrections: same routes
            with self.subTest(opaque):
                self.assertEqual(rules.correction_is(items[opaque], reviews[opaque]["corrected_reading"]), "reading")
        for opaque in ("cr1-723cba", "cr1-80cd84", "cr1-4d44fd"):                  # substantive corrections stay corrections
            with self.subTest(opaque):
                self.assertIsNone(rules.correction_is(items[opaque], reviews[opaque]["corrected_reading"]))
        # 6dfc38 differs from the readers only in WHOM it inherits: the tool's agreement ignores inherited links, so the rule must not
        self.assertIsNone(rules.correction_is(items["cr1-6dfc38"], reviews["cr1-6dfc38"]["corrected_reading"]))

    def test_stored_chain_comparison(self):
        items = pilot_items()
        self.assertTrue(rules.stored_equals_reading(items["cr1-80cd84"]))        # reverting would change nothing (adjudication §5.1)
        self.assertTrue(rules.stored_equals_reading(items["cr1-d695ec"]))
        self.assertFalse(rules.stored_equals_reading(items["cr1-e87ace"]))       # the stored chain fuses a gap phrase into a name


class FormatGap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.item = pilot_items()["cr1-750b73"]
        cls.correction = pilot_reviews()["cr1-750b73"]["corrected_reading"]

    def flagged(self, **changes):
        reading = copy.deepcopy(self.correction)
        group = reading["groups"][0]
        group["levels"][2][0]["out_of_order"] = True
        group["connecting_span"] = changes.get("span", SPAN)
        return reading

    def errors(self, reading):
        return out_of_order_validator.validate_chain(reading, self.item["text"], self.item["id"], self.item["context"])

    def test_the_reader_format_refuses_it_and_the_extension_accepts_it(self):
        self.assertIn("occurs only before the previous level", validate_v3_4.validate_chain(self.correction, self.item["text"], self.item["id"], self.item["context"])[0])
        reading = self.flagged()
        self.assertEqual(self.errors(reading), [])
        expanded, errors = out_of_order_validator.expand(reading, self.item["text"], self.item["context"])
        self.assertEqual(errors, [])
        self.assertEqual([(l["surface"], l.get("out_of_order", False)) for l in expanded["routes"][0]["links"]],
                         [("الترمذي", False), ("إسحاق بن منصور", False), ("عبد الرحمن بن مهدي", False), ("عكرمة بن عمار", True)])   # route order: the connection first, then the earlier isnad
        self.assertEqual(expanded["routes"][0]["connecting_span"], SPAN)

    def test_misdeclared_extensions_are_refused(self):
        table = [
            ("a span that is not in the text", self.flagged(span="حدثنا بذلك فلان"), "connecting_span"),
            ("a span that does not contain the connecting names", self.flagged(span="حدثنا بذلك إسحاق بن منصور"), "out_of_order"),
            ("a span missing", {**self.flagged(), "groups": [{k: v for k, v in self.flagged()["groups"][0].items() if k != "connecting_span"}] + self.flagged()["groups"][1:]}, "out_of_order"),
        ]
        first_level = self.flagged()
        first_level["groups"][0]["levels"][0][0]["out_of_order"] = True
        table.append(("the first level flagged", first_level, "out_of_order"))
        unflagged_span = copy.deepcopy(self.correction)
        unflagged_span["groups"][0]["connecting_span"] = SPAN
        table.append(("a span without a flagged item", unflagged_span, "out_of_order"))
        for name, reading, code in table:
            with self.subTest(name):
                errors = self.errors(reading)
                self.assertTrue(errors and any(e.startswith(code) for e in errors), errors)

    def test_the_reviewer_validator_takes_it_only_when_allowed(self):
        review = copy.deepcopy(pilot_reviews()["cr1-750b73"])
        review["corrected_reading"] = self.flagged()
        self.assertTrue(any(e.startswith("corrected_reading:") for e in validate_review(review, self.item)))
        self.assertEqual(validate_review(review, self.item, allow_out_of_order=True), [])


class BuiltSets(unittest.TestCase):
    """The sets are built files: their counts, isolation and jobs (build_review_packets_v1_1.py --sets)."""

    @classmethod
    def setUpClass(cls):
        cls.sets_doc = json.loads((REVIEWER / "SETS.json").read_text(encoding="utf-8"))
        cls.SETS = {name: info["readings"] for name, info in cls.sets_doc["sets"].items()}

    def test_counts_jobs_and_prompt(self):
        prompt = json.loads((REVIEWER / "prompt-reviewer-v1_1.json").read_text(encoding="utf-8"))
        self.assertEqual(prompt["sha256"], hashlib.sha256((REVIEWER / "prompt-reviewer-v1_1.md").read_bytes()).hexdigest())
        expected_names = {"review-applied-b001", "review-disagreements-t02"} | {f"review-t{n:02d}/{part}" for n in range(1, 11) for part in ("eligible", "held")}
        self.assertEqual(set(self.SETS), expected_names)
        for name, count in self.SETS.items():
            with self.subTest(name):
                out = REVIEWER / name
                jobs = json.loads((out / "jobs.json").read_text(encoding="utf-8"))
                self.assertEqual(jobs["expected"]["items"], count)
                self.assertEqual(jobs["expected"]["jobs"], -(-count // 10))
                self.assertEqual(jobs["prompt"]["sha256"], prompt["sha256"])
                seen = []
                for job in jobs["jobs"]:
                    packet = json.loads(Path(job["packet_file"]).read_text(encoding="utf-8"))
                    ids = [i["id"] for i in packet["items"]]
                    seen += ids
                    self.assertEqual(ids, job["expected_items"])
                    self.assertLessEqual(len(ids), 10)
                    self.assertIn("prompt-reviewer-v1_1.md", job["instruction"])
                    self.assertIn(prompt["sha256"], job["instruction"])
                    self.assertIn("claude-opus-5-5", jobs["model"])
                    self.assertEqual(hashlib.sha256(Path(job["packet_file"]).read_bytes()).hexdigest(), job["packet_sha256"])
                self.assertEqual(len(seen), count)
                self.assertEqual(len(set(seen)), count)

    def test_packets_carry_no_private_key_and_the_facts_are_private(self):
        for name in self.SETS:
            with self.subTest(name):
                out = REVIEWER / name
                originals = set(json.loads((out / "private" / "id_map.json").read_text(encoding="utf-8"))["ids"].values())
                for packet_path in sorted((out / "packets").glob("packet-*.json")):
                    text = packet_path.read_text(encoding="utf-8")
                    self.assertFalse([o for o in originals if o in text], packet_path.name)
                    for forbidden in ('"eligible"', '"applies"', '"hadith_id"', "tranche-0", '"stored_chains"', "not_clearable"):
                        self.assertNotIn(forbidden, text)
                    for item in json.loads(text)["items"]:
                        self.assertIn(item["status"], rules.STATUSES)
                        self.assertTrue(all(h["code"] in rules.HOLDS for h in item["holds"]), item["holds"])

    def test_status_and_holds_by_set(self):
        def manifest(name):
            return json.loads((REVIEWER / name / "private" / "manifest.json").read_text(encoding="utf-8"))["items"]
        applied = manifest("review-applied-b001")
        self.assertEqual({r["status"] for r in applied.values()}, {"applied"})
        self.assertGreaterEqual(sum(r["not_clearable"] for r in applied.values()), 12)               # at least the 12 al-Faqih route statements v3.3 would hold
        withheld_expected = {"01": 3, "02": 5}
        for n in range(1, 11):
            tranche = f"{n:02d}"
            eligible, held = manifest(f"review-t{tranche}/eligible"), manifest(f"review-t{tranche}/held")
            self.assertEqual({r["status"] for r in eligible.values()}, {"pending"})
            self.assertEqual(sum(r["not_clearable"] for r in eligible.values()), 0)
            self.assertEqual({r["status"] for r in held.values()}, {"held"})
            self.assertEqual(sum("withheld_by_earlier_check" in r["holds"] for r in held.values()), withheld_expected.get(tranche, 0))
            self.assertTrue(all(r["readers_agree"] for r in {**eligible, **held}.values()))
            self.assertFalse(set(r["id"] for r in eligible.values()) & set(r["id"] for r in held.values()))
        differ = manifest("review-disagreements-t02")
        self.assertTrue(all(not r["readers_agree"] and "readers_differ" in r["holds"] for r in differ.values()))

    def test_the_applied_set_is_the_fix_stores(self):
        store = ROOT.parents[2] / "reviews" / "ai" / "records" / "chain-fixes"
        if not store.is_dir():
            self.skipTest("no fix store")
        state = json.loads((store / "state.json").read_text(encoding="utf-8"))["fixes"]
        live_applied = sum(1 for f in state if f.get("database") == "applied")
        ids, provenance = builder.applied_b001()
        built = (REVIEWER / "review-applied-b001" / "private" / "applied_ids.txt").read_text(encoding="utf-8").split()
        self.assertEqual(provenance["applied_fixes"], live_applied)
        self.assertEqual(provenance["b001_applied_fixes"], len(ids))
        self.assertEqual(sorted(ids), sorted(built))                                                 # the store has not moved since the build


class Flows(unittest.TestCase):
    """Second pass, re-queue and record, on the pilot's real packets and pass-1 outputs (copied; prompt version 1.0.0)."""

    def setUp(self):
        self.temp = Path(tempfile.mkdtemp())
        self.batch = self.temp / "pilot"
        shutil.copytree(PILOT / "packets", self.batch / "packets")
        shutil.copytree(PILOT / "outputs", self.batch / "outputs")
        shutil.copytree(PILOT / "private", self.batch / "private")
        self.prompt = json.loads((REVIEWER / "prompt-reviewer-v1_1.json").read_text(encoding="utf-8"))

    def tearDown(self):
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_second_pass_takes_only_real_corrections_and_requeue_takes_the_invalid_item(self):
        builder.second_pass("pilot", self.prompt, base=self.temp, prompt_version=OLD)
        jobs = json.loads((self.batch / "jobs-pass-2.json").read_text(encoding="utf-8"))
        ids = [i for j in jobs["jobs"] for i in j["expected_items"]]
        # 22 corrections in the pilot, 1 invalid (750b73), 3 cosmetic (same routes as the readers': a confirmation, no second run): 18 left
        self.assertEqual(len(ids), 18)
        self.assertNotIn("cr1-750b73", ids)
        self.assertFalse({"cr1-e87ace", "cr1-593d35", "cr1-cd74d5"} & set(ids))
        self.assertIn("cr1-6dfc38", ids)                                                              # differs from the readers only in the inherited name: a real correction
        builder.requeue("pilot", "1", self.prompt, root=self.temp, prompt_version=OLD)
        again = json.loads((self.batch / "jobs-pass-1r.json").read_text(encoding="utf-8"))
        self.assertEqual([i for j in again["jobs"] for i in j["expected_items"]], ["cr1-750b73"])
        packet = json.loads(Path(again["jobs"][0]["packet_file"]).read_text(encoding="utf-8"))
        self.assertEqual(packet["items"][0]["text"], pilot_items()["cr1-750b73"]["text"])            # same content for the new worker

    def test_record_says_what_the_rule_does_with_each_item(self):
        summary = record_reviews_v1_1.record(self.batch, prompt_version=OLD)
        self.assertEqual((summary["valid"], summary["invalid_or_missing (re-queue)"]), (80, 1))
        outcomes = {}
        for line in (self.batch / "private" / "outcomes.tsv").read_text(encoding="utf-8").splitlines()[1:]:
            fields = line.split("\t")
            outcomes[fields[0]] = fields[8]
        self.assertEqual(outcomes["cr1-750b73"], "requeue")
        self.assertEqual(outcomes["cr1-e87ace"], "label_ai_reviewed")                                # v1 reverted this right reading to a worse stored chain
        self.assertEqual(outcomes["cr1-80cd84"], "label_disputed")                                   # applied + a (right) correction: stays applied, labelled, queued
        self.assertEqual(outcomes["cr1-723cba"], "queue_for_human")                                  # held + one correction run
        self.assertEqual(outcomes["cr1-2fc4ff"], "keep_held")                                        # al-Faqih route statement: a non-clearable hold
        self.assertEqual(summary["second_pass_needed"], 18)


if __name__ == "__main__":
    unittest.main()
