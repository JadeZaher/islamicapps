"""Table-driven tests for the v2 pure logic, on real corpus texts (record ids cited per case).

Run from this directory:  python -B -m unittest test_correspondence_logic_v2
"""

import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import correspondence_logic_v2 as logic2  # noqa: E402
import correspondence_logic as v1  # noqa: E402
import matn_isolation as isolation  # noqa: E402
import test_correspondence_logic as v1_tests  # noqa: E402  (its real raw texts and normalizer)

TEXT = v1_tests.TEXT
ISOLATOR = v1_tests.ISOLATOR
NORMALIZER = v1_tests.NORMALIZER
RULES = logic2.CompilerRules()

# Comparison-form texts (the normalizer's output) of real reports.
COMPARISON = {
    "pure-canon:pc_86099": "من تعار من الليل فقال لا اله الا الله وحده لا شريك له له الملك وله الحمد وهو علي كل شيء قدير سبحان الله والحمد لله والله اكبر ولا حول ولا قوة الا بالله ثم قال رب اغفر لي او قال ثم دعا استجيب له فان عزم فتوضا ثم صلي تقبلت صلاته",
    "k6:1123": "النبي قال من تعار من الليل فقال لا اله الا الله وحده لا شريك له له الملك وله الحمد وهو علي كل شيء قدير الحمد لله وسبحان الله ولا اله الا الله والله اكبر ولا حول ولا قوة الا بالله ثم قال اللهم اغفر لي او دعا استجيب فان توضا وصلي قبلت صلاته",
    "pure-canon:pc_88101": "من قال لا اله الا الله وحده لا شريك له له الملك وله الحمد وهو علي كل شيء قدير او منح منحة او هدي زقاقا كان كمن اعتق رقبة",
    "pure-canon:pc_71103": "لا ضرر ولا ضرار",                       # Musnad al-Shafi'i
    "pure-canon:pc_73747": "لا ضرر ولا ضرار",                       # Muwatta' Malik
    "thaqalayn:62bf1020746c9022820d1258": "قال قضي رسول الله بالشفعة بين الشركاء في الارضين والمساكن وقال لا ضرر ولا ضرار وقال اذا رفت الارف وحدت الحدود فلا شفعة",
    "pure-canon:pc_2343": "اليمين علي المدعي عليه",                # Musnad al-Shafi'i
    "thaqalayn:2ddf468a7120c956f4341167": "قال سالته عن ليلة القدر فقال التمسها في ليلة احدي وعشرين او ليلة ثلاث وعشرين",
    "night_23": "ليلة ثلاث وعشرين",                                   # Musnad Ahmad, 3 words
    "muslim_referential_a": "عن النبي بمثله",                         # Sahih Muslim, 3 words, points at another report
    "muslim_referential_b": "عن النبي بمثله",
}
TAHLIL = "لا اله الا الله وحده لا شريك له له الملك وله الحمد وهو علي كل شيء قدير"


class Ids:
    """Word ids shared by a test's reports, as the build's vocabulary does."""

    def __init__(self):
        self.ids = {}

    def __call__(self, word):
        return self.ids.setdefault(word, len(self.ids))


def prepare(text, ids, frequent=frozenset(), anchor=None):
    words = text.split()
    flags = logic2.formula_flags([ids(w) for w in words], set(frequent), set()) if len(words) >= logic2.GRAM_WORDS else None
    prepared = logic2.prepare(words, flags)
    if anchor is not None:
        prepared.anchor_documents = anchor
    return prepared


class CompilerCutTests(unittest.TestCase):
    def isolate(self, key):
        matn, *_ = ISOLATOR.isolate({"record_id": key, "text_ar": TEXT[key], "matn_ar": ""})
        return matn

    def test_remarks_are_cut_for_comparison_only(self):
        cases = [  # (record, work, remark that must be gone, wording that must stay)
            ("k6:24181", "Jami' al-Tirmidhi", "أبو عيسى", "من كنت مولاه فعلي مولاه"),   # قال أبو عيسى هذا حديث حسن صحيح غريب
            ("k6:24260", "Jami' al-Tirmidhi", "حسن غريب", "كتاب الله حبل ممدود"),       # قال هذا حديث حسن غريب (no Abu Isa)
        ]
        for key, work, gone, stays in cases:
            with self.subTest(key=key):
                matn = self.isolate(key)
                text, was_cut = RULES.cut(matn, work)
                self.assertTrue(was_cut)
                self.assertNotIn(gone, text)
                self.assertIn(stays, text)
                self.assertLess(len(text), len(matn))

    def test_other_works_and_remark_free_texts_are_untouched(self):
        for key, work in (("k6:14", "Sahih Bukhari"), ("pure-canon:pc_135", "Musnad Ahmad"),
                          ("thaqalayn:2c632b5bab96ee31ba561142", "Al-Kafi")):
            with self.subTest(key=key):
                matn = self.isolate(key)
                self.assertEqual(RULES.cut(matn, work), (matn, False))

    def test_a_shared_remark_no_longer_links_two_different_reports(self):
        # Tirmidhi's Ghadir report and Thaqalayn report both end with a grade sentence ("هذا حديث حسن ... غريب").
        ghadir, thaqalayn = self.isolate("k6:24181"), self.isolate("k6:24260")
        shared = {}
        for label, cutting in (("uncut", False), ("cut", True)):
            words = []
            for matn in (ghadir, thaqalayn):
                text = RULES.cut(matn, "Jami' al-Tirmidhi")[0] if cutting else matn
                words.append(set(v1.shingle_hashes_at(v1.letters_bytes(NORMALIZER.words(text)))))
            shared[label] = len(words[0] & words[1])
        self.assertGreater(shared["uncut"], shared["cut"])


class FormulaTests(unittest.TestCase):
    def test_flags_cover_the_tahlil_and_only_the_tahlil(self):
        ids = Ids()
        frequent = set(logic2.gram_keys([ids(w) for w in TAHLIL.split()], logic2.GRAM_WORDS))
        words = COMPARISON["pure-canon:pc_88101"].split()
        flags = logic2.formula_flags([ids(w) for w in words], frequent, set())
        self.assertEqual(" ".join(w for w, f in zip(words, flags) if f), TAHLIL)
        self.assertEqual(" ".join(logic2.residual_words(words, flags)), "من قال او منح منحة او هدي زقاقا كان كمن اعتق رقبة")

    def test_gram_counter_confirms_only_grams_over_the_threshold(self):
        ids = Ids()
        documents = [[ids(w) for w in text.split()] for text in (
            COMPARISON["pure-canon:pc_88101"], COMPARISON["k6:1123"], COMPARISON["pure-canon:pc_86099"],
            COMPARISON["pure-canon:pc_71103"])]
        counter = logic2.GramCounter()
        for document in documents:
            counter.first_pass(logic2.gram_keys(document, 4))
        for document in documents:
            counter.second_pass(logic2.gram_keys(document, 4), 3)
        tahlil_keys = set(logic2.gram_keys([ids(w) for w in TAHLIL.split()], 4))
        self.assertTrue(tahlil_keys <= counter.frequent())     # in 3 of the 4 reports
        self.assertFalse(set(logic2.gram_keys([ids(w) for w in "لا ضرر ولا ضرار".split()], 4)) & counter.frequent())


class VerdictTests(unittest.TestCase):
    def verdict(self, key_a, key_b, anchor_short=None, with_inventory=True):
        ids = Ids()
        frequent = set(logic2.gram_keys([ids(w) for w in TAHLIL.split()], logic2.GRAM_WORDS)) if with_inventory else set()
        a, b = (prepare(COMPARISON[key], ids, frequent) for key in (key_a, key_b))
        if anchor_short is not None:
            (a if len(a.words) <= len(b.words) else b).anchor_documents = anchor_short
        result = logic2.compare(a, b)
        return result.pair_class if result else None

    def test_pairs(self):
        rows = [  # (case, key a, key b, anchor of the short side, expected class)
            ("same hadith, tahlil inside (Ahmad / Bukhari)", "pure-canon:pc_86099", "k6:1123", None, logic2.CLASS_VARIANT),
            ("only the tahlil is shared: not a telling", "pure-canon:pc_88101", "k6:1123", None, logic2.CLASS_FORMULA_ONLY),
            ("the same two reports without an inventory pass the v1 rules", "pure-canon:pc_88101", "k6:1123", "no_inventory", logic2.CLASS_VARIANT),
            ("لا ضرر ولا ضرار in Shafi'i and Malik", "pure-canon:pc_71103", "pure-canon:pc_73747", None, logic2.CLASS_SHORT_SAME_WORDING),
            ("لا ضرر ولا ضرار quoted in a Kafi report", "pure-canon:pc_71103", "thaqalayn:62bf1020746c9022820d1258", 13, logic2.CLASS_QUOTED),
            ("the same saying with no distinctive anchor is not quoted", "pure-canon:pc_71103", "thaqalayn:62bf1020746c9022820d1258", None, None),
            ("two different short sayings", "pure-canon:pc_71103", "pure-canon:pc_2343", None, None),
            ("two referential Muslim reports (عن النبي بمثله)", "muslim_referential_a", "muslim_referential_b", 5, None),
            ("a common 3-word phrase inside a longer report (anchor 250)", "night_23", "thaqalayn:2ddf468a7120c956f4341167", 250, None),
            ("the same phrase when its anchor is distinctive", "night_23", "thaqalayn:2ddf468a7120c956f4341167", 13, logic2.CLASS_QUOTED),
        ]
        for case, key_a, key_b, anchor, expected in rows:
            with self.subTest(case=case):
                inventory = anchor != "no_inventory"
                anchor_value = anchor if isinstance(anchor, int) else None
                self.assertEqual(self.verdict(key_a, key_b, anchor_value, inventory), expected)

    def test_real_raw_texts_with_the_same_chain_do_not_match(self):
        # Two Kafi reports with the same opening chain and different matns (v1 isolation test), through the v2 comparison.
        ids = Ids()
        matns = []
        for key in ("thaqalayn:2c632b5bab96ee31ba561142", "thaqalayn:fdd84768919cc0213fea4f98"):
            matn, *_ = ISOLATOR.isolate({"record_id": key, "text_ar": TEXT[key], "matn_ar": ""})
            matns.append(prepare(" ".join(NORMALIZER.words(matn)), ids))
        self.assertIsNone(logic2.compare(*matns))


if __name__ == "__main__":
    unittest.main()
