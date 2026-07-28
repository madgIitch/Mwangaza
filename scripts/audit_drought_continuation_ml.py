"""Audit whether 30-day drought-continuation ML is implemented fairly."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mwangaza.probabilistic.ml_sanity_audit import (
    audit_config_from_mapping,
    audit_ml_sanity,
    hgb_grid_from_sequence,
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
        "--config",
        type=Path,
        default=Path("config/probabilistic/drought-continuation-ml-audit.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/models/drought-continuation-ml-audit"),
    )
    parser.add_argument("--evaluated-at", help="Metadata timestamp excluded from run hash.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    feature_path = _resolve(args.features, "adm1-features.jsonl")
    label_path = _resolve(args.labels, "independent-labels.jsonl")
    episode_path = _resolve(args.episodes, "episodes.jsonl")
    payload = json.loads(args.config.read_text(encoding="utf-8"))
    config = audit_config_from_mapping(payload["audit"])
    hgb_grid = hgb_grid_from_sequence(payload["hgb_grid"])
    print("Mwangaza 30-day continuation ML sanity audit")
    print(f"Features: {feature_path}")
    print(f"Labels: {label_path}")
    print(f"Episodes: {episode_path}")
    print(f"HGB configurations: {len(hgb_grid)}")
    print(f"Hazard C values: {len(config.hazard_c_grid)}")
    print(f"Bootstrap episode samples: {config.bootstrap_iterations}")
    print(f"Holdout cutoff: {config.holdout_cutoff} (strictly forbidden)")
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
        progress=EtaProgress("ML audit risk set"),
    )
    input_hashes = {
        "features": _sha256(feature_path),
        "labels": _sha256(label_path),
        "episodes": _sha256(episode_path),
        "config": _sha256(args.config),
    }
    run = audit_ml_sanity(
        rows,
        episodes,
        hgb_grid=hgb_grid,
        input_hashes=input_hashes,
        config=config,
        progress=EtaProgress("ML sanity audit"),
    )
    oof = run.pop("oof_predictions")
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    config_path = output / "resolved-config.json"
    selections_path = output / "fold-selections.json"
    oof_path = output / "oof-predictions.jsonl"
    metrics_path = output / "metrics.json"
    bootstrap_path = output / "bootstrap.json"
    audit_path = output / "audit.json"
    _atomic_text(config_path, canonical_json(payload) + "\n")
    _atomic_text(
        selections_path,
        canonical_json({"fold_selections": run["fold_selections"]}) + "\n",
    )
    _atomic_text(oof_path, "".join(canonical_json(item) + "\n" for item in oof))
    _atomic_text(
        metrics_path,
        canonical_json(
            {
                "candidates": run["candidates"],
                "recommended_candidate": run["recommended_candidate"],
                "recommendation": run["recommendation"],
            }
        )
        + "\n",
    )
    _atomic_text(bootstrap_path, canonical_json(run["bootstrap"]) + "\n")
    _atomic_text(audit_path, canonical_json(run) + "\n")
    manifest = {
        "schema_version": "mwangaza.drought-continuation-ml-audit-manifest.v1",
        "evaluated_at": args.evaluated_at or datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "run_hash": run["run_hash"],
        "input_hashes": input_hashes,
        "holdout_rows_used": 0,
        "risk_set_row_count": len(rows),
        "oof_prediction_count": len(oof),
        "missing_indicator_columns_by_fold": [
            {
                "evaluation_year": selection["evaluation_year"],
                "hgb": selection["missing_indicator_columns"]["hgb"],
                "hazard": selection["missing_indicator_columns"]["hazard"],
            }
            for selection in run["fold_selections"]
        ],
        "outputs": {
            "resolved_config_sha256": _sha256(config_path),
            "fold_selections_sha256": _sha256(selections_path),
            "oof_predictions_sha256": _sha256(oof_path),
            "metrics_sha256": _sha256(metrics_path),
            "bootstrap_sha256": _sha256(bootstrap_path),
            "audit_sha256": _sha256(audit_path),
        },
    }
    _atomic_text(output / "manifest.json", canonical_json(manifest) + "\n")
    _print_summary(run, len(rows), len(oof), output)


def _print_summary(run: dict[str, Any], rows: int, oof: int, output: Path) -> None:
    print(f"\nPre-holdout risk-set rows: {rows}")
    print(f"OOF rows: {oof}")
    print("Holdout rows used: 0")
    print("\nEpisode-weighted 30-day results:")
    for item in run["candidates"]:
        metrics = item["metrics"]
        bootstrap = item["bootstrap"]
        print(
            f"  {item['candidate']:<42} "
            f"Brier={metrics['episode_weighted_brier']:.6f} "
            f"BSS={metrics['episode_weighted_bss']:+.6f} "
            f"ECE={metrics['episode_weighted_ece']:.6f} "
            f"delta95=[{bootstrap['lower_95']:+.6f}, {bootstrap['upper_95']:+.6f}] "
            f"verdict={item['verdict']}"
        )
    print(f"\nRecommendation: {run['recommendation']} ({run['recommended_candidate']})")
    print(f"Run hash: {run['run_hash']}")
    print(f"Manifest: {output / 'manifest.json'}")


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


if __name__ == "__main__":
    main()
