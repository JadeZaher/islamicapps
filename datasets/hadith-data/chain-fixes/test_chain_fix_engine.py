"""Engine and replay on real pilot reports: kinds, identity carry, planned ids, the replay rewrite and hash binding.

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


BATCH_001 = HERE.parent / "chain-reader" / "v3" / "batch-001"
PACKETS = {row["id"]: row for path in sorted((BATCH_001 / "packets").glob("packet-*.jsonl"))
           for row in (json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())}


def batch_output(report_id: str) -> dict:
    return json.loads((BATCH_001 / "outputs" / "pass-a" / f"{report_id}.json").read_text(encoding="utf-8"))


class ReaderV3Test(unittest.TestCase):
    """Batch-001 readings (prompt v3) through tool v3_1, as the first applied batch was (AGENTS.md §reader formats)."""

    def run_v3(self, report_id: str, base: dict, **extra) -> dict:
        packet = PACKETS[report_id]
        return engine.run_item({"key": "0", "text": packet["text"], "expected_id": report_id, "output": batch_output(report_id),
                                "base": base, "record_id": "test:1", "source_work_id": "imami:test", "evidence": [packet["text"][:40]],
                                "reader_format": "v3", "tool_version": "v3_1", "context": packet.get("context"), **extra})

    def test_an_empty_agreed_reading_is_a_no_chain_disposition_that_plans_no_chain(self):
        stored = {"chains": [{"branch": 0, "mentions": [{"id": "mention:test:1:0000:0000", "surface_ar": "العائد في هبته"}]}]}
        result = self.run_v3("b1-2c405e", stored)
        self.assertEqual((result["errors"], result["holds"]), ([], []))
        self.assertEqual(result["disposition"], "no_chain_by_reading")
        self.assertEqual(result["planned"], {"chains": []})
        self.assertIn("chain_removed", result["comparison"]["fix_kinds"])

    def test_the_source_named_in_the_text_is_a_row_with_its_kind(self):
        result = self.run_v3("b1-011436", {"chains": []})
        self.assertEqual(result["errors"], [])
        mentions = result["planned"]["chains"][0]["mentions"]
        self.assertEqual([m["reader_kind"] for m in mentions], ["narrator", "narrator", "narrator", "imam_in_text"])
        self.assertIsNone(result["disposition"])

    def test_a_variant_group_holds_the_reading(self):
        result = self.run_v3("b1-244c94", {"chains": []})       # «الأعمش ... جابرا» marked variant beside the route to Jabir
        self.assertIn("has_variant_group", [hold["code"] for hold in result["holds"]])

    def test_a_v3_1_reading_needs_the_v3_1_tool(self):
        result = self.run_v3("b1-011436", {"chains": []}, reader_format="v3_1", tool_version="v3")
        self.assertTrue(result["errors"][0].startswith("tool_version:"))

    def test_inherited_names_repeat_a_rule_checked_chain_or_hold(self):
        cited = ["محمد بن موسى بن المتوكل", "علي بن إبراهيم", "إبراهيم بن هاشم", "محمد بن أبي عمير", "من سمع", "أبا عبد الله الصادق"]
        previous = {"hadith_id": "hadith:test:prev", "chains": [{"chain_id": "chain:test:prev:0000", "branch": 0, "structure_status": "checked_by_rule",
                                                                "mentions": [{"id": f"mention:test:prev:0000:{p:04d}", "position": p, "surface_ar": s,
                                                                              "inherited_from_mention_id": None} for p, s in enumerate(cited)]}]}
        result = self.run_v3("b1-2e0f3a", {"chains": []}, previous={"prev2": previous})
        self.assertEqual(result["holds"], [])
        mentions = result["planned"]["chains"][0]["mentions"]
        self.assertEqual([m["inherited_from_mention_id"] for m in mentions], [f"mention:test:prev:0000:{p:04d}" for p in range(6)])
        self.assertEqual([m["surface_ar"] for m in mentions], cited)
        self.assertTrue(all(m["span"] is None and m["reader_kind"] == "inherited" for m in mentions))
        previous["chains"][0]["structure_status"] = "uncertain"
        held = self.run_v3("b1-2e0f3a", {"chains": []}, previous={"prev2": previous})
        self.assertEqual([hold["code"] for hold in held["holds"]], ["inherited_source_chain_uncertain"])
        self.assertEqual([h["code"] for h in self.run_v3("b1-2e0f3a", {"chains": []})["holds"]], ["inherited_previous_report_unknown"])


class ReplayTest(unittest.TestCase):
    def override(self) -> dict:
        result = EngineTest().run_item(ABU_DAWUD, ABU_DAWUD_READ, evidence=["الليث بن سعد"])
        text = ABU_DAWUD["text"]
        return {"format": replay.OVERRIDES_FORMAT, "hadith_id": ABU_DAWUD["hadith_id"], "record_id": "k6:17633", "fix_id": "chain-fix:t",
                "arabic_sha256": replay.sha256_text(text), "reader_text_sha256": replay.sha256_text(text), "text_layout": "full_text",
                "effect": "replace_routes", "structure_status": "read_by_model", "planned": result["planned"]}

    def old_rows(self) -> tuple[list[list], list[list], list[list]]:
        """The rule-built rows of k6:17633 in the projection's CSV order: «سليمان بن يسار» stands (source index), the rest unresolved."""
        chains, mentions, candidates = [], [], []
        for c in ABU_DAWUD["stored_chains"]:
            chains.append([c["chain_id"], ABU_DAWUD["hadith_id"], c["branch"], len(c["surfaces"]), False, "extract_isnad_unified", None,
                           "0", None, None, "uncertain", "{not_a_name}", None, "narrator:work:abu-dawud", "direct"])
            for p, s in enumerate(c["surfaces"]):
                mention_id = f"{c['chain_id'].replace('chain:', 'mention:', 1)}:{p:04d}"
                stands = s == "سليمان بن يسار"
                mentions.append([mention_id, c["chain_id"], ABU_DAWUD["hadith_id"], p, s, s, None, None, "u", "f",
                                 "person" if stands else "unclassified", "source_index" if stands else "unresolved",
                                 "source_index" if stands else None, "narrator:rawi:7" if stands else None, 1.0 if stands else None,
                                 "source_index_confirmed_by_text" if stands else None,
                                 "Sulayman" if stands else "Bukayr", "identity_name" if stands else "transliteration_table",
                                 "narrator:rawi:7" if stands else None, None, None])
                candidates.append([replay.candidate_id(mention_id, "name_exact", "narrator:rawi:9"), mention_id, ABU_DAWUD["hadith_id"],
                                   "narrator:rawi:9", "name_exact", "tier0", None, None, None])
        return chains, mentions, candidates

    def test_rewrite_follows_the_apply_rule_for_kept_carried_and_new_names(self):
        row = self.override()
        chains, mentions, candidates = self.old_rows()
        counts = Counter()
        new_chains, new_mentions, new_candidates = replay.rewrite_rows(row, chains, mentions, candidates, {}, str, counts)
        self.assertEqual([c[0] for c in new_chains], ["chain:k6:17633:0000", "chain:k6:17633:0001"])
        self.assertEqual(new_chains[0][10:], ["read_by_model", None, "chain-fix:t", "narrator:work:abu-dawud", "direct"])
        first = [m for m in new_mentions if m[1] == "chain:k6:17633:0000"]
        # «سليمان بن يسار» keeps its neighbours: identity carried; «يزيد بن خالد» kept with a new teacher: candidates only;
        # «الليث بن سعد» is new: unresolved, no candidate, no Latin form.
        self.assertEqual(first[3][4], "سليمان بن يسار")
        self.assertEqual(first[3][13], "narrator:rawi:7")
        self.assertEqual((first[0][11], first[0][16]), ("unresolved", "Bukayr"))
        self.assertEqual((first[1][4], first[1][11], first[1][16]), ("الليث بن سعد", "unresolved", None))
        self.assertNotIn(first[1][0], {c[1] for c in new_candidates})
        self.assertIn(replay.candidate_id(first[0][0], "name_exact", "narrator:rawi:9"), {c[0] for c in new_candidates})
        self.assertEqual(counts["mentions_new"], 2)

    def test_a_no_chain_reading_leaves_no_row(self):
        row = {**self.override(), "planned": {"chains": []}, "disposition": "no_chain_by_reading"}
        self.assertEqual(replay.rewrite_rows(row, *self.old_rows(), {}, str, Counter()), ([], [], []))

    def test_an_inherited_name_repeats_its_cited_mention(self):
        row = self.override()
        cited = ["mention:k6:1:0000:0002", "chain:k6:1:0000", "hadith:k6:1", 2, "بكير", "بكير", None, None, "u", "f", "person",
                 "source_index", "source_index", "narrator:rawi:3", 1.0, "source_index_confirmed_by_text", "Bukayr", "identity_name",
                 "narrator:rawi:3", None, None]
        cited_candidate = [replay.candidate_id(cited[0], "source_index_confirmed_by_text", "narrator:rawi:3"), cited[0], "hadith:k6:1",
                           "narrator:rawi:3", "source_index_confirmed_by_text", "full", 2, None, None]
        planned = json.loads(json.dumps(row["planned"]))
        planned["chains"][0]["mentions"][2].update(inherited_from_mention_id=cited[0], kept_mention_id=None, span=None)
        _, new_mentions, new_candidates = replay.rewrite_rows({**row, "planned": planned}, *self.old_rows(),
                                                              {cited[0]: (cited, [cited_candidate])}, str, Counter())
        inherited = new_mentions[2]
        self.assertEqual((inherited[11], inherited[13], inherited[16], inherited[20]), ("unresolved", None, None, cited[0]))
        self.assertIn(replay.candidate_id(inherited[0], "source_index_confirmed_by_text", "narrator:rawi:3"), {c[0] for c in new_candidates})

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
