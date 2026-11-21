"""Table-driven tests on real rows for the identity rules: provider English, Imam kunyas, the machine-reviewed tier."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import external_identity as xid  # noqa: E402
from imam_kunya import ImamKunyaRegister  # noqa: E402
from provider_english import provider_form  # noqa: E402


class ProviderEnglishForms(unittest.TestCase):
    """Rows of diagnostics/chain-reconciliation/output/imami_surface_lexicon.jsonl.gz (top forms, real counts)."""

    def test_dominant_form_that_renders_the_name(self):
        cases = [
            ("ابي عبد الله", {"Abu ‘Abdillah": 714, "Abu Abdullah": 334, "Abu Abdillah": 83, "abu ‘Abdallah": 81,
                              "Imam Jafar ibn Muhammad Al-Sadiq": 79}, "Abu ‘Abdillah"),
            ("علي بن ابراهيم", {"Ali ibn Ibrahim": 1265, "Ali Bin Ibrahim": 30, "Ali b. Ibrahim": 10}, "Ali ibn Ibrahim"),
            ("ابي جعفر", {"abu Ja’far": 196, "Abu Ja'far Imam Muhammad ibn Ali Al-Baqir": 56,
                          "Imam Muhammad ibn Ali Al-Baqir": 49, "abu Ja‘far": 36}, "Abu Ja’far"),       # variants pooled
            ("محمد بن اسماعيل", {"Muhammad ibn ’Isma‘il": 68, "Muhammad ibn ‘Isma’il": 34,
                                 "Muhammad ibn Isma'il": 20}, "Muhammad ibn ’Isma‘il"),
            ("ابيه", {"father": 1899, "father, Imam Muhammad ibn Ali Al-Baqir": 38, "grandfather": 22}, "father"),
            ("عدة من اصحابنا", {"A number of our people": 1117, "A number of our companions": 37},
             "A number of our people"),
        ]
        for key, forms, expected in cases:
            with self.subTest(key=key):
                self.assertEqual(provider_form(key, forms)[0], expected)

    def test_refuses_a_neighbours_name_or_a_clause(self):
        cases = [
            # The owner's example chain (Ma'ani al-Akhbar): every pairing of this key is shifted by one name.
            ("بكر بن عبد الله بن حبيب", {"Tamim ibn Buhlool": 6, "Uthman ibn Ubayd": 1}),
            ("سعد بن عبد الله", {"father - may God be pleased with him - narrated": 98, "Sa’d ibn ‘Abdillāh": 52}),
            ("محمد بن احمد بن يحيي بن عمران الاشعري", {"Muhammad ibn Yahya al-Attar": 9}),
            ("عنه", {"(narrator of the Hadith above)": 190, "the narrator of the previous Hadith": 94}),
            ("ابيه محمد بن علي", {"father Muhammad ibn Ali (s)": 5}),     # kinship accepted for أبيه alone
        ]
        for key, forms in cases:
            with self.subTest(key=key):
                self.assertIsNone(provider_form(key, forms))


class ImamKunyas(unittest.TestCase):
    register = ImamKunyaRegister.load()

    def test_convention_and_shared_kunyas(self):
        cases = [
            # (surface as extracted, tradition, marker after it in the text, basis, Imam ordinals)
            ("أبا عبد الله", "Imami", True, "imam_kunya_convention", ["6"]),          # thaqalayn:06c871a7...
            ("أبي عبد الله ع", "Imami", False, "imam_kunya_convention", ["6"]),       # marker inside the surface
            ("أبي الحسن الرضا", "Imami", True, "imam_kunya_convention", ["8"]),
            ("أبي الحسن الأول", "Imami", True, "imam_kunya_convention", ["7"]),
            ("أبي جعفر الثاني", "Imami", True, "imam_kunya_convention", ["9"]),
            ("أبي إبراهيم", "Imami", True, "imam_kunya_convention", ["7"]),
            ("أبي جعفر", "Imami", True, "imam_kunya_candidate", ["5", "9"]),          # shared, no qualifier
            ("أبي الحسن", "Imami", True, "imam_kunya_candidate", ["7", "8", "10"]),
        ]
        for surface, tradition, marker, basis, ordinals in cases:
            with self.subTest(surface=surface):
                match = self.register.match(surface, tradition, marker)
                self.assertEqual(match.basis, basis)
                self.assertEqual([imam.split(":")[-1] for imam in match.imam_ids], ordinals)

    def test_never_outside_the_rule(self):
        cases = [
            ("أبي عبد الله", "Sunni", True),          # an Imami convention only
            ("أبي عبد الله", "Imami", False),         # no honorific marker
            ("أبي عبد الله البرقي", "Imami", True),   # other words after the kunya: a different man
            ("أبو جعفر محمد بن علي بن الحسين", "Imami", False),   # al-Saduq himself, no marker
            ("أبي بصير", "Imami", True),              # not an Imam's kunya
        ]
        for surface, tradition, marker in cases:
            with self.subTest(surface=surface, tradition=tradition):
                self.assertIsNone(self.register.match(surface, tradition, marker))


class MachineReviewedTier(unittest.TestCase):
    """Candidates as they occur in the projection (mention ids in comments); person keys from the link sidecar."""

    keys = xid.PersonKeys(lexicon_link={"narrator:hadith-kg:4967": "narrator:rawi:18"},
                          riwayat_to_kg={"narrator:riwayat:N0000609": "narrator:hadith-kg:4967"})

    def test_standing_identity(self):
        cases = [
            ("K6 confirmed; hadith-kg and Riwayat name the same man through the links (k6:19122:0001:0004)",
             [xid.Candidate("narrator:rawi:18", "source_index_confirmed_by_text"),
              xid.Candidate("narrator:hadith-kg:4967", "source_hadith_kg"),
              xid.Candidate("narrator:riwayat:N0000609", "source_riwayat_confirmed_by_text", origin="upstream_annotation")],
             ("narrator:rawi:18", "source_index_confirmed_by_text")),
            ("two independent sources agree: unconfirmed K6 and unconfirmed hadith-kg on one person",
             [xid.Candidate("narrator:rawi:18", "source_index"), xid.Candidate("narrator:hadith-kg:4967", "source_hadith_kg")],
             ("narrator:rawi:18", "two_sources_agree")),
            ("Riwayat's Sunni id is hadith-kg's own: Riwayat + K6 is not two sources",
             [xid.Candidate("narrator:rawi:18", "source_index"),
              xid.Candidate("narrator:riwayat:N0000609", "source_riwayat", origin="upstream_annotation")],
             None),
            ("Riwayat confirmed from Thaqalayn's annotation (Imami)",
             [xid.Candidate("narrator:riwayat:N0152727", "source_riwayat_confirmed_by_text", origin="upstream_annotation")],
             ("narrator:riwayat:N0152727", "source_riwayat_confirmed_by_text")),
            ("Riwayat's automatic linker is shown but never counted",
             [xid.Candidate("narrator:riwayat:N0157112", "source_riwayat_confirmed_by_text", origin="riwayat_automatic_linking")],
             None),
            ("a label-like Riwayat record cannot carry the tier",
             [xid.Candidate("narrator:riwayat:N0001", "source_riwayat_confirmed_by_text", origin="upstream_annotation",
                            label_like=True)],
             None),
            ("Imam kunya convention; the Riwayat kunya label beside it is a label, not a contest",
             [xid.Candidate("narrator:imam:6", "imam_kunya_convention"),
              xid.Candidate("narrator:riwayat:N0153369", "source_riwayat", origin="upstream_annotation",
                            placeholder="kunya_only_name")],
             ("narrator:imam:6", "imam_kunya_convention")),
            ("contested: K6 and a name match name two lexicon rows",
             [xid.Candidate("narrator:rawi:20012", "source_index_confirmed_by_text"),
              xid.Candidate("narrator:rawi:20005", "name_exact")],
             None),
            ("not comparable across authorities without a link: K6 stands",
             [xid.Candidate("narrator:rawi:20012", "source_index_confirmed_by_text"),
              xid.Candidate("narrator:hadith-kg:3443", "source_hadith_kg_confirmed_by_text")],
             ("narrator:rawi:20012", "source_index_confirmed_by_text")),
            ("shared Imam kunya alone: candidates only",
             [xid.Candidate("narrator:imam:5", "imam_kunya_candidate"), xid.Candidate("narrator:imam:9", "imam_kunya_candidate")],
             None),
        ]
        for label, candidates, expected in cases:
            with self.subTest(label):
                self.assertEqual(xid.standing_identity(candidates, self.keys), expected)

    def test_a_linked_external_claim_naming_someone_else_contests(self):
        keys = xid.PersonKeys(lexicon_link={"narrator:hadith-kg:3443": "narrator:rawi:20005"})
        candidates = [xid.Candidate("narrator:rawi:20012", "source_index_confirmed_by_text"),
                      xid.Candidate("narrator:hadith-kg:3443", "source_hadith_kg_confirmed_by_text")]
        self.assertIsNone(xid.standing_identity(candidates, keys))


class RiwayatLabels(unittest.TestCase):
    def test_label_reasons(self):
        shared = xid.shared_riwayat_names([
            {"name_ar": "أَحْمَدَ بْنِ مُحَمَّدٍ", "claims_in_our_mentions": 900},
            {"name_ar": "أحمد بن محمد", "claims_in_our_mentions": 300},
            {"name_ar": "علي بن إبراهيم", "claims_in_our_mentions": 5522},
            {"name_ar": "ـعلي بن إبراهيم", "claims_in_our_mentions": 4},
        ])
        cases = [
            ({"name_ar": "أحمد بن محمد", "flags": []}, "name_held_by_several_ids"),
            ({"name_ar": "علي بن إبراهيم", "flags": []}, None),             # one dominant id; the rest are artefacts
            ({"name_ar": "ابن فضال", "flags": []}, "nasab_only_label"),
            ({"name_ar": "أَبِي عَبْدِ اللَّهِ ع", "flags": [], "name_placeholder_reason": "kunya_only_name"},
             "placeholder:kunya_only_name"),
            ({"name_ar": "ذر بن عبد الله بن زرارة", "flags": ["merged_names_suspect"]}, "riwayat_flag:merged_names_suspect"),
        ]
        for row, expected in cases:
            with self.subTest(name=row["name_ar"]):
                self.assertEqual(xid.riwayat_label_reason(row, shared), expected)


if __name__ == "__main__":
    unittest.main()
