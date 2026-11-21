"""Table-driven tests for the pure logic in generate_hy_mt2_candidates.py (real corpus rows, no API)."""

import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "generate_hy_mt2_candidates.py"
SPEC = importlib.util.spec_from_file_location("hy_mt2_candidates_test", MODULE_PATH)
hy = importlib.util.module_from_spec(SPEC)
sys.modules["hy_mt2_candidates_test"] = hy
SPEC.loader.exec_module(hy)

PEACE = "(peace and blessings be upon him)"


class GlyphSubstitutionTests(unittest.TestCase):
    def test_real_rows(self):
        cases = [
            # k6:15005: two parenthesised ligatures
            ("the Prophet (ﷺ) and said: O; So the Prophet (ﷺ) forbade",
             f"the Prophet {PEACE} and said: O; So the Prophet {PEACE} forbade", 2),
            # k6:24464: opening paren never closed in the source; must not become "((".
            ("the Messenger of Allah (ﷺ said:  \"When any one", f"the Messenger of Allah {PEACE} said:  \"When any one", 1),
            # bare ligature
            ("the Prophet ﷺ said", f"the Prophet {PEACE} said", 1),
            # ligature inside an enclosing parenthesis keeps the enclosing paren balanced
            ("(the Prophet ﷺ)", f"(the Prophet {PEACE})", 1),
            # thaqalayn:3550efe7...: jalla jalaluhu
            ("In the decree of Allah ﷻ , there is nothing", "In the decree of Allah (may His glory be exalted) , there is nothing", 1),
        ]
        for source, expected, count in cases:
            with self.subTest(source=source):
                self.assertEqual(hy.glyph_substitution(source), (expected, count))

    def test_rows_that_must_not_be_touched(self):
        for source in (
            "No Arabic at all here.",  # nothing to substitute
            "Narrated 'Ali ِ (ﷺ)",  # stray kasra (thaqalayn:643118a6...) is not an honorific
            "He said ﷺ and then الله",  # Arabic letters remain: needs the model
        ):
            with self.subTest(source=source):
                self.assertIsNone(hy.glyph_substitution(source))


class SentenceSplitterTests(unittest.TestCase):
    # k6:4946 (real Sahih Bukhari row): several full-stop terminated sentences.
    BUKHARI = (
        "وقال لي طلق حدثنا زائدة، عن منصور، عن مجاهد، عن ابن عباس، ‏{‏فيما عرضتم‏}‏ يقول إني أريد التزويج، "
        "ولوددت أنه تيسر لي امرأة صالحة‏.‏ وقال القاسم يقول إنك على كريمة، وإني فيك لراغب، وإن الله لسائق إليك خيرا‏.‏ "
        "أو نحو هذا‏.‏ وقال عطاء يعرض ولا يبوح يقول إن لي حاجة وأبشري، وأنت بحمد الله نافقة‏.‏ وتقول هي قد أسمع ما تقول‏.‏"
    )
    # pc_88097 (real Pure Canon row): no sentence punctuation at all.
    UNPUNCTUATED = (
        "من قال لا إله إلا الله وحده لا شريك له دخل الجنة قال قلت وإن زنى وإن سرق قال وإن زنى وإن سرق "
        "قلت وإن زنى وإن سرق قال وإن زنى وإن سرق قلت وإن زنى وإن سرق قال وإن زنى وإن سرق "
        "على رغم أنف أبي الدرداء قال فخرجت لأنادي بها في الناس"
    )

    def test_short_row_is_one_chunk(self):
        self.assertEqual(hy.split_sentences(self.BUKHARI, target=5000), [(0, len(self.BUKHARI))])

    def test_chunks_partition_text_and_end_on_sentence_boundaries(self):
        chunks = hy.split_sentences(self.BUKHARI, target=200, hard=1000)
        self.assertGreater(len(chunks), 1)
        self.assertEqual(chunks[0][0], 0)
        self.assertEqual(chunks[-1][1], len(self.BUKHARI))
        for (_, end), (next_start, _) in zip(chunks, chunks[1:]):
            self.assertEqual(end, next_start)
        for start, end in chunks[:-1]:
            chunk = self.BUKHARI[start:end].strip("‏ \n")
            self.assertTrue(chunk.endswith("."), chunk[-8:])

    def test_unsplittable_row_is_refused_not_cut_mid_sentence(self):
        self.assertIsNone(hy.split_sentences(self.UNPUNCTUATED, target=100, hard=150))


class ScreenTests(unittest.TestCase):
    # pc_88097: the Arabic itself repeats "وإن زنى وإن سرق"; faithful English repeats too.
    ARABIC = SentenceSplitterTests.UNPUNCTUATED + " قال فلقيني عمر فقال ارجع"
    FAITHFUL = (
        'Whoever says, "There is no god but Allah alone, with no partner," will enter Paradise. He said: I said, '
        '"Even if he commits zina and even if he steals?" He said, "Even if he commits zina and even if he steals." '
        'I said, "Even if he commits zina and even if he steals?" He said, "Even if he commits zina and even if he '
        'steals." I said, "Even if he commits zina and even if he steals?" He said, "Even if he commits zina and even '
        "if he steals - against Abu al-Darda's will!\" He said: So I went out to proclaim it among the people. He said: "
        'Then Umar met me and said, "Go back."'
    )

    def test_source_repetition_is_not_a_loop(self):
        self.assertEqual(hy.screen_translation(self.FAITHFUL, self.ARABIC, "stop"), [])

    def test_failure_modes(self):
        looped = "The man went to the market and bought some bread for his family. " * 4
        cases = {
            "repetition_loop": (looped + "He returned home with a full basket.", SentenceSplitterTests.BUKHARI, "stop"),
            "arabic_leakage": (self.FAITHFUL + " عمر", self.ARABIC, "stop"),
            "truncated_finish_reason_length": (self.FAITHFUL, self.ARABIC, "length"),
            "length_ratio_too_short": ("Whoever says there is no god but Allah enters Paradise.", self.ARABIC, "stop"),
            "prompt_echo": (self.FAITHFUL + " Translate the following text into English.", self.ARABIC, "stop"),
            "copied_input": (self.ARABIC, self.ARABIC, "stop"),
        }
        for expected, (text_en, text_ar, finish) in cases.items():
            with self.subTest(expected=expected):
                self.assertIn(expected, hy.screen_translation(text_en, text_ar, finish))


if __name__ == "__main__":
    unittest.main()
