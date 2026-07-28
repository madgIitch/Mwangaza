from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from mwangaza.contracts import ContractValidationError
from mwangaza.contracts.drought_continuation import DroughtContinuationProbability
from mwangaza.probabilistic.continuation_serving import (
    EXPECTED_AUDIT_RUN_HASH,
    EXPECTED_ROUTING_RUN_HASH,
    SNAPSHOT_SCHEMA_VERSION,
)
from mwangaza.probabilistic.survival import canonical_json


class DroughtContinuationServiceError(RuntimeError):
    """Raised when a materialized continuation snapshot cannot be trusted."""


@dataclass(frozen=True)
class ContinuationSnapshot:
    generated_at: str
    snapshot_hash: str
    artifact: dict[str, Any]
    items: tuple[DroughtContinuationProbability, ...]
    is_demo: bool = False


def load_continuation_snapshot(path: Path | None = None) -> ContinuationSnapshot:
    source = path or continuation_snapshot_path()
    payload = _json(source)
    if payload.get("schema_version") != SNAPSHOT_SCHEMA_VERSION:
        raise DroughtContinuationServiceError("continuation snapshot schema mismatch")
    expected_snapshot_hash = str(payload.get("snapshot_hash") or "")
    stable = dict(payload)
    stable.pop("snapshot_hash", None)
    stable.pop("generated_at", None)
    if _hash(stable) != expected_snapshot_hash:
        raise DroughtContinuationServiceError("continuation snapshot hash mismatch")
    artifact = payload.get("artifact")
    if not isinstance(artifact, dict):
        raise DroughtContinuationServiceError("continuation artifact metadata is missing")
    if artifact.get("audit_run_hash") != EXPECTED_AUDIT_RUN_HASH:
        raise DroughtContinuationServiceError("continuation audit evidence mismatch")
    if artifact.get("routing_run_hash") != EXPECTED_ROUTING_RUN_HASH:
        raise DroughtContinuationServiceError("continuation routing evidence mismatch")
    is_demo = bool(payload.get("is_demo"))
    model_failure = None if is_demo else _verify_materialized_files(source, artifact)
    values = payload.get("items")
    if not isinstance(values, list):
        raise DroughtContinuationServiceError("continuation snapshot items are missing")
    if model_failure:
        values = [_degrade_ml(item, model_failure) for item in values]
    try:
        items = tuple(DroughtContinuationProbability.from_mapping(item) for item in values)
    except (ContractValidationError, TypeError, ValueError) as exc:
        raise DroughtContinuationServiceError("continuation snapshot contract is invalid") from exc
    return ContinuationSnapshot(
        generated_at=str(payload.get("generated_at") or ""),
        snapshot_hash=expected_snapshot_hash,
        artifact=_public_artifact(artifact),
        items=tuple(
            sorted(items, key=lambda item: (item.region_id, item.as_of, item.horizon_days))
        ),
        is_demo=is_demo,
    )


def continuation_snapshot_path() -> Path:
    configured = os.environ.get("MWANGAZA_DROUGHT_CONTINUATION_SNAPSHOT")
    if configured:
        return Path(configured)
    root = Path(__file__).resolve().parents[3]
    if (
        os.environ.get("MWANGAZA_MODE", "").lower() == "demo"
        or os.environ.get("MWANGAZA_API_DATA_MODE", "").lower() == "demo"
    ):
        return root / "demo_data" / "drought-continuation-probabilities.json"
    return root / "data" / "models" / "drought-continuation-serving" / "snapshot.json"


def continuation_response(
    snapshot: ContinuationSnapshot,
    *,
    region_id: str | None = None,
    as_of: str | None = None,
    horizon_days: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    items: Iterable[DroughtContinuationProbability] = snapshot.items
    if region_id:
        normalized = region_id.strip().lower()
        items = (item for item in items if item.region_id.lower() == normalized)
    if as_of:
        requested_date = as_of[:10]
        items = (item for item in items if item.as_of[:10] == requested_date)
    if horizon_days is not None:
        items = (item for item in items if item.horizon_days == horizon_days)
    values = tuple(items)
    page = values[offset : offset + limit]
    return {
        "snapshot_schema_version": SNAPSHOT_SCHEMA_VERSION,
        "generated_at": snapshot.generated_at,
        "snapshot_hash": snapshot.snapshot_hash,
        "artifact": snapshot.artifact,
        "availability": "available",
        "is_demo": snapshot.is_demo,
        "items": [item.to_dict() for item in page],
        "limit": limit,
        "offset": offset,
        "total": len(values),
    }


def unavailable_response(reason_code: str, *, limit: int, offset: int) -> dict[str, Any]:
    return {
        "snapshot_schema_version": SNAPSHOT_SCHEMA_VERSION,
        "generated_at": None,
        "snapshot_hash": None,
        "artifact": None,
        "availability": "unavailable",
        "reason_codes": [reason_code],
        "items": [],
        "limit": limit,
        "offset": offset,
        "total": 0,
    }


def _verify_materialized_files(source: Path, artifact: dict[str, Any]) -> str | None:
    manifest_path = source.parent / "manifest.json"
    try:
        manifest = _json(manifest_path)
    except DroughtContinuationServiceError:
        return "serving_manifest_unavailable"
    outputs = manifest.get("outputs")
    if not isinstance(outputs, dict):
        return "serving_manifest_invalid"
    if manifest.get("audit_run_hash") != EXPECTED_AUDIT_RUN_HASH:
        return "audit_hash_mismatch"
    if manifest.get("routing_run_hash") != EXPECTED_ROUTING_RUN_HASH:
        return "routing_hash_mismatch"
    if outputs.get("snapshot_sha256") != _sha256(source):
        return "snapshot_file_hash_mismatch"
    filename = outputs.get("model_filename")
    expected = outputs.get("model_sha256")
    if not isinstance(filename, str) or Path(filename).name != filename:
        return "model_filename_invalid"
    model_path = source.parent / filename
    if not model_path.is_file():
        return "model_artifact_missing"
    if _sha256(model_path) != expected or artifact.get("bundle_sha256") != expected:
        return "model_artifact_hash_mismatch"
    return None


def _degrade_ml(item: Any, reason: str) -> Any:
    if not isinstance(item, dict):
        return item
    if item.get("status") == "not_applicable":
        return item
    result = dict(item)
    estimates = []
    for value in item.get("estimates", []):
        if not isinstance(value, dict) or value.get("kind") != "experimental_ml_prediction":
            estimates.append(value)
            continue
        estimate = dict(value)
        estimate.update(
            {
                "status": "unavailable",
                "probability": None,
                "quality": {"status": "blocked"},
                "reason_codes": [reason],
                "drivers": [],
            }
        )
        estimates.append(estimate)
    result["estimates"] = estimates
    result["status"] = (
        "available"
        if any(
            isinstance(value, dict) and value.get("status") == "available" for value in estimates
        )
        else "unavailable"
    )
    if result["status"] == "unavailable":
        result["reason_codes"] = ["all_estimates_unavailable"]
    return result


def _public_artifact(value: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "bundle_run_hash",
        "bundle_sha256",
        "audit_run_hash",
        "routing_run_hash",
        "routing_sha256",
    }
    return {name: value[name] for name in sorted(allowed) if name in value}


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise DroughtContinuationServiceError("continuation artifact unavailable") from exc
    if not isinstance(value, dict):
        raise DroughtContinuationServiceError("continuation artifact must be an object")
    return value


def _hash(value: object) -> str:
    return f"sha256:{hashlib.sha256(canonical_json(value).encode()).hexdigest()}"


def _sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


__all__ = [
    "ContinuationSnapshot",
    "DroughtContinuationServiceError",
    "continuation_response",
    "continuation_snapshot_path",
    "load_continuation_snapshot",
    "unavailable_response",
]
