"""Table-driven tests for the projection rules in export_postgres.py (pure logic with real branching)."""

from __future__ import annotations

import csv
import gzip
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import export_postgres as ep  # noqa: E402


class GradeRules(unittest.TestCase):
    def test_map_to_canonical_matches_grade_taxonomy(self):
        cases = [
            ("صحيح", "sahih"),
            ("  صحيح   ", "sahih"),
            ("حسن كالصحيح", "sahih"),          # exact compound
            ("ضعيف على المشهور معتبر عند ي", "mu_tabar"),
            ("ضعيف على المشهور وهو معتبر", "mu_tabar"),  # contains: معتبر wins over ضعيف
            ("مجهول", "majhul"),
            ("موثق", "muwaththaq"),
            ("لم يخرجه", "ungraded"),
            ("ثابت", "ungraded"),              # Pure Canon inclusion label is not a grade
            ("Sahih", "sahih"),
            ("مختلف فيه", "mukhtalaf"),
            ("موضوع", "mawdu"),
            ("حسن ی", "hasan"),                # Persian ya folded before matching
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(ep.map_to_canonical(raw), expected)

    def test_clean_grade_detail_fixes_ocr_splits(self):
        self.assertEqual(ep.clean_grade_detail("صحيح على الظاه ر"), "صحيح على الظاهر")
        self.assertEqual(ep.clean_grade_detail(""), "")

    def test_parse_gradings_full(self):
        value = ("Allamah Baqir al-Majlisi:  صحيح     (Mirʾāt al-ʿUqūl fī Sharḥ Akhbār Āl al-Rasūl (1/25)) | "
                 "Shaykh Baqir al-Behbudi: لم يخرجه (Sahih al-Kafi) | malformed segment")
        entries, skipped = ep.parse_gradings_full(value)
        self.assertEqual(skipped, 1)
        self.assertEqual([entry["scholar"] for entry in entries], ["Allamah Baqir al-Majlisi", "Shaykh Baqir al-Behbudi"])
        self.assertEqual(entries[0]["grade"], "صحيح")
        self.assertEqual(entries[0]["citation"], "Mirʾāt al-ʿUqūl fī Sharḥ Akhbār Āl al-Rasūl (1/25)")
        self.assertEqual(entries[1]["citation"], "Sahih al-Kafi")

    def test_split_citation(self):
        cases = [
            ("Mirʾāt al-ʿUqūl (1/25)", ("Mirʾāt al-ʿUqūl", "1", "25")),
            ("Sahih al-Kafi (1/ 1)", ("Sahih al-Kafi", "1", "1")),
            ("Sahih al-Kafi", ("Sahih al-Kafi", None, None)),
            ("", (None, None, None)),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(ep.split_citation(raw), expected)


class LexiconRules(unittest.TestCase):
    def test_parse_hijri_year_ports_io_ts(self):
        cases = [
            (("11", "11 AH/632 CE"), 11),
            (("53", "53 BH/570 CE (9th Rabi' awwal)"), -53),
            (("53", "53 BHمكة"), -53),          # ASCII boundary next to Arabic, as JS \b sees it
            (("53", "53 BHX"), 53),             # BH inside a Latin word is not Before Hijra
            (("c. 120", None), None),           # ranges and qualified tokens stay raw only
            (("١٢٠", None), None),              # Arabic-Indic digits are not an exact ASCII token
            (("", None), None),
        ]
        for (raw, context), expected in cases:
            with self.subTest(raw=raw, context=context):
                self.assertEqual(ep.parse_hijri_year(raw, context), expected)

    def test_english_name(self):
        cases = [
            ("Abu Bakr As-Siddique ( أبو بكر الصديق ( رضي الله عنه", "Abu Bakr As-Siddique"),
            ("Prophet Muhammad(saw) ( محمّد صلّی الله", "Prophet Muhammad(saw)"),
            ("Plain English Only", "Plain English Only"),
            ("محمد بن مسلم", None),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(ep.english_name(raw), expected)


class IsnadRules(unittest.TestCase):
    def test_review_unit_ids(self):
        coarse_a, fine_a = ep.review_unit_ids("سفيان", "الزهري", "الحميدي", "sunni:bukhari")
        coarse_b, fine_b = ep.review_unit_ids("سفيان", "الزهري", "علي", "sunni:bukhari")
        coarse_c, _ = ep.review_unit_ids("سفيان", "منصور", "الحميدي", "sunni:bukhari")
        self.assertEqual(coarse_a, coarse_b)    # coarse ignores the student
        self.assertNotEqual(fine_a, fine_b)     # fine does not
        self.assertNotEqual(coarse_a, coarse_c)  # teacher context separates units
        self.assertEqual(len(coarse_a), 64)


RECONCILED = Path(__file__).resolve().parent.parent / "reconciled"
PROJECTION = Path(os.environ.get(
    "PG_PROJECTION",
    Path(__file__).resolve().parent.parent / "development" / "pg-load-2026-11-21" / "projection-v3"))


def sidecar_rows(name: str, record_ids: set[str]) -> dict[str, dict]:
    rows = {}
    with gzip.open(RECONCILED / name, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row["record_id"] in record_ids:
                rows[row["record_id"]] = row
    return rows


class IdentityRules(unittest.TestCase):
    """Owner decisions 2026-11-21: every candidate kept with its basis; the machine-reviewed identity stands only when confirmed and uncontested."""

    def test_verified_narrator(self):
        confirmed = "source_index_confirmed_by_text"
        cases = [
            ([("n:1", "name_exact"), ("n:1", confirmed)], "n:1"),               # name and source agree
            ([("n:1", confirmed)], "n:1"),
            ([("n:2", "name_exact"), ("n:1", confirmed)], None),               # contested: shown, never settled
            ([("n:3", "name_kunya_only"), ("n:1", confirmed)], "n:1"),         # a kunya-only match is a label, never a contest
            ([("n:3", "name_kunya_only"), ("n:2", "name_exact"), ("n:1", confirmed)], None),  # a name match still contests
            ([("n:1", "name_exact"), ("n:1", "source_index")], None),          # agreement without confirmation
            ([("n:1", "name_spelling_fold")], None),
            ([], None),
        ]
        for candidates, expected in cases:
            with self.subTest(candidates=candidates):
                self.assertEqual(ep.verified_narrator(candidates), expected)

    def test_candidate_agreement(self):
        cases = [([], "none"), (["n:1"], "one"), (["n:1", "n:1"], "one"), (["n:1", "n:2"], "differ")]
        for narrators, expected in cases:
            with self.subTest(narrators=narrators):
                self.assertEqual(ep.candidate_agreement(narrators), expected)


BUNDLE_HADITHS = Path(__file__).resolve().parent.parent / "development" / "pg-load-2026-11-21" / "bundle" / "nodes" / "hadiths.csv"


def bundle_hadiths(record_ids: set[str]) -> dict[str, dict[str, str]]:
    """Real hadith rows from the bundle the development database was loaded from, keyed by record_id."""
    found: dict[str, dict[str, str]] = {}
    with BUNDLE_HADITHS.open("rt", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        names = [ep.typed_column_name(column) if not column.startswith(":") else None for column in next(reader)]
        for values in reader:
            row = {name: value for name, value in zip(names, values) if name}
            if row["record_id"] in record_ids:
                found[row["record_id"]] = row
                if len(found) == len(record_ids):
                    break
    return found


class NonRulingRule(unittest.TestCase):
    """grading-recovery's classification, reused: a non-ruling never becomes an assessment."""

    def test_non_ruling_reason(self):
        cases = [
            ("لم يخرجه", "not_included_by_grader"),       # al-Bihbudi's Sahih al-Kafi: "he did not include it"
            ("لم يخرجه ", "not_included_by_grader"),
            ("سكت عنه", "grader_silent"),
            ("كالسابق", "back_reference_only"),
            ("صحيح", None),
            ("ضعيف على المشهور", None),
        ]
        for grade, expected in cases:
            with self.subTest(grade=grade):
                self.assertEqual(ep.non_ruling_reason(grade), expected)


@unittest.skipUnless(BUNDLE_HADITHS.is_file(), "development bundle not present")
class MatnRuleOnRealRows(unittest.TestCase):
    """A matn is stored only when it is the report's own (review 2026-11-21)."""

    @classmethod
    def setUpClass(cls):
        cls.rows = bundle_hadiths({"k6:23658", "k6:1"})
        cls.isolator = ep.matn_isolator()

    def matn(self, record_id: str):
        row = self.rows[record_id]
        return ep.accepted_matn(self.isolator, record_id, row["text_ar"], ep.blank_to_none(row["matn_ar"]))

    def test_another_reports_matn_is_not_stored(self):
        # Tirmidhi k6:23658: the upstream fill joined on (source, hadith number) and attached a neighbour's matn.
        stored, reason = self.matn("k6:23658")
        self.assertIsNone(stored)
        self.assertIn(reason, {"matn_column_not_in_text", "matn_column_includes_chain"})

    def test_the_reports_own_matn_is_stored(self):
        stored, reason = self.matn("k6:1")       # Bukhari 1: the matn column sits inside its own text
        self.assertIsNone(reason)
        self.assertEqual(stored, self.rows["k6:1"]["matn_ar"])

    def test_blank_matn_is_no_matn(self):
        self.assertEqual(ep.accepted_matn(self.isolator, "k6:1", "نص", None), (None, None))


class CorrespondenceProjection(unittest.TestCase):
    """Pairs bind to each side's loaded Arabic; a changed text drops the pair and counts it."""

    # A real pair from report-correspondence-v1 (Bukhari 1 / Muslim 5036).
    PAIR = {
        "pair_id": "report-pair:e385045b60639fa39743", "hadith_id_a": "hadith:k6:1", "hadith_id_b": "hadith:k6:12318",
        "arabic_sha256_a": "6636241d13338ee3a62c1cbe0f7b254ae2ea9bd537e0cf84d88c77d0b6c595ab",
        "arabic_sha256_b": "9086b1c82fe75611fb30b21d8bde69ed851b38b751b57e332d33348cb0b1bf57",
        "scope": "cross_work_same_tradition", "class": "same_report_variant_wording", "jaccard": "0.3818",
        "containment": "0.5575", "global_containment": "0.5575", "length_ratio": "0.9826", "shared_shingles": "63",
        "shingles_a": "115", "shingles_b": "113", "words_a": "30", "words_b": "33", "score_band": "jaccard_0.3-0.4",
        "matn_split_a": "reliable", "matn_split_b": "reliable", "cluster_id": "report-cluster:a01d6f733a6ab9952cce",
        "basis": "textual_overlap", "method_version": "report-correspondence-v1",
    }

    def write_output(self, directory: Path, input_sha: str) -> None:
        with (directory / "report_correspondence_pairs.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(self.PAIR))
            writer.writeheader()
            writer.writerow(self.PAIR)
        with (directory / "report_correspondence_cluster_members.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["cluster_id", "hadith_id", "star_centre", "is_star_centre", "method_version"])
            for hadith_id in ("hadith:k6:1", "hadith:k6:12318"):
                writer.writerow([self.PAIR["cluster_id"], hadith_id, "hadith:k6:1", str(hadith_id == "hadith:k6:1"),
                                 "report-correspondence-v1"])
        (directory / "summary.json").write_text(json.dumps({
            "inputs_sha256": {"x/all_hadiths_unified.incomplete.csv.gz": input_sha},
            "parameters": {"method_version": "report-correspondence-v1"}}), encoding="utf-8")

    def test_pair_binds_to_loaded_arabic(self):
        self.assertEqual(ep.correspondence_pair_id("hadith:k6:1", "hadith:k6:12318"), self.PAIR["pair_id"])
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.write_output(directory, "in")
            loaded = {"hadith:k6:1": {"arabic_sha256": self.PAIR["arabic_sha256_a"]},
                      "hadith:k6:12318": {"arabic_sha256": self.PAIR["arabic_sha256_b"]}}
            pairs, members, counts, _ = ep.project_correspondences(directory, loaded, "in")
            self.assertEqual([row[0] for row in pairs], [self.PAIR["pair_id"]])
            self.assertEqual(len(members), 2)
            # The same pair against a changed Muslim text: dropped and counted, never loaded.
            loaded["hadith:k6:12318"] = {"arabic_sha256": "0" * 64}
            pairs, _, counts, _ = ep.project_correspondences(directory, loaded, "in")
            self.assertEqual(pairs, [])
            self.assertEqual(counts["pairs_dropped:arabic_hash_changed"], 1)
            # Output built from another corpus is refused outright.
            with self.assertRaisesRegex(ep.ProjectionError, "another unified CSV"):
                ep.project_correspondences(directory, loaded, "other")


@unittest.skipUnless((RECONCILED / "k6_source_index.jsonl.gz").is_file(), "reconciled sidecars not built")
class SidecarRulesOnRealRows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.k6 = sidecar_rows("k6_source_index.jsonl.gz", {"k6:1", "k6:47"})
        cls.canon = sidecar_rows("pure_canon_chain.jsonl.gz", {"pure-canon:pc_9"})
        cls.no_chain = sidecar_rows("no_chain_in_source.jsonl.gz", {"pure-canon:pc_236"})

    def test_full_agreement_maps_every_position_to_its_source_id(self):
        row = self.k6["k6:1"]
        alignment = ep.align_source_index(row, row["text_branches"])
        self.assertEqual(alignment, {(0, position): (position, False) for position in range(6)})
        # Any difference from the extracted branches maps nothing rather than shifting identities.
        self.assertIsNone(ep.align_source_index(row, [row["text_branches"][0][:-1]]))

    def test_a_tahwil_trunk_inherits_its_twins_source_id_but_a_convergence_does_not(self):
        row = self.k6["k6:47"]       # روح عن عوف عن الحسن / محمد عن أبي هريرة
        alignment = ep.align_source_index(row, row["text_branches"])
        self.assertEqual(alignment[(1, 0)], (0, True))        # the shared opening, written once in the Arabic
        self.assertEqual(alignment[(1, 2)], (2, True))
        self.assertEqual(alignment[(1, 3)], (4, False))       # محمد, corroborated in its own branch
        self.assertNotIn((0, 4), alignment)                    # أبي هريرة at the convergence: not inherited

    def test_pure_canon_chain_replaces_the_matn_extraction_and_no_chain_drops_invented_chains(self):
        hadith_info = {"hadith:pure-canon:pc_9": {"arabic_sha256": self.canon["pure-canon:pc_9"]["text_ar_sha256"]},
                       "hadith:pure-canon:pc_236": {"arabic_sha256": self.no_chain["pure-canon:pc_236"]["text_ar_sha256"]}}
        record_to_hadith = {"pure-canon:pc_9": "hadith:pure-canon:pc_9", "pure-canon:pc_236": "hadith:pure-canon:pc_236"}
        invented = {"id": "chain:pure-canon:pc_9:0000", "branch": 0, "mentions": [("m", "اركبها", "اركبها")]}
        branches = {"hadith:pure-canon:pc_9": [invented], "hadith:pure-canon:pc_236": [dict(invented)]}
        counts = ep.apply_chain_sidecars(branches, self.no_chain, self.canon, hadith_info, record_to_hadith, str)
        self.assertNotIn("hadith:pure-canon:pc_236", branches)
        [chain] = branches["hadith:pure-canon:pc_9"]
        self.assertEqual(chain["extraction_method"], "source_chain_field")
        self.assertEqual([surface for _, surface, _ in chain["mentions"]],
                         ["إسحاق ابن عيسى", "ليث", "ابن شهاب", "عروة", "عائشة"])
        self.assertEqual(chain["mentions"][0][0], "mention:pure-canon:pc_9:0000:0000")
        self.assertEqual(counts["pure_canon_chain:text_ar_chains_replaced"], 1)
        # A sidecar bound to other Arabic is refused, never applied.
        hadith_info["hadith:pure-canon:pc_9"]["arabic_sha256"] = "0" * 64
        with self.assertRaisesRegex(ep.ProjectionError, "different Arabic"):
            ep.apply_chain_sidecars({}, {}, self.canon, hadith_info, record_to_hadith, str)


@unittest.skipUnless((PROJECTION / "canonical" / "manifest.json").is_file(), "full projection not built")
class ProjectionOutputOnRealRows(unittest.TestCase):
    """Real mentions read back from the projection the development database was loaded from."""

    @classmethod
    def setUpClass(cls):
        wanted = {"hadith:k6:11089", "hadith:k6:11880", "hadith:k6:10000", "hadith:k6:10035",
                  "hadith:thaqalayn:0020ba715081e8ba3e669657"}
        canonical = PROJECTION / "canonical"
        with (canonical / "chain_mentions.csv").open(encoding="utf-8", newline="") as handle:
            cls.mentions = {row["id"]: row for row in csv.DictReader(handle) if row["hadith_id"] in wanted}
        cls.candidates: dict[str, list[tuple[str, str]]] = {}
        with (canonical / "chain_mention_candidates.csv").open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                if row["hadith_id"] in wanted:
                    cls.candidates.setdefault(row["mention_id"], []).append((row["narrator_id"], row["basis"]))
        with (canonical / "narrators.csv").open(encoding="utf-8", newline="") as handle:
            cls.placeholders = {row["id"]: row["placeholder_reason"] for row in csv.DictReader(handle)
                                if row["placeholder_reason"]}

    def test_name_match_and_source_index_agree_and_the_link_is_verified(self):
        mention = "mention:k6:11880:0000:0000"            # عبد الله بن عبد الرحمن الدارمي
        self.assertEqual(sorted(self.candidates[mention]), [
            ("narrator:rawi:30025", "name_exact"), ("narrator:rawi:30025", "source_index_confirmed_by_text")])
        self.assertEqual(self.mentions[mention]["narrator_id"], "narrator:rawi:30025")
        self.assertEqual(self.mentions[mention]["resolution"], "source_index")

    def test_disagreeing_identities_are_both_emitted_and_nothing_is_verified(self):
        mention = "mention:k6:11089:0000:0001"            # حسين بن محمد
        self.assertEqual(sorted(self.candidates[mention]), [
            ("narrator:rawi:20384", "source_index"), ("narrator:rawi:39284", "name_exact")])
        self.assertEqual(self.mentions[mention]["narrator_id"], "")
        self.assertEqual(self.mentions[mention]["resolution"], "unresolved")

    def test_kunya_only_match_is_labelled_and_does_not_contest_a_confirmed_source_id(self):
        mention = "mention:k6:10000:0000:0001"            # أبو معاوية
        self.assertEqual(sorted(self.candidates[mention]), [
            ("narrator:rawi:19383", "name_kunya_only"), ("narrator:rawi:20354", "source_index_confirmed_by_text")])
        self.assertEqual(self.placeholders["narrator:rawi:19383"], "kunya_only_name")
        self.assertEqual(self.mentions[mention]["narrator_id"], "narrator:rawi:20354")  # owner decision 2026-11-21

    def test_an_imami_mention_has_no_automatic_candidate(self):
        imami = [mention for mention, row in self.mentions.items() if row["hadith_id"].startswith("hadith:thaqalayn:")]
        self.assertTrue(imami)
        self.assertTrue(all(mention not in self.candidates for mention in imami))

    def test_a_placeholder_row_is_never_targeted(self):
        mention = "mention:k6:10035:0000:0002"            # شعبة: the Shykh stub 29483 holds the bare key
        self.assertEqual(self.mentions[mention]["surface_ar"], "شعبة")
        self.assertEqual(self.candidates[mention], [("narrator:rawi:20020", "source_index")])
        self.assertEqual(self.placeholders["narrator:rawi:29483"], "unidentified_shaykh_marker")
        for mention_candidates in self.candidates.values():
            for narrator_id, basis in mention_candidates:
                self.assertTrue(basis == "name_kunya_only" or narrator_id not in self.placeholders)


class CsvCells(unittest.TestCase):
    def test_cells(self):
        cases = [(None, None), ("", None), (ep.Verbatim(""), ""), (True, "true"), (False, "false"), (3, "3"),
                 (1.0, "1.0"), ("نص", "نص")]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(ep.cell(value), expected)

    def test_blank_to_none_keeps_text_as_written(self):
        self.assertIsNone(ep.blank_to_none("   "))
        self.assertEqual(ep.blank_to_none(" 1 "), " 1 ")


class Refusals(unittest.TestCase):
    def test_bundle_without_import_ready_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "manifest.json").write_text(json.dumps({"content_sha256": "x", "files": []}), encoding="utf-8")
            (root / "validation_report.json").write_text(
                json.dumps({"import_ready": False, "content_sha256": "x"}), encoding="utf-8")
            with self.assertRaisesRegex(ep.ProjectionError, "import_ready"):
                ep.Bundle(root)

    def test_header_must_equal_live_catalog(self):
        catalog = {"sources": [{"name": "id", "role": "csv"}, {"name": "slug", "role": "csv"},
                               {"name": "updated_at", "role": "bookkeeping"}]}
        ep.check_header(catalog, "sources", ["slug", "id"])
        with self.assertRaisesRegex(ep.ProjectionError, "missing=\\['slug'\\]"):
            ep.check_header(catalog, "sources", ["id"])
        with self.assertRaisesRegex(ep.ProjectionError, "extra=\\['updated_at'\\]"):
            ep.check_header(catalog, "sources", ["id", "slug", "updated_at"])


if __name__ == "__main__":
    unittest.main()
