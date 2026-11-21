"""The pinned translator (translation_model.json) drives both generators; no API is called."""

import argparse
import importlib.util
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

DATA_DIR = Path(__file__).resolve().parents[1]


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, DATA_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


translation = load_module("pin_test_generator", "generate_machine_translation_candidates.py")
hy = load_module("pin_test_hy_mt2", "generate_hy_mt2_candidates.py")
PIN = json.loads((DATA_DIR / "translation_model.json").read_text(encoding="utf-8"))


def defaults_for(backend, model=None, allow=False):
    args = argparse.Namespace(
        backend=backend, api_base=None, model=model, output=None, checkpoint=None,
        max_cost_usd=None, allow_unpinned_model=allow,
    )
    translation.apply_backend_defaults(args)
    return args


class PinConfigTests(unittest.TestCase):
    def test_pin_is_the_owner_decision(self):
        self.assertEqual(PIN["model_id"], "tencent/hy-mt2-30b-a3b")
        self.assertEqual(PIN["provider"], "openrouter")
        self.assertEqual(PIN["decision"]["decided_by"], "owner")
        self.assertIn("{source_text}", PIN["prompt"]["template"])

    def test_hy_generator_reads_every_pinned_value(self):
        self.assertEqual(hy.MODEL, PIN["model_id"])
        self.assertEqual(hy.PIPELINE, PIN["pipeline"])
        self.assertEqual(hy.PROMPT_VERSION, PIN["prompt"]["version"])
        self.assertEqual(hy.PROMPT_TEMPLATE, PIN["prompt"]["template"])
        self.assertEqual(hy.TEMPERATURE, PIN["generation"]["temperature"])
        self.assertEqual(hy.CONTEXT_TOKENS, PIN["generation"]["context_tokens"])
        self.assertEqual(hy.MAX_COMPLETION_TOKENS, PIN["generation"]["max_completion_tokens"])
        self.assertAlmostEqual(hy.PRICE_PROMPT * 1e6, PIN["pricing_usd_per_million_tokens"]["prompt"])
        self.assertAlmostEqual(hy.PRICE_COMPLETION * 1e6, PIN["pricing_usd_per_million_tokens"]["completion"])
        self.assertEqual(hy.SCREEN_VERSION, PIN["qa_screen"]["version"])
        self.assertEqual(hy.PROVIDER_POLICY, PIN["provider_policy"])

    def test_request_body_sent_to_openrouter_carries_the_pin(self):
        captured = {}

        def fake_urlopen(request, timeout):
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return io.BytesIO(json.dumps({"choices": [], "usage": {}}).encode("utf-8"))

        with mock.patch.object(hy.urllib.request, "urlopen", fake_urlopen):
            hy.call_model("test-key", "نص عربي", 512)
        body = captured["body"]
        self.assertEqual(body["model"], PIN["model_id"])
        self.assertEqual(body["messages"], [{"role": "user", "content": PIN["prompt"]["template"].format(source_text="نص عربي")}])
        self.assertEqual(body["temperature"], PIN["generation"]["temperature"])
        self.assertEqual(body["provider"], PIN["provider_policy"])


class OlderGeneratorPinTests(unittest.TestCase):
    def test_default_model_is_the_pin_for_both_backends(self):
        for backend in ("openrouter", "local"):
            with self.subTest(backend=backend):
                self.assertEqual(defaults_for(backend).model, PIN["model_id"])

    def test_unpinned_model_is_refused_unless_explicitly_allowed(self):
        for backend, model in (
            ("openrouter", "google/gemini-2.5-flash"),
            ("local", "google/gemma-4-e4b"),
            ("openrouter", "tencent/hy-mt2-7b"),
        ):
            with self.subTest(backend=backend, model=model):
                with self.assertRaisesRegex(ValueError, "not the pinned translator"):
                    defaults_for(backend, model)
                self.assertEqual(defaults_for(backend, model, allow=True).model, model)

    def test_main_refuses_an_unpinned_model_before_any_work(self):
        argv = ["generate", "--backend", "openrouter", "--dry-run", "--model", "google/gemini-2.5-flash"]
        with mock.patch.object(sys, "argv", argv), self.assertRaisesRegex(ValueError, "--allow-unpinned-model"):
            translation.main()

    def test_default_artifacts_are_named_for_the_model_so_journals_cannot_mix(self):
        pinned = defaults_for("openrouter")
        self.assertEqual(pinned.output.name, "openrouter_hy_mt2_30b_a3b_candidates.jsonl")
        self.assertEqual(pinned.checkpoint.name, "openrouter_hy_mt2_30b_a3b_checkpoint.sqlite3")
        past = defaults_for("openrouter", "google/gemini-2.5-flash", allow=True)
        self.assertEqual(past.output.name, "openrouter_gemini_2_5_flash_candidates.jsonl")


if __name__ == "__main__":
    unittest.main()
