import csv
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HADITH_DATA_DIR = Path(__file__).resolve().parents[1]
if str(HADITH_DATA_DIR) not in sys.path:
    sys.path.insert(0, str(HADITH_DATA_DIR))

from neo4j_export.contract import (
    NODE_FILES,
    RAWI_COLUMNS,
    RAWI_PROFILE_COLUMNS,
    RAWI_PROFILE_PROVENANCE,
    RAWI_PROFILE_REVIEW_STATE,
    SOURCE_QUALITY_EXCLUSIONS,
    UNIFIED_COLUMNS,
)
from neo4j_export.export_bundle import export_bundle
from neo4j_export.validate_bundle import validate_bundle


def _base_row(**overrides):
    row = {column: "" for column in UNIFIED_COLUMNS}
    row.update(
        {
            "id": "1",
            "hadith_id": "1",
            "source": "Sahih Bukhari",
            "tradition": "Sunni",
            "chapter_no": "1",
            "hadith_no": "1",
            "chapter": "Revelation",
            "chain_indx": "1,2",
            "text_ar": (
                "حدثنا زيد، عن عمرو، عن النبي صلى الله عليه وسلم قال: نص.\n"
                "سطر عربي ثان."
            ),
            "text_en": "A translated report.\nA second English line.",
            "sanad": "حدثنا زيد، عن عمرو",
            "record_id": "k6:test-1",
            "source_record_id": "test-1",
            "provenance_source": "all_hadiths_clean.csv.gz:k6_snapshot",
            "translation_status": "complete",
            "translation_source": "fixture:source-translation",
            "translation_review_status": "source_status_unknown",
        }
    )
    row.update(overrides)
    return row


def _write_fixture(root: Path):
    dataset = root / "schema-v2.csv"
    rawis = root / "rawis.csv"
    rows = [
        _base_row(),
        _base_row(
            id="2",
            hadith_id="2",
            source="Al-Kafi",
            source_work_id="imami:al-kafi",
            source_display_label="Al-Kafi Volume 1",
            tradition="Imami",
            volume="1",
            chapter_no="2",
            chapter="Knowledge",
            chain_indx="",
            text_ar="حدثنا جعفر، عن محمد، قال: خبر إمامي.",
            text_en="An Imami report.",
            record_id="thaqalayn:test-2",
            source_record_id="provider-file:1|hadith:2",
            provenance_source="shia-hadith/v2_books",
            provider_file_id="1",
            provider_book_id="Al-Kafi-Volume-1-Kulayni",
            url="https://thaqalayn.net/hadith/1/2/1/1",
            translation_source="Thaqalayn API V2",
            translation_review_status="source_provided",
        ),
        _base_row(
            id="3",
            hadith_id="3",
            source="Musnad al-Imam Zayd ibn Ali",
            source_work_id="",
            source_display_label="Musnad Zayd",
            tradition="Zaydi",
            volume="1",
            chapter_no="3",
            chapter="Purification",
            chain_indx="",
            text_ar=(
                "حدثنا زيد، عن عمرو، ح وحدثنا بكر، عن خالد، عن عمرو، "
                "عن النبي صلى الله عليه وسلم قال: خبر."
            ),
            text_en="A branched Zaydi report.",
            record_id="openiti:zaydi:test-3",
            source_record_id="zaydi|3",
            provenance_source="zaydi-hadith/parsed_hadiths.json",
            translation_source="zaydi-hadith/parsed_hadiths.json",
            translation_review_status="machine_unreviewed",
        ),
        _base_row(
            id="4",
            hadith_id="4",
            source="al-Jami al-Sahih (Musnad al-Rabi ibn Habib)",
            source_work_id="",
            source_display_label="Musnad al-Rabi",
            tradition="Ibadi",
            volume="1",
            chapter_no="4",
            chapter="Prayer",
            chain_indx="",
            text_ar="حدثنا الربيع، عن جابر، قال: خبر إباضي.",
            text_en="An Ibadi report.",
            record_id="openiti:ibadi:test-4",
            source_record_id="ibadi|4",
            provenance_source="ibadi-hadith/parsed_hadiths.json",
            translation_source="ibadi-hadith/parsed_hadiths.json",
            translation_review_status="machine_unreviewed",
        ),
        _base_row(
            id="5",
            hadith_id="5",
            source="Kitab al-Ghayba (Tusi)",
            source_work_id="imami:kitab-al-ghayba-tusi",
            source_display_label="Kitab al-Ghayba",
            tradition="Imami",
            volume="1",
            chapter_no="0",
            chapter="Introduction",
            chain_indx="",
            text_ar="مقدمة الكتاب وليست حديثا.",
            text_en="This must not become a normal translation node.",
            record_id="thaqalayn:06840b21d9e61e1ab351aec4",
            source_record_id="provider-file:7|hadith:0",
            provenance_source="shia-hadith/v2_books",
            provider_file_id="7",
            provider_book_id="Kitab-al-Ghayba-Tusi",
            url="https://thaqalayn.net/hadith/1/0/1/0",
            translation_source="Thaqalayn API V2",
            translation_review_status="source_provided",
        ),
    ]
    with dataset.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=UNIFIED_COLUMNS, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    with rawis.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=RAWI_COLUMNS, lineterminator="\n"
        )
        writer.writeheader()
        first_profile = {
            column: f"raw {column} one" for column in RAWI_PROFILE_COLUMNS
        }
        first_profile.update(
            {
                "students_inds": "2, 2, 999",
                "teachers_inds": "1",
                "birth_date_place": "unsupported biography",
                "birth_place": "source-surface place",
            }
        )
        second_profile = {
            column: f"raw {column} two" for column in RAWI_PROFILE_COLUMNS
        }
        second_profile.update(
            {
                "students_inds": "NA",
                "teachers_inds": "1",
                "birth_date_place": "unsupported place",
            }
        )
        writer.writerow(
            {"scholar_indx": "1", "name": "زيد", **first_profile}
        )
        writer.writerow(
            {"scholar_indx": "2", "name": "عمرو", **second_profile}
        )
    return dataset, rawis, rows


def _read_dicts(path: Path):
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class Neo4jGraphBundleTests(unittest.TestCase):
    def test_deterministic_all_tradition_bundle_and_gates(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            dataset, rawis, input_rows = _write_fixture(root)
            first = root / "bundle-a"
            second = root / "bundle-b"
            first_manifest = export_bundle(
                dataset,
                rawis,
                first,
                "fixture_noncanonical",
                coverage_scope="fixture_partial",
            )
            second_manifest = export_bundle(
                dataset,
                rawis,
                second,
                "fixture_noncanonical",
                coverage_scope="fixture_partial",
            )

            self.assertEqual(
                first_manifest["content_sha256"],
                second_manifest["content_sha256"],
            )
            first_files = sorted(
                path.relative_to(first).as_posix()
                for path in first.rglob("*")
                if path.is_file()
            )
            second_files = sorted(
                path.relative_to(second).as_posix()
                for path in second.rglob("*")
                if path.is_file()
            )
            self.assertEqual(first_files, second_files)
            for relative_path in first_files:
                self.assertEqual(
                    (first / relative_path).read_bytes(),
                    (second / relative_path).read_bytes(),
                    relative_path,
                )

            report = validate_bundle(first, compare_bundle=second)
            self.assertTrue(report["import_ready"], report["errors"])
            self.assertFalse(report["publication_ready"])
            self.assertTrue(
                report["gates"]["narrator_profile_binding"]["available"]
            )
            self.assertTrue(
                report["gates"]["narrator_profile_binding"]["performed"]
            )
            self.assertTrue(
                report["gates"]["narrator_profile_binding"]["passed"]
            )
            self.assertFalse(
                report["gates"]["narrator_profile_binding"][
                    "passed_for_publication"
                ]
            )
            self.assertIn(
                "narrator profiles are not publication-reviewed: "
                f"{RAWI_PROFILE_REVIEW_STATE}",
                report["publication_blockers"],
            )
            self.assertTrue(
                report["gates"]["deterministic_compare"]["equal"]
            )
            self.assertEqual(
                first_manifest["counts"]["by_tradition"],
                {"Ibadi": 1, "Imami": 2, "Sunni": 1, "Zaydi": 1},
            )
            registry = json.loads(
                (first / "source_work_registry.json").read_text(encoding="utf-8")
            )
            self.assertEqual(len(registry["source_works"]), 34)
            for relative_path, spec in NODE_FILES.items():
                with (first / relative_path).open(
                    "r", encoding="utf-8", newline=""
                ) as handle:
                    header = next(csv.reader(handle))
                self.assertTrue(header[0].startswith("import_id:ID("))
                self.assertEqual(header[1], "id:string")
                self.assertEqual(header, spec["header"])

            hadiths = _read_dicts(first / "nodes" / "hadiths.csv")
            sunni = next(row for row in hadiths if row["record_id:string"] == "k6:test-1")
            self.assertEqual(sunni["text_ar:string"], input_rows[0]["text_ar"])
            self.assertEqual(
                sunni["arabic_sha256:string"],
                __import__("hashlib").sha256(
                    input_rows[0]["text_ar"].encode("utf-8")
                ).hexdigest(),
            )
            excluded = next(
                row
                for row in hadiths
                if row["record_id:string"]
                == "thaqalayn:06840b21d9e61e1ab351aec4"
            )
            self.assertEqual(excluded["quality_excluded:boolean"], "true")
            self.assertEqual(
                excluded["quality_exclusion_reason:string"],
                SOURCE_QUALITY_EXCLUSIONS[
                    "thaqalayn:06840b21d9e61e1ab351aec4"
                ],
            )

            translations = _read_dicts(first / "nodes" / "translations.csv")
            self.assertTrue(
                all(row["candidate_only:boolean"] == "false" for row in translations)
            )
            self.assertFalse(
                any(
                    row["import_id:ID(Translation-ID)"].startswith(
                        "translation:thaqalayn:06840b21d9e61e1ab351aec4:"
                    )
                    for row in translations
                )
            )
            self.assertFalse(
                any(
                    row["import_id:ID(Translation-ID)"].startswith(
                        ("translation:openiti:zaydi:", "translation:openiti:ibadi:")
                    )
                    for row in translations
                )
            )
            dispositions = {
                row["record_id:string"]: row["translation_disposition:string"]
                for row in hadiths
            }
            self.assertEqual(
                dispositions["openiti:zaydi:test-3"],
                "omitted_machine_candidate",
            )
            self.assertEqual(
                dispositions["openiti:ibadi:test-4"],
                "omitted_machine_candidate",
            )
            zaydi_chains = [
                row
                for row in _read_dicts(first / "nodes" / "chains.csv")
                if row["hadith_id:string"] == "hadith:openiti:zaydi:test-3"
            ]
            self.assertGreaterEqual(len(zaydi_chains), 2)
            self.assertTrue(
                all(row["resolved:boolean"] == "false" for row in zaydi_chains)
            )
            self.assertGreater(
                len(_read_dicts(first / "relationships" / "next_in_chain.csv")),
                0,
            )
            biographies = _read_dicts(first / "nodes" / "biographies.csv")
            self.assertEqual(len(biographies), 2)
            profile_one = next(
                row
                for row in biographies
                if row["scholar_indx:int"] == "1"
            )
            self.assertEqual(
                profile_one["import_id:ID(Biography-ID)"],
                "biography:narrator-lexicon:1",
            )
            self.assertEqual(
                profile_one["subject_id:string"], "narrator:rawi:1"
            )
            self.assertEqual(
                profile_one["review_state:string"],
                RAWI_PROFILE_REVIEW_STATE,
            )
            self.assertEqual(
                profile_one["provenance:string"],
                RAWI_PROFILE_PROVENANCE,
            )
            self.assertEqual(profile_one["citation_id:string"], "")
            self.assertEqual(
                profile_one["birth_place:string"], "source-surface place"
            )
            self.assertIn("Profile", profile_one[":LABEL"].split(";"))
            self.assertEqual(
                len(
                    _read_dicts(
                        first / "relationships" / "biography_of.csv"
                    )
                ),
                2,
            )
            self.assertEqual(
                len(
                    _read_dicts(
                        first
                        / "relationships"
                        / "biography_from_source.csv"
                    )
                ),
                2,
            )
            student_edges = _read_dicts(
                first / "relationships" / "student_of.csv"
            )
            self.assertEqual(len(student_edges), 1)
            self.assertEqual(
                student_edges[0][":START_ID(Narrator-ID)"],
                "narrator:rawi:2",
            )
            self.assertEqual(
                student_edges[0][":END_ID(Narrator-ID)"],
                "narrator:rawi:1",
            )
            self.assertEqual(
                student_edges[0]["evidence_fields:string"],
                "students_inds|teachers_inds",
            )
            self.assertEqual(student_edges[0]["evidence_count:int"], "2")
            self.assertEqual(student_edges[0]["reciprocal:boolean"], "true")
            self.assertEqual(
                first_manifest["narrator_profiles"],
                {
                    "profile_nodes": 2,
                    "raw_profile_fields": list(RAWI_PROFILE_COLUMNS),
                    "profile_review_state": RAWI_PROFILE_REVIEW_STATE,
                    "profile_provenance": RAWI_PROFILE_PROVENANCE,
                    "indexed_learning_assertion_tokens": 5,
                    "indexed_learning_duplicate_fields": 1,
                    "indexed_learning_duplicate_occurrences": 1,
                    "unique_indexed_pairs": 3,
                    "exported_student_of_pairs": 1,
                    "corroborated_pairs": 1,
                    "omitted_missing_endpoint_pairs": 1,
                    "omitted_self_pairs": 1,
                    "direction": "student_to_teacher",
                    "evidence_policy": (
                        "teachers_inds on the student row and students_inds "
                        "on the teacher row are aggregated without claiming "
                        "citation review"
                    ),
                },
            )
            self.assertEqual(
                len(_read_dicts(first / "nodes" / "citations.csv")), 0
            )
            self.assertEqual(len(_read_dicts(first / "nodes" / "places.csv")), 0)
            self.assertEqual(len(_read_dicts(first / "nodes" / "events.csv")), 0)

            k6_book_edges = [
                row
                for row in _read_dicts(
                    first / "relationships" / "hadith_in_book.csv"
                )
                if row[":START_ID(Hadith-ID)"] == "hadith:k6:test-1"
            ]
            k6_chapter_edges = [
                row
                for row in _read_dicts(
                    first / "relationships" / "hadith_in_chapter.csv"
                )
                if row[":START_ID(Hadith-ID)"] == "hadith:k6:test-1"
            ]
            self.assertEqual(len(k6_book_edges), 1)
            self.assertEqual(k6_chapter_edges, [])

            loader = (first / "neo4j-admin-import.ps1").read_text(encoding="utf-8")
            for flag in (
                "--id-type=string",
                "--input-encoding=UTF-8",
                "--bad-tolerance=0",
                "--skip-duplicate-nodes=false",
                "--skip-bad-relationships=false",
                "--overwrite-destination=false",
                "--multiline-fields-format=v2",
                "--dry-run=true",
                "Neo4j 2026.02 or newer is required",
            ):
                self.assertIn(flag, loader)

    def test_rawi_row_shape_and_unavailable_binding_are_explicit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            dataset, rawis, _ = _write_fixture(root)
            clean = root / "clean"
            export_bundle(
                dataset,
                rawis,
                clean,
                "fixture_noncanonical",
                coverage_scope="fixture_partial",
            )
            with rawis.open("r", encoding="utf-8", newline="") as handle:
                original_rows = list(csv.reader(handle))

            extra_rows = [list(row) for row in original_rows]
            extra_rows[1].append("unexpected-extra-column")
            with rawis.open("w", encoding="utf-8", newline="") as handle:
                csv.writer(handle, lineterminator="\n").writerows(extra_rows)
            shape_report = validate_bundle(clean)
            self.assertFalse(shape_report["import_ready"])
            self.assertTrue(
                any(
                    "bound rawi registry has a non-exact row shape"
                    in error
                    for error in shape_report["errors"]
                )
            )
            with self.assertRaisesRegex(ValueError, "non-exact row shape"):
                export_bundle(
                    dataset,
                    rawis,
                    root / "extra-shape-export",
                    "fixture_noncanonical",
                    coverage_scope="fixture_partial",
                )

            missing_rawis = root / "missing-shape-rawis.csv"
            missing_rows = [list(row) for row in original_rows]
            missing_rows[1].pop()
            with missing_rawis.open(
                "w", encoding="utf-8", newline=""
            ) as handle:
                csv.writer(handle, lineterminator="\n").writerows(
                    missing_rows
                )
            with self.assertRaisesRegex(ValueError, "non-exact row shape"):
                export_bundle(
                    dataset,
                    missing_rawis,
                    root / "missing-shape-export",
                    "fixture_noncanonical",
                    coverage_scope="fixture_partial",
                )

            rawis.unlink()
            unavailable_report = validate_bundle(clean)
            profile_gate = unavailable_report["gates"][
                "narrator_profile_binding"
            ]
            self.assertFalse(profile_gate["available"])
            self.assertFalse(profile_gate["performed"])
            self.assertFalse(profile_gate["passed"])

            complete_unavailable = root / "complete-unavailable"
            shutil.copytree(clean, complete_unavailable)
            manifest_path = complete_unavailable / "manifest.json"
            manifest = json.loads(
                manifest_path.read_text(encoding="utf-8")
            )
            manifest["coverage"]["scope"] = "complete"
            manifest_path.write_text(
                json.dumps(
                    manifest,
                    ensure_ascii=False,
                    sort_keys=True,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            complete_report = validate_bundle(complete_unavailable)
            self.assertFalse(complete_report["import_ready"])
            self.assertTrue(
                any(
                    "complete bundle validation requires the bound rawi "
                    "profile source to be available"
                    in error
                    for error in complete_report["errors"]
                )
            )

    def test_orphan_and_collision_tampering_fail_integrity(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            dataset, rawis, _ = _write_fixture(root)
            clean = root / "clean"
            export_bundle(
                dataset,
                rawis,
                clean,
                "fixture_noncanonical",
                coverage_scope="fixture_partial",
            )

            orphan = root / "orphan"
            shutil.copytree(clean, orphan)
            edge_path = orphan / "relationships" / "hadith_in_collection.csv"
            rows = _read_dicts(edge_path)
            rows[0][":END_ID(Collection-ID)"] = "collection:missing"
            with edge_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=list(rows[0]),
                    lineterminator="\n",
                )
                writer.writeheader()
                writer.writerows(rows)
            orphan_report = validate_bundle(orphan)
            self.assertFalse(orphan_report["import_ready"])
            self.assertTrue(
                any("orphan endpoint" in error for error in orphan_report["errors"])
            )
            compare_report = validate_bundle(clean, compare_bundle=orphan)
            self.assertFalse(compare_report["import_ready"])
            self.assertTrue(
                any(
                    "compare bundle failed independent integrity validation"
                    in error
                    for error in compare_report["errors"]
                )
            )

            collision = root / "collision"
            shutil.copytree(clean, collision)
            narrator_path = collision / "nodes" / "narrators.csv"
            narrator_rows = _read_dicts(narrator_path)
            duplicate = dict(narrator_rows[0])
            duplicate["scholar_indx:int"] = "999"
            with narrator_path.open("a", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=list(duplicate),
                    lineterminator="\n",
                )
                writer.writerow(duplicate)
            collision_report = validate_bundle(collision)
            self.assertFalse(collision_report["import_ready"])
            self.assertTrue(
                any(
                    "duplicate/colliding node ID" in error
                    for error in collision_report["errors"]
                )
            )

            profile_tamper = root / "profile-tamper"
            shutil.copytree(clean, profile_tamper)
            biography_path = profile_tamper / "nodes" / "biographies.csv"
            biography_rows = _read_dicts(biography_path)
            biography_rows[0]["birth_place:string"] = "invented normalization"
            with biography_path.open(
                "w", encoding="utf-8", newline=""
            ) as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=list(biography_rows[0]),
                    lineterminator="\n",
                )
                writer.writeheader()
                writer.writerows(biography_rows)
            profile_report = validate_bundle(profile_tamper)
            self.assertFalse(profile_report["import_ready"])
            self.assertTrue(
                any(
                    "raw profile SHA-256 mismatch" in error
                    for error in profile_report["errors"]
                )
            )

            direction_tamper = root / "direction-tamper"
            shutil.copytree(clean, direction_tamper)
            student_path = (
                direction_tamper / "relationships" / "student_of.csv"
            )
            student_rows = _read_dicts(student_path)
            start = student_rows[0][":START_ID(Narrator-ID)"]
            student_rows[0][":START_ID(Narrator-ID)"] = student_rows[0][
                ":END_ID(Narrator-ID)"
            ]
            student_rows[0][":END_ID(Narrator-ID)"] = start
            with student_path.open(
                "w", encoding="utf-8", newline=""
            ) as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=list(student_rows[0]),
                    lineterminator="\n",
                )
                writer.writeheader()
                writer.writerows(student_rows)
            direction_report = validate_bundle(direction_tamper)
            self.assertFalse(direction_report["import_ready"])
            self.assertTrue(
                any(
                    "STUDENT_OF source binding/direction failures" in error
                    for error in direction_report["errors"]
                )
            )

            unlisted = root / "unlisted"
            shutil.copytree(clean, unlisted)
            (unlisted / "machine_translation_candidates.csv").write_text(
                "candidate_only:boolean\ntrue\n", encoding="utf-8"
            )
            unlisted_report = validate_bundle(unlisted)
            self.assertFalse(unlisted_report["import_ready"])
            self.assertTrue(
                any(
                    "unlisted bundle files" in error
                    for error in unlisted_report["errors"]
                )
            )


if __name__ == "__main__":
    unittest.main()
