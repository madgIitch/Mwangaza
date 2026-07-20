from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import app
from tests.fixtures.deterministic import FIXED_NOW, FakeEarthEngine, FakeNotifier, fixed_clock


class AutomatedTestingInfrastructureTests(unittest.TestCase):
    def test_shared_fakes_are_deterministic_and_do_not_use_network(self) -> None:
        gee = FakeEarthEngine([TimeoutError("retry"), {"value": 0.2}])
        with self.assertRaises(TimeoutError):
            gee.query(region="som")
        self.assertEqual(gee.query(region="som"), {"value": 0.2})
        self.assertEqual(fixed_clock(), FIXED_NOW)

        notifier = FakeNotifier()
        self.assertEqual(notifier.send({"alert_id": "alert-1"}), "simulated-001")
        self.assertEqual(len(notifier.messages), 1)

    def test_legacy_streamlit_shim_remains_safe_without_streamlit(self) -> None:
        output = io.StringIO()
        with patch.dict("sys.modules", {"streamlit": None}), redirect_stdout(output):
            app.main()
        self.assertIn("moved to React/Vite", output.getvalue())


if __name__ == "__main__":
    unittest.main()
