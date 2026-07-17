from __future__ import annotations

from typing import Any

from mwangaza.contracts import ExposureEstimate


def exposure_from_payload(payload: dict[str, Any] | None) -> ExposureEstimate | None:
    if not isinstance(payload, dict):
        return None
    if payload.get("payload_type") != ExposureEstimate.payload_type:
        return None
    try:
        return ExposureEstimate.from_dict(payload)
    except ValueError:
        return None


def display_exposure_value(estimate: ExposureEstimate | None) -> str:
    if estimate is None or estimate.population_estimate is None:
        return "No data"
    if estimate.display_range:
        return estimate.display_range
    if estimate.rounded_value:
        return estimate.rounded_value
    return _rounded_people(estimate.population_estimate)


def exposure_detail(estimate: ExposureEstimate | None) -> str:
    if estimate is None:
        return "No valid exposure dataset"
    parts = [
        f"{estimate.metric}",
        f"source {estimate.source}",
        f"year {estimate.source_year}",
        estimate.resolution,
        estimate.method,
        f"quality {estimate.quality_flag}",
    ]
    if estimate.is_demo:
        parts.append("demo/synthetic")
    if estimate.warnings:
        parts.append("warning: " + "; ".join(estimate.warnings))
    return " | ".join(part for part in parts if part)


def _rounded_people(value: float) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 10_000:
        return f"{round(value / 1_000) * 1_000:,.0f}"
    if value >= 1_000:
        return f"{round(value / 100) * 100:,.0f}"
    return f"{round(value):,.0f}"
