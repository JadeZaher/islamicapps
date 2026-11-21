import csv
import gzip
import hashlib
import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "regen_unified_csvs.py"
SPEC = importlib.util.spec_from_file_location("regen_unified_csvs_curation", MODULE_PATH)
regen = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(regen)

SHIA_BUILD_PATH = (
    Path(__file__).resolve().parents[1] / "shia-hadith" / "build_csv.py"
)
SHIA_BUILD_SPEC = importlib.util.spec_from_file_location(
    "shia_build_csv_curation", SHIA_BUILD_PATH
)
shia_build = importlib.util.module_from_spec(SHIA_BUILD_SPEC)
assert SHIA_BUILD_SPEC and SHIA_BUILD_SPEC.loader
SHIA_BUILD_SPEC.loader.exec_module(shia_build)


class TranslationGateTests(unittest.TestCase):
    def test_legitimate_refusal_word_is_not_a_model_refusal(self):
        text = "The buyer refused the offer and returned the property."
        self.assertEqual(regen.translation_issue(text), "")

    def test_model_refusal_is_release_blocking(self):
        self.assertEqual(
            regen.translation_issue("I cannot translate this passage."),
            "model_refusal_or_error",
        )

    def test_non_english_and_placeholders_are_release_blocking(self):
        self.assertEqual(regen.translation_issue("حدثنا زيد"), "arabic_leakage")
        self.assertEqual(regen.translation_issue("TBA"), "placeholder")

    def test_inline_placeholders_arabic_leakage_and_wrong_script_are_blocked(self):
        self.assertEqual(
            regen.translation_issue("Translation TODO: recover source text."),
            "placeholder",
        )
        self.assertEqual(
            regen.translation_issue("The transmitter said حدثنا زيد."),
            "arabic_leakage",
        )
        self.assertEqual(
            regen.translation_issue("Это перевод with two words."),
            "wrong_language",
        )

    def test_short_translation_is_context_sensitive(self):
        self.assertEqual(regen.translation_issue("Eat.", "كلوا"), "")
        self.assertEqual(
            regen.translation_issue("Nafi'", "حدثنا " * 20),
            "suspiciously_short",
        )

    def test_same_as_arabic_is_release_blocking(self):
        arabic = "قال رسول الله"
        self.assertEqual(regen.translation_issue(arabic, arabic), "same_as_arabic")
        self.assertEqual(
            regen.translation_issue("قال، رسول الله!", "قال رسول الله"),
            "same_as_arabic",
        )


class MetadataParityTests(unittest.TestCase):
    def test_current_source_and_provenance_identifiers_are_meaningful(self):
        for value in ("1", "pc_7", "url-path:/hadith/1/2/3/4"):
            with self.subTest(source_record_id=value):
                self.assertTrue(regen.is_meaningful_source_record_id(value))
        for value in (
            "all_hadiths_clean.csv.gz:k6_snapshot",
            "shia-hadith/v2_books",
            "legacy_k6_source_export",
        ):
            with self.subTest(provenance=value):
                self.assertTrue(regen.is_meaningful_provenance_locator(value))

    def test_placeholder_metadata_tokens_are_rejected(self):
        for value in ("", " <missing> ", "N/A", "unknown", "t b d", "?"):
            with self.subTest(value=value):
                self.assertFalse(regen.is_meaningful_source_record_id(value))
                self.assertFalse(regen.is_meaningful_provenance_locator(value))

    def test_model_identifiers_match_loader_specificity_contract(self):
        for value in ("google/gemma-4-e4b", "manual:claude-opus-4.7"):
            with self.subTest(valid=value):
                self.assertTrue(
                    regen.is_specific_translation_model_identifier(value)
                )
        for value in (
            "gemma-4-e4b", "model", "ai/model", "vendor/x", "default/model",
            "unknown",
        ):
            with self.subTest(invalid=value):
                self.assertFalse(
                    regen.is_specific_translation_model_identifier(value)
                )
        self.assertTrue(
            regen.translation_model_required("classical translation pipeline", "source_verified")
        )


class ClassicalTranslationIndexTests(unittest.TestCase):
    def test_prefers_enhanced_text_and_keys_by_source_record_id(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "translations.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=("id", "text_ar", "text_en", "text_en_enhanced"),
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "id": "pc_7",
                        "text_ar": "نص",
                        "text_en": "First pass translation",
                        "text_en_enhanced": "Reviewed translation",
                    }
                )
            missing_jsonl = Path(directory) / "missing.jsonl"
            with (
                mock.patch.object(regen, "CLASSICAL_TRANSLATIONS_CSV", str(path)),
                mock.patch.object(
                    regen, "CLASSICAL_TRANSLATIONS_CLEAN_JSONL", str(missing_jsonl)
                ),
            ):
                index = regen.load_classical_translation_index()
            self.assertEqual(index["pc_7"]["text_en"], "Reviewed translation")

    def test_clean_jsonl_fills_only_missing_enhanced_translation(self):
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "translations.csv"
            with csv_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=("id", "text_ar", "text_en", "text_en_enhanced",
                                "source_canonical"),
                )
                writer.writeheader()
                writer.writerow(
                    {"id": "pc_27", "text_ar": "نص", "text_en": "",
                     "text_en_enhanced": "", "source_canonical": "Musnad Ahmad"}
                )
            jsonl_path = Path(directory) / "clean.jsonl"
            jsonl_path.write_text(
                json.dumps(
                    {"id": "pc_27", "text_ar": "نص",
                     "source_canonical": "Musnad Ahmad",
                     "text_en": "Recovered translation"},
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            with (
                mock.patch.object(regen, "CLASSICAL_TRANSLATIONS_CSV", str(csv_path)),
                mock.patch.object(
                    regen, "CLASSICAL_TRANSLATIONS_CLEAN_JSONL", str(jsonl_path)
                ),
            ):
                index = regen.load_classical_translation_index()
            self.assertEqual(index["pc_27"]["text_en"], "Recovered translation")
            self.assertIn("classical_translations_clean.jsonl", index["pc_27"]["translation_source"])

    def test_clean_jsonl_can_supply_unique_identity_absent_from_enhanced(self):
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "translations.csv"
            csv_path.write_text(
                "id,text_ar,text_en,text_en_enhanced,source_canonical\n",
                encoding="utf-8",
            )
            jsonl_path = Path(directory) / "clean.jsonl"
            jsonl_path.write_text(
                json.dumps({
                    "id": "pc_missing",
                    "text_ar": "نص فريد",
                    "source_canonical": "Musnad Ahmad",
                    "text_en": "A uniquely identified recovered translation.",
                }, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            with (
                mock.patch.object(regen, "CLASSICAL_TRANSLATIONS_CSV", str(csv_path)),
                mock.patch.object(
                    regen, "CLASSICAL_TRANSLATIONS_CLEAN_JSONL", str(jsonl_path)
                ),
            ):
                index = regen.load_classical_translation_index()

        self.assertEqual(index["pc_missing"]["source_canonical"], "Musnad Ahmad")
        self.assertEqual(index["pc_missing"]["text_ar"], "نص فريد")

    def test_clean_jsonl_translation_without_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "translations.csv"
            csv_path.write_text(
                "id,text_ar,text_en,text_en_enhanced,source_canonical\n",
                encoding="utf-8",
            )
            jsonl_path = Path(directory) / "clean.jsonl"
            jsonl_path.write_text(
                json.dumps({
                    "text_ar": "نص",
                    "source_canonical": "Musnad Ahmad",
                    "text_en": "Translation without identity.",
                }, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            with (
                mock.patch.object(regen, "CLASSICAL_TRANSLATIONS_CSV", str(csv_path)),
                mock.patch.object(
                    regen, "CLASSICAL_TRANSLATIONS_CLEAN_JSONL", str(jsonl_path)
                ),
            ):
                with self.assertRaisesRegex(ValueError, "missing ID"):
                    regen.load_classical_translation_index()

    def test_clean_jsonl_conflicting_identity_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "translations.csv"
            csv_path.write_text(
                "id,text_ar,text_en,text_en_enhanced,source_canonical\n"
                "pc_1,النص الأول,,,Musnad Ahmad\n",
                encoding="utf-8",
            )
            jsonl_path = Path(directory) / "clean.jsonl"
            jsonl_path.write_text(
                json.dumps({
                    "id": "pc_1",
                    "text_ar": "النص الثاني",
                    "source_canonical": "Musnad Ahmad",
                    "text_en": "A translation attached to conflicting Arabic.",
                }, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            with (
                mock.patch.object(regen, "CLASSICAL_TRANSLATIONS_CSV", str(csv_path)),
                mock.patch.object(
                    regen, "CLASSICAL_TRANSLATIONS_CLEAN_JSONL", str(jsonl_path)
                ),
            ):
                with self.assertRaisesRegex(ValueError, "Conflicting"):
                    regen.load_classical_translation_index()


class TranslationOverrideTests(unittest.TestCase):
    def test_override_requires_exact_arabic_hash(self):
        arabic = "قال رسول الله"
        record = {"record_id": "k6:1", "text_ar": arabic, "text_en": ""}
        override = {
            "k6:1": {
                "record_id": "k6:1",
                "arabic_sha256": hashlib.sha256(arabic.encode("utf-8")).hexdigest(),
                "text_en": "The Messenger of Allah said this.",
                "translation_source": "https://example.test/source",
                "translation_review_status": "source_verified",
            }
        }
        self.assertEqual(regen.apply_translation_overrides([record], override), 1)
        self.assertEqual(record["translation_status"], "complete")

    def test_stale_override_is_rejected(self):
        record = {"record_id": "k6:1", "text_ar": "نص", "text_en": ""}
        override = {
            "k6:1": {
                "record_id": "k6:1",
                "arabic_sha256": "0" * 64,
                "text_en": "A valid-looking English translation.",
                "translation_source": "source",
                "translation_review_status": "reviewed",
            }
        }
        with self.assertRaisesRegex(ValueError, "Arabic hash mismatch"):
            regen.apply_translation_overrides([record], override)


class SourceIdentityCollisionTests(unittest.TestCase):
    def test_reused_translation_on_different_arabic_is_blocked(self):
        shared = {
            "source": "Musnad al-Rabi ibn Habib",
            "hadith_id": "rabi_0387",
            "hadith_no": "387",
            "text_en": "One reused English translation.",
        }
        rows = [
            {**shared, "record_id": "one", "text_ar": "النص الأول"},
            {**shared, "record_id": "two", "text_ar": "النص الثاني"},
        ]
        self.assertEqual(regen.source_translation_collision_ids(rows), {"one", "two"})


class NarratorResolverConservatismTests(unittest.TestCase):
    def test_unicode_format_and_presentation_forms_are_lookup_equivalent(self):
        exact = {regen.narrator_normalize("أبو عوانة"): "7"}
        self.assertEqual(
            regen.resolve_narrator("ﺃﺑﻮ\u200f عوانة", exact, {}), "7"
        )

    def test_shared_prefix_without_full_name_agreement_is_not_resolved(self):
        blocked = {"محمد": [("21", "محمد بن عبد الله")]}
        self.assertIsNone(
            regen.resolve_narrator("محمد بن أحمد", {}, blocked)
        )

    def test_containment_match_remains_a_non_resolving_candidate(self):
        surface = "أبو عوانة اليشكري وضاح"
        normalized_names = (
            regen.narrator_normalize("أبو عوانة"),
            regen.narrator_normalize("أبو عوانة اليشكري"),
        )
        blocked = {
            regen.narrator_normalize(surface)[:4]: [
                ("7", normalized_names[0]),
                ("7", normalized_names[1]),
            ]
        }
        self.assertIsNone(regen.resolve_narrator(surface, {}, blocked))
        self.assertEqual(
            {
                candidate["scholar_indx"]
                for candidate in regen.narrator_resolution_candidates(
                    surface, blocked
                )
            },
            {"7"},
        )

    def test_unique_kunya_segment_is_not_added_to_exact_index(self):
        with tempfile.TemporaryDirectory() as directory:
            rawis = Path(directory) / "all_rawis.csv"
            with rawis.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=("scholar_indx", "name"))
                writer.writeheader()
                writer.writerow({
                    "scholar_indx": "7",
                    "name": "Abu Awana ( أبو عوانة اليشكري وضاح بن خالد )",
                })
            exact, candidates = regen.build_narrator_index(str(rawis))

        short_kunya = regen.narrator_normalize("أبو عوانة")
        self.assertNotIn(short_kunya, exact)
        self.assertEqual(
            regen.resolve_narrator("أبو عوانة", exact, candidates), None
        )
        self.assertTrue(
            regen.narrator_resolution_candidates("أبو عوانة", candidates)
        )


class NarratorSpellingFoldTests(unittest.TestCase):
    """Adopted tiered lookup: tier 0 unchanged, tier 1 spelling folds, tier 2 guarded kunya fold."""

    REGISTRY = (
        ("1", "'Abdullah bin Suraqa ( عبد الله بن سراقة ( رضي الله عنه"),   # unclosed paren keeps the formula
        ("2", "Prophet Muhammad ( محمد صلى الله عليه وسلم ( رضي الله عنه"),   # bare name only after strip
        ("3", "Abu Salamah bin Abdur Rahman ( أبو سلمة بن عبد الرحمن )"),
        ("4", "Abu Salmah ( أبو سلمة )"),
        ("5", "Ubayy bin Kab ( أبي بن كعب )"),
        ("6", "Tabi bin Amir ( تبيع بن عامر )"),
        ("7", "Tby ibn Amir ( تبيع ابن عامر )"),
        ("8", "Aisha bint Qudama ( عائشة بنت قدامة )"),
        ("9", "Abd Allah bin Abbas ( عبد الله بن عباس )"),
        ("10", "Ibn Abi Layla ( ابن ابي ليلى )"),
        ("11", "Abu al-Qasim ( أبو القاسم )"),
    )

    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as directory:
            rawis = Path(directory) / "all_rawis.csv"
            with rawis.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=("scholar_indx", "name"))
                writer.writeheader()
                for indx, name in cls.REGISTRY:
                    writer.writerow({"scholar_indx": indx, "name": name})
            cls.exact, cls.blocked = regen.build_narrator_index(str(rawis))

    def resolve(self, surface):
        return regen.resolve_narrator(surface, self.exact, self.blocked)

    def test_spelling_variants_resolve_to_the_same_identity(self):
        table = [
            ("عبد الله بن سراقة", "1"),            # blessing formula removed at the registry source
            ("عبدالله بن عباس", "9"),              # theophoric spacing
            ("ابو القاسم", "11"),
            ("ابوالقاسم", "11"),                   # joined kunya compound
            ("عائشة ابنة قدامة", "8"),             # ابنة to بنت
            ("عبد الله ابن عباس", "9"),            # ابن to بن
            ("( عبد الله بن عباس ،", "9"),                   # punctuation
            ("ابي سلمة بن عبد الرحمن", "3"),       # guarded kunya case fold: has a nasab
        ]
        for surface, expected in table:
            with self.subTest(surface=surface):
                self.assertEqual(self.resolve(surface), expected)

    def test_different_names_and_underspecified_surfaces_stay_unresolved(self):
        table = [
            "محمد",                 # bare name that is unique only after formula strip is withheld
            "ابي سلمة",             # kunya-only: the case fold never completes it (registry spells it ابو)
            "ابو كعب",              # Ubayy is an ism, not a kunya
            "عائشة ابنه قدامة",     # 'his son' is not a nasab connector
            "عبيد الله بن عباس",
            "ابو حسن",
        ]
        for surface in table:
            with self.subTest(surface=surface):
                self.assertIsNone(self.resolve(surface))

    def test_exact_match_wins_and_ambiguous_folds_never_resolve(self):
        self.assertEqual(self.resolve("ابي بن كعب"), "5")
        self.assertEqual(self.resolve("تبيع بن عامر"), "6")      # tier-0 exact, kept although the folds collide
        self.assertEqual(self.resolve("تبيع ابن عامر"), "7")
        self.assertIsNone(self.resolve("تبيع  بن   عامر"))        # only tier 1 sees it: two identities, ambiguous

    def test_tier_zero_entries_are_unchanged_and_formula_keys_are_gone_from_tier_one(self):
        self.assertIn(regen.narrator_normalize("أبو سلمة"), self.exact)
        self.assertTrue(all(not regen._BLESSING_FORMULA.search(key) for key in self.exact.folded))
        self.assertEqual(self.exact.withheld_bare_names, ["2"])


class ThaqalaynResolverContractTests(unittest.TestCase):
    @staticmethod
    def chain_stats():
        return {
            "rows_with_arabic_text": 0,
            "rows_empty_arabic_text": 0,
            "rows_with_thaqalayn_sanad": 0,
            "rows_resolution_failed": 0,
            "rows_extraction_failed": 0,
            "extractor_failures_ignored": 0,
        }

    def test_missing_optional_extractor_telemetry_does_not_disable_resolver(self):
        fake_isnad = types.ModuleType("extract_isnad_unified")
        fake_isnad._compute_chain_indx = lambda **kwargs: "1"
        fake_regen = types.ModuleType("regen_unified_csvs")
        fake_regen.build_narrator_index = lambda path: ({"name": "1"}, {"name": []})
        fake_regen.resolve_narrator = lambda name, exact, blocked: "1"
        spec = importlib.util.spec_from_file_location(
            "shia_build_without_optional_telemetry", SHIA_BUILD_PATH
        )
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader

        with mock.patch.dict(
            sys.modules,
            {
                "extract_isnad_unified": fake_isnad,
                "regen_unified_csvs": fake_regen,
            },
        ):
            spec.loader.exec_module(module)

        self.assertTrue(module._RESOLVER_AVAILABLE)
        self.assertEqual(module._UNIFIED_CHAIN_STATS, {})

    def test_signature_mismatch_aborts_instead_of_emitting_empty_chain(self):
        hadith = {"id": 1, "arabicText": "حدثنا زيد"}
        incompatible = lambda text_ar, fallback: ""
        with mock.patch.object(shia_build, "_compute_chain_indx", incompatible):
            with self.assertRaisesRegex(RuntimeError, "contract failed"):
                shia_build.transform_hadith(
                    hadith,
                    1,
                    "1",
                    {},
                    {},
                    self.chain_stats(),
                    lambda name: None,
                )

    def test_none_chain_output_aborts_instead_of_becoming_blank(self):
        hadith = {"id": 1, "arabicText": "حدثنا زيد"}
        with mock.patch.object(
            shia_build, "_compute_chain_indx", return_value=None
        ):
            with self.assertRaisesRegex(RuntimeError, "non-string"):
                shia_build.transform_hadith(
                    hadith,
                    1,
                    "1",
                    {},
                    {},
                    self.chain_stats(),
                    lambda name: None,
                )

    def test_extraction_limit_empties_staged_thaqalayn_row(self):
        hadith = {"id": 1, "arabicText": "حدثنا زيد"}
        limited = regen.IsnadExtractionLimitError(
            "segment_co_transmitters", 65
        )
        stats = self.chain_stats()
        with mock.patch.object(
            shia_build, "_compute_chain_indx", side_effect=limited
        ):
            row = shia_build.transform_hadith(
                hadith, 1, "1", {}, {}, stats, lambda name: 1,
            )
        self.assertEqual(row["chain_indx"], "")
        self.assertEqual(stats["rows_extraction_failed"], 1)

    def test_unresolved_narrator_empties_staged_thaqalayn_row(self):
        hadith = {"id": 1, "arabicText": "حدثنا مجهول"}
        unresolved = regen.UnresolvedNarratorError(
            "مجهول", branch_index=0, narrator_index=0,
            reason="not found or ambiguous",
        )
        stats = self.chain_stats()
        with mock.patch.object(
            shia_build, "_compute_chain_indx", side_effect=unresolved
        ):
            row = shia_build.transform_hadith(
                hadith, 1, "1", {}, {}, stats, lambda name: None,
            )
        self.assertEqual(row["chain_indx"], "")
        self.assertEqual(stats["rows_resolution_failed"], 1)

    def test_missing_indices_abort_before_source_rows_are_opened(self):
        with (
            mock.patch.object(shia_build, "_RESOLVER_AVAILABLE", True),
            mock.patch.object(
                shia_build, "_load_resolver_indices", return_value=({}, {})
            ),
            mock.patch.object(shia_build.glob, "glob", return_value=["1.json"]),
        ):
            with self.assertRaisesRegex(RuntimeError, "non-empty narrator"):
                shia_build.main()

    def test_dependency_failure_reports_original_import_error(self):
        missing = ImportError("extractor sentinel missing")
        with (
            mock.patch.object(shia_build, "_RESOLVER_AVAILABLE", False),
            mock.patch.object(shia_build, "_RESOLVER_IMPORT_ERROR", missing),
            mock.patch.object(shia_build.glob, "glob", return_value=["1.json"]),
        ):
            with self.assertRaisesRegex(RuntimeError, "extractor sentinel missing"):
                shia_build.main()

    def test_zero_resolver_attempts_abort_and_preserve_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_dir = root / "v2_books"
            input_dir.mkdir()
            (input_dir / "1.json").write_text(
                json.dumps([{
                    "id": 1,
                    "bookId": "Al-Kafi-Volume-1-Kulayni",
                    "book": "Al-Kāfi",
                    "volume": 1,
                    "arabicText": "حدثنا زيد",
                }], ensure_ascii=False),
                encoding="utf-8",
            )
            output = root / "existing.csv"
            output.write_text("published\n", encoding="utf-8")

            with (
                mock.patch.object(shia_build, "INPUT_DIR", str(input_dir)),
                mock.patch.object(shia_build, "OUTPUT_PATH", str(output)),
                mock.patch.object(shia_build, "_RESOLVER_AVAILABLE", True),
                mock.patch.object(
                    shia_build,
                    "_load_resolver_indices",
                    return_value=({"name": "1"}, {"name": [("1", "name")]}),
                ),
                mock.patch.object(
                    shia_build, "_compute_chain_indx", return_value=""
                ),
            ):
                with self.assertRaisesRegex(RuntimeError, "never invoked"):
                    shia_build.main()

            self.assertEqual(output.read_text(encoding="utf-8"), "published\n")


class StableIdentityTests(unittest.TestCase):
    def test_thaqalayn_identity_ignores_mutable_display_label(self):
        base = {
            "source": "Al-Kāfi",
            "provider_file_id": "1",
            "provider_book_id": "Al-Kafi-Volume-1-Kulayni",
            "url": "https://thaqalayn.net/hadith/1/2/3/4",
            "volume": "2",
            "chapter_no": "3",
            "hadith_no": "4",
            "hadith_id": "99",
        }
        first = regen.apply_thaqalayn_identity(dict(base))
        second = regen.apply_thaqalayn_identity(
            {**base, "source": "Al-Kafi (normalized display)"}
        )

        self.assertEqual(
            first["source_record_id"], "provider-file:1|hadith:99"
        )
        self.assertEqual(first["record_id"], second["record_id"])

    def test_legacy_identity_uses_url_volume_and_hadith_tuple(self):
        first = regen.apply_thaqalayn_identity({
            "url": "https://thaqalayn.net/hadith/1/0/1/1",
            "volume": "1",
            "hadith_id": "7",
        })
        second = regen.apply_thaqalayn_identity({
            "url": "https://thaqalayn.net/hadith/1/0/1/1",
            "volume": "2",
            "hadith_id": "7",
        })

        self.assertEqual(
            first["source_record_id"],
            "url-path:/hadith/1/0/1/1|volume:1|hadith:7",
        )
        self.assertNotEqual(first["record_id"], second["record_id"])

    def test_thaqalayn_identity_survives_shia_projection_and_rebuild(self):
        first = regen.apply_thaqalayn_identity({
            "hadith_id": "7",
            "provider_file_id": "1",
            "provider_book_id": "Al-Kafi-Volume-1-Kulayni",
            "source": "Al-Kāfi",
            "volume": "1",
            "url": "https://thaqalayn.net/hadith/1/0/1/7",
        })
        projected = regen._project([first], regen.SHIA_COLS)[0]
        rebuilt = regen.apply_thaqalayn_identity(projected)

        self.assertEqual(rebuilt["source_record_id"], first["source_record_id"])
        self.assertEqual(rebuilt["record_id"], first["record_id"])
        self.assertEqual(rebuilt["provider_file_id"], "1")
        self.assertEqual(
            rebuilt["provider_book_id"], "Al-Kafi-Volume-1-Kulayni"
        )

    def test_full_thaqalayn_asset_has_globally_unique_provider_identities(self):
        books_dir = SHIA_BUILD_PATH.parent / "v2_books"
        rows = []
        for path in sorted(
            books_dir.glob("[0-9]*.json"), key=lambda item: int(item.stem)
        ):
            for hadith in json.loads(path.read_text(encoding="utf-8")):
                rows.append({
                    "provider_file_id": path.stem,
                    "provider_book_id": hadith.get("bookId", ""),
                    "hadith_id": hadith.get("id", ""),
                    "volume": hadith.get("volume", ""),
                    "url": hadith.get("URL", ""),
                })

        identified = regen.apply_thaqalayn_identities(rows)
        self.assertGreater(len(identified), 30_000)
        self.assertEqual(
            len({row["source_record_id"] for row in identified}),
            len(identified),
        )

    def test_thaqalayn_preflight_rejects_duplicate_provider_coordinates(self):
        duplicate = {
            "provider_file_id": "1",
            "provider_book_id": "Al-Kafi-Volume-1-Kulayni",
            "hadith_id": "7",
        }
        with self.assertRaisesRegex(ValueError, "Duplicate Thaqalayn"):
            regen.apply_thaqalayn_identities([duplicate, dict(duplicate)])


class ImamiSourceWorkRegistryTests(unittest.TestCase):
    def test_registry_covers_each_local_thaqalayn_provider_book_once(self):
        registry = regen.load_imami_source_work_registry()
        book_names_path = (
            SHIA_BUILD_PATH.parent / "v2_books" / "BookNames.json"
        )
        provider_book_ids = {
            book["bookId"]
            for book in json.loads(book_names_path.read_text(encoding="utf-8"))
        }

        self.assertEqual(
            set(registry["by_provider_book_id"]), provider_book_ids
        )
        self.assertEqual(len(registry["by_source_work_id"]), 22)

    def test_shared_display_labels_resolve_by_provider_book_id(self):
        registry = regen.load_imami_source_work_registry()
        mufid = regen.reconcile_imami_source_work({
            "source": "Al-Amālī",
            "provider_book_id": "Al-Amali-Mufid",
        }, registry)
        saduq = regen.reconcile_imami_source_work({
            "source": "Al-Amālī",
            "provider_book_id": "Al-Amali-Saduq",
        }, registry)
        tusi = regen.reconcile_imami_source_work({
            "source": "Kitāb al-Ghayba",
            "provider_book_id": "Kitab-al-Ghayba-Tusi",
        }, registry)
        numani = regen.reconcile_imami_source_work({
            "source": "Kitāb al-Ghayba",
            "provider_book_id": "Kitab-al-Ghayba-Numani",
        }, registry)

        self.assertEqual(mufid["source"], "Al-Amali (Mufid)")
        self.assertEqual(saduq["source"], "Al-Amali (Saduq)")
        self.assertNotEqual(mufid["source_work_id"], saduq["source_work_id"])
        self.assertEqual(tusi["source"], "Kitab al-Ghayba (Tusi)")
        self.assertEqual(numani["source"], "Kitab al-Ghayba (Nu'mani)")
        self.assertNotEqual(tusi["source_work_id"], numani["source_work_id"])

    def test_legacy_display_only_imami_rows_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "provider_book_id"):
            regen.reconcile_imami_source_work({"source": "Al-Amālī"})

    def test_openiti_identity_includes_hadith_number(self):
        base = {
            "id": "duplicate_source_id",
            "source": "Example",
            "tradition": "Ibadi",
            "text_ar": "نص",
            "text_en": "An English translation",
        }
        stats = regen.new_canonical_chain_stats()
        first = regen.openiti_to_shia_row(
            {**base, "hadith_no": 1}, 1, lambda _: 1, stats
        )
        second = regen.openiti_to_shia_row(
            {**base, "hadith_no": 2}, 2, lambda _: 1, stats
        )
        self.assertNotEqual(first["record_id"], second["record_id"])

    def test_openiti_provenance_uses_asset_directory_not_tradition_name(self):
        with tempfile.TemporaryDirectory() as directory:
            collection = Path(directory) / "rida-hadith"
            collection.mkdir()
            (collection / "parsed_hadiths.json").write_text(
                json.dumps({
                    "hadiths": [{
                        "id": "rida_1",
                        "hadith_no": 1,
                        "source": "Sahifat al-Imam Ali al-Rida",
                        "tradition": "Imami",
                        "text_ar": "نص",
                        "text_en": "An English translation.",
                    }],
                }, ensure_ascii=False),
                encoding="utf-8",
            )
            loaded = regen.load_openiti_hadiths(str(collection))[0]
            row = regen.openiti_to_shia_row(
                loaded, 1, lambda _: 1, regen.new_canonical_chain_stats()
            )

        self.assertEqual(row["provenance_source"], "rida-hadith/parsed_hadiths.json")
        self.assertEqual(row["translation_source"], "rida-hadith/parsed_hadiths.json")


class CanonicalIsnadIntegrationTests(unittest.TestCase):
    def test_arabic_chain_overwrites_legacy_k6_chain(self):
        row = {"text_ar": "حدثنا زيد عن عمرو", "chain_indx": "999"}
        stats = regen.new_canonical_chain_stats()
        regen.apply_canonical_chain(
            row,
            lambda surface: {"زيد": 10, "عمرو": 20}.get(surface),
            stats,
        )
        self.assertEqual(row["chain_indx"], "10,20")
        self.assertEqual(stats["rows_resolved"], 1)

    def test_unresolved_surface_empties_whole_row(self):
        stats = regen.new_canonical_chain_stats()
        cell = regen.canonical_chain_indx(
            "حدثنا زيد عن مجهول",
            lambda surface: 10 if surface == "زيد" else None,
            stats,
        )
        self.assertEqual(cell, "")
        self.assertEqual(stats["rows_resolution_failed"], 1)

    def test_extraction_limit_empties_whole_row_with_telemetry(self):
        stats = regen.new_canonical_chain_stats()
        limited = regen.IsnadExtractionLimitError(
            "tahweel_stitching", 65
        )
        with mock.patch.object(
            regen, "_compute_chain_indx", side_effect=limited
        ):
            cell = regen.canonical_chain_indx(
                "حدثنا زيد", lambda _: 1, stats
            )
        self.assertEqual(cell, "")
        self.assertEqual(stats["rows_extraction_failed"], 1)
        self.assertEqual(stats["rows_resolution_failed"], 0)

    def test_classical_preflight_limit_empties_row_without_aborting_load(self):
        source = next(
            key for key, value in regen.CLASSICAL_SOURCE_MAP.items()
            if value == "Musnad Ahmad"
        )
        record = {
            "id": "pc_limit",
            "source": source,
            "hadith_no": 1,
            "text_ar": "حدثنا زيد",
            "chain": "حدثنا زيد",
        }
        canonical_stats = regen.new_canonical_chain_stats()
        limited = regen.IsnadExtractionLimitError(
            "segment_co_transmitters", 65
        )
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "pure_canon.jsonl"
            source_path.write_text(
                json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            with mock.patch.object(
                regen, "extract_isnad_branches", side_effect=limited
            ):
                rows, _, stats = regen.load_classical_sunni_rows(
                    str(source_path), {}, {}, {}, canonical_stats
                )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["chain_indx"], "")
        self.assertEqual(rows[0]["sanad"], "")
        self.assertEqual(stats["isnad_attempted"], 1)
        self.assertEqual(stats["isnad_extracted"], 0)
        self.assertEqual(canonical_stats["rows_attempted"], 1)
        self.assertEqual(canonical_stats["rows_extraction_failed"], 1)

    def test_both_openiti_projections_use_canonical_arabic_chain(self):
        hadith = {
            "id": "rabi_1",
            "hadith_no": 1,
            "page_ref": "V01P001",
            "source": "Example",
            "tradition": "Ibadi",
            "text_ar": "حدثنا زيد عن عمرو",
            "text_en": "English",
        }
        resolver = lambda surface: {"زيد": 10, "عمرو": 20}.get(surface)
        clean = regen.openiti_to_clean_row(
            hadith, 1, resolver, regen.new_canonical_chain_stats()
        )
        shia = regen.openiti_to_shia_row(
            hadith, 1, resolver, regen.new_canonical_chain_stats()
        )
        self.assertEqual(clean["chain_indx"], "10,20")
        self.assertEqual(shia["chain_indx"], "10,20")


class EvidenceCurationGateTests(unittest.TestCase):
    @staticmethod
    def valid_bundle():
        citation_id = "citation:edition-one-page-one"
        return {
            "schema_version": 1,
            "citations": [{
                "citation_id": citation_id,
                "work_id": "work:example",
                "edition_id": "edition:example-one",
                "locator": "vol. 1, p. 1",
                "review_status": "source_verified",
            }],
            "biographical_assertions": [{
                "assertion_id": "assertion:person-one-death",
                "person_id": "person:one",
                "predicate": "death",
                "calendar": "AH",
                "year_min": 100,
                "year_max": 100,
                "precision": "year",
                "uncertainty": "none",
                "citation_id": citation_id,
                "review_status": "human_verified",
            }],
            "source_author_assertions": [{
                "assertion_id": "assertion:work-one-compiler",
                "source_work_id": "work:example",
                "author_person_id": "person:one",
                "role": "compiler",
                "citation_id": citation_id,
                "review_status": "source_verified",
            }],
            "historical_event_assertions": [{
                "assertion_id": "assertion:event-one-date",
                "subject_id": "event:one",
                "subject_type": "historical_event",
                "calendar": "AH",
                "precision": "unknown",
                "uncertainty": "unknown",
                "citation_id": citation_id,
                "review_status": "human_verified",
            }],
            "epoch_assertions": [{
                "assertion_id": "assertion:epoch-one-date",
                "subject_id": "epoch:one",
                "subject_type": "epoch",
                "calendar": "AH",
                "year_min": 1,
                "year_max": 100,
                "precision": "range",
                "uncertainty": "approximate",
                "citation_id": citation_id,
                "review_status": "source_verified",
            }],
        }

    @staticmethod
    def manifest_for(bundle, ready=True, uncited=0, unreviewed=0):
        keys = (
            "citations", "biographical_assertions", "source_author_assertions",
            "historical_event_assertions", "epoch_assertions",
        )
        return {
            "schema_version": 1,
            "ready_for_graph_publication": ready,
            "counts": {
                **{key: len(bundle[key]) for key in keys},
                "uncited_claims": uncited,
                "unreviewed_claims": unreviewed,
            },
        }

    def write_assets(self, root, bundle, manifest):
        schema = root / "evidence_curation.schema.json"
        schema.write_text(
            Path(regen.EVIDENCE_CURATION_SCHEMA_JSON).read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        bundle_path = root / "evidence_curation.json"
        bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
        manifest_path = root / "evidence_curation_manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        return manifest_path, bundle_path, schema

    def test_real_schema_valid_reviewed_claim_bundle_passes(self):
        bundle = self.valid_bundle()
        with tempfile.TemporaryDirectory() as directory:
            paths = self.write_assets(
                Path(directory), bundle, self.manifest_for(bundle)
            )
            gate = regen.evidence_curation_gate(*(str(path) for path in paths))

        self.assertTrue(gate["passed"])
        self.assertEqual(gate["actual_counts"]["citations"], 1)

    def test_ready_summary_and_fabricated_counts_cannot_pass_empty_bundle(self):
        bundle = {
            "schema_version": 1,
            "citations": [],
            "biographical_assertions": [],
            "source_author_assertions": [],
            "historical_event_assertions": [],
            "epoch_assertions": [],
        }
        manifest = self.manifest_for(bundle)
        for key in (
            "citations", "biographical_assertions", "source_author_assertions",
            "historical_event_assertions", "epoch_assertions",
        ):
            manifest["counts"][key] = 1
        with tempfile.TemporaryDirectory() as directory:
            paths = self.write_assets(Path(directory), bundle, manifest)
            gate = regen.evidence_curation_gate(*(str(path) for path in paths))

        self.assertFalse(gate["passed"])
        self.assertEqual(gate["counts"]["manifest_count_mismatches"], 5)
        self.assertEqual(gate["counts"]["missing_citations"], 1)

    def test_duplicate_ids_broken_references_and_unreviewed_claims_block(self):
        bundle = self.valid_bundle()
        bundle["citations"].append(dict(bundle["citations"][0]))
        bundle["biographical_assertions"][0]["citation_id"] = "citation:missing"
        bundle["epoch_assertions"][0]["review_status"] = "machine_unreviewed"
        manifest = self.manifest_for(bundle, uncited=1, unreviewed=1)
        with tempfile.TemporaryDirectory() as directory:
            paths = self.write_assets(Path(directory), bundle, manifest)
            gate = regen.evidence_curation_gate(*(str(path) for path in paths))

        self.assertFalse(gate["passed"])
        self.assertEqual(gate["counts"]["duplicate_citation_ids"], 1)
        self.assertEqual(gate["counts"]["broken_citation_references"], 1)
        self.assertEqual(gate["counts"]["unreviewed_claims"], 1)
        self.assertGreater(gate["counts"]["schema_validation_errors"], 0)


class ManifestAuditTests(unittest.TestCase):
    @staticmethod
    def ready_row(**updates):
        row = {
            "record_id": "provider:1",
            "source_record_id": "1",
            "provenance_source": "provider/source.json",
            "source": "Example Work",
            "tradition": "Sunni",
            "chain_indx": "1",
            "text_ar": "Arabic source text",
            "text_en": "A complete verified English translation.",
            "translation_status": "complete",
            "translation_source": "licensed source edition",
            "translation_model": "",
            "translation_review_status": "source_verified",
        }
        row.update(updates)
        return row

    def test_manifest_counts_translation_provenance_states(self):
        rows = [
            {
                "record_id": "k6:1",
                "source": "One",
                "tradition": "Sunni",
                "translation_status": "complete",
                "translation_source": "source-a",
                "translation_model": "model-a",
                "translation_review_status": "source_verified",
            },
            {
                "record_id": "k6:2",
                "source": "One",
                "tradition": "Sunni",
                "translation_status": "missing",
                "translation_source": "",
                "translation_review_status": "",
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "manifest.json"
            regen.write_curation_manifest(
                rows, [], str(output), source_registry={}, narrator_ids=set(),
                input_paths=[],
            )
            manifest = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(manifest["translation_status_counts"], {"complete": 1, "missing": 1})
        self.assertEqual(
            manifest["translation_review_status_counts"],
            {"<missing>": 1, "source_verified": 1},
        )
        self.assertEqual(
            manifest["translation_source_counts"],
            {"<missing>": 1, "source-a": 1},
        )
        self.assertEqual(
            manifest["translation_model_counts"],
            {"<missing>": 1, "model-a": 1},
        )

    def test_manifest_inputs_fingerprint_chain_extractor_and_helpers(self):
        paths = regen._manifest_input_paths(
            "sunni-input.csv", "imami-input.csv", rebuilt_imami=False
        )

        self.assertIn(regen.UNIFIED_ISNAD_EXTRACTOR, paths)
        self.assertIn(regen.UNIFIED_ISNAD_HELPERS, paths)
        self.assertIn(regen.EVIDENCE_CURATION_SCHEMA_JSON, paths)
        self.assertIn(regen.EVIDENCE_CURATION_BUNDLE_JSON, paths)

    def test_custom_input_paths_cannot_omit_citation_evidence_gate(self):
        blocked_gate = {
            "passed": False,
            "counts": {"bundle_missing_or_invalid": 1},
        }
        with (
            tempfile.TemporaryDirectory() as directory,
            mock.patch.object(
                regen, "evidence_curation_gate", return_value=blocked_gate
            ) as gate,
        ):
            manifest = regen.write_curation_manifest(
                [self.ready_row()], [], str(Path(directory) / "manifest.json"),
                source_registry={"Example Work": "Sunni"},
                narrator_ids={1},
                input_paths=[],
            )

        gate.assert_called_once_with()
        self.assertFalse(manifest["ready_for_full_load"])
        self.assertEqual(
            manifest["full_load_gates"]["citation_bound_evidence"],
            blocked_gate,
        )

    def test_published_manifest_is_bound_to_logical_csv_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            csv_path = root / "all_hadiths_unified.csv"
            csv_path.write_bytes(b"record_id,text_ar,text_en\nk6:1,arabic,English\n")
            with gzip.open(str(csv_path) + ".gz", "wb") as handle:
                handle.write(csv_path.read_bytes())
            manifest_path = root / "curation_manifest.json"
            manifest_path.write_text(
                json.dumps({"ready_for_full_load": True}),
                encoding="utf-8",
            )
            published_csv_path = root / "published" / "all_hadiths_unified.csv"

            with mock.patch.object(regen, "BASE_DIR", str(root)):
                regen.bind_published_dataset_manifest(
                    str(manifest_path), str(csv_path), str(published_csv_path)
                )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            gzip_physical_hash = hashlib.sha256(
                (root / "all_hadiths_unified.csv.gz").read_bytes()
            ).hexdigest()

        expected = hashlib.sha256(
            b"record_id,text_ar,text_en\nk6:1,arabic,English\n"
        ).hexdigest()
        self.assertEqual(manifest["published_dataset"]["logical_sha256"], expected)
        self.assertEqual(manifest["published_dataset"]["csv"]["sha256"], expected)
        self.assertEqual(
            manifest["published_dataset"]["csv"]["path"],
            "published/all_hadiths_unified.csv",
        )
        self.assertEqual(
            manifest["published_dataset"]["gzip"]["path"],
            "published/all_hadiths_unified.csv.gz",
        )
        self.assertEqual(
            manifest["published_dataset"]["gzip"]["logical_sha256"], expected
        )
        self.assertEqual(
            manifest["published_dataset"]["gzip"]["sha256"],
            gzip_physical_hash,
        )

    def test_full_readiness_requires_chain_registry_provenance_and_review(self):
        ready = self.ready_row()
        with (
            tempfile.TemporaryDirectory() as directory,
            mock.patch.object(
                regen, "evidence_curation_gate",
                return_value={"passed": True, "counts": {}},
            ),
        ):
            root = Path(directory)
            ready_path = root / "ready.json"
            ready_manifest = regen.write_curation_manifest(
                [ready], [], str(ready_path),
                source_registry={"Example Work": "Sunni"},
                narrator_ids={1},
                input_paths=[],
            )
            blocked_path = root / "blocked.json"
            blocked_manifest = regen.write_curation_manifest(
                [{**ready, "chain_indx": "", "source": "Display Variant",
                  "translation_review_status": "source_provided"}],
                [], str(blocked_path),
                source_registry={"Example Work": "Sunni"},
                narrator_ids={1},
                input_paths=[],
            )

        self.assertTrue(ready_manifest["ready_for_full_load"])
        self.assertFalse(blocked_manifest["ready_for_full_load"])
        self.assertEqual(blocked_manifest["release_blockers"], {})
        self.assertEqual(
            blocked_manifest["full_load_gates"]["chain"]["counts"]["missing_chain_indx"],
            1,
        )
        self.assertEqual(
            blocked_manifest["full_load_gates"]["source_registry"]["counts"]
            ["unregistered_source_rows"],
            1,
        )
        self.assertEqual(
            blocked_manifest["full_load_gates"]["translation_review"]["counts"]
            ["not_publication_ready"],
            1,
        )

    def test_chain_gate_reports_coverage_by_tradition(self):
        sunni = self.ready_row(record_id="sunni:1", tradition="Sunni")
        imami = self.ready_row(
            record_id="imami:1", tradition="Imami", chain_indx=""
        )
        gates = regen.assess_full_load_gates(
            [sunni, imami],
            source_registry={"Example Work": "Sunni"},
            narrator_ids={1},
        )
        by_tradition = gates["chain"]["by_tradition"]
        self.assertEqual(by_tradition["Sunni"]["present_chain_indx"], 1)
        self.assertEqual(by_tradition["Sunni"]["missing_chain_indx"], 0)
        self.assertEqual(by_tradition["Imami"]["present_chain_indx"], 0)
        self.assertEqual(by_tradition["Imami"]["missing_chain_indx"], 1)


class PublicationMechanicsTests(unittest.TestCase):
    def test_incomplete_publication_cannot_overwrite_canonical_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stage = root / "stage"
            stage.mkdir()
            canonical_names = (
                "all_hadiths_unified.csv", "all_hadiths_unified.csv.gz",
                "all_hadiths_clean.csv", "all_hadiths_clean.csv.gz",
                "all_hadiths_shia.csv", "all_hadiths_shia.csv.gz",
                "curation_backlog.csv", "curation_candidate_manifest.json",
                "curation_manifest.json",
            )
            canonical = {}
            for name in canonical_names:
                path = root / name
                path.write_bytes(f"published:{name}".encode("utf-8"))
                canonical[path] = path.read_bytes()

            staged = {}
            for name in (
                "all_hadiths_unified.csv", "all_hadiths_clean.csv",
                "all_hadiths_shia.csv",
            ):
                path = stage / name
                path.write_bytes(f"candidate:{name}".encode("utf-8"))
                Path(f"{path}.gz").write_bytes(b"candidate gzip")
                staged[name] = path
            backlog = stage / "curation_backlog.csv"
            backlog.write_text("issue\n", encoding="utf-8")
            manifest = stage / "curation_manifest.json"
            manifest.write_text(
                json.dumps({"ready_for_full_load": False}), encoding="utf-8"
            )
            development_root = root / "development" / "incomplete-curation"

            with mock.patch.object(regen, "BASE_DIR", str(root)):
                targets = regen.publish_incomplete_development_artifacts(
                    str(staged["all_hadiths_unified.csv"]),
                    str(staged["all_hadiths_clean.csv"]),
                    str(staged["all_hadiths_shia.csv"]),
                    str(backlog),
                    str(manifest),
                    development_root=str(development_root),
                )

            self.assertTrue(Path(targets["manifest"]).is_file())
            self.assertTrue(Path(targets["unified_csv"]).name.endswith(".incomplete.csv"))
            for path, expected in canonical.items():
                self.assertEqual(path.read_bytes(), expected)

    def test_canonical_backup_and_replace_share_one_lock_scope(self):
        events = []

        class LockScope:
            def __enter__(self):
                events.append("lock-enter")

            def __exit__(self, *_args):
                events.append("lock-exit")

        with (
            mock.patch.object(regen, "publication_lock", return_value=LockScope()),
            mock.patch.object(
                regen, "backup_unified_csv",
                side_effect=lambda _path: events.append("backup"),
            ),
            mock.patch.object(
                regen, "publish_staged_files",
                side_effect=lambda *_args, **_kwargs: events.append("replace"),
            ),
        ):
            regen.publish_canonical_dataset(
                [("manifest.stage", "manifest.json")],
                "manifest.json",
                "all_hadiths_unified.csv",
            )

        self.assertEqual(
            events, ["lock-enter", "backup", "replace", "lock-exit"]
        )

    def test_stage_directory_is_cleaned_when_build_raises(self):
        with tempfile.TemporaryDirectory() as directory:
            created = []

            def fail_after_staging(stage_dir):
                created.append(Path(stage_dir))
                (Path(stage_dir) / "partial.csv").write_text(
                    "partial", encoding="utf-8"
                )
                raise RuntimeError("simulated staged rebuild failure")

            with mock.patch.object(regen, "BASE_DIR", directory):
                with self.assertRaisesRegex(RuntimeError, "simulated"):
                    regen.run_with_stage_dir(fail_after_staging)

            self.assertEqual(len(created), 1)
            self.assertFalse(created[0].exists())

    def test_no_shia_prefers_exact_authoritative_gzip_over_stale_plain(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plain = root / "all_hadiths_shia.csv"
            gzip_path = Path(str(plain) + ".gz")
            header = (
                "hadith_id,provider_file_id,provider_book_id,source,volume,"
                "chain_indx,url,text_ar,text_en\n"
            )
            plain.write_text(
                header
                + "1,1,Al-Kafi-Volume-1-Kulayni,Stale,1,,"
                  "https://thaqalayn.net/hadith/1/0/1/1,Arabic,English\n",
                encoding="utf-8",
            )
            authoritative = (
                header
                + "1,1,Al-Kafi-Volume-1-Kulayni,Al-Kāfi,1,42,"
                  "https://thaqalayn.net/hadith/1/0/1/1,Arabic,English\n"
            ).encode("utf-8")
            with gzip.open(gzip_path, "wb") as handle:
                handle.write(authoritative)

            selected = regen.resolve_no_shia_input(str(plain))
            rows = regen.load_imami_rows(
                selected, authoritative_input=True
            )
            manifest_inputs = regen._manifest_input_paths(
                "sunni-input.csv", selected, rebuilt_imami=False
            )
            with mock.patch.object(regen, "BASE_DIR", str(root)):
                manifest = regen.write_curation_manifest(
                    [],
                    [],
                    str(root / "manifest.json"),
                    source_registry={},
                    narrator_ids=set(),
                    input_paths=[selected],
                )
            selected_hash = hashlib.sha256(gzip_path.read_bytes()).hexdigest()

        self.assertEqual(selected, str(gzip_path.resolve()))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["chain_indx"], "42")
        self.assertIn(selected, manifest_inputs)
        self.assertNotIn(str(plain), manifest_inputs)
        self.assertEqual(
            manifest["inputs"]["all_hadiths_shia.csv.gz"]["sha256"],
            selected_hash,
        )

    def test_manifest_commit_target_must_be_last(self):
        with self.assertRaisesRegex(ValueError, "replaced last"):
            regen.publish_staged_files(
                [("manifest.stage", "manifest.json"), ("data.stage", "data.csv")],
                commit_target="manifest.json",
            )

    def test_failed_candidate_preserves_valid_bound_manifest_byte_for_byte(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            active_csv = root / "all_hadiths_unified.csv"
            active_csv.write_bytes(b"id,text\n1,published\n")
            with gzip.open(str(active_csv) + ".gz", "wb") as handle:
                handle.write(active_csv.read_bytes())
            active_manifest = root / "curation_manifest.json"
            active_manifest.write_text(
                json.dumps({"ready_for_full_load": True}), encoding="utf-8"
            )
            with mock.patch.object(regen, "BASE_DIR", str(root)):
                regen.bind_published_dataset_manifest(
                    str(active_manifest), str(active_csv)
                )
            published_bytes = active_manifest.read_bytes()

            staged_backlog = root / "backlog.stage"
            staged_backlog.write_text("issue\n", encoding="utf-8")
            backlog = root / "curation_backlog.csv"
            staged_candidate = root / "candidate.stage"
            staged_candidate.write_text(
                json.dumps({"ready_for_full_load": False}), encoding="utf-8"
            )
            candidate = root / "curation_candidate_manifest.json"

            outcome = regen.publish_failed_candidate(
                str(staged_backlog), str(backlog), str(staged_candidate),
                str(candidate), str(active_manifest), str(active_csv),
            )

            self.assertEqual(outcome, "preserved_active_manifest")
            self.assertEqual(active_manifest.read_bytes(), published_bytes)
            self.assertFalse(
                json.loads(candidate.read_text(encoding="utf-8"))
                ["ready_for_full_load"]
            )

    def test_clean_input_transparently_falls_back_to_gzip(self):
        with tempfile.TemporaryDirectory() as directory:
            plain = Path(directory) / "all_hadiths_clean.csv"
            payload = (
                'id,source,text_ar,text_en\n'
                '1,Sahih Bukhari,Arabic,English translation\n'
            ).encode("utf-8")
            with gzip.open(str(plain) + ".gz", "wb") as handle:
                handle.write(payload)

            rows = regen.load_sunni_rows(str(plain))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["tradition"], "Sunni")

    def test_plain_and_gzip_pair_must_have_identical_logical_content(self):
        with tempfile.TemporaryDirectory() as directory:
            plain = Path(directory) / "all_hadiths_clean.csv"
            plain.write_bytes(b"id,source\n1,Sahih Bukhari\n")
            with gzip.open(str(plain) + ".gz", "wb") as handle:
                handle.write(b"id,source\n2,Sahih Muslim\n")

            with self.assertRaisesRegex(ValueError, "logical content diverges"):
                regen.resolve_csv_input_path(str(plain))

    def test_gzip_companion_is_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "candidate.csv"
            csv_path.write_bytes(b"id,text\n1,stable\n")
            regen.compress_csv(str(csv_path))
            first = Path(str(csv_path) + ".gz").read_bytes()
            regen.compress_csv(str(csv_path))
            second = Path(str(csv_path) + ".gz").read_bytes()

        self.assertEqual(first, second)
        self.assertEqual(gzip.decompress(second), b"id,text\n1,stable\n")

    def test_publish_rolls_back_already_replaced_files_on_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first_stage = root / "first.stage"
            second_stage = root / "second.stage"
            first_target = root / "first.csv"
            second_target = root / "second.csv"
            first_stage.write_text("new-first", encoding="utf-8")
            second_stage.write_text("new-second", encoding="utf-8")
            first_target.write_text("old-first", encoding="utf-8")
            second_target.write_text("old-second", encoding="utf-8")
            real_replace = regen.os.replace

            def fail_second_stage(source, target):
                if Path(source) == second_stage and Path(target) == second_target:
                    raise OSError("simulated publication failure")
                return real_replace(source, target)

            with mock.patch.object(regen.os, "replace", side_effect=fail_second_stage):
                with self.assertRaisesRegex(OSError, "simulated"):
                    regen.publish_staged_files([
                        (str(first_stage), str(first_target)),
                        (str(second_stage), str(second_target)),
                    ])

            self.assertEqual(first_target.read_text(encoding="utf-8"), "old-first")
            self.assertEqual(second_target.read_text(encoding="utf-8"), "old-second")


if __name__ == "__main__":
    unittest.main()
