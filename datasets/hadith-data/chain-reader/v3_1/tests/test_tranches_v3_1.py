"""Tranche planning, jobs and the judge draw on a synthetic population (no database).

    python -B -X utf8 -m unittest discover -s v3_1/tests -p "test_tranches_v3_1.py"        (from chain-reader/)
"""

from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
V31 = Path(__file__).resolve().parent.parent
ROOT = V31.parent
TRANCHES = ROOT / "tranches"
sys.path.insert(0, str(TRANCHES))

import build_tranches  # noqa: E402
import draw_judge_sample  # noqa: E402

WORKS = {"sunni:bukhari": 700, "sunni:muslim": 900, "sunni:nasai": 300, "imami:man-la-yahduruhu-al-faqih": 400, "imami:uyun-akhbar-al-rida": 120, "imami:al-khisal": 80, "imami:al-kafi": 500, "sunni:ahmad": 200}


def population() -> list[dict]:
    return [{"hadith_id": f"hadith:{work}:{n}", "work": work, "uncertain_chains": 1, "reader_chars": 400, "opening": None} for work, count in WORKS.items() for n in range(count)]


class Plan(unittest.TestCase):
    def setUp(self):
        self.pop = population()
        self.excluded = {r["hadith_id"] for r in self.pop[:50]}                   # «batch 001»
        self.forced = {r["hadith_id"] for r in self.pop[:10]}                      # the re-read reports
        self.tranches, self.plan = build_tranches.plan_tranches(self.pop, self.forced, self.excluded, 7, 1000, 20)

    def test_scope_exclusion_and_forced_reports(self):
        placed = [r["hadith_id"] for t in self.tranches for r in t]
        self.assertEqual(len(placed), len(set(placed)))
        self.assertTrue(all(r["work"] not in ("imami:al-kafi", "sunni:ahmad") for t in self.tranches for r in t), "al-Kafi and the other Sunni works are outside the three groups")
        self.assertEqual(len(placed), 700 + 900 + 300 + 400 + 120 + 80 - (50 - 10))           # 40 excluded, 10 forced back in
        self.assertTrue(self.forced <= {r["hadith_id"] for r in self.tranches[0]}, "forced reports go to tranche 01")
        self.assertFalse((self.excluded - self.forced) & set(placed))

    def test_sizes_are_whole_packets_and_every_tranche_mirrors_the_population(self):
        sizes = [len(t) for t in self.tranches]
        self.assertEqual(sizes, self.plan["sizes"])
        self.assertTrue(all(s % 20 == 0 for s in sizes[:-1]))
        total = Counter(r["work"] for t in self.tranches for r in t)
        for tranche in self.tranches:
            counts = Counter(r["work"] for r in tranche)
            for work, all_count in total.items():
                expected = all_count * len(tranche) / sum(sizes)
                self.assertLessEqual(abs(counts[work] - expected), 1.01 + (10 if work == "sunni:bukhari" and tranche is self.tranches[0] else 0), (work, counts[work], expected))        # the 10 forced reports are Bukhari

    def test_opaque_ids_are_unique_across_tranches_and_carry_only_the_tranche(self):
        salt, named = build_tranches.opaque_ids(self.tranches, 7)
        ids = [opaque for t in named for opaque, _ in t]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(i.startswith("t") and len(i) == 10 for i in ids))
        self.assertEqual({opaque[:3] for opaque, _ in named[0]}, {"t01"})


class Jobs(unittest.TestCase):
    def test_pairings_cover_every_packet_once_per_pass_and_shift_pass_b(self):
        for count in (1, 2, 49, 50):
            pairs = build_tranches.pairings(count)
            for label in "ab":
                flat = [n for pair in pairs[label] for n in pair]
                self.assertEqual(flat, [f"{n:03d}" for n in range(1, count + 1)])
                self.assertTrue(all(1 <= len(pair) <= 2 for pair in pairs[label]))
            if count > 2:
                self.assertNotEqual(pairs["a"][0], pairs["b"][0])
                self.assertEqual(len(pairs["b"][0]), 1)

    def test_instruction_names_the_prompt_the_packets_the_output_and_the_run_line(self):
        prompt = {"path": "C:\\p\\prompt-v3_1.md", "version": "3.1.0", "sha256": "a" * 64}
        text = build_tranches.instruction(prompt, ["C:\\t\\packet-001.jsonl", "C:\\t\\packet-002.jsonl"], "C:\\t\\outputs\\pass-a", "C:\\t\\outputs\\pass-a\\RUN.txt", "t01-a-001-002", ["001", "002"])
        for fragment in ("C:\\p\\prompt-v3_1.md", "version 3.1.0, sha256 " + "a" * 64, "two packet files", "C:\\t\\packet-002.jsonl", "C:\\t\\outputs\\pass-a\\<id>.json",
                         "run_id=t01-a-001-002 | packets=001,002 | model=<model id> | start=<UTC start> | end=<UTC end> | files=<number of files you wrote>", "Never skip an id"):
            self.assertIn(fragment, text)
        one = build_tranches.instruction(prompt, ["C:\\t\\packet-001.jsonl"], "C:\\t\\o", "C:\\t\\o\\RUN.txt", "t01-b-001", ["001"])
        self.assertIn("one packet file", one)


class JudgeDraw(unittest.TestCase):
    def test_seeded_stratified_and_reproducible(self):
        eligible = {"sunni_six_books": [f"t01-s{n}" for n in range(550)], "imami_faqih": [f"t01-f{n}" for n in range(230)], "imami_other_not_kafi": [f"t01-o{n}" for n in range(3)]}
        first = draw_judge_sample.draw(eligible, 100, 20261201)
        self.assertEqual(first, draw_judge_sample.draw(eligible, 100, 20261201))
        self.assertNotEqual(first, draw_judge_sample.draw(eligible, 100, 20261202))
        self.assertEqual({g: len(v) for g, v in first.items()}, {"sunni_six_books": 70, "imami_faqih": 29, "imami_other_not_kafi": 1})
        self.assertEqual(sum(len(v) for v in draw_judge_sample.draw({"sunni_six_books": ["a", "b"], "imami_faqih": [], "imami_other_not_kafi": []}, 100, 1).values()), 2, "fewer eligible than asked: all of them")

    def test_cli_reads_a_tranche_and_writes_the_judge_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            tdir = Path(tmp) / "tranche-02"
            (tdir / "triage" / "readings").mkdir(parents=True)
            (tdir / "private").mkdir()
            ids = {f"t02-{n:06d}": {"hadith_id": f"hadith:{n}", "work": "sunni:muslim" if n % 3 else "imami:man-la-yahduruhu-al-faqih", "stratum": "sunni_six_books" if n % 3 else "imami_faqih"} for n in range(60)}
            (tdir / "private" / "id_map.json").write_text(json.dumps({"ids": ids}), encoding="utf-8")
            (tdir / "private" / "reports.jsonl").write_text("\n".join(json.dumps({"id": i, "text": "نص", "stored_chains": [{"surfaces": ["مخزن"]}], "previous_reports": []}, ensure_ascii=False) for i in ids) + "\n", encoding="utf-8")
            rows = ["id\tpacket\twork\tvalid_a\tvalid_b\tagree\tflag\tholds\teligible\tapplies\tproblems"]
            for n, i in enumerate(ids):
                rows.append(f"{i}\tpacket-001.jsonl\t{ids[i]['work']}\tTrue\tTrue\tTrue\t\t\t{n % 5 != 0}\t{'chain' if n % 5 else ''}\t{{}}")
                (tdir / "triage" / "readings" / f"{i}.json").write_text(json.dumps({"expanded_a": {"routes": [{"links": [{"surface": "راو", "kind": "narrator"}]}]}}, ensure_ascii=False), encoding="utf-8")
            (tdir / "triage" / "triage.tsv").write_text("\n".join(rows) + "\n", encoding="utf-8")
            original = draw_judge_sample.HERE
            draw_judge_sample.HERE = Path(tmp)
            try:
                draw_judge_sample.main(["--tranche", "02", "--n", "20"])
            finally:
                draw_judge_sample.HERE = original
            with (tdir / "judge" / "sample.tsv").open(encoding="utf-8") as handle:
                sample = list(csv.DictReader(handle, delimiter="\t"))
            self.assertEqual(len(sample), 20)
            self.assertTrue(all(ids[r["id"]]["stratum"] == r["group"] and r["applies"] == "chain" for r in sample), "only eligible readings are drawn")
            self.assertEqual(json.loads((tdir / "judge" / "draw.json").read_text(encoding="utf-8"))["seed"], 20261202)


if __name__ == "__main__":
    unittest.main()
