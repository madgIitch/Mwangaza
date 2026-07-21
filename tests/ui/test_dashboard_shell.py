from __future__ import annotations

import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mwangaza.alerts.repository import AlertRepository
from mwangaza.actions import recommend_actions
from mwangaza.contracts import RiskSnapshot
from mwangaza.services.dashboard_shell import load_dashboard_shell_data
from mwangaza.ui.dashboard import SAFE_ERROR_MESSAGE, build_dashboard_shell_html, render_dashboard


class FakeStreamlit:
    def __init__(self) -> None:
        self.page_config: dict[str, object] | None = None
        self.markdown_calls: list[tuple[str, bool]] = []
        self.html_calls: list[str] = []

    def set_page_config(self, **kwargs: object) -> None:
        self.page_config = kwargs

    def markdown(self, body: str, *, unsafe_allow_html: bool = False) -> None:
        self.markdown_calls.append((body, unsafe_allow_html))

    def html(self, body: str) -> None:
        self.html_calls.append(body)


class FakeComponentsV1:
    def __init__(self) -> None:
        self.html_calls: list[tuple[str, int, bool]] = []

    def html(self, body: str, *, height: int, scrolling: bool) -> None:
        self.html_calls.append((body, height, scrolling))


class FakeComponents:
    def __init__(self) -> None:
        self.v1 = FakeComponentsV1()


class FakeStreamlitWithComponents(FakeStreamlit):
    def __init__(self) -> None:
        super().__init__()
        self.components = FakeComponents()


class DashboardShellTests(unittest.TestCase):
    def test_home_shell_shows_brand_update_and_data_status(self) -> None:
        html = build_dashboard_shell_html(load_dashboard_shell_data("demo"))

        self.assertIn("Mwangaza", html)
        self.assertIn("Bringing Light to Early Action", html)
        self.assertIn("Last update:", html)
        self.assertIn("Data is current", html)

    def test_shell_uses_mockup_inspired_operational_layout(self) -> None:
        html = build_dashboard_shell_html(load_dashboard_shell_data("demo"))

        self.assertIn('class="status-band"', html)
        self.assertIn('class="sidebar"', html)
        self.assertIn('class="workspace"', html)
        self.assertIn('class="side-column"', html)
        self.assertIn('class="footer"', html)
        self.assertIn("IGAD regional drought operations", html)

    def test_navigation_contains_required_sections(self) -> None:
        html = build_dashboard_shell_html(load_dashboard_shell_data("demo"))

        for label in ("Overview", "Region", "Alerts", "Reports", "About"):
            self.assertIn(f">{label}<", html)
        self.assertIn('type="button" data-nav-target="region"', html)
        self.assertIn("scrollIntoView", html)
        self.assertNotIn('href="#region"', html)
        self.assertNotIn('href="#overview"', html)

    def test_data_modes_are_visually_distinct(self) -> None:
        html = build_dashboard_shell_html(load_dashboard_shell_data("cache"))

        self.assertIn('data-mode="live"', html)
        self.assertIn(">Live data<", html)
        self.assertIn('data-mode="cache"', html)
        self.assertIn(">Cache data<", html)
        self.assertIn('data-mode="demo"', html)
        self.assertIn(">Demo data<", html)
        self.assertIn('mode-chip is-active" data-mode="cache"', html)

    def test_materialized_cache_feeds_dashboard_before_demo_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp) / "cache"
            cache_dir.mkdir()
            risk = _risk_snapshot(is_simulated=False).to_dict()
            ndvi = {
                "payload_type": "indicator_observation",
                "schema_version": "mwangaza.contracts.v1",
                "region_id": "ken",
                "indicator": "ndvi",
                "period_start": "2026-07-01T00:00:00Z",
                "period_end": "2026-07-08T00:00:00Z",
                "value": 0.31,
                "unit": "index",
                "source": "MODIS/061/MOD13Q1",
                "quality_flag": "ok",
                "is_simulated": False,
                "metadata": {"updated_at": "2026-07-09T00:00:00Z"},
            }
            (cache_dir / "risk.json").write_text(json.dumps({"payload": risk}), encoding="utf-8")
            (cache_dir / "ndvi.json").write_text(json.dumps({"payload": ndvi}), encoding="utf-8")

            data = load_dashboard_shell_data(cache_dir=cache_dir, data_dir=Path(tmp))

        self.assertEqual(data.data_status.mode, "cache")
        self.assertEqual(data.data_status.source, "Materialized observed data")
        self.assertEqual(data.selected_region, "KEN")
        self.assertEqual(data.risk_map.selected_region_id, "ken")
        self.assertEqual(
            next(region for region in data.risk_map.regions if region.region_id == "ken").color_level,
            "red",
        )
        self.assertIn("0.31", {metric.value for metric in data.metrics})
        self.assertIn("Activate urgent coordination review", data.recommendations[0])

    def test_default_loader_uses_live_gee_payloads_before_cache_or_demo(self) -> None:
        with patch(
            "mwangaza.services.dashboard_shell.load_live_gee_dashboard_payloads",
            return_value=[_risk_snapshot(is_simulated=False).to_dict()],
        ):
            data = load_dashboard_shell_data()

        self.assertEqual(data.data_status.mode, "live")
        self.assertEqual(data.data_status.source, "Google Earth Engine live query")
        self.assertEqual(data.data_status.message, "Using live Google Earth Engine data")
        self.assertEqual(data.selected_region, "KEN")

    def test_default_loader_keeps_preferred_live_region_with_multiple_risks(self) -> None:
        with (
            patch.dict(os.environ, {"MWANGAZA_DASHBOARD_REGION_ID": "som"}),
            patch(
                "mwangaza.services.dashboard_shell.load_live_gee_dashboard_payloads",
                return_value=[
                    _json_payload(
                        _risk_snapshot(region_id="som", risk_level="watch", score=49.8, is_simulated=False)
                    ),
                    _json_payload(
                        _risk_snapshot(region_id="ken", risk_level="emergency", score=82.0, is_simulated=False)
                    ),
                    _json_payload(
                        _risk_snapshot(
                            region_id="somalia-pilot",
                            risk_level="warning",
                            score=64.0,
                            is_simulated=False,
                        )
                    ),
                ],
            ),
        ):
            data = load_dashboard_shell_data()

        self.assertEqual(data.selected_region, "SOM")
        self.assertEqual(data.risk_map.selected_region_id, "som")
        by_region = {region.region_id: region for region in data.risk_map.regions}
        self.assertEqual(by_region["som"].color_level, "yellow")
        self.assertEqual(by_region["ken"].color_level, "red")
        self.assertIn("49.8", {metric.value for metric in data.metrics})
        self.assertEqual([profile.region_id for profile in data.region_profiles], ["som", "ken"])
        somalia = next(profile for profile in data.region_profiles if profile.region_id == "som")
        self.assertEqual(somalia.pilot_units[0].pilot_id, "somalia-pilot")
        self.assertEqual(somalia.pilot_units[0].score, 64.0)
        self.assertEqual(somalia.pilot_units[0].risk_level, "warning")
        kenya = next(profile for profile in data.region_profiles if profile.region_id == "ken")
        self.assertEqual(kenya.alerts[0].region, "KEN")
        self.assertIn("Activate urgent coordination review", kenya.recommendations[0])

    def test_live_profile_exposes_conclusive_adm1_observations(self) -> None:
        adm1_risk = _json_payload(
            _risk_snapshot(region_id="adm1-so-hi", risk_level="warning", score=63.0, is_simulated=False)
        )
        payloads = [
            _json_payload(_risk_snapshot(region_id="som", risk_level="watch", score=49.8, is_simulated=False)),
            adm1_risk,
            _signal_payload(region_id="adm1-so-hi", indicator="ndvi", period_end="2026-07-08T00:00:00Z", value=0.18, baseline=0.2, quality_flag="ok"),
            _signal_payload(region_id="adm1-so-hi", indicator="rainfall_mm", period_end="2026-07-08T00:00:00Z", value=3.1, baseline=7.0, quality_flag="ok"),
            _signal_payload(region_id="adm1-so-hi", indicator="lst_c", period_end="2026-07-08T00:00:00Z", value=31.2, baseline=29.0, quality_flag="ok"),
        ]
        with patch("mwangaza.services.dashboard_shell.load_live_gee_dashboard_payloads", return_value=payloads):
            data = load_dashboard_shell_data()

        somalia = next(profile for profile in data.region_profiles if profile.region_id == "som")
        self.assertEqual(len(somalia.administrative_units), 1)
        unit = somalia.administrative_units[0]
        self.assertEqual(unit.boundary_iso, "SO-HI")
        self.assertEqual(unit.score, 63.0)
        self.assertEqual(unit.risk_level, "warning")
        self.assertEqual(unit.ndvi, 0.18)
        self.assertEqual(unit.rainfall_mm, 3.1)
        self.assertEqual(len(unit.contributions), 3)
        self.assertAlmostEqual(
            sum(item["weighted_contribution"] for item in unit.contributions),
            unit.score or 0,
            places=2,
        )
        self.assertAlmostEqual(sum(item["share_of_composite"] for item in unit.contributions), 1.0)

    def test_temporal_periods_default_to_latest_available_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp) / "cache"
            cache_dir.mkdir()
            older = _risk_snapshot(
                region_id="som",
                risk_level="watch",
                score=41.0,
                period_start="2026-06-01T00:00:00Z",
                period_end="2026-06-15T00:00:00Z",
            )
            latest = _risk_snapshot(
                region_id="som",
                risk_level="warning",
                score=68.0,
                period_start="2026-07-01T00:00:00Z",
                period_end="2026-07-15T00:00:00Z",
            )
            (cache_dir / "older.json").write_text(json.dumps({"payload": older.to_dict()}), encoding="utf-8")
            (cache_dir / "latest.json").write_text(json.dumps({"payload": latest.to_dict()}), encoding="utf-8")

            data = load_dashboard_shell_data(cache_dir=cache_dir, data_dir=Path(tmp))

        self.assertEqual([period.label for period in data.temporal_periods], ["2026-07-15", "2026-06-15"])
        self.assertEqual(data.temporal_periods[0].status, "partial")
        self.assertEqual(data.data_status.last_updated, "2026-07-15 00:00:00 UTC")
        self.assertIn("68", {metric.value for metric in data.metrics})

    def test_temporal_selector_embeds_loaded_periods_without_recalculation_hooks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp) / "cache"
            cache_dir.mkdir()
            for name, score, end in (
                ("older", 41.0, "2026-06-15T00:00:00Z"),
                ("latest", 68.0, "2026-07-15T00:00:00Z"),
            ):
                risk = _risk_snapshot(
                    region_id="som",
                    risk_level="watch",
                    score=score,
                    period_start=end.replace("15T", "01T"),
                    period_end=end,
                )
                (cache_dir / f"{name}.json").write_text(json.dumps({"payload": risk.to_dict()}), encoding="utf-8")

            html = build_dashboard_shell_html(load_dashboard_shell_data(cache_dir=cache_dir, data_dir=Path(tmp)))

        self.assertIn("data-period-selector", html)
        self.assertIn("data-temporal-periods", html)
        self.assertIn("2026-07-15", html)
        self.assertIn("2026-06-15", html)
        self.assertIn('data-period-status="partial"', html)
        self.assertIn("function renderPeriod", html)
        self.assertIn("mapSlot.innerHTML", html)
        self.assertNotIn("load_live_gee_dashboard_payloads", html)

    def test_indicator_trends_render_units_sources_baseline_and_quality_details(self) -> None:
        html = build_dashboard_shell_html(load_dashboard_shell_data("demo"))

        self.assertIn("Indicator Trends", html)
        self.assertIn("trend-chart", html)
        self.assertIn("trend-observed", html)
        self.assertIn("trend-baseline", html)
        self.assertIn("Latest quality:", html)
        self.assertIn("Latest anomaly:", html)
        self.assertIn("MODIS/061/MOD13Q1", html)
        self.assertIn("UCSB-CHG/CHIRPS/DAILY", html)

    def test_indicator_trends_are_derived_from_loaded_payload_series_with_gaps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp) / "cache"
            cache_dir.mkdir()
            payloads = [
                _signal_payload(
                    region_id="som",
                    indicator="ndvi",
                    period_end="2026-06-15T00:00:00Z",
                    value=0.25,
                    baseline=0.3,
                    quality_flag="ok",
                ),
                _signal_payload(
                    region_id="som",
                    indicator="ndvi",
                    period_end="2026-06-30T00:00:00Z",
                    value=None,
                    baseline=0.28,
                    quality_flag="no_data",
                ),
                _signal_payload(
                    region_id="som",
                    indicator="ndvi",
                    period_end="2026-07-15T00:00:00Z",
                    value=0.18,
                    baseline=0.27,
                    quality_flag="ok",
                ),
                _risk_snapshot(
                    region_id="som",
                    risk_level="watch",
                    score=44.0,
                    period_start="2026-07-01T00:00:00Z",
                    period_end="2026-07-15T00:00:00Z",
                ).to_dict(),
            ]
            (cache_dir / "payloads.json").write_text(json.dumps({"payload": payloads}), encoding="utf-8")

            data = load_dashboard_shell_data(cache_dir=cache_dir, data_dir=Path(tmp))
            html = build_dashboard_shell_html(data)

        ndvi = next(series for series in data.trends if series.indicator == "ndvi")
        self.assertEqual(len(ndvi.points), 3)
        self.assertTrue(ndvi.points[1].is_gap)
        self.assertEqual(ndvi.points[-1].anomaly_value, -0.09000000000000002)
        self.assertIn("trend-gap", html)
        self.assertIn("quality=no_data", html)
        self.assertIn("Historical baseline when available", html)

    def test_monthly_trends_use_series_mean_without_creating_dashboard_periods(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp) / "cache"
            cache_dir.mkdir()
            monthly = []
            for period_end, value in (
                ("2026-05-15T00:00:00Z", 0.1),
                ("2026-06-15T00:00:00Z", 0.2),
                ("2026-07-15T00:00:00Z", 0.3),
            ):
                signal = _signal_payload(
                    region_id="som",
                    indicator="ndvi",
                    period_end=period_end,
                    value=value,
                    baseline=0.0,
                    quality_flag="ok",
                )
                signal["metadata"] = {
                    "updated_at": period_end,
                    "trend_series": True,
                    "aggregation_period": "monthly",
                }
                monthly.append(signal)
            payloads = [
                *monthly,
                _risk_snapshot(
                    region_id="som",
                    risk_level="watch",
                    score=44.0,
                    period_start="2026-07-01T00:00:00Z",
                    period_end="2026-07-15T00:00:00Z",
                ).to_dict(),
            ]
            (cache_dir / "payloads.json").write_text(json.dumps({"payload": payloads}), encoding="utf-8")

            data = load_dashboard_shell_data(cache_dir=cache_dir, data_dir=Path(tmp))

        ndvi = next(series for series in data.trends if series.indicator == "ndvi")
        self.assertEqual(len(ndvi.points), 3)
        self.assertAlmostEqual(ndvi.points[0].baseline_value or 0, 0.2)
        self.assertAlmostEqual(ndvi.points[0].anomaly_value or 0, -0.1)
        self.assertIn("Mean of 3 available monthly points", ndvi.baseline_label)
        self.assertEqual(len(data.temporal_periods), 1)

    def test_historical_comparison_uses_same_window_excludes_insufficient_data_and_ranks_dryness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp) / "cache"
            cache_dir.mkdir()
            payloads = [
                _signal_payload(
                    region_id="som",
                    indicator="rainfall_mm",
                    period_end="2026-07-15T00:00:00Z",
                    value=18.0,
                    baseline=30.0,
                    quality_flag="ok",
                ),
                _signal_payload(
                    region_id="som",
                    indicator="rainfall_mm",
                    period_end="2025-07-15T00:00:00Z",
                    value=24.0,
                    baseline=30.0,
                    quality_flag="ok",
                ),
                _signal_payload(
                    region_id="som",
                    indicator="rainfall_mm",
                    period_end="2024-07-15T00:00:00Z",
                    value=16.0,
                    baseline=30.0,
                    quality_flag="ok",
                ),
                _signal_payload(
                    region_id="som",
                    indicator="rainfall_mm",
                    period_end="2023-07-15T00:00:00Z",
                    value=12.0,
                    baseline=30.0,
                    quality_flag="insufficient_history",
                ),
                _signal_payload(
                    region_id="som",
                    indicator="rainfall_mm",
                    period_end="2025-06-30T00:00:00Z",
                    value=4.0,
                    baseline=20.0,
                    quality_flag="ok",
                ),
            ]
            (cache_dir / "payloads.json").write_text(json.dumps({"payload": payloads}), encoding="utf-8")

            data = load_dashboard_shell_data(cache_dir=cache_dir, data_dir=Path(tmp))

        comparison = data.historical_comparison
        self.assertIsNotNone(comparison)
        assert comparison is not None
        self.assertEqual(comparison.season_window, "07-01 to 07-15")
        self.assertEqual([period.label for period in comparison.periods], ["2025-07-15", "2024-07-15"])
        self.assertNotIn("2023-07-15T00:00:00Z", {period.period_key for period in comparison.periods})
        self.assertEqual(comparison.ranking, "Current rainfall ranks #2 of 3 comparable periods; lower rainfall is drier.")
        self.assertIn("satellite observations only", comparison.narrative)
        self.assertNotIn("caused", comparison.narrative.lower())
        self.assertNotIn("affected people", comparison.narrative.lower())

    def test_historical_comparison_ui_shows_versions_and_limits_selection_to_three_periods(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp) / "cache"
            cache_dir.mkdir()
            payloads = [
                _signal_payload(
                    region_id="som",
                    indicator="rainfall_mm",
                    period_end=f"{year}-07-15T00:00:00Z",
                    value=value,
                    baseline=30.0,
                    quality_flag="ok",
                )
                for year, value in ((2026, 18.0), (2025, 24.0), (2024, 16.0), (2023, 28.0), (2022, 31.0))
            ]
            (cache_dir / "payloads.json").write_text(json.dumps({"payload": payloads}), encoding="utf-8")

            html = build_dashboard_shell_html(load_dashboard_shell_data(cache_dir=cache_dir, data_dir=Path(tmp)))

        self.assertIn("Historical Comparison", html)
        self.assertIn("Season window: 07-01 to 07-15", html)
        self.assertIn("Version: MODIS/061/MOD13Q1", html)
        self.assertIn('data-historical-period="2025-07-15T00:00:00Z" checked', html)
        self.assertIn('data-historical-period="2022-07-15T00:00:00Z" disabled', html)
        self.assertIn("checked.length >= 3", html)
        self.assertIn("Current rainfall ranks #2 of 5 comparable periods", html)
        self.assertIn("does not infer impacts", html)

    def test_exposure_estimate_uses_potentially_exposed_metadata_and_demo_label(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp) / "cache"
            cache_dir.mkdir()
            payloads = [
                _risk_snapshot(
                    region_id="som",
                    risk_level="warning",
                    score=66.0,
                    period_start="2026-07-01T00:00:00Z",
                    period_end="2026-07-15T00:00:00Z",
                ).to_dict(),
                _exposure_payload(
                    region_id="som",
                    population=1180000.0,
                    display_range="1.1M-1.3M",
                    warnings=["mixed source years: population 2024, livestock 2021"],
                ),
            ]
            (cache_dir / "payloads.json").write_text(json.dumps({"payload": payloads}), encoding="utf-8")

            data = load_dashboard_shell_data(cache_dir=cache_dir, data_dir=Path(tmp))
            html = build_dashboard_shell_html(data)

        exposure = next(metric for metric in data.metrics if metric.label == "potentially_exposed")
        self.assertEqual(exposure.value, "1.1M-1.3M")
        self.assertIn("source demo-population-grid", exposure.detail)
        self.assertIn("year 2024", exposure.detail)
        self.assertIn("1 km", exposure.detail)
        self.assertIn("regional_fixture_sum", exposure.detail)
        self.assertIn("quality ok", exposure.detail)
        self.assertIn("demo/synthetic", exposure.detail)
        self.assertIn("warning: mixed source years", exposure.detail)
        self.assertIn("potentially_exposed", html)
        self.assertIn("1.1M-1.3M", html)
        self.assertIn("demo/synthetic", html)
        self.assertNotIn("Exposed population", html)

    def test_invalid_exposure_dataset_is_hidden_without_invented_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp) / "cache"
            cache_dir.mkdir()
            exposure = _exposure_payload(region_id="som", population=1180000.0)
            exposure["source"] = "C:\\Users\\secret\\population.csv"
            payloads = [
                _risk_snapshot(
                    region_id="som",
                    risk_level="watch",
                    score=44.0,
                    period_start="2026-07-01T00:00:00Z",
                    period_end="2026-07-15T00:00:00Z",
                ).to_dict(),
                exposure,
            ]
            (cache_dir / "payloads.json").write_text(json.dumps({"payload": payloads}), encoding="utf-8")

            data = load_dashboard_shell_data(cache_dir=cache_dir, data_dir=Path(tmp))

        exposure_metric = next(metric for metric in data.metrics if metric.label == "potentially_exposed")
        self.assertEqual(exposure_metric.value, "No data")
        self.assertEqual(exposure_metric.detail, "No valid exposure dataset")

    def test_dashboard_debug_flag_logs_loader_decision(self) -> None:
        with (
            patch.dict(os.environ, {"MWANGAZA_DASHBOARD_DEBUG": "1"}),
            patch(
                "mwangaza.services.dashboard_shell.load_live_gee_dashboard_payloads",
                return_value=[_risk_snapshot(is_simulated=False).to_dict()],
            ),
            patch("builtins.print") as fake_print,
        ):
            load_dashboard_shell_data()

        lines = [call.args[0] for call in fake_print.call_args_list]
        self.assertIn("[mwangaza.dashboard] trying live GEE dashboard payloads", lines)
        self.assertIn(
            "[mwangaza.dashboard] loader selected mode=live source=Google Earth Engine live query",
            lines,
        )

    def test_dashboard_renders_regional_risk_map_with_legend_and_tooltips(self) -> None:
        html = build_dashboard_shell_html(load_dashboard_shell_data("demo"))

        self.assertIn('class="regional-risk-map"', html)
        self.assertIn('aria-label="IGAD regional risk map"', html)
        for level in ("green", "yellow", "orange", "red", "unknown"):
            self.assertIn(f'data-risk-level="{level}"', html)
        self.assertIn("Somalia | score: 82 | level: red", html)
        self.assertIn("risk-region risk-red is-selected", html)

    def test_regional_risk_map_has_client_side_selection_interaction(self) -> None:
        html = build_dashboard_shell_html(load_dashboard_shell_data("demo"))

        self.assertIn('data-region-name="Somalia"', html)
        self.assertIn('data-period="2026-07-01 to 2026-07-15"', html)
        self.assertIn("addEventListener(\"click\"", html)
        self.assertIn("addEventListener(\"keydown\"", html)
        self.assertIn('role", "button"', html)
        self.assertIn("data-region-readout-name", html)
        self.assertIn('class="regional-risk-map" data-selected-region="som"', html)
        self.assertIn("data-selected-region-label", html)
        self.assertIn('querySelector("[data-selected-region-label]")', html)
        self.assertNotIn('querySelector("[data-selected-region]")', html)
        self.assertIn("data-region-selector", html)
        self.assertIn("data-region-detail", html)
        self.assertIn("data-region-metrics", html)
        self.assertIn("URLSearchParams(window.location.search)", html)

    def test_region_drilldown_profiles_are_embedded_without_nested_rendering(self) -> None:
        html = build_dashboard_shell_html(load_dashboard_shell_data("demo"))

        self.assertEqual(html.count('class="mwa-shell"'), 1)
        self.assertEqual(html.count('class="regional-risk-map"'), 1)
        self.assertNotIn("<iframe", html.lower())
        match = re.search(
            r'<script type="application/json" data-region-profiles="[^"]+">(.*?)</script>',
            html,
            re.S,
        )
        self.assertIsNotNone(match)
        profiles = json.loads(match.group(1))
        self.assertIn("som", profiles)
        self.assertIn("ken", profiles)
        self.assertEqual(profiles["ken"]["metrics"][0]["label"], "NDVI anomaly")
        self.assertEqual(profiles["som"]["alerts"][0]["region"], "Somalia")
        self.assertEqual(profiles["som"]["pilot_units"][0]["pilot_id"], "somalia-pilot")
        self.assertEqual(profiles["ken"]["pilot_units"][0]["pilot_id"], "northern-kenya-pilot")
        self.assertEqual(profiles["eth"]["pilot_units"], [])

    def test_interaction_script_is_scoped_to_current_shell_instance(self) -> None:
        html = build_dashboard_shell_html(load_dashboard_shell_data("demo"))

        self.assertIn('data-shell-id="mwa-', html)
        self.assertIn('data-region-profiles="mwa-', html)
        self.assertIn('data-temporal-periods="mwa-', html)
        self.assertIn("currentScript?.previousElementSibling", html)
        self.assertIn('document.querySelectorAll(".mwa-shell")', html)
        self.assertNotIn('document.querySelector(".mwa-shell")', html)
        self.assertNotIn('document.querySelector("[data-region-profiles]")', html)
        self.assertNotIn('document.querySelector("[data-temporal-periods]")', html)

    def test_subnational_pilot_panel_labels_non_pilot_regions_as_national_only(self) -> None:
        html = build_dashboard_shell_html(load_dashboard_shell_data("demo"))

        self.assertIn("Subnational pilot", html)
        self.assertIn("Somalia Pilot Area", html)
        self.assertIn("Northern Kenya Pilot Area", html)
        self.assertIn("IGAD coverage remains national here.", html)
        self.assertIn("data-pilot-id", html)

    def test_materialized_cache_accepts_powershell_utf8_bom(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp) / "cache"
            cache_dir.mkdir()
            body = json.dumps({"payload": _risk_snapshot(is_simulated=False).to_dict()})
            (cache_dir / "risk.json").write_text(f"\ufeff{body}", encoding="utf-8")

            data = load_dashboard_shell_data(cache_dir=cache_dir, data_dir=Path(tmp))

        self.assertEqual(data.data_status.mode, "cache")
        self.assertEqual(data.selected_region, "KEN")

    def test_alert_sqlite_overrides_demo_alert_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp) / "cache"
            cache_dir.mkdir()
            risk = _risk_snapshot(risk_level="warning", score=66.0, is_simulated=False)
            (cache_dir / "risk.json").write_text(
                json.dumps({"payload": risk.to_dict()}),
                encoding="utf-8",
            )
            repo = AlertRepository(Path(tmp) / "alerts.sqlite")
            try:
                repo.upsert_alert(risk, recommend_actions(risk))
            finally:
                repo.close()

            data = load_dashboard_shell_data(
                cache_dir=cache_dir,
                data_dir=Path(tmp),
                alert_db_path=Path(tmp) / "alerts.sqlite",
            )

        self.assertEqual(len(data.alerts), 1)
        self.assertEqual(data.alerts[0].region, "KEN")
        self.assertEqual(data.alerts[0].severity, "warning")
        self.assertIn("66", data.alerts[0].title)
        self.assertEqual(data.alerts[0].status, "active")
        self.assertEqual(data.alerts[0].region_type, "country")
        self.assertEqual(data.alerts[0].priority_rank, 1)
        self.assertEqual(data.alerts[0].recommended_action, data.alerts[0].action)
        self.assertIn(("Model Version", "composite-risk-v1"), data.alerts[0].evidence)

    def test_active_alerts_hide_resolved_and_sort_by_severity_quality_date_score(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp) / "cache"
            cache_dir.mkdir()
            snapshots = (
                _risk_snapshot(
                    region_id="som",
                    risk_level="warning",
                    score=70.0,
                    period_start="2026-07-01T00:00:00Z",
                    period_end="2026-07-15T00:00:00Z",
                ),
                _risk_snapshot(
                    region_id="ken",
                    risk_level="emergency",
                    score=82.0,
                    period_start="2026-07-01T00:00:00Z",
                    period_end="2026-07-08T00:00:00Z",
                ),
                _risk_snapshot(
                    region_id="eth",
                    risk_level="watch",
                    score=49.0,
                    period_start="2026-07-01T00:00:00Z",
                    period_end="2026-07-16T00:00:00Z",
                ),
            )
            (cache_dir / "risk.json").write_text(
                json.dumps({"payload": [snapshot.to_dict() for snapshot in snapshots]}),
                encoding="utf-8",
            )
            repo = AlertRepository(Path(tmp) / "alerts.sqlite")
            try:
                resolved = repo.upsert_alert(snapshots[0], recommend_actions(snapshots[0]))
                repo.resolve_alert(resolved.alert_id, reason="superseded")
                repo.upsert_alert(snapshots[1], recommend_actions(snapshots[1]))
                repo.upsert_alert(snapshots[2], recommend_actions(snapshots[2]))
            finally:
                repo.close()

            data = load_dashboard_shell_data(
                cache_dir=cache_dir,
                data_dir=Path(tmp),
                alert_db_path=Path(tmp) / "alerts.sqlite",
            )

        self.assertEqual([alert.region_id for alert in data.alerts], ["ken", "eth"])
        self.assertEqual([alert.priority_rank for alert in data.alerts], [1, 2])
        self.assertTrue(all(alert.status == "active" for alert in data.alerts))
        self.assertNotIn("som", {alert.region_id for alert in data.alerts})

    def test_active_alert_panel_renders_filters_evidence_actions_and_unknown_separate_from_green(self) -> None:
        html = build_dashboard_shell_html(load_dashboard_shell_data("demo"))

        self.assertIn('data-alert-filter="severity"', html)
        self.assertIn('data-alert-filter="region"', html)
        self.assertIn('data-alert-filter="type"', html)
        self.assertIn("function applyAlertFilters", html)
        self.assertIn("alertPanel.innerHTML = alertsHtml(profile.alerts)", html)
        self.assertNotIn("alertsPanel.outerHTML", html)
        self.assertIn('data-alert-panel', html)
        self.assertIn('data-region-type="country"', html)
        self.assertIn('class="alert-evidence"', html)
        self.assertIn("Model Version: demo-risk-v1", html)
        self.assertIn("Prepare early action checklist.", html)
        self.assertIn('.alert-item[data-severity="unknown"]', html)
        self.assertIn(".alert-item[data-severity=\"normal\"]", html)
        self.assertNotIn('.alert-item[data-severity="unknown"] { border-left-color: var(--mwa-green); }', html)
        self.assertIn("No active alerts available for this region.", html)
        self.assertIn("No alerts match the selected filters.", html)

    def test_loader_error_renders_safe_fallback_without_trace(self) -> None:
        fake = FakeStreamlit()

        def boom() -> object:
            raise RuntimeError("C:\\Users\\peorr\\Downloads\\secret.json")

        render_dashboard(data_loader=boom, streamlit_module=fake)  # type: ignore[arg-type]

        self.assertEqual(fake.page_config["layout"], "wide")
        self.assertTrue(fake.html_calls)
        html = fake.html_calls[0]
        self.assertIn(SAFE_ERROR_MESSAGE, html)
        self.assertIn("Dashboard data could not be loaded", html)
        self.assertNotIn("Traceback", html)
        self.assertNotIn("RuntimeError", html)
        self.assertNotIn("secret.json", html)
        self.assertNotIn("C:\\Users", html)

    def test_render_prefers_components_html_for_svg_support(self) -> None:
        fake = FakeStreamlitWithComponents()

        render_dashboard(data_loader=lambda: load_dashboard_shell_data("demo"), streamlit_module=fake)

        self.assertFalse(fake.html_calls)
        self.assertTrue(fake.components.v1.html_calls)
        html, height, scrolling = fake.components.v1.html_calls[0]
        self.assertEqual(height, 900)
        self.assertTrue(scrolling)
        self.assertIn("<svg", html)
        self.assertIn('fill="#c93636"', html)

    def test_layout_contract_prevents_horizontal_scroll(self) -> None:
        html = build_dashboard_shell_html(load_dashboard_shell_data("demo"))

        self.assertIn("overflow-x: hidden", html)
        self.assertIn("minmax(0, 1fr)", html)
        self.assertIn("min-width: 0", html)
        self.assertIn("max-width: 1366px", html)

    def test_low_bandwidth_mode_renders_accessible_table_without_map_geometry(self) -> None:
        with patch.dict(os.environ, {"MWANGAZA_LOW_BANDWIDTH": "1"}):
            lite = build_dashboard_shell_html(load_dashboard_shell_data("demo"))
        full = build_dashboard_shell_html(load_dashboard_shell_data("demo"))

        self.assertLess(len(lite), len(full))
        self.assertIn('data-low-bandwidth="true"', lite)
        self.assertIn("data-low-bandwidth-toggle", lite)
        self.assertIn("<table>", lite)
        self.assertIn("<th>Indicator</th>", lite)
        self.assertIn("Composite score", lite)
        self.assertIn("Drought risk escalation", lite)
        self.assertIn("Prioritize water trucking readiness", lite)
        self.assertIn("mwangaza-executive-report", lite)
        self.assertIn("/api/v1/snapshots/latest", lite)
        self.assertNotIn("<svg", lite)
        self.assertNotIn("ui_geometry", lite)
        self.assertNotIn("regional-risk-svg", lite)


def _risk_snapshot(
    *,
    region_id: str = "ken",
    risk_level: str = "emergency",
    score: float = 82.0,
    is_simulated: bool = False,
    period_start: str = "2026-07-01T00:00:00Z",
    period_end: str = "2026-07-08T00:00:00Z",
) -> RiskSnapshot:
    scale = score / 75.2
    contributions = {
        "ndvi": {
            "weight": 0.4,
            "score": 72.0 * scale,
            "weighted_contribution": 0.4 * 72.0 * scale,
            "source": "TEST/ndvi",
            "quality_flag": "ok",
        },
        "rainfall_mm": {
            "weight": 0.4,
            "score": 84.0 * scale,
            "weighted_contribution": 0.4 * 84.0 * scale,
            "source": "TEST/rainfall",
            "quality_flag": "ok",
        },
        "lst_c": {
            "weight": 0.2,
            "score": 64.0 * scale,
            "weighted_contribution": 0.2 * 64.0 * scale,
            "source": "TEST/lst",
            "quality_flag": "ok",
        },
    }
    return RiskSnapshot(
        region_id=region_id,
        period_start=period_start,
        period_end=period_end,
        composite_score=score,
        risk_level=risk_level,
        contributing_indicators=("ndvi", "rainfall_mm"),
        source="mwangaza.risk.composite",
        quality_flag="ok",
        is_simulated=is_simulated,
        metadata={
            "model_version": "composite-risk-v1",
            "updated_at": "2026-07-09T00:00:00Z",
            "contributions": contributions,
        },
    )


def _json_payload(risk: RiskSnapshot) -> dict[str, object]:
    return json.loads(json.dumps(risk.to_dict()))


def _signal_payload(
    *,
    region_id: str,
    indicator: str,
    period_end: str,
    value: float | None,
    baseline: float,
    quality_flag: str,
) -> dict[str, object]:
    return {
        "payload_type": "indicator_observation",
        "schema_version": "mwangaza.contracts.v1",
        "region_id": region_id,
        "indicator": indicator,
        "period_start": period_end.replace("15T", "01T").replace("30T", "16T"),
        "period_end": period_end,
        "value": value,
        "unit": "index",
        "source": "MODIS/061/MOD13Q1",
        "quality_flag": quality_flag,
        "is_simulated": False,
        "metadata": {"updated_at": period_end, "baseline_value": baseline},
    }


def _exposure_payload(
    *,
    region_id: str,
    population: float,
    display_range: str = "1.1M-1.3M",
    warnings: list[str] | None = None,
) -> dict[str, object]:
    return {
        "payload_type": "exposure_estimate",
        "schema_version": "mwangaza.contracts.v1",
        "region_id": region_id,
        "period_start": "2026-07-01T00:00:00Z",
        "period_end": "2026-07-15T00:00:00Z",
        "metric": "potentially_exposed",
        "population_estimate": population,
        "livelihood_estimate": 410000.0,
        "rounded_value": "1.2M",
        "precision_label": "rounded_to_100k",
        "display_range": display_range,
        "source": "demo-population-grid",
        "source_year": 2024,
        "resolution": "1 km",
        "method": "regional_fixture_sum",
        "quality_flag": "ok",
        "is_demo": True,
        "warnings": warnings or [],
        "metadata": {"fixture": "ui"},
    }


if __name__ == "__main__":
    unittest.main()
