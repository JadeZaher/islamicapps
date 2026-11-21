"""Table-driven tests on real passages for the consolidation rules (run from this directory):

    python -B -m unittest test_assessment_logic
"""

import unittest

import assessment_logic as L


def decide(sentence, preceding="", work="sunni:tirmidhi"):
    result = L.classify_report_statement(sentence, preceding, work)
    return None if result is None else (result["decision"], result.get("reason"), result.get("term_ar"))


REPORT = "حدثنا قتيبة حدثنا الليث عن نافع عن ابن عمر قال قال رسول الله صلى الله عليه وسلم كذا ‏.‏ "


class CompilerStatements(unittest.TestCase):
    def test_report_statements(self):
        cases = [
            # (sentence, preceding, work, expected decision, reason, term)
            ("قال أبو عيسى هذا حديث حسن صحيح وهو حديث مالك", REPORT, "sunni:tirmidhi", "compiler_statement", None, "هذا حديث حسن صحيح"),
            ("قال هذا حديث حسن غريب إنما نعرفه من حديث يحيى بن أيوب", REPORT, "sunni:tirmidhi", "compiler_statement", None, "هذا حديث حسن غريب"),
            ("قال أبو عيسى هذا حديث ليس إسناده بصحيح", REPORT, "sunni:tirmidhi", "compiler_statement", None, "هذا حديث ليس إسناده بصحيح"),
            # the grade is of Abu Hurayra's report, but this text is Ibn Umar's (k6:21553)
            ("قال أبو عيسى حديث أبي هريرة حديث حسن صحيح", REPORT, "sunni:tirmidhi", "held", "named_report_not_this_text", None),
            # 'عمر' must not be found inside 'عمرو' (k6:21952, found in the 60-row sample)
            ("قال أبو عيسى حديث ابن عمر حديث حسن صحيح", "عن عمرو بن شعيب عن أبيه عن جده قال كذا ‏.‏ ", "sunni:tirmidhi",
             "held", "named_report_not_this_text", None),
            ("قال أبو عيسى حديث عائشة أحسن شيء في هذا الباب وأصح", REPORT, "sunni:tirmidhi", "held",
             "comparative_soundest_in_chapter_not_a_grade", None),
            ("قال وسمعت محمد بن إسماعيل يقول هذا حديث غير محفوظ والصحيح ما روى شعيب", REPORT, "sunni:tirmidhi", "held",
             "another_authority_speaks", None),
            ("قال أبو داود هذا حديث منكر", REPORT, "sunni:abudawud", "compiler_statement", None, "هذا حديث منكر"),
            # Abu Dawud's remark about a narrator is not a report grading
            ("قال أبو داود وأبو زيد هو مولى بني ثعلبة", REPORT, "sunni:abudawud", None, None, None),
            # a transmitter of the Sunan speaks, not the compiler (k6:19876)
            ("قال أبو علي اللؤلؤي سمعت أبا داود يقول هذا حديث منكر", REPORT, "sunni:abudawud", "held", "another_authority_speaks", None),
            # unmarked voice is the compiler's only in the Jami' of al-Tirmidhi
            ("وهذا حديث منكر", REPORT, "sunni:nasai", "held", "speaker_not_marked_as_compiler", None),
            # 'الحسن' is a name, not a grade (k6:15986)
            ("وهذا حديث يوسف عن الحسن بن عبيد الله", REPORT, "sunni:abudawud", None, None, None),
            # 'وهم' as 'and they' inside a matn (k6:10192)
            ("يقولون هذا وهم يطوفون بالبيت", REPORT, "sunni:muslim", None, None, None),
        ]
        for sentence, preceding, work, decision, reason, term in cases:
            with self.subTest(sentence=sentence):
                got = decide(sentence, preceding, work)
                if decision is None:
                    self.assertIsNone(got)
                    continue
                self.assertEqual(got[0], decision)
                if reason:
                    self.assertEqual(got[1], reason)
                if term:
                    self.assertEqual(got[2], term)

    def test_bukhari_quoted_by_tirmidhi(self):
        result = L.classify_report_statement("وسألت محمد بن إسماعيل عن هذا الحديث فقال هو حديث حسن", REPORT, "sunni:tirmidhi")
        self.assertEqual((result["decision"], result["term_ar"]), ("quoted_ruling", "حسن"))
        self.assertIn("Bukhari", result["grader"])

    def test_closing_column_statement_after_another_chain(self):
        # pc_28711 (sample row 25): the closing column runs on into the next report's chain without punctuation
        closing = "وفي الباب عن ابن عباس وحديث عبادة حديث حسن حدثنا هناد حدثنا ابن أبي زائدة نحوه قال أبو عيسى هذا حديث حسن غريب"
        opener = L.first_chain_opener(closing)
        before = L.report_statements(closing[:opener], "sunni:tirmidhi")
        self.assertEqual([s["term_ar"] for s in before], ["وحديث عبادة حديث حسن"])
        self.assertTrue(L.report_statements(closing[opener:], "sunni:tirmidhi"), "the next report's grade is found, to be held")


class Canonical(unittest.TestCase):
    def test_imami_terms(self):
        cases = [("صحيح", "sahih"), ("موثق", "muwaththaq"), ("ضعيف على المشهور", "da_if"), ("معتبر", "mu_tabar"),
                 # the taxonomy overstatements the glossary flagged: kept verbatim, canonical null
                 ("حسن كالصحيح", None), ("مجهول كالصحيح", None), ("مرفوع", None), ("مضمر", None),
                 ("ضعيف على المشهور معتبر عند ي", None), ("حسن أو موثق", None), ("مرسل كالموثق", None)]
        for term, expected in cases:
            with self.subTest(term=term):
                self.assertEqual(L.imami_canonical(term)[0], expected)

    def test_imami_non_rulings_excluded(self):
        for term, reason in (("لم يخرجه", "not_included_by_grader"), ("سكت عنه", "grader_silent"),
                             ("كالسابق", "back_reference_only"), ("صحيح", None)):
            with self.subTest(term=term):
                self.assertEqual(L.imami_non_ruling_reason(term), reason)

    def test_statement_canonical_only_for_one_bare_term(self):
        for clause, expected in (("هذا حديث حسن", "hasan"), ("هذا حديث حسن صحيح", None), ("هذا حديث حسن غريب", None),
                                 ("هذا حديث ضعيف", "da_if"), ("هذا الحديث ليس بصحيح", None), ("هذا مرسل", "mursal")):
            with self.subTest(clause=clause):
                self.assertEqual(L.statement_canonical(L.fold(clause))[0], expected)

    def test_narrator_canonical(self):
        for verdict, expected in (("ثقة", "thiqa"), ("ثقة ثبت", "thiqa_thabt"), ("لا بأس به", "la_basa_bihi"),
                                  ("صدوق يهم", None), ("مقبول", None), ("ثقة في نفسه", None), ("مجهول الحال", None),
                                  ("كان ثقة", "thiqa")):
            with self.subTest(verdict=verdict):
                self.assertEqual(L.narrator_canonical(verdict)[0], expected)


class CriticStatements(unittest.TestCase):
    def test_hadith_kg_statement_kinds(self):
        cases = [("ثقة", "verdict"), ("ذكره في الثقات", "listed_in_work"), ("ذكره في تاريخ دمشق", "mention_only"),
                 ("سكت عنه", "silence"), ("له صحبة", "companion_status"), ("فيه نظر", "verdict"),
                 ("ذكره في تاريخ بغداد ولم يذكر فيه جرحا ولا تعديلا", "mention_only"), ("كتبت عنه وكان صدوقا", "verdict")]
        for qawl, kind in cases:
            with self.subTest(qawl=qawl):
                self.assertEqual(L.classify_critic_statement(qawl)[0], kind)

    def test_book_named_in_qawl(self):
        self.assertEqual(L.qawl_book_and_text("قال في التقريب  مقبول"), ("التقريب", "مقبول"))

    def test_editorial_label_is_not_a_critic(self):
        self.assertIn(1472, L.HADITH_KG_NOT_A_CRITIC)

    def test_templated_hukum_is_computed(self):
        self.assertTrue(L.is_templated_hukum("إسناد ضعيف فيه عبد الله بن لهيعة الحضرمي وهو ضعيف الحديث"))
        self.assertTrue(L.is_templated_hukum("إسناده متصل ، رجاله ثقات ، رجاله رجال الشيخين"))


class Mizzi(unittest.TestCase):
    def statements(self, text):
        return [s for s in L.mizzi_statements(text) if s["decision"] in ("verdict", "listed_in_work")]

    def test_father_of_ibn_abi_hatim(self):
        (row,) = self.statements("قال عبد الرحمن بن أبي حاتم: سألت أبي عنه، فقال: صدوق.")
        self.assertEqual((row["critic_ar"], row["reporter_ar"]), ("ابو حاتم الرازي", "عبد الرحمن بن ابي حاتم"))

    def test_quoted_through_reporter(self):
        (row,) = self.statements("وقال إسحاق بن منصور، عن يحيى بن معين: ثقة.")
        self.assertEqual((row["critic_key"], row["reporter_ar"]), ("ibn_main", "اسحاق بن منصور"))

    def test_several_critics_each_get_a_row(self):
        rows = self.statements("وقال أحمد بن عبد الله العجلي، والنسائي: ثقة.")
        self.assertEqual(sorted(r["critic_key"] for r in rows), ["ijli", "nasai"])

    def test_question_about_someone_else_is_held(self):
        rows = L.mizzi_statements("وقال عبد الله بن أحمد بن حنبل: سألت أبي عن أسلم المنقري من أين هو؟ قال: لا أدري، وهو عندنا ثقة.")
        self.assertEqual(rows[0]["decision"], "held")

    def test_death_date_is_not_a_verdict(self):
        self.assertEqual(self.statements("وقال محمد بن سعد: مات سنة ست وثلاثين ومئتين."), [])

    def test_listed_in_ibn_hibban_thiqat(self):
        rows = self.statements("وذكره ابن حبان في كتاب الثقات.")
        self.assertEqual((rows[0]["decision"], rows[0]["critic_key"]), ("listed_in_work", "ibn_hibban"))


class ImamiRijal(unittest.TestCase):
    def decisions(self, text):
        return [(v["decision"], v.get("reason"), tuple(v["terms"])) for v in L.imami_rijal_verdicts(text)]

    def test_najashi_own_verdicts_and_held_clauses(self):
        cases = [
            ("- عباد بن صهيب أبو بكر التميمي الكليبي اليربوعي بصري، ثقة، روى عن أبي عبد الله عليه السلام كتابا.",
             ("verdict", None, ("ثقة",))),
            ("- مصعب بن يزيد الأنصاري قال أبو العباس: ليس بذاك. له كتاب.",
             ("held", "quoted_or_reported_not_the_author", ("ليس بذاك",))),
            ("- الحسين بن علوان الكلبي مولاهم كوفي عامي، وأخوه الحسن يكنى أبا محمد ثقة.",
             ("held", "subject_may_be_a_relative", ("ثقة",))),
            ("- محمد بن مسكان، ذكره الكشي وقال: هو مجهول.", ("held", "quoted_or_reported_not_the_author", ("مجهول",))),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertIn(expected, self.decisions(text))

    def test_imam_speech_in_quotes_is_ignored(self):
        text = '- أبان بن تغلب، وقال أبو عبد الله عليه السلام: " ثقة ثقة ". ثقة'
        self.assertEqual([d for d in self.decisions(text) if d[0] == "verdict"], [("verdict", None, ("ثقة",))])


class Aspects(unittest.TestCase):
    def test_aspect_keys_shared_with_rijal_lane(self):
        cases = [("صدوق يهم ورمي بالإرجاء", ("verdict_term", ["reliability", "precision_memory", "doctrine"])),
                 ("واقفي", ("doctrinal_or_other_note", ["doctrine"])), ("ثقة يدلس", ("verdict_term", ["reliability", "specific_defect"])),
                 ("صدوق كثير الغلط", ("verdict_term", ["reliability", "precision_memory"])), ("شيخ", ("verdict_term", ["not_distinguished"]))]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(L.aspects_of(text, "verdict"), expected)


class Folding(unittest.TestCase):
    def test_comparison_letters_ignore_blessing_formula_variants(self):
        self.assertEqual(L.comparison_letters("قال رسول الله صلى الله عليه وآله وسلم كذا"),
                         L.comparison_letters("قال رسول الله صلى الله عليه وسلم كذا"))

    def test_chain_names_ignore_ibn_and_transmission_words(self):
        self.assertEqual(L.chain_name_letters("حدثنا قتيبة حدثنا الليث عن ابن شهاب"),
                         L.chain_name_letters("حدثنا قتيبة، أخبرنا الليث، عن بن شهاب"))


if __name__ == "__main__":
    unittest.main()
