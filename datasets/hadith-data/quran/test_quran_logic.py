"""Tests for quran_logic on the real Tanzil texts and real report wordings.

Run from this directory: python -B -m unittest test_quran_logic
"""

import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import quran_logic as logic  # noqa: E402

TANZIL = HERE.parent.parent / "sources" / "external" / "quran-tanzil"
STREAMS = logic.load_tanzil(TANZIL)
NAMES = [logic.sura_key(n) for n in ("البقرة", "الإخلاص", "الرحمن", "الأعراف")]


def match(text):
    skeleton = logic.build_skeleton(text)
    spans = logic.merge_editions([logic.find_spans(skeleton, s) for s in STREAMS.values()])
    return skeleton, spans


def refs(span):
    return {(c["sura"], c["aya_from"], c["aya_to"]) for c in span.candidates}


class Folds(unittest.TestCase):
    def test_uthmani_and_imlai_spellings_share_a_skeleton(self):
        cases = [  # (Uthmani as Tanzil writes it, imla'i as a report writes it)
            ("بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ", "بسم الله الرحمن الرحيم"),
            ("إِنَّآ أَعْطَيْنَٰكَ ٱلْكَوْثَرَ", "إنا أعطيناك الكوثر"),
            ("ٱلسَّيِّـَٔاتِ", "السيئات"),
            ("مَّسْـُٔولًا", "مسؤولا"),
            ("رَحْمَتَ ٱللَّهِ", "رحمة الله"),
            ("یَوْمِ ٱلدِّینِ", "يوم الدين"),          # Persian ya
        ]
        for uthmani, imlai in cases:
            with self.subTest(imlai):
                self.assertEqual("".join(logic.skeleton_words(uthmani)), "".join(logic.skeleton_words(imlai)))

    def test_fold_is_separate_from_the_project_normalizer(self):
        self.assertEqual(logic.fold_quranic_orthography("اءؤئة"), "ت")
        self.assertEqual(logic.project_normalize("أُمَّةً"), "امة")


class Matching(unittest.TestCase):
    def test_vocalized_quotation_in_brackets_is_found_with_its_verse(self):
        text = "ثم قرأ ‏{‏ قل هو الله أحد الله الصمد ‏}‏ ثم ركع"
        _, spans = match(text)
        self.assertEqual(len(spans), 1)
        self.assertEqual(refs(spans[0]), {(112, 1, 2)})
        self.assertEqual(spans[0].words, 6)

    def test_quotation_spanning_two_verses(self):
        _, spans = match("فقرأ قل هو الله أحد الله الصمد لم يلد ولم يولد")
        self.assertEqual(refs(spans[0]), {(112, 1, 3)})

    def test_repeated_verse_keeps_every_candidate(self):
        _, spans = match("فبأي آلاء ربكما تكذبان")
        self.assertGreater(len(refs(spans[0])), 20)       # al-Rahman repeats it 31 times
        self.assertTrue(all(sura == 55 for sura, _, _ in refs(spans[0])))

    def test_span_stops_at_a_whole_word_on_both_sides(self):
        text = "ثم استوى على العرش أي علا"
        skeleton, spans = match(text)
        start, end = logic.original_offsets(text, logic.letter_origins(text), spans[0])
        self.assertEqual(text[start:end], "ثم استوى على العرش")

    def test_span_starts_at_the_hamza_of_its_first_word(self):
        text = "قال إذا جاء نصر الله والفتح"
        _, spans = match(text)
        start, end = logic.original_offsets(text, logic.letter_origins(text), spans[0])
        self.assertTrue(text[start:end].startswith("إذا"))

    def test_uthmani_spelling_in_the_report_matches_the_uthmani_edition(self):
        _, spans = match("ٱلصَّلَوٰةَ وَءَاتُوا۟ ٱلزَّكَوٰةَ وَٱرْكَعُوا۟ مَعَ ٱلرَّٰكِعِينَ")
        self.assertIn((2, 43, 43), refs(spans[0]))

    def test_ordinary_speech_with_no_verse_finds_nothing(self):
        self.assertEqual(match("حدثنا مسدد قال حدثنا يحيى عن شعبة عن قتادة عن أنس قال كان النبي يصلي")[1], [])


class Classes(unittest.TestCase):
    def test_formulae_are_not_citations(self):
        for text, expected in [("بسم الله الرحمن الرحيم", "basmala"), ("رضي الله عنهما", "radiya_anhum"),
                               ("الحمد لله رب العالمين", "hamdala")]:
            with self.subTest(text):
                letters = "".join(logic.skeleton_words(text))
                self.assertEqual(logic.formula_of(letters), expected)
                self.assertEqual(logic.classify_span(4, logic.formula_of(letters), [{"kind": "brackets"}], 1)["kind"],
                                 "formula")

    def test_class_table(self):
        bracket, none = [{"kind": "brackets", "text": ""}], []
        cases = [  # words, cues, reports holding the span -> (kind, confidence)
            (8, bracket, 1, ("citation", "high")),
            (3, bracket, 1, ("citation", "low")),
            (2, bracket, 1, ("short_phrase", None)),
            (4, none, 1, ("short_phrase", None)),
            (5, none, 1, ("citation", "low")),
            (11, none, 1, ("citation", "medium")),
            (16, none, 1, ("citation", "high")),
            (3, none, 40, ("common_phrase", None)),
            (8, none, 40, ("citation", "low")),
        ]
        for words, cues, count, expected in cases:
            with self.subTest(words=words, count=count):
                verdict = logic.classify_span(words, None, cues, count)
                self.assertEqual((verdict["kind"], verdict["confidence"]), expected)


class Cues(unittest.TestCase):
    def kinds(self, text, needle):
        start = text.index(needle)
        return {c["kind"] for c in logic.cues_around(text, start, start + len(needle), NAMES)}

    def test_cues(self):
        cases = [
            ("ثم قرأ ‏{‏ قل هو الله أحد ‏}‏", "قل هو الله أحد", "brackets"),
            ("فقال الله تعالى: لقد كان لكم", "لقد كان لكم", "introducer"),
            ("ونزلت سورة الإخلاص قل هو الله أحد", "قل هو الله أحد", "sura_named"),
            ("قل هو الله أحد إلى آخر الآية", "قل هو الله أحد", "aya_word_after"),
        ]
        for text, needle, expected in cases:
            with self.subTest(expected):
                self.assertIn(expected, self.kinds(text, needle))

    def test_no_cue_for_bare_honorific_wording(self):
        self.assertFalse(self.kinds("قال النبي عز وجل شيئا لقد كان لكم", "لقد كان لكم") & logic.STRONG_CUES)


if __name__ == "__main__":
    unittest.main()
