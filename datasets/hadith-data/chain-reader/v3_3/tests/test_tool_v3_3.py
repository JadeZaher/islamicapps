"""v3.3 tool tests. Flows: the judges' real cases (tranche 02 out-of-sample verdicts, tranche 01 and batch 001) through validate, expand, agree and the v3.3 holds on the real pass outputs, each
change with the readings it must catch (judged wrong) and the readings it must spare (judged right); table-driven units for the boundaries. Real-data tests skip when a tranche is absent.

    python -B -X utf8 -m unittest discover -s v3_3/tests -p "test_*.py"        (from chain-reader/)
"""

from __future__ import annotations

import csv
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
V33 = HERE.parent
ROOT = V33.parent
for path in (str(ROOT), str(ROOT / "v3_2"), str(V33)):
    sys.path.insert(0, path)

import holds_v3_3 as holds  # noqa: E402
import triage_v3_3 as triage_module  # noqa: E402

N = "narrator"
TAB = chr(9)
T01, T02 = ROOT / "tranches" / "tranche-01", ROOT / "tranches" / "tranche-02"
T02_ANALYSIS = T02 / "judge-v3_2" / "analysis"


def link(surface, kind=N, start=None, end=None):
    return {"surface": surface, "kind": kind, "start": start, "end": end}


def route(*surfaces, group=0, tail_kind=N):
    """A route of narrators (the compiler head is not given: judged_links drops it anyway); positions are the order."""
    links = [link(s, N, i * 10, i * 10 + 5) for i, s in enumerate(surfaces)]
    if tail_kind != N:
        links[-1]["kind"] = tail_kind
    return {"links": links, "variant": False, "group": group}


class MutabaaUnits(unittest.TestCase):
    MARKED = ["تابعه قتيبة حدثنا العنقزي عن حنظلة", "حدثنا فلان. وتابعه ابن أبي الزناد عن أبيه", "وقد تابعه عبد الله بن صالح", "تَابَعَهُ عَبْدُ الرَّزَّاقِ عَنْ مَعْمَرٍ", "تابعها أحمد", "وقد تابع ابن جريج على ذلك ابن إسحاق", "وتابع يونس على قوله"]
    NOT_MARKED = ["صادق بار راشد تابع للحق ثم توفي", "اللهم اجعلني تابعا لصالحي من مضى", "ومن كره بقلبه فقد سلم ولكن من رضي وتابع فقيل يا رسول الله", "ثبتنا على متابعته", "من تابع هؤلاء الخمس", "في الأرض تتابع الأمطار"]

    def test_the_marker_forms(self):
        for text in self.MARKED:
            with self.subTest(text=text):
                self.assertIsNotNone(holds.mutabaa_marker(text))
        for text in self.NOT_MARKED:
            with self.subTest(text=text):
                self.assertIsNone(holds.mutabaa_marker(text))

    def test_the_hold_needs_more_than_one_route(self):
        text = "حدثنا أحمد عن زيد. تابعه قتيبة عن عمرو"
        one = {"routes": [route("أحمد", "زيد")], "matn_start": 10}
        two = {"routes": [route("أحمد", "زيد"), route("قتيبة", "عمرو")], "matn_start": 10}
        output = {"status": "read", "needs_ruling": False}
        self.assertNotIn("mutabaa_marker", [h["code"] for h in holds.compute_holds(one, output, text, None)])
        self.assertIn("mutabaa_marker", [h["code"] for h in holds.compute_holds(two, output, text, None)])


class RouteShapeUnits(unittest.TestCase):
    def test_route_ends_inside_another_route(self):
        wrong = [route("أ", "ب", "ج", "د"), route("هـ", "ج")]                     # route two stops at ج, which stands inside route one: the tail «د» was dropped (facedc, 181bd0)
        right_same_end = [route("أ", "ب", "ج", "د"), route("هـ", "د")]             # both reach د: two isnads of one saying
        right_disjoint = [route("أ", "ب"), route("ج", "د")]
        back_reference = [route("أ", "ب", "ج", "د"), route("هـ", "ج", tail_kind="back_reference")]      # «عن سهيل، بهذا الإسناد» states its tail (8b0565)
        short_form = [route("أ", "هشام بن عروة", "د"), route("ب", "هشام")]        # d02f9f: «هشام» / «هشام بن عروة»
        same_end_short_form = [route("أ", "عبد الله بن مرة", "عبد الله"), route("ب", "عبد الله")]    # a2c20f: every route ends at «عبد الله»: no tail missing
        self.assertIsNotNone(holds.route_ends_inside_another_route(wrong))
        self.assertIsNone(holds.route_ends_inside_another_route(right_same_end))
        self.assertIsNone(holds.route_ends_inside_another_route(right_disjoint))
        self.assertIsNone(holds.route_ends_inside_another_route(back_reference))
        self.assertIsNotNone(holds.route_ends_inside_another_route(short_form))
        self.assertIsNone(holds.route_ends_inside_another_route(same_end_short_form))

    def test_half_route_needs_a_different_last_link(self):
        long_route = route("أ", "ب", "ج", "د")
        self.assertIsNotNone(holds.short_route_detail([long_route, route("هـ", "ز")]))        # 2 of 4, ends elsewhere: a tail is missing (03f4b1, 80403f)
        self.assertIsNone(holds.short_route_detail([long_route, route("هـ", "د")]))           # 2 of 4 but both end at د: 1552aa
        self.assertIsNone(holds.short_route_detail([long_route, route("هـ", "ب", "ج")]))       # 3 of 4: not short
        self.assertIsNone(holds.short_route_detail([route("أ", "ب", "ج"), route("هـ")]))       # longest has fewer than 4
        two_longest = [long_route, route("و", "ز", "ح", "ط"), route("هـ", "د")]                # ends where ONE of the two longest ends is still the same man
        self.assertIsNone(holds.short_route_detail(two_longest))
        self.assertIsNotNone(holds.short_route_detail([long_route, route("و", "ز", "ح", "ط"), route("هـ", "ك")]))

    @staticmethod
    def previous(*entries):
        return [{"ref": f"prev{i + 1}", "number": number, "has_written_chain": written, "chain_text": chain} for i, (number, written, chain) in enumerate(entries)]

    def _far(self, previous):
        reading_routes = [{"links": [{"surface": "علي بن أبي طالب", "kind": "inherited", "from": "prev%d" % len(previous), "start": None, "end": None}], "variant": False}]
        return holds.inherited_from_far_report(reading_routes, {"previous_reports": previous}, "222 - بهذا الإسناد قال")

    def test_inherited_distance_alone_does_not_hold_when_every_report_between_is_a_pass_through(self):
        passes = [("221", False, "221 - وبإسناده"), ("220", False, "220 - وبإسناده"), ("219", False, "219 - وبهذا الإسناد"), ("218", False, "218 - وبإسناده"),
                  ("217", False, "217 - وبإسناده"), ("216", False, "216 - وبإسناده"), ("215", False, "215 - وبإسناده")]
        source = ("214", True, "214 - حدثنا محمد بن عمر قال حدثني أبو محمد")
        self.assertIsNone(self._far(self.previous(*passes, source)))                                                # 5505a6
        own_chain = list(passes)
        own_chain[3] = ("218", True, "218 - حدثنا أحمد بن محمد عن أبيه")
        self.assertIsNotNone(self._far(self.previous(*own_chain, source)))                                         # an intermediate writes its own chain
        names_speaker = list(passes)
        names_speaker[2] = ("219", False, "219 - قال الصادق عليه السلام")
        self.assertIsNotNone(self._far(self.previous(*names_speaker, source)))                                      # an intermediate that is not a back reference
        missing = passes[:2] + passes[3:]                                                                           # #219 is not in the packet: unknown, so the hold stays
        self.assertIsNotNone(self._far(self.previous(*missing, source)))
        near = self.previous(("221", False, "221 - وبإسناده"), ("220", True, "220 - حدثنا X"))
        self.assertIsNone(self._far(near))                                                                         # within three: never held (unchanged)

    def test_faqih_route_statement_pattern(self):
        faqih = {"work": {"key": "imami:man-la-yahduruhu-al-faqih", "tradition": "imami"}}
        for text in ("و ما كان فيه عن محمّد بن سنان فقد رويته عن محمّد بن عليّ ماجيلويه- رضي اللّه عنه- عن عمّه", "و كلّ ما كان في هذا الكتاب عن عليّ بن جعفر فقد رويته عن أبي- رضي اللّه عنه- عن محمّد بن يحيى",
                     "وما كان فيه عن يعقوب بن عثيم‌ فقد رويته عن محمّد بن موسى"):
            with self.subTest(text=text):
                self.assertIsNotNone(holds.faqih_route_statement(text, faqih))
                self.assertIsNone(holds.faqih_route_statement(text, {"work": {"key": "sunni:muslim", "tradition": "sunni"}}))     # Imami works only
        for text in ("حدثنا محمد بن الحسن عن أبيه عن الصادق عليه السلام قال: ما كان فيه خير فقد رويته", "و روى الحلبي عن أبي عبد الله عليه السلام قال: ما كان فيه من شيء"):
            with self.subTest(text=text):
                self.assertIsNone(holds.faqih_route_statement(text, faqih))


@unittest.skipUnless((T02 / "outputs" / "pass-a").is_dir() and (T02_ANALYSIS / "sample_verdicts.tsv").is_file(), "tranche 02 is not in this checkout")
class Tranche02RealCases(unittest.TestCase):
    """The out-of-sample judgement of tranche 02, case by case (README of its judge, sections 4, 5, 9)."""

    @classmethod
    def setUpClass(cls):
        cls.packets = triage_module.load_packets(T02 / "packets")
        with (T02_ANALYSIS / "sample_verdicts.tsv").open(encoding="utf-8") as handle:
            cls.verdicts = {row["id"]: row["reader"] for row in csv.DictReader(handle, delimiter="\t")}
        with (T02_ANALYSIS / "hold_verdicts.tsv").open(encoding="utf-8") as handle:
            cls.verdicts.update({row["id"]: row["reader"] for row in csv.DictReader(handle, delimiter="\t")})
        cls.cache: dict = {}

    @classmethod
    def row(cls, short: str, **flags) -> dict:
        key = (short, tuple(sorted(flags.items())))
        if key not in cls.cache:
            report_id = "t02-" + short
            cls.cache[key] = triage_module.triage({report_id: cls.packets[report_id]}, T02 / "outputs" / "pass-a", T02 / "outputs" / "pass-b", None, **flags)[0]
        return cls.cache[key]

    def test_mutabaa_marker_catches_the_two_eligible_wrong_readings(self):
        for short in ("1061e3", "cf6189"):                                 # both judged wrong (cf6189 by the judge's scan), both eligible under v3.2
            with self.subTest(short=short):
                self.assertIn("mutabaa_marker", self.row(short)["holds"])
                self.assertFalse(self.row(short)["eligible"])
        self.assertEqual(self.verdicts["t02-1061e3"], "W")

    def test_route_ends_inside_another_route_catches_wrong_and_spares_the_old_hold_s_two_right_readings(self):
        for short in ("facedc", "181bd0", "b88276", "30b092", "d02f9f"):
            with self.subTest(short=short):
                self.assertIn("route_ends_inside_another_route", self.row(short)["holds"])
        for short in ("89130e", "8b0565"):                                   # judged right; the broad old hold cost them
            with self.subTest(short=short):
                self.assertEqual(self.verdicts["t02-" + short], "R")
                self.assertNotIn("route_ends_inside_another_route", self.row(short)["holds"])
                self.assertNotIn("routes_end_at_different_links", self.row(short)["holds"])
        self.assertTrue(self.row("89130e")["eligible"])                      # 8b0565 stays held by back_reference_without_previous_report: the packet carried no previous report

    def test_half_route_keeps_the_eight_wrong_and_releases_1552aa(self):
        for short in ("dee88c", "56b32a", "03f4b1", "0aec9d", "80403f", "facedc", "181bd0", "b88276"):
            with self.subTest(short=short):
                self.assertEqual(self.verdicts["t02-" + short], "W")
                self.assertIn("route_at_most_half_the_longest", self.row(short)["holds"])
        self.assertEqual(self.verdicts["t02-1552aa"], "R")
        self.assertTrue(self.row("1552aa")["eligible"])

    def test_inheritance_through_pass_through_reports_is_eligible(self):
        self.assertEqual(self.verdicts["t02-5505a6"], "R")
        self.assertTrue(self.row("5505a6")["eligible"])

    def test_the_variant_hold_stays_unless_released_explicitly(self):
        for short in ("a2d173", "0d88a6", "3efbb5"):
            with self.subTest(short=short):
                self.assertIn("has_variant_group", self.row(short)["holds"])
                carried = self.row(short, variant_notes_supported=True)
                self.assertIn("has_variant_group", carried["holds"])            # carrying the notes releases nothing
                self.assertEqual(carried["suppressed"], [])
                self.assertFalse(carried["eligible"])
        released = self.row("a2d173", variant_notes_supported=True, release_variant_readings=True)
        self.assertEqual(released["suppressed"], ["has_variant_group"])
        self.assertNotIn("has_variant_group", released["holds"])
        with self.assertRaises(ValueError):
            triage_module.triage({"t02-a2d173": self.packets["t02-a2d173"]}, T02 / "outputs" / "pass-a", T02 / "outputs" / "pass-b", None, release_variant_readings=True)

    def test_faqih_route_statements_are_tagged_and_held_until_the_owner_rules(self):
        statements = ["0bcea2", "1531a8", "397ef7", "46c4c6", "94355c", "beb57a"]       # the six eligible readings of the judge's census, all judged right
        for short in statements:
            with self.subTest(short=short):
                self.assertEqual(self.verdicts["t02-" + short], "R")
                row = self.row(short)
                self.assertIn("faqih_route_statement", row["tags"])
                self.assertIn("needs_ruling_faqih_route_statement", row["holds"])
                self.assertFalse(row["eligible"])
        self.assertEqual(self.row("0a8f48")["tags"], ["faqih_route_statement"])         # the other four statements are tagged too
        self.assertEqual(self.row("00cfb3")["tags"], [])                                 # an ordinary Sunni chain is not

    def test_judged_right_readings_lost_are_only_the_faqih_statements(self):
        """Every judged-right sampled reading of tranche 02 that is not eligible under v3.3 is held by the faqih statement hold (what the owner's ruling releases) or was held before."""
        with (T02_ANALYSIS / "sample_verdicts.tsv").open(encoding="utf-8") as handle:
            sample = [row["id"][4:] for row in csv.DictReader(handle, delimiter=TAB) if row["reader"] in ("R", "RO")]
        self.assertGreater(len(sample), 200)
        lost = [short for short in sample if not self.row(short)["eligible"]]
        self.assertEqual(sorted(lost), sorted(["0bcea2", "1531a8", "397ef7", "46c4c6", "94355c", "beb57a"]))


@unittest.skipUnless((T01 / "outputs" / "pass-a").is_dir(), "tranche 01 is not in this checkout")
class Tranche01RealCases(unittest.TestCase):
    """Tranche 01 under v3.3: the narrowed holds must not reopen what the v3.2 tests pin, and b36519 must still be held."""

    @classmethod
    def setUpClass(cls):
        cls.packets = triage_module.load_packets(T01 / "packets")
        cls.cache: dict = {}

    def row(self, short):
        if short not in self.cache:
            self.cache[short] = triage_module.triage({"t01-" + short: self.packets["t01-" + short]}, T01 / "outputs" / "pass-a", T01 / "outputs" / "pass-b", None)[0]
        return self.cache[short]

    def test_far_inheritance_with_unknown_reports_between_is_still_held(self):
        self.assertIn("inherited_from_far_report", self.row("b36519")["holds"])      # #1067-#1070 are not in the packet: unknown, not pass-through

    def test_the_four_right_two_isnad_readings_stay_eligible(self):
        for short in ("dd8d9b", "0c66ee", "610c03", "31cf87"):                       # judged right; second isnads after the saying, abbreviated or ending in a back reference
            with self.subTest(short=short):
                self.assertTrue(self.row(short)["eligible"], self.row(short)["holds"])

    def test_the_v3_2_wrong_cases_that_are_still_held(self):
        for short, code in (("05c2d0", "first_links_split_by_comma"), ("eb2b15", "semicolon_in_multi_route_isnad"), ("30fa50", "has_variant_group"), ("07d717", "imami_single_narrator_without_source")):
            with self.subTest(short=short):
                self.assertIn(code, self.row(short)["holds"])

    def test_the_narrowing_releases_6d7565_a_judged_wrong_reading(self):
        """Pinned on purpose: the narrowing the owner asked for (a shorter route held only when its last link differs) lets 6d7565 through (judged wrong, in-sample). README section 4."""
        self.assertTrue(self.row("6d7565")["eligible"])


if __name__ == "__main__":
    unittest.main()
