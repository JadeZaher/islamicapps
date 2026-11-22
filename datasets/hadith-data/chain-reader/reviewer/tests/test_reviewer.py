"""Chain reviewer: the output validator (table-driven, on real pilot packet items), the decision rule, the packets' isolation and the pilot scorer (reviewer/README.md §tests).

    python -B -X utf8 -m unittest discover -s reviewer/tests -p "test_*.py"            (from chain-reader/)
"""

from __future__ import annotations

import copy
import csv
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REVIEWER = HERE.parent
ROOT = REVIEWER.parent
for path in (str(ROOT), str(ROOT / "v3_2"), str(ROOT / "v3_4"), str(REVIEWER), str(REVIEWER / "pilot-001")):
    if path not in sys.path:
        sys.path.insert(0, path)
from review_rules import HOLDS, clearable, outcome  # noqa: E402
from validate_review import validate_output  # noqa: E402
import score_reviewer  # noqa: E402

PILOT = REVIEWER / "pilot-001"


def packets() -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted((PILOT / "packets").glob("packet-*.json"))]


def find(predicate) -> tuple[dict, dict]:
    for packet in packets():
        for item in packet["items"]:
            if predicate(item):
                return packet, item
    raise LookupError


def review_for(item: dict, decision: str = "confirm_reading") -> dict:
    groups = [g for tag in ("A", "B") for g in item["readers"][tag].get("variant_groups") or []]
    return {"id": item["id"], "decision": decision, "question": None, "reasons": [{"claim": "the chain as written", "source": "text", "quote": item["text"][:25]}],
            "variant_verdicts": [{"group": g["group"], "verdict": "remark_about_another_version", "quote": g["remark"]} for g in groups],
            "corrected_reading": None, "uncertainty": "low", "uncertainty_note": ""}


def single(packet: dict, item: dict, review: dict) -> list[str]:
    """Errors of an output whose only review is `review`, against a packet reduced to that item."""
    one = dict(packet, items=[item])
    return validate_output({"format": "shura-chain-review-output/1", "specialist_id": "chain-reviewer", "prompt_version": "1.0.0", "packet_id": packet["packet_id"], "reviews": [review]}, one)


class ValidateReview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packet, cls.agreed = find(lambda i: i["readers_agree"] and i["readers"]["A"].get("variant_groups"))
        cls.previous_packet, cls.with_previous = find(lambda i: i["readers_agree"] and any(p.get("chain_text") for p in i["context"].get("previous_reports") or []))
        cls.differ_packet = cls.packet                                # the pilot holds agreed readings only: the same item, marked as differing readers
        cls.differ = dict(copy.deepcopy(cls.agreed), readers_agree=False)

    def test_valid_reviews_pass(self):
        self.assertEqual(single(self.packet, self.agreed, review_for(self.agreed)), [])
        corrected = review_for(self.agreed, "confirm_with_correction")
        corrected["corrected_reading"] = {"id": self.agreed["id"], "status": "read", "groups": copy.deepcopy(self.agreed["readers"]["A"]["groups"]), "shared_tail": None,
                                          "needs_ruling": False, "notes": [], "fixes": []}
        self.assertEqual(single(self.packet, self.agreed, corrected), [])
        refer = review_for(self.agreed, "refer_to_human")
        refer["question"] = "a first-person narrative with an implicit transmission"
        self.assertEqual(single(self.packet, self.agreed, refer), [])
        previous = next(p for p in self.with_previous["context"]["previous_reports"] if p.get("chain_text"))
        quoting = review_for(self.with_previous)
        quoting["reasons"].append({"claim": "the earlier report", "source": previous["ref"], "quote": previous["chain_text"][:15]})
        self.assertEqual(single(self.previous_packet, self.with_previous, quoting), [])

    def test_rejected_reviews(self):
        item = self.agreed
        group = item["readers"]["A"]["variant_groups"][0]["group"]

        def changed(change, decision="confirm_reading"):
            review = review_for(item, decision)
            change(review)
            return review
        table = [
            ("a decision outside the vocabulary", changed(lambda r: r.update(decision="approve")), "decision:"),
            ("a quote not exact (a letter changed)", changed(lambda r: r["reasons"][0].update(quote=item["text"][:25].replace(item["text"][3], "ـ", 1) + "x")), "quote_not_exact"),
            ("a quote from an unknown source", changed(lambda r: r["reasons"][0].update(source="memory")), "quote_source"),
            ("a quote from a previous report that is not there", changed(lambda r: r["reasons"][0].update(source="prev9")), "quote_source"),
            ("no reasons", changed(lambda r: r.update(reasons=[])), "reasons:"),
            ("a variant group without a verdict", changed(lambda r: r.update(variant_verdicts=[])), f"variant_verdicts: {item['id']} has no verdict for variant group {group}"),
            ("a verdict outside the vocabulary", changed(lambda r: r["variant_verdicts"][0].update(verdict="maybe")), "variant_verdicts:"),
            ("a verdict for a group no reader wrote", changed(lambda r: r["variant_verdicts"].append({"group": "A.g9", "verdict": "route_of_this_saying", "quote": item["text"][:10]})), "variant_verdicts:"),
            ("refer_to_human without the question", changed(lambda r: None, "refer_to_human"), "question:"),
            ("a question on a confirmation", changed(lambda r: r.update(question="who is he")), "question:"),
            ("a correction without the reading", changed(lambda r: None, "confirm_with_correction"), "corrected_reading:"),
            ("a correction whose surface is not in the text", changed(lambda r: r.update(corrected_reading={"id": item["id"], "status": "read", "groups": [{"levels": [[{"surface": "زيد بن عمرو بن نفيل الخطابي", "kind": "narrator"}]]}],
                                                                                                            "shared_tail": None, "needs_ruling": False, "notes": [], "fixes": []}), "confirm_with_correction"), "corrected_reading:"),
            ("an empty correction (that is no_chain)", changed(lambda r: r.update(corrected_reading={"id": item["id"], "status": "read", "groups": [], "shared_tail": None, "needs_ruling": False, "notes": [], "fixes": []}),
                                                               "confirm_with_correction"), "corrected_reading:"),
            ("a reading on a decision that is not a correction", changed(lambda r: r.update(corrected_reading={"id": item["id"]})), "corrected_reading:"),
            ("prefer a reader when the readers agree", changed(lambda r: None, "prefer_reader_a"), "decision:"),
            ("uncertainty outside the vocabulary", changed(lambda r: r.update(uncertainty="none")), "uncertainty:"),
        ]
        for name, review, expected in table:
            with self.subTest(name):
                errors = single(self.packet, item, review)
                self.assertTrue(any(e.startswith(expected) for e in errors), errors)

    def test_confirming_a_disagreement_is_refused(self):
        self.assertTrue(any(e.startswith("decision:") for e in single(self.differ_packet, self.differ, review_for(self.differ))))
        self.assertEqual(single(self.differ_packet, self.differ, review_for(self.differ, "prefer_reader_b")), [])

    def test_every_item_reviewed_once(self):
        packet = packets()[0]
        reviews = [review_for(item) for item in packet["items"]]
        header = {"format": "shura-chain-review-output/1", "specialist_id": "chain-reviewer", "prompt_version": "1.0.0", "packet_id": packet["packet_id"]}
        self.assertTrue(any(e.startswith("item:") and "has no review" in e for e in validate_output({**header, "reviews": reviews[1:]}, packet)))
        self.assertTrue(any("reviewed 2 times" in e for e in validate_output({**header, "reviews": reviews + reviews[:1]}, packet)))
        self.assertTrue(any(e.startswith("header: prompt_version") for e in validate_output({**header, "prompt_version": "0.9.0", "reviews": reviews}, packet)))


class DecisionRule(unittest.TestCase):
    def test_owner_rule_on_clearable_holds(self):
        for code in ("route_at_most_half_the_longest", "route_ends_inside_another_route", "has_variant_group", "mutabaa_marker", "readers_differ", "flag_one_reader"):
            self.assertTrue(clearable(code), code)
        for code in ("needs_ruling", "needs_ruling_prophet_no_transmitter", "needs_ruling_faqih_route_statement", "back_reference_without_previous_report", "inherited_from_far_report",
                     "stale_text", "two_sayings_not_supported", "some_future_hold"):
            self.assertFalse(clearable(code), code)

    def test_outcomes(self):
        table = [
            ("held, agreed, shape hold, confirmed", ("held", "confirm_reading", ["route_at_most_half_the_longest"], True, False, None), "apply_reading"),
            ("held, unruled question, confirmed", ("held", "confirm_reading", ["has_variant_group", "needs_ruling"], True, False, None), "keep_held"),
            ("held, missing previous report, corrected twice alike", ("held", "confirm_with_correction", ["back_reference_without_previous_report"], True, False, True), "keep_held"),
            ("held, correction, one run", ("held", "confirm_with_correction", ["has_variant_group"], True, False, None), "queue_for_human"),
            ("held, correction, second run agrees", ("held", "confirm_with_correction", ["has_variant_group"], True, False, True), "apply_correction"),
            ("held, correction, second run differs", ("held", "confirm_with_correction", ["has_variant_group"], True, False, False), "queue_for_human"),
            ("held, readers differ, prefer B", ("held", "prefer_reader_b", ["readers_differ"], False, False, None), "apply_reader_b"),
            ("held, no chain on an agreed empty reading", ("held", "no_chain", ["empty_reading_transmission_name"], True, True, None), "apply_reading"),
            ("held, no chain against routes, one run", ("held", "no_chain", ["route_ends_inside_another_route"], True, False, None), "queue_for_human"),
            ("held, keep stored", ("held", "keep_stored", ["has_variant_group"], True, False, None), "discard_reading"),
            ("held, refer", ("held", "refer_to_human", ["has_variant_group"], True, False, None), "keep_held"),
            ("applied, confirmed", ("applied", "confirm_reading", [], True, False, None), "label_ai_reviewed"),
            ("applied, refer", ("applied", "refer_to_human", [], True, False, None), "revert_to_stored"),
            ("applied, keep stored", ("applied", "keep_stored", [], True, False, None), "revert_to_stored"),
            ("applied, correction, one run", ("applied", "confirm_with_correction", [], True, False, None), "revert_to_stored"),
            ("applied, correction, second run agrees", ("applied", "confirm_with_correction", [], True, False, True), "apply_correction"),
        ]
        for name, args, expected in table:
            with self.subTest(name):
                self.assertEqual(outcome(*args), expected)


class PacketsAndPilot(unittest.TestCase):
    def test_packets_carry_no_private_key(self):
        id_map = json.loads((PILOT / "private" / "id_map.json").read_text(encoding="utf-8"))["ids"]
        originals = set(id_map.values())
        for packet in packets():
            text = json.dumps(packet, ensure_ascii=False)
            self.assertFalse([o for o in originals if o in text], packet["packet_id"])
            for forbidden in ('"eligible"', '"judge', '"applies"', '"hadith_id"', "tranche-02", '"stored_chains"'):
                self.assertNotIn(forbidden, text)
            for item in packet["items"]:
                self.assertTrue(all(h["code"] in HOLDS for h in item["holds"]), item["holds"])
                self.assertLessEqual(len(packet["items"]), 10)

    def test_pilot_composition(self):
        with (PILOT / "private" / "key.tsv").open(encoding="utf-8", newline="") as handle:
            key = list(csv.DictReader(handle, delimiter="\t"))
        sets = {name: sum(1 for r in key if r["set"] == name) for name in {r["set"] for r in key}}
        self.assertEqual(sum(1 for r in key if "shape_hold" in r["set"]), 21)
        self.assertEqual(sum(1 for r in key if "variant_hold" in r["set"]), 30)
        self.assertEqual(sets.get("eligible_sample"), 30)
        self.assertEqual(len(key), sum(len(p["items"]) for p in packets()))

    def test_scorer_counts_a_perfect_and_a_rubber_stamp_reviewer(self):
        """A reviewer that rejects exactly the judge-wrong readings catches all of them; one that confirms everything catches none."""
        with (PILOT / "private" / "key.tsv").open(encoding="utf-8", newline="") as handle:
            key = {row["opaque"]: row for row in csv.DictReader(handle, delimiter="\t")}
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            shutil.copytree(PILOT / "packets", base / "packets")
            shutil.copytree(PILOT / "private", base / "private")
            results = {}
            for name, wrong_decision in (("perfect", "keep_stored"), ("stamp", "confirm_reading")):
                out = base / "outputs" / f"pass-{1 if name == 'perfect' else 2}"
                out.mkdir(parents=True)
                for packet in packets():
                    reviews = []
                    for item in packet["items"]:
                        judged = score_reviewer.judge_class(key[item["id"]])
                        decision = wrong_decision if judged == "wrong" else "confirm_reading"
                        if decision == "confirm_reading" and not item["readers_agree"]:
                            decision = "prefer_reader_a" if item["readers"]["A"]["valid"] else "prefer_reader_b"
                        reviews.append(review_for(item, decision))
                    (out / f"packet-{packet['packet_id'][-2:]}.output.json").write_text(json.dumps({"format": "shura-chain-review-output/1", "specialist_id": "chain-reviewer",
                        "prompt_version": "1.0.0", "packet_id": packet["packet_id"], "reviews": reviews}, ensure_ascii=False), encoding="utf-8")
                results[name] = score_reviewer.score(base, 1 if name == "perfect" else 2)
        perfect, stamp = results["perfect"], results["stamp"]
        self.assertEqual(perfect["invalid_outputs"], [])
        self.assertGreater(perfect["judge_wrong"]["n"], 0)
        self.assertEqual(perfect["judge_wrong"]["caught (not confirmed)"], perfect["judge_wrong"]["n"])
        self.assertEqual(stamp["judge_wrong"]["caught (not confirmed)"], 0)
        self.assertEqual(perfect["agreement_with_judge"], 1.0)


if __name__ == "__main__":
    unittest.main()
