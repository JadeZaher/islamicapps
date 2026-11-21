"""Table-driven tests for the pure correspondence logic, on real corpus texts (record ids cited per case).

Run from this directory:  python -B -m unittest test_correspondence_logic
"""

import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import diagnostic_common as common  # noqa: E402
import correspondence_logic as logic  # noqa: E402
import matn_isolation as isolation  # noqa: E402

REGEN = common.load_regen()
EXTRACTOR = common.load_extractor()
NORMALIZER = logic.ComparisonNormalizer(REGEN)
ISOLATOR = isolation.MatnIsolator(EXTRACTOR, {}, {})

# Real corpus texts (text_ar, byte-identical).
TEXT = {
    # Sunni, Sahih Bukhari
    "k6:14": "حدثنا أبو اليمان، قال أخبرنا شعيب، قال حدثنا أبو الزناد، عن الأعرج، عن أبي هريرة  رضى الله عنه  أن رسول الله صلى الله عليه وسلم قال ‏\"‏ فوالذي نفسي بيده لا يؤمن أحدكم حتى أكون أحب إليه من والده وولده ‏\"‏‏.‏",
    "k6:15": "حدثنا يعقوب بن إبراهيم، قال حدثنا ابن علية، عن عبد العزيز بن صهيب، عن أنس، عن النبي صلى الله عليه وسلم ح وحدثنا آدم، قال حدثنا شعبة، عن قتادة، عن أنس، قال قال النبي صلى الله عليه وسلم ‏\"‏ لا يؤمن أحدكم حتى أكون أحب إليه من والده وولده والناس أجمعين ‏\"‏‏.‏",
    # Sunni, Jami' al-Tirmidhi
    "k6:24260": "حدثنا علي بن المنذر، - كوفي - حدثنا محمد بن فضيل، قال حدثنا الأعمش، عن عطية، عن أبي سعيد، والأعمش، عن حبيب بن أبي ثابت، عن زيد بن أرقم، رضي الله عنهما قالا قال رسول الله صلى الله عليه وسلم ‏\"‏ إني تارك فيكم ما إن تمسكتم به لن تضلوا بعدي أحدهما أعظم من الآخر كتاب الله حبل ممدود من السماء إلى الأرض وعترتي أهل بيتي ولن يتفرقا حتى يردا على الحوض فانظروا كيف تخلفوني فيهما ‏\"‏ ‏.‏ قال هذا حديث حسن غريب ‏.‏",
    "k6:24181": "حدثنا محمد بن بشار، حدثنا محمد بن جعفر، حدثنا شعبة، عن سلمة بن كهيل، قال سمعت أبا الطفيل، يحدث عن أبي سريحة، أو زيد بن أرقم شك شعبة - عن النبي صلى الله عليه وسلم قال ‏\"‏ من كنت مولاه فعلي مولاه ‏\"‏ ‏.‏ قال أبو عيسى هذا حديث حسن صحيح غريب ‏.‏",
    # Sunni, Musnad Ahmad (Pure Canon: text_ar is the matn only)
    "pure-canon:pc_17898": "إني أوشك أن أدعى فأجيب وإني تارك فيكم الثقلين كتاب الله وعترتي كتاب الله حبل ممدود من السماء إلى الأرض وعترتي أهل بيتي وإن اللطيف الخبير أخبرني أنهما لن يفترقا حتى يردا علي الحوض فانظروا بم تخلفوني فيهما",
    "pure-canon:pc_135": "اتقوا الحديث عني إلا ما علمتم فإنه من كذب علي متعمدا فليتبوأ مقعده من النار",
    # Imami, Al-Khisal
    "thaqalayn:992549055eecb0eafd2196ca": "2-97 حدثنا الحسن بن عبد الله بن سعيد العسكري قال: أخبرنا محمد بن حمدان القشيري قال: أخبرنا المغيرة بن محمد بن المهلب قال: حدثني أبي قال: حدثني عبد الله بن داود، عن فضيل بن مرزوق، عن عطية العوفي، عن أبي سعيد الخدري قال: قال رسول الله صلى الله عليه وآله: إني تارك فيكم أمرين أحدهما أطول من الآخر كتاب الله حبل ممدود من السماء إلى الارض وعترتي، ألا وإنهما لن يفترقا حتى يردا علي الحوضفقلت لابي سعيد: من عترته؟ قال: أهل بيته",
    # Imami, 'Uyun Akhbar al-Rida (vocalized)
    "thaqalayn:45dbeaa0f4efcba3e70c6ee2": "183 - وَبِهذَا الإسناد قالَ: قـالَ رَسُولَ اللَّهِ صَلَّى اللهُعَلَيْـهِ وَآلِـهِ: مَن كُنْت مَوْلاهُ فَعَلِىٌّمَوْلاهُ. اَللَّهُمَّ والَ مَن والاهُ وَعادَ مَن عاداهُ وَانصُر مَن نَصْرَه وَاخْذُلْ مَنْ خَذَلَهُ.",
    # Imami, Al-Kafi: two reports with the same opening chain and different matns
    "thaqalayn:2c632b5bab96ee31ba561142": "2ـ عَلِيُّ بْنُ إِبْرَاهِيمَ عَنْ أَبِيهِ عَنِ ابْنِ أَبِي عُمَيْرٍ عَنْ بَعْضِ أَصْحَابِهِ عَنْ أَبِي عَبْدِ الله (عَلَيْهِ السَّلام) قَالَ إِذَا مَاتَ الْمُؤْمِنُ الْفَقِيهُ ثُلِمَ فِي الاسْلامِ ثُلْمَةٌ لا يَسُدُّهَا شَيْ‏ءٌ.",
    "thaqalayn:fdd84768919cc0213fea4f98": "4ـ عَلِيُّ بْنُ إِبْرَاهِيمَ عَنْ أَبِيهِ عَنِ ابْنِ أَبِي عُمَيْرٍ عَنْ عُمَرَ بْنِ أُذَيْنَةَ عَنْ أَبِي عَبْدِ الله (عَلَيْهِ السَّلام) قَالَ خَلَقَ الله الْمَشِيئَةَ بِنَفْسِهَا ثُمَّ خَلَقَ الاشْيَاءَ بِالْمَشِيئَةِ.",
    # Ibadi, Musnad al-Rabi'
    "openiti:ibadi:rabi_0738|738|V01P190": "أبو عبيدة عن جابر بن زيد عن ابن عباس عن رسول الله صلى الله عليه وسلم قال: «من كذب علي متعمدا فليتبوأ مقعده من النار». مكانا يتخذه في النار.",
}
PURE_CANON = {"pure-canon:pc_17898", "pure-canon:pc_135"}


def matn_of(record_id: str) -> str:
    """The canonical extractor boundary, or the whole text for Pure Canon (matn-only source)."""
    if record_id in PURE_CANON:
        return TEXT[record_id]
    matn, _ = ISOLATOR._extractor_matn(TEXT[record_id])
    return matn


def score_texts(left: str, right: str):
    words_a, words_b = NORMALIZER.words(left), NORMALIZER.words(right)
    score = logic.score_sets(logic.shingle_set(words_a), logic.shingle_set(words_b))
    return score, logic.classify(score, len(words_a), len(words_b))


class ComparisonTextTest(unittest.TestCase):
    def test_normalization_table(self):
        cases = [
            # (input, expected comparison words)
            ("قال رسول الله صلى الله عليه وسلم", ["قال", "رسول", "الله"]),
            ("قَالَ رَسُولُ اللَّهِ ﷺ", ["قال", "رسول", "الله"]),
            ("عن أبي عبد الله (عليه السلام) قال", ["عن", "ابي", "عبد", "الله", "قال"]),
            ("عن أبي عبد الله ع قال", ["عن", "ابي", "عبد", "الله", "قال"]),
            ("عن علي \" ع م \" قال", ["عن", "علي", "قال"]),
            ("قـالَ الله عز وجل", ["قال", "الله"]),
            ("فَسَأَلْتُهُ عَنْ ذَلِکَ <br> فَقَالَ", ["فسالته", "عن", "ذلك", "فقال"]),
            ("رضى الله عنه قال", ["قال"]),
            ("و لكن من النار", ["و", "لكن", "من", "النار"]),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(NORMALIZER.words(text), expected)

    def test_vocalized_and_plain_spellings_share_every_shingle(self):
        plain = "من كنت مولاه فعلي مولاه اللهم وال من والاه وعاد من عاداه"
        vocalized = "مَن كُنْت مَوْلاهُ فَعَلِىٌّ مَوْلاهُ. اَللَّهُمَّ والَ مَن والاهُ وَعادَ مَن عاداهُ"
        self.assertEqual(logic.shingle_set(NORMALIZER.words(plain)), logic.shingle_set(NORMALIZER.words(vocalized)))

    def test_shingles_ignore_word_spacing(self):
        # Thaqalayn often detaches the conjunction: "و لكن" and "ولكن" are the same text.
        self.assertEqual(logic.shingle_set(NORMALIZER.words("و لكن من النار")),
                         logic.shingle_set(NORMALIZER.words("ولكن من النار")))


class MatnBoundaryTest(unittest.TestCase):
    def test_boundary_table(self):
        cases = [
            # (record, matn must start with, matn must not contain)
            ("k6:14", "أن رسول الله", "أبو الزناد"),
            ("k6:15", "قال قال النبي", "قتادة"),                   # after the tahwil, last segment
            ("thaqalayn:992549055eecb0eafd2196ca", "قال: قال رسول الله", "عطية"),
        ]
        for record_id, start, absent in cases:
            with self.subTest(record=record_id):
                matn = matn_of(record_id)
                self.assertTrue(matn.startswith(start), matn[:40])
                self.assertNotIn(absent, matn)


class PairClassificationTest(unittest.TestCase):
    def test_real_pairs_table(self):
        cases = [
            # (record a, record b, allowed classes; None means the pair must NOT be kept)
            ("pure-canon:pc_17898", "k6:24260", {logic.CLASS_VARIANT, logic.CLASS_PARTIAL}),      # Ahmad / Tirmidhi
            ("pure-canon:pc_17898", "thaqalayn:992549055eecb0eafd2196ca",                          # Sunni / Imami
             {logic.CLASS_VARIANT, logic.CLASS_PARTIAL}),
            ("k6:14", "k6:15", {logic.CLASS_SAME_WORDING, logic.CLASS_VARIANT}),                  # two Bukhari tellings
            ("pure-canon:pc_17898", "pure-canon:pc_135", {None}),                                # unrelated reports
            ("thaqalayn:2c632b5bab96ee31ba561142", "thaqalayn:fdd84768919cc0213fea4f98", {None}),  # same chain only
            ("k6:24181", "thaqalayn:45dbeaa0f4efcba3e70c6ee2", {None}),                          # 4-word matn: too short
            ("pure-canon:pc_135", "openiti:ibadi:rabi_0738|738|V01P190",                         # Sunni / Ibadi
             {logic.CLASS_VARIANT, logic.CLASS_PARTIAL}),
        ]
        for left, right, allowed in cases:
            with self.subTest(pair=(left, right)):
                score, pair_class = score_texts(matn_of(left), matn_of(right))
                self.assertIn(pair_class, allowed, f"J={score.jaccard:.2f} C={score.containment:.2f}")

    def test_isolating_the_matn_removes_a_chain_driven_match(self):
        left, right = "thaqalayn:2c632b5bab96ee31ba561142", "thaqalayn:fdd84768919cc0213fea4f98"
        whole, whole_class = score_texts(TEXT[left], TEXT[right])
        isolated, isolated_class = score_texts(matn_of(left), matn_of(right))
        self.assertIsNotNone(whole_class, f"J={whole.jaccard:.2f} C={whole.containment:.2f}")  # the chain alone
        self.assertIsNone(isolated_class)
        self.assertLess(isolated.jaccard, 0.1)

    def test_threshold_table(self):
        # (shared, size a, size b, words a, words b, expected class)
        cases = [
            (90, 100, 100, 20, 20, logic.CLASS_SAME_WORDING),
            (60, 100, 100, 20, 20, logic.CLASS_VARIANT),        # J = 0.43, containment 0.60
            (40, 50, 200, 16, 60, logic.CLASS_PARTIAL),          # J = 0.19, containment 0.80
            (40, 50, 200, 10, 60, None),                         # same overlap, shorter side under 15 words
            (95, 100, 100, 7, 7, None),                          # near-identical but under MIN_WORDS
            (30, 100, 100, 20, 20, None),                        # weak overlap
        ]
        for shared, size_a, size_b, words_a, words_b, expected in cases:
            with self.subTest(case=(shared, size_a, size_b, words_a, words_b)):
                self.assertEqual(logic.classify(logic.PairScore(shared, size_a, size_b), words_a, words_b), expected)


class LocalContainmentTest(unittest.TestCase):
    def test_scattered_shingles_are_not_a_contained_passage(self):
        short = matn_of("pure-canon:pc_135")
        short_words = NORMALIZER.words(short)
        short_sequence = logic.shingle_hashes_at(logic.letters_bytes(short_words))
        unrelated = [NORMALIZER.words(matn_of(k)) for k in ("pure-canon:pc_17898", "k6:24260", "k6:15",
                                                             "thaqalayn:992549055eecb0eafd2196ca")]
        cases = [
            # (name, long text words, minimum local containment, maximum local containment)
            ("passage quoted inside a longer text", unrelated[0] + short_words + unrelated[1], 0.95, 1.0),
            ("only scattered words of it", [w for text in unrelated for w in text] + short_words[::3], 0.0, 0.4),
        ]
        for name, long_words, low, high in cases:
            with self.subTest(case=name):
                long_sequence = logic.shingle_hashes_at(logic.letters_bytes(long_words))
                score = logic.score_sets(set(short_sequence), set(long_sequence), short_sequence, long_sequence)
                self.assertIsNotNone(score.local)
                self.assertGreaterEqual(score.containment, low)
                self.assertLessEqual(score.containment, high)
                self.assertGreaterEqual(score.global_containment, score.containment - 1e-9)

    def test_sliding_window_table(self):
        # (short set, long sequence, short length, expected local containment)
        cases = [
            ({1, 2, 3, 4}, [9, 1, 2, 3, 4, 9, 9, 9, 9, 9], 4, 1.0),            # contiguous
            ({1, 2, 3, 4}, [1, 9, 9, 9, 2, 9, 9, 9, 3, 9, 9, 9, 4], 4, 0.5),  # spread out: two per window of 5
            ({1, 2, 3, 4}, [9, 9, 9], 4, 0.0),
        ]
        for short_set, long_sequence, length, expected in cases:
            with self.subTest(sequence=long_sequence):
                self.assertEqual(logic.local_containment(short_set, long_sequence, length), expected)


class MinHashTest(unittest.TestCase):
    def test_signature_estimates_jaccard_on_a_real_pair(self):
        a = logic.shingle_set(NORMALIZER.words(matn_of("pure-canon:pc_17898")))
        b = logic.shingle_set(NORMALIZER.words(matn_of("k6:24260")))
        exact = logic.score_sets(a, b).jaccard
        sig_a, sig_b = logic.one_permutation_minhash(a), logic.one_permutation_minhash(b)
        estimate = sum(x == y for x, y in zip(sig_a, sig_b)) / logic.OPH_BINS
        self.assertLess(abs(estimate - exact), 0.15)

    def test_identical_sets_share_every_band_and_unrelated_share_none(self):
        a = logic.shingle_set(NORMALIZER.words(TEXT["pure-canon:pc_17898"]))
        c = logic.shingle_set(NORMALIZER.words(TEXT["pure-canon:pc_135"]))
        keys_a = logic.band_keys(logic.one_permutation_minhash(a))
        self.assertEqual(keys_a, logic.band_keys(logic.one_permutation_minhash(list(reversed(a)))))
        self.assertFalse(set(keys_a) & set(logic.band_keys(logic.one_permutation_minhash(c))))

    def test_window_table(self):
        # (word count, expected window starts in words)
        cases = [(5, [0]), (16, [0]), (17, [0, 1]), (24, [0, 8]), (33, [0, 8, 16, 17])]
        for count, starts in cases:
            with self.subTest(words=count):
                words = ["كلمة"] * count
                spans = logic.window_letter_spans(words)
                self.assertEqual([s // 4 for s, _ in spans], starts)


class ClusterGuardTest(unittest.TestCase):
    def test_cluster_table(self):
        S, V, P = logic.CLASS_SAME_WORDING, logic.CLASS_VARIANT, logic.CLASS_PARTIAL
        cases = [
            ("a star: every member linked to the centre",
             [("a", "b", S), ("b", "c", V)], {"a": 10, "b": 10, "c": 10}, [{"a", "b", "c"}]),
            ("a path of strong edges does not chain beyond one hop from a centre",
             [("a", "b", V), ("b", "c", V), ("c", "d", V)], {"a": 10, "b": 10, "c": 10, "d": 10},
             [{"a", "b", "c"}, {"d"}]),
            ("one-to-one containment merges",
             [("short", "long", P)], {"short": 10, "long": 50}, [{"short", "long"}]),
            ("a compound report does not chain two reports together",
             [("x", "compound", P), ("y", "compound", P)], {"x": 10, "y": 10, "compound": 80},
             [{"x"}, {"y"}, {"compound"}]),
            ("a passage held by two unrelated long reports does not join them",
             [("passage", "long1", P), ("passage", "long2", P)], {"passage": 10, "long1": 60, "long2": 70},
             [{"passage"}, {"long1"}, {"long2"}]),
            ("containment of a whole strong cluster still merges one-to-one",
             [("a", "b", S), ("a", "long", P), ("b", "long", P)], {"a": 10, "b": 11, "long": 90},
             [{"a", "b", "long"}]),
        ]
        for name, pairs, lengths, expected in cases:
            with self.subTest(case=name):
                cluster_of, _, _ = logic.build_clusters(pairs, lengths)
                groups = {}
                for item, cluster_id in cluster_of.items():
                    groups.setdefault(cluster_id, set()).add(item)
                self.assertEqual(sorted(map(sorted, groups.values())), sorted(map(sorted, expected)))

    def test_cluster_id_is_order_independent(self):
        self.assertEqual(logic.cluster_identifier(["hadith:b", "hadith:a"]),
                         logic.cluster_identifier(["hadith:a", "hadith:b"]))


if __name__ == "__main__":
    unittest.main()
