"""Table-driven tests on real rijal passages (al-Najashi, al-Tusi, al-Kashshi, Taqrib, Tahdhib al-Kamal).

Run from this directory: python -B -m unittest test_rijal_extract
"""

import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import rijal_extract as rx  # noqa: E402

# (passage as printed, expected verdicts on the subject [(term_id, term as written)], expected flagged terms)
TERM_CASES = [
    # al-Najashi no. 200: the author's own words
    ("أحمد بن الحسين بن عمر بن يزيد الصيقل أبو جعفر كوفي، ثقة، من أصحابنا، جده عمر بن يزيد بياع السابري، روى عن "
     "أبي عبد الله وأبى الحسن عليهما السلام.", [("thiqa", "ثقة"), ("min_ashabina", "من أصحابنا")], []),
    # negation: must NOT yield thiqa
    ("فلان كوفي، ليس بثقة، له كتاب.", [], [("thiqa", "negated")]),
    # hearsay across a colon: 'يقال: إنه كان فطحيا' is reported, not al-Najashi's own; the later ثقة is his
    ("عكرمة بن ربعي الفياض أبو الحسين، وقيل أبو عبد الله يقال: إنه كان فطحيا، ثقة.",
     [("thiqa", "ثقة")], [("fathi", "hearsay_or_reported")]),
    # al-Najashi on al-Husayn b. Abi Sa'id: the father is described, then the subject
    ("وأبوه وجهين في الواقفة، وكان الحسين ثقة في حديثه", [("thiqa_fi_al_hadith", "ثقة في حديثه")], []),
    # a brother: subject may differ
    ("وأخوه أحمد ثقة، روى عنه أحمد بن محمد بن عيسى.", [], [("thiqa", "subject_may_differ")]),
    # 'عدة من أصحابنا' in a route names transmitters, never a description
    ("له كتاب، أخبرنا به عدة من أصحابنا، عن أبي المفضل، عن ابن بطة.", [], []),
    # al-Najashi: 'ليس بذاك' is its own jarh phrase
    ("قال أبو العباس: ليس بذاك.", [("laysa_bi_dhaka", "ليس بذاك")], []),
    # 'بثقة' with no negator is not a term use
    ("حدثني بثقة من أهل البصرة.", [], []),
    # al-Tusi, Rijal: one-word entries
    ("واقفي.", [("waqifi", "واقفي")], []),
]


class TermTests(unittest.TestCase):
    def test_terms_table(self):
        for passage, verdicts, flagged in TERM_CASES:
            with self.subTest(passage=passage[:40]):
                rows = rx.find_terms(passage, "test")
                on_subject = [(r["term_id"], r["term_verbatim"]) for r in rows if r["is_verdict_on_subject"]]
                self.assertEqual(on_subject, verdicts)
                off = [(r["term_id"], flag) for r in rows if not r["is_verdict_on_subject"] for flag in r["flags"]
                       if flag in ("negated", "hearsay_or_reported", "subject_may_differ")]
                self.assertEqual(off, flagged)

    def test_route_span_skips_terms_inside_routes(self):
        text = "ثقة. له كتاب، أخبرنا به جماعة عن رجل ثقة عنه."
        rows = rx.find_terms(text, "test", skip_spans=tuple(rx.route_spans(text)))
        self.assertEqual([r["term_verbatim"] for r in rows], ["ثقة"])

    def test_verbatim_keeps_source_letters(self):
        text = "الحسين بن أبي سعيد، ثِقَةٌ، من أصحابنا"
        rows = rx.find_terms(text, "test")
        self.assertEqual(rows[0]["term_verbatim"], "ثِقَةٌ")

    def test_fold_with_offsets_matches_phrase_fold(self):
        for text in ("أَبِي عَبْدِ اللَّهِ جَعْفَرِ بْنِ مُحَمَّدٍ عَلَيْهِمَا السَّلَامُ", "أبی جعفر ع", "  إبراهيم  بن  هاشم "):
            self.assertEqual(rx.fold_with_offsets(text)[0], rx.phrase_fold(text))


class ImamTests(unittest.TestCase):
    CASES = [  # surface, at chain end, rijal clause, expected imams or None
        ("أبي عبد الله", False, False, None),  # an ordinary kunya mid-chain
        ("أبي عبد الله", True, False, ["husayn", "sadiq"]),
        ("أبی عبد الله ع", False, False, ["husayn", "sadiq"]),
        ("أبي الحسن الرضا عليه السلام", False, False, ["rida"]),
        ("أَبِي عَبْدِ اللَّهِ جَعْفَرِ بْنِ مُحَمَّدٍ عَلَيْهِمَا السَّلَامُ", False, False, ["sadiq"]),
        ("أمير المؤمنين", False, False, ["ali"]),
        ("علي", True, False, None),  # too common to read as the Imam without a marker
        ("علي بن محمد", True, False, None),
        ("أبي بصير", True, False, None),
        ("أبي جعفر", False, True, ["baqir", "jawad"]),
    ]

    def test_imam_readings(self):
        for surface, end, clause, expected in self.CASES:
            with self.subTest(surface=surface, end=end):
                reading = rx.imam_reading(surface, at_chain_end=end, rijal_clause=clause)
                self.assertEqual(reading["imams"] if reading else None, expected)

    def test_tusi_sections(self):
        for heading, imam in (("أصحاب أبي عبد الله جعفر بن محمد الصادق عليهما السلام", "sadiq"),
                              ("أصحاب أبي الحسن الثاني علي بن موسى الرضا عليهما السلام", "rida"),
                              ("أصحاب أبي جعفر محمد بن علي الثاني عليهما السلام", "jawad"),
                              ("باب ذكر أسماء من لم يرو عن واحد من الأئمة عليهم السلام", "none")):
            self.assertEqual(rx.tusi_section_imam(heading), imam)


class PeopleAndBooksTests(unittest.TestCase):
    def test_route_student_from_pronoun(self):
        # al-Najashi no. 200
        people = rx.named_people("له كتب لا يعرف منها إلا النوادر قرأته أنا وأحمد بن الحسين رحمه الله على أبيه، عن "
                                 "أحمد بن محمد بن يحيى قال: حدثنا أبي، عن محمد بن أحمد بن يحيى عنه.")
        self.assertEqual(people["route_students"], ["محمد بن احمد بن يحيي"])

    def test_route_student_when_route_ends_in_subject(self):
        # al-Tusi, Fihrist [200]: the route ends 'عن جده الحسن بن راشد'
        people = rx.named_people("له كتاب الراهب والراهبة، أخبرنا به ابن أبي جيد، عن محمد بن الحسن ابن الوليد، عن "
                                 "القاسم بن يحيى، عن جده الحسن بن راشد.",
                                 is_subject=lambda name: name == "الحسن بن راشد")
        self.assertEqual(people["route_students"], ["القاسم بن يحيي"])

    def test_teachers_split_on_conjunction_but_keep_waw_names(self):
        self.assertEqual(rx.split_conjoined_names("أبي عبد الله وأبي الحسن"), ["أبي عبد الله", "أبي الحسن"])
        self.assertEqual(rx.split_conjoined_names("وهب بن وهب"), ["وهب بن وهب"])

    def test_books_najashi_201(self):
        books = rx.books_named("له كتب، منها: كتاب التاريخ ولم يتمه، كتاب دعاء السفر، كتاب الافضال، حدثنا شيخنا "
                               "أبو عبد الله عنه بكتبه.")
        self.assertEqual([b["verbatim"] for b in books if b["kind"] == "kitab"],
                         ["كتاب التاريخ ولم يتمه", "كتاب دعاء السفر", "كتاب الافضال"])

    def test_no_book_from_a_route(self):
        self.assertEqual(rx.books_named("رواه عن كتاب أبيه."), [])

    def test_mizzi_lists(self):
        lists = rx.mizzi_lists("روى عن: الأسود بن هلال (س) ، وزر بن حبيش الأسدي (ع) ، وقرأ عليه القرآن، وأبي وائل "
                               "شقيق بن سلمة. روى عنه: أبان بن يزيد العطار (د سي) ، وإبراهيم بن طهمان. قال أحمد: ثقة.")
        self.assertEqual(lists["teachers"], ["الاسود بن هلال", "زر بن حبيش الاسدي", "ابي وائل شقيق بن سلمة"])
        self.assertEqual(lists["students"], ["ابان بن يزيد العطار", "ابراهيم بن طهمان"])


class KashshiTests(unittest.TestCase):
    def test_section_subjects(self):
        for title, subjects, kind in (
                ("في حمران بن أعين", ["حمران بن اعين"], "person"),
                ("حذيفة وعبد الله بن مسعود", ["حذيفة", "عبد الله بن مسعود"], "person"),
                ("ما روى في حماد بن عيسى الجهني البصري ودعوة أبى الحسن (ع) له، وكم عاش",
                 ["حماد بن عيسي الجهني البصري"], "person"),
                ("في الزيدية", [], "group"),
                ("في وهب بن وهب", ["وهب بن وهب"], "person")):
            result = rx.kashshi_subjects(title)
            self.assertEqual((result["subjects"], result["kind"]), (subjects, kind))

    def test_reports_continue_unnumbered_paragraphs(self):
        reports = rx.split_kashshi_reports([{"text": "2 - محمد بن سعيد الكشي قالا:", "page": "v1p5"},
                                            {"text": "قال الصادق اعرفوا منازل شيعتنا", "page": "v1p5"},
                                            {"text": "3 - إبراهيم بن محمد", "page": "v1p6"}])
        self.assertEqual([r["number"] for r in reports], ["2", "3"])
        self.assertIn("اعرفوا", reports[0]["text"])


class NameMatchTests(unittest.TestCase):
    CASES = [  # chain name key, entry headword key, expected basis
        ("محمد بن مسلم", "محمد بن مسلم بن رباح ابو جعفر الاوقص", "nasab_prefix_and_tokens"),
        ("علي بن ابراهيم", "علي بن ابراهيم", "exact_full_name"),
        ("زرارة", "زرارة بن اعين الشيباني", "short_name_in_headword"),
        ("زرارة", "عبيد بن زرارة بن اعين الشيباني", None),  # the father's name is not the person
        ("ابي بصير", "ليث بن البختري المرادي ابو بصير", "short_name_in_headword"),
        ("ابي بصير", "علي بن ابي بصير", None),
        ("بن ابي عمير", "محمد بن ابو عمير", "short_name_in_headword"),
        ("الحلبي", "عبيد الله بن علي بن ابو شعبة الحلبي", "short_name_in_headword"),
        ("محمد بن مسلم", "احمد بن محمد بن مسلم", None),
        # a theophoric ism alone is a short name: only as the entry's own ism, and only with corroboration
        ("عبد العزيز", "عبد العزيز", "short_name_in_headword"),
    ]

    def test_shapes_that_never_corroborate(self):
        for key, shape in (("غيره", "single"), ("ابيه", "relational_name"), ("عبد العزيز", "single"),
                           ("ابي بصير", "kunya"), ("بن ابي عمير", "ibn"), ("محمد بن مسلم", "full")):
            self.assertEqual(rx.name_shape(key), shape)

    def test_name_match(self):
        for name, entry_key, expected in self.CASES:
            with self.subTest(name=name, entry=entry_key):
                shape = rx.name_shape(name)
                self.assertEqual(rx.name_match_basis(name, [entry_key], set(entry_key.split()), shape), expected)


class LifeFactTests(unittest.TestCase):
    def test_arrival_with_full_year(self):
        # al-Najashi no. 202
        facts = rx.life_facts("أحمد بن محمد بن جعفر أبو علي الصولي بصري، صحب الجلودي عمره، وقدم بغداد سنة ثلاث و "
                              "خمسين وثلاثمائة، وسمع الناس منه")
        self.assertEqual([(f["kind"], f["place_id"], f["year_min"], f["year_max"]) for f in facts],
                         [("travelled_or_arrived", "baghdad", 353, 353)])

    def test_event_and_regnal_dating(self):
        # al-Tusi, Rijal no. 205
        facts = rx.life_facts("كنيته أبو خالد، شهد العقبة في السبعين وشهد بدرا وما بعدها من الغزوات واليمامة، و مات في "
                              "خلافة عمر.")
        kinds = [(f["kind"], f.get("event_as_written"), f.get("history_event_ref")) for f in facts]
        self.assertIn(("present_at_event", "العقبة", None), kinds)
        self.assertIn(("present_at_event", "بدرا", "Battle of Badr"), kinds)
        regnal = [f for f in facts if f["kind"] == "regnal_dating"]
        self.assertEqual(regnal[0]["ruler_or_period_as_written"], "عمر")
        self.assertIsNone(regnal[0]["year_min"])  # a reign is never turned into years here

    def test_uhud_needs_a_trigger(self):
        self.assertEqual([f for f in rx.life_facts("روى عنه احد من اصحابنا") if f["kind"] == "present_at_event"], [])

    def test_places(self):
        self.assertEqual(rx.place_of("بالكوفة"), "kufa")
        self.assertEqual(rx.place_of("قم"), "qum")
        self.assertIsNone(rx.place_of("عمان"))  # Oman / Amman are written alike


class CitationTests(unittest.TestCase):
    def test_locate_folded_back_to_source_letters(self):
        citable = "مات سنة ثمان وأربعين ومئتين بالكوفة"
        self.assertEqual(rx.locate_verbatim(citable, "مات سنة ثمان واربعين"), ("مات سنة ثمان وأربعين", None))
        self.assertEqual(rx.locate_verbatim(citable, "قتل سنة")[0], None)

    def test_incomplete_citation_is_reported(self):
        problems = rx.citation_problems({"work": {"author": "x", "title": "y", "tradition": "imami"}})
        self.assertIn("missing passage_ar", problems)


if __name__ == "__main__":
    unittest.main()
