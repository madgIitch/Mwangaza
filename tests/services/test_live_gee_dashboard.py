from __future__ import annotations

import unittest
from unittest.mock import patch

from mwangaza.data.lst import LstCollectionConfig, LstQueryResult
from mwangaza.data.ndvi import NdviCollectionConfig, NdviQueryResult
from mwangaza.data.rainfall import RainfallCollectionConfig, RainfallQueryResult
from mwangaza.services.live_gee_dashboard import (
    build_live_gee_payloads,
    build_live_gee_payloads_for_adm1_regions,
    build_live_gee_payloads_for_recent_periods,
    build_live_gee_payloads_for_regions,
    build_live_gee_trend_payloads_for_regions,
    comparable_period_windows,
    dashboard_live_adm1_region_ids,
    dashboard_live_region_ids,
    monthly_period_windows,
    recent_period_windows,
    resolve_live_gee_period,
)


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


class FakeBatchLiveGeeAdapter(FakeLiveGeeAdapter):
    def query_adm1_values(
        self,
        regions: tuple[object, ...],
        period_start: str,
        period_end: str,
    ) -> dict[str, dict[str, float]]:
        del period_start, period_end
        return {
            str(getattr(region, "id")): {"ndvi": 0.22, "rainfall_mm": 8.5, "lst_c": 32.4}
            for region in regions
        }


class FakeTrendBatchLiveGeeAdapter(FakeLiveGeeAdapter):
    def __init__(self) -> None:
        self.calls = 0

    def query_time_series_values(
        self,
        regions: tuple[object, ...],
        windows: tuple[tuple[str, str], ...],
    ) -> dict[tuple[str, str, str], dict[str, float]]:
        self.calls += 1
        return {
            (str(getattr(region, "id")), start, end): {
                "ndvi": 0.2 + index / 100,
                "rainfall_mm": 10.0 + index,
                "lst_c": 30.0 + index / 10,
            }
            for index, (start, end) in enumerate(windows)
            for region in regions
        }


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

    def test_builds_live_payloads_for_multiple_regions_in_order(self) -> None:
        payloads = build_live_gee_payloads_for_regions(
            ("som", "ken"),
            "2026-07-01T00:00:00Z",
            "2026-07-15T00:00:00Z",
            adapter=FakeLiveGeeAdapter(),  # type: ignore[arg-type]
        )

        risks = [payload for payload in payloads if payload.get("payload_type") == "risk_snapshot"]
        self.assertEqual([risk["region_id"] for risk in risks], ["som", "ken"])
        self.assertEqual(len(payloads), 10)
        self.assertFalse(any(payload.get("is_simulated") is True for payload in payloads))

    def test_dashboard_live_region_ids_include_enabled_pilot_regions(self) -> None:
        with patch.dict("os.environ", {"MWANGAZA_ENABLED_COUNTRIES": "SOM,KEN"}):
            region_ids = dashboard_live_region_ids("som")

        self.assertEqual(region_ids[0], "som")
        self.assertIn("ken", region_ids)
        self.assertIn("somalia-pilot", region_ids)
        self.assertIn("northern-kenya-pilot", region_ids)
        self.assertNotIn("eth", region_ids)

    def test_default_adm1_scope_covers_all_enabled_igad_countries(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            region_ids = dashboard_live_adm1_region_ids()

        self.assertEqual(len(region_ids), 121)
        self.assertIn("adm1-so-hi", region_ids)
        self.assertIn("adm1-ke-43", region_ids)
        self.assertIn("adm1-et-aa", region_ids)
        self.assertIn("adm1-dj-ar", region_ids)

    def test_adm1_scope_can_be_disabled_or_restricted_by_country(self) -> None:
        with patch.dict("os.environ", {"MWANGAZA_GEE_ADM1_ENABLED": "false"}, clear=True):
            self.assertEqual(dashboard_live_adm1_region_ids(), ())
        with patch.dict("os.environ", {"MWANGAZA_GEE_ADM1_COUNTRIES": "ETH"}, clear=True):
            region_ids = dashboard_live_adm1_region_ids()

        self.assertEqual(len(region_ids), 11)
        self.assertTrue(all(region_id.startswith("adm1-et-") for region_id in region_ids))

    def test_adm1_scope_follows_enabled_countries_when_not_explicitly_restricted(self) -> None:
        with patch.dict("os.environ", {"MWANGAZA_ENABLED_COUNTRIES": "SOM,DJI"}, clear=True):
            region_ids = dashboard_live_adm1_region_ids()

        self.assertEqual(len(region_ids), 24)
        self.assertTrue(all(region_id.startswith(("adm1-so-", "adm1-dj-")) for region_id in region_ids))

    def test_adm1_payload_keeps_exact_boundary_provenance(self) -> None:
        payloads = build_live_gee_payloads(
            "adm1-so-hi",
            "2026-07-01T00:00:00Z",
            "2026-07-15T00:00:00Z",
            adapter=FakeLiveGeeAdapter(),  # type: ignore[arg-type]
        )
        risk = next(payload for payload in payloads if payload.get("payload_type") == "risk_snapshot")

        self.assertEqual(risk["metadata"]["boundary_iso"], "SO-HI")
        self.assertTrue(risk["metadata"]["boundary_id"])
        self.assertEqual(risk["metadata"]["parent_region_id"], "som")

    def test_adm1_failures_are_isolated_per_boundary(self) -> None:
        def build(region_id: str, *_args: object, **_kwargs: object) -> list[dict[str, object]]:
            if region_id == "adm1-so-hi":
                raise RuntimeError("simulated unit failure")
            return [{"region_id": region_id}]

        with patch("mwangaza.services.live_gee_dashboard.build_live_gee_payloads", side_effect=build):
            payloads = build_live_gee_payloads_for_adm1_regions(
                ("adm1-so-hi", "adm1-so-bn"),
                "2026-07-01T00:00:00Z",
                "2026-07-15T00:00:00Z",
                adapter=FakeLiveGeeAdapter(),  # type: ignore[arg-type]
            )

        self.assertEqual(payloads, [{"region_id": "adm1-so-bn"}])

    def test_adm1_batch_builds_all_contracts_from_one_result_set(self) -> None:
        payloads = build_live_gee_payloads_for_adm1_regions(
            ("adm1-so-hi", "adm1-so-bn"),
            "2026-07-01T00:00:00Z",
            "2026-07-15T00:00:00Z",
            adapter=FakeBatchLiveGeeAdapter(),  # type: ignore[arg-type]
        )

        risks = [payload for payload in payloads if payload.get("payload_type") == "risk_snapshot"]
        self.assertEqual({risk["region_id"] for risk in risks}, {"adm1-so-hi", "adm1-so-bn"})
        self.assertTrue(all(risk["metadata"]["aggregation_mode"] == "reduceRegions" for risk in risks))
        self.assertEqual(len(payloads), 10)
        ndvi_rows = [payload for payload in payloads if payload.get("indicator") == "ndvi"]
        self.assertTrue(all(row["metadata"]["summary_qa_values"] == [0, 1] for row in ndvi_rows))

    def test_empty_adm1_scope_does_not_query_the_adapter(self) -> None:
        adapter = FakeBatchLiveGeeAdapter()
        with patch.object(adapter, "query_adm1_values") as query:
            payloads = build_live_gee_payloads_for_adm1_regions(
                (),
                "2026-07-01T00:00:00Z",
                "2026-07-15T00:00:00Z",
                adapter=adapter,  # type: ignore[arg-type]
            )

        self.assertEqual(payloads, [])
        query.assert_not_called()

    def test_country_and_pilot_payloads_share_one_batch_result_set(self) -> None:
        payloads = build_live_gee_payloads_for_regions(
            ("som", "somalia-pilot"),
            "2026-07-01T00:00:00Z",
            "2026-07-15T00:00:00Z",
            adapter=FakeBatchLiveGeeAdapter(),  # type: ignore[arg-type]
        )

        risks = [payload for payload in payloads if payload.get("payload_type") == "risk_snapshot"]
        self.assertEqual([risk["region_id"] for risk in risks], ["som", "somalia-pilot"])
        self.assertTrue(all(risk["metadata"]["aggregation_mode"] == "reduceRegions" for risk in risks))

    def test_builds_live_payloads_for_pilot_regions(self) -> None:
        payloads = build_live_gee_payloads_for_regions(
            ("som", "somalia-pilot"),
            "2026-07-01T00:00:00Z",
            "2026-07-15T00:00:00Z",
            adapter=FakeLiveGeeAdapter(),  # type: ignore[arg-type]
        )

        risks = [payload for payload in payloads if payload.get("payload_type") == "risk_snapshot"]
        self.assertEqual([risk["region_id"] for risk in risks], ["som", "somalia-pilot"])
        self.assertEqual(len(payloads), 10)

    def test_recent_period_windows_are_limited_and_descending(self) -> None:
        windows = recent_period_windows("2026-07-15T00:00:00Z", point_count=3)

        self.assertEqual(
            windows,
            (
                ("2026-06-16T00:00:00Z", "2026-07-15T00:00:00Z"),
                ("2026-05-16T00:00:00Z", "2026-06-15T00:00:00Z"),
                ("2026-04-16T00:00:00Z", "2026-05-15T00:00:00Z"),
            ),
        )
        self.assertEqual(len(recent_period_windows("2026-07-15T00:00:00Z", point_count=99)), 24)
        self.assertEqual(monthly_period_windows("2026-07-31T00:00:00Z", month_count=2)[1][1], "2026-06-30T00:00:00Z")

    def test_builds_bounded_seasonally_comparable_history_windows(self) -> None:
        self.assertEqual(
            comparable_period_windows("2026-07-15T00:00:00Z", years=2),
            (
                ("2025-07-01T00:00:00Z", "2025-07-15T00:00:00Z"),
                ("2024-07-01T00:00:00Z", "2024-07-15T00:00:00Z"),
            ),
        )

    def test_builds_recent_live_payloads_for_series_points(self) -> None:
        payloads = build_live_gee_payloads_for_recent_periods(
            ("som",),
            "2026-07-15T00:00:00Z",
            adapter=FakeLiveGeeAdapter(),  # type: ignore[arg-type]
            point_count=2,
        )

        self.assertEqual(len(payloads), 6)
        self.assertTrue(all(payload["metadata"]["trend_series"] for payload in payloads))
        self.assertEqual(
            sorted({payload["period_end"] for payload in payloads}),
            ["2026-06-15T00:00:00Z", "2026-07-15T00:00:00Z"],
        )

    def test_builds_twenty_four_months_in_one_remote_batch(self) -> None:
        adapter = FakeTrendBatchLiveGeeAdapter()

        payloads = build_live_gee_trend_payloads_for_regions(
            ("som",),
            "2026-07-15T00:00:00Z",
            adapter=adapter,  # type: ignore[arg-type]
            month_count=24,
        )

        self.assertEqual(adapter.calls, 1)
        self.assertEqual(len(payloads), 72)
        self.assertEqual(len({payload["period_end"] for payload in payloads}), 24)
        self.assertTrue(all(payload["metadata"]["aggregation_period"] == "monthly" for payload in payloads))


if __name__ == "__main__":
    unittest.main()
