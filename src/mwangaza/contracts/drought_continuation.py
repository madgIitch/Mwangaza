from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Mapping

from mwangaza.contracts import ContractValidationError

SCHEMA_VERSION = "mwangaza.drought-continuation-probability.v1"
ESTIMATE_KINDS = frozenset({"experimental_ml_prediction", "historical_reference"})
STATUSES = frozenset({"available", "unavailable", "not_applicable"})
HORIZONS = frozenset({30, 60, 90, 180})


@dataclass(frozen=True)
class ContinuationEstimate:
    kind: str
    status: str
    probability: float | None
    estimator_kind: str
    model: str
    experimental: bool
    operational_use: bool
    validation: dict[str, Any] = field(default_factory=dict)
    quality: dict[str, Any] = field(default_factory=dict)
    reason_codes: tuple[str, ...] = ()
    drivers: tuple[dict[str, Any], ...] = ()
    artifact: dict[str, Any] = field(default_factory=dict)
    evidence: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> ContinuationEstimate:
        item = cls(
            kind=_required_string(value, "kind"),
            status=_required_string(value, "status"),
            probability=_optional_probability(value.get("probability")),
            estimator_kind=_required_string(value, "estimator_kind"),
            model=_required_string(value, "model"),
            experimental=_required_bool(value, "experimental"),
            operational_use=_required_bool(value, "operational_use"),
            validation=_required_object(value, "validation"),
            quality=_required_object(value, "quality"),
            reason_codes=_string_tuple(value.get("reason_codes", ()), "reason_codes"),
            drivers=_object_tuple(value.get("drivers", ()), "drivers"),
            artifact=_optional_object(value, "artifact"),
            evidence=_optional_object(value, "evidence"),
        )
        item.validate()
        return item

    def validate(self) -> None:
        if self.kind not in ESTIMATE_KINDS:
            raise ContractValidationError("unsupported continuation estimate kind")
        if self.status not in {"available", "unavailable"}:
            raise ContractValidationError("estimate status must be available or unavailable")
        if (self.status == "available") != (self.probability is not None):
            raise ContractValidationError("probability presence must match estimate status")
        if self.operational_use:
            raise ContractValidationError("continuation estimates are not operational")
        if len(self.drivers) > 3:
            raise ContractValidationError("at most three continuation drivers are allowed")
        if any(driver.get("causal") is not False for driver in self.drivers):
            raise ContractValidationError("continuation drivers must be explicitly non-causal")
        if self.kind == "experimental_ml_prediction":
            if not self.experimental or self.estimator_kind != "ml":
                raise ContractValidationError("experimental ML identity is inconsistent")
            if self.validation.get("status") != "inconclusive":
                raise ContractValidationError("experimental ML must retain inconclusive validation")
            interval = self.validation.get("bootstrap_delta_brier_ci95")
            if not isinstance(interval, list) or len(interval) != 2:
                raise ContractValidationError("experimental ML requires its bootstrap IC95")
        elif self.experimental or self.estimator_kind != "baseline":
            raise ContractValidationError("historical reference identity is inconsistent")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["reason_codes"] = list(self.reason_codes)
        payload["drivers"] = list(self.drivers)
        return payload


@dataclass(frozen=True)
class DroughtContinuationProbability:
    region_id: str
    as_of: str
    horizon_days: int
    target: str
    current_drought_status: str
    current_phase: str
    current_trend: str
    elapsed_days: int | None
    status: str
    reason_codes: tuple[str, ...] = ()
    estimates: tuple[ContinuationEstimate, ...] = ()
    schema_version: str = SCHEMA_VERSION

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> DroughtContinuationProbability:
        estimates = value.get("estimates", ())
        if not isinstance(estimates, (list, tuple)):
            raise ContractValidationError("estimates must be a list")
        elapsed = value.get("elapsed_days")
        if elapsed is not None and (not isinstance(elapsed, int) or isinstance(elapsed, bool)):
            raise ContractValidationError("elapsed_days must be an integer or null")
        item = cls(
            schema_version=str(value.get("schema_version") or SCHEMA_VERSION),
            region_id=_required_string(value, "region_id"),
            as_of=_required_string(value, "as_of"),
            horizon_days=_required_int(value, "horizon_days"),
            target=_required_string(value, "target"),
            current_drought_status=_required_string(value, "current_drought_status"),
            current_phase=_required_string(value, "current_phase"),
            current_trend=_required_string(value, "current_trend"),
            elapsed_days=elapsed,
            status=_required_string(value, "status"),
            reason_codes=_string_tuple(value.get("reason_codes", ()), "reason_codes"),
            estimates=tuple(ContinuationEstimate.from_mapping(entry) for entry in estimates),
        )
        item.validate()
        return item

    def validate(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ContractValidationError("unsupported drought continuation schema_version")
        _parse_iso(self.as_of)
        if self.horizon_days not in HORIZONS:
            raise ContractValidationError("horizon_days must be 30, 60, 90 or 180")
        if self.target != "same_episode_continues":
            raise ContractValidationError("unsupported drought continuation target")
        if self.status not in STATUSES:
            raise ContractValidationError("unsupported drought continuation status")
        if self.current_drought_status not in {"active", "inactive", "unknown"}:
            raise ContractValidationError("unsupported current_drought_status")
        kinds = [estimate.kind for estimate in self.estimates]
        if len(kinds) != len(set(kinds)):
            raise ContractValidationError("continuation estimate kinds must be unique")
        if self.status == "not_applicable":
            if self.current_drought_status != "inactive" or self.estimates:
                raise ContractValidationError("not_applicable requires known inactive drought")
            return
        if self.current_drought_status != "active":
            raise ContractValidationError("available/unavailable requires active drought")
        if self.status == "unavailable" and not self.estimates:
            return
        if self.horizon_days == 30:
            if set(kinds) != ESTIMATE_KINDS:
                raise ContractValidationError("30-day active result requires ML and reference")
        elif kinds != ["historical_reference"]:
            raise ContractValidationError("long horizons allow only historical reference")
        has_probability = any(estimate.status == "available" for estimate in self.estimates)
        if (self.status == "available") != has_probability:
            raise ContractValidationError("result status must match available estimates")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["reason_codes"] = list(self.reason_codes)
        payload["estimates"] = [estimate.to_dict() for estimate in self.estimates]
        return payload


def _required_string(value: Mapping[str, Any], name: str) -> str:
    item = value.get(name)
    if not isinstance(item, str) or not item.strip():
        raise ContractValidationError(f"{name} is required")
    return item.strip()


def _required_bool(value: Mapping[str, Any], name: str) -> bool:
    item = value.get(name)
    if not isinstance(item, bool):
        raise ContractValidationError(f"{name} must be boolean")
    return item


def _required_int(value: Mapping[str, Any], name: str) -> int:
    item = value.get(name)
    if not isinstance(item, int) or isinstance(item, bool):
        raise ContractValidationError(f"{name} must be an integer")
    return item


def _optional_probability(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractValidationError("probability must be numeric or null")
    result = float(value)
    if not math.isfinite(result) or not 0 <= result <= 1:
        raise ContractValidationError("probability must be finite and between zero and one")
    return result


def _required_object(value: Mapping[str, Any], name: str) -> dict[str, Any]:
    item = value.get(name)
    if not isinstance(item, dict):
        raise ContractValidationError(f"{name} must be an object")
    return dict(item)


def _optional_object(value: Mapping[str, Any], name: str) -> dict[str, Any]:
    item = value.get(name, {})
    if not isinstance(item, dict):
        raise ContractValidationError(f"{name} must be an object")
    return dict(item)


def _string_tuple(value: Any, name: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ContractValidationError(f"{name} must be a list of strings")
    return tuple(value)


def _object_tuple(value: Any, name: str) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, (list, tuple)) or not all(isinstance(item, dict) for item in value):
        raise ContractValidationError(f"{name} must be a list of objects")
    return tuple(dict(item) for item in value)


def _parse_iso(value: str) -> None:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractValidationError("as_of must be ISO8601") from exc


__all__ = [
    "ContinuationEstimate",
    "DroughtContinuationProbability",
    "ESTIMATE_KINDS",
    "HORIZONS",
    "SCHEMA_VERSION",
    "STATUSES",
]
