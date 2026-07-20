from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "demo_kenya.py"
FIXTURE = ROOT / "tests" / "fixtures" / "scenarios" / "kenya" / "snapshot.json"


def module():
    spec = importlib.util.spec_from_file_location("demo_kenya", SCRIPT)
    assert spec and spec.loader
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


class KenyaScenarioTests(unittest.TestCase):
    def test_complete_idempotent_selection_and_languages(self):
        scenario = module()
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state.json"
            first = scenario.prepare_scenario(FIXTURE, state, "KEN-010", "sw")
            second = scenario.prepare_scenario(FIXTURE, state, "KEN-010", "sw")
            saved = json.loads(state.read_text(encoding="utf-8"))
        self.assertEqual(first, second)
        self.assertEqual(first["highlighted_unit"], "KEN-023")
        self.assertEqual(first["selected_unit"], first["report"]["unit_id"])
        self.assertEqual(first["effective_language"], "sw")
        self.assertEqual(len(saved["scenarios"]), 1)

    def test_language_fallback_is_explicit(self):
        scenario = module()
        with tempfile.TemporaryDirectory() as directory:
            result = scenario.prepare_scenario(FIXTURE, Path(directory) / "state.json", language="fr")
        self.assertEqual(result["effective_language"], "en")
        self.assertEqual(result["warnings"][0]["code"], "language_fallback")

    def test_missing_report_fails_without_state(self):
        scenario = module()
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        del fixture["units"][0]["report"]
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            invalid, state = base / "invalid.json", base / "state.json"
            invalid.write_text(json.dumps(fixture), encoding="utf-8")
            with self.assertRaises(scenario.ScenarioError):
                scenario.prepare_scenario(invalid, state)
            self.assertFalse(state.exists())


if __name__ == "__main__":
    unittest.main()
