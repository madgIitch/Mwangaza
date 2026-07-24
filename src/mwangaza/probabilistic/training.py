from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

import sklearn
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_extraction import DictVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from mwangaza.probabilistic.dataset import TrainingDataset, TrainingRow

TRAINING_SCHEMA_VERSION = "mwangaza.probabilistic-training-run.v1"
MODEL_ORDER = (
    "persistence",
    "seasonal_climatology",
    "historical_frequency",
    "logistic_regression",
    "hist_gradient_boosting",
)


class TrainingValidationError(ValueError):
    """Raised when a training request violates the temporal contract."""


@dataclass(frozen=True)
class TrainingConfig:
    seed: int = 2026
    initial_train_periods: int = 36
    min_train_rows: int = 20
    min_class_count: int = 2
    improvement_tolerance: float = 1e-12

    def __post_init__(self) -> None:
        if self.initial_train_periods < 2:
            raise TrainingValidationError("initial_train_periods must be at least 2")
        if self.min_train_rows < 4:
            raise TrainingValidationError("min_train_rows must be at least 4")
        if self.min_class_count < 1:
            raise TrainingValidationError("min_class_count must be positive")
        if self.improvement_tolerance < 0 or not math.isfinite(self.improvement_tolerance):
            raise TrainingValidationError("improvement_tolerance must be finite and non-negative")


@dataclass(frozen=True)
class FoldSummary:
    fold: int
    train_end: str
    test_as_of: str
    gap_periods: int
    train_rows: int
    test_rows: int


@dataclass(frozen=True)
class OofPrediction:
    region_id: str
    as_of: str
    actual: int
    probability: float
    fold: int


@dataclass(frozen=True)
class CandidateResult:
    name: str
    status: str
    reason: str
    brier_score: float | None
    predictions: tuple[OofPrediction, ...]
    parameters: dict[str, Any]


@dataclass(frozen=True)
class HorizonTrainingResult:
    horizon_periods: int
    horizon_days: int | None
    status: str
    reason: str
    selected_model: str | None
    candidates: tuple[CandidateResult, ...]
    folds: tuple[FoldSummary, ...]
    trained_until: str | None


@dataclass(frozen=True)
class TrainingRun:
    schema_version: str
    dataset_hash: str
    feature_manifest_version: str
    threshold_versions: tuple[str, ...]
    seed: int
    sklearn_version: str
    results: tuple[HorizonTrainingResult, ...]
    run_hash: str


def train_risk_candidates(
    dataset: TrainingDataset, config: TrainingConfig | None = None
) -> TrainingRun:
    resolved = config or TrainingConfig()
    _validate_dataset(dataset)
    results = tuple(
        _train_horizon(dataset, horizon, resolved)
        for horizon in sorted({row.horizon_periods for row in dataset.rows})
    )
    base = {
        "schema_version": TRAINING_SCHEMA_VERSION,
        "dataset_hash": dataset.dataset_hash,
        "feature_manifest_version": dataset.feature_manifest_version,
        "threshold_versions": tuple(
            sorted(
                {
                    row.lineage["threshold_version"]
                    for row in dataset.rows
                    if row.lineage.get("threshold_version")
                }
            )
        ),
        "seed": resolved.seed,
        "sklearn_version": sklearn.__version__,
        "results": results,
    }
    digest = hashlib.sha256(_canonical_json(base).encode("utf-8")).hexdigest()
    return TrainingRun(**base, run_hash=f"sha256:{digest}")


def canonical_training_run_json(run: TrainingRun) -> str:
    return _canonical_json(run) + "\n"


def _train_horizon(
    dataset: TrainingDataset, horizon: int, config: TrainingConfig
) -> HorizonTrainingResult:
    rows = [
        row for row in dataset.rows if row.horizon_periods == horizon and row.target is not None
    ]
    dates = sorted({row.as_of for row in rows})
    if len(dates) <= config.initial_train_periods + horizon:
        return _rejected_horizon(horizon, rows, "insufficient_periods")

    predictions: dict[str, list[OofPrediction]] = {name: [] for name in MODEL_ORDER}
    failures: dict[str, str] = {}
    folds: list[FoldSummary] = []
    for test_index in range(config.initial_train_periods + horizon, len(dates)):
        test_date = dates[test_index]
        train_end_index = test_index - horizon - 1
        train_dates = set(dates[: train_end_index + 1])
        train_rows = [row for row in rows if row.as_of in train_dates]
        test_rows = [row for row in rows if row.as_of == test_date]
        if not _eligible_training_rows(train_rows, config):
            continue
        fold_number = len(folds)
        folds.append(
            FoldSummary(
                fold=fold_number,
                train_end=dates[train_end_index],
                test_as_of=test_date,
                gap_periods=horizon,
                train_rows=len(train_rows),
                test_rows=len(test_rows),
            )
        )
        y_train = [int(row.target) for row in train_rows if row.target is not None]
        for name in MODEL_ORDER:
            try:
                probabilities = _predict_candidate(
                    name, train_rows, test_rows, y_train, dataset.feature_names, config.seed
                )
            except (ValueError, TypeError) as exc:
                failures.setdefault(name, type(exc).__name__)
                continue
            for row, probability in zip(test_rows, probabilities, strict=True):
                predictions[name].append(
                    OofPrediction(
                        region_id=row.region_id,
                        as_of=row.as_of,
                        actual=int(row.target),
                        probability=_bounded(probability),
                        fold=fold_number,
                    )
                )

    candidates = tuple(
        _candidate_result(name, predictions[name], failures.get(name, "")) for name in MODEL_ORDER
    )
    if not folds:
        return _rejected_horizon(horizon, rows, "no_eligible_folds", candidates=candidates)
    by_name = {candidate.name: candidate for candidate in candidates}
    persistence = by_name["persistence"].brier_score
    climatology = by_name["seasonal_climatology"].brier_score
    ml = [
        candidate
        for candidate in candidates
        if candidate.name in {"logistic_regression", "hist_gradient_boosting"}
        and candidate.brier_score is not None
    ]
    if persistence is None or climatology is None or not ml:
        return _rejected_horizon(
            horizon, rows, "baseline_or_ml_unavailable", candidates=candidates, folds=tuple(folds)
        )
    best = min(ml, key=lambda item: (item.brier_score, MODEL_ORDER.index(item.name)))  # type: ignore[arg-type]
    threshold = min(persistence, climatology) - config.improvement_tolerance
    if best.brier_score is None or best.brier_score >= threshold:
        return HorizonTrainingResult(
            horizon_periods=horizon,
            horizon_days=_horizon_days(rows),
            status="rejected_insufficient_skill",
            reason="ml_did_not_improve_persistence_and_climatology",
            selected_model=None,
            candidates=candidates,
            folds=tuple(folds),
            trained_until=max(row.as_of for row in rows),
        )
    return HorizonTrainingResult(
        horizon_periods=horizon,
        horizon_days=_horizon_days(rows),
        status="selected",
        reason="best_out_of_sample_brier",
        selected_model=best.name,
        candidates=candidates,
        folds=tuple(folds),
        trained_until=max(row.as_of for row in rows),
    )


def _predict_candidate(
    name: str,
    train_rows: list[TrainingRow],
    test_rows: list[TrainingRow],
    y_train: list[int],
    feature_names: tuple[str, ...],
    seed: int,
) -> list[float]:
    if name == "persistence":
        return [float(row.features.get("current_severe") or 0.0) for row in test_rows]
    if name == "historical_frequency":
        probability = sum(y_train) / len(y_train)
        return [probability] * len(test_rows)
    if name == "seasonal_climatology":
        return [_seasonal_probability(train_rows, row) for row in test_rows]
    estimator = _estimator(name, seed, feature_names)
    x_train = [_record(row, feature_names) for row in train_rows]
    x_test = [_record(row, feature_names) for row in test_rows]
    estimator.fit(x_train, y_train)
    return [float(item[1]) for item in estimator.predict_proba(x_test)]


def _estimator(name: str, seed: int, feature_names: tuple[str, ...]) -> Pipeline:
    del feature_names
    if name == "logistic_regression":
        model: Any = LogisticRegression(random_state=seed, max_iter=1000, solver="lbfgs")
    elif name == "hist_gradient_boosting":
        model = HistGradientBoostingClassifier(
            random_state=seed, max_iter=100, learning_rate=0.08, max_leaf_nodes=15
        )
    else:
        raise TrainingValidationError("unknown candidate")
    return Pipeline(
        [
            ("vectorize", DictVectorizer(sparse=False)),
            ("impute", SimpleImputer(strategy="median", keep_empty_features=True)),
            ("scale", StandardScaler()),
            ("model", model),
        ]
    )


def _record(row: TrainingRow, feature_names: tuple[str, ...]) -> dict[str, Any]:
    return {"region_id": row.region_id} | {
        name: row.features.get(name) if row.features.get(name) is not None else math.nan
        for name in feature_names
    }


def _seasonal_probability(train_rows: list[TrainingRow], test_row: TrainingRow) -> float:
    test_season = _season(test_row.as_of)
    matching = [
        int(row.target)
        for row in train_rows
        if row.target is not None and _season(row.as_of) == test_season
    ]
    values = matching or [int(row.target) for row in train_rows if row.target is not None]
    return sum(values) / len(values)


def _season(value: str) -> int:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return (parsed.month - 1) * 3 + (1 if parsed.day <= 10 else 2 if parsed.day <= 20 else 3)


def _eligible_training_rows(rows: list[TrainingRow], config: TrainingConfig) -> bool:
    targets = [int(row.target) for row in rows if row.target is not None]
    return (
        len(targets) >= config.min_train_rows
        and targets.count(0) >= config.min_class_count
        and targets.count(1) >= config.min_class_count
    )


def _candidate_result(name: str, predictions: list[OofPrediction], failure: str) -> CandidateResult:
    if not predictions:
        return CandidateResult(
            name=name,
            status="rejected",
            reason=failure or "no_oof_predictions",
            brier_score=None,
            predictions=(),
            parameters=_parameters(name),
        )
    brier = sum((item.probability - item.actual) ** 2 for item in predictions) / len(predictions)
    return CandidateResult(
        name=name,
        status="evaluated",
        reason="out_of_sample",
        brier_score=brier,
        predictions=tuple(predictions),
        parameters=_parameters(name),
    )


def _parameters(name: str) -> dict[str, Any]:
    if name == "logistic_regression":
        return {"solver": "lbfgs", "max_iter": 1000}
    if name == "hist_gradient_boosting":
        return {"max_iter": 100, "learning_rate": 0.08, "max_leaf_nodes": 15}
    return {"kind": name}


def _rejected_horizon(
    horizon: int,
    rows: list[TrainingRow],
    reason: str,
    *,
    candidates: tuple[CandidateResult, ...] = (),
    folds: tuple[FoldSummary, ...] = (),
) -> HorizonTrainingResult:
    return HorizonTrainingResult(
        horizon_periods=horizon,
        horizon_days=_horizon_days(rows),
        status="rejected_insufficient_skill",
        reason=reason,
        selected_model=None,
        candidates=candidates,
        folds=folds,
        trained_until=max((row.as_of for row in rows), default=None),
    )


def _horizon_days(rows: list[TrainingRow]) -> int | None:
    return next((row.horizon_days for row in rows if row.horizon_days is not None), None)


def _bounded(value: float) -> float:
    if not math.isfinite(value):
        raise TrainingValidationError("candidate produced non-finite probability")
    return min(1.0, max(0.0, value))


def _validate_dataset(dataset: TrainingDataset) -> None:
    if not dataset.dataset_hash.startswith("sha256:"):
        raise TrainingValidationError("dataset_hash is invalid")
    if dataset.frequency != "dekadal":
        raise TrainingValidationError("Sprint 62 requires a dekadal dataset")
    if not dataset.rows:
        raise TrainingValidationError("dataset rows are empty")


def _canonical_json(value: Any) -> str:
    def default(item: Any) -> Any:
        if hasattr(item, "__dataclass_fields__"):
            return asdict(item)
        raise TypeError(f"unsupported type {type(item).__name__}")

    return json.dumps(
        value,
        default=default,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
