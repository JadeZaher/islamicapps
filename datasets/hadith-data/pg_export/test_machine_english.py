"""Machine English overlay: what reaches `translations` and what is held out. Run: python -I test_machine_english.py"""

from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import machine_english as me  # noqa: E402

MODEL = "tencent/hy-mt2-30b-a3b"
ARABIC = "حدثنا أبو عبيدة عن جابر بن زيد عن ابن عباس رضي الله عنهما قال قال رسول الله صلى الله عليه وسلم إنما الأعمال بالنيات وإنما لكل امرئ ما نوى"
ENGLISH = ("Abu Ubayda narrated to us from Jabir ibn Zayd from Ibn Abbas, may Allah be pleased with them both, who said: the Messenger of Allah "
           "(peace and blessings be upon him) said: Actions are only by intentions, and every person will have only what he intended.")
HASH = hashlib.sha256(ARABIC.encode()).hexdigest()


def candidate(**changes) -> dict:
    row = {"record_id": "openiti:ibadi:rabi_0001", "arabic_sha256": HASH, "text_en": ENGLISH, "translation_source": "hy-mt2-openrouter-v1",
           "translation_model": MODEL, "response_model": MODEL, "response_provider": "Tencent", "prompt_version": "hy-mt2-terminology-en-prompt-v2",
           "prompt_sha256": "ab" * 32, "finish_reasons": ["stop"], "qa": {"status": "accepted_machine_unreviewed", "errors": []},
           "origin_journal": "journal.jsonl", "created_at": "2026-11-22T08:10:00Z"}
    row.update(changes)
    return row


def run(candidates, existing=()):
    info = {"hadith:openiti:ibadi:rabi_0001": {"arabic_sha256": HASH, "source_record_id": "rabi_0001"}}
    text = {"hadith:openiti:ibadi:rabi_0001": ARABIC}
    return me.overlay_translations(list(existing), info, text, {"openiti:ibadi:rabi_0001": "hadith:openiti:ibadi:rabi_0001"}, candidates, MODEL)


def existing_row(state="source_provided", quality="complete"):
    return ["translation:openiti:ibadi:rabi_0001:en", "hadith:openiti:ibadi:rabi_0001", "en", "Old text.", None, state, quality, state,
            "src", None, None, None, "rabi_0001", HASH]


class MachineEnglishOverlay(unittest.TestCase):
    def test_matching_draft_becomes_a_machine_row_with_model_and_trace(self):
        rows, report = run([candidate()])
        (row,) = rows
        self.assertEqual((row[5], row[6], row[9], row[13]), ("machine_unreviewed", "complete", MODEL, HASH))
        self.assertIn("provider=Tencent", row[11])
        self.assertIn("prompt=hy-mt2-terminology-en-prompt-v2", row[11])
        self.assertEqual(report["used"], 1)

    def test_a_draft_for_changed_arabic_is_never_published(self):
        rows, report = run([candidate(arabic_sha256="0" * 64)])
        self.assertEqual(rows, [])
        self.assertEqual(report["held_out_by_reason"]["stale_arabic_hash"], 1)

    def test_source_english_wins_and_a_failing_row_is_replaced_in_place(self):
        kept, kept_report = run([candidate()], [existing_row()])
        self.assertEqual((kept[0][3], kept_report["kept_source_english"]), ("Old text.", 1))
        replaced, report = run([candidate()], [existing_row(quality="arabic_leakage")])
        self.assertEqual((len(replaced), replaced[0][0], replaced[0][5], report["replaced_failing_row"]),
                         (1, "translation:openiti:ibadi:rabi_0001:en", "machine_unreviewed", 1))

    def test_gate_holds_out_each_unsafe_draft(self):
        cases = {
            "empty": candidate(text_en="  "),
            "arabic_leakage": candidate(text_en=ENGLISH + " قال"),
            "refusal_or_meta_text": candidate(text_en="I'm sorry, but I cannot translate this text into English as an AI language model."),
            "length_ratio_out_of_bounds": candidate(text_en="Actions are by intentions."),
            "truncated": candidate(finish_reasons=["length"]),
            "model_not_pinned": candidate(translation_model="other/model"),
            "not_accepted_by_screen": candidate(qa={"status": "rejected", "errors": ["repetition_loop"]}),
            "prompt_not_recorded": candidate(prompt_version=""),
        }
        for reason, draft in cases.items():
            with self.subTest(reason=reason):
                rows, report = run([draft])
                self.assertEqual(rows, [])
                self.assertIn(reason, report["held_out_by_reason"])

    def test_honorific_symbol_is_not_leakage(self):
        rows, _ = run([candidate(text_en=ENGLISH.replace("(peace and blessings be upon him)", "ﷺ"))])
        self.assertEqual(len(rows), 1)


if __name__ == "__main__":
    unittest.main()
