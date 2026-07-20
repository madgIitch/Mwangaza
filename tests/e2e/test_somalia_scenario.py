from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "demo_somalia.py"
FIXTURE = ROOT / "tests" / "fixtures" / "scenarios" / "somalia" / "snapshot.json"


def load_scenario_module():
    spec = importlib.util.spec_from_file_location("demo_somalia", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SomaliaScenarioTests(unittest.TestCase):
    def test_offline_scenario_is_complete_and_idempotent(self) -> None:
        scenario = load_scenario_module()
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "state.json"
            first = scenario.prepare_scenario(FIXTURE, state_path)
            second = scenario.prepare_scenario(FIXTURE, state_path)
            state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "complete")
        self.assertTrue(first["offline"])
        self.assertEqual(set(first["artifacts"]), set(scenario.REQUIRED_ARTIFACTS))
        self.assertEqual(len(first["alerts"]), 1)
        self.assertEqual(len(first["notifications"]), 1)
        self.assertEqual(len(state["scenarios"]), 1)
        for artifact in first["artifacts"].values():
            self.assertEqual(artifact["snapshot_id"], first["snapshot_id"])
            self.assertIn(artifact["provenance"], {"demo", "simulated"})

    def test_cli_reports_invalid_fixture_without_completed_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            fixture, state = base / "invalid.json", base / "state.json"
            fixture.write_text('{"mode": "demo"}', encoding="utf-8")
            completed = subprocess.run([sys.executable, str(SCRIPT), "--fixture", str(fixture), "--state", str(state)], check=False, capture_output=True, text=True)
            self.assertFalse(state.exists())
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("snapshot_id", completed.stderr)

    def test_cli_succeeds_without_network_or_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state.json"
            completed = subprocess.run([sys.executable, str(SCRIPT), "--fixture", str(FIXTURE), "--state", str(state)], check=False, capture_output=True, text=True, env={})
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["mode"], "demo")


if __name__ == "__main__":
    unittest.main()
