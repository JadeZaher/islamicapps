"""The model registry validates, agrees with the pin, and docs/models.md is exactly what it renders."""

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("render_model_docs_test", DATA_DIR / "render_model_docs.py")
render = importlib.util.module_from_spec(SPEC)
sys.modules["render_model_docs_test"] = render
SPEC.loader.exec_module(render)

REGISTRY = render.load_json(render.REGISTRY_PATH)
SCHEMA = render.load_json(render.SCHEMA_PATH)
PIN = render.load_json(render.PIN_PATH)


class RegistryTests(unittest.TestCase):
    def test_registry_matches_schema_and_pin(self):
        self.assertEqual(render.validate(REGISTRY, SCHEMA, SCHEMA), [])
        self.assertEqual(render.integrity_errors(REGISTRY, PIN), [])

    def test_the_pinned_translator_is_candidate_only(self):
        (entry,) = [item for item in REGISTRY["entries"] if item["pinned"]]
        self.assertEqual(entry["model_id"], PIN["model_id"])
        self.assertEqual(entry["output_status"], "candidate_only")
        self.assertTrue(any("release" in use or "canonical" in use for use in entry["prohibited_uses"]))

    def test_broken_registries_are_rejected(self):
        def mutate(change):
            broken = copy.deepcopy(REGISTRY)
            change(broken)
            return render.validate(broken, SCHEMA, SCHEMA) + render.integrity_errors(broken, PIN)

        cases = {
            "unknown status": lambda r: r["entries"][0].update(output_status="approved"),
            "pin drift": lambda r: r["entries"][0].update(model_id="tencent/hy-mt2-7b"),
            "no evidence": lambda r: r["entries"][1].update(evidence=[]),
            "unrecorded model without status": lambda r: r["entries"][1].update(model_id=None),
            "vague identity without note": lambda r: r["entries"][5].update(model_id_note=""),
        }
        for name, change in cases.items():
            with self.subTest(name):
                self.assertTrue(mutate(change))


class GeneratedDocTests(unittest.TestCase):
    def test_docs_models_md_matches_the_registry(self):
        expected = render.build()
        actual = render.DOC_PATH.read_text(encoding="utf-8").replace("\r\n", "\n")
        self.assertEqual(actual, expected, "run: python datasets/hadith-data/render_model_docs.py")

    def test_doc_names_the_pin_and_flags_vague_identities(self):
        text = render.build()
        self.assertIn("`tencent/hy-mt2-30b-a3b` **pinned**", text)
        for entry in REGISTRY["entries"]:
            if entry["model_id_status"] != "namespaced_specific":
                self.assertIn(entry["id"], text)
                self.assertIn(entry["model_id_status"], text)


if __name__ == "__main__":
    unittest.main()
