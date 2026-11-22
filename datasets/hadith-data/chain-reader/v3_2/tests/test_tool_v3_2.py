"""v3.2 tool tests. Flows: the judge's real tranche-01 cases (right and wrong) driven through validate, expand, agree and hold on the real pass outputs; table-driven folds with negatives; the
openers. Real-data tests read tranches/tranche-01 (packets, outputs, judge verdicts) and skip if it is absent.

    python -B -X utf8 -m unittest discover -s v3_2/tests -p "test_*.py"        (from chain-reader/)
"""

from __future__ import annotations

import copy
import csv
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
V32 = HERE.parent
ROOT = V32.parent
for path in (str(ROOT), str(V32)):
    sys.path.insert(0, path)

import holds_v3_2 as holds  # noqa: E402
import triage_v3_2 as triage_module  # noqa: E402
from expand_v3_2 import canonical, expand, readings_agree, variant_keys  # noqa: E402
from norm_v3_2 import link_key  # noqa: E402
from validate_v3_2 import validate_v3_2, with_default_fixes  # noqa: E402

TRANCHE = ROOT / "tranches" / "tranche-01"
VERDICTS = TRANCHE / "judge" / "analysis" / "sample_verdicts.tsv"
N, U = "narrator", "unnamed"


def lv(*names):
    return [[{"surface": s, "kind": N} for s in (n if isinstance(n, list) else [n])] for n in names]


def output(groups, report_id="x", **extra):
    return {"id": report_id, "status": "read", "groups": groups, "shared_tail": None, "needs_ruling": False, "notes": [], "fixes": [], **extra}


class FoldTests(unittest.TestCase):
    """Every fold of norm_v3_2 with an example, and what it must NOT fold (FOLDS.md)."""

    EQUAL = [
        ("أبا النضر، مولى عمر بن عبيد الله", "أبا النضر"),                 # 084141: a patron appended to the name
        ("عكرمة مولى ابن عباس", "عكرمة"),                                   # 58d272
        ("بعض بني أبي رافع، مولى النبي", "بعض بني أبي رافع"),
        ("أم المؤمنين، عائشة", "عائشة"),                                      # 167c0f: a title before the name
        ("أمير المؤمنين علي بن أبي طالب", "علي بن أبي طالب"),                # 6a2991
        ("أم محمد امرأة أبيه", "أم محمد"),                                   # c36297: a relation appended
        ("أبا عمر صاحب أبي العباس ثعلب", "أبا عمر"),                         # d98ce4: a companion appended to a kunya
    ]
    DIFFERENT = [
        ("سعيد مولى عمر", "خالد مولى عمر"),                                   # same patron, two men: the patron is cut, the name is not
        ("أم المؤمنين", "عائشة"),                                             # a title alone is not stripped to nothing
        ("أمير المؤمنين", "علي"),
        ("علي صاحب الدار", "علي"),                                            # «صاحب» is cut only after a kunya
        ("أم سلمة", "أم عطية"),
        ("مولى عمر بن عبيد الله", "عمر بن عبيد الله"),                       # a name that STARTS with «مولى» keeps it
    ]

    def test_equal_pairs(self):
        for first, second in self.EQUAL:
            with self.subTest(first=first):
                self.assertEqual(link_key(first), link_key(second))

    def test_different_men_stay_different(self):
        for first, second in self.DIFFERENT:
            with self.subTest(first=first, second=second):
                self.assertNotEqual(link_key(first), link_key(second))
        self.assertTrue(link_key("أم المؤمنين"))                              # never empty

    def test_restated_short_form_needs_the_same_slot_and_neighbours(self):
        def reading(*routes):
            return {"routes": [{"links": [{"surface": s, "start": i, "end": i + 1, "kind": N} for i, s in enumerate(route)], "variant": False} for route in routes]}
        fuller = reading(["ابن وهب", "مخرمة بن بكير", "نافع"], ["هارون", "ابن وهب", "مخرمة بن بكير", "نافع"])
        shorter = reading(["ابن وهب", "مخرمة", "نافع"], ["هارون", "ابن وهب", "مخرمة بن بكير", "نافع"])
        self.assertTrue(readings_agree(fuller, shorter))                       # 59eb95
        self.assertFalse(readings_agree(fuller, reading(["ابن وهب", "مخرمة", "سالم"], ["هارون", "ابن وهب", "مخرمة بن بكير", "نافع"])))     # a neighbour differs
        self.assertFalse(readings_agree(reading(["محمد بن علي", "نافع"]), reading(["محمد بن سيرين", "نافع"])))                              # not a prefix
        self.assertFalse(readings_agree(reading(["محمد بن علي", "نافع"]), reading(["محمد", "سالم"])))
        self.assertFalse(readings_agree(reading(["أ", "ب بن ج", "د بن ه"]), reading(["أ", "ب", "د"])))                                      # two slots differ


class VariantTests(unittest.TestCase):
    TEXT = "حدثنا أبو بكر، حدثنا وكيع، عن سفيان، عن عمرو، عن جابر ‏.‏ بمثل حديث سليمان بن بلال ‏.‏"

    def _read(self, groups):
        reading, errors = expand(output(groups), self.TEXT)
        self.assertEqual(errors, [])
        return reading

    def test_variant_group_is_a_remark_not_a_route(self):
        reading = self._read([{"levels": lv("أبو بكر", "وكيع", "سفيان", "عمرو", "جابر")}, {"levels": lv("سليمان بن بلال"), "variant": True}])
        self.assertEqual(len(reading["routes"]), 1)
        self.assertFalse(any(r["variant"] for r in reading["routes"]))
        self.assertEqual([r["surfaces"] for r in reading["variant_remarks"]], [[["سليمان بن بلال"]]])
        self.assertIn("بمثل حديث", reading["variant_remarks"][0]["quote"])

    def test_agreement_ignores_the_remark_and_the_hold_follows_the_flag(self):
        with_remark = self._read([{"levels": lv("أبو بكر", "وكيع", "سفيان", "عمرو", "جابر")}, {"levels": lv("سليمان بن بلال"), "variant": True}])
        without = self._read([{"levels": lv("أبو بكر", "وكيع", "سفيان", "عمرو", "جابر")}])
        self.assertTrue(readings_agree(with_remark, without))
        self.assertNotEqual(variant_keys(with_remark), variant_keys(without))      # compared separately, never blocking
        codes = [h["code"] for h in holds.compute_holds(with_remark, output([]), self.TEXT, None)]
        self.assertIn("has_variant_group", codes)
        self.assertNotIn("has_variant_group", [h["code"] for h in holds.compute_holds(without, output([]), self.TEXT, None)])

    def test_a_reading_of_only_variant_groups_is_never_an_empty_reading(self):
        reading = self._read([{"levels": lv("سليمان بن بلال"), "variant": True}])
        self.assertEqual(reading["routes"], [])
        self.assertTrue(reading["only_variant_groups"])
        self.assertIn("variant_only_reading", [h["code"] for h in holds.compute_holds(reading, output([]), self.TEXT, None)])


class RealCases(unittest.TestCase):
    """The judge's tranche-01 cases through the whole tool (validate, expand, agree, hold) on the real outputs."""

    @classmethod
    def setUpClass(cls):
        if not (TRANCHE / "outputs" / "pass-a").is_dir() or not VERDICTS.is_file():
            raise unittest.SkipTest("tranche 01 is not in this checkout")
        cls.packets = triage_module.load_packets(TRANCHE / "packets")
        with VERDICTS.open(encoding="utf-8") as handle:
            cls.verdicts = {row["id"]: row for row in csv.DictReader(handle, delimiter="\t")}
        cls._cache: dict = {}

    @classmethod
    def row(cls, short: str, variant_notes_supported: bool = False) -> dict:
        key = (short, variant_notes_supported)
        if key not in cls._cache:
            report_id = "t01-" + short
            cls._cache[key] = triage_module.triage({report_id: cls.packets[report_id]}, TRANCHE / "outputs" / "pass-a", TRANCHE / "outputs" / "pass-b", None, variant_notes_supported)[0]
        return cls._cache[key]

    def assertHeld(self, short, code):
        self.assertIn(code, self.row(short)["holds"], short)

    def assertNotHeld(self, short, code):
        self.assertNotIn(code, self.row(short)["holds"], short)

    # ---- the three narrow shape holds, wrong and right ----
    SHAPE = {"route_at_most_half_the_longest": (["6d7565"], ["dd8d9b", "0c66ee", "610c03", "31cf87"]),          # a dropped shared head (right: the four the broad rule wrongly caught)
             "first_links_split_by_comma": (["05c2d0"], ["dd8d9b", "0c66ee", "610c03", "31cf87"]),               # a kunya and a name read as two men
             "semicolon_in_multi_route_isnad": (["eb2b15"], ["dd8d9b", "0c66ee", "610c03", "31cf87"])}          # co-transmitters grouped after «؛»

    def test_shape_holds_catch_the_judged_wrong_and_spare_the_judged_right(self):
        for code, (wrong, right) in self.SHAPE.items():
            for short in wrong:
                with self.subTest(code=code, wrong=short):
                    self.assertEqual(self.verdicts["t01-" + short]["reader"], "W")
                    self.assertHeld(short, code)
            for short in right:
                with self.subTest(code=code, right=short):
                    self.assertIn(self.verdicts["t01-" + short]["reader"], ("R", "RO"))
                    self.assertNotHeld(short, code)

    def test_the_broad_routes_end_hold_is_not_reinstated(self):
        for short in ("dd8d9b", "0c66ee", "610c03", "31cf87"):                  # v3.1's exemptions let these four through; they must stay eligible
            with self.subTest(short=short):
                self.assertTrue(self.row(short)["eligible"], self.row(short)["holds"])

    # ---- Imami holds ----
    def test_imami_holds(self):
        self.assertHeld("07d717", "imami_single_narrator_without_source")      # «و قال الحلبي: و سألته» (undecided)
        self.assertHeld("f14c39", "imami_single_narrator_without_source")      # «في رواية جميل أنه قال»
        self.assertHeld("b36519", "inherited_from_far_report")                 # the Imam of a report five back
        self.assertNotHeld("80a548", "inherited_from_far_report")              # prev2 of the packet but one report back: fine
        self.assertHeld("2973ea", "empty_reading_unsettled_opening")           # «و مع قوله عليه السلام»
        self.assertHeld("cf634a", "needs_ruling_prophet_no_transmitter")       # the Prophet speaks, no transmitter

    def test_every_judged_right_reading_stays_eligible(self):
        """In-sample: no judged-right eligible reading of tranche 01 is held by a v3.2 hold (v3_2/HOLDS.md)."""
        draw = json.loads((TRANCHE / "judge" / "analysis" / "draw_extension.json").read_text(encoding="utf-8"))
        sampled = set(draw["base"]) | {i for ids in draw["extension"].values() for i in ids}
        right = [i[4:] for i, v in self.verdicts.items() if i in sampled and v["reader"] in ("R", "RO")]         # every judged-right reading was eligible under v3.1
        self.assertGreater(len(right), 150)
        self.assertEqual([short for short in right if not self.row(short)["eligible"]], [])

    def test_the_variant_readings_are_held_until_notes_are_supported(self):
        for short in ("30fa50", "c93705", "e3f7d5"):
            with self.subTest(short=short):
                self.assertHeld(short, "has_variant_group")
                self.assertFalse(self.row(short)["eligible"])
                lifted = self.row(short, variant_notes_supported=True)
                self.assertEqual(lifted["suppressed"], ["has_variant_group"])
                self.assertNotIn("has_variant_group", lifted["holds"])

    # ---- validity and agreement ----
    def test_equivalent_readings_now_agree(self):
        for short in ("084141", "167c0f", "2a00dd", "352803", "561fd8", "58d272", "59eb95", "6a2991", "a9947f", "c36297", "d98ce4"):   # the 11 of the judge's 40
            with self.subTest(short=short):
                self.assertTrue(self.row(short)["agree"])

    def test_different_readings_still_differ(self):
        for short in ("26bb55", "2aea01", "306ccd", "3b10bc", "5dc04b", "75e2df", "881857", "cb56aa", "fb4b56"):                       # real differences, not spellings
            with self.subTest(short=short):
                self.assertFalse(self.row(short)["agree"])

    def test_bracketed_insertion_handled_differently_is_held_not_applied(self):
        row = self.row("54c186")
        self.assertTrue(row["agree"])
        self.assertIn("bracketed_insertion_differs", row["holds"])

    def test_missing_fixes_key_is_valid(self):
        packet = self.packets["t01-30fa50"]
        pass_output = json.loads((TRANCHE / "outputs" / "pass-a" / "t01-30fa50.json").read_text(encoding="utf-8"))
        stripped = {k: v for k, v in pass_output.items() if k != "fixes"}
        self.assertEqual(validate_v3_2(stripped, packet["text"], "t01-30fa50", packet["context"]), [])
        self.assertEqual(with_default_fixes(stripped)["fixes"], [])
        self.assertIn("fixes", with_default_fixes(stripped))
        self.assertTrue(validate_v3_2({**stripped, "extra": 1}, packet["text"], "t01-30fa50", packet["context"]))     # any other shape error still counts


class OpenerTests(unittest.TestCase):
    OPENINGS = [
        ("5719 - وَ مَعَ قَوْلِهِ عَلَيْهِ اَلسَّلاَمُ: «الإسلام يعلو»", "quoted_saying"),
        ("و مع قوله صلى الله عليه وآله: «x»", "quoted_saying"),
        ("و مع قوله تعالى: «x»", None),                                           # the Qur'an is no speaker
        ("وقال عليه السلام: «x»", "implicit_speaker"),
        ("و سأل علي بن جعفر أخاه موسى بن جعفر", "asker_named"),
    ]

    def test_openers(self):
        for text, expected in self.OPENINGS:
            with self.subTest(text=text):
                self.assertEqual(holds.opening_class(text), expected)

    def test_quoted_saying_opener_does_not_inherit(self):
        self.assertFalse(holds.inherits_from_previous("و مع قوله عليه السلام: «x»"))      # the packets carry no previous report for it: only an empty reading is held

    EMPTY = [
        ("و مع قوله عليه السلام: «الإسلام يعلو»", "unsettled_opening"),
        ("وقال صلى الله عليه وآله: لا تعضية في ميراث", "prophet_no_transmitter"),         # cf634a
        ("و نهى صلى الله عليه و آله عن السوم ما بين طلوع الفجر", "prophet_no_transmitter"),
        ("كما روي عن النبي صلى الله عليه وآله أنه قال: «x»", "prophet_no_transmitter"),
        ("5763 - اليد العليا خير من اليد السفلى", "applicable"),                          # a plain saying: still "no chain"
        ("فقصتها حفصة على النبي صلى الله عليه وسلم فقال", "applicable"),                  # the Prophet only in the scene
    ]

    def test_empty_reading_states(self):
        for text, expected in self.EMPTY:
            with self.subTest(text=text):
                self.assertEqual(holds.empty_reading_state(text)[0], expected)

    def test_the_prophet_rule_does_not_depend_on_the_work(self):
        for key in ("sunni:muslim", "imami:man-la-yahduruhu-al-faqih", "imami:maani-al-akhbar"):
            with self.subTest(key=key):
                found = [h["code"] for h in holds.compute_holds({"routes": [], "matn_start": 0}, {"status": "read", "needs_ruling": False}, "وقال صلى الله عليه وآله: لا تعضية في ميراث", {"work": {"key": key, "tradition": key.split(":")[0]}})]
                self.assertIn("needs_ruling_prophet_no_transmitter", found)


class ShapeHoldUnits(unittest.TestCase):
    """The shape holds on hand-made readings: the boundaries (half, four links, comma only, «و» between)."""

    @staticmethod
    def route(*surfaces, start=0, gap=3):
        links, cursor = [], start
        for surface in surfaces:
            links.append({"surface": surface, "start": cursor, "end": cursor + len(surface), "kind": N})
            cursor += len(surface) + gap
        return {"links": links, "variant": False}

    def test_half_the_longest(self):
        self.assertIsNotNone(holds.short_route_detail([self.route("a", "b", "c", "d"), self.route("a", "b")]))      # 2 of 4: at most half
        self.assertIsNone(holds.short_route_detail([self.route("a", "b", "c", "d"), self.route("a", "b", "c")]))    # 3 of 4: not
        self.assertIsNone(holds.short_route_detail([self.route("a", "b", "c"), self.route("a")]))                    # longest has fewer than 4
        self.assertIsNone(holds.short_route_detail([self.route("a", "b", "c", "d")]))                                # one route

    def test_first_links_split_by_comma(self):
        def routes_in(text):
            """Two routes `X ... Z` and `Y ... Z` whose offsets are found in the text."""
            def link(surface, after=0):
                start = text.index(surface, after)
                return {"surface": surface, "start": start, "end": start + len(surface), "kind": N}
            shared = link("ZZ")
            return [{"links": [link("XXXXX"), shared], "variant": False}, {"links": [link("YYYYY"), shared], "variant": False}]
        for text, expected in (("XXXXX، YYYYY ZZ", True), ("XXXXX ،YYYYY ZZ", True), ("XXXXX، وYYYYY ZZ", False), ("XXXXX YYYYY ZZ", False), ("XXXXX، قال YYYYY ZZ", False)):
            with self.subTest(text=text):
                self.assertEqual(holds.first_links_split_by_comma(routes_in(text), text) is not None, expected)


if __name__ == "__main__":
    unittest.main()
