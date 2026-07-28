"""Evaluate how long an already-active drought episode is likely to continue."""

from __future__ import annotations

import argparse
import hashlib
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from mwangaza.probabilistic.progress import EtaProgress
from mwangaza.probabilistic.survival import (
    SurvivalConfig,
    SurvivalEvaluationError,
    build_survival_rows,
    canonical_json,
    evaluate_survival,
    load_actual_episodes,
    load_phase_observations,
    refine_survival_episodes,
    risk_set_payload,
    split_survival_rows,
    validate_holdout_unlock,
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
        "--output",
        type=Path,
        default=Path("data/historical/drought-survival-evaluation"),
    )
    parser.add_argument("--min-train-rows", type=int, default=80)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--unlock-final-holdout", action="store_true")
    parser.add_argument("--frozen-validation-run-hash")
    parser.add_argument("--evaluated-at", help="Metadata timestamp excluded from run hash.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    feature_path = _resolve(args.features, "adm1-features.jsonl")
    label_path = _resolve(args.labels, "independent-labels.jsonl")
    episode_path = _resolve(args.episodes, "episodes.jsonl")
    split = "holdout" if args.unlock_final_holdout else "validation"
    print(f"Features: {feature_path}")
    print(f"Labels: {label_path}")
    print(f"Episodes: {episode_path}")
    print("Continuation horizons: 30, 60, 90, 180 days")
    print(f"Evaluation split: {split}")
    print(f"Output: {args.output}")
    if args.dry_run:
        return

    frozen_hash = None
    if split == "holdout":
        try:
            frozen_hash = validate_holdout_unlock(
                args.output, args.frozen_validation_run_hash
            )
        except SurvivalEvaluationError as exc:
            parser.error(str(exc))

    observations = load_phase_observations(label_path)
    audited_episodes = load_actual_episodes(episode_path)
    episodes = refine_survival_episodes(audited_episodes, observations)
    print(f"Validated phase observations: {len(observations)}")
    print(f"Audited episodes: {len(audited_episodes)}")
    print(f"Strict survival episodes: {len(episodes)}")
    rows = build_survival_rows(
        feature_path,
        observations,
        episodes,
        progress=EtaProgress("Survival risk-set alignment"),
    )
    config = SurvivalConfig(min_train_rows=args.min_train_rows, seed=args.seed)
    splits = split_survival_rows(rows, episodes, config)
    print(f"Risk-set rows: {len(rows)}")
    print(
        "Episode splits: "
        + ", ".join(
            f"{name}={len({row.episode_id for row in split_rows})}"
            for name, split_rows in sorted(splits.items())
        )
    )
    run = evaluate_survival(
        rows,
        episodes,
        split=split,
        config=config,
        ablation=split == "validation",
        progress=EtaProgress("Survival candidate evaluation"),
    )
    predictions = run.pop("predictions")
    split_dir = args.output / split
    split_dir.mkdir(parents=True, exist_ok=True)
    risk_set_path = args.output / "risk-set.jsonl"
    predictions_path = split_dir / "predictions.jsonl"
    evaluation_path = split_dir / "evaluation.json"
    input_hashes = {
        "features": _sha256(feature_path),
        "labels": _sha256(label_path),
        "episodes": _sha256(episode_path),
    }
    _atomic_text(
        risk_set_path,
        "".join(canonical_json(risk_set_payload(row, input_hashes)) + "\n" for row in rows),
    )
    _atomic_text(
        predictions_path,
        "".join(canonical_json(item) + "\n" for item in predictions),
    )
    _atomic_text(evaluation_path, canonical_json(run) + "\n")
    manifest = {
        "schema_version": "mwangaza.drought-survival-evaluation-manifest.v1",
        "split": split,
        "evaluated_at": args.evaluated_at
        or datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "holdout_unlocked": split == "holdout",
        "frozen_validation_run_hash": frozen_hash,
        "input_hashes": input_hashes,
        "risk_set_row_count": len(rows),
        "risk_set_sha256": _sha256(risk_set_path),
        "prediction_count": len(predictions),
        "predictions_sha256": _sha256(predictions_path),
        "evaluation_sha256": _sha256(evaluation_path),
        "run_hash": run["run_hash"],
    }
    _atomic_text(split_dir / "manifest.json", canonical_json(manifest) + "\n")

    print(f"\nBaseline champion: {run['baseline_champion']}")
    for candidate in run["candidates"]:
        print(
            f"{candidate['candidate']:<24} "
            f"IBS={candidate['integrated_brier']:.6f} "
            f"recovery_MAE={_format(candidate['mean_absolute_recovery_error_days'])} "
            f"status={candidate['skill_status']}"
        )
        print(
            "  "
            + " | ".join(
                f"{item['horizon_days']}d Brier={item['brier_score']:.6f}"
                for item in candidate["horizons"]
            )
        )
    if run["ablation"]:
        print("\nLogistic ablation (positive delta means the family helps):")
        for item in sorted(
            run["ablation"], key=lambda value: value["delta_integrated_brier"], reverse=True
        ):
            print(
                f"  {item['excluded_family']:<24} "
                f"delta_IBS={item['delta_integrated_brier']:+.6f}"
            )
    print(f"\nRun hash: {run['run_hash']}")
    print(f"Manifest: {split_dir / 'manifest.json'}")
    if split == "validation":
        print("Final holdout remains sealed. Freeze this run before unlocking it.")
    else:
        print("Final holdout opened once; do not tune models from this result.")


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


def _format(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1f}d"


if __name__ == "__main__":
    main()
