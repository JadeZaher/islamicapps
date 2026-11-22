"""Table-driven tests for the chain chronology guard, on lexicon years of real narrators and real K6 chains."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from chain_chronology import Lifespan, contest_chain, seam_blocked_pairs, transmission_chronology  # noqa: E402

# Lexicon (all_rawis.csv) years of the narrators in the chains below.
UMAR = Lifespan(-41, 23)                 # rawi:3 ʿUmar b. al-Khattab
AWZAI = Lifespan(88, 157)                # rawi:20024 al-Awzaʿi
ZUHRI = Lifespan(51, 124)                # al-Zuhri
MAHMUD = Lifespan(None, 247)             # Mahmud b. Khalid
UBAYDULLAH = Lifespan(70, 140)           # rawi:11201 ʿUbaydullah b. ʿUmar b. Hafs
NAFI = Lifespan(30, 119)                 # Nafiʿ
NAKHAI = Lifespan(47, 96)                # Ibrahim al-Nakhaʿi
IBN_MASUD = Lifespan(None, 32)           # Ibn Masʿud
ABD_AL_RAZZAQ = Lifespan(126, 211)
MAMAR = Lifespan(96, 154)
IBN_HIBBAN = Lifespan(47, 121)           # Muhammad b. Yahya b. Hibban (the K6 index's reading of al-Dhuhli)
KHALID = Lifespan(None, 106)             # Khalid b. al-Harith: the lexicon's year is a century early
SHUBA = Lifespan(82, 160)
LONG_GAP = Lifespan(None, 23 + 61)
EDGE_GAP = Lifespan(None, 23 + 60)


class PairRule(unittest.TestCase):
    def test_rule(self):
        cases = [
            # student, teacher, attested, adjacent, expected
            ("teacher born after the student died", UMAR, AWZAI, False, True, "teacher_born_after_student_died"),
            ("student born after the teacher died", AWZAI, UMAR, False, True, "student_born_after_teacher_died"),
            ("only deaths, gap over the bound", Lifespan(None, 23), LONG_GAP, False, True,
             "teacher_died_long_after_student"),
            ("only deaths, gap at the bound", Lifespan(None, 23), EDGE_GAP, False, True, None),
            ("ordinary pair", ABD_AL_RAZZAQ, MAMAR, False, True, None),
            ("no years", Lifespan(), Lifespan(), False, True, None),
            ("the lexicon lists the pair: a date is wrong", KHALID, Lifespan(None, 106 + 80), True, True, None),
            ("born after an ancestor died is not impossible two links up", AWZAI, UMAR, False, False, None),
        ]
        for name, student, teacher, attested, adjacent, expected in cases:
            with self.subTest(name):
                self.assertEqual(transmission_chronology(student, teacher, attested, adjacent), expected)


class Seams(unittest.TestCase):
    def test_blocked_window(self):
        cases = [
            ("hadith:k6:28195 chain 0000: al-Awzaʿi at 2 and 6", ["m", "u", "a", "z", "x", "y", "a", "q"], {2, 3, 4, 5}),
            ("one narrator twice in a row", ["a", "b", "b", "c"], {1}),
            ("no repeat", ["a", "b", "c"], set()),
            ("unidentified names never seam", [None, "b", None, "c"], set()),
        ]
        for name, ids, expected in cases:
            with self.subTest(name):
                self.assertEqual(seam_blocked_pairs(ids), expected)


class Contest(unittest.TestCase):
    def run_chain(self, chain, attested=frozenset()):
        ids = [name for name, _ in chain]
        return contest_chain(ids, {name: life for name, life in chain if life}, attested)

    def test_outcomes(self):
        cases = [
            # hadith:k6:28147 «حدثنا محمود بن خالد حدثنا عمر عن الأوزاعي»: the later ʿUmar read as the Companion. ʿUmar
            # conflicts with al-Awzaʿi and al-Zuhri; al-Awzaʿi only with him.
            ("one name against two members", [("mahmud", MAHMUD), ("umar", UMAR), ("awzai", AWZAI), ("zuhri", ZUHRI)],
             frozenset(), {1}),
            # hadith:k6:10550 chain 0002 «أبي» read as the Companion; the lexicon ties ʿUbaydullah to Nafiʿ.
            ("anchored partner", [("umar", UMAR), ("ubaydullah", UBAYDULLAH), ("nafi", NAFI)],
             frozenset({("ubaydullah", "nafi")}), {0}),
            # Muhammad b. Yahya b. Hibban at position 0 under ʿAbd al-Razzaq, who the lexicon ties to Maʿmar.
            ("anchored teacher, position 0", [("hibban", IBN_HIBBAN), ("razzaq", ABD_AL_RAZZAQ), ("mamar", MAMAR)],
             frozenset({("razzaq", "mamar")}), {0}),
            ("no evidence either way", [("hibban", IBN_HIBBAN), ("razzaq", ABD_AL_RAZZAQ)], frozenset(), {0, 1}),
            # al-Nakhaʿi from Ibn Masʿud: born 15 years after his death, the classic mursal; both identities stand.
            ("irsal", [("nakhai", NAKHAI), ("ibn_masud", IBN_MASUD)], frozenset(), set()),
            ("attested pair with a wrong year", [("khalid", KHALID), ("shuba", SHUBA)], frozenset({("khalid", "shuba")}),
             set()),
            # hadith:k6:28195: al-Awzaʿi repeats (a flattened tahwil); he keeps his identity, ʿUmar does not.
            ("repeated narrator is never withheld",
             [("mahmud", MAHMUD), ("umar", UMAR), ("awzai", AWZAI), ("zuhri", ZUHRI), ("x", None), ("awzai", AWZAI)],
             frozenset(), {1}),
            ("pair across the seam is not contested",
             [("zuhri", ZUHRI), ("umar", UMAR), ("zuhri", ZUHRI)], frozenset(), set()),
        ]
        for name, chain, attested, expected in cases:
            with self.subTest(name):
                self.assertEqual(set(self.run_chain(chain, attested).withheld), expected)

    def test_reason_names_the_years(self):
        result = self.run_chain([("mahmud", MAHMUD), ("umar", UMAR), ("awzai", AWZAI), ("zuhri", ZUHRI)])
        self.assertEqual(result.withheld[1],
                         "chronology: the person named here died in 23 AH, before the next transmitter was born (88 AH)")
        both = self.run_chain([("hibban", IBN_HIBBAN), ("razzaq", ABD_AL_RAZZAQ)])
        self.assertTrue(both.withheld[1].endswith("the chain cannot tell which of the two names is wrong"))
        self.assertEqual((both.decided, both.undecided), (0, 1))


if __name__ == "__main__":
    unittest.main()
