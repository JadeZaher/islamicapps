"""Chain builder rules on the real parsed OpenITI works, one row per audited case (chain-audit/ibadi-zaydi fixtures).

Run: python -I datasets/hadith-data/pg_export/test_chain_builder.py
"""

import json
import sys
import unittest
from collections import Counter
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


class ImamiChainRules(unittest.TestCase):
    """The Imami audit's cases (chain-audit/imami/README.md), each a real surface or text."""

    KAFI_3_4_16_1 = ("1ـ عَلِيُّ بْنُ إِبْرَاهِيمَ عَنْ أَبِيهِ وَمُحَمَّدُ بْنُ إِسْمَاعِيلَ عَنِ الْفَضْلِ بْنِ شَاذَانَ جَمِيعاً عَنْ حَمَّادِ بْنِ"
                     " عِيسَى عَنْ حَرِيزٍ عَنْ زُرَارَةَ قَالَ قَالَ أَبُو جَعْفَرٍ (عَلَيْهِ الْسَّلام) إِذَا قُمْتَ فِي الصَّلاَةِ")

    def test_jamian_groups_meet_at_the_shared_narrator(self):
        # Noor's structured sanad (hadithId 108787): two routes meeting at Hammad b. ʿIsa, no cross link.
        counts = Counter()
        chains = cb.build_imami_chains(self.KAFI_3_4_16_1, [], "al-kafi", counts)
        self.assertEqual([[cb.imami_fold(m.surface) for m in chain.mentions] for chain in chains], [
            ["علي بن ابراهيم", "ابيه", "حماد بن عيسي", "حريز", "زرارة"],
            ["محمد بن اسماعيل", "الفضل بن شاذان", "حماد بن عيسي", "حريز", "زرارة"]])

    def test_plain_co_transmitters_before_jamian_are_not_regrouped(self):
        self.assertIsNone(cb.jamian_groups("علي بن إبراهيم عن أبيه و محمد بن عيسى جميعا عن يونس"))

    def test_surfaces(self):
        # (surface, position, after an Imam, work) -> (mentions as (text, link kind), chain suspension)
        cases = [
            ("و روى حماد بن عثمان", 0, False, "man-la-yahduruhu-al-faqih", [("حماد بن عثمان", None)], "route_given_elsewhere"),
            ("و روى عنه عمر بن يزيد", 0, False, "man-la-yahduruhu-al-faqih", [("عمر بن يزيد", None)], "back_reference"),
            ("و سأل صفوان بن يحيى أبا الحسن", 0, False, "man-la-yahduruhu-al-faqih",
             [("صفوان بن يحيى", None), ("أبا الحسن", None)], "route_given_elsewhere"),
            ("وعنه", 0, False, "kamil-al-ziyarat", [("وعنه", "not_a_narrator")], "back_reference"),
            ("و بهذا الإسناد", 0, False, "al-kafi", [("و بهذا الإسناد", "not_a_narrator")], "back_reference"),
            ("داود بن أبي يزيد عمن ذكره", 3, False, "al-kafi", [("داود بن أبي يزيد", None), ("عمن ذكره", "anonymous")], None),
            ("بعض أصحابه رفعه", 1, False, "al-kafi", [("بعض أصحابه رفعه", "anonymous")], None),
            ("سبعين", 2, False, "al-amali-saduq", [], None),
            ("4/86 الكافي علي", 0, False, "mujam-al-ahadith-al-mutabara", [("علي", None)], None),
            ("موسى بن بشار العطار 1", 2, False, "mujam-al-ahadith-al-mutabara", [("موسى بن بشار العطار", None)], None),
            ("الرجل يدخل الحمام و هو صائم فقال لا بأس ما لم يخش ضعفا", 3, True, "al-kafi", [], None),
            ("قلنا أما الذي يدل على صحتها فإن الشيعة الإمامية يروونها على", 0, False, "al-kafi", [], None),
            ("عيسى بن عبد الله بن محمد بن عمر بن علي بن أبي طالب ع", 3, False, "kamil-al-ziyarat",
             [("عيسى بن عبد الله بن محمد بن عمر بن علي بن أبي طالب ع", None)], None),
        ]
        for surface, position, after_imam, work, expected, suspension in cases:
            with self.subTest(surface):
                mentions, opened = cb.clean_imami_mention(surface, position, after_imam, work, Counter())
                self.assertEqual([(m.surface, m.link_kind) for m in mentions], expected)
                self.assertEqual(opened, suspension)

    def test_same_isnad_after_the_previous_report_is_filled_only_when_certain(self):
        def chain(*surfaces, label=True):
            mentions = [cb.BuiltMention("وبهذا الإسناد", "not_a_narrator")] if label else []
            return [cb.ImamiChain(mentions + [cb.BuiltMention(s) for s in surfaces], "back_reference" if label else None)]
        built = {"p": chain("محمد بن يحيى", "أحمد بن محمد", "ابن محبوب", "أبي عبد الله", label=False),
                 "whole": chain(), "named": chain("ابن محبوب", "أبي عبد الله"), "elsewhere": chain("يونس")}
        previous = {"whole": "p", "named": "whole", "elsewhere": "p"}
        counts = Counter()
        depth = cb.resolve_same_isnad(built, previous, {key: f"rec:{key}" for key in built}, counts)
        self.assertEqual([m.surface for m in built["whole"][0].mentions], ["محمد بن يحيى", "أحمد بن محمد", "ابن محبوب", "أبي عبد الله"])
        self.assertTrue(all(m.inherited_from[0] == "rec:p" for m in built["whole"][0].mentions))
        self.assertEqual([m.surface for m in built["named"][0].mentions], ["محمد بن يحيى", "أحمد بن محمد", "ابن محبوب", "أبي عبد الله"])
        self.assertEqual([m.inherited_from is None for m in built["named"][0].mentions], [False, False, True, True])
        self.assertEqual(built["elsewhere"][0].suspension, "back_reference")       # «عن يونس»: not in the previous chain
        self.assertEqual(depth, {"whole": 1, "named": 2})

    def test_fused_co_transmitters_become_one_level(self):
        mention = cb.BuiltMention("أبي و محمد بن الحسن بن أحمد بن الوليد")
        self.assertEqual([m.surface for m in cb.split_fused(mention, Counter())], ["أبي", "محمد بن الحسن بن أحمد بن الوليد"])


class SunniChainRules(unittest.TestCase):
    """The Sunni audit's confirmed cases (chain-audit/sunni/fixtures.json: real rows of production)."""

    @classmethod
    def setUpClass(cls):
        data = json.loads((HERE.parent / "chain-audit" / "sunni" / "fixtures.json").read_text(encoding="utf-8"))
        cls.text = {h["id"]: h["text_ar"] for h in data["hadiths"]}
        by_chain: dict = {}
        for mention in data["mentions"]:
            by_chain.setdefault(mention["chain_id"], []).append(mention)
        cls.branches: dict = {}
        for chain in sorted(data["chains"], key=lambda c: (c["hadith_id"], c["branch"])):
            surfaces = [m["surface_ar"] for m in sorted(by_chain.get(chain["id"], []), key=lambda m: m["position"])]
            cls.branches.setdefault(chain["hadith_id"], []).append(surfaces)

    def rebuilt(self, hadith_id: str) -> list[list[str]]:
        chains = cb.build_sunni_chains(self.text[hadith_id], self.branches[hadith_id], Counter())
        return [[m.surface for m in chain.mentions] for chain in chains]

    def test_flattened_tahwil_is_split_at_its_seam(self):
        routes = self.rebuilt("hadith:k6:28195")           # al-Awzaʿi twice: «... عن ابن شهاب. ح وأخبرنا عمرو بن عثمان ...»
        self.assertEqual(len(routes), 2)
        self.assertEqual(routes[0][:2], ["محمود بن خالد", "عمر"])
        self.assertEqual(routes[1][0], "عمرو بن عثمان")
        self.assertTrue(all(route.count("الأوزاعي") == 1 for route in routes))

    def test_a_single_route_without_a_seam_is_unchanged(self):
        self.assertEqual(self.rebuilt("hadith:k6:10025"), self.branches["hadith:k6:10025"])

    def test_formula_words_leave_the_name(self):
        cases = [("ابن جريج بهذا الحديث", "ابن جريج"), ("النضر بن شميل كلاهما", "النضر بن شميل"),
                 ("سهيل في هذا الإسناد بمعنى حديث مالك فليكفر يمينه", "سهيل"), ("بهذا الإسناد", None),
                 ("تقاربا في اللفظ", None), ("عبد الله بن عمر", "عبد الله بن عمر")]
        for surface, expected in cases:
            with self.subTest(surface):
                self.assertEqual(cb.formula_trim(surface)[0], expected)

    def test_missing_link_is_flagged_after_a_fully_named_student(self):
        deaths = {"s": 239, "t": 105, "u": 200}
        cases = [(["x", "s", "t"], ["أ", "عثمان بن أبي شيبة", "حميد"], 1),   # k6:11793 shape: 134 years
                 (["x", "u", "t"], ["أ", "عثمان بن أبي شيبة", "حميد"], None),  # 95 years: a plausible pair
                 (["x", "s", "t"], ["أ", "عثمان", "حميد"], None)]               # a one-word student: not decided here
        for identities, surfaces, expected in cases:
            with self.subTest(identities=identities, surfaces=surfaces):
                self.assertEqual(cb.missing_link_after(identities, deaths, surfaces), expected)


if __name__ == "__main__":
    unittest.main(verbosity=1)
