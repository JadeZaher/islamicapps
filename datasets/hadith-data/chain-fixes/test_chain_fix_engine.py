"""Engine and replay on real pilot reports: kinds, identity carry, planned ids, replay origins and hash binding.

    python -I datasets/hadith-data/chain-fixes/test_chain_fix_engine.py
"""

from __future__ import annotations

import gzip
import json
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "pg_export"))

import chain_fix_engine as engine  # noqa: E402
import replay  # noqa: E402

PILOT = {row["id"]: row for row in (json.loads(line) for line in (HERE.parent / "chain-reader" / "pilot" / "reports.jsonl")
                                    .read_text(encoding="utf-8").splitlines() if line.strip())}


def base_of(row: dict) -> dict:
    return {"chains": [{"branch": c["branch"], "mentions": [
        {"id": f"{c['chain_id'].replace('chain:', 'mention:', 1)}:{p:04d}", "surface_ar": s} for p, s in enumerate(c["surfaces"])]}
        for c in row["stored_chains"]]}


def reading(row: dict, names: list[list[str]], tail: int | None, matn_word: str) -> dict:
    text, routes = row["text"], []
    for route in names:
        cursor, links = 0, []
        for name in route:
            start = text.index(name, cursor)
            links.append({"surface": name, "start": start, "end": start + len(name), "kind": "narrator"})
            cursor = start + len(name)
        routes.append({"links": links, "shared_tail_from": tail})
    return {"id": row["id"], "routes": routes, "matn_start": text.index(matn_word), "notes": []}


ABU_DAWUD = PILOT["cr-0248"]          # k6:17633, al-Layth lost from both stored chains
ABU_DAWUD_READ = reading(ABU_DAWUD, [["يزيد بن خالد", "الليث بن سعد", "بكير", "سليمان بن يسار", "أبي هريرة"],
                                     ["قتيبة", "الليث بن سعد", "بكير", "سليمان بن يسار", "أبي هريرة"]], 1, "بعثنا")


class EngineTest(unittest.TestCase):
    def run_item(self, row: dict, output: dict, **extra) -> dict:
        return engine.run_item({"key": "0", "text": row["text"], "expected_id": row["id"], "output": output, "base": base_of(row),
                                "record_id": row["hadith_id"].removeprefix("hadith:"), "source_work_id": f"{row['tradition']}:{row['work']}",
                                **extra})

    def test_added_link_kinds_and_carry(self):
        result = self.run_item(ABU_DAWUD, ABU_DAWUD_READ, evidence=["أن الليث بن سعد"])
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["comparison"]["fix_kinds"], ["link_added", "shared_tail_attached"])
        first = result["planned"]["chains"][0]["mentions"]
        self.assertEqual([m["id"] for m in first][:2], ["mention:k6:17633:0000:0000", "mention:k6:17633:0000:0001"])
        self.assertEqual([m["carry_identity"] for m in first], [False, False, False, True, True])
        # the review unit is the projection's formula over the new neighbours
        self.assertEqual(first[1]["review_unit_fine_id"], engine.review_unit_ids("الليث بن سعد", "بكير", "يزيد بن خالد", "sunni:abudawud")[1])

    def test_stored_reading_is_no_change_across_a_comma_inside_a_name(self):
        muslim = PILOT["cr-0001"]
        output = reading(muslim, [["عبيد الله بن عمر القواريري", "سفيان بن عيينة", "ابن أبي نجيح", "مجاهد", "قزعة", "أبي سعيد، الخدري"],
                                  ["أحمد بن عبدة", "سفيان بن عيينة", "ابن أبي نجيح", "مجاهد", "قزعة", "أبي سعيد، الخدري"]], 1, "ذكر العزل")
        result = self.run_item(muslim, output, evidence=["عن أبي سعيد، الخدري"])
        self.assertEqual(result["comparison"]["fix_kinds"], ["no_change"])
        self.assertTrue(all(m["carry_identity"] for c in result["planned"]["chains"] for m in c["mentions"]))

    def test_unnamed_link_with_a_comma_inside_reads_as_the_stored_one_and_is_labelled_anonymous(self):
        bukhari = PILOT["cr-0202"]       # k6:1277: «أخبرني من، شهد النبي», stored as «من شهد النبي»
        output = reading(bukhari, [["مسلم", "شعبة", "الشيباني", "الشعبي", "من، شهد النبي"]], None, "أنه أتى")
        output["routes"][0]["links"][-1]["kind"] = "unnamed"
        result = self.run_item(bukhari, output, evidence=["أخبرني من، شهد النبي"])
        self.assertEqual(result["comparison"]["fix_kinds"], ["no_change"])
        self.assertEqual(result["planned"]["chains"][0]["mentions"][-1]["link_kind_if_new"], "anonymous")

    def test_a_trimmed_name_is_a_changed_surface_and_loses_its_identity(self):
        # The Sunni builder's clause-trim case (pg_export/AGENTS.md §Sunni chains): «زرارة بن أوفى يحدث» stored as one name.
        text = "حدثنا قتيبة، حدثنا أبو عوانة، عن قتادة، عن زرارة بن أوفى يحدث عن سعد بن هشام، قال سألت عائشة"
        row = {"id": "x", "hadith_id": "hadith:fixture:9", "tradition": "sunni", "work": "muslim", "text": text,
               "stored_chains": [{"chain_id": "chain:fixture:9:0000", "branch": 0,
                                  "surfaces": ["قتيبة", "أبو عوانة", "قتادة", "زرارة بن أوفى يحدث", "سعد بن هشام", "عائشة"]}]}
        output = reading(row, [["قتيبة", "أبو عوانة", "قتادة", "زرارة بن أوفى", "سعد بن هشام", "عائشة"]], None, "عائشة")
        output["matn_start"] = len(text)
        result = self.run_item(row, output, evidence=["عن زرارة بن أوفى يحدث عن"], require_coverage=True)
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["comparison"]["fix_kinds"], ["surface_changed"])
        mentions = result["planned"]["chains"][0]["mentions"]
        self.assertEqual((mentions[3]["surface_ar"], mentions[3]["kept_mention_id"]), ("زرارة بن أوفى", None))
        self.assertEqual([m["carry_identity"] for m in mentions], [True, True, False, False, False, True])

    def test_isnad_phrase_is_dropped_and_marks_the_route_as_relying_elsewhere(self):
        text = "حدثنا زهير، ح وحدثني بشر، قالا حدثنا شعبة، بهذا الإسناد. غير أنه قال كذا"
        row = {"id": "x", "hadith_id": "hadith:fixture:7", "tradition": "sunni", "work": "muslim", "text": text,
               "stored_chains": [{"chain_id": "chain:fixture:7:0000", "branch": 0, "surfaces": ["زهير", "شعبة"]},
                                 {"chain_id": "chain:fixture:7:0001", "branch": 1, "surfaces": ["بشر", "شعبة"]}]}
        span = lambda word: {"surface": word, "start": text.index(word), "end": text.index(word) + len(word), "kind": "narrator"}
        phrase = dict(span("بهذا الإسناد"), kind="back_reference")
        output = {"id": "x", "matn_start": text.index("غير"), "notes": [], "routes": [
            {"links": [span("زهير"), span("شعبة"), phrase], "shared_tail_from": 1},
            {"links": [span("بشر"), span("شعبة"), phrase], "shared_tail_from": 1}]}
        result = self.run_item(row, output, evidence=["بهذا الإسناد"])
        self.assertEqual(result["comparison"]["fix_kinds"], ["no_change"])
        self.assertEqual([c["suspension"] for c in result["planned"]["chains"]], ["back_reference", "back_reference"])

    def test_validator_errors_come_back_verbatim(self):
        bad = json.loads(json.dumps(ABU_DAWUD_READ))
        bad["routes"][0]["links"][0]["surface"] = "يزيد بن خالد الرملي"
        result = self.run_item(ABU_DAWUD, bad, evidence=["يزيد"])
        self.assertTrue(any(error.startswith("surface_mismatch: r0l0") for error in result["errors"]), result["errors"])

    def test_miscounted_offsets_are_refound_from_the_surfaces(self):
        shifted = json.loads(json.dumps(ABU_DAWUD_READ))
        for route in shifted["routes"]:
            for link in route["links"]:
                link["start"] += 1
                link["end"] += 1
        result = self.run_item(ABU_DAWUD, shifted, evidence=["الليث بن سعد"])
        self.assertEqual(result["errors"], [])
        self.assertTrue(result["offsets_repaired"])


V2_PACKETS = {row["id"]: row for packet in sorted((HERE.parent / "chain-reader" / "context" / "pilot-v2" / "packets").glob("packet-*.jsonl"))
              for row in (json.loads(line) for line in packet.read_text(encoding="utf-8").splitlines() if line.strip())}
V2_OUTPUTS = HERE.parent / "chain-reader" / "context" / "outputs-v2" / "run-a"


class ReaderV2Test(unittest.TestCase):
    """v2 outputs (levels, no offsets) on real pilot reports: expanded, validated, compared; holds computed, never applied."""

    def run_v2(self, report_id: str) -> dict:
        row, packet = PILOT[report_id], V2_PACKETS[report_id]
        output = json.loads((V2_OUTPUTS / f"{report_id}.json").read_text(encoding="utf-8"))
        return engine.run_item({"key": "0", "text": packet["text"], "expected_id": report_id, "output": output, "base": base_of(row),
                                "record_id": row["hadith_id"].removeprefix("hadith:"), "source_work_id": f"{row['tradition']}:{row['work']}",
                                "evidence": [packet["text"][:12]], "reader_format": "v2", "context": packet.get("context")})

    def test_a_stored_reading_expands_and_compares_with_no_hold(self):
        result = self.run_v2("cr-0001")
        self.assertEqual((result["errors"], result["holds"]), ([], []))
        self.assertEqual(result["comparison"]["fix_kinds"], ["no_change"])
        # The compiler head expand adds is the projection's to add, never a planned mention.
        self.assertTrue(all(m["span"][0] is not None for c in result["planned"]["chains"] for m in c["mentions"]))

    def test_a_reading_the_rulings_do_not_settle_is_held(self):
        result = self.run_v2("cr-0006")
        self.assertEqual(result["errors"], [])
        self.assertIn("needs_ruling", [hold["code"] for hold in result["holds"]])

    def test_the_v2_validators_errors_come_back_verbatim(self):
        self.assertTrue(self.run_v2("cr-0002")["errors"][0].startswith("occurrence:"))


class ReplayTest(unittest.TestCase):
    def override(self) -> dict:
        result = EngineTest().run_item(ABU_DAWUD, ABU_DAWUD_READ, evidence=["الليث بن سعد"])
        text = ABU_DAWUD["text"]
        return {"format": replay.OVERRIDES_FORMAT, "hadith_id": ABU_DAWUD["hadith_id"], "record_id": "k6:17633", "fix_id": "chain-fix:t",
                "arabic_sha256": replay.sha256_text(text), "reader_text_sha256": replay.sha256_text(text), "text_layout": "full_text",
                "effect": "replace_routes", "structure_status": "read_by_model", "planned": result["planned"]}

    def test_kept_names_bring_their_origin_new_names_none(self):
        old = [{"id": c["chain_id"], "branch": c["branch"], "sanad_confidence": "0",
                "mentions": [(f"{c['chain_id'].replace('chain:', 'mention:', 1)}:{p:04d}", s, s) for p, s in enumerate(c["surfaces"])],
                "origins": [(7, p) for p in range(len(c["surfaces"]))]} for c in ABU_DAWUD["stored_chains"]]
        counts = Counter()
        branches = replay.replay_branches(self.override(), old, counts)
        self.assertEqual(branches[0]["origins"], [(7, 0), None, (7, 1), (7, 2), (7, 3)])
        self.assertEqual(counts["mentions_new"], 2)
        self.assertEqual(replay.mention_id_map(self.override())["mention:k6:17633:0000:0001"], "mention:k6:17633:0000:0002")

    def test_binding_and_file_round_trip(self):
        row = self.override()
        text = ABU_DAWUD["text"]
        self.assertIsNone(replay.binding_problem(row, text, row["arabic_sha256"], None))
        self.assertEqual(replay.binding_problem(row, text + " ", replay.sha256_text(text + " "), None), "arabic_changed")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "o.jsonl.gz"
            with gzip.open(path, "wt", encoding="utf-8") as handle:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            self.assertEqual(list(replay.load_overrides(path)), [ABU_DAWUD["hadith_id"]])
            with gzip.open(path, "at", encoding="utf-8") as handle:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            with self.assertRaises(ValueError):
                replay.load_overrides(path)
        self.assertEqual(replay.load_overrides(Path(directory) / "absent.jsonl.gz"), {})


if __name__ == "__main__":
    unittest.main()
