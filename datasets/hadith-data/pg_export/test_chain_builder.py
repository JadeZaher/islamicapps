"""Chain builder rules on the real parsed OpenITI works, one row per audited case (chain-audit/ibadi-zaydi fixtures).

Run: python -I datasets/hadith-data/pg_export/test_chain_builder.py
"""

import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent / "reconciled")]
import build_openiti_extraction_sidecar as sidecar  # noqa: E402
import chain_builder as cb  # noqa: E402
import external_identity as xid  # noqa: E402


def parsed_reports() -> list[cb.OpenitiReport]:
    reports = []
    for path in sidecar.PARSED.values():
        hadiths = json.loads(path.read_text(encoding="utf-8"))["hadiths"]
        record_ids = [sidecar.record_id_of(h)[0] for h in hadiths]
        for index, hadith in enumerate(hadiths):
            parent = None
            if hadith.get("sanad_inherits_from"):
                parent = [record_ids[j] for j in range(index) if hadiths[j]["id"] == hadith["sanad_inherits_from"]][-1]
            reports.append(cb.OpenitiReport(record_ids[index], cb.work_of(record_ids[index]), hadith["text_ar"],
                                            hadith.get("sanad_ar"), hadith.get("matn_ar"), hadith["split_confidence"], parent))
    return reports


class ChainBuilderOnRealReports(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rule, cls.register = cb.load_zayd_rule()
        cls.result = cb.build_openiti_chains(parsed_reports(), rule)
        cls.by_short = {record_id.split(":")[2].split("|")[0]: branches
                        for record_id, branches in cls.result.branches.items()}

    def chain(self, short: str) -> list[cb.BuiltMention]:
        branches = self.by_short[short]
        self.assertEqual(len(branches), 1, f"{short}: {branches}")
        return branches[0]

    def surfaces(self, short: str) -> list[str]:
        return [cb.fold(mention.surface) for mention in self.chain(short)]

    def test_written_chains(self):
        # (report, expected names in order) — compiler dropped, honorifics and frame words out, links after (ع م) kept.
        cases = [
            ("rabi_0001", ["ابو عبيده مسلم بن ابي كريمه التميمي", "جابر بن زيد الازدي", "عبد الله بن عباس"]),
            ("rabi_0883", ["عبد الرحمن بن حرمله", "سعيد بن المسيب"]),                      # D2c: al-Rabi not a mention
            ("rabi_0928", ["جابر بن زيد"]),                                               # mursal of Jabir stays
            ("zayd_0002", ["زيد بن علي", "ابائه", "علي بن ابي طالب"]),                     # D2c: Abu Khalid not a mention
            ("zayd_0128", ["زيد بن علي", "ابيه", "جده", "علي"]),               # D6d: «عن جده (ع م) عن علي»
            ("rida_0001", ["علي بن موسي الرضي", "ابي موسي بن جعفر", "ابي جعفر بن محمد", "ابي محمد بن علي",
                           "ابي علي بن الحسين", "ابي الحسين ابن علي", "ابي", "علي بن ابي طالب"]),   # D6b: the Imam chain
        ]
        for short, expected in cases:
            with self.subTest(short):
                self.assertEqual(self.surfaces(short), expected)

    def test_no_surface_is_a_frame_word_honorific_or_matn(self):
        bad = ("كرم الله", "جهه ", "قال", "سالت", "سئل", "عليه السلام", "في قوله")
        for record_id, branches in self.result.branches.items():
            for branch in branches:
                for mention in branch:
                    with self.subTest(record_id=record_id, surface=mention.surface):
                        self.assertFalse(any(word in cb.fold(mention.surface) + " " for word in bad))

    def test_low_confidence_split_has_no_own_chain(self):
        self.assertEqual(self.by_short["rabi_0002"], [])                                  # D3e, D5d

    def test_continuation_inherits_marked_names_and_opener_is_never_a_mention(self):
        imam_chain = self.surfaces("rida_0001")
        for short in ("rida_0003", "rida_0005", "rida_0012#6"):
            with self.subTest(short):
                chain = self.chain(short)
                self.assertEqual([cb.fold(m.surface) for m in chain], imam_chain)
                self.assertTrue(all(m.inherited_from and m.inherited_from[0].startswith("openiti:imami:rida_0001|")
                                    for m in chain))

    def test_named_link_shortens_the_inherited_chain_for_that_report_only(self):
        chain = self.chain("rida_0004#3")              # «وباسناده قال: حدثني علي بن الحسين»
        self.assertEqual(cb.fold(chain[-1].surface), "علي بن الحسين")
        self.assertIsNone(chain[-1].inherited_from)
        self.assertEqual(len(self.chain("rida_0005")), 8)   # the next «وباسناده» repeats the full chain again

    def test_named_route_replaces_the_companion(self):
        chain = self.chain("rabi_0346")                # «ومن طريق ابن عباس عنه»: undeclared before round 2 (D1c)
        self.assertEqual(cb.fold(chain[-1].surface), "ابن عباس")
        self.assertTrue(all(m.inherited_from for m in chain[:-1]))

    def test_balagh_is_a_marked_gap_not_a_repair(self):
        chain = self.chain("rabi_0425")
        self.assertIn("anonymous", [m.link_kind for m in chain])

    def test_zayd_relations_follow_the_opening_isnad_only_in_the_fixed_shape(self):
        identities = [m.rule_identity[0] if m.rule_identity else None for m in self.chain("zayd_0170")]
        self.assertEqual(identities, ["narrator:imam:zayd", "narrator:imam:4", "narrator:imam:3", "narrator:imam:1"])
        self.assertTrue(all("zayd_0001" in m.rule_identity[1] for m in self.chain("zayd_0170")))
        self.assertEqual([m.link_kind for m in self.chain("zayd_0170")], [None, "derived_relation", "derived_relation", None])
        self.assertTrue(all(m.rule_identity is None for m in self.chain("zayd_0002")))   # «عن آبائه»: not the shape

    def test_register_addition_is_credited_to_the_work(self):
        self.assertEqual([person["id"] for person in self.register], ["narrator:imam:zayd"])
        self.assertIn("zayd_0001", self.register[0]["asserted_by"])


class KunyaOnlySurface(unittest.TestCase):
    def test_a_kunya_alone_cannot_confirm_a_source(self):
        claim = xid.Candidate("narrator:riwayat:N0013779", "source_riwayat_confirmed_by_text", "full_agreement:full_name_key")
        cases = [("أبو عبيدة", "source_riwayat"), ("أبي هريرة", "source_riwayat"),
                 ("أبو عبيدة مسلم بن أبي كريمة", "source_riwayat_confirmed_by_text"),
                 ("جابر بن زيد", "source_riwayat_confirmed_by_text")]
        for surface, basis in cases:
            with self.subTest(surface):
                demoted = xid.demote_kunya_only(claim, surface)
                self.assertEqual(demoted.basis, basis)
                self.assertEqual(xid.standing_identity([demoted], xid.PersonKeys()) is None, basis == "source_riwayat")


if __name__ == "__main__":
    unittest.main(verbosity=1)
