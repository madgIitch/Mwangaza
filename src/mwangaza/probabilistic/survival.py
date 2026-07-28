from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_extraction import DictVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from mwangaza.probabilistic.episode_evaluation import ActualEpisode, load_actual_episodes

ACTIVE_PHASES = frozenset({"phase_alert", "phase_alarm", "phase_emergency"})
INACTIVE_PHASES = frozenset({"phase_normal", "phase_recovery"})
VALIDATED_STATUSES = frozenset({"validated", "source_unit_explicit"})
HORIZONS = (30, 60, 90, 180)
BASELINES = ("always_active", "empirical_survival", "phase_survival")
ML_MODELS = ("logistic_regression", "hist_gradient_boosting")
CANDIDATES = (*BASELINES, *ML_MODELS)
FEATURE_FAMILIES = (
    "rainfall_drought",
    "vegetation",
    "soil_water",
    "atmospheric_demand",
    "season_region",
)
SCHEMA_VERSION = "mwangaza.drought-continuation-survival.v1"
MONOTONIC_VERSION = "cumulative-min-30-60-90-180-v1"


class SurvivalEvaluationError(RuntimeError):
    """Raised when continuation evaluation would be unsafe or ambiguous."""


@dataclass(frozen=True)
class SurvivalConfig:
    horizons_days: tuple[int, ...] = HORIZONS
    train_cutoff: str = "2021-01-01"
    holdout_cutoff: str = "2024-01-01"
    min_train_rows: int = 80
    min_class_count: int = 2
    min_test_episodes: int = 5
    threshold: float = 0.5
    elapsed_bin_days: int = 30
    seed: int = 2026

    def __post_init__(self) -> None:
        if tuple(sorted(self.horizons_days)) != self.horizons_days:
            raise SurvivalEvaluationError("horizons_days must be ordered")
        if len(set(self.horizons_days)) != len(self.horizons_days):
            raise SurvivalEvaluationError("horizons_days must be unique")
        if date.fromisoformat(self.train_cutoff) >= date.fromisoformat(self.holdout_cutoff):
            raise SurvivalEvaluationError("train_cutoff must precede holdout_cutoff")
        if self.min_train_rows < 4 or self.min_class_count < 1:
            raise SurvivalEvaluationError("training support thresholds are invalid")
        if not 0 < self.threshold < 1 or self.elapsed_bin_days < 1:
            raise SurvivalEvaluationError("threshold or elapsed bin is invalid")


@dataclass(frozen=True)
class PhaseObservation:
    label_id: str
    region_id: str
    valid_from: str
    valid_to: str
    issued_at: str
    active: bool
    phase: str
    trend: str


@dataclass(frozen=True)
class SurvivalRow:
    sample_id: str
    episode_id: str
    region_id: str
    as_of: str
    period_end: str
    elapsed_days: int
    left_censored: bool
    current_phase: str
    current_trend: str
    features: dict[str, float | str | None]
    targets: dict[int, int | None]
    target_reasons: dict[int, str]


@dataclass(frozen=True)
class SurvivalPrediction:
    split: str
    candidate: str
    sample_id: str
    episode_id: str
    region_id: str
    as_of: str
    horizon_days: int
    actual: int | None
    probability: float
    monotonic_version: str


def load_phase_observations(path: Path) -> tuple[PhaseObservation, ...]:
    source = path / "independent-labels.jsonl" if path.is_dir() else path
    result = []
    for item in _jsonl(source):
        value = str(item.get("normalized_value"))
        if (
            item.get("label_semantics") != "drought_hazard_event"
            or item.get("review_status") not in VALIDATED_STATUSES
            or not item.get("adm1_region_id")
            or value not in ACTIVE_PHASES | INACTIVE_PHASES
        ):
            continue
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        result.append(
            PhaseObservation(
                label_id=str(item["label_id"]),
                region_id=str(item["adm1_region_id"]),
                valid_from=str(item["valid_from"]),
                valid_to=str(item["valid_to"]),
                issued_at=str(item.get("issued_at") or item["valid_from"]),
                active=value in ACTIVE_PHASES,
                phase=value,
                trend=str(metadata.get("trend") or "unknown"),
            )
        )
    return tuple(sorted(result, key=lambda row: (row.region_id, row.valid_from, row.label_id)))


def refine_survival_episodes(
    audited_episodes: Iterable[ActualEpisode],
    observations: Iterable[PhaseObservation],
) -> tuple[ActualEpisode, ...]:
    """Split audited hazard episodes at explicit recovery or unknown calendar gaps."""

    by_region = _group_observations(observations)
    result: list[ActualEpisode] = []
    for parent in sorted(audited_episodes, key=lambda item: item.episode_id):
        relevant = [
            item
            for item in by_region.get(parent.region_id, ())
            if item.active
            and date.fromisoformat(item.valid_from) <= date.fromisoformat(parent.valid_to)
            and date.fromisoformat(item.valid_to) >= date.fromisoformat(parent.valid_from)
        ]
        current: list[PhaseObservation] = []
        current_end: date | None = None
        for item in sorted(relevant, key=lambda value: value.valid_from):
            start = date.fromisoformat(item.valid_from)
            if current and current_end and start > current_end + timedelta(days=1):
                result.append(_survival_episode(parent, current, by_region[parent.region_id]))
                current = []
            current.append(item)
            current_end = date.fromisoformat(item.valid_to)
        if current:
            result.append(_survival_episode(parent, current, by_region[parent.region_id]))
    unique = {item.episode_id: item for item in result}
    return tuple(
        sorted(
            unique.values(),
            key=lambda item: (item.region_id, item.valid_from, item.episode_id),
        )
    )


def build_survival_rows(
    feature_path: Path,
    observations: Iterable[PhaseObservation],
    episodes: Iterable[ActualEpisode],
    *,
    horizons_days: tuple[int, ...] = HORIZONS,
    progress: Callable[[int, int], None] | None = None,
) -> tuple[SurvivalRow, ...]:
    observation_index = _group_observations(observations)
    episode_index = _group_episodes(episodes)
    source = feature_path / "adm1-features.jsonl" if feature_path.is_dir() else feature_path
    total = sum(1 for _ in source.open("r", encoding="utf-8"))
    result = []
    with source.open("r", encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            payload = json.loads(line)
            region = str(payload["region_id"])
            if region in observation_index and region in episode_index:
                period_end = date.fromisoformat(str(payload["period_end"]))
                as_of = _as_date(str(payload["as_of"]))
                current = _observation_at(observation_index[region], period_end)
                episode = _episode_at(episode_index[region], period_end)
                if (
                    current is not None
                    and current.active
                    and _as_date(current.issued_at) <= as_of
                    and episode is not None
                ):
                    _validate_signal_availability(payload, as_of)
                    targets = {}
                    reasons = {}
                    for horizon in horizons_days:
                        target, reason = _continuation_target(
                            episode,
                            observation_index[region],
                            period_end + timedelta(days=horizon),
                        )
                        targets[horizon] = target
                        reasons[horizon] = reason
                    identity = {
                        "episode_id": episode.episode_id,
                        "region_id": region,
                        "as_of": payload["as_of"],
                    }
                    result.append(
                        SurvivalRow(
                            sample_id=f"survival:{hashlib.sha256(canonical_json(identity).encode()).hexdigest()[:20]}",
                            episode_id=episode.episode_id,
                            region_id=region,
                            as_of=str(payload["as_of"]),
                            period_end=period_end.isoformat(),
                            elapsed_days=(period_end - date.fromisoformat(episode.valid_from)).days,
                            left_censored=episode.left_censored,
                            current_phase=current.phase,
                            current_trend=current.trend,
                            features=_feature_record(payload, current, episode, period_end),
                            targets=targets,
                            target_reasons=reasons,
                        )
                    )
            if progress:
                progress(number, total)
    return tuple(sorted(result, key=lambda row: (row.period_end, row.region_id, row.sample_id)))


def split_survival_rows(
    rows: Iterable[SurvivalRow],
    episodes: Iterable[ActualEpisode],
    config: SurvivalConfig | None = None,
) -> dict[str, tuple[SurvivalRow, ...]]:
    resolved = config or SurvivalConfig()
    train_cutoff = date.fromisoformat(resolved.train_cutoff)
    holdout_cutoff = date.fromisoformat(resolved.holdout_cutoff)
    split_by_episode = {}
    for episode in episodes:
        start = date.fromisoformat(episode.valid_from)
        end = date.fromisoformat(episode.valid_to)
        if end < train_cutoff:
            split_by_episode[episode.episode_id] = "train"
        elif train_cutoff <= start and end < holdout_cutoff:
            split_by_episode[episode.episode_id] = "validation"
        elif start >= holdout_cutoff:
            split_by_episode[episode.episode_id] = "holdout"
        else:
            split_by_episode[episode.episode_id] = "purged_boundary"
    result: dict[str, list[SurvivalRow]] = defaultdict(list)
    for row in rows:
        result[split_by_episode.get(row.episode_id, "purged_boundary")].append(row)
    _assert_disjoint(result)
    return {
        name: tuple(sorted(values, key=lambda row: (row.period_end, row.region_id)))
        for name, values in result.items()
    }


def evaluate_survival(
    rows: Iterable[SurvivalRow],
    episodes: Iterable[ActualEpisode],
    *,
    split: str = "validation",
    config: SurvivalConfig | None = None,
    ablation: bool = True,
    progress: Callable[[int, int], None] | None = None,
) -> dict[str, Any]:
    resolved = config or SurvivalConfig()
    splits = split_survival_rows(rows, episodes, resolved)
    if split not in {"validation", "holdout"}:
        raise SurvivalEvaluationError("split must be validation or holdout")
    train = list(splits.get("train", ()))
    if split == "holdout":
        train.extend(splits.get("validation", ()))
    test = list(splits.get(split, ()))
    if not train or not test:
        raise SurvivalEvaluationError(f"{split} lacks train or test rows")
    predictions = _candidate_predictions(train, test, resolved, split, progress=progress)
    metrics = _candidate_metrics(predictions, test, episodes, resolved)
    baseline = min(BASELINES, key=lambda name: (metrics[name]["integrated_brier"], name))
    for candidate in CANDIDATES:
        if candidate in BASELINES:
            metrics[candidate]["skill_status"] = "baseline"
            metrics[candidate]["skill_reason"] = "reference_candidate"
        else:
            status, reason = continuation_skill_decision(
                metrics[candidate], metrics[baseline], resolved.min_test_episodes
            )
            metrics[candidate]["skill_status"] = status
            metrics[candidate]["skill_reason"] = reason
    ablation_rows = (
        _ablation(train, test, episodes, resolved, split, metrics["logistic_regression"])
        if ablation and split == "validation"
        else []
    )
    prediction_payload = [asdict(item) for item in predictions]
    base = {
        "schema_version": SCHEMA_VERSION,
        "split": split,
        "config": asdict(resolved),
        "train_row_count": len(train),
        "test_row_count": len(test),
        "train_episode_count": len({row.episode_id for row in train}),
        "test_episode_count": len({row.episode_id for row in test}),
        "purged_episode_count": len(
            {row.episode_id for row in splits.get("purged_boundary", ())}
        ),
        "baseline_champion": baseline,
        "candidates": [metrics[name] for name in CANDIDATES],
        "ablation": ablation_rows,
        "predictions_sha256": _hash(prediction_payload),
    }
    return {
        **base,
        "run_hash": _hash(base),
        "predictions": prediction_payload,
    }


def continuation_skill_decision(
    model: Mapping[str, Any], baseline: Mapping[str, Any], min_test_episodes: int = 5
) -> tuple[str, str]:
    if int(model["test_episode_count"]) < min_test_episodes:
        return "rejected", "insufficient_test_episodes"
    model_by_horizon = {item["horizon_days"]: item for item in model["horizons"]}
    baseline_by_horizon = {item["horizon_days"]: item for item in baseline["horizons"]}
    no_horizon_worse = all(
        model_by_horizon[horizon]["brier_score"]
        <= baseline_by_horizon[horizon]["brier_score"]
        for horizon in model_by_horizon
    )
    improves = (
        float(model["integrated_brier"]) < float(baseline["integrated_brier"])
        and no_horizon_worse
        and model["mean_absolute_recovery_error_days"] is not None
        and baseline["mean_absolute_recovery_error_days"] is not None
        and float(model["mean_absolute_recovery_error_days"])
        < float(baseline["mean_absolute_recovery_error_days"])
    )
    if improves:
        return "continuation_skill_eligible", "improves_integrated_brier_and_recovery"
    return "rejected", "did_not_improve_survival_baseline"


def apply_monotonic_probabilities(
    values: Mapping[int, float], horizons: Iterable[int] = HORIZONS
) -> dict[int, float]:
    result = {}
    previous = 1.0
    for horizon in horizons:
        previous = min(previous, _bounded(float(values[horizon])))
        result[horizon] = previous
    return result


def validate_holdout_unlock(output_dir: Path, frozen_validation_run_hash: str | None) -> str:
    if not frozen_validation_run_hash:
        raise SurvivalEvaluationError(
            "holdout unlock requires --frozen-validation-run-hash"
        )
    validation_manifest = output_dir / "validation" / "manifest.json"
    if not validation_manifest.is_file():
        raise SurvivalEvaluationError("validation manifest is required before holdout")
    expected = str(json.loads(validation_manifest.read_text(encoding="utf-8"))["run_hash"])
    if frozen_validation_run_hash != expected:
        raise SurvivalEvaluationError("frozen validation run hash does not match")
    if (output_dir / "holdout" / "manifest.json").exists():
        raise SurvivalEvaluationError("final holdout has already been opened")
    return expected


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def risk_set_payload(
    row: SurvivalRow, input_hashes: Mapping[str, str]
) -> dict[str, Any]:
    """Serialize an auditable risk-set row without dropping its model inputs."""

    return {
        **asdict(row),
        "input_hashes": dict(sorted(input_hashes.items())),
    }


def _continuation_target(
    episode: ActualEpisode,
    observations: Iterable[PhaseObservation],
    target_date: date,
) -> tuple[int | None, str]:
    if target_date <= date.fromisoformat(episode.valid_to):
        return 1, "same_episode_active"
    recovered = any(
        not item.active
        and date.fromisoformat(episode.valid_to) < date.fromisoformat(item.valid_from)
        and date.fromisoformat(item.valid_from) <= target_date
        for item in observations
    )
    return (0, "validated_recovery") if recovered else (None, "recovery_unobserved")


def _survival_episode(
    parent: ActualEpisode,
    values: list[PhaseObservation],
    all_observations: Iterable[PhaseObservation],
) -> ActualEpisode:
    start = min(date.fromisoformat(item.valid_from) for item in values)
    end = max(date.fromisoformat(item.valid_to) for item in values)
    identity = {
        "parent_episode_id": parent.episode_id,
        "region_id": parent.region_id,
        "valid_from": start.isoformat(),
        "valid_to": end.isoformat(),
    }
    inactive_before = any(
        not item.active and date.fromisoformat(item.valid_to) < start
        for item in all_observations
    )
    inactive_after = any(
        not item.active and date.fromisoformat(item.valid_from) > end
        for item in all_observations
    )
    return ActualEpisode(
        episode_id=f"survival:{hashlib.sha256(canonical_json(identity).encode()).hexdigest()[:20]}",
        region_id=parent.region_id,
        valid_from=start.isoformat(),
        valid_to=end.isoformat(),
        left_censored=not inactive_before,
        right_censored=not inactive_after,
    )


def _candidate_predictions(
    train: list[SurvivalRow],
    test: list[SurvivalRow],
    config: SurvivalConfig,
    split: str,
    *,
    excluded_family: str | None = None,
    candidates: tuple[str, ...] = CANDIDATES,
    progress: Callable[[int, int], None] | None = None,
) -> tuple[SurvivalPrediction, ...]:
    raw: dict[tuple[str, str], dict[int, float]] = defaultdict(dict)
    total = len(candidates) * len(config.horizons_days)
    completed = 0
    for candidate in candidates:
        for horizon in config.horizons_days:
            train_known = [row for row in train if row.targets[horizon] is not None]
            if not _eligible_train(train_known, horizon, config):
                raise SurvivalEvaluationError(
                    f"{candidate}:{horizon} has insufficient training support"
                )
            probabilities = _predict_horizon(
                candidate,
                train_known,
                test,
                horizon,
                config,
                excluded_family=excluded_family,
            )
            for row, probability in zip(test, probabilities, strict=True):
                raw[(candidate, row.sample_id)][horizon] = probability
            completed += 1
            if progress:
                progress(completed, total)
    result = []
    by_sample = {row.sample_id: row for row in test}
    for (candidate, sample_id), values in sorted(raw.items()):
        monotonic = apply_monotonic_probabilities(values, config.horizons_days)
        row = by_sample[sample_id]
        for horizon in config.horizons_days:
            result.append(
                SurvivalPrediction(
                    split=split,
                    candidate=candidate,
                    sample_id=sample_id,
                    episode_id=row.episode_id,
                    region_id=row.region_id,
                    as_of=row.as_of,
                    horizon_days=horizon,
                    actual=row.targets[horizon],
                    probability=monotonic[horizon],
                    monotonic_version=MONOTONIC_VERSION,
                )
            )
    return tuple(result)


def _predict_horizon(
    candidate: str,
    train: list[SurvivalRow],
    test: list[SurvivalRow],
    horizon: int,
    config: SurvivalConfig,
    *,
    excluded_family: str | None,
) -> list[float]:
    targets = [int(row.targets[horizon]) for row in train if row.targets[horizon] is not None]
    frequency = sum(targets) / len(targets)
    if candidate == "always_active":
        return [1.0] * len(test)
    if candidate == "empirical_survival":
        by_bin: dict[int, list[int]] = defaultdict(list)
        for row, target in zip(train, targets, strict=True):
            by_bin[row.elapsed_days // config.elapsed_bin_days].append(target)
        return [
            sum(by_bin[key]) / len(by_bin[key]) if by_bin[key] else frequency
            for row in test
            for key in [row.elapsed_days // config.elapsed_bin_days]
        ]
    if candidate == "phase_survival":
        by_phase: dict[str, list[int]] = defaultdict(list)
        for row, target in zip(train, targets, strict=True):
            by_phase[row.current_phase].append(target)
        return [
            sum(by_phase[row.current_phase]) / len(by_phase[row.current_phase])
            if by_phase[row.current_phase]
            else frequency
            for row in test
        ]
    estimator = _estimator(candidate, config.seed)
    estimator.fit(
        [_filtered_features(row.features, excluded_family) for row in train], targets
    )
    return [
        float(value[1])
        for value in estimator.predict_proba(
            [_filtered_features(row.features, excluded_family) for row in test]
        )
    ]


def _candidate_metrics(
    predictions: Iterable[SurvivalPrediction],
    test: list[SurvivalRow],
    episodes: Iterable[ActualEpisode],
    config: SurvivalConfig,
) -> dict[str, dict[str, Any]]:
    episode_by_id = {item.episode_id: item for item in episodes}
    grouped: dict[str, list[SurvivalPrediction]] = defaultdict(list)
    for item in predictions:
        grouped[item.candidate].append(item)
    result = {}
    for candidate, values in grouped.items():
        horizons = []
        for horizon in config.horizons_days:
            known = [
                item for item in values if item.horizon_days == horizon and item.actual is not None
            ]
            if not known:
                raise SurvivalEvaluationError(f"{candidate}:{horizon} has no known test targets")
            brier = sum((item.probability - int(item.actual)) ** 2 for item in known) / len(
                known
            )
            log_loss = -sum(
                int(item.actual) * math.log(_clip(item.probability))
                + (1 - int(item.actual)) * math.log(_clip(1 - item.probability))
                for item in known
            ) / len(known)
            predicted_active = [item for item in known if item.probability >= config.threshold]
            predicted_recovery = [item for item in known if item.probability < config.threshold]
            positives = sum(int(item.actual) for item in known)
            true_active = sum(int(item.actual) for item in predicted_active)
            true_recovery = sum(1 - int(item.actual) for item in predicted_recovery)
            horizons.append(
                {
                    "horizon_days": horizon,
                    "known_count": len(known),
                    "positive_count": positives,
                    "negative_count": len(known) - positives,
                    "brier_score": brier,
                    "log_loss": log_loss,
                    "continuation_recall": true_active / positives if positives else None,
                    "recovery_precision": (
                        true_recovery / len(predicted_recovery) if predicted_recovery else None
                    ),
                    "calibration_bins": _calibration_bins(known),
                }
            )
        recovery_errors = _recovery_errors(values, test, episode_by_id, config)
        result[candidate] = {
            "candidate": candidate,
            "test_episode_count": len({item.episode_id for item in values}),
            "integrated_brier": sum(item["brier_score"] for item in horizons)
            / len(horizons),
            "mean_absolute_recovery_error_days": (
                sum(recovery_errors) / len(recovery_errors) if recovery_errors else None
            ),
            "recovery_error_denominator": len(recovery_errors),
            "horizons": horizons,
        }
    return result


def _recovery_errors(
    predictions: Iterable[SurvivalPrediction],
    test: Iterable[SurvivalRow],
    episode_by_id: Mapping[str, ActualEpisode],
    config: SurvivalConfig,
) -> list[int]:
    by_sample: dict[str, list[SurvivalPrediction]] = defaultdict(list)
    for item in predictions:
        by_sample[item.sample_id].append(item)
    row_by_sample = {item.sample_id: item for item in test}
    result = []
    for sample_id, values in by_sample.items():
        row = row_by_sample[sample_id]
        episode = episode_by_id[row.episode_id]
        if episode.right_censored:
            continue
        ordered = sorted(values, key=lambda item: item.horizon_days)
        predicted = next(
            (
                item.horizon_days
                for item in ordered
                if item.probability < config.threshold
            ),
            max(config.horizons_days) + 30,
        )
        actual = max(
            0,
            (date.fromisoformat(episode.valid_to) - date.fromisoformat(row.period_end)).days,
        )
        result.append(abs(predicted - actual))
    return result


def _ablation(
    train: list[SurvivalRow],
    test: list[SurvivalRow],
    episodes: Iterable[ActualEpisode],
    config: SurvivalConfig,
    split: str,
    full_metrics: Mapping[str, Any],
) -> list[dict[str, Any]]:
    result = []
    for family in FEATURE_FAMILIES:
        predictions = _candidate_predictions(
            train,
            test,
            config,
            split,
            excluded_family=family,
            candidates=("logistic_regression",),
        )
        metrics = _candidate_metrics(predictions, test, episodes, config)[
            "logistic_regression"
        ]
        result.append(
            {
                "excluded_family": family,
                "integrated_brier": metrics["integrated_brier"],
                "delta_integrated_brier": metrics["integrated_brier"]
                - float(full_metrics["integrated_brier"]),
            }
        )
    return result


def _feature_record(
    payload: Mapping[str, Any],
    current: PhaseObservation,
    episode: ActualEpisode,
    period_end: date,
) -> dict[str, float | str | None]:
    result: dict[str, float | str | None] = {
        "region_id": str(payload["region_id"]),
        "current_phase": current.phase,
        "current_trend": current.trend,
        "elapsed_days": float((period_end - date.fromisoformat(episode.valid_from)).days),
        "left_censored": "yes" if episode.left_censored else "no",
    }
    for name, signal in sorted(payload["signals"].items()):
        result[name] = signal.get("value")
        result[f"{name}__age_days"] = signal.get("age_days")
    angle = 2 * math.pi * period_end.timetuple().tm_yday / 365.25
    result["season_sin"] = math.sin(angle)
    result["season_cos"] = math.cos(angle)
    return result


def _filtered_features(
    features: Mapping[str, float | str | None], excluded_family: str | None
) -> dict[str, float | str | None]:
    if excluded_family is None:
        return dict(features)
    return {
        name: value
        for name, value in features.items()
        if _feature_family(name) != excluded_family
    }


def _feature_family(name: str) -> str:
    lowered = name.lower()
    if any(token in lowered for token in ("rain", "spi", "spei", "precip")):
        return "rainfall_drought"
    if any(token in lowered for token in ("ndvi", "vegetation", "evi", "lai")):
        return "vegetation"
    if any(token in lowered for token in ("soil", "water", "reservoir")):
        return "soil_water"
    if any(token in lowered for token in ("evap", "temperature", "vpd")):
        return "atmospheric_demand"
    return "season_region"


def _eligible_train(
    rows: list[SurvivalRow], horizon: int, config: SurvivalConfig
) -> bool:
    targets = [int(row.targets[horizon]) for row in rows if row.targets[horizon] is not None]
    return (
        len(targets) >= config.min_train_rows
        and targets.count(0) >= config.min_class_count
        and targets.count(1) >= config.min_class_count
    )


def _estimator(candidate: str, seed: int) -> Pipeline:
    if candidate == "logistic_regression":
        model: Any = LogisticRegression(random_state=seed, max_iter=1000, solver="lbfgs")
    elif candidate == "hist_gradient_boosting":
        model = HistGradientBoostingClassifier(
            random_state=seed, max_iter=100, learning_rate=0.08, max_leaf_nodes=15
        )
    else:
        raise SurvivalEvaluationError(f"unknown candidate: {candidate}")
    return Pipeline(
        [
            ("vectorize", DictVectorizer(sparse=False)),
            ("impute", SimpleImputer(strategy="median", keep_empty_features=True)),
            ("scale", StandardScaler()),
            ("model", model),
        ]
    )


def _calibration_bins(values: list[SurvivalPrediction]) -> list[dict[str, Any]]:
    bins = []
    for lower in (0.0, 0.2, 0.4, 0.6, 0.8):
        upper = lower + 0.2
        members = [
            item
            for item in values
            if lower <= item.probability < upper
            or (upper == 1.0 and item.probability == 1.0)
        ]
        bins.append(
            {
                "lower": lower,
                "upper": upper,
                "count": len(members),
                "mean_probability": (
                    sum(item.probability for item in members) / len(members)
                    if members
                    else None
                ),
                "observed_frequency": (
                    sum(int(item.actual) for item in members) / len(members)
                    if members
                    else None
                ),
            }
        )
    return bins


def _group_observations(
    values: Iterable[PhaseObservation],
) -> dict[str, tuple[PhaseObservation, ...]]:
    grouped: dict[str, list[PhaseObservation]] = defaultdict(list)
    for item in values:
        grouped[item.region_id].append(item)
    return {key: tuple(items) for key, items in grouped.items()}


def _group_episodes(
    values: Iterable[ActualEpisode],
) -> dict[str, tuple[ActualEpisode, ...]]:
    grouped: dict[str, list[ActualEpisode]] = defaultdict(list)
    for item in values:
        grouped[item.region_id].append(item)
    return {key: tuple(items) for key, items in grouped.items()}


def _observation_at(
    values: Iterable[PhaseObservation], target: date
) -> PhaseObservation | None:
    matches = [
        item
        for item in values
        if date.fromisoformat(item.valid_from) <= target <= date.fromisoformat(item.valid_to)
    ]
    if not matches:
        return None
    if len({item.active for item in matches}) != 1:
        raise SurvivalEvaluationError(f"conflicting validated phase at {target}")
    return matches[0]


def _episode_at(
    values: Iterable[ActualEpisode], target: date
) -> ActualEpisode | None:
    matches = [
        item
        for item in values
        if date.fromisoformat(item.valid_from) <= target <= date.fromisoformat(item.valid_to)
    ]
    if len(matches) > 1:
        raise SurvivalEvaluationError(f"overlapping episodes at {target}")
    return matches[0] if matches else None


def _validate_signal_availability(payload: Mapping[str, Any], as_of: date) -> None:
    for name, signal in payload["signals"].items():
        available = signal.get("available_at")
        if available and _as_date(str(available)) > as_of:
            raise SurvivalEvaluationError(
                f"feature unavailable at as_of: {payload['region_id']}:{name}"
            )


def _assert_disjoint(splits: Mapping[str, Iterable[SurvivalRow]]) -> None:
    episode_sets = {
        name: {row.episode_id for row in rows}
        for name, rows in splits.items()
        if name != "purged_boundary"
    }
    names = sorted(episode_sets)
    for index, left in enumerate(names):
        for right in names[index + 1 :]:
            overlap = episode_sets[left] & episode_sets[right]
            if overlap:
                raise SurvivalEvaluationError(f"episode split leakage: {sorted(overlap)[0]}")


def _bounded(value: float) -> float:
    if not math.isfinite(value):
        raise SurvivalEvaluationError("non-finite probability")
    return min(1.0, max(0.0, value))


def _clip(value: float) -> float:
    return min(1 - 1e-15, max(1e-15, value))


def _hash(value: object) -> str:
    return f"sha256:{hashlib.sha256(canonical_json(value).encode()).hexdigest()}"


def _jsonl(path: Path) -> tuple[dict[str, Any], ...]:
    return tuple(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines())


def _as_date(value: str) -> date:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).date()


__all__ = [
    "ActualEpisode",
    "PhaseObservation",
    "SurvivalConfig",
    "SurvivalEvaluationError",
    "SurvivalPrediction",
    "SurvivalRow",
    "apply_monotonic_probabilities",
    "build_survival_rows",
    "canonical_json",
    "continuation_skill_decision",
    "evaluate_survival",
    "load_actual_episodes",
    "load_phase_observations",
    "refine_survival_episodes",
    "risk_set_payload",
    "split_survival_rows",
    "validate_holdout_unlock",
]
