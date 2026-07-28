"""Calibrate and freeze the hybrid drought-continuation policy."""

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

from mwangaza.probabilistic.continuation_calibration import (
    ContinuationCalibrationError,
    config_from_mapping,
    evaluate_hybrid_continuation,
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
        "--validation-manifest",
        type=Path,
        default=Path(
            "data/historical/drought-survival-evaluation/validation/manifest.json"
        ),
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/probabilistic/drought-continuation-gate.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/models/drought-continuation"),
    )
    parser.add_argument("--evaluated-at", help="Metadata timestamp excluded from run hash.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    feature_path = _resolve(args.features, "adm1-features.jsonl")
    label_path = _resolve(args.labels, "independent-labels.jsonl")
    episode_path = _resolve(args.episodes, "episodes.jsonl")
    config_payload = json.loads(args.config.read_text(encoding="utf-8"))
    config = config_from_mapping(config_payload["gate"])
    validation_manifest = _validation_manifest(
        args.validation_manifest, str(config_payload["validation_run_hash"])
    )
    print("Mwangaza drought-continuation hybrid calibration")
    print(f"Features: {feature_path}")
    print(f"Labels: {label_path}")
    print(f"Episodes: {episode_path}")
    print(f"Validation evidence: {validation_manifest['run_hash']}")
    print(f"Holdout cutoff: {config.holdout_cutoff} (rows at/after cutoff forbidden)")
    print("Routing policy: HGB+Platt 30d; phase_survival 60/90/180d")
    print(f"Output: {args.output}")
    if args.dry_run:
        return

    observations = tuple(
        item
        for item in load_phase_observations(label_path)
        if item.valid_from < config.holdout_cutoff
    )
    audited = load_actual_episodes(episode_path)
    episodes = tuple(
        item
        for item in refine_survival_episodes(audited, observations)
        if item.valid_to < config.holdout_cutoff
    )
    rows = build_survival_rows(
        feature_path,
        observations,
        episodes,
        progress=EtaProgress("Continuation calibration risk set"),
    )
    input_hashes = {
        "features": _sha256(feature_path),
        "labels": _sha256(label_path),
        "episodes": _sha256(episode_path),
        "validation_manifest": _sha256(args.validation_manifest),
        "config": _sha256(args.config),
    }
    run = evaluate_hybrid_continuation(
        rows,
        episodes,
        input_hashes=input_hashes,
        config=config,
        progress=EtaProgress("Nested calibration folds"),
    )
    oof = run.pop("oof_predictions")
    bundle = run.pop("model_bundle")
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    resolved_config_path = output / "resolved-config.json"
    oof_path = output / "oof-predictions.jsonl"
    routing_path = output / "routing.json"
    evaluation_path = output / "evaluation.json"
    _atomic_text(
        resolved_config_path,
        canonical_json(
            {
                "schema_version": config_payload["schema_version"],
                "validation_run_hash": validation_manifest["run_hash"],
                "gate": asdict(config),
            }
        )
        + "\n",
    )
    _atomic_text(oof_path, "".join(canonical_json(item) + "\n" for item in oof))
    _atomic_text(
        routing_path,
        canonical_json(
            {
                "schema_version": run["schema_version"],
                "target": run["target"],
                "run_hash": run["run_hash"],
                "global_routes": run["global_routes"],
                "regional_routes": run["regional_routes"],
                "phase_baselines": run["phase_baselines"],
            }
        )
        + "\n",
    )
    _atomic_text(evaluation_path, canonical_json(run) + "\n")
    model_path = None
    if bundle is not None:
        model_path = output / f"hgb-platt-30d-{run['run_hash'][7:19]}.joblib"
        _atomic_joblib(model_path, bundle)
    manifest = {
        "schema_version": "mwangaza.drought-continuation-model-manifest.v1",
        "evaluated_at": args.evaluated_at
        or datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "run_hash": run["run_hash"],
        "input_hashes": input_hashes,
        "holdout_evidence_hash": config.holdout_evidence_hash,
        "holdout_used_for_fit_calibration_or_gate": False,
        "risk_set_row_count": len(rows),
        "oof_prediction_count": len(oof),
        "outputs": {
            "resolved_config_sha256": _sha256(resolved_config_path),
            "oof_predictions_sha256": _sha256(oof_path),
            "routing_sha256": _sha256(routing_path),
            "evaluation_sha256": _sha256(evaluation_path),
            "model_sha256": _sha256(model_path) if model_path else None,
            "model_filename": model_path.name if model_path else None,
        },
    }
    _atomic_text(output / "manifest.json", canonical_json(manifest) + "\n")
    _print_summary(run, len(rows), len(oof), output)


def _validation_manifest(path: Path, expected_hash: str) -> dict[str, Any]:
    if not path.is_file():
        raise ContinuationCalibrationError(f"validation manifest not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("split") != "validation":
        raise ContinuationCalibrationError("only the 62F validation manifest is allowed")
    if payload.get("holdout_unlocked") is not False:
        raise ContinuationCalibrationError("validation evidence must have holdout_unlocked=false")
    if payload.get("run_hash") != expected_hash:
        raise ContinuationCalibrationError("62F validation run hash mismatch")
    return payload


def _print_summary(run: dict[str, Any], row_count: int, oof_count: int, output: Path) -> None:
    print(f"\nPre-holdout risk-set rows: {row_count}")
    print(f"OOF evaluation predictions: {oof_count}")
    print("Holdout rows used: 0")
    for candidate, metrics in run["metrics"].items():
        print(
            f"{candidate:<32} Brier={metrics['brier_score']:.6f} "
            f"BSS={metrics['brier_skill_score']:+.6f} ECE={metrics['ece']:.6f}"
        )
    print("\nHybrid routing:")
    for route in run["global_routes"]:
        reasons = ",".join(route["reason_codes"]) or "none"
        print(
            f"  {route['horizon_days']:>3}d {route['status']:<16} "
            f"candidate={route['candidate'] or 'none'} reasons={reasons}"
        )
    print(f"\nRun hash: {run['run_hash']}")
    print(f"Manifest: {output / 'manifest.json'}")


def _resolve(path: Path, filename: str) -> Path:
    resolved = path / filename if path.is_dir() else path
    if not resolved.is_file():
        raise SystemExit(f"required artifact not found: {resolved}")
    return resolved


def _sha256(path: Path | None) -> str:
    if path is None:
        raise ValueError("cannot hash an absent path")
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
        joblib.dump(value, temporary, compress=0)
        os.replace(temporary, path)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise


if __name__ == "__main__":
    main()
