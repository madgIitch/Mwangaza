from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, Iterable, Sequence

from mwangaza.contracts import (
    INDICATOR_UNITS,
    Anomaly,
    Baseline,
    ContractPayload,
    ContractValidationError,
    IndicatorObservation,
    loads_payload,
    validate_payload,
)

SignalPayload = IndicatorObservation | Anomaly | Baseline
QUALITY_PRESENT = {"ok"}
QUALITY_DEGRADED = {"degraded"}
QUALITY_ABSENT = {"no_data", "insufficient_history", "invalid"}


class IndicatorSnapshotError(ValueError):
    pass


@dataclass(frozen=True)
class IndicatorSnapshot:
    snapshot_id: str
    region_id: str
    period_start: str
    period_end: str
    indicators_present: tuple[str, ...]
    indicators_absent: tuple[str, ...]
    indicators_degraded: tuple[str, ...]
    signals: tuple[dict[str, Any], ...]
    oldest_updated_at: str
    newest_updated_at: str
    content_hash: str
    quality_flag: str
    is_simulated: bool
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_indicator_snapshot(
    region_id: str,
    period_start: str,
    period_end: str,
    signals: Sequence[SignalPayload | dict[str, Any] | str],
    *,
    expected_indicators: Iterable[str] | None = None,
) -> IndicatorSnapshot:
    if not region_id.strip():
        raise IndicatorSnapshotError("region_id is required")
    _parse_datetime(period_start, "period_start")
    _parse_datetime(period_end, "period_end")
    if _parse_datetime(period_start, "period_start") > _parse_datetime(period_end, "period_end"):
        raise IndicatorSnapshotError("period_start must be before or equal to period_end")

    normalized = [_coerce_signal(signal) for signal in signals]
    expected = _normalize_expected(expected_indicators, normalized)
    serialized = [
        _serialize_signal(signal, region_id, period_start, period_end)
        for signal in normalized
    ]
    _reject_duplicate_signals(serialized)

    present, absent, degraded = _classify_indicators(expected, serialized)
    updated_times = [_serialized_signal_updated_at(signal, period_end) for signal in serialized]
    if not updated_times:
        updated_times = [_parse_datetime(period_end, "period_end")]
    oldest = min(updated_times).astimezone(UTC).isoformat().replace("+00:00", "Z")
    newest = max(updated_times).astimezone(UTC).isoformat().replace("+00:00", "Z")

    stable_signals = tuple(sorted(serialized, key=_signal_sort_key))
    content = {
        "region_id": region_id.strip().lower(),
        "period_start": period_start,
        "period_end": period_end,
        "expected_indicators": sorted(expected),
        "signals": stable_signals,
        "oldest_updated_at": oldest,
        "newest_updated_at": newest,
    }
    content_hash = _stable_hash(content)
    quality_flag = _snapshot_quality(present, absent, degraded)
    return IndicatorSnapshot(
        snapshot_id=content_hash[:16],
        region_id=region_id.strip().lower(),
        period_start=period_start,
        period_end=period_end,
        indicators_present=tuple(sorted(present)),
        indicators_absent=tuple(sorted(absent)),
        indicators_degraded=tuple(sorted(degraded)),
        signals=stable_signals,
        oldest_updated_at=oldest,
        newest_updated_at=newest,
        content_hash=content_hash,
        quality_flag=quality_flag,
        is_simulated=all(signal.get("is_simulated") is True for signal in stable_signals),
        metadata={"signal_count": len(stable_signals), "hash_algorithm": "sha256"},
    )


def _coerce_signal(signal: SignalPayload | dict[str, Any] | str) -> SignalPayload:
    try:
        payload = loads_payload(signal) if isinstance(signal, dict | str) else signal
        validate_payload(payload)
    except (ContractValidationError, TypeError, json.JSONDecodeError) as exc:
        raise IndicatorSnapshotError(str(exc)) from exc
    if not isinstance(payload, IndicatorObservation | Anomaly | Baseline):
        raise IndicatorSnapshotError(f"unsupported snapshot payload_type: {payload.payload_type}")
    return payload


def _serialize_signal(
    signal: SignalPayload,
    region_id: str,
    period_start: str,
    period_end: str,
) -> dict[str, Any]:
    payload = signal.to_dict()
    if payload["region_id"] != region_id.strip().lower():
        raise IndicatorSnapshotError("all signals must use the snapshot region_id")
    if payload["period_start"] != period_start or payload["period_end"] != period_end:
        raise IndicatorSnapshotError("all signals must use the snapshot analysis window")
    indicator = payload["indicator"]
    if indicator not in INDICATOR_UNITS:
        raise IndicatorSnapshotError(f"unsupported indicator: {indicator}")
    if signal.payload_type != "anomaly" and payload["unit"] != INDICATOR_UNITS[indicator]:
        raise IndicatorSnapshotError(f"unit {payload['unit']} is incompatible with {indicator}")
    _signal_updated_at(signal, period_end)
    _assert_json_serializable(payload)
    return payload


def _normalize_expected(
    expected_indicators: Iterable[str] | None,
    signals: Sequence[SignalPayload],
) -> set[str]:
    expected = set(expected_indicators or [signal.indicator for signal in signals])
    unknown = sorted(indicator for indicator in expected if indicator not in INDICATOR_UNITS)
    if unknown:
        raise IndicatorSnapshotError(f"unsupported expected indicators: {', '.join(unknown)}")
    return expected


def _reject_duplicate_signals(signals: Sequence[dict[str, Any]]) -> None:
    seen: set[tuple[str, str]] = set()
    for signal in signals:
        key = (signal["payload_type"], signal["indicator"])
        if key in seen:
            raise IndicatorSnapshotError(
                f"duplicate signal for payload_type={key[0]} indicator={key[1]}"
            )
        seen.add(key)


def _classify_indicators(
    expected: set[str],
    signals: Sequence[dict[str, Any]],
) -> tuple[set[str], set[str], set[str]]:
    by_indicator: dict[str, list[dict[str, Any]]] = {}
    for signal in signals:
        by_indicator.setdefault(signal["indicator"], []).append(signal)

    present: set[str] = set()
    absent: set[str] = set(expected) - set(by_indicator)
    degraded: set[str] = set()
    for indicator, items in by_indicator.items():
        flags = {item["quality_flag"] for item in items}
        if flags & QUALITY_DEGRADED:
            degraded.add(indicator)
        if flags <= QUALITY_ABSENT:
            absent.add(indicator)
        if flags & QUALITY_PRESENT:
            present.add(indicator)
    return present, absent, degraded


def _snapshot_quality(present: set[str], absent: set[str], degraded: set[str]) -> str:
    if absent and not present and not degraded:
        return "no_data"
    if absent:
        return "invalid"
    if degraded:
        return "degraded"
    return "ok"


def _signal_updated_at(signal: SignalPayload, period_end: str) -> datetime:
    updated_at = signal.metadata.get("updated_at", period_end)
    if not isinstance(updated_at, str):
        raise IndicatorSnapshotError("metadata.updated_at must be an ISO8601 string")
    return _parse_datetime(updated_at, "metadata.updated_at")


def _serialized_signal_updated_at(signal: dict[str, Any], period_end: str) -> datetime:
    metadata = signal.get("metadata", {})
    if not isinstance(metadata, dict):
        raise IndicatorSnapshotError("metadata must be an object")
    updated_at = metadata.get("updated_at", period_end)
    if not isinstance(updated_at, str):
        raise IndicatorSnapshotError("metadata.updated_at must be an ISO8601 string")
    return _parse_datetime(updated_at, "metadata.updated_at")


def _parse_datetime(value: str, field_name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise IndicatorSnapshotError(f"{field_name} must be ISO8601") from exc
    if parsed.tzinfo is None:
        raise IndicatorSnapshotError(f"{field_name} must include timezone")
    return parsed.astimezone(UTC)


def _stable_hash(content: dict[str, Any]) -> str:
    return sha256(json.dumps(content, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _signal_sort_key(signal: dict[str, Any]) -> tuple[str, str, str]:
    return (signal["indicator"], signal["payload_type"], signal.get("source", ""))


def _assert_json_serializable(payload: dict[str, Any]) -> None:
    try:
        json.dumps(payload, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise IndicatorSnapshotError("signal payload must be JSON serializable") from exc


__all__ = [
    "IndicatorSnapshot",
    "IndicatorSnapshotError",
    "build_indicator_snapshot",
]
