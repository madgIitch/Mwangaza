from __future__ import annotations

import json
import math
import unittest
from pathlib import Path

from mwangaza.contracts import (
    SCHEMA_VERSION,
    Anomaly,
    Baseline,
    ContractValidationError,
    Forecast,
    IndicatorObservation,
    dumps_payload,
    loads_payload,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "contracts"


class ContractRoundtripTests(unittest.TestCase):
    def test_canonical_fixtures_roundtrip_without_loss(self) -> None:
        for path in sorted(FIXTURES.glob("*.json")):
            with self.subTest(path=path.name):
                raw = json.loads(path.read_text(encoding="utf-8"))
                payload = loads_payload(raw)
                self.assertTrue(payload.to_dict()["is_simulated"])
                self.assertEqual(payload.to_dict()["schema_version"], SCHEMA_VERSION)
                self.assertEqual(json.loads(dumps_payload(payload)), raw)

    def test_indicator_observation_required_contract(self) -> None:
        payload = loads_payload(_fixture("indicator_observation.json"))
        self.assertIsInstance(payload, IndicatorObservation)
        public = payload.to_dict()
        self.assertEqual(public["indicator"], "ndvi")
        self.assertEqual(public["unit"], "index")
        self.assertIn("region_id", public)
        self.assertIn("quality_flag", public)

    def test_all_payload_classes_are_exposed(self) -> None:
        self.assertIsInstance(loads_payload(_fixture("baseline.json")), Baseline)
        self.assertIsInstance(loads_payload(_fixture("anomaly.json")), Anomaly)
        self.assertEqual(loads_payload(_fixture("risk_snapshot.json")).payload_type, "risk_snapshot")
        self.assertEqual(loads_payload(_fixture("alert.json")).payload_type, "alert")
        self.assertIsInstance(loads_payload(_fixture("forecast.json")), Forecast)


class ContractValidationTests(unittest.TestCase):
    def test_rejects_non_finite_values(self) -> None:
        payload = _fixture("indicator_observation.json")
        payload["value"] = math.inf
        with self.assertRaisesRegex(ContractValidationError, "value"):
            loads_payload(payload)

    def test_rejects_incompatible_indicator_unit(self) -> None:
        payload = _fixture("indicator_observation.json")
        payload["unit"] = "mm"
        with self.assertRaisesRegex(ContractValidationError, "incompatible"):
            loads_payload(payload)

    def test_rejects_inverted_dates(self) -> None:
        payload = _fixture("indicator_observation.json")
        payload["period_start"] = "2026-07-20T00:00:00Z"
        with self.assertRaisesRegex(ContractValidationError, "period_start"):
            loads_payload(payload)

    def test_rejects_unknown_region(self) -> None:
        payload = _fixture("indicator_observation.json")
        payload["region_id"] = "missing-region"
        with self.assertRaisesRegex(ContractValidationError, "region_id"):
            loads_payload(payload)

    def test_rejects_missing_schema_version(self) -> None:
        payload = _fixture("indicator_observation.json")
        del payload["schema_version"]
        with self.assertRaisesRegex(ContractValidationError, "schema_version"):
            loads_payload(payload)

    def test_rejects_unknown_indicator(self) -> None:
        payload = _fixture("indicator_observation.json")
        payload["indicator"] = "soil_moisture"
        with self.assertRaisesRegex(ContractValidationError, "indicator"):
            loads_payload(payload)

    def test_rejects_missing_is_simulated_for_fixture_payloads(self) -> None:
        payload = _fixture("indicator_observation.json")
        del payload["is_simulated"]
        with self.assertRaisesRegex(ContractValidationError, "is_simulated"):
            loads_payload(payload)

    def test_rejects_simulated_fixture_contradiction(self) -> None:
        payload = _fixture("indicator_observation.json")
        payload["is_simulated"] = False
        payload["metadata"]["fixture"] = "canonical"
        with self.assertRaisesRegex(ContractValidationError, "is_simulated"):
            loads_payload(payload)

    def test_value_none_requires_no_data_quality_flag(self) -> None:
        payload = _fixture("indicator_observation.json")
        payload["value"] = None
        with self.assertRaisesRegex(ContractValidationError, "value=None"):
            loads_payload(payload)

        payload["quality_flag"] = "no_data"
        loaded = loads_payload(payload)
        self.assertIsNone(loaded.to_dict()["value"])

    def test_rejects_sensitive_source_path(self) -> None:
        payload = _fixture("indicator_observation.json")
        payload["source"] = "C:\\Users\\secret\\token.json"
        with self.assertRaisesRegex(ContractValidationError, "source"):
            loads_payload(payload)


def _fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
