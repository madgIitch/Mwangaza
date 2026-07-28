"""Freeze the 30-day experimental hazard and materialize dual probabilities."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib

from mwangaza.probabilistic.continuation_serving import (
    AuditEvidence,
    ContinuationServingError,
    audit_evidence_from_mapping,
    freeze_hazard_bundle,
    materialize_probability_snapshot,
    serving_config_from_mapping,
)
from mwangaza.probabilistic.progress import EtaProgress
from mwangaza.probabilistic.survival import (
    build_survival_rows,
    canonical_json,
    load_actual_episodes,
    load_phase_observations,
    refine_survival_episodes,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--features",
        type=Path,
        default=Path("data/historical/adm1-probabilistic-features"),
    )
    parser.add_argument(
        "--labels",
        type=Path,
        default=Path("data/historical/drought-hazard-labels"),
    )
    parser.add_argument(
        "--episodes",
        type=Path,
        default=Path("data/historical/drought-hazard-audit"),
    )
    parser.add_argument(
        "--audit",
        type=Path,
        default=Path("data/models/drought-continuation-ml-audit"),
    )
    parser.add_argument(
        "--routing",
        type=Path,
        default=Path("data/models/drought-continuation"),
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/probabilistic/drought-continuation-serving.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/models/drought-continuation-serving"),
    )
    parser.add_argument("--evaluated-at", help="Metadata timestamp excluded from run hash.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    feature_path = _resolve(args.features, "adm1-features.jsonl")
    label_path = _resolve(args.labels, "independent-labels.jsonl")
    episode_path = _resolve(args.episodes, "episodes.jsonl")
    audit_manifest_path = _resolve(args.audit, "manifest.json")
    audit_metrics_path = _resolve(args.audit, "metrics.json")
    routing_path = _resolve(args.routing, "routing.json")
    routing_manifest_path = _resolve(args.routing, "manifest.json")
    payload = json.loads(args.config.read_text(encoding="utf-8"))
    config = serving_config_from_mapping(payload["hazard"])
    evidence = audit_evidence_from_mapping(payload["evidence"])
    audit_manifest = _json(audit_manifest_path)
    audit_metrics = _json(audit_metrics_path)
    routing = _json(routing_path)
    routing_manifest = _json(routing_manifest_path)
    _verify_evidence(
        evidence,
        audit_manifest,
        audit_metrics,
        routing,
        routing_manifest,
        routing_path,
    )

    print("Mwangaza drought-continuation serving materialization")
    print("30d: experimental discrete-time logistic hazard + historical reference")
    print("60/90/180d: historical reference only")
    print(f"Frozen hazard C: {config.c}")
    print(f"Training cutoff: {config.holdout_cutoff} (strictly excluded)")
    print(f"63B evidence: {evidence.audit_run_hash} ({evidence.validation_status})")
    print(f"Output: {args.output}")
    if args.dry_run:
        return

    observations = load_phase_observations(label_path)
    episodes = refine_survival_episodes(load_actual_episodes(episode_path), observations)
    rows = build_survival_rows(
        feature_path,
        observations,
        episodes,
        progress=EtaProgress("Continuation serving risk set"),
    )
    input_hashes = {
        "features": _sha256(feature_path),
        "labels": _sha256(label_path),
        "episodes": _sha256(episode_path),
        "audit_manifest": _sha256(audit_manifest_path),
        "audit_metrics": _sha256(audit_metrics_path),
        "routing": _sha256(routing_path),
        "routing_manifest": _sha256(routing_manifest_path),
        "config": _sha256(args.config),
    }
    bundle = freeze_hazard_bundle(
        rows,
        episodes,
        evidence=evidence,
        input_hashes=input_hashes,
        config=config,
    )
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    model_path = output / f"hazard-30d-{bundle.run_hash[7:19]}.joblib"
    _atomic_joblib(model_path, bundle)
    model_sha256 = _sha256(model_path)
    generated_at = args.evaluated_at or datetime.now(UTC).isoformat().replace("+00:00", "Z")
    snapshot = materialize_probability_snapshot(
        bundle,
        rows,
        observations,
        routing,
        bundle_sha256=model_sha256,
        routing_sha256=_sha256(routing_path),
        generated_at=generated_at,
        config=config,
    )
    config_path = output / "resolved-config.json"
    snapshot_path = output / "snapshot.json"
    _atomic_text(
        config_path,
        canonical_json(
            {
                "schema_version": payload["schema_version"],
                "hazard": asdict(config),
                "evidence": asdict(evidence),
            }
        )
        + "\n",
    )
    _atomic_text(snapshot_path, canonical_json(snapshot) + "\n")
    ml_available = sum(
        estimate["status"] == "available"
        for item in snapshot["items"]
        for estimate in item["estimates"]
        if estimate["kind"] == "experimental_ml_prediction"
    )
    manifest = {
        "schema_version": "mwangaza.drought-continuation-serving-manifest.v1",
        "generated_at": generated_at,
        "run_hash": bundle.run_hash,
        "snapshot_hash": snapshot["snapshot_hash"],
        "audit_run_hash": evidence.audit_run_hash,
        "routing_run_hash": evidence.routing_run_hash,
        "holdout_used_for_fit": False,
        "trained_through": bundle.trained_through,
        "training_row_count": sum(bundle.training_region_rows.values()),
        "training_region_count": len(bundle.training_region_rows),
        "materialized_item_count": len(snapshot["items"]),
        "experimental_ml_available_count": ml_available,
        "input_hashes": input_hashes,
        "outputs": {
            "model_filename": model_path.name,
            "model_sha256": model_sha256,
            "snapshot_filename": snapshot_path.name,
            "snapshot_sha256": _sha256(snapshot_path),
            "resolved_config_sha256": _sha256(config_path),
        },
    }
    _atomic_text(output / "manifest.json", canonical_json(manifest) + "\n")
    print(f"\nRisk-set rows: {len(rows)}")
    print(f"Training rows pre-2024: {sum(bundle.training_region_rows.values())}")
    print(f"Training regions: {len(bundle.training_region_rows)}")
    print(f"Materialized items: {len(snapshot['items'])}")
    print(f"Experimental ML available: {ml_available}")
    print("Holdout rows used for fit: 0")
    print(f"Run hash: {bundle.run_hash}")
    print(f"Manifest: {output / 'manifest.json'}")


def _verify_evidence(
    evidence: AuditEvidence,
    audit_manifest: dict[str, Any],
    audit_metrics: dict[str, Any],
    routing: dict[str, Any],
    routing_manifest: dict[str, Any],
    routing_path: Path,
) -> None:
    if audit_manifest.get("run_hash") != evidence.audit_run_hash:
        raise ContinuationServingError("63B audit manifest run hash mismatch")
    if audit_manifest.get("holdout_rows_used") != 0:
        raise ContinuationServingError("63B evidence used forbidden holdout rows")
    candidate = next(
        (
            item
            for item in audit_metrics.get("candidates", [])
            if item.get("candidate") == "discrete_time_logistic_hazard"
        ),
        None,
    )
    if not isinstance(candidate, dict) or candidate.get("verdict") != "inconclusive":
        raise ContinuationServingError("63B hazard evidence is missing or relabelled")
    metrics = candidate.get("metrics", {})
    bootstrap = candidate.get("bootstrap", {})
    expected = {
        "episode_weighted_brier": evidence.episode_weighted_brier,
        "episode_weighted_bss": evidence.episode_weighted_brier_skill_score,
        "episode_weighted_ece": evidence.episode_weighted_ece,
    }
    if any(metrics.get(name) != value for name, value in expected.items()):
        raise ContinuationServingError("63B metric evidence mismatch")
    if (
        bootstrap.get("lower_95") != evidence.bootstrap_delta_brier_lower_95
        or bootstrap.get("upper_95") != evidence.bootstrap_delta_brier_upper_95
        or candidate.get("improved_outer_folds") != evidence.improved_outer_folds
    ):
        raise ContinuationServingError("63B interval or fold evidence mismatch")
    if routing.get("run_hash") != evidence.routing_run_hash:
        raise ContinuationServingError("63 routing run hash mismatch")
    if routing_manifest.get("run_hash") != evidence.routing_run_hash:
        raise ContinuationServingError("63 routing manifest run hash mismatch")
    if routing_manifest.get("outputs", {}).get("routing_sha256") != _sha256(routing_path):
        raise ContinuationServingError("63 routing file hash mismatch")


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ContinuationServingError(f"required JSON artifact is invalid: {path.name}") from exc
    if not isinstance(value, dict):
        raise ContinuationServingError(f"required JSON artifact is not an object: {path.name}")
    return value


def _resolve(path: Path, filename: str) -> Path:
    resolved = path / filename if path.is_dir() else path
    if not resolved.is_file():
        raise SystemExit(f"required artifact not found: {resolved}")
    return resolved


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise


def _atomic_joblib(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    os.close(handle)
    try:
        joblib.dump(value, temporary)
        with Path(temporary).open("r+b") as stream:
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise


if __name__ == "__main__":
    main()
