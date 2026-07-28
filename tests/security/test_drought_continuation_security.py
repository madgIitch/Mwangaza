from __future__ import annotations

import hashlib
import json
from pathlib import Path

from mwangaza.probabilistic.survival import canonical_json
from mwangaza.services.drought_continuation import (
    continuation_response,
    load_continuation_snapshot,
)


def test_corrupt_model_blocks_ml_but_preserves_reference_without_path_leak(
    tmp_path: Path,
) -> None:
    payload = json.loads(
        Path("demo_data/drought-continuation-probabilities.json").read_text(encoding="utf-8")
    )
    payload.pop("is_demo")
    stable = dict(payload)
    stable.pop("snapshot_hash")
    stable.pop("generated_at")
    payload["snapshot_hash"] = _hash(stable)
    snapshot_path = tmp_path / "snapshot.json"
    snapshot_path.write_text(canonical_json(payload) + "\n", encoding="utf-8")
    model_path = tmp_path / "model.joblib"
    model_path.write_bytes(b"corrupt")
    manifest = {
        "audit_run_hash": payload["artifact"]["audit_run_hash"],
        "routing_run_hash": payload["artifact"]["routing_run_hash"],
        "outputs": {
            "snapshot_sha256": _sha256(snapshot_path),
            "model_filename": model_path.name,
            "model_sha256": payload["artifact"]["bundle_sha256"],
        },
    }
    (tmp_path / "manifest.json").write_text(canonical_json(manifest) + "\n", encoding="utf-8")

    snapshot = load_continuation_snapshot(snapshot_path)
    response = continuation_response(
        snapshot,
        region_id="adm1-ke-43",
        horizon_days=30,
    )
    ml, baseline = response["items"][0]["estimates"]
    serialized = json.dumps(response)

    assert ml["status"] == "unavailable"
    assert ml["reason_codes"] == ["model_artifact_hash_mismatch"]
    assert baseline["status"] == "available"
    assert response["items"][0]["status"] == "available"
    assert str(tmp_path) not in serialized
    assert "model.joblib" not in serialized


def _hash(value: object) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode()).hexdigest()


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
