"""Table-driven tests for transliteration.py and mention_text.py on real names from the corpus (Thaqalayn, K6)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import mention_text as mt  # noqa: E402
import transliteration as tr  # noqa: E402


class VocalizedNames(unittest.TestCase):
    def test_reads_the_marks_the_text_carries(self):
        cases = [
            # (vocalized as written in Thaqalayn's Arabic, expected Latin)
            ("أَبِي عَبْدِ اللَّهِ", "Abi ʿAbd Allah"),
            ("مُحَمَّدُ بْنُ يَحْيَى", "Muhammad ibn Yahya"),
            ("عَلِيُّ بْنُ إِبْرَاهِيمَ", "ʿAli ibn Ibrahim"),
            ("أَحْمَدَ بْنِ مُحَمَّدِ بْنِ عِيسَى", "Ahmad ibn Muhammad ibn ʿIsa"),
            ("الْحُسَيْنِ بْنِ سَعِيدٍ", "al-Husayn ibn Saʿid"),
            ("ابْنِ أَبِي عُمَيْرٍ", "Ibn Abi ʿUmayr"),
            ("حَمَّادِ بْنِ عِيسَى", "Hammad ibn ʿIsa"),                     # shadda doubles the letter
            ("زُرَارَةَ", "Zurara"),                                        # ta marbuta as -a, case ending dropped
            ("الْحَلَبِيِّ", "al-Halabi"),                                   # nisba -iyy read as -i
            ("عَبْدِ الرَّحْمَنِ بْنِ أَبِي نَجْرَانَ", "ʿAbd al-Rahman ibn Abi Najran"),  # article always al- (no assimilation)
            ("أَبِي الْحَسَنِ الرِّضَا", "Abi al-Hasan al-Rida"),
            ("مُوسَى بْنِ جَعْفَرٍ", "Musa ibn Jaʿfar"),                      # alif maqsura
            ("يَزِيدَ بْنِ إِسْحَاقَ الْأَشْعَرِيِّ", "Yazid ibn Ishaq al-Ashʿari"),  # hamza after the article not written
            ("الْحُسَيْنِ بْنِ أَبِي الْعَلَاءِ", "al-Husayn ibn Abi al-ʿAlaʾ"),       # final hamza written
            ("شِهَابِ بْنِ عَبْدِ رَبِّهِ", "Shihab ibn ʿAbd Rabbihi"),         # pronoun suffix keeps its vowel
            ("أَبِيهِ", "Abihi"),
            ("عَلِيُّ بْنُ الْحُسَيْنِ وَ غَيْرُهُ", "ʿAli ibn al-Husayn wa ghayruhu"),
            ("ابْنِ أَبِی عُمَیْرٍ", "Ibn Abi ʿUmayr"),                       # Persian ی as written in some editions
            ("عُثْمَانَ بْنِ عِیسَی", "ʿUthman ibn ʿIsa"),                     # final Persian ی after fatha = alif maqsura
            ("عَمْرِو بْنِ شِمْرٍ", "ʿAmr ibn Shimr"),                          # the silent waw of ʿAmr
            ("مُحَمَّدُ بنُ يحيى", "Muhammad ibn Yahya"),                      # an unvocalized word read from the table
        ]
        for arabic, expected in cases:
            with self.subTest(arabic=arabic):
                self.assertEqual(tr.latin_name(arabic), (expected, "transliteration_vocalized"))

    def test_refuses_rather_than_guessing(self):
        cases = [
            "مُحَمَّدُ بْنُ هَمَّامٍ الْمُكْتِبِ بن غراب الخيبري",   # الخيبري: unvocalized and not in the table
            "خير الجعافر جعفر بن محمد",                         # unvocalized; الجعافر is not a curated element
            "الحسين بن إبراهيم بن أحمد بن هشام المكتب",          # المكتب: al-Mukattib or al-Maktab, deliberately absent
            "أبي مريم الأنصاري ثم الخزرجي",                       # الخزرجي not curated
            "",
        ]
        for arabic in cases:
            with self.subTest(arabic=arabic):
                self.assertIsNone(tr.latin_name(arabic))


class TableNames(unittest.TestCase):
    def test_every_word_covered(self):
        cases = [
            ("جعفر بن محمد بن مالك", "Jaʿfar ibn Muhammad ibn Malik"),
            ("عبد الله بن عطاء", "ʿAbd Allah ibn ʿAtaʾ"),
            ("أبي عبد الله ع", "Abi ʿAbd Allah"),                  # the honorific abbreviation is not part of the name
            ("أحمد بن محمد بن الهيثم العجلي", "Ahmad ibn Muhammad ibn al-Haytham al-ʿIjli"),
            ("أحمد بن يحيى بن زكريا القطان", "Ahmad ibn Yahya ibn Zakariyya al-Qattan"),
            ("علي بن أبي طالب", "ʿAli ibn Abi Talib"),
            ("أبو هريرة", "Abu Hurayra"),
            ("معمر بن راشد", None),          # Maʿmar or Muʿammar: deliberately absent, so Arabic alone
            ("عبيدة السلماني", None),        # ʿUbayda or ʿAbida
            ("حصين بن عبد الرحمن", None),    # Husayn or Hasin
            ("حدثنا قتيبة", None),           # a reporting verb left in the surface is not a name element
        ]
        for arabic, expected in cases:
            with self.subTest(arabic=arabic):
                result = tr.latin_name(arabic)
                self.assertEqual(result, (expected, "transliteration_table") if expected else None)


class MentionSpans(unittest.TestCase):
    TEXT = ("عَلِيُّ بْنُ إِبْرَاهِيمَ عَنْ أَبِيهِ عَنِ ابْنِ أَبِي عُمَيْرٍ عَنْ حَمَّادٍ عَنِ الْحَلَبِيِّ "
            "عَنْ أَبِي عَبْدِ اللَّهِ ع قَالَ")

    def test_finds_each_surface_in_chain_order_with_its_marks(self):
        text = mt.PlainText(self.TEXT)
        surfaces = ["علي بن إبراهيم", "أبيه", "ابن أبي عمير", "حماد", "الحلبي", "أبي عبد الله ع"]
        spans = mt.locate_mentions(text, surfaces)
        self.assertNotIn(None, spans)
        self.assertEqual([text.original_span(*span) for span in spans],
                         ["عَلِيُّ بْنُ إِبْرَاهِيمَ", "أَبِيهِ", "ابْنِ أَبِي عُمَيْرٍ", "حَمَّادٍ", "الْحَلَبِيِّ",
                          "أَبِي عَبْدِ اللَّهِ"])
        self.assertEqual([text.honorific_after(*span) for span in spans], [False] * 5 + [True])

    def test_whole_words_only(self):
        text = mt.PlainText("حدثنا عمرو بن دينار عن عمر")
        self.assertEqual(mt.locate_mentions(text, ["عمر"]), [(23, 3)])   # not the عمر inside عمرو
        self.assertEqual(mt.locate_mentions(text, ["زيد"]), [None])

    def test_honorific_forms(self):
        for after, expected in [(" عليه السلام قال", True), (" (ع) قال", True), (" - عليهما السلام", True),
                                (" قال", False), (" عن أبيه", False)]:
            with self.subTest(after=after):
                text = mt.PlainText("عن أبي جعفر" + after)
                span = mt.locate_mentions(text, ["أبي جعفر"])[0]
                self.assertEqual(text.honorific_after(*span), expected)


if __name__ == "__main__":
    unittest.main()
