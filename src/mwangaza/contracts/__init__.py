from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Callable, ClassVar, Iterable, TypeVar

from mwangaza.regions import RegionCatalogError, get_region

SCHEMA_VERSION = "mwangaza.contracts.v1"
INDICATOR_UNITS = {
    "ndvi": "index",
    "rainfall_mm": "mm",
    "lst_c": "celsius",
    "composite_score": "score",
    "potentially_exposed": "people_estimate",
}
QUALITY_FLAGS = ("ok", "no_data", "insufficient_history", "invalid", "degraded")
NULL_VALUE_FLAGS = ("no_data", "insufficient_history", "invalid")
RISK_LEVELS = ("low", "watch", "warning", "emergency")
ALERT_SEVERITIES = ("info", "watch", "warning", "critical")
ALERT_STATUSES = ("draft", "active", "resolved", "cancelled")
EXPOSURE_METHODS = ("regional_fixture_sum", "weighted_overlap", "not_available")

Payload = TypeVar("Payload", bound="ContractPayload")
RegionValidator = Callable[[str], object]


class ContractValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ContractPayload:
    payload_type: ClassVar[str]
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["payload_type"] = self.payload_type
        return payload

    def validate(self, region_validator: RegionValidator | None = None) -> None:
        _validate_schema_version(self.schema_version)


@dataclass(frozen=True)
class IndicatorObservation(ContractPayload):
    payload_type: ClassVar[str] = "indicator_observation"
    region_id: str = ""
    indicator: str = ""
    period_start: str = ""
    period_end: str = ""
    value: float | None = None
    unit: str = ""
    source: str = ""
    quality_flag: str = ""
    is_simulated: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> IndicatorObservation:
        item = cls(
            schema_version=_required_str(payload, "schema_version"),
            region_id=_required_str(payload, "region_id"),
            indicator=_required_str(payload, "indicator"),
            period_start=_required_str(payload, "period_start"),
            period_end=_required_str(payload, "period_end"),
            value=_optional_number(payload, "value"),
            unit=_required_str(payload, "unit"),
            source=_required_str(payload, "source"),
            quality_flag=_required_str(payload, "quality_flag"),
            is_simulated=_required_bool(payload, "is_simulated"),
            metadata=_metadata(payload),
        )
        item.validate()
        return item

    def validate(self, region_validator: RegionValidator | None = None) -> None:
        super().validate(region_validator)
        _validate_region_id(self.region_id, region_validator)
        _validate_indicator_unit(self.indicator, self.unit)
        _validate_period(self.period_start, self.period_end)
        _validate_source(self.source)
        _validate_quality_value(self.quality_flag, self.value)


@dataclass(frozen=True)
class Baseline(ContractPayload):
    payload_type: ClassVar[str] = "baseline"
    region_id: str = ""
    indicator: str = ""
    period_start: str = ""
    period_end: str = ""
    baseline_start_year: int = 0
    baseline_end_year: int = 0
    mean: float | None = None
    median: float | None = None
    stddev: float | None = None
    observations: int = 0
    unit: str = ""
    source: str = ""
    quality_flag: str = ""
    is_simulated: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Baseline:
        item = cls(
            schema_version=_required_str(payload, "schema_version"),
            region_id=_required_str(payload, "region_id"),
            indicator=_required_str(payload, "indicator"),
            period_start=_required_str(payload, "period_start"),
            period_end=_required_str(payload, "period_end"),
            baseline_start_year=_required_int(payload, "baseline_start_year"),
            baseline_end_year=_required_int(payload, "baseline_end_year"),
            mean=_optional_number(payload, "mean"),
            median=_optional_number(payload, "median"),
            stddev=_optional_number(payload, "stddev"),
            observations=_required_int(payload, "observations"),
            unit=_required_str(payload, "unit"),
            source=_required_str(payload, "source"),
            quality_flag=_required_str(payload, "quality_flag"),
            is_simulated=_required_bool(payload, "is_simulated"),
            metadata=_metadata(payload),
        )
        item.validate()
        return item

    def validate(self, region_validator: RegionValidator | None = None) -> None:
        super().validate(region_validator)
        _validate_region_id(self.region_id, region_validator)
        _validate_indicator_unit(self.indicator, self.unit)
        _validate_period(self.period_start, self.period_end)
        if self.baseline_start_year > self.baseline_end_year:
            raise ContractValidationError("baseline years are inverted")
        if self.observations < 0:
            raise ContractValidationError("observations must be non-negative")
        _validate_optional_finite("mean", self.mean)
        _validate_optional_finite("median", self.median)
        _validate_optional_finite("stddev", self.stddev)
        _validate_source(self.source)
        _validate_quality_flag(self.quality_flag)


@dataclass(frozen=True)
class Anomaly(ContractPayload):
    payload_type: ClassVar[str] = "anomaly"
    region_id: str = ""
    indicator: str = ""
    period_start: str = ""
    period_end: str = ""
    value: float | None = None
    unit: str = ""
    baseline_id: str = ""
    method: str = ""
    source: str = ""
    quality_flag: str = ""
    is_simulated: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Anomaly:
        item = cls(
            schema_version=_required_str(payload, "schema_version"),
            region_id=_required_str(payload, "region_id"),
            indicator=_required_str(payload, "indicator"),
            period_start=_required_str(payload, "period_start"),
            period_end=_required_str(payload, "period_end"),
            value=_optional_number(payload, "value"),
            unit=_required_str(payload, "unit"),
            baseline_id=_required_str(payload, "baseline_id"),
            method=_required_str(payload, "method"),
            source=_required_str(payload, "source"),
            quality_flag=_required_str(payload, "quality_flag"),
            is_simulated=_required_bool(payload, "is_simulated"),
            metadata=_metadata(payload),
        )
        item.validate()
        return item

    def validate(self, region_validator: RegionValidator | None = None) -> None:
        super().validate(region_validator)
        _validate_region_id(self.region_id, region_validator)
        _validate_indicator(self.indicator)
        _validate_period(self.period_start, self.period_end)
        _validate_quality_value(self.quality_flag, self.value)
        _validate_source(self.source)
        if self.unit not in {"index", "mm", "celsius", "score", "people_estimate", "percent"}:
            raise ContractValidationError(f"unsupported anomaly unit: {self.unit}")


@dataclass(frozen=True)
class RiskSnapshot(ContractPayload):
    payload_type: ClassVar[str] = "risk_snapshot"
    region_id: str = ""
    period_start: str = ""
    period_end: str = ""
    composite_score: float | None = None
    risk_level: str = ""
    contributing_indicators: tuple[str, ...] = ()
    source: str = ""
    quality_flag: str = ""
    is_simulated: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> RiskSnapshot:
        item = cls(
            schema_version=_required_str(payload, "schema_version"),
            region_id=_required_str(payload, "region_id"),
            period_start=_required_str(payload, "period_start"),
            period_end=_required_str(payload, "period_end"),
            composite_score=_optional_number(payload, "composite_score"),
            risk_level=_required_str(payload, "risk_level"),
            contributing_indicators=tuple(_required_list(payload, "contributing_indicators")),
            source=_required_str(payload, "source"),
            quality_flag=_required_str(payload, "quality_flag"),
            is_simulated=_required_bool(payload, "is_simulated"),
            metadata=_metadata(payload),
        )
        item.validate()
        return item

    def validate(self, region_validator: RegionValidator | None = None) -> None:
        super().validate(region_validator)
        _validate_region_id(self.region_id, region_validator)
        _validate_period(self.period_start, self.period_end)
        _validate_quality_value(self.quality_flag, self.composite_score)
        if self.risk_level not in RISK_LEVELS:
            raise ContractValidationError(f"unsupported risk_level: {self.risk_level}")
        for indicator in self.contributing_indicators:
            _validate_indicator(indicator)
        _validate_source(self.source)


@dataclass(frozen=True)
class Alert(ContractPayload):
    payload_type: ClassVar[str] = "alert"
    alert_id: str = ""
    region_id: str = ""
    issued_at: str = ""
    severity: str = ""
    status: str = ""
    risk_level: str = ""
    message: str = ""
    source: str = ""
    quality_flag: str = ""
    is_simulated: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Alert:
        item = cls(
            schema_version=_required_str(payload, "schema_version"),
            alert_id=_required_str(payload, "alert_id"),
            region_id=_required_str(payload, "region_id"),
            issued_at=_required_str(payload, "issued_at"),
            severity=_required_str(payload, "severity"),
            status=_required_str(payload, "status"),
            risk_level=_required_str(payload, "risk_level"),
            message=_required_str(payload, "message"),
            source=_required_str(payload, "source"),
            quality_flag=_required_str(payload, "quality_flag"),
            is_simulated=_required_bool(payload, "is_simulated"),
            metadata=_metadata(payload),
        )
        item.validate()
        return item

    def validate(self, region_validator: RegionValidator | None = None) -> None:
        super().validate(region_validator)
        _validate_region_id(self.region_id, region_validator)
        _parse_datetime(self.issued_at, "issued_at")
        if self.severity not in ALERT_SEVERITIES:
            raise ContractValidationError(f"unsupported severity: {self.severity}")
        if self.status not in ALERT_STATUSES:
            raise ContractValidationError(f"unsupported status: {self.status}")
        if self.risk_level not in RISK_LEVELS:
            raise ContractValidationError(f"unsupported risk_level: {self.risk_level}")
        _validate_source(self.source)
        _validate_quality_flag(self.quality_flag)


@dataclass(frozen=True)
class Forecast(ContractPayload):
    payload_type: ClassVar[str] = "forecast"
    region_id: str = ""
    indicator: str = ""
    issue_time: str = ""
    target_period_start: str = ""
    target_period_end: str = ""
    horizon_days: int = 0
    value: float | None = None
    unit: str = ""
    uncertainty: float | None = None
    source: str = ""
    quality_flag: str = ""
    is_simulated: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Forecast:
        item = cls(
            schema_version=_required_str(payload, "schema_version"),
            region_id=_required_str(payload, "region_id"),
            indicator=_required_str(payload, "indicator"),
            issue_time=_required_str(payload, "issue_time"),
            target_period_start=_required_str(payload, "target_period_start"),
            target_period_end=_required_str(payload, "target_period_end"),
            horizon_days=_required_int(payload, "horizon_days"),
            value=_optional_number(payload, "value"),
            unit=_required_str(payload, "unit"),
            uncertainty=_optional_number(payload, "uncertainty"),
            source=_required_str(payload, "source"),
            quality_flag=_required_str(payload, "quality_flag"),
            is_simulated=_required_bool(payload, "is_simulated"),
            metadata=_metadata(payload),
        )
        item.validate()
        return item

    def validate(self, region_validator: RegionValidator | None = None) -> None:
        super().validate(region_validator)
        _validate_region_id(self.region_id, region_validator)
        _validate_indicator_unit(self.indicator, self.unit)
        _parse_datetime(self.issue_time, "issue_time")
        _validate_period(self.target_period_start, self.target_period_end)
        if self.horizon_days <= 0:
            raise ContractValidationError("horizon_days must be positive")
        _validate_quality_value(self.quality_flag, self.value)
        _validate_optional_finite("uncertainty", self.uncertainty)
        _validate_source(self.source)


@dataclass(frozen=True)
class ExposureEstimate(ContractPayload):
    payload_type: ClassVar[str] = "exposure_estimate"
    region_id: str = ""
    period_start: str = ""
    period_end: str = ""
    metric: str = "potentially_exposed"
    population_estimate: float | None = None
    livelihood_estimate: float | None = None
    rounded_value: str = ""
    precision_label: str = ""
    display_range: str = ""
    source: str = ""
    source_year: int = 0
    resolution: str = ""
    method: str = ""
    quality_flag: str = ""
    is_demo: bool = False
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ExposureEstimate:
        item = cls(
            schema_version=_required_str(payload, "schema_version"),
            region_id=_required_str(payload, "region_id"),
            period_start=_required_str(payload, "period_start"),
            period_end=_required_str(payload, "period_end"),
            metric=_required_str(payload, "metric"),
            population_estimate=_optional_number(payload, "population_estimate"),
            livelihood_estimate=_optional_number(payload, "livelihood_estimate"),
            rounded_value=str(payload.get("rounded_value", "")).strip(),
            precision_label=_required_str(payload, "precision_label"),
            display_range=str(payload.get("display_range", "")).strip(),
            source=_required_str(payload, "source"),
            source_year=_required_int(payload, "source_year"),
            resolution=_required_str(payload, "resolution"),
            method=_required_str(payload, "method"),
            quality_flag=_required_str(payload, "quality_flag"),
            is_demo=_required_bool(payload, "is_demo"),
            warnings=tuple(_optional_str_list(payload, "warnings")),
            metadata=_metadata(payload),
        )
        item.validate()
        return item

    def validate(self, region_validator: RegionValidator | None = None) -> None:
        super().validate(region_validator)
        _validate_region_id(self.region_id, region_validator)
        _validate_period(self.period_start, self.period_end)
        if self.metric != "potentially_exposed":
            raise ContractValidationError("exposure metric must be potentially_exposed")
        if self.method not in EXPOSURE_METHODS:
            raise ContractValidationError(f"unsupported exposure method: {self.method}")
        _validate_quality_flag(self.quality_flag)
        _validate_source(self.source)
        if self.source_year <= 0:
            raise ContractValidationError("source_year must be positive")
        if self.population_estimate is None and self.quality_flag == "ok":
            raise ContractValidationError("ok exposure requires population_estimate")
        _validate_optional_finite("population_estimate", self.population_estimate)
        _validate_optional_finite("livelihood_estimate", self.livelihood_estimate)
        lowered = json.dumps(self.to_dict(), sort_keys=True).lower()
        if "affected" in lowered:
            raise ContractValidationError("exposure payload must not use affected terminology")


PAYLOAD_TYPES: dict[str, type[ContractPayload]] = {
    IndicatorObservation.payload_type: IndicatorObservation,
    Baseline.payload_type: Baseline,
    Anomaly.payload_type: Anomaly,
    RiskSnapshot.payload_type: RiskSnapshot,
    Alert.payload_type: Alert,
    Forecast.payload_type: Forecast,
    ExposureEstimate.payload_type: ExposureEstimate,
}


def dumps_payload(payload: ContractPayload) -> str:
    payload.validate()
    return json.dumps(payload.to_dict(), sort_keys=True, separators=(",", ":"))


def loads_payload(raw: str | dict[str, Any]) -> ContractPayload:
    data = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(data, dict):
        raise ContractValidationError("payload must be a JSON object")
    metadata = data.get("metadata")
    payload_type = _required_str(data, "payload_type")
    if isinstance(metadata, dict) and metadata.get("fixture"):
        if payload_type == ExposureEstimate.payload_type:
            if data.get("is_demo") is not True:
                raise ContractValidationError("exposure fixtures must set is_demo=true")
        elif data.get("is_simulated") is not True:
            raise ContractValidationError("canonical fixtures must set is_simulated=true")
    cls = PAYLOAD_TYPES.get(payload_type)
    if cls is None:
        raise ContractValidationError(f"unsupported payload_type: {payload_type}")
    return cls.from_dict(data)  # type: ignore[attr-defined]


def validate_payload(payload: ContractPayload, region_validator: RegionValidator | None = None) -> None:
    payload.validate(region_validator)


def _validate_schema_version(schema_version: str) -> None:
    if schema_version != SCHEMA_VERSION:
        raise ContractValidationError(f"unsupported schema_version: {schema_version}")


def _validate_region_id(region_id: str, region_validator: RegionValidator | None) -> None:
    if not region_id:
        raise ContractValidationError("region_id is required")
    validator = region_validator or get_region
    try:
        validator(region_id)
    except (RegionCatalogError, KeyError, ValueError) as exc:
        raise ContractValidationError(f"unknown region_id: {region_id}") from exc


def _validate_indicator(indicator: str) -> None:
    if indicator not in INDICATOR_UNITS:
        raise ContractValidationError(f"unsupported indicator: {indicator}")


def _validate_indicator_unit(indicator: str, unit: str) -> None:
    _validate_indicator(indicator)
    expected = INDICATOR_UNITS[indicator]
    if unit != expected:
        raise ContractValidationError(f"unit {unit} is incompatible with indicator {indicator}")


def _validate_period(start: str, end: str) -> None:
    start_dt = _parse_datetime(start, "period_start")
    end_dt = _parse_datetime(end, "period_end")
    if start_dt > end_dt:
        raise ContractValidationError("period_start must be before or equal to period_end")


def _parse_datetime(value: str, field_name: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractValidationError(f"{field_name} must be ISO8601") from exc


def _validate_quality_value(quality_flag: str, value: float | None) -> None:
    _validate_quality_flag(quality_flag)
    if value is None:
        if quality_flag not in NULL_VALUE_FLAGS:
            raise ContractValidationError("value=None requires a no-data quality_flag")
        return
    _validate_optional_finite("value", value)


def _validate_quality_flag(quality_flag: str) -> None:
    if quality_flag not in QUALITY_FLAGS:
        raise ContractValidationError(f"unsupported quality_flag: {quality_flag}")


def _validate_optional_finite(field_name: str, value: float | None) -> None:
    if value is None:
        return
    if not isinstance(value, int | float) or not math.isfinite(value):
        raise ContractValidationError(f"{field_name} must be finite")


def _validate_source(source: str) -> None:
    if not source or source.startswith("/") or "\\" in source:
        raise ContractValidationError("source must be a non-sensitive source identifier")


def _required_str(payload: dict[str, Any], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ContractValidationError(f"{field_name} is required")
    return value.strip()


def _required_bool(payload: dict[str, Any], field_name: str) -> bool:
    value = payload.get(field_name)
    if not isinstance(value, bool):
        raise ContractValidationError(f"{field_name} is required")
    return value


def _required_int(payload: dict[str, Any], field_name: str) -> int:
    value = payload.get(field_name)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ContractValidationError(f"{field_name} must be an integer")
    return value


def _optional_number(payload: dict[str, Any], field_name: str) -> float | None:
    value = payload.get(field_name)
    if value is None:
        return None
    if not isinstance(value, int | float) or isinstance(value, bool) or not math.isfinite(value):
        raise ContractValidationError(f"{field_name} must be finite")
    return float(value)


def _required_list(payload: dict[str, Any], field_name: str) -> list[str]:
    value = payload.get(field_name)
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ContractValidationError(f"{field_name} must be a list of strings")
    return value


def _optional_str_list(payload: dict[str, Any], field_name: str) -> list[str]:
    value = payload.get(field_name, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ContractValidationError(f"{field_name} must be a list of strings")
    return value


def _metadata(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("metadata", {})
    if not isinstance(value, dict):
        raise ContractValidationError("metadata must be an object")
    return value
