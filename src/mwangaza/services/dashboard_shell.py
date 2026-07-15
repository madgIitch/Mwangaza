from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from mwangaza import PROJECT_NAME, TAGLINE

DataMode = Literal["live", "cache", "demo"]
Freshness = Literal["current", "stale", "error", "loading", "empty"]
Severity = Literal["normal", "watch", "warning", "critical", "unknown"]


@dataclass(frozen=True)
class NavigationItem:
    key: str
    label: str
    active: bool = False


@dataclass(frozen=True)
class DataStatus:
    mode: DataMode
    freshness: Freshness
    source: str
    last_updated: str
    message: str


@dataclass(frozen=True)
class RegionMetric:
    label: str
    value: str
    unit: str
    severity: Severity
    detail: str


@dataclass(frozen=True)
class AlertSummary:
    region: str
    severity: Severity
    title: str
    period: str
    action: str


@dataclass(frozen=True)
class DashboardShellData:
    project: str
    tagline: str
    selected_region: str
    data_status: DataStatus
    navigation: tuple[NavigationItem, ...]
    metrics: tuple[RegionMetric, ...]
    alerts: tuple[AlertSummary, ...]
    recommendations: tuple[str, ...]


def load_dashboard_shell_data(mode: DataMode = "demo") -> DashboardShellData:
    """Return deterministic shell data; Sprint 22 intentionally performs no remote reads."""

    status_by_mode = {
        "live": DataStatus(
            mode="live",
            freshness="current",
            source="Live pipeline",
            last_updated="2026-07-15 16:00 UTC",
            message="Data is current",
        ),
        "cache": DataStatus(
            mode="cache",
            freshness="stale",
            source="Versioned cache",
            last_updated="2026-07-14 06:00 UTC",
            message="Using cached data",
        ),
        "demo": DataStatus(
            mode="demo",
            freshness="current",
            source="Demo fixture",
            last_updated="2026-07-15 16:00 UTC",
            message="Data is current",
        ),
    }
    return DashboardShellData(
        project=PROJECT_NAME,
        tagline=TAGLINE,
        selected_region="Somalia",
        data_status=status_by_mode[mode],
        navigation=(
            NavigationItem("overview", "Overview", True),
            NavigationItem("region", "Region"),
            NavigationItem("alerts", "Alerts"),
            NavigationItem("reports", "Reports"),
            NavigationItem("about", "About"),
        ),
        metrics=(
            RegionMetric("NDVI anomaly", "-0.18", "z", "warning", "Vegetation stress"),
            RegionMetric("Rainfall anomaly", "-42", "%", "critical", "Below seasonal baseline"),
            RegionMetric("LST anomaly", "+2.4", "C", "warning", "Surface heat elevated"),
            RegionMetric("Composite score", "78", "/100", "critical", "High drought risk"),
            RegionMetric("Data quality", "Good", "", "normal", "Most indicators available"),
            RegionMetric("Exposed population", "1.2M", "est.", "watch", "Exposure estimate"),
        ),
        alerts=(
            AlertSummary(
                "Somalia",
                "critical",
                "Drought risk escalation",
                "Jul 2026",
                "View details",
            ),
            AlertSummary(
                "Northern Kenya",
                "warning",
                "Rainfall deficit watch",
                "Jul 2026",
                "View details",
            ),
            AlertSummary(
                "Ethiopia",
                "watch",
                "Vegetation stress emerging",
                "Jul 2026",
                "View details",
            ),
        ),
        recommendations=(
            "Prioritize water trucking readiness in high-risk districts.",
            "Pre-position livestock feed in pastoral corridors.",
            "Coordinate district verification before publishing alerts.",
        ),
    )


def fallback_dashboard_shell_data() -> DashboardShellData:
    data = load_dashboard_shell_data("demo")
    return DashboardShellData(
        project=data.project,
        tagline=data.tagline,
        selected_region=data.selected_region,
        data_status=DataStatus(
            mode="demo",
            freshness="error",
            source="Safe fallback",
            last_updated=data.data_status.last_updated,
            message="Dashboard data could not be loaded",
        ),
        navigation=data.navigation,
        metrics=data.metrics,
        alerts=(),
        recommendations=("Retry after checking configuration and data refresh status.",),
    )
