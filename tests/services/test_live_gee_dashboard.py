from __future__ import annotations

import unittest

from mwangaza.data.lst import LstCollectionConfig, LstQueryResult
from mwangaza.data.ndvi import NdviCollectionConfig, NdviQueryResult
from mwangaza.data.rainfall import RainfallCollectionConfig, RainfallQueryResult
from mwangaza.services.live_gee_dashboard import build_live_gee_payloads, resolve_live_gee_period


class FakeLiveGeeAdapter:
    def latest_collection_date(self, collection_id: str) -> str:
        dates = {
            "MODIS/061/MOD13Q1": "2026-06-25T00:00:00Z",
            "UCSB-CHG/CHIRPS/DAILY": "2026-07-10T00:00:00Z",
            "MODIS/061/MOD11A2": "2026-07-08T00:00:00Z",
        }
        return dates[collection_id]

    def query_ndvi(
        self,
        geometry: dict[str, object],
        period_start: str,
        period_end: str,
        config: NdviCollectionConfig,
    ) -> NdviQueryResult:
        return NdviQueryResult(
            mean_raw=3200.0,
            valid_pixel_count=10,
            total_pixel_count=10,
            actual_period_start=period_start,
            actual_period_end=period_end,
            is_simulated=False,
            metadata={"updated_at": period_end, "source_mode": "live"},
        )

    def query_rainfall(
        self,
        geometry: dict[str, object],
        period_start: str,
        period_end: str,
        config: RainfallCollectionConfig,
    ) -> RainfallQueryResult:
        return RainfallQueryResult(
            accumulated_mm=12.0,
            available_days=15,
            actual_period_start=period_start,
            actual_period_end=period_end,
            valid_pixel_count=10,
            total_pixel_count=10,
            is_simulated=False,
            metadata={"updated_at": period_end, "source_mode": "live"},
        )

    def query_lst(
        self,
        geometry: dict[str, object],
        period_start: str,
        period_end: str,
        config: LstCollectionConfig,
    ) -> LstQueryResult:
        return LstQueryResult(
            mean_c=35.0,
            median_c=34.0,
            valid_pixel_count=10,
            total_pixel_count=10,
            actual_period_start=period_start,
            actual_period_end=period_end,
            is_simulated=False,
            metadata={"updated_at": period_end, "source_mode": "live"},
        )


class LiveGeeDashboardTests(unittest.TestCase):
    def test_builds_real_gee_dashboard_payloads_from_adapter_results(self) -> None:
        payloads = build_live_gee_payloads(
            "som",
            "2026-07-01T00:00:00Z",
            "2026-07-15T00:00:00Z",
            adapter=FakeLiveGeeAdapter(),  # type: ignore[arg-type]
        )

        by_type = {payload.get("payload_type", "indicator_snapshot"): payload for payload in payloads}
        self.assertIn("risk_snapshot", by_type)
        self.assertFalse(any(payload.get("is_simulated") is True for payload in payloads))
        self.assertEqual(by_type["risk_snapshot"]["region_id"], "som")
        self.assertEqual(by_type["risk_snapshot"]["metadata"]["source_mode"], "live")
        indicators = {payload.get("indicator") for payload in payloads}
        self.assertIn("ndvi", indicators)
        self.assertIn("rainfall_mm", indicators)
        self.assertIn("lst_c", indicators)

    def test_resolves_default_window_to_latest_common_collection_date(self) -> None:
        start, end = resolve_live_gee_period(FakeLiveGeeAdapter())

        self.assertEqual(start, "2026-06-11T00:00:00Z")
        self.assertEqual(end, "2026-06-25T00:00:00Z")


if __name__ == "__main__":
    unittest.main()
