"""Table-driven tests of the v2 tool chain: validate_v2, expand, holds, score_v2 (one accepted case per rule, one rejection per failure)."""
import copy
import sys
import unittest
from pathlib import Path

CONTEXT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CONTEXT))
sys.path.insert(0, str(CONTEXT.parent))
from expand import canonical, expand  # noqa: E402
from holds import compute_holds  # noqa: E402
from score_v2 import surface_in_text_with_attached_wa, to_v1_shape  # noqa: E402
from validate_v2 import validate_chain, validate_text  # noqa: E402
from norm import surface_in_text  # noqa: E402

TEXT = "6ـ عَلِيُّ بْنُ إِبْرَاهِيمَ وَمُحَمَّدُ بْنُ يَحْيَى عَنْ يُونُسَ قَالَ سَأَلْتُ أَبَا عَبْدِ اللَّهِ عَنْ كذا ثم قال يونس"
CONTEXT_BLOCK = {
    "work": {"tradition": "imami", "compiler": {"ar": "الكليني", "head_of_every_chain": True, "added_by_tool": True}},
    "previous_reports": [{"ref": "prev1", "chain_text": "5 - أحمد بن إدريس عن علي بن محمد عن الفضل", "text_head": "5 - أحمد بن إدريس عن علي بن محمد عن الفضل قال كذا"}],
    "source_claims": [{"source": "K6I", "sequence": ["علي بن إبراهيم القمي"]}],
}


def it(surface, kind="narrator", **extra):
    return dict({"surface": surface, "kind": kind}, **extra)


def reading(groups, tail=None, **over):
    base = {"id": "cr-1", "status": "read", "groups": [{"levels": g} for g in groups], "shared_tail": tail, "needs_ruling": False, "notes": [], "fixes": []}
    base.update(over)
    return base


GOOD = reading([[[it("علي بن إبراهيم"), it("محمد بن يحيى")], [it("يونس")], [it("أبا عبد الله", "imam_in_text")]]])


def fix(kind, evidence):
    return {"kind": kind, "reason": "r", "evidence": evidence, "confidence": "low"}


def with_(change):
    output = copy.deepcopy(GOOD)
    change(output)
    return output


CHAIN_CASES = [
    ("accepted: alternatives in a level, imam_in_text last", GOOD, None),
    ("surface not in the text", reading([[[it("زرارة")]]]), "surface_not_in_text"),
    ("order: a level that only occurs before the previous one", reading([[[it("يونس")], [it("علي بن إبراهيم")]]]), "order"),
    ("occurrence picks the second mention", reading([[[it("يونس", occurrence=2)]]]), None),
    ("occurrence that does not exist", reading([[[it("يونس", occurrence=3)]]]), "occurrence"),
    ("kind outside the reader vocabulary (the compiler is the tool's)", reading([[[it("الكليني", "compiler_head")]]]), "kind"),
    ("imam_in_text not last in its route", reading([[[it("أبا عبد الله", "imam_in_text")], [it("يونس", occurrence=2)]]]), "imam_in_text"),
    ("empty level", reading([[[it("يونس")], []]]), "shape"),
    ("inherited from a ref the context has", reading([[[it("أحمد بن إدريس", "inherited", **{"from": "prev1"})], [it("علي بن إبراهيم")]]]), None),
    ("inherited from an unknown ref", reading([[[it("أحمد بن إدريس", "inherited", **{"from": "prev9"})]]]), "inherited"),
    ("inherited words not in the cited report", reading([[[it("زرارة", "inherited", **{"from": "prev1"})]]]), "inherited"),
    ("status outside the vocabulary", with_(lambda o: o.update(status="maybe")), "status"),
    ("cannot_read without the packet flag", reading([], status="cannot_read_without_previous_report"), "status"),
    ("fix quote not in the text", with_(lambda o: o["fixes"].append(fix("text_garbled", [{"source": "text", "quote": "غير موجود"}]))), "evidence_quote"),
    ("fix quote found in the K6I item by its letters", with_(lambda o: o["fixes"].append(fix("chain_differs_from_source", [{"source": "text", "quote": "علي بن إبراهيم"}, {"source": "K6I", "quote": "علي بن ابراهيم القمي"}]))), None),
    ("online evidence needs a url", with_(lambda o: o["fixes"].append(fix("data_problem_other", [{"source": "online", "quote": "x"}]))), "evidence_online"),
    ("an old v1 key is rejected", with_(lambda o: o.update(matn_start=5)), "shape"),
]


class ChainValidation(unittest.TestCase):
    def test_cases(self):
        for name, output, expected in CHAIN_CASES:
            with self.subTest(name):
                errors = validate_chain(output, TEXT, "cr-1", CONTEXT_BLOCK)
                if expected is None:
                    self.assertEqual(errors, [])
                else:
                    self.assertTrue(any(e.startswith(expected) for e in errors), errors)

    def test_flagged_packet_must_not_get_a_short_chain(self):
        flagged = dict(CONTEXT_BLOCK, needs_previous_report=True)
        self.assertTrue(any(e.startswith("needs_previous_report") for e in validate_chain(GOOD, TEXT, "cr-1", flagged)))
        refused = reading([], status="cannot_read_without_previous_report")
        self.assertEqual(validate_chain(refused, TEXT, "cr-1", flagged), [])


class Expansion(unittest.TestCase):
    def test_levels_become_routes_with_offsets_and_matn_start(self):
        result, errors = expand(GOOD, TEXT, CONTEXT_BLOCK)
        self.assertEqual(errors, [])
        routes = [[l["surface"] for l in r["links"]] for r in result["routes"]]
        self.assertEqual(len(routes), 2)
        self.assertEqual(routes[0][0], "الكليني")                                  # the compiler head, added by the tool
        link = result["routes"][0]["links"][1]
        self.assertEqual(TEXT[link["start"]:link["end"]], link["surface"])         # surfaces keep the text's diacritics
        imam = result["routes"][0]["links"][-1]
        self.assertGreaterEqual(imam["start"], result["matn_start"])               # imam_in_text lies in the saying; it does not move matn_start

    def test_compiler_written_in_the_text_is_not_added_again(self):
        text = "الكليني عن يونس قال كذا"
        result, _ = expand(reading([[[it("الكليني")], [it("يونس")]]]), text, CONTEXT_BLOCK)
        self.assertEqual([l["kind"] for l in result["routes"][0]["links"]], ["narrator", "narrator"])

    def test_shared_tail_and_equivalent_readings_compare_equal(self):
        text = "حدثنا أ، حدثنا ب، قالا حدثنا ج، عن د"
        levels = reading([[[it("أ"), it("ب")], [it("ج")], [it("د")]]])
        exploded = reading([[[it("أ")]], [[it("ب")]]], [[it("ج")], [it("د")]])
        a, b = expand(levels, text)[0], expand(exploded, text)[0]
        self.assertEqual(canonical(a), canonical(b))
        self.assertEqual([r["shared_tail_from"] for r in b["routes"]], [1, 1])
        self.assertEqual(b["routes"][0]["links"][1]["start"], b["routes"][1]["links"][1]["start"])   # the tail is written once

    def test_expansion_limit(self):
        text = " ".join(f"ن{i}" for i in range(60))
        wide = reading([[[it(f"ن{i}") for i in range(0, 20)], [it(f"ن{i}") for i in range(20, 40)], [it(f"ن{i}") for i in range(40, 60)]]])
        self.assertTrue(any(e.startswith("too_many_routes") for e in expand(wide, text)[1]))


class Holds(unittest.TestCase):
    def codes(self, output, text=TEXT, context=CONTEXT_BLOCK, stored=None):
        result, _ = expand(output, text, context)
        return [h["code"] for h in compute_holds(result, output, text, context, stored)]

    def test_each_hold(self):
        self.assertEqual(self.codes(GOOD), [])
        self.assertIn("drops_stored_name", self.codes(GOOD, stored=["علي بن إبراهيم", "يونس", "كذا ثم"]))
        self.assertNotIn("drops_stored_name", self.codes(GOOD, stored=["وعلي بن إبراهيم", "زرارة"]))            # present with attached «و»; the other is not in the text
        text = "حدثنا " + " ".join(f"ن{i}" for i in range(10)) + " قال كذا"
        nine = reading([[[it(f"ن{i}") for i in range(8)]]])
        self.assertEqual(self.codes(nine, text), [])                                                    # eight routes: at the limit, not over it
        many = reading([[[it("ن0"), it("ن1"), it("ن2")], [it("ن3"), it("ن4"), it("ن5")], [it("ن6"), it("ن7")]]])
        self.assertIn("too_many_routes", self.codes(many, text))                                       # 18 routes
        nested = "حدثنا أ وب جميعا عن ج؛ وحدثنا د وه جميعا عن ز قال كذا"
        self.assertIn("nested_jami", self.codes(reading([[[it("أ"), it("ب")], [it("ج")]], [[it("د"), it("ه")], [it("ز")]]]), nested))
        opening = "13- عنه، عن أحمد بن مهران قال كذا"
        self.assertIn("back_reference_without_previous_report", self.codes(reading([[[it("عنه", "back_reference")], [it("أحمد بن مهران")]]]), opening, {"work": {}}))
        self.assertNotIn("back_reference_without_previous_report", self.codes(reading([[[it("عنه", "back_reference")], [it("أحمد بن مهران")]]]), opening, CONTEXT_BLOCK))
        self.assertIn("needs_ruling", self.codes(with_(lambda o: o.update(needs_ruling=True))))
        refused = reading([], status="cannot_read_without_previous_report")
        self.assertIn("cannot_read_without_previous_report", self.codes(refused, "5 - وبهذا الإسناد قال كذا", dict(CONTEXT_BLOCK, needs_previous_report=True)))


class TextValidation(unittest.TestCase):
    TEXT = "عدة من أصحابنا عن سهل قال كذا وكذا"
    CONTEXT = {"text_and_metadata": {"copies": [{"source": "HKG", "relation": "differs", "theirs_span": "قال كذا منوكذا"}], "metadata": {"ours": {"report_number": "159"}, "gradings": []}}}
    DIFF = {"ours": "كذا وكذا", "theirs": "كذا منوكذا", "source": "HKG"}
    FIX = fix("text_differs_from_source", [{"source": "text", "quote": "قال كذا وكذا"}])

    @staticmethod
    def out(text_check, metadata_check=None, fixes=None):
        return {"id": "cr-1", "text_check": text_check, "metadata_check": metadata_check or {"status": "matches", "compared": ["THQ"], "differences": []}, "fixes": fixes or [], "notes": []}

    def test_cases(self):
        D, F = self.DIFF, self.FIX
        cases = [
            ("matches", self.out({"status": "matches", "compared": ["HKG"], "differences": []}), None),
            ("not_checked with a reason", self.out({"status": "not_checked", "compared": [], "differences": [], "reason": "no second copy"}), None),
            ("not_checked without a reason", self.out({"status": "not_checked", "compared": [], "differences": []}), "text_check_reason"),
            ("status outside the vocabulary", self.out({"status": "ok", "compared": ["HKG"], "differences": []}), "text_check_status"),
            ("differs with a quoted difference and a fix", self.out({"status": "differs", "compared": ["HKG"], "differences": [D]}, fixes=[F]), None),
            ("differs without a fix", self.out({"status": "differs", "compared": ["HKG"], "differences": [D]}), "text_check_fix"),
            ("differs without differences", self.out({"status": "differs", "compared": ["HKG"], "differences": []}, fixes=[F]), "text_check_differences"),
            ("our quote is not in the text", self.out({"status": "differs", "compared": ["HKG"], "differences": [dict(D, ours="غير موجود")]}, fixes=[F]), "difference_quote"),
            ("their quote is not in the context item", self.out({"status": "differs", "compared": ["HKG"], "differences": [dict(D, theirs="لم يقل")]}, fixes=[F]), "difference_quote"),
            ("online claim without url", self.out({"status": "differs", "compared": ["https://example.org/h/1"], "differences": [dict(D, source="online")]}, fixes=[F]), "difference_online"),
            ("online claim with url", self.out({"status": "differs", "compared": ["https://example.org/h/1"], "differences": [dict(D, source="online", url="https://example.org/h/1")]}, fixes=[F]), None),
            ("compared names neither a code nor a URL", self.out({"status": "matches", "compared": ["google"], "differences": []}), "text_check_compared"),
            ("matches that lists differences", self.out({"status": "matches", "compared": ["HKG"], "differences": [D]}), "text_check_differences"),
        ]
        for name, output, expected in cases:
            with self.subTest(name):
                errors = validate_text(output, self.TEXT, "cr-1", self.CONTEXT)
                if expected is None:
                    self.assertEqual(errors, [])
                else:
                    self.assertTrue(any(e.startswith(expected) for e in errors), errors)


class ScoreShape(unittest.TestCase):
    def test_derived_links_leave_the_v1_shape_and_imam_is_a_switch(self):
        result, _ = expand(GOOD, TEXT, CONTEXT_BLOCK)
        dropped = to_v1_shape(result, "drop")
        self.assertEqual([l["surface"] for l in dropped["routes"][0]["links"]][-1], "يُونُسَ")
        kept = to_v1_shape(result, "keep")
        self.assertEqual(len(kept["routes"][0]["links"]), len(dropped["routes"][0]["links"]) + 1)
        self.assertTrue(all(l["kind"] == "narrator" for l in kept["routes"][0]["links"]))

    def test_shared_tail_index_follows_the_dropped_head(self):
        text = "حدثنا أ، حدثنا ب، قالا حدثنا ج"
        result, _ = expand(reading([[[it("أ")]], [[it("ب")]]], [[it("ج")]]), text, CONTEXT_BLOCK)
        shaped = to_v1_shape(result, "drop")
        self.assertEqual([r["shared_tail_from"] for r in shaped["routes"]], [1, 1])

    def test_attached_wa_is_a_stored_name_present_in_the_text(self):
        text = "حدثنا عبيد الله بن عمر القواريري، وأحمد بن عبدة، قال ابن عبدة أخبرنا"
        self.assertFalse(surface_in_text("أحمد بن عبدة", text))                      # v1: dropped as "not in text" (the artifact)
        self.assertTrue(surface_in_text_with_attached_wa("أحمد بن عبدة", text))
        self.assertFalse(surface_in_text_with_attached_wa("زهير بن حرب", text))


if __name__ == "__main__":
    unittest.main()
