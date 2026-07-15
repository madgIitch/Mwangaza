from __future__ import annotations

import math
from dataclasses import dataclass

ALERT_LEVELS = ("green", "yellow", "orange", "red", "unknown")


class ThresholdError(ValueError):
    pass


@dataclass(frozen=True)
class ThresholdBand:
    level: str
    minimum: float
    maximum: float


@dataclass(frozen=True)
class ThresholdPreset:
    threshold_version: str
    domain_min: float
    domain_max: float
    bands: tuple[ThresholdBand, ...]
    is_official: bool = False
    label: str = "prototype"


@dataclass(frozen=True)
class ThresholdClassification:
    level: str
    threshold_version: str
    value: float | None
    reason: str


def default_threshold_preset() -> ThresholdPreset:
    return ThresholdPreset(
        threshold_version="prototype-thresholds-v1",
        domain_min=0.0,
        domain_max=100.0,
        bands=(
            ThresholdBand("green", 0.0, 25.0),
            ThresholdBand("yellow", 25.0, 50.0),
            ThresholdBand("orange", 50.0, 75.0),
            ThresholdBand("red", 75.0, 100.0),
        ),
        is_official=False,
        label="prototype-not-igad-official",
    )


def validate_preset(preset: ThresholdPreset) -> None:
    if not preset.threshold_version:
        raise ThresholdError("threshold_version is required")
    if preset.domain_min >= preset.domain_max:
        raise ThresholdError("threshold domain is inverted")
    if not preset.bands:
        raise ThresholdError("threshold bands are required")
    expected_min = preset.domain_min
    for index, band in enumerate(preset.bands):
        if band.level not in ALERT_LEVELS or band.level == "unknown":
            raise ThresholdError(f"unsupported threshold level: {band.level}")
        if not all(math.isfinite(value) for value in (band.minimum, band.maximum)):
            raise ThresholdError("threshold bounds must be finite")
        if band.minimum != expected_min:
            raise ThresholdError("threshold ranges must cover the domain without gaps or overlaps")
        if band.minimum >= band.maximum:
            raise ThresholdError("threshold band is inverted")
        expected_min = band.maximum
        if index == len(preset.bands) - 1 and band.maximum != preset.domain_max:
            raise ThresholdError("threshold ranges must cover the domain without gaps or overlaps")


def classify_value(
    value: float | None,
    *,
    preset: ThresholdPreset | None = None,
    quality_blocked: bool = False,
) -> ThresholdClassification:
    resolved = preset or default_threshold_preset()
    validate_preset(resolved)
    if quality_blocked:
        return ThresholdClassification("unknown", resolved.threshold_version, value, "quality_blocked")
    if value is None:
        return ThresholdClassification("unknown", resolved.threshold_version, None, "value_missing")
    if not isinstance(value, int | float) or not math.isfinite(value):
        raise ThresholdError("value must be finite")
    if value < resolved.domain_min or value > resolved.domain_max:
        raise ThresholdError("value outside threshold domain")
    for index, band in enumerate(resolved.bands):
        is_last = index == len(resolved.bands) - 1
        if band.minimum <= value < band.maximum or (is_last and value == band.maximum):
            return ThresholdClassification(band.level, resolved.threshold_version, float(value), "matched")
    raise ThresholdError("value was not covered by threshold bands")


__all__ = [
    "ALERT_LEVELS",
    "ThresholdBand",
    "ThresholdClassification",
    "ThresholdError",
    "ThresholdPreset",
    "classify_value",
    "default_threshold_preset",
    "validate_preset",
]
