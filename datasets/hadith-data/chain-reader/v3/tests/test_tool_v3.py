"""Table-driven tests of the v3 tool on the second pilot's real reports and outputs (read-only: context/outputs-v2, pilot/reports.jsonl).

    python -B -X utf8 -m unittest discover -s v3/tests -p "test_tool_v3.py"        (from chain-reader/)

Each table row is a case the judge named (analysis-v2/README.md) and what the v3 tool must do with the readers' real outputs. Rows marked KNOWN_MISS document
what the tool does not catch, so a change that starts catching it shows up.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
V3 = HERE.parent
ROOT = V3.parent
CTX = ROOT / "context"
for path in (str(ROOT), str(V3), str(CTX)):
    sys.path.insert(0, path)

import expand as expand_v2  # noqa: E402  (context/expand.py, read-only)
import expand_v3  # noqa: E402
import holds_v3  # noqa: E402
import norm_v3  # noqa: E402
import validate_v3  # noqa: E402
from validate import load_reports, parse_output  # noqa: E402

REPORTS = load_reports(ROOT / "pilot" / "reports.jsonl")
PACKETS = {}
for packet_file in sorted((CTX / "pilot-v2" / "packets").glob("packet-*.jsonl")):
    for line in packet_file.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            PACKETS[row["id"]] = row


def output_of(run: str, report_id: str) -> dict:
    return parse_output((CTX / "outputs-v2" / run / f"{report_id}.json").read_text(encoding="utf-8"))[0]


def context_of(report_id: str) -> dict:
    report = REPORTS[report_id]
    context = json.loads(json.dumps(PACKETS[report_id]["context"]))
    context.setdefault("work", {})["key"] = f"{report['tradition']}:{report['work']}"
    return context


def read(run: str, report_id: str, tool=expand_v3):
    return tool.expand(output_of(run, report_id), REPORTS[report_id]["text"], context_of(report_id))


def holds_of(run: str, report_id: str) -> list[str]:
    reading, _ = read(run, report_id)
    other = output_of("run-b" if run == "run-a" else "run-a", report_id)
    return [h["code"] for h in holds_v3.compute_holds(reading, output_of(run, report_id), REPORTS[report_id]["text"], context_of(report_id),
                                                       [s for c in REPORTS[report_id]["stored_chains"] for s in c["surfaces"]], other)]


class SpellingFold(unittest.TestCase):
    # id, pass whose v2 output was invalid, what the text writes that the reader spelled differently
    CASES = [("cr-0031", "run-a", "على (alif maqsura)"), ("cr-0036", "run-a", "Persian yeh"), ("cr-0019", "run-b", "«و بهذا» with a space"), ("cr-0006", "run-b", "stray occurrence 2"), ("cr-0071", "run-a", "على (alif maqsura)"),
             ("cr-0055", "run-a", "Persian yeh"), ("cr-0233", "run-a", "على and a glued honorific"), ("cr-0085", "run-b", "kunya case أبو/أبي هريرة")]

    def test_v2_refused_and_v3_reads_with_the_texts_own_characters(self):
        for report_id, run, why in self.CASES:
            with self.subTest(report_id=report_id, why=why):
                old, old_errors = read(run, report_id, expand_v2)
                self.assertIsNone(old, "the case must be one v2 refused")
                new, errors = read(run, report_id)
                self.assertEqual(errors, [])
                text = REPORTS[report_id]["text"]
                for route in new["routes"]:
                    for link in route["links"]:
                        if link["start"] is not None:
                            self.assertEqual(text[link["start"]:link["end"]], link["surface"], "the surface is the text's own characters")

    def test_the_kunya_error_of_cr_0070_is_gone_but_the_stray_marker_inside_a_name_is_not_tolerated(self):
        # B wrote «أبو محمد» for «أبي محمد» (folded now) and «الحسين بن زيد» for the text's «الحسين بن (ي‍) زيد» (a marker inside the name: still refused)
        _, errors = read("run-b", "cr-0070")
        self.assertEqual([e.split(":")[0] for e in errors], ["surface_not_in_text"])
        self.assertIn("الحسين بن زيد", errors[0])

    def test_the_other_reader_of_each_case_still_reads_the_same(self):
        for report_id in ("cr-0031", "cr-0006", "cr-0085"):
            with self.subTest(report_id=report_id):
                a, _ = read("run-a", report_id)
                b, _ = read("run-b", report_id)
                self.assertTrue(a and b)
                self.assertEqual(expand_v3.canonical(a), expand_v3.canonical(b))


class EquivalentReadingsCompareEqual(unittest.TestCase):
    # both passes valid under v2 but canonical() differed: trailing epithet, nisba, attached «و», «بهذا الحديث»
    CASES = ["cr-0163", "cr-0166", "cr-0167", "cr-0151", "cr-0180"]

    def test_v3_canonical_equal_where_v2_was_not(self):
        for report_id in self.CASES:
            with self.subTest(report_id=report_id):
                a2, _ = read("run-a", report_id, expand_v2)
                b2, _ = read("run-b", report_id, expand_v2)
                self.assertTrue(a2 and b2)
                self.assertNotEqual(expand_v2.canonical(a2), expand_v2.canonical(b2))
                a3, _ = read("run-a", report_id)
                b3, _ = read("run-b", report_id)
                self.assertEqual(expand_v3.canonical(a3), expand_v3.canonical(b3))

    def test_different_men_stay_different(self):
        # one letter or one word apart is a different reading: the folds must not make everything equal
        self.assertNotEqual(norm_v3.link_key("محمد بن علي"), norm_v3.link_key("محمد بن الحسن"))
        self.assertNotEqual(norm_v3.link_key("أبو بكر بن أبي شيبة"), norm_v3.link_key("أبو بكر بن عياش"))
        self.assertEqual(norm_v3.link_key("وأحمد بن عبدة"), norm_v3.link_key("أحمد بن عبدة"))
        self.assertEqual(norm_v3.link_key("على بن محمد"), norm_v3.link_key("علي بن محمد"))


class CompilerWrittenInTheText(unittest.TestCase):
    def heads(self, run: str, report_id: str) -> int:
        reading, _ = read(run, report_id)
        return sum(1 for route in reading["routes"] if route["links"][0]["kind"] == "compiler_head")

    def test_text_writes_the_compiler_under_a_longer_spelling(self):
        # cr-0183: head «الحسين بن سعيد الأهوازي» + the text's «الحسين بن سعيد»; cr-0197: «الصدوق» + «أبو جعفر محمد بن علي … ابن بابويه القمي»
        for report_id in ("cr-0183", "cr-0197"):
            with self.subTest(report_id=report_id):
                self.assertEqual(self.heads("run-a", report_id), 0)
                old, _ = read("run-a", report_id, expand_v2)
                self.assertTrue(any(r["links"][0]["kind"] == "compiler_head" and len(r["links"]) > 1 for r in old["routes"]), "v2 wrote the compiler twice")

    def test_a_transmitter_who_shares_the_compilers_short_name_does_not_suppress_the_head(self):
        text = "حدثنا مسلم بن إبراهيم، حدثنا شعبة، عن قتادة، عن أنس، قال كذا"
        output = {"id": "t", "status": "read", "groups": [{"levels": [[{"surface": "مسلم بن إبراهيم", "kind": "narrator"}], [{"surface": "شعبة", "kind": "narrator"}]]}],
                  "shared_tail": None, "needs_ruling": False, "notes": [], "fixes": []}
        context = {"work": {"key": "sunni:muslim", "compiler": {"ar": "مسلم", "head_of_every_chain": True}}}
        reading, errors = expand_v3.expand(output, text, context)
        self.assertEqual(errors, [])
        self.assertEqual(reading["routes"][0]["links"][0]["kind"], "compiler_head")
        # ... while the compiler written as his own full name is the compiler
        text2 = "حدثنا مسلم بن الحجاج، حدثنا شعبة"
        output["groups"][0]["levels"][0][0]["surface"] = "مسلم بن الحجاج"
        reading2, _ = expand_v3.expand(output, text2, context)
        self.assertEqual(reading2["routes"][0]["links"][0]["kind"], "narrator")

    def test_musnad_zayd_head_is_abu_khalid_al_wasiti(self):
        profile = expand_v3.PROFILES["zaydi:musnad-zayd"]
        self.assertTrue(profile["compiler_head"])
        self.assertIn("أبو خالد الواسطي", profile["compiler_aliases"])


class SameManWrittenTwice(unittest.TestCase):
    def test_short_and_full_form_in_succession_are_one_link(self):
        reading, _ = read("run-a", "cr-0144")                     # «كلاهما عن المعتمر … حدثنا معتمر بن سليمان»
        for route in reading["routes"]:
            names = [l["surface"] for l in route["links"]]
            self.assertIn("معتمر بن سليمان", names)
            self.assertNotIn("المعتمر", names)
        self.assertTrue(any("one man written twice" in n for n in reading["tool_notes"]))

    def test_two_different_men_with_one_name_are_not_merged(self):
        reading, _ = read("run-a", "cr-0200")                     # «محمد بن الحسن» then «محمد بن الحسن الصفار»
        names = [l["surface"] for l in reading["routes"][0]["links"] if l["kind"] == "narrator"]
        self.assertEqual(len(names), 5)
        self.assertEqual(reading["tool_notes"], [])
        self.assertFalse(norm_v3.same_man("محمد", "محمد بن علي"))   # a bare first name is not a short form


class Holds(unittest.TestCase):
    # id, pass, hold codes that must be present, hold codes that must be absent
    CASES = [
        ("cr-0133", "run-a", {"routes_end_at_different_links"}, set()),       # shared tail «سمعت أبا هريرة» dropped from route one
        ("cr-0133", "run-b", {"routes_end_at_different_links"}, set()),
        ("cr-0157", "run-a", {"routes_end_at_different_links"}, set()),       # route one ends «ابن أبي عمير»
        ("cr-0193", "run-a", {"back_reference_only"}, set()),                 # previous report supplied, «بهذا الإسناد» not expanded
        ("cr-0008", "run-a", {"back_reference_only"}, set()),                 # names stand three reports back
        ("cr-0136", "run-a", {"second_isnad_not_same_saying"}, set()),        # the isnad of an appended poem
        ("cr-0147", "run-b", {"routes_end_at_different_links"}, set()),       # B adds «الصعب بن جثامة» to some routes only
        ("cr-0147", "run-a", set(), {"routes_end_at_different_links"}),       # A: every route ends alike
        ("cr-0075", "run-a", set(), {"routes_end_at_different_links"}),       # «عن أبي جعفر وأبي عبد الله»: a level of alternatives at the end
        ("cr-0044", "run-a", set(), {"routes_end_at_different_links"}),       # «|»-separated alternatives of the source's own field
        ("cr-0267", "run-a", set(), {"routes_end_at_different_links"}),       # two Imams named as one level
        ("cr-0091", "run-a", set(), {"back_reference_only"}),                 # own names, then a closing «بهذا الإسناد»: the Sunni convention
        ("cr-0194", "run-a", set(), {"back_reference_only"}),                 # «وعنه (ع)» with the inherited name taken
        ("cr-0033", "run-a", set(), {"drops_stored_name"}),                   # removed: it punished corrections
        ("cr-0183", "run-a", set(), {"drops_stored_name"}),
    ]
    # what the tool does not catch: speaker omitted (cr-0177), Companion's place of hearing added (cr-0264 B), a restated route (cr-0033)
    KNOWN_MISS = [("cr-0177", "run-a"), ("cr-0264", "run-b"), ("cr-0033", "run-a")]

    def test_table(self):
        for report_id, run, present, absent in self.CASES:
            with self.subTest(report_id=report_id, run=run):
                codes = set(holds_of(run, report_id))
                self.assertLessEqual(present, codes)
                self.assertFalse(absent & codes, f"{absent & codes} fired")

    def test_known_misses_stay_unheld(self):
        for report_id, run in self.KNOWN_MISS:
            with self.subTest(report_id=report_id):
                self.assertEqual(set(holds_of(run, report_id)) - {"back_reference_without_previous_report"}, set())

    def test_needs_ruling_holds_only_when_both_readers_set_it(self):
        for report_id, held in (("cr-0202", True), ("cr-0264", False), ("cr-0008", False)):
            with self.subTest(report_id=report_id):
                a, b = output_of("run-a", report_id), output_of("run-b", report_id)
                self.assertEqual("needs_ruling" in holds_of("run-a", report_id), held)
                self.assertEqual(holds_v3.ruling_flag_state(a, b) == "both", held)
        self.assertEqual(holds_v3.ruling_flag_state(output_of("run-a", "cr-0264"), output_of("run-b", "cr-0264")), "a_only")

    def test_missing_previous_report_still_holds(self):
        for report_id in ("cr-0143", "cr-0168", "cr-0121"):
            with self.subTest(report_id=report_id):
                self.assertIn("back_reference_without_previous_report", holds_of("run-a", report_id))


class BackReferenceDetection(unittest.TestCase):
    def test_shared_cases(self):
        for case in json.loads((HERE / "backref_cases.json").read_text(encoding="utf-8")):
            with self.subTest(text=case["text"][:40]):
                self.assertEqual(holds_v3.opens_with_back_reference(case["text"]), case["opens"])
                self.assertEqual(holds_v3.opening_form(case["text"]), case["form"])

    def test_the_six_missed_ids_and_cr_0151_are_detected(self):
        for report_id in ("cr-0019", "cr-0084", "cr-0121", "cr-0143", "cr-0164", "cr-0168", "cr-0151"):
            with self.subTest(report_id=report_id):
                self.assertTrue(holds_v3.opens_with_back_reference(REPORTS[report_id]["text"]))


class Validation(unittest.TestCase):
    def test_variant_group_is_accepted_and_marks_its_routes(self):
        text = "حدثنا مسدد، حدثنا يحيى، عن شعبة ... ورواه خالد عن شعبة"
        output = {"id": "t", "status": "read", "groups": [{"levels": [[{"surface": "مسدد", "kind": "narrator"}], [{"surface": "يحيى", "kind": "narrator"}]]},
                                                          {"variant": True, "levels": [[{"surface": "خالد", "kind": "narrator"}]]}],
                  "shared_tail": [[{"surface": "شعبة", "kind": "narrator", "occurrence": 1}]], "needs_ruling": False, "notes": [], "fixes": []}
        self.assertEqual(validate_v3.validate_chain(output, text, "t", {}), [])
        reading, _ = expand_v3.expand(output, text, {})
        self.assertEqual([r["variant"] for r in reading["routes"]], [False, True])
        output["groups"][1]["variant"] = "yes"
        self.assertTrue(validate_v3.validate_chain(output, text, "t", {}))
        output["groups"][1] = {"levels": output["groups"][1]["levels"], "flag": 1}
        self.assertTrue(validate_v3.validate_chain(output, text, "t", {}))

    def test_cannot_read_needs_the_flag(self):
        output = {"id": "t", "status": "cannot_read_without_previous_report", "groups": [], "shared_tail": None, "needs_ruling": False, "notes": [], "fixes": []}
        self.assertTrue(validate_v3.validate_chain(output, "وبهذا الإسناد عن أحمد", "t", {}))
        self.assertEqual(validate_v3.validate_chain(output, "وبهذا الإسناد عن أحمد", "t", {"needs_previous_report": True}), [])


if __name__ == "__main__":
    unittest.main()
