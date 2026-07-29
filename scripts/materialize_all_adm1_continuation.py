"""Materialize satellite drought-continuation probabilities for every IGAD ADM1."""

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

import joblib  # type: ignore[import-untyped]

from mwangaza.probabilistic.progress import EtaProgress
from mwangaza.probabilistic.satellite_continuation import (
    SatelliteContinuationError,
    build_satellite_samples,
    config_from_mapping,
    derive_satellite_states,
    freeze_satellite_bundle,
    load_feature_payloads,
    materialize_satellite_snapshot,
    validate_against_ndma,
)
from mwangaza.probabilistic.survival import canonical_json
from mwangaza.regions import ADM1_LEVEL, list_regions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--features",
        type=Path,
        default=Path("data/historical/adm1-probabilistic-features"),
    )
    parser.add_argument(
        "--ndma-labels",
        type=Path,
        default=Path("data/historical/drought-hazard-labels"),
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/probabilistic/satellite-drought-continuation.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/models/drought-continuation-serving"),
    )
    parser.add_argument("--evaluated-at", help="Metadata timestamp excluded from stable hashes.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config_payload = _json(args.config)
    config = config_from_mapping(config_payload)
    feature_path = args.features / "adm1-features.jsonl" if args.features.is_dir() else args.features
    manifest_path = args.features / "manifest.json" if args.features.is_dir() else args.features.parent / "manifest.json"
    regions = tuple(list_regions(level=ADM1_LEVEL, include_administrative=True))
    region_ids = tuple(region.id for region in regions)
    print("Mwangaza all-ADM1 satellite drought continuation")
    print(f"Catalog: {len(region_ids)} ADM1 ({sum(region.iso3 == 'KEN' for region in regions)} Kenya)")
    print(f"Features: {feature_path}")
    print(f"Output: {args.output}")
    print("Target: observed_drought_condition_continues")
    print("NDMA: external validation only; FEWS NET: impact evidence only")
    if args.dry_run:
        return

    progress = EtaProgress("All-ADM1 continuation", percent_step=10)
    total_steps = 7
    progress(0, total_steps)
    payloads = load_feature_payloads(feature_path)
    progress(1, total_steps)
    states = derive_satellite_states(payloads, config, expected_region_ids=region_ids)
    progress(2, total_steps)
    samples = build_satellite_samples(states, config.horizons_days)
    progress(3, total_steps)
    input_hashes = {
        "features": _sha256(feature_path),
        "feature_manifest": _sha256(manifest_path),
        "config": _sha256(args.config),
    }
    bundle = freeze_satellite_bundle(samples, input_hashes=input_hashes, config=config)
    progress(4, total_steps)
    ndma_validation = validate_against_ndma(states, args.ndma_labels)
    generated_at = args.evaluated_at or datetime.now(UTC).isoformat().replace("+00:00", "Z")
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    model_path = output / f"satellite-continuation-{bundle.run_hash[7:19]}.joblib"
    _atomic_joblib(model_path, bundle)
    model_sha256 = _sha256(model_path)
    progress(5, total_steps)
    snapshot = materialize_satellite_snapshot(
        bundle,
        states,
        generated_at=generated_at,
        bundle_sha256=model_sha256,
        expected_region_ids=region_ids,
        external_validation=ndma_validation,
    )
    snapshot_path = output / "snapshot.json"
    config_path = output / "resolved-config.json"
    _atomic_text(snapshot_path, canonical_json(snapshot) + "\n")
    _atomic_text(
        config_path,
        canonical_json({
            "schema_version": config_payload["schema_version"],
            "condition": asdict(config),
        }) + "\n",
    )
    progress(6, total_steps)
    active_regions = {
        item["region_id"] for item in snapshot["items"]
        if item["current_drought_status"] == "active"
    }
    manifest: dict[str, Any] = {
        "schema_version": "mwangaza.satellite-continuation-serving-manifest.v1",
        "generated_at": generated_at,
        "analysis_as_of": snapshot["analysis_as_of"],
        "run_hash": bundle.run_hash,
        "snapshot_hash": snapshot["snapshot_hash"],
        "target": snapshot["target"],
        "state_version": bundle.state_version,
        "catalog_region_count": len(region_ids),
        "kenya_region_count": sum(region.iso3 == "KEN" for region in regions),
        "materialized_item_count": len(snapshot["items"]),
        "active_region_count": len(active_regions),
        "training_row_count": bundle.training_row_count,
        "training_region_count": len(bundle.training_regions),
        "trained_through": bundle.trained_through,
        "validation": bundle.validation,
        "external_validation": ndma_validation,
        "source_roles": {
            "gee": "state_target_and_predictors",
            "ndma": "external_validation_only",
            "fews_net": "acute_food_insecurity_impact_only",
        },
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
    progress(7, total_steps)
    print(f"Rows: {len(payloads)}")
    print(f"Satellite samples: {len(samples)}")
    print(f"Training rows: {bundle.training_row_count}")
    print(f"Training regions: {len(bundle.training_regions)}")
    print(f"Current ADM1 evaluated: {len(region_ids)}/121")
    print(f"Kenya ADM1 evaluated: {sum(region.iso3 == 'KEN' for region in regions)}/47")
    print(f"Active conditions: {len(active_regions)}")
    print(f"Materialized items: {len(snapshot['items'])}/484")
    print(f"Analysis as of: {snapshot['analysis_as_of']}")
    print(f"ML qualified: {bool(bundle.validation.get('qualified_for_experimental_serving'))}")
    print(f"Run hash: {bundle.run_hash}")


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SatelliteContinuationError(f"invalid JSON artifact: {path.name}") from exc
    if not isinstance(value, dict):
        raise SatelliteContinuationError(f"JSON artifact must be an object: {path.name}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _atomic_text(path: Path, content: str) -> None:
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
