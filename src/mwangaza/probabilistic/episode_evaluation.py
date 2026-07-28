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

ACTIVE_PHASES = frozenset({"phase_alert", "phase_alarm", "phase_emergency"})
INACTIVE_PHASES = frozenset({"phase_normal", "phase_recovery"})
VALIDATED_STATUSES = frozenset({"validated", "source_unit_explicit"})
BASELINES = ("persistence", "seasonal_climatology", "historical_frequency")
ML_MODELS = ("logistic_regression", "hist_gradient_boosting")
CANDIDATES = (*BASELINES, *ML_MODELS)
SCHEMA_VERSION = "mwangaza.drought-episode-evaluation.v1"


class EpisodeEvaluationError(RuntimeError):
    """Raised when an episode evaluation would be ambiguous or leak labels."""


@dataclass(frozen=True)
class EpisodeEvaluationConfig:
    horizons_days: tuple[int, ...] = (10, 20, 30)
    first_test_year: int = 2019
    max_gap_days: int = 32
    probability_threshold: float = 0.5
    min_train_rows: int = 100
    min_class_count: int = 2
    min_test_episodes: int = 2
    seed: int = 2026

    def __post_init__(self) -> None:
        if not self.horizons_days or any(value <= 0 for value in self.horizons_days):
            raise EpisodeEvaluationError("horizons_days must be positive")
        if len(set(self.horizons_days)) != len(self.horizons_days):
            raise EpisodeEvaluationError("horizons_days must be unique")
        if self.max_gap_days < 0:
            raise EpisodeEvaluationError("max_gap_days must be non-negative")
        if not 0 < self.probability_threshold < 1:
            raise EpisodeEvaluationError("probability_threshold must be between 0 and 1")
        if self.min_train_rows < 4 or self.min_class_count < 1:
            raise EpisodeEvaluationError("training support thresholds are invalid")


@dataclass(frozen=True)
class HazardObservation:
    label_id: str
    region_id: str
    valid_from: str
    valid_to: str
    issued_at: str
    target: int
    normalized_value: str


@dataclass(frozen=True)
class ActualEpisode:
    episode_id: str
    region_id: str
    valid_from: str
    valid_to: str
    left_censored: bool
    right_censored: bool


@dataclass(frozen=True)
class EvaluationRow:
    region_id: str
    as_of: str
    target_date: str
    horizon_days: int
    target: int
    episode_id: str | None
    current_active: int | None
    features: dict[str, float | str | None]


@dataclass(frozen=True)
class OofEpisodePrediction:
    candidate: str
    fold: int
    region_id: str
    as_of: str
    target_date: str
    horizon_days: int
    actual: int
    actual_episode_id: str | None
    probability: float


@dataclass(frozen=True)
class PredictedEpisode:
    predicted_episode_id: str
    candidate: str
    horizon_days: int
    region_id: str
    valid_from: str
    valid_to: str
    issued_from: str
    max_probability: float
    point_count: int


def load_hazard_observations(path: Path) -> tuple[HazardObservation, ...]:
    rows = _jsonl(path / "independent-labels.jsonl" if path.is_dir() else path)
    result = []
    for item in rows:
        if item.get("label_semantics") != "drought_hazard_event":
            continue
        if item.get("review_status") not in VALIDATED_STATUSES or not item.get(
            "adm1_region_id"
        ):
            continue
        value = str(item.get("normalized_value"))
        if value in ACTIVE_PHASES:
            target = 1
        elif value in INACTIVE_PHASES:
            target = 0
        else:
            continue
        result.append(
            HazardObservation(
                label_id=str(item["label_id"]),
                region_id=str(item["adm1_region_id"]),
                valid_from=str(item["valid_from"]),
                valid_to=str(item["valid_to"]),
                issued_at=str(item.get("issued_at") or item["valid_from"]),
                target=target,
                normalized_value=value,
            )
        )
    return tuple(sorted(result, key=lambda row: (row.region_id, row.valid_from, row.label_id)))


def load_actual_episodes(path: Path) -> tuple[ActualEpisode, ...]:
    rows = _jsonl(path / "episodes.jsonl" if path.is_dir() else path)
    return tuple(
        ActualEpisode(
            episode_id=str(item["episode_id"]),
            region_id=str(item["adm1_region_id"]),
            valid_from=str(item["valid_from"]),
            valid_to=str(item["valid_to"]),
            left_censored=bool(item.get("left_censored")),
            right_censored=bool(item.get("right_censored")),
        )
        for item in rows
    )


def build_evaluation_rows(
    feature_path: Path,
    observations: Iterable[HazardObservation],
    episodes: Iterable[ActualEpisode],
    *,
    horizons_days: tuple[int, ...] = (10, 20, 30),
    progress: Callable[[int, int], None] | None = None,
) -> tuple[EvaluationRow, ...]:
    observation_index = _observation_index(observations)
    episode_index = _episode_index(episodes)
    regions = frozenset(observation_index)
    path = feature_path / "adm1-features.jsonl" if feature_path.is_dir() else feature_path
    total = sum(1 for _ in path.open("r", encoding="utf-8"))
    result: list[EvaluationRow] = []
    with path.open("r", encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            payload = json.loads(line)
            region = str(payload["region_id"])
            if region in regions:
                as_of = _as_date(payload["as_of"])
                period_end = date.fromisoformat(str(payload["period_end"]))
                _validate_signal_availability(payload, as_of)
                features = _feature_record(payload)
                current = _known_observation(observation_index[region], period_end)
                current_active = (
                    current.target
                    if current is not None and _as_date(current.issued_at) <= as_of
                    else None
                )
                for horizon in horizons_days:
                    target_date = period_end + timedelta(days=horizon)
                    target_observation = _known_observation(
                        observation_index[region], target_date
                    )
                    if target_observation is None:
                        continue
                    episode_id = None
                    if target_observation.target == 1:
                        episode = _containing_episode(episode_index[region], target_date)
                        if episode is None:
                            raise EpisodeEvaluationError(
                                f"active target lacks episode: {region}:{target_date}"
                            )
                        episode_id = episode.episode_id
                    result.append(
                        EvaluationRow(
                            region_id=region,
                            as_of=payload["as_of"],
                            target_date=target_date.isoformat(),
                            horizon_days=horizon,
                            target=target_observation.target,
                            episode_id=episode_id,
                            current_active=current_active,
                            features=features,
                        )
                    )
            if progress is not None:
                progress(number, total)
    return tuple(sorted(result, key=lambda row: (row.horizon_days, row.target_date, row.region_id)))


def evaluate_candidates(
    rows: Iterable[EvaluationRow],
    episodes: Iterable[ActualEpisode],
    config: EpisodeEvaluationConfig | None = None,
    *,
    progress: Callable[[int, int], None] | None = None,
) -> dict[str, Any]:
    resolved = config or EpisodeEvaluationConfig()
    all_rows = tuple(rows)
    episode_by_id = {item.episode_id: item for item in episodes}
    results = []
    all_predictions: list[OofEpisodePrediction] = []
    all_predicted_episodes: list[PredictedEpisode] = []
    total = sum(
        len(
            {
                date.fromisoformat(row.target_date).year
                for row in all_rows
                if row.horizon_days == horizon
                and date.fromisoformat(row.target_date).year >= resolved.first_test_year
            }
        )
        for horizon in resolved.horizons_days
    )
    completed = 0
    if progress:
        progress(0, total)
    for horizon in resolved.horizons_days:
        horizon_rows = tuple(row for row in all_rows if row.horizon_days == horizon)
        years = sorted(
            {
                date.fromisoformat(row.target_date).year
                for row in horizon_rows
                if date.fromisoformat(row.target_date).year >= resolved.first_test_year
            }
        )
        predictions: dict[str, list[OofEpisodePrediction]] = {
            name: [] for name in CANDIDATES
        }
        folds = []
        for fold, year in enumerate(years):
            cutoff = date(year, 1, 1)
            test_episode_ids = {
                item.episode_id
                for item in episode_by_id.values()
                if date.fromisoformat(item.valid_from).year == year
            }
            train = [
                row
                for row in horizon_rows
                if date.fromisoformat(row.target_date) < cutoff
                and row.episode_id not in test_episode_ids
            ]
            test = [
                row
                for row in horizon_rows
                if (
                    row.episode_id in test_episode_ids
                    or (
                        row.episode_id is None
                        and date.fromisoformat(row.target_date).year == year
                    )
                )
            ]
            _assert_no_episode_leakage(train, test)
            if _eligible_train(train, resolved) and test:
                fold_counts = {}
                for candidate in CANDIDATES:
                    probabilities = _predict(candidate, train, test, resolved)
                    fold_counts[candidate] = len(probabilities)
                    predictions[candidate].extend(
                        OofEpisodePrediction(
                            candidate=candidate,
                            fold=fold,
                            region_id=row.region_id,
                            as_of=row.as_of,
                            target_date=row.target_date,
                            horizon_days=horizon,
                            actual=row.target,
                            actual_episode_id=row.episode_id,
                            probability=_bounded(probability),
                        )
                        for row, probability in zip(test, probabilities, strict=True)
                    )
                folds.append(
                    {
                        "fold": fold,
                        "test_year": year,
                        "train_rows": len(train),
                        "test_rows": len(test),
                        "test_episode_count": len(
                            {row.episode_id for row in test if row.episode_id}
                        ),
                        "candidate_prediction_counts": fold_counts,
                    }
                )
            completed += 1
            if progress:
                progress(completed, total)

        candidate_results = []
        candidate_metrics: dict[str, dict[str, Any]] = {}
        for candidate in CANDIDATES:
            candidate_predictions = tuple(predictions[candidate])
            predicted = group_predicted_episodes(
                candidate_predictions,
                threshold=resolved.probability_threshold,
                max_gap_days=resolved.max_gap_days,
            )
            metrics = episode_metrics(candidate_predictions, predicted, episode_by_id)
            candidate_metrics[candidate] = metrics
            candidate_results.append({"candidate": candidate, **metrics})
            all_predictions.extend(candidate_predictions)
            all_predicted_episodes.extend(predicted)

        baseline = min(
            BASELINES,
            key=lambda name: (
                candidate_metrics[name]["brier_score"],
                BASELINES.index(name),
            ),
        )
        for item in candidate_results:
            if item["candidate"] not in ML_MODELS:
                item["skill_status"] = "baseline"
                item["skill_reason"] = "reference_candidate"
                continue
            item["skill_status"], item["skill_reason"] = episode_skill_decision(
                item,
                candidate_metrics[baseline],
                min_test_episodes=resolved.min_test_episodes,
            )
        results.append(
            {
                "horizon_days": horizon,
                "folds": folds,
                "baseline_champion": baseline,
                "candidates": candidate_results,
            }
        )

    prediction_rows = [asdict(item) for item in all_predictions]
    predicted_episode_rows = [asdict(item) for item in all_predicted_episodes]
    base = {
        "schema_version": SCHEMA_VERSION,
        "config": asdict(resolved),
        "row_count": len(all_rows),
        "results": results,
        "predictions_sha256": _hash(prediction_rows),
        "predicted_episodes_sha256": _hash(predicted_episode_rows),
    }
    return {
        **base,
        "run_hash": _hash(base),
        "predictions": prediction_rows,
        "predicted_episodes": predicted_episode_rows,
    }


def group_predicted_episodes(
    predictions: Iterable[OofEpisodePrediction],
    *,
    threshold: float = 0.5,
    max_gap_days: int = 32,
) -> tuple[PredictedEpisode, ...]:
    grouped: dict[tuple[str, str, int], list[OofEpisodePrediction]] = defaultdict(list)
    for item in predictions:
        if item.probability >= threshold:
            grouped[(item.candidate, item.region_id, item.horizon_days)].append(item)
    result = []
    for (candidate, region, horizon), values in sorted(grouped.items()):
        current: list[OofEpisodePrediction] = []
        last: date | None = None
        for item in sorted(values, key=lambda row: row.target_date):
            target = date.fromisoformat(item.target_date)
            if current and last and target > last + timedelta(days=max_gap_days):
                result.append(_predicted_episode(candidate, region, horizon, current))
                current = []
            current.append(item)
            last = target
        if current:
            result.append(_predicted_episode(candidate, region, horizon, current))
    return tuple(result)


def episode_skill_decision(
    ml_metrics: Mapping[str, Any],
    baseline_metrics: Mapping[str, Any],
    *,
    min_test_episodes: int = 2,
) -> tuple[str, str]:
    if int(ml_metrics["actual_episode_count"]) < min_test_episodes:
        return "rejected", "insufficient_test_episodes"
    improves = (
        float(ml_metrics["brier_score"]) < float(baseline_metrics["brier_score"])
        and float(ml_metrics["event_f1"]) > float(baseline_metrics["event_f1"])
        and int(ml_metrics["false_alarm_count"])
        <= int(baseline_metrics["false_alarm_count"])
    )
    if improves:
        return "episode_skill_eligible", "improves_best_baseline"
    return "rejected", "did_not_improve_brier_f1_and_false_alarms"


def episode_metrics(
    predictions: Iterable[OofEpisodePrediction],
    predicted_episodes: Iterable[PredictedEpisode],
    episode_by_id: Mapping[str, ActualEpisode],
) -> dict[str, Any]:
    prediction_rows = tuple(predictions)
    predicted = tuple(predicted_episodes)
    actual_ids = sorted(
        {
            item.actual_episode_id
            for item in prediction_rows
            if item.actual == 1 and item.actual_episode_id
        }
    )
    actual = [episode_by_id[item] for item in actual_ids]
    matches = _match_episodes(actual, predicted)
    matched_actual = {left.episode_id for left, _ in matches}
    matched_predicted = {right.predicted_episode_id for _, right in matches}
    recall = len(matches) / len(actual) if actual else 0.0
    precision = len(matches) / len(predicted) if predicted else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    leads = []
    onset_errors = []
    duration_errors = []
    recovery_errors = []
    for truth, forecast in matches:
        truth_start = date.fromisoformat(truth.valid_from)
        truth_end = date.fromisoformat(truth.valid_to)
        forecast_start = date.fromisoformat(forecast.valid_from)
        forecast_end = date.fromisoformat(forecast.valid_to)
        if not truth.left_censored:
            onset_errors.append(abs((forecast_start - truth_start).days))
            issued = min(
                _as_date(item.as_of)
                for item in prediction_rows
                if item.candidate == forecast.candidate
                and item.region_id == truth.region_id
                and item.probability >= 0.5
                and truth_start <= date.fromisoformat(item.target_date) <= truth_end
            )
            leads.append((truth_start - issued).days)
        if not truth.right_censored:
            duration_errors.append(
                abs((forecast_end - forecast_start).days - (truth_end - truth_start).days)
            )
            recovery_errors.append(abs((forecast_end - truth_end).days))
    return {
        "prediction_count": len(prediction_rows),
        "actual_episode_count": len(actual),
        "predicted_episode_count": len(predicted),
        "matched_episode_count": len(matches),
        "missed_episode_count": len(actual) - len(matched_actual),
        "false_alarm_count": len(predicted) - len(matched_predicted),
        "event_recall": recall,
        "event_precision": precision,
        "event_f1": f1,
        "mean_lead_days": _mean(leads),
        "mean_absolute_onset_error_days": _mean(onset_errors),
        "mean_absolute_duration_error_days": _mean(duration_errors),
        "mean_absolute_recovery_error_days": _mean(recovery_errors),
        "onset_metric_denominator": len(onset_errors),
        "recovery_metric_denominator": len(recovery_errors),
        "brier_score": (
            sum((item.probability - item.actual) ** 2 for item in prediction_rows)
            / len(prediction_rows)
            if prediction_rows
            else 1.0
        ),
    }


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _observation_index(
    observations: Iterable[HazardObservation],
) -> dict[str, tuple[HazardObservation, ...]]:
    grouped: dict[str, list[HazardObservation]] = defaultdict(list)
    for item in observations:
        grouped[item.region_id].append(item)
    return {
        key: tuple(sorted(values, key=lambda item: item.valid_from))
        for key, values in grouped.items()
    }


def _episode_index(
    episodes: Iterable[ActualEpisode],
) -> dict[str, tuple[ActualEpisode, ...]]:
    grouped: dict[str, list[ActualEpisode]] = defaultdict(list)
    for item in episodes:
        grouped[item.region_id].append(item)
    return {
        key: tuple(sorted(values, key=lambda item: item.valid_from))
        for key, values in grouped.items()
    }


def _known_observation(
    values: Iterable[HazardObservation], target: date
) -> HazardObservation | None:
    matching = [
        item
        for item in values
        if date.fromisoformat(item.valid_from) <= target <= date.fromisoformat(item.valid_to)
    ]
    if not matching:
        return None
    targets = {item.target for item in matching}
    if len(targets) != 1:
        raise EpisodeEvaluationError(f"conflicting validated labels at {target}")
    return matching[0]


def _containing_episode(
    values: Iterable[ActualEpisode], target: date
) -> ActualEpisode | None:
    matches = [
        item
        for item in values
        if date.fromisoformat(item.valid_from) <= target <= date.fromisoformat(item.valid_to)
    ]
    if len(matches) > 1:
        raise EpisodeEvaluationError(f"overlapping actual episodes at {target}")
    return matches[0] if matches else None


def _feature_record(payload: Mapping[str, Any]) -> dict[str, float | str | None]:
    result: dict[str, float | str | None] = {"region_id": str(payload["region_id"])}
    for name, signal in sorted(payload["signals"].items()):
        result[name] = signal.get("value")
        result[f"{name}__age_days"] = signal.get("age_days")
    target = date.fromisoformat(str(payload["period_end"]))
    angle = 2 * math.pi * target.timetuple().tm_yday / 365.25
    result["season_sin"] = math.sin(angle)
    result["season_cos"] = math.cos(angle)
    return result


def _validate_signal_availability(payload: Mapping[str, Any], as_of: date) -> None:
    for name, signal in payload["signals"].items():
        available = signal.get("available_at")
        if available and _as_date(available) > as_of:
            raise EpisodeEvaluationError(
                f"feature unavailable at as_of: {payload['region_id']}:{name}"
            )


def _assert_no_episode_leakage(
    train: Iterable[EvaluationRow], test: Iterable[EvaluationRow]
) -> None:
    train_ids = {row.episode_id for row in train if row.episode_id}
    test_ids = {row.episode_id for row in test if row.episode_id}
    overlap = train_ids & test_ids
    if overlap:
        raise EpisodeEvaluationError(f"episode split leakage: {sorted(overlap)[0]}")


def _eligible_train(rows: list[EvaluationRow], config: EpisodeEvaluationConfig) -> bool:
    targets = [row.target for row in rows]
    return (
        len(rows) >= config.min_train_rows
        and targets.count(0) >= config.min_class_count
        and targets.count(1) >= config.min_class_count
    )


def _predict(
    candidate: str,
    train: list[EvaluationRow],
    test: list[EvaluationRow],
    config: EpisodeEvaluationConfig,
) -> list[float]:
    frequency = sum(row.target for row in train) / len(train)
    if candidate == "historical_frequency":
        return [frequency] * len(test)
    if candidate == "persistence":
        return [
            frequency if row.current_active is None else float(row.current_active)
            for row in test
        ]
    if candidate == "seasonal_climatology":
        by_month: dict[int, list[int]] = defaultdict(list)
        for row in train:
            by_month[date.fromisoformat(row.target_date).month].append(row.target)
        return [
            sum(by_month[month]) / len(by_month[month]) if by_month[month] else frequency
            for row in test
            for month in [date.fromisoformat(row.target_date).month]
        ]
    estimator = _estimator(candidate, config.seed)
    estimator.fit([row.features for row in train], [row.target for row in train])
    return [float(value[1]) for value in estimator.predict_proba([row.features for row in test])]


def _estimator(candidate: str, seed: int) -> Pipeline:
    if candidate == "logistic_regression":
        model: Any = LogisticRegression(random_state=seed, max_iter=1000, solver="lbfgs")
    elif candidate == "hist_gradient_boosting":
        model = HistGradientBoostingClassifier(
            random_state=seed, max_iter=100, learning_rate=0.08, max_leaf_nodes=15
        )
    else:
        raise EpisodeEvaluationError(f"unknown candidate: {candidate}")
    return Pipeline(
        [
            ("vectorize", DictVectorizer(sparse=False)),
            ("impute", SimpleImputer(strategy="median", keep_empty_features=True)),
            ("scale", StandardScaler()),
            ("model", model),
        ]
    )


def _predicted_episode(
    candidate: str,
    region: str,
    horizon: int,
    values: list[OofEpisodePrediction],
) -> PredictedEpisode:
    ordered = sorted(values, key=lambda item: item.target_date)
    identity = {
        "candidate": candidate,
        "region": region,
        "horizon": horizon,
        "from": ordered[0].target_date,
        "to": ordered[-1].target_date,
    }
    return PredictedEpisode(
        predicted_episode_id=f"predicted:{hashlib.sha256(canonical_json(identity).encode()).hexdigest()[:20]}",
        candidate=candidate,
        horizon_days=horizon,
        region_id=region,
        valid_from=ordered[0].target_date,
        valid_to=ordered[-1].target_date,
        issued_from=min(item.as_of for item in ordered),
        max_probability=max(item.probability for item in ordered),
        point_count=len(ordered),
    )


def _match_episodes(
    actual: Iterable[ActualEpisode], predicted: Iterable[PredictedEpisode]
) -> list[tuple[ActualEpisode, PredictedEpisode]]:
    candidates = []
    for truth in actual:
        for forecast in predicted:
            if truth.region_id != forecast.region_id:
                continue
            start = max(date.fromisoformat(truth.valid_from), date.fromisoformat(forecast.valid_from))
            end = min(date.fromisoformat(truth.valid_to), date.fromisoformat(forecast.valid_to))
            if start <= end:
                candidates.append(((end - start).days + 1, truth, forecast))
    matched_actual: set[str] = set()
    matched_predicted: set[str] = set()
    result = []
    for _, truth, forecast in sorted(
        candidates,
        key=lambda item: (-item[0], item[1].episode_id, item[2].predicted_episode_id),
    ):
        if truth.episode_id in matched_actual or forecast.predicted_episode_id in matched_predicted:
            continue
        matched_actual.add(truth.episode_id)
        matched_predicted.add(forecast.predicted_episode_id)
        result.append((truth, forecast))
    return result


def _mean(values: list[int]) -> float | None:
    return sum(values) / len(values) if values else None


def _bounded(value: float) -> float:
    if not math.isfinite(value):
        raise EpisodeEvaluationError("candidate produced non-finite probability")
    return min(1.0, max(0.0, value))


def _hash(value: object) -> str:
    return f"sha256:{hashlib.sha256(canonical_json(value).encode()).hexdigest()}"


def _jsonl(path: Path) -> tuple[dict[str, Any], ...]:
    return tuple(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines())


def _as_date(value: str) -> date:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
