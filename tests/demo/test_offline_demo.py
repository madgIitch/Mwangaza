from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OfflineDemoTests(unittest.TestCase):
    def test_reset_is_idempotent(self):
        reset = load_script("reset_demo")
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state.json"
            state.write_text('{"is_demo":false,"foreign":"preserved elsewhere"}', encoding="utf-8")
            first = reset.reset_demo(state)
            second = reset.reset_demo(state)
            saved = json.loads(state.read_text(encoding="utf-8"))
        self.assertEqual(first, second)
        self.assertEqual(saved, first)
        self.assertTrue(saved["is_demo"])
        self.assertEqual(saved["alerts"], [])
        self.assertEqual(saved["outbox"], [])

    def test_scenarios_expose_demo_metadata(self):
        for name, fixture in (("demo_somalia", "somalia"), ("demo_kenya", "kenya")):
            scenario = load_script(name)
            fixture_path = ROOT / "tests" / "fixtures" / "scenarios" / fixture / "snapshot.json"
            with tempfile.TemporaryDirectory() as directory:
                result = scenario.prepare_scenario(fixture_path, Path(directory) / "state.json")
            self.assertTrue(result["is_demo"])
            self.assertIn("reference_date", result)


if __name__ == "__main__":
    unittest.main()
