from __future__ import annotations

import math
from dataclasses import dataclass
from html import escape
from typing import Any, Iterable

from mwangaza.contracts import RiskSnapshot
from mwangaza.regions import COUNTRY_LEVEL, Region, list_regions

RISK_COLOR_LEVELS = ("green", "yellow", "orange", "red", "unknown")
RISK_LEVEL_LABELS = {
    "green": "Low",
    "yellow": "Watch",
    "orange": "Warning",
    "red": "Critical",
    "unknown": "Unknown",
}
RISK_LEVEL_CLASS = {
    "green": "risk-green",
    "yellow": "risk-yellow",
    "orange": "risk-orange",
    "red": "risk-red",
    "unknown": "risk-unknown",
}
RISK_LEVEL_COLORS = {
    "green": "#1f7a4d",
    "yellow": "#f4c542",
    "orange": "#e68032",
    "red": "#c93636",
    "unknown": "#8c9690",
}
BLOCKING_QUALITY_FLAGS = {"invalid", "no_data", "insufficient_history"}


@dataclass(frozen=True)
class RegionalRiskMapRegion:
    region_id: str
    name: str
    iso3: str
    ui_geometry: dict[str, Any]
    risk_level: str
    score: float | None
    period_start: str
    period_end: str
    quality_flag: str
    source_mode: str
    selected: bool = False

    @property
    def color_level(self) -> str:
        return risk_level_to_color(self.risk_level, self.score, self.quality_flag)

    @property
    def tooltip(self) -> str:
        score = "No data" if self.score is None else _format_number(self.score)
        period = _period_label(self.period_start, self.period_end)
        return (
            f"{self.name} | score: {score} | level: {self.color_level} | "
            f"period: {period} | quality: {self.quality_flag or 'unknown'}"
        )


@dataclass(frozen=True)
class RegionalRiskMap:
    regions: tuple[RegionalRiskMapRegion, ...]
    selected_region_id: str


def build_regional_risk_map(
    risks: Iterable[RiskSnapshot | dict[str, Any]],
    *,
    selected_region_id: str = "som",
    source_mode: str = "demo",
    regions: Iterable[Region] | None = None,
) -> RegionalRiskMap:
    catalog = tuple(regions or list_regions(level=COUNTRY_LEVEL, include_pilots=False))
    risk_by_region = _latest_risk_by_region(risks)
    selected = selected_region_id.strip().lower()
    return RegionalRiskMap(
        selected_region_id=selected,
        regions=tuple(
            _map_region(region, risk_by_region.get(region.id), source_mode, selected)
            for region in catalog
        ),
    )


def build_regional_risk_map_html(risk_map: RegionalRiskMap) -> str:
    bounds = _bounds(risk_map.regions)
    paths = "\n".join(_render_region_path(region, bounds) for region in risk_map.regions)
    legend = "\n".join(
        '<span class="risk-legend-item {klass}" data-risk-level="{level}">'
        '<i aria-hidden="true"></i>{label}</span>'.format(
            klass=RISK_LEVEL_CLASS[level],
            level=level,
            label=RISK_LEVEL_LABELS[level],
        )
        for level in RISK_COLOR_LEVELS
    )
    return f"""
<div class="regional-risk-map" data-selected-region="{escape(risk_map.selected_region_id)}">
  <svg class="regional-risk-svg" viewBox="0 0 760 420" role="img" aria-label="IGAD regional risk map">
    {paths}
  </svg>
  <div class="risk-map-legend" aria-label="Risk legend">{legend}</div>
</div>
"""


def demo_regional_risk_map(*, selected_region_id: str = "som") -> RegionalRiskMap:
    risks = (
        _demo_risk("som", 82.0, "emergency", "ok"),
        _demo_risk("ken", 61.0, "warning", "ok"),
        _demo_risk("eth", 38.0, "watch", "degraded"),
        _demo_risk("uga", 18.0, "low", "ok"),
        _demo_risk("dji", None, "low", "no_data"),
    )
    return build_regional_risk_map(risks, selected_region_id=selected_region_id, source_mode="demo")


def risk_level_to_color(risk_level: str, score: float | None, quality_flag: str) -> str:
    if quality_flag in BLOCKING_QUALITY_FLAGS or score is None or not _finite(score):
        return "unknown"
    normalized = risk_level.lower()
    if normalized in {"low", "normal", "green"}:
        return "green"
    if normalized in {"watch", "yellow"}:
        return "yellow"
    if normalized in {"warning", "orange"}:
        return "orange"
    if normalized in {"emergency", "critical", "red"}:
        return "red"
    return "unknown"


def _latest_risk_by_region(risks: Iterable[RiskSnapshot | dict[str, Any]]) -> dict[str, RiskSnapshot]:
    latest: dict[str, RiskSnapshot] = {}
    for item in risks:
        risk = _coerce_risk(item)
        if risk is None:
            continue
        current = latest.get(risk.region_id)
        if current is None or risk.period_end >= current.period_end:
            latest[risk.region_id] = risk
    return latest


def _coerce_risk(item: RiskSnapshot | dict[str, Any]) -> RiskSnapshot | None:
    if isinstance(item, RiskSnapshot):
        return item
    if not isinstance(item, dict) or item.get("payload_type") != RiskSnapshot.payload_type:
        return None
    try:
        return RiskSnapshot.from_dict(item)
    except Exception:
        return None


def _map_region(
    region: Region,
    risk: RiskSnapshot | None,
    source_mode: str,
    selected_region_id: str,
) -> RegionalRiskMapRegion:
    if risk is None:
        return RegionalRiskMapRegion(
            region_id=region.id,
            name=region.name,
            iso3=region.iso3,
            ui_geometry=region.ui_geometry,
            risk_level="unknown",
            score=None,
            period_start="",
            period_end="",
            quality_flag="no_data",
            source_mode=source_mode,
            selected=region.id == selected_region_id,
        )
    return RegionalRiskMapRegion(
        region_id=region.id,
        name=region.name,
        iso3=region.iso3,
        ui_geometry=region.ui_geometry,
        risk_level=_public_risk_level(risk),
        score=risk.composite_score,
        period_start=risk.period_start,
        period_end=risk.period_end,
        quality_flag=risk.quality_flag,
        source_mode=source_mode,
        selected=region.id == selected_region_id,
    )


def _public_risk_level(risk: RiskSnapshot) -> str:
    override = risk.metadata.get("risk_level_override")
    if override == "unknown":
        return "unknown"
    return risk.risk_level


def _render_region_path(region: RegionalRiskMapRegion, bounds: tuple[float, float, float, float]) -> str:
    path = _polygon_path(region.ui_geometry, bounds)
    classes = f"risk-region {RISK_LEVEL_CLASS[region.color_level]}"
    if region.selected:
        classes += " is-selected"
    return (
        '<path class="{classes}" d="{path}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}" '
        'data-region-id="{region_id}" data-risk-level="{level}" data-score="{score}" '
        'data-region-name="{name}" data-period="{period}" data-quality="{quality}" '
        'tabindex="0"><title>{tooltip}</title></path>'
    ).format(
        region_id=escape(region.region_id),
        name=escape(region.name),
        level=escape(region.color_level),
        score=escape("" if region.score is None else _format_number(region.score)),
        period=escape(_period_label(region.period_start, region.period_end)),
        quality=escape(region.quality_flag),
        classes=escape(classes),
        path=escape(path),
        fill=RISK_LEVEL_COLORS[region.color_level],
        stroke="#17231c" if region.selected else "#ffffff",
        stroke_width="4" if region.selected else "2",
        tooltip=escape(region.tooltip),
    )


def _polygon_path(geometry: dict[str, Any], bounds: tuple[float, float, float, float]) -> str:
    coordinates = geometry.get("coordinates")
    if not isinstance(coordinates, list) or not coordinates:
        return ""
    ring = coordinates[0]
    points = [_project(float(lon), float(lat), bounds) for lon, lat in ring]
    if not points:
        return ""
    first, *rest = points
    return " ".join((f"M {first[0]:.2f} {first[1]:.2f}", *(f"L {x:.2f} {y:.2f}" for x, y in rest), "Z"))


def _bounds(regions: Iterable[RegionalRiskMapRegion]) -> tuple[float, float, float, float]:
    points: list[tuple[float, float]] = []
    for region in regions:
        coordinates = region.ui_geometry.get("coordinates")
        if isinstance(coordinates, list) and coordinates:
            points.extend((float(lon), float(lat)) for lon, lat in coordinates[0])
    if not points:
        return (0.0, 0.0, 1.0, 1.0)
    lon_values = [lon for lon, _lat in points]
    lat_values = [lat for _lon, lat in points]
    return (min(lon_values), min(lat_values), max(lon_values), max(lat_values))


def _project(lon: float, lat: float, bounds: tuple[float, float, float, float]) -> tuple[float, float]:
    min_lon, min_lat, max_lon, max_lat = bounds
    width = max(max_lon - min_lon, 1e-9)
    height = max(max_lat - min_lat, 1e-9)
    x = 28.0 + ((lon - min_lon) / width) * 704.0
    y = 392.0 - ((lat - min_lat) / height) * 364.0
    return x, y


def _demo_risk(region_id: str, score: float | None, risk_level: str, quality_flag: str) -> RiskSnapshot:
    return RiskSnapshot(
        region_id=region_id,
        period_start="2026-07-01T00:00:00Z",
        period_end="2026-07-15T00:00:00Z",
        composite_score=score,
        risk_level=risk_level,
        contributing_indicators=("ndvi", "rainfall_mm") if score is not None else (),
        source="mwangaza.demo.risk",
        quality_flag=quality_flag,
        is_simulated=True,
        metadata={"model_version": "demo-regional-risk-map-v1"},
    )


def _period_label(period_start: str, period_end: str) -> str:
    if period_start and period_end:
        return f"{period_start[:10]} to {period_end[:10]}"
    if period_end:
        return period_end[:10]
    return "No period"


def _format_number(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _finite(value: float | None) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value)


__all__ = [
    "RISK_COLOR_LEVELS",
    "RISK_LEVEL_COLORS",
    "RegionalRiskMap",
    "RegionalRiskMapRegion",
    "build_regional_risk_map",
    "build_regional_risk_map_html",
    "demo_regional_risk_map",
    "risk_level_to_color",
]
