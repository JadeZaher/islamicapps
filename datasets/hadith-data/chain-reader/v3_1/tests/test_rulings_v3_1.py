"""v3.1 on batch 001's real readings and on the examples' real packets (read-only: v3/batch-001/{packets,outputs}, analysis-batch-001/sample.tsv, v3_1/examples).

    python -B -X utf8 -m unittest discover -s v3_1/tests -p "test_rulings_v3_1.py"        (from chain-reader/)

Every row is a case the batch-001 judge named (analysis-batch-001/cases.md) and what the v3.1 tool must now do with the readers' real v3 outputs: the tool's typo and scope folds,
`routes_end_at_different_links`, the asker ruling, the empty readings, the submission of inherited and no-chain readings.
"""

from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
V31 = HERE.parent
ROOT = V31.parent
V3 = ROOT / "v3"
B1 = V3 / "batch-001"
for path in (str(ROOT), str(V31)):
    sys.path.insert(0, path)

import expand_v3_1  # noqa: E402
import holds_v3_1  # noqa: E402
import to_submission_v3_1  # noqa: E402
import triage_v3_1  # noqa: E402
from norm import MARKS  # noqa: E402
from norm_v3_1 import fold_v3, link_key  # noqa: E402
from validate import parse_output  # noqa: E402

PACKETS = triage_v3_1.load_packets(B1 / "packets")
STORED = {row["id"]: [s for chain in row["stored_chains"] for s in chain["surfaces"]]
          for row in (json.loads(line) for line in (B1 / "private" / "reports.jsonl").read_text(encoding="utf-8").splitlines() if line.strip())}
JUDGE = {row["id"]: row for row in csv.DictReader((ROOT / "analysis-batch-001" / "sample.tsv").open(encoding="utf-8"), delimiter="\t")}
ROWS = {row["id"]: row for row in triage_v3_1.triage(PACKETS, B1 / "outputs" / "pass-a", B1 / "outputs" / "pass-b", STORED)}


def rid(short: str) -> str:
    return short if short.startswith("b1-") else "b1-" + short


def output_of(tag: str, short: str) -> dict:
    return parse_output((B1 / "outputs" / f"pass-{tag}" / f"{rid(short)}.json").read_text(encoding="utf-8"))[0]


class TypoAndScopeFolds(unittest.TestCase):
    """The judge's tool class: a joined name, an attached «ل», and the scope classes that two right readings differ by."""

    def test_surfaces_the_text_spells_oddly_are_found(self):
        for short, tags in (("6e0cb4", "b"), ("b50f75", "ab"), ("d8f54e", "ab")):          # 6e0cb4 A «أبي طالب» corrects the text's «بيطالب»: a reader's correction, still invalid
            for tag in tags:
                packet = PACKETS[rid(short)]
                reading, errors = expand_v3_1.expand(output_of(tag, short), packet["text"], packet["context"])
                self.assertEqual(errors, [], (short, tag))
        packet = PACKETS["b1-6e0cb4"]
        self.assertTrue(expand_v3_1.expand(output_of("a", "6e0cb4"), packet["text"], packet["context"])[1])
        joined, _ = expand_v3_1.expand(output_of("b", "6e0cb4"), packet["text"], packet["context"])
        self.assertTrue(any("بنجعفر" in MARKS.sub("", link["surface"]) for link in joined["routes"][0]["links"]), "the joined «بنجعفر» is located as written")
        reading, _ = expand_v3_1.expand(output_of("a", "d8f54e"), PACKETS["b1-d8f54e"]["text"], PACKETS["b1-d8f54e"]["context"])
        self.assertEqual(fold_v3(reading["routes"][0]["links"][-1]["surface"]), "للرضا", "the surface is the text's own characters, preposition included")

    def test_scope_variants_of_one_name_now_agree(self):
        for short in ("1b65ce", "b43223", "de6e12", "d8f54e"):
            self.assertTrue(ROWS[rid(short)]["agree"], short)

    def test_different_men_stay_different(self):
        for first, second in (("علي بن الحسين", "علي بن الحسن"), ("الرضا", "الكاظم"), ("جابر", "جابر بن سمرة"), ("أبو الحسن الرضا", "أبو الحسن الكاظم"), ("موسى بن جعفر", "موسى بن عمران")):
            self.assertNotEqual(link_key(first), link_key(second), (first, second))
        for first, second in (("جابر", "جابرا"), ("الرضا", "أبو الحسن الرضا"), ("أحمد بن عيسى", "أحمد بن عيسى المصريان"), ("الرضا", "للرضا")):
            self.assertEqual(link_key(first), link_key(second), (first, second))


class RoutesEndAtDifferentLinks(unittest.TestCase):
    def test_the_four_dropped_tails_are_still_held(self):
        for short in ("160be9", "162ebe", "844adb", "d2bb6c"):
            self.assertIn("routes_end_at_different_links", ROWS[rid(short)]["holds"], short)

    def test_an_abbreviated_route_and_two_independent_isnads_are_released(self):
        for short in ("21210d", "3c59ef"):                       # «فذكر نحوه»; two isnads that end at different Companions
            self.assertNotIn("routes_end_at_different_links", ROWS[rid(short)]["holds"], short)
            self.assertTrue(ROWS[rid(short)]["eligible"], short)

    def test_a_nested_chain_stays_held_by_its_own_hold(self):
        self.assertIn("nested_semicolon", ROWS["b1-ee5c9a"]["holds"])


class AskerIsALink(unittest.TestCase):
    NINE = ("1507aa", "2fd814", "5d1972", "7b9421", "9fc153", "b348c8", "b9039f", "b908c9", "f03941")      # the judge's Q1d: readers dropped the asker

    def test_readings_that_drop_the_asker_are_held(self):
        for short in self.NINE:
            self.assertIn("asker_not_a_link", ROWS[rid(short)]["holds"], short)
            self.assertFalse(ROWS[rid(short)]["eligible"], short)

    def test_the_reading_that_kept_the_writer_of_the_question_is_not(self):
        self.assertNotIn("asker_not_a_link", ROWS["b1-4cbe02"]["holds"])          # «و كتب البزنطي إلى أبي الحسن»: البزنطي, أبي الحسن

    def test_asker_offsets(self):
        text = "5610 - و كتب البزنطي إلى أبي الحسن عليه السلام : في رجل"
        self.assertEqual(text[holds_v3_1.named_asker_offset(text):][:7], "البزنطي")
        for no_asker in ("و كتب إليه في رجل", "و سئل : عن رجل", "و سأله: عن الخلاخل", "و قال عليه السلام: «كذا"):
            self.assertIsNone(holds_v3_1.named_asker_offset(no_asker), no_asker)


class EmptyReadings(unittest.TestCase):
    """The 57 empty readings of batch 001: the 33 «clear» and the 3 Prophet reports apply as «no chain by reading»; every report the rulings touch is held."""

    def test_table(self):
        applies, held = [], []
        for short, row in JUDGE.items():
            if row["class"] != "empty-reading hold":
                continue
            tags = row["owner_question_tags"]
            (applies if ROWS[short]["applies"] == "no_chain" else held).append(short)
            if tags.startswith(("cat:clear,", "cat:clear", "cat:prophet")) and tags not in ("cat:clear-no-name",):
                self.assertEqual(ROWS[short]["applies"], "no_chain", (short, ROWS[short]["holds"]))
            else:
                self.assertFalse(ROWS[short]["eligible"], (short, tags))
                self.assertTrue({"empty_reading_unsettled_opening", "empty_reading_transmission_name"} & set(ROWS[short]["holds"]), (short, ROWS[short]["holds"]))
        self.assertEqual((len(applies), len(held)), (36, 21))

    def test_a_name_after_a_transmission_word_holds_an_empty_reading(self):
        for text, code in (("و روى زرارة بن أعين عن أبي جعفر عليه السلام: «من فعل كذا", "transmission_name"), ("حدثنا محمد بن علي: «كذا", "transmission_name"),
                           ("و روي عن أبي عبد الله عليه السلام: «كذا", "transmission_name"), ("و روي: «أن من قتل وزغا", "applicable"),
                           ("و في خبر آخر: «لا يكون الوفاء", "applicable"), ("قال أبو جعفر مصنف هذا الكتاب: الدليل على", "applicable"),
                           ("قال محمد بن راشد: «فلما سمعت", "unsettled_opening"), ("و قضى أمير المؤمنين عليه السلام في امرأة", "unsettled_opening")):
            self.assertEqual(holds_v3_1.empty_reading_state(text)[0], code, text)

    def test_the_old_blanket_hold_is_gone(self):
        self.assertTrue(all("reading_empty_stored_has_links" not in row["holds"] for row in ROWS.values()))


class OpeningClasses(unittest.TestCase):
    def test_shared_cases(self):
        for case in json.loads((HERE / "opening_cases_v3_1.json").read_text(encoding="utf-8")):
            self.assertEqual(holds_v3_1.opening_class(case["text"]), case["class"], case["text"][:40])

    def test_an_opening_that_leans_on_the_earlier_report_is_held_without_one(self):
        packet = {"work": {"key": "imami:man-la-yahduruhu-al-faqih"}}
        output = {"status": "read", "needs_ruling": False}
        text = "4014 - و سأله سماعة : عن الطعام"
        reading, _ = expand_v3_1.expand({"id": "x", "status": "read", "groups": [{"levels": [[{"surface": "سماعة", "kind": "narrator"}]]}], "shared_tail": None, "needs_ruling": False, "notes": [], "fixes": []}, text, packet)
        codes = [h["code"] for h in holds_v3_1.compute_holds(reading, output, text, packet)]
        self.assertIn("back_reference_without_previous_report", codes)


class Submission(unittest.TestCase):
    """The examples' real packets (a named asker, a pronoun asker with an inherited Imam, an inherited speaker, a saying with no isnad) through triage and to_submission."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        (base / "packets").mkdir()
        packets = [json.loads(line) for line in (V31 / "examples" / "example-packets.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        (base / "packets" / "packet-001.jsonl").write_text("\n".join(json.dumps(p, ensure_ascii=False) for p in packets) + "\n", encoding="utf-8")
        n, i, u = "narrator", "inherited", "imam_in_text"
        readings = {
            "b1-4cbe02": [[[("البزنطي", n)], [("أبي الحسن", u)]]],
            "b1-05f29e": [[[("سماعة", n)], [("أبي عبد الله", i, "prev1")]]],
            "b1-38f586": [[[("الصادق", i, "prev1")]]],
            "b1-2c405e": [],
        }
        for tag in ("a", "b"):
            (base / "outputs" / f"pass-{tag}").mkdir(parents=True)
            for report_id, groups in readings.items():
                body = {"id": report_id, "status": "read", "groups": [{"levels": [[dict(surface=s[0], kind=s[1], **({"from": s[2]} if len(s) > 2 else {})) for s in level] for level in levels]} for levels in groups],
                        "shared_tail": None, "needs_ruling": False, "notes": [], "fixes": []}
                (base / "outputs" / f"pass-{tag}" / f"{report_id}.json").write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
            (base / "outputs" / f"pass-{tag}" / "RUN.txt").write_text(f"run_id=t01-{tag}-001 | packets=001 | model=test-model-1 | start=2026-11-23T09:00:00Z | end=2026-11-23T09:10:00Z | files=4\n", encoding="utf-8")
        previous = {"b1-05f29e": [{"ref": "prev1", "hadith_id": "hadith:thaqalayn:previous-of-05f29e", "supplies": "chain"}], "b1-38f586": [{"ref": "prev1", "hadith_id": "hadith:thaqalayn:previous-of-38f586", "supplies": "speaker"}]}
        (base / "reports.jsonl").write_text("\n".join(json.dumps({"id": p["id"], "hadith_id": "hadith:thaqalayn:" + p["id"], "text": p["text"], "stored_chains": [{"chain_id": "chain:x", "surfaces": ["stored junk"]}],
                                                                  "previous_reports": previous.get(p["id"], [])}, ensure_ascii=False) for p in packets) + "\n", encoding="utf-8")
        self.base = base

    def tearDown(self):
        self.tmp.cleanup()

    def run_submission(self):
        base = self.base
        to_submission_v3_1.main(["--packets", str(base / "packets"), "--reports", str(base / "reports.jsonl"), "--pass-a", str(base / "outputs" / "pass-a"), "--pass-b", str(base / "outputs" / "pass-b"), "--out", str(base / "sub")])
        return json.loads((base / "sub" / "packet-001.envelope.json").read_text(encoding="utf-8")), json.loads((base / "sub" / "packet-001.no_chain.envelope.json").read_text(encoding="utf-8"))

    def test_triage_applies_chains_and_no_chain(self):
        base = self.base
        rows = {r["id"]: r for r in triage_v3_1.triage(triage_v3_1.load_packets(base / "packets"), base / "outputs" / "pass-a", base / "outputs" / "pass-b")}
        self.assertEqual({k: (r["eligible"], r["applies"], r["holds"]) for k, r in rows.items()},
                         {"b1-4cbe02": (True, "chain", []), "b1-05f29e": (True, "chain", []), "b1-38f586": (True, "chain", []), "b1-2c405e": (True, "no_chain", [])})

    def test_inherited_readings_are_submitted_citing_the_previous_report(self):
        chain, no_chain = self.run_submission()
        fixes = {f["reader_output_v3"]["id"]: f for f in chain["fixes"]}
        self.assertEqual(set(fixes), {"b1-4cbe02", "b1-05f29e", "b1-38f586"})
        self.assertEqual(fixes["b1-05f29e"]["inherited_from"], [{"ref": "prev1", "previous_report_id": "hadith:thaqalayn:previous-of-05f29e", "supplies": "chain", "surfaces": ["أبي عبد الله"]}])
        self.assertEqual(fixes["b1-38f586"]["inherited_from"][0]["previous_report_id"], "hadith:thaqalayn:previous-of-38f586")
        self.assertIsNone(fixes["b1-38f586"]["output"], "no written link: the v1-shaped copy is null, the v3 reading is the submission")
        self.assertNotIn("inherited_from", fixes["b1-4cbe02"])
        self.assertEqual([fold_v3(l["surface"]) for l in fixes["b1-4cbe02"]["output"]["routes"][0]["links"]], ["البزنطي", "ابو الحسن"])
        self.assertEqual(chain["run"]["prompt_version"], "3.1.0")

    def test_an_empty_reading_goes_out_as_no_chain_by_reading(self):
        _, no_chain = self.run_submission()
        self.assertEqual(no_chain["format"], "shura-chain-no-chain-envelope/1")
        self.assertEqual([(f["output"]["id"], f["disposition"], f["stored_chain_surfaces"]) for f in no_chain["fixes"]], [("b1-2c405e", "no_chain_by_reading", ["stored junk"])])


if __name__ == "__main__":
    unittest.main()
