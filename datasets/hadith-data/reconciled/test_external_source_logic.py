"""Table-driven tests for external_source_logic on real rows (hadith-kg, Riwayat, our corpus).

Run from this directory: python -B -m unittest test_external_source_logic
"""

import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import external_source_logic as logic  # noqa: E402
import sidecar_io as io_  # noqa: E402

rc, common = io_.rc, io_.common
sys.path.insert(0, str(io_.RECONCILE_DIR))
from measure_source_index_agreement import classify  # noqa: E402
sys.path.insert(0, str(common.DIAGNOSTICS_DIR / "biography-verification"))
import rijal_sources as rs  # noqa: E402

REGEN = rs.regen()


def comparison_key(text):
    return rc.name_invariant.compute_name_invariant(text, base_normalize=REGEN.narrator_fold_normalize)


# hadith-kg hadith 1 (Sahih al-Bukhari 1): sanad_rawis pos 1..6 with rawis.name / rawis.nickname.
KG_BUKHARI_1 = [
    ("hadith-kg:rawi:4698", ["عبد الله بن الزبير بن عيسى بن عبيد الله بن أسامة بن عبد الله بن حميد بن زهير بن الحارث بن أسد بن عبد العزى",
                             "الحميدي عبد الله بن الزبير"]),
    ("hadith-kg:rawi:3443", ["سفيان بن عيينة بن ميمون", "سفيان بن عيينة الهلالي"]),
    ("hadith-kg:rawi:8272", ["يحيى بن سعيد بن قيس بن عمرو بن سهل بن ثعلبة بن الحارث بن زيد بن ثعلبة بن غنم بن مالك بن النجار",
                             "يحيى بن سعيد الأنصاري"]),
    ("hadith-kg:rawi:6796", ["محمد بن إبراهيم بن الحارث بن خالد بن صخر بن عامر بن كعب بن سعد بن تيم بن مرة",
                             "محمد بن إبراهيم القرشي"]),
    ("hadith-kg:rawi:5719", ["علقمة بن وقاص بن محصن بن كلدة بن عبد ياليل", "علقمة بن وقاص العتواري"]),
    ("hadith-kg:rawi:5913", ["عمر بن الخطاب بن نفيل بن عبد العزى بن رياح بن عبد الله بن قرط بن رزاح بن عدي بن كعب",
                             "عمر بن الخطاب العدوي"]),
]
# Our extraction of k6:1 (same report), as the projection stores it.
OUR_BUKHARI_1 = ["الحميدي عبد الله بن الزبير", "سفيان", "يحيى بن سعيد الأنصاري", "محمد بن إبراهيم التيمي",
                 "علقمة بن وقاص الليثي", "عمر بن الخطاب"]


class MatchSelection(unittest.TestCase):
    def test_select_match(self):
        cases = [  # (whole hits, matn hits, class, candidates)
            (["1"], ["1", "2"], logic.MATCH_WHOLE, ["1"]),
            (["1", "7"], ["3"], logic.MATCH_AMBIGUOUS, ["1", "7"]),     # never falls through to containment
            ([], ["H0889497"], logic.MATCH_MATN, ["H0889497"]),
            ([], ["H1", "H2"], logic.MATCH_AMBIGUOUS, ["H1", "H2"]),
            ([], [], "", []),
        ]
        for whole, matn, expected_class, expected in cases:
            with self.subTest(whole=whole, matn=matn):
                self.assertEqual(logic.select_match(whole, matn), (expected_class, expected))

    def test_reverse_uniqueness_demotes_shared_picks(self):
        decided = logic.enforce_reverse_uniqueness({
            0: (logic.MATCH_WHOLE, ["9"]), 1: (logic.MATCH_MATN, ["9"]),     # two of ours pick hadith-kg 9
            2: (logic.MATCH_WHOLE, ["10"]), 3: (logic.MATCH_AMBIGUOUS, ["4", "5"])})
        self.assertEqual(decided[0][0], logic.MATCH_AMBIGUOUS)
        self.assertEqual(decided[1][2], "external_report_claimed_by_several_of_ours")
        self.assertEqual(decided[2], (logic.MATCH_WHOLE, ["10"], ""))
        self.assertEqual(decided[3][2], "several_external_reports_in_the_same_work")

    def test_work_map_is_one_to_one_per_dataset(self):
        kg = logic.external_books(logic.DATASET_HADITH_KG)
        riwayat = logic.external_books(logic.DATASET_RIWAYAT)
        self.assertEqual(kg[55], "zaydi:musnad-zayd")          # not Sunni, whatever the dataset says
        self.assertEqual(riwayat["مسند الربيع بن حبيب"], "ibadi:musnad-rabi")
        self.assertEqual(riwayat["al-tawhid"], "imami:al-tawhid-saduq")
        self.assertNotIn("tahdhib-al-ahkam", riwayat)            # not in our corpus: never matched


class ExternalNamePlaceholders(unittest.TestCase):
    def test_reasons_on_real_names(self):
        cases = [  # (dataset name as written, reason)
            ("أَبِيهِ", "relational_name"),                                   # Riwayat N0152715 (Thaqalayn label)
            ("عِدَّةٌ مِنْ أَصْحَابِنَا", "collective_or_anonymous_name"),     # Riwayat N0152719
            ("بَعْضِ أَصْحَابِنَا", "collective_or_anonymous_name"),
            ("سُفْيَانُ", "bare_single_token_name"),
            ("أَبِي عَبْدِ اللَّهِ ( عليه السلام )", "kunya_only_name"),        # theophoric kunya is still a kunya
            ("أَبِي عَبْدِ اللَّهِ ع", "kunya_only_name"),                     # Riwayat N0153369: abbreviated formula
            ("الرِّضَا ع", "bare_single_token_name"),
            ("أبو معاوية", "kunya_only_name"),
            ("مُحَمَّدُ بْنُ يَحْيَى الْعَطَّارُ", ""),
            ("ابْنِ مَحْبُوبٍ", ""),                                          # nasab form, a person label
            ("أبو بكر بن أبي شيبة", ""),                                     # kunya with nasab
            ("أبي عبد الله الجدلي", ""),                                     # kunya plus nisba
        ]
        for name, reason in cases:
            with self.subTest(name=name):
                self.assertEqual(logic.external_name_placeholder(rs.name_key(name)), reason)

    def test_basis_and_origin(self):
        cases = [  # (dataset, report class, placeholder, basis)
            ("riwayat", "full_agreement", "", "source_riwayat_confirmed_by_text"),
            ("hadith_kg", "multi_branch_all_source_ids_aligned", "", "source_hadith_kg_confirmed_by_text"),
            ("riwayat", "full_agreement", "kunya_only_name", "source_riwayat"),      # never confirmed by kunya
            ("hadith_kg", "full_agreement", logic.KG_STUB, "source_hadith_kg"),       # name taken from the text
            ("hadith_kg", "same_length_name_mismatch", "", "source_hadith_kg"),
            ("hadith_kg", "length_differs_text_longer", "", "source_hadith_kg"),
        ]
        for dataset, report_class, reason, basis in cases:
            with self.subTest(dataset=dataset, report_class=report_class, reason=reason):
                self.assertEqual(logic.mention_basis(dataset, report_class, reason), basis)
        for method, origin in (("source_annotation_thaqalayn", "upstream_annotation"),
                               ("thaqalayn_id_on_reparsed_span", "upstream_annotation"),
                               ("source_annotation_kg", "upstream_annotation"), ("manual_gold", "riwayat_manual_gold"),
                               ("ranker2", "riwayat_automatic_linking"), ("joint_unique", "riwayat_automatic_linking"),
                               ("claude_label", "riwayat_automatic_linking")):
            with self.subTest(method=method):
                self.assertEqual(logic.riwayat_id_origin(method), origin)


class Alignment(unittest.TestCase):
    """The K6 classify, run unchanged on external ids through the name-only stand-in registry."""

    def setUp(self):
        self.names = logic.ExternalNames(comparison_key, dict(KG_BUKHARI_1))
        self.ids = [external_id for external_id, _ in KG_BUKHARI_1]

    def test_same_report_same_order_is_corroborated(self):
        label, tiers, pairs = classify(self.names, self.ids, [OUR_BUKHARI_1])
        self.assertEqual(label, "full_agreement")
        self.assertEqual(len(pairs), 6)
        self.assertIn(tiers[1], rc.CORROBORATED)     # bare سفيان is consistent with سفيان بن عيينة as written

    def test_must_not_corroborate(self):
        cases = [  # (our branch, expected class)
            (OUR_BUKHARI_1[:2] + ["شعبة"] + OUR_BUKHARI_1[3:], "same_length_name_mismatch"),  # another person named
            (list(reversed(OUR_BUKHARI_1)), "same_length_name_mismatch"),                     # order reversed
            (OUR_BUKHARI_1[:5], "length_differs_source_longer"),
            (["أبيه"] + OUR_BUKHARI_1[1:], "same_length_name_mismatch"),   # relational: no parent links, never attested
        ]
        for branch, expected in cases:
            with self.subTest(branch=branch[:3]):
                label, _, _ = classify(self.names, self.ids, [branch])
                self.assertEqual(label, expected)

    def test_unknown_external_position_never_corroborates(self):
        ids = self.ids[:2] + ["riwayat-unidentified:H0:1:3"] + self.ids[3:]
        label, tiers, _ = classify(self.names, ids, [OUR_BUKHARI_1])
        self.assertEqual(label, "same_length_name_mismatch")
        self.assertEqual(tiers[2], "source_id_not_in_registry")


class LexiconLinks(unittest.TestCase):
    def test_link_decision(self):
        cases = [  # (name unique, Sunni context, year agrees, K6 agrees, year conflicts, basis)
            (True, True, True, False, False, logic.LINK_YEAR),
            (True, True, False, True, False, logic.LINK_K6),
            (True, True, True, True, False, logic.LINK_BOTH),
            (True, True, False, True, True, logic.LINK_K6),       # K6 positions outweigh a conflicting lexicon year
            # must NOT link
            (True, True, False, False, False, ""),                 # unique name alone
            (False, True, True, True, False, ""),                  # name held by several narrators
            (True, False, True, False, False, ""),                 # Imami-only narrator (e.g. Riwayat N0153303)
            (True, True, False, False, True, ""),                  # death years disagree, nothing else
        ]
        for name_unique, sunni, year, k6, conflict, expected in cases:
            with self.subTest(case=(name_unique, sunni, year, k6, conflict)):
                self.assertEqual(logic.link_decision(name_unique, sunni, year, k6, conflict), expected)

    def test_years_and_k6_majority(self):
        cases = [((217, 217, 216, 218), True), ((None, None, 100, 100), False), ((None, 130, 121, 130), True),
                 ((104, 104, 103, 103), False)]
        for args, expected in cases:
            with self.subTest(args=args):
                self.assertEqual(logic.years_overlap(*args), expected)
        for args, expected in (((3, 4, 5), True), ((1, 1, 1), True), ((1, 3, 1), False), ((2, 2, 5), False),
                               ((0, 0, 0), False)):
            with self.subTest(args=args):
                self.assertEqual(logic.k6_agrees(*args), expected)


class QuranSpans(unittest.TestCase):
    def test_parse_real_hadith_kg_spans(self):
        cases = [  # (hadith-kg span text, [(sura number, from, to)], quote starts with)
            ("اقْرَأْ بِاسْمِ رَبِّكَ الَّذِي خَلَقَ { 1 } خَلَقَ الإِنْسَانَ مِنْ عَلَقٍ { 2 } اقْرَأْ وَرَبُّكَ الأَكْرَمُ { 3 } "
             "سورة العلق آية 1-3", [(96, 1, 3)], "اقْرَأْ"),                                       # hadith-kg 3, seq 0
            ("لا تُحَرِّكْ بِهِ لِسَانَكَ لِتَعْجَلَ بِهِ سورة القيامة آية 16", [(75, 16, 16)], "لا تُحَرِّكْ"),  # 4, seq 0
            ("إِلَى قَوْلِهِ غَفُورًا رَحِيمًا سورة النساء آية 106 ـ 110", [(4, 106, 110)], "إِلَى"),
            ("قُلْ هُوَ اللَّهُ أَحَدٌ سورة آل عِمْرَانَ آية 1", [(3, 1, 1)], "قُلْ"),
            ("نص بلا مرجع", [], "نص"),
        ]
        for span, refs, head in cases:
            with self.subTest(span=span[:20]):
                quote, references = logic.parse_quran_span(span)
                self.assertEqual([(r["sura_number"], r["aya_from"], r["aya_to"]) for r in references], refs)
                self.assertTrue(quote.startswith(head))
                self.assertNotIn("سورة", quote)

    def test_labels_are_removed_before_text_comparison(self):
        # hadith-kg 4 (Bukhari 5) carries an inline label; our K6 text of the same report does not.
        theirs = "قَالَ : فِي قَوْلِهِ تَعَالَى : لا تُحَرِّكْ بِهِ لِسَانَكَ لِتَعْجَلَ بِهِ سورة القيامة آية 16 ، قَالَ"
        ours = "قال في قوله تعالى لا تحرك به لسانك لتعجل به قال"
        normalize = REGEN.narrator_normalize
        self.assertNotEqual(logic.skeleton_words(normalize(theirs))[0], logic.skeleton_words(normalize(ours))[0])
        self.assertEqual(logic.skeleton_words(normalize(logic.strip_quran_labels(theirs)))[0],
                         logic.skeleton_words(normalize(ours))[0])
        # a sura named in the hadith itself is not a label (no `آية <number>` follows)
        self.assertEqual(logic.strip_quran_labels("من قرأ سورة البقرة في ليلة"), "من قرأ سورة البقرة في ليلة")

    def test_relocation(self):
        ours = "قَالَ اللَّهُ تَعَالَى : لَا تُحَرِّكْ بِهِ لِسَانَكَ لِتَعْجَلَ بِهِ ، قَالَ"
        letters, origins, starts, ends = logic.letters_with_origins(ours, REGEN.narrator_normalize)
        whole, _ = logic.skeleton_words(REGEN.narrator_normalize(ours))
        self.assertEqual(letters, whole)
        needle, _ = logic.skeleton_words(REGEN.narrator_normalize("لا تُحَرِّكْ بِهِ لِسَانَكَ لِتَعْجَلَ بِهِ"))
        hit = logic.relocate_unique(needle, letters, starts, ends)
        begin, end = logic.original_span(ours, origins, hit, len(needle))
        self.assertEqual(ours[begin:end], "لَا تُحَرِّكْ بِهِ لِسَانَكَ لِتَعْجَلَ بِهِ")
        cases = [  # must NOT relocate
            ("لسان", "inside a longer word"),
            ("قال", "repeated"),
            ("ولا تحرك", "absent"),
        ]
        for text, why in cases:
            with self.subTest(why=why):
                probe, _ = logic.skeleton_words(REGEN.narrator_normalize(text))
                self.assertIsNone(logic.relocate_unique(probe, letters, starts, ends))


if __name__ == "__main__":
    unittest.main()
