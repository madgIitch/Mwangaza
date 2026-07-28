"""Evaluate ADM1 drought candidates against validated real hazard episodes."""

from __future__ import annotations

import argparse
import hashlib
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from mwangaza.probabilistic.episode_evaluation import (
    EpisodeEvaluationConfig,
    build_evaluation_rows,
    canonical_json,
    evaluate_candidates,
    load_actual_episodes,
    load_hazard_observations,
)
from mwangaza.probabilistic.progress import EtaProgress


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
        default=Path("data/historical/drought-episode-evaluation"),
    )
    parser.add_argument("--first-test-year", type=int, default=2019)
    parser.add_argument("--min-train-rows", type=int, default=100)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--evaluated-at", help="Metadata timestamp; excluded from run hash.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    feature_path = _resolve(args.features, "adm1-features.jsonl")
    label_path = _resolve(args.labels, "independent-labels.jsonl")
    episode_path = _resolve(args.episodes, "episodes.jsonl")
    print(f"Features: {feature_path}")
    print(f"Labels: {label_path}")
    print(f"Episodes: {episode_path}")
    print("Horizons: 10, 20, 30 days")
    print(f"Output: {args.output}")
    if args.dry_run:
        return

    observations = load_hazard_observations(label_path)
    episodes = load_actual_episodes(episode_path)
    print(f"Validated hazard observations: {len(observations)}")
    print(f"Actual episodes: {len(episodes)}")
    evaluation_rows = build_evaluation_rows(
        feature_path,
        observations,
        episodes,
        progress=EtaProgress("Episode target alignment"),
    )
    print(f"Known evaluation rows: {len(evaluation_rows)}")
    run = evaluate_candidates(
        evaluation_rows,
        episodes,
        EpisodeEvaluationConfig(
            first_test_year=args.first_test_year,
            min_train_rows=args.min_train_rows,
            seed=args.seed,
        ),
        progress=EtaProgress("Episode candidate evaluation"),
    )

    predictions = run.pop("predictions")
    predicted_episodes = run.pop("predicted_episodes")
    args.output.mkdir(parents=True, exist_ok=True)
    predictions_path = args.output / "oof-predictions.jsonl"
    predicted_path = args.output / "predicted-episodes.jsonl"
    evaluation_path = args.output / "evaluation.json"
    _atomic_text(predictions_path, "".join(canonical_json(item) + "\n" for item in predictions))
    _atomic_text(predicted_path, "".join(canonical_json(item) + "\n" for item in predicted_episodes))
    _atomic_text(evaluation_path, canonical_json(run) + "\n")
    manifest = {
        "schema_version": "mwangaza.drought-episode-evaluation-manifest.v1",
        "evaluated_at": args.evaluated_at
        or datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "input_hashes": {
            "features": _sha256(feature_path),
            "labels": _sha256(label_path),
            "episodes": _sha256(episode_path),
        },
        "evaluation_row_count": len(evaluation_rows),
        "actual_episode_count": len(episodes),
        "prediction_count": len(predictions),
        "predicted_episode_count": len(predicted_episodes),
        "evaluation_sha256": _sha256(evaluation_path),
        "predictions_sha256": _sha256(predictions_path),
        "predicted_episodes_sha256": _sha256(predicted_path),
        "run_hash": run["run_hash"],
    }
    _atomic_text(args.output / "manifest.json", canonical_json(manifest) + "\n")

    for horizon in run["results"]:
        print(
            f"\nHorizon {horizon['horizon_days']} days "
            f"(baseline={horizon['baseline_champion']})"
        )
        for candidate in horizon["candidates"]:
            print(
                f"  {candidate['candidate']:<24} "
                f"Brier={candidate['brier_score']:.6f} "
                f"F1={candidate['event_f1']:.3f} "
                f"recall={candidate['event_recall']:.3f} "
                f"false_alarms={candidate['false_alarm_count']} "
                f"status={candidate['skill_status']}"
            )
    print(f"\nRun hash: {run['run_hash']}")
    print(f"Manifest: {args.output / 'manifest.json'}")
    print("Serving remains disabled; this sprint only evaluates independent episode skill.")


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
