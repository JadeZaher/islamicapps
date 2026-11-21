"""Focused tests for bounded narrator-resolution audit aggregation."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "audit_narrator_resolution.py"
SPEC = importlib.util.spec_from_file_location("audit_narrator_resolution_test", MODULE_PATH)
audit = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(audit)


class DiskCandidateAggregationTests(unittest.TestCase):
    def test_high_cardinality_candidates_emit_bounded_exact_deterministic_top(self):
        store = audit.DiskFrequencyCounter(max_pending_keys=2, max_pending_bytes=64)
        try:
            for index in range(64):
                store.increment_candidate(
                    surface=f"surface-{index:03d}",
                    scholar_indx=f"scholar-{index:03d}",
                    normalized_surface=f"normalized-{index:03d}",
                    row_number=index + 2,
                    hadith_id=f"hadith-{index:03d}",
                    source="source-first",
                    tradition="Ibadi",
                )

            for surface_index, extra_occurrences in ((49, 3), (10, 1), (11, 1)):
                for occurrence in range(extra_occurrences):
                    store.increment_candidate(
                        surface=f"surface-{surface_index:03d}",
                        scholar_indx=f"scholar-{surface_index:03d}",
                        normalized_surface=f"normalized-{surface_index:03d}",
                        row_number=1_000 + occurrence,
                        hadith_id="later-evidence",
                        source="source-later",
                        tradition="Sunni",
                    )

            emitted = store.top_candidates(3)

            self.assertEqual(store.candidate_count(), 64)
            self.assertEqual(len(emitted), 3)
            with self.assertRaisesRegex(ValueError, "non-negative"):
                store.top_candidates(-1)
            self.assertEqual(
                [(entry["surface"], entry["occurrences"]) for entry in emitted],
                [
                    ("surface-049", 4),
                    ("surface-010", 2),
                    ("surface-011", 2),
                ],
            )
            self.assertEqual(
                emitted[0]["evidence"],
                {
                    "transforms": ["NFKC", "remove_unicode_format_controls"],
                    "registry_match": "exact_normalized_unique_identity",
                    "first_input_row": 51,
                    "first_hadith_id": "hadith-049",
                    "first_source": "source-first",
                    "first_tradition": "Ibadi",
                },
            )
            self.assertEqual(
                emitted[0]["candidate_type"],
                "unicode_normalization_equivalence",
            )
            self.assertEqual(
                emitted[0]["status"],
                "machine_audited_not_human_verified",
            )
        finally:
            store.close()


class AuditOutputPathTests(unittest.TestCase):
    def test_atomic_write_does_not_follow_predictable_sibling_temp(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "audit.json"
            predictable = output.with_suffix(".json.tmp")
            predictable.write_text("sentinel", encoding="utf-8")

            audit.write_json(output, {"safe": True})

            self.assertEqual(predictable.read_text(encoding="utf-8"), "sentinel")
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), {"safe": True})

    def test_outputs_cannot_replace_inputs_or_each_other(self):
        with self.assertRaises(ValueError):
            audit.validate_output_paths(
                audit.DEFAULT_INPUT,
                audit.REGISTRY_PATH,
                audit.DEFAULT_INPUT,
                audit.DEFAULT_CANDIDATES,
            )
        with self.assertRaisesRegex(ValueError, "distinct"):
            audit.validate_output_paths(
                audit.DEFAULT_INPUT,
                audit.REGISTRY_PATH,
                audit.DEFAULT_AUDIT,
                audit.DEFAULT_AUDIT,
            )

    def test_durable_defaults_are_allowed(self):
        outputs = audit.validate_output_paths(
            audit.DEFAULT_INPUT,
            audit.REGISTRY_PATH,
            audit.DEFAULT_AUDIT,
            audit.DEFAULT_CANDIDATES,
        )
        self.assertEqual(outputs, (audit.DEFAULT_AUDIT.resolve(), audit.DEFAULT_CANDIDATES.resolve()))

    def test_default_symlink_is_rejected_before_resolution(self):
        default_audit = Path(audit.os.path.abspath(audit.os.fspath(audit.DEFAULT_AUDIT)))
        original_is_symlink = Path.is_symlink

        def pretend_default_is_symlink(path):
            return path == default_audit or original_is_symlink(path)

        with mock.patch.object(Path, "is_symlink", autospec=True, side_effect=pretend_default_is_symlink):
            with self.assertRaisesRegex(ValueError, "symlink"):
                audit.validate_output_paths(
                    audit.DEFAULT_INPUT,
                    audit.REGISTRY_PATH,
                    audit.DEFAULT_AUDIT,
                    audit.DEFAULT_CANDIDATES,
                )

    def test_redirected_diagnostics_parent_is_rejected(self):
        diagnostics_parent = Path(audit.os.path.abspath(audit.os.fspath(audit.DIAGNOSTIC_DIR.parent)))
        original_is_symlink = Path.is_symlink

        def pretend_parent_is_symlink(path):
            return path == diagnostics_parent or original_is_symlink(path)

        with mock.patch.object(Path, "is_symlink", autospec=True, side_effect=pretend_parent_is_symlink):
            with self.assertRaisesRegex(ValueError, "symlinks"):
                audit.validate_output_paths(
                    audit.DEFAULT_INPUT,
                    audit.REGISTRY_PATH,
                    audit.DIAGNOSTIC_DIR / "audit.json",
                    audit.DIAGNOSTIC_DIR / "candidates.json",
                )


if __name__ == "__main__":
    unittest.main()
