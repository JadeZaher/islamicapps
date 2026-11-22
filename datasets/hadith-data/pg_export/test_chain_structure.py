"""Chain structure gate (chain_structure.py): the detectors on the re-checks' real rows, and the pure rules table-driven."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent.parent))

import chain_structure as cs  # noqa: E402

FIXTURES = HERE.parent / "chain-audit" / "structure-gate" / "fixtures.json"
ROUND_FIVE_FIXTURES = HERE.parent / "chain-audit" / "round5" / "fixtures.json"


def report_of(case: dict) -> cs.ReportChains:
    return cs.ReportChains(case["text"], case["chains"], case["tradition"], case["inherited"], case["thaqalayn"],
                           case["work"], case["routes_from_text"])


class DetectorsOnTheRechecksRows(unittest.TestCase):
    """Rows the round-3 re-check read: each defect is flagged with the reason that names it; correct rows stay checked."""

    @classmethod
    def setUpClass(cls):
        cls.fixtures = json.loads(FIXTURES.read_text(encoding="utf-8"))

    def test_each_read_row(self):
        for case in self.fixtures["cases"]:
            with self.subTest(case["hadith_id"], why=case["why"]):
                reasons = cs.assess(report_of(case))
                chosen = range(len(reasons)) if case["chain"] is None else [case["chain"]]
                for index in chosen:
                    if case["reason"] is None:
                        self.assertEqual(reasons[index], [], f"chain {index}")
                    else:
                        self.assertIn(case["reason"], reasons[index], f"chain {index}")

    def test_retired_reports(self):
        for case in self.fixtures["retired"]:
            with self.subTest(case["hadith_id"], why=case["why"]):
                self.assertEqual(cs.retire_reason(case["work"], case["tradition"], case["report_text"],
                                                  case["routes_from_text"]), case["reason"])

    def test_every_reason_has_reader_wording(self):
        self.assertTrue(cs.GATE_REASONS <= set(cs.REASON_TEXT))


class RoundFiveRecalibration(unittest.TestCase):
    """Rows round 4 read: shapes the recalibrated gate must now flag, and correct chains it must no longer withhold."""

    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads(ROUND_FIVE_FIXTURES.read_text(encoding="utf-8"))["cases"]

    def test_each_round_four_row(self):
        for case in self.cases:
            with self.subTest(case["hadith_id"], why=case["why"]):
                reasons = cs.assess(report_of(case))[case["chain"]]
                if "flag" in case:
                    self.assertIn(case["flag"], reasons)
                else:
                    self.assertNotIn(case["clear"], reasons)

    def test_not_a_name_shapes(self):
        for surface, kwargs, expected in [
            ("تابع/", {}, True), ("أبو الحسن القطان حدثناه خازم بن يحيى", {}, True),
            ("علي بن جعفر أخاه موسى بن جعفر", {}, True), ("الدال على الخير كفاعله", {"single_link": True}, True),
            ("الدال على الخير كفاعله", {"single_link": False}, False),       # a saying is only read as such when it is the whole chain
            ("سعيد يعني المقبري", {"routes_from_text": False}, False),         # Pure Canon: the source's own gloss
            ("سعيد يعني المقبري", {"routes_from_text": True}, True),           # a text-built chain with a gloss stays unchecked
            ("وبهذا الإسناد", {}, False), ("عمن حدثه", {}, False),            # label links, not names
            ("أبو الحسن القطان", {"single_link": True}, False),               # a kunya-led name has a nasab word
        ]:
            with self.subTest(surface, **kwargs):
                self.assertEqual(cs.not_a_name(surface, **kwargs), expected)

    def test_hearing_shapes_after_the_last_link(self):
        for tail, expected in [
            ("أنه سمع أسماء بنت أبي بكر تقول", True), ("أنه نظر إلى عبد الله بن عمر كيف يحكي", True),
            ("قال قرأت على عبد الله بن عمر", True), ("قالا نشهد على عائشة أنها قالت", True),
            ("قلت من حدثك قال ابن عباس", True), ("، قال عمرو بن دينار قال ابن عباس", True),
            ("قال سمعت رسول الله يقول", False), ("قال سمعت النبي", False),   # the Prophet is the end of the chain, not a lost link
        ]:
            with self.subTest(tail):
                chain = ["حدثنا مسدد", "يحيى"]
                text = "حدثنا مسدد، حدثنا يحيى، " + tail
                reasons = cs.assess(cs.ReportChains(text, [["مسدد", "يحيى"]], "Sunni"))[0]
                self.assertEqual("text_names_more_after" in reasons, expected, chain)

    def test_sibling_skips_link(self):
        self.assertEqual(cs.sibling_skips_link([["أ", "ب", "ج", "د"], ["أ", "ب", "د"]]), [True, True])
        self.assertEqual(cs.sibling_skips_link([["أ", "ب", "ج"], ["أ", "ب", "د"]]), [False, False])   # co-transmitters: same length
        self.assertEqual(cs.sibling_skips_link([["أ", "ب", "ج"], ["ب", "ج"]]), [False, False])         # a shared tail, not a skip
        self.assertEqual(cs.sibling_skips_link([["أ", "ب", "ج", "د"]]), [False])


class PureRules(unittest.TestCase):
    def test_not_a_name(self):
        for surface, expected in [
            ("الرجل يصلي قاعدا", True), ("ابن عمر نهى النبي", True), ("ت", True), ("3/45 الكافي", True),
            ("غير واحد - المعنى", True), ("عبد الرحمن بن أبي بكرة", False), ("أبي", False), ("غير واحد", False),
            ("بعض أصحابنا", False), ("محمد بن أحمد بن يحيى بن عمران الأشعري", False),
        ]:
            with self.subTest(surface):
                self.assertEqual(cs.not_a_name(surface), expected)

    def test_joined_names(self):
        for surface, expected in [("الحلبي و زرارة", True), ("زراره و حمران", True), ("أبي وأم عبد الملك", True),
                                  ("وكيع", False), ("عدة من أصحابنا", False), ("محمد بن مسلم", False)]:
            with self.subTest(surface):
                self.assertEqual(cs.joined_names(surface), expected)

    def test_duplicated_link(self):
        for left, right, expected in [
            ("إسماعيل بن جعفر", "إسماعيل", True), ("حماد", "حماد بن زيد", True), ("محمد بن رافع", "ابن رافع", True),
            ("سفيان", "سفيان بن عيينة", True),
            ("أحمد بن محمد", "أحمد بن محمد بن أبي نصر", False),        # two men in al-Kafi
            ("محمد بن الحسن", "محمد بن الحسن الصفار", False),          # al-Saduq's two shaykhs
            ("علي بن إبراهيم", "أبيه", False), ("عن أبيه", "أبيه", False),
        ]:
            with self.subTest(f"{left} > {right}"):
                self.assertEqual(cs.duplicated_link(left, right), expected)

    def test_report_level_shapes(self):
        long_route = ["أ بن ب", "ج بن د", "هـ بن و", "ز بن ح", "ط بن ي"]
        cases = [
            # (chains, text, tradition, expected per chain)
            ([long_route, ["ك بن ل"]], "", "Sunni", [[], ["short_beside_long"]]),
            ([["زيد", "عمرو"]], "حدثنا زيد عن عمرو ح وحدثنا بكر عن عمرو", "Sunni", [["unaccounted_route_marker"]]),
            ([["زيد", "عمرو", "بكر", "زيد"]], "", "Sunni", [["repeated_name"]]),
        ]
        for chains, text, tradition, expected in cases:
            with self.subTest(chains=chains):
                self.assertEqual(cs.assess(cs.ReportChains(text, chains, tradition)), expected)

    def test_many_routes_only_where_routes_are_read_from_the_text(self):
        chains = [["أ بن ب"], ["ج بن د"], ["هـ بن و"]]
        self.assertEqual(cs.assess(cs.ReportChains("", chains, "Sunni"))[0], ["many_routes"])
        self.assertEqual(cs.assess(cs.ReportChains("", chains, "Sunni", routes_from_text=False))[0], [])
        self.assertEqual(cs.assess(cs.ReportChains("", chains, "Imami"))[0], [])

    def test_text_between_links_reads_asides_and_co_transmitters_as_accounted(self):
        text = "حدثنا قتيبة بن سعيد، وبشر بن معاذ، قالا حدثنا أبو عوانة - يعني اليشكري - عن قتادة، عن أنس"
        chains = [["قتيبة بن سعيد", "أبو عوانة", "قتادة", "أنس"], ["بشر بن معاذ", "أبو عوانة", "قتادة", "أنس"]]
        self.assertEqual(cs.assess(cs.ReportChains(text, chains, "Sunni")), [[], []])
        lost = "حدثنا قتيبة، حدثنا ليث، عن نافع، عن رجل من أهل المدينة عن ابن عمر"
        self.assertEqual(cs.assess(cs.ReportChains(lost, [["قتيبة", "ليث", "نافع", "ابن عمر"]], "Sunni")),
                         [["text_between_links"]])


if __name__ == "__main__":
    unittest.main()
