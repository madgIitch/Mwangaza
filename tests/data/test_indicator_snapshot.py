from __future__ import annotations

import unittest
from dataclasses import replace

from mwangaza.contracts import Anomaly, IndicatorObservation
from mwangaza.data.indicator_snapshot import (
    IndicatorSnapshotError,
    build_indicator_snapshot,
)


def _observation(**overrides: object) -> IndicatorObservation:
    payload = {
        "region_id": "ken",
        "indicator": "ndvi",
        "period_start": "2026-07-01T00:00:00Z",
        "period_end": "2026-07-08T00:00:00Z",
        "value": 0.42,
        "unit": "index",
        "source": "TEST/NDVI",
        "quality_flag": "ok",
        "is_simulated": True,
        "metadata": {"updated_at": "2026-07-09T03:00:00Z"},
    }
    payload.update(overrides)
    return IndicatorObservation(**payload)


def _anomaly(**overrides: object) -> Anomaly:
    payload = {
        "region_id": "ken",
        "indicator": "rainfall_mm",
        "period_start": "2026-07-01T00:00:00Z",
        "period_end": "2026-07-08T00:00:00Z",
        "value": -12.0,
        "unit": "mm",
        "baseline_id": "rainfall-baseline-v1",
        "method": "current_minus_mean",
        "source": "mwangaza.anomaly.rainfall",
        "quality_flag": "degraded",
        "is_simulated": True,
        "metadata": {"updated_at": "2026-07-10T06:30:00Z"},
    }
    payload.update(overrides)
    return Anomaly(**payload)


class IndicatorSnapshotTests(unittest.TestCase):
    def test_builds_snapshot_for_single_region_and_window(self) -> None:
        snapshot = build_indicator_snapshot(
            "ken",
            "2026-07-01T00:00:00Z",
            "2026-07-08T00:00:00Z",
            [_observation(), _anomaly()],
            expected_indicators=("ndvi", "rainfall_mm", "lst_c"),
        )

        self.assertEqual(snapshot.region_id, "ken")
        self.assertEqual(snapshot.period_start, "2026-07-01T00:00:00Z")
        self.assertEqual(snapshot.period_end, "2026-07-08T00:00:00Z")
        self.assertEqual(snapshot.indicators_present, ("ndvi",))
        self.assertEqual(snapshot.indicators_absent, ("lst_c",))
        self.assertEqual(snapshot.indicators_degraded, ("rainfall_mm",))
        self.assertEqual(snapshot.quality_flag, "invalid")
        self.assertEqual(snapshot.oldest_updated_at, "2026-07-09T03:00:00Z")
        self.assertEqual(snapshot.newest_updated_at, "2026-07-10T06:30:00Z")
        self.assertEqual(snapshot.snapshot_id, snapshot.content_hash[:16])
        self.assertTrue(snapshot.is_simulated)
        self.assertEqual(snapshot.metadata["signal_count"], 2)

    def test_rejects_region_or_window_mismatch(self) -> None:
        with self.assertRaisesRegex(IndicatorSnapshotError, "region_id"):
            build_indicator_snapshot(
                "ken",
                "2026-07-01T00:00:00Z",
                "2026-07-08T00:00:00Z",
                [_observation(region_id="som")],
            )
        with self.assertRaisesRegex(IndicatorSnapshotError, "window"):
            build_indicator_snapshot(
                "ken",
                "2026-07-01T00:00:00Z",
                "2026-07-08T00:00:00Z",
                [_observation(period_end="2026-07-09T00:00:00Z")],
            )

    def test_hash_is_reproducible_when_signal_order_changes(self) -> None:
        first = build_indicator_snapshot(
            "ken",
            "2026-07-01T00:00:00Z",
            "2026-07-08T00:00:00Z",
            [_observation(), _anomaly()],
            expected_indicators=("ndvi", "rainfall_mm"),
        )
        second = build_indicator_snapshot(
            "ken",
            "2026-07-01T00:00:00Z",
            "2026-07-08T00:00:00Z",
            [_anomaly(), _observation()],
            expected_indicators=("rainfall_mm", "ndvi"),
        )

        self.assertEqual(first.content_hash, second.content_hash)
        self.assertEqual(first.signals, second.signals)

    def test_updating_source_creates_new_snapshot_without_mutating_previous(self) -> None:
        original_signal = _observation(value=0.42, metadata={"updated_at": "2026-07-09T03:00:00Z"})
        original = build_indicator_snapshot(
            "ken",
            "2026-07-01T00:00:00Z",
            "2026-07-08T00:00:00Z",
            [original_signal],
        )
        updated = build_indicator_snapshot(
            "ken",
            "2026-07-01T00:00:00Z",
            "2026-07-08T00:00:00Z",
            [
                replace(
                    original_signal,
                    value=0.5,
                    metadata={"updated_at": "2026-07-11T03:00:00Z"},
                )
            ],
        )

        self.assertNotEqual(original.content_hash, updated.content_hash)
        self.assertNotEqual(original.snapshot_id, updated.snapshot_id)
        self.assertEqual(original.signals[0]["value"], 0.42)
        self.assertEqual(updated.signals[0]["value"], 0.5)

    def test_uses_period_end_as_updated_at_fallback(self) -> None:
        snapshot = build_indicator_snapshot(
            "ken",
            "2026-07-01T00:00:00Z",
            "2026-07-08T00:00:00Z",
            [_observation(metadata={})],
        )

        self.assertEqual(snapshot.oldest_updated_at, "2026-07-08T00:00:00Z")
        self.assertEqual(snapshot.newest_updated_at, "2026-07-08T00:00:00Z")

    def test_accepts_contract_dict_input(self) -> None:
        snapshot = build_indicator_snapshot(
            "ken",
            "2026-07-01T00:00:00Z",
            "2026-07-08T00:00:00Z",
            [_observation().to_dict()],
        )

        self.assertEqual(snapshot.indicators_present, ("ndvi",))
        self.assertEqual(snapshot.signals[0]["payload_type"], "indicator_observation")

    def test_rejects_duplicate_invalid_timestamp_and_non_serializable_metadata(self) -> None:
        with self.assertRaisesRegex(IndicatorSnapshotError, "duplicate"):
            build_indicator_snapshot(
                "ken",
                "2026-07-01T00:00:00Z",
                "2026-07-08T00:00:00Z",
                [_observation(), _observation(source="TEST/NDVI/V2")],
            )
        with self.assertRaisesRegex(IndicatorSnapshotError, "updated_at"):
            build_indicator_snapshot(
                "ken",
                "2026-07-01T00:00:00Z",
                "2026-07-08T00:00:00Z",
                [_observation(metadata={"updated_at": "not-a-date"})],
            )
        with self.assertRaisesRegex(IndicatorSnapshotError, "serializable"):
            build_indicator_snapshot(
                "ken",
                "2026-07-01T00:00:00Z",
                "2026-07-08T00:00:00Z",
                [_observation(metadata={"updated_at": "2026-07-09T03:00:00Z", "bad": object()})],
            )

    def test_rejects_unknown_expected_indicator_and_incompatible_unit(self) -> None:
        with self.assertRaisesRegex(IndicatorSnapshotError, "unsupported expected"):
            build_indicator_snapshot(
                "ken",
                "2026-07-01T00:00:00Z",
                "2026-07-08T00:00:00Z",
                [_observation()],
                expected_indicators=("unknown",),
            )
        with self.assertRaisesRegex(IndicatorSnapshotError, "incompatible"):
            build_indicator_snapshot(
                "ken",
                "2026-07-01T00:00:00Z",
                "2026-07-08T00:00:00Z",
                [_observation(unit="mm")],
            )


if __name__ == "__main__":
    unittest.main()
