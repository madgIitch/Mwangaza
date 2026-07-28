from __future__ import annotations

import hashlib
import math
import random
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date
from typing import Any, Callable, Iterable, Mapping, Sequence

from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_extraction import DictVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from mwangaza.probabilistic.continuation_calibration import (
    HybridGateConfig,
    PlattParameters,
    assert_pre_holdout,
    build_nested_calibration_folds,
)
from mwangaza.probabilistic.episode_evaluation import ActualEpisode
from mwangaza.probabilistic.survival import SurvivalRow, canonical_json

SCHEMA_VERSION = "mwangaza.drought-continuation-ml-sanity-audit.v1"
CANDIDATE_FIELDS = {
    "phase_survival": "baseline_probability",
    "hgb_weighted_missing_raw": "hgb_raw_probability",
    "hgb_weighted_missing_platt_annual": "hgb_annual_probability",
    "hgb_weighted_missing_platt_pooled": "hgb_pooled_probability",
    "discrete_time_logistic_hazard": "hazard_probability",
}


class MlSanityAuditError(RuntimeError):
    """Raised when an ML audit would leak time or lose statistical meaning."""


@dataclass(frozen=True)
class AuditConfig:
    evaluation_years: tuple[int, ...] = (2021, 2022, 2023)
    holdout_cutoff: str = "2024-01-01"
    horizon_days: int = 30
    inner_first_year: int = 2018
    bootstrap_iterations: int = 2000
    confidence_level: float = 0.95
    max_ece: float = 0.15
    seed: int = 2026
    hazard_c_grid: tuple[float, ...] = (0.1, 1.0, 10.0)

    def __post_init__(self) -> None:
        if self.horizon_days != 30:
            raise MlSanityAuditError("the audit is frozen to the 30-day horizon")
        if tuple(sorted(self.evaluation_years)) != self.evaluation_years:
            raise MlSanityAuditError("evaluation years must be ordered")
        if self.bootstrap_iterations < 100:
            raise MlSanityAuditError("bootstrap_iterations must be at least 100")
        if not 0 < self.confidence_level < 1:
            raise MlSanityAuditError("confidence_level must be between zero and one")
        if not self.hazard_c_grid or any(value <= 0 for value in self.hazard_c_grid):
            raise MlSanityAuditError("hazard C grid must be positive")


@dataclass(frozen=True)
class HgbParameters:
    max_leaf_nodes: int
    learning_rate: float
    max_iter: int
    min_samples_leaf: int
    l2_regularization: float = 0.0

    def __post_init__(self) -> None:
        if self.max_leaf_nodes < 2 or self.learning_rate <= 0 or self.max_iter < 1:
            raise MlSanityAuditError("invalid HGB audit parameters")
        if self.min_samples_leaf < 1 or self.l2_regularization < 0:
            raise MlSanityAuditError("invalid HGB regularization parameters")


def audit_config_from_mapping(value: Mapping[str, Any]) -> AuditConfig:
    payload = dict(value)
    for name in ("evaluation_years", "hazard_c_grid"):
        if name in payload:
            payload[name] = tuple(payload[name])
    return AuditConfig(**payload)


def hgb_grid_from_sequence(values: Sequence[Mapping[str, Any]]) -> tuple[HgbParameters, ...]:
    if not values or len(values) > 8:
        raise MlSanityAuditError("HGB grid must contain between one and eight entries")
    result = tuple(HgbParameters(**dict(item)) for item in values)
    if len({canonical_json(asdict(item)) for item in result}) != len(result):
        raise MlSanityAuditError("HGB grid entries must be unique")
    return result


def episode_equal_weights(rows: Iterable[SurvivalRow]) -> list[float]:
    values = tuple(rows)
    counts: dict[str, int] = defaultdict(int)
    for row in values:
        counts[row.episode_id] += 1
    return [1.0 / counts[row.episode_id] for row in values]


def audit_ml_sanity(
    rows: Iterable[SurvivalRow],
    episodes: Iterable[ActualEpisode],
    *,
    hgb_grid: Sequence[HgbParameters],
    input_hashes: Mapping[str, str],
    config: AuditConfig | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> dict[str, Any]:
    resolved = config or AuditConfig()
    row_values = tuple(rows)
    episode_values = tuple(episodes)
    _validate_hashes(input_hashes)
    assert_pre_holdout(
        row_values,
        episode_values,
        HybridGateConfig(
            evaluation_years=resolved.evaluation_years,
            holdout_cutoff=resolved.holdout_cutoff,
        ),
    )
    if len(hgb_grid) > 8:
        raise MlSanityAuditError("HGB grid exceeds eight frozen configurations")
    gate_config = HybridGateConfig(
        evaluation_years=resolved.evaluation_years,
        holdout_cutoff=resolved.holdout_cutoff,
    )
    folds = build_nested_calibration_folds(row_values, episode_values, gate_config)
    by_episode = _rows_by_episode(row_values)
    oof: list[dict[str, Any]] = []
    selections = []
    total_steps = len(folds) * (len(hgb_grid) + len(resolved.hazard_c_grid) + 5)
    completed = 0
    for fold in folds:
        calibration_year = fold.evaluation_year - 1
        inner_years = tuple(range(resolved.inner_first_year, calibration_year))
        hgb_selection = select_hgb_parameters(
            row_values,
            episode_values,
            hgb_grid,
            inner_years,
            resolved,
        )
        completed += len(hgb_grid)
        if progress:
            progress(completed, total_steps)
        hazard_selection = select_hazard_c(
            row_values,
            episode_values,
            resolved.hazard_c_grid,
            inner_years,
            resolved,
        )
        completed += len(resolved.hazard_c_grid)
        if progress:
            progress(completed, total_steps)

        base = _known_rows(by_episode, fold.base_episode_ids, resolved.horizon_days)
        calibration = _known_rows(by_episode, fold.calibration_episode_ids, resolved.horizon_days)
        evaluation = _known_rows(by_episode, fold.evaluation_episode_ids, resolved.horizon_days)
        development = tuple(sorted((*base, *calibration), key=_row_key))
        _require_binary(base, f"outer-base-{fold.evaluation_year}")
        _require_binary(calibration, f"annual-calibration-{fold.evaluation_year}")
        _require_binary(evaluation, f"outer-evaluation-{fold.evaluation_year}")

        final_hgb = fit_hgb(development, hgb_selection["parameters"], resolved)
        hgb_raw = predict_continuation(final_hgb, evaluation)
        baseline = phase_survival_predictions(development, evaluation, resolved.horizon_days)
        completed += 1
        if progress:
            progress(completed, total_steps)

        annual_hgb = fit_hgb(base, hgb_selection["parameters"], resolved)
        annual_calibrator = fit_weighted_platt(
            predict_continuation(annual_hgb, calibration),
            _targets(calibration, resolved.horizon_days),
            episode_equal_weights(calibration),
            seed=resolved.seed,
        )
        hgb_annual = annual_calibrator.predict(predict_continuation(annual_hgb, evaluation))
        completed += 1
        if progress:
            progress(completed, total_steps)

        pooled_history = temporal_oof_predictions(
            row_values,
            episode_values,
            hgb_selection["parameters"],
            tuple(range(resolved.inner_first_year, fold.evaluation_year)),
            resolved,
            estimator_kind="hgb",
        )
        pooled_calibrator = fit_weighted_platt(
            (item["probability"] for item in pooled_history),
            (item["actual"] for item in pooled_history),
            _mapping_episode_weights(pooled_history),
            seed=resolved.seed,
        )
        hgb_pooled = pooled_calibrator.predict(hgb_raw)
        completed += 1
        if progress:
            progress(completed, total_steps)

        hazard = fit_hazard(development, float(hazard_selection["c"]), resolved)
        hazard_probability = predict_hazard_continuation(hazard, evaluation)
        completed += 1
        if progress:
            progress(completed, total_steps)

        for row, base_p, raw_p, annual_p, pooled_p, hazard_p in zip(
            evaluation,
            baseline,
            hgb_raw,
            hgb_annual,
            hgb_pooled,
            hazard_probability,
            strict=True,
        ):
            oof.append(
                {
                    "evaluation_year": fold.evaluation_year,
                    "sample_id": row.sample_id,
                    "episode_id": row.episode_id,
                    "region_id": row.region_id,
                    "as_of": row.as_of,
                    "actual": int(row.targets[resolved.horizon_days]),
                    "baseline_probability": base_p,
                    "hgb_raw_probability": raw_p,
                    "hgb_annual_probability": annual_p,
                    "hgb_pooled_probability": pooled_p,
                    "hazard_probability": hazard_p,
                }
            )
        selections.append(
            {
                "evaluation_year": fold.evaluation_year,
                "hgb": {
                    "parameters": asdict(hgb_selection["parameters"]),
                    "scores": hgb_selection["scores"],
                },
                "hazard": hazard_selection,
                "annual_calibration_known": len(calibration),
                "annual_calibration_episodes": len({row.episode_id for row in calibration}),
                "pooled_calibration_known": len(pooled_history),
                "pooled_calibration_episodes": len({item["episode_id"] for item in pooled_history}),
                "missing_indicator_columns": {
                    "hgb": missing_indicator_count(final_hgb),
                    "hazard": missing_indicator_count(hazard),
                },
            }
        )
        completed += 1
        if progress:
            progress(completed, total_steps)

    baseline_metrics = audit_probability_metrics(oof, CANDIDATE_FIELDS["phase_survival"])
    candidate_results = []
    bootstrap_results = []
    for candidate, field in CANDIDATE_FIELDS.items():
        metrics = audit_probability_metrics(oof, field, baseline_metrics)
        if candidate == "phase_survival":
            bootstrap = {
                "candidate": candidate,
                "iterations": resolved.bootstrap_iterations,
                "point_delta_brier": 0.0,
                "lower_95": 0.0,
                "upper_95": 0.0,
            }
            verdict = "reference"
            improved_folds = 0
        else:
            bootstrap = clustered_episode_bootstrap(
                oof,
                candidate_field=field,
                baseline_field=CANDIDATE_FIELDS["phase_survival"],
                iterations=resolved.bootstrap_iterations,
                confidence_level=resolved.confidence_level,
                seed=resolved.seed + len(candidate_results),
            )
            improved_folds = sum(
                1
                for year, score in metrics["fold_brier"].items()
                if score < baseline_metrics["fold_brier"][year]
            )
            verdict = skill_verdict(metrics, bootstrap, improved_folds, resolved)
        candidate_results.append(
            {
                "candidate": candidate,
                "verdict": verdict,
                "improved_outer_folds": improved_folds,
                "metrics": metrics,
                "bootstrap": bootstrap,
            }
        )
        bootstrap_results.append(bootstrap)

    ranked = sorted(
        (item for item in candidate_results if item["candidate"] != "phase_survival"),
        key=lambda item: (
            {"robust_skill": 0, "inconclusive": 1, "no_skill": 2}[item["verdict"]],
            item["metrics"]["episode_weighted_brier"],
            item["candidate"],
        ),
    )
    base_payload = {
        "schema_version": SCHEMA_VERSION,
        "target": "same_episode_continues",
        "horizon_days": resolved.horizon_days,
        "config": asdict(resolved),
        "hgb_grid": [asdict(item) for item in hgb_grid],
        "input_hashes": dict(sorted(input_hashes.items())),
        "episode_weighting": "each_episode_total_weight_one",
        "fold_selections": selections,
        "candidates": candidate_results,
        "bootstrap": bootstrap_results,
        "recommended_candidate": ranked[0]["candidate"],
        "recommendation": ranked[0]["verdict"],
        "oof_count": len(oof),
        "oof_episode_count": len({item["episode_id"] for item in oof}),
        "oof_sha256": _hash(oof),
        "holdout_rows_used": 0,
    }
    return {
        **base_payload,
        "run_hash": _hash(base_payload),
        "oof_predictions": oof,
    }


def select_hgb_parameters(
    rows: Sequence[SurvivalRow],
    episodes: Sequence[ActualEpisode],
    grid: Sequence[HgbParameters],
    inner_years: Sequence[int],
    config: AuditConfig,
) -> dict[str, Any]:
    scores = []
    for parameters in grid:
        predictions = temporal_oof_predictions(
            rows,
            episodes,
            parameters,
            inner_years,
            config,
            estimator_kind="hgb",
        )
        score = mapping_episode_weighted_brier(predictions, "probability")
        scores.append({"parameters": asdict(parameters), "episode_weighted_brier": score})
    selected = min(
        scores,
        key=lambda item: (item["episode_weighted_brier"], canonical_json(item["parameters"])),
    )
    return {"parameters": HgbParameters(**selected["parameters"]), "scores": scores}


def select_hazard_c(
    rows: Sequence[SurvivalRow],
    episodes: Sequence[ActualEpisode],
    grid: Sequence[float],
    inner_years: Sequence[int],
    config: AuditConfig,
) -> dict[str, Any]:
    scores = []
    for c_value in grid:
        predictions = temporal_oof_predictions(
            rows,
            episodes,
            float(c_value),
            inner_years,
            config,
            estimator_kind="hazard",
        )
        score = mapping_episode_weighted_brier(predictions, "probability")
        scores.append({"c": float(c_value), "episode_weighted_brier": score})
    selected = min(scores, key=lambda item: (item["episode_weighted_brier"], item["c"]))
    return {"c": selected["c"], "scores": scores}


def temporal_oof_predictions(
    rows: Sequence[SurvivalRow],
    episodes: Sequence[ActualEpisode],
    parameters: HgbParameters | float,
    years: Sequence[int],
    config: AuditConfig,
    *,
    estimator_kind: str,
) -> list[dict[str, Any]]:
    by_episode = _rows_by_episode(rows)
    result = []
    for year in years:
        train_ids = _episode_ids_before(episodes, date(year, 1, 1))
        test_ids = _episode_ids_within_year(episodes, year)
        train = _known_rows(by_episode, train_ids, config.horizon_days)
        test = _known_rows(by_episode, test_ids, config.horizon_days)
        if not _has_both_classes(train, config.horizon_days) or not _has_both_classes(
            test, config.horizon_days
        ):
            continue
        if estimator_kind == "hgb":
            if not isinstance(parameters, HgbParameters):
                raise MlSanityAuditError("HGB temporal OOF requires HgbParameters")
            estimator = fit_hgb(train, parameters, config)
            probabilities = predict_continuation(estimator, test)
        elif estimator_kind == "hazard":
            estimator = fit_hazard(train, float(parameters), config)
            probabilities = predict_hazard_continuation(estimator, test)
        else:
            raise MlSanityAuditError(f"unknown audit estimator: {estimator_kind}")
        for row, probability in zip(test, probabilities, strict=True):
            result.append(
                {
                    "year": year,
                    "episode_id": row.episode_id,
                    "actual": int(row.targets[config.horizon_days]),
                    "probability": probability,
                }
            )
    if not result:
        raise MlSanityAuditError("temporal OOF produced no evaluable predictions")
    return result


def fit_hgb(
    rows: Sequence[SurvivalRow], parameters: HgbParameters, config: AuditConfig
) -> Pipeline:
    estimator = _audit_pipeline(
        HistGradientBoostingClassifier(
            random_state=config.seed,
            max_leaf_nodes=parameters.max_leaf_nodes,
            learning_rate=parameters.learning_rate,
            max_iter=parameters.max_iter,
            min_samples_leaf=parameters.min_samples_leaf,
            l2_regularization=parameters.l2_regularization,
        )
    )
    estimator.fit(
        [_audit_features(row) for row in rows],
        _targets(rows, config.horizon_days),
        model__sample_weight=episode_equal_weights(rows),
    )
    return estimator


def fit_hazard(rows: Sequence[SurvivalRow], c_value: float, config: AuditConfig) -> Pipeline:
    estimator = _audit_pipeline(
        LogisticRegression(
            C=c_value,
            random_state=config.seed,
            max_iter=2000,
            solver="lbfgs",
        )
    )
    continuation = _targets(rows, config.horizon_days)
    recovery = [1 - target for target in continuation]
    estimator.fit(
        [_hazard_features(row) for row in rows],
        recovery,
        model__sample_weight=episode_equal_weights(rows),
    )
    return estimator


def predict_continuation(estimator: Pipeline, rows: Sequence[SurvivalRow]) -> list[float]:
    return [
        float(value[1]) for value in estimator.predict_proba([_audit_features(row) for row in rows])
    ]


def predict_hazard_continuation(estimator: Pipeline, rows: Sequence[SurvivalRow]) -> list[float]:
    return [
        1 - float(value[1])
        for value in estimator.predict_proba([_hazard_features(row) for row in rows])
    ]


def hazard_feature_record(row: SurvivalRow) -> dict[str, float | str | None]:
    """Return the frozen discrete-hazard feature record used by fit and inference."""

    return _hazard_features(row)


def fit_weighted_platt(
    probabilities: Iterable[float],
    targets: Iterable[int],
    sample_weights: Iterable[float],
    *,
    seed: int,
) -> PlattParameters:
    probability_values = tuple(float(value) for value in probabilities)
    target_values = tuple(int(value) for value in targets)
    weight_values = tuple(float(value) for value in sample_weights)
    if not probability_values or len(probability_values) != len(target_values):
        raise MlSanityAuditError("weighted Platt inputs must be aligned")
    if len(weight_values) != len(target_values) or set(target_values) != {0, 1}:
        raise MlSanityAuditError("weighted Platt requires aligned weights and both classes")
    estimator = LogisticRegression(random_state=seed, solver="lbfgs", max_iter=2000)
    estimator.fit(
        [[_logit(value)] for value in probability_values],
        target_values,
        sample_weight=weight_values,
    )
    return PlattParameters(
        coefficient=float(estimator.coef_[0][0]),
        intercept=float(estimator.intercept_[0]),
        version="episode-weighted-platt-logit-v1",
    )


def phase_survival_predictions(
    train: Sequence[SurvivalRow], test: Sequence[SurvivalRow], horizon: int
) -> list[float]:
    weights = episode_equal_weights(train)
    by_phase_weight: dict[str, float] = defaultdict(float)
    by_phase_total: dict[str, float] = defaultdict(float)
    weighted_positive = 0.0
    total_weight = 0.0
    for row, weight in zip(train, weights, strict=True):
        target = row.targets[horizon]
        if target is None:
            continue
        by_phase_weight[row.current_phase] += weight * int(target)
        by_phase_total[row.current_phase] += weight
        weighted_positive += weight * int(target)
        total_weight += weight
    if not total_weight:
        raise MlSanityAuditError("phase baseline lacks weighted support")
    fallback = weighted_positive / total_weight
    return [
        by_phase_weight[row.current_phase] / by_phase_total[row.current_phase]
        if by_phase_total[row.current_phase]
        else fallback
        for row in test
    ]


def audit_probability_metrics(
    rows: Sequence[Mapping[str, Any]],
    probability_field: str,
    baseline: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    values = [row for row in rows if row.get(probability_field) is not None]
    if not values:
        raise MlSanityAuditError(f"no predictions for {probability_field}")
    weights = _mapping_episode_weights(values)
    total_weight = sum(weights)
    probabilities = [_bounded(float(row[probability_field])) for row in values]
    targets = [int(row["actual"]) for row in values]
    weighted_brier = (
        sum(
            weight * (probability - target) ** 2
            for weight, probability, target in zip(weights, probabilities, targets, strict=True)
        )
        / total_weight
    )
    unweighted_brier = sum(
        (probability - target) ** 2
        for probability, target in zip(probabilities, targets, strict=True)
    ) / len(values)
    weighted_log_loss = (
        -sum(
            weight
            * (
                target * math.log(_clip(probability))
                + (1 - target) * math.log(_clip(1 - probability))
            )
            for weight, probability, target in zip(weights, probabilities, targets, strict=True)
        )
        / total_weight
    )
    bins = _weighted_calibration_bins(probabilities, targets, weights)
    ece = sum(
        item["weight"]
        / total_weight
        * abs(float(item["mean_probability"]) - float(item["observed_frequency"]))
        for item in bins
        if item["weight"]
    )
    fold_brier = {}
    for year in sorted({int(row["evaluation_year"]) for row in values}):
        fold_rows = [row for row in values if int(row["evaluation_year"]) == year]
        fold_brier[str(year)] = mapping_episode_weighted_brier(fold_rows, probability_field)
    baseline_brier = float(baseline["episode_weighted_brier"]) if baseline else weighted_brier
    return {
        "probability_field": probability_field,
        "known_count": len(values),
        "episode_count": len({row["episode_id"] for row in values}),
        "positive_count": sum(targets),
        "negative_count": len(targets) - sum(targets),
        "episode_weighted_brier": weighted_brier,
        "unweighted_brier": unweighted_brier,
        "baseline_episode_weighted_brier": baseline_brier,
        "episode_weighted_bss": 0.0 if baseline is None else 1 - weighted_brier / baseline_brier,
        "episode_weighted_log_loss": weighted_log_loss,
        "episode_weighted_ece": ece,
        "calibration_bins": bins,
        "fold_brier": fold_brier,
    }


def mapping_episode_weighted_brier(
    rows: Sequence[Mapping[str, Any]], probability_field: str
) -> float:
    weights = _mapping_episode_weights(rows)
    total = sum(weights)
    return (
        sum(
            weight * (float(row[probability_field]) - int(row["actual"])) ** 2
            for row, weight in zip(rows, weights, strict=True)
        )
        / total
    )


def clustered_episode_bootstrap(
    rows: Sequence[Mapping[str, Any]],
    *,
    candidate_field: str,
    baseline_field: str,
    iterations: int,
    confidence_level: float,
    seed: int,
) -> dict[str, Any]:
    by_episode: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        if row.get(candidate_field) is None or row.get(baseline_field) is None:
            continue
        candidate_error = (float(row[candidate_field]) - int(row["actual"])) ** 2
        baseline_error = (float(row[baseline_field]) - int(row["actual"])) ** 2
        by_episode[str(row["episode_id"])].append(candidate_error - baseline_error)
    episode_deltas = [sum(values) / len(values) for _, values in sorted(by_episode.items())]
    if len(episode_deltas) < 2:
        raise MlSanityAuditError("cluster bootstrap requires at least two episodes")
    generator = random.Random(seed)
    samples = []
    for _ in range(iterations):
        sample = [generator.choice(episode_deltas) for _ in episode_deltas]
        samples.append(sum(sample) / len(sample))
    samples.sort()
    alpha = (1 - confidence_level) / 2
    return {
        "candidate_field": candidate_field,
        "iterations": iterations,
        "episode_count": len(episode_deltas),
        "point_delta_brier": sum(episode_deltas) / len(episode_deltas),
        "lower_95": _quantile(samples, alpha),
        "upper_95": _quantile(samples, 1 - alpha),
        "seed": seed,
    }


def skill_verdict(
    metrics: Mapping[str, Any],
    bootstrap: Mapping[str, Any],
    improved_folds: int,
    config: AuditConfig,
) -> str:
    improves = float(metrics["episode_weighted_brier"]) < float(
        metrics["baseline_episode_weighted_brier"]
    )
    if not improves:
        return "no_skill"
    robust = (
        float(bootstrap["upper_95"]) < 0
        and improved_folds >= 2
        and float(metrics["episode_weighted_ece"]) <= config.max_ece
    )
    return "robust_skill" if robust else "inconclusive"


def missing_indicator_count(estimator: Pipeline) -> int:
    imputer = estimator.named_steps["impute"]
    indicator = getattr(imputer, "indicator_", None)
    return len(indicator.features_) if indicator is not None else 0


def _audit_pipeline(model: Any) -> Pipeline:
    return Pipeline(
        [
            ("vectorize", DictVectorizer(sparse=False)),
            (
                "impute",
                SimpleImputer(
                    strategy="median",
                    add_indicator=True,
                    keep_empty_features=True,
                ),
            ),
            ("scale", StandardScaler()),
            ("model", model),
        ]
    )


def _audit_features(row: SurvivalRow) -> dict[str, float | str | None]:
    return dict(row.features)


def _hazard_features(row: SurvivalRow) -> dict[str, float | str | None]:
    result = dict(row.features)
    result["elapsed_log_days"] = math.log1p(row.elapsed_days)
    result["elapsed_month"] = float(row.elapsed_days // 30)
    result["elapsed_month_squared"] = float((row.elapsed_days // 30) ** 2)
    result["hazard_current_phase"] = row.current_phase
    result["hazard_current_trend"] = row.current_trend
    return result


def _weighted_calibration_bins(
    probabilities: Sequence[float], targets: Sequence[int], weights: Sequence[float]
) -> list[dict[str, Any]]:
    result = []
    for lower in (0.0, 0.2, 0.4, 0.6, 0.8):
        upper = lower + 0.2
        indexes = [
            index
            for index, probability in enumerate(probabilities)
            if lower <= probability < upper or (upper == 1.0 and probability == 1.0)
        ]
        bin_weight = sum(weights[index] for index in indexes)
        result.append(
            {
                "lower": lower,
                "upper": upper,
                "count": len(indexes),
                "weight": bin_weight,
                "mean_probability": (
                    sum(weights[index] * probabilities[index] for index in indexes) / bin_weight
                    if bin_weight
                    else None
                ),
                "observed_frequency": (
                    sum(weights[index] * targets[index] for index in indexes) / bin_weight
                    if bin_weight
                    else None
                ),
            }
        )
    return result


def _mapping_episode_weights(rows: Sequence[Mapping[str, Any]]) -> list[float]:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[str(row["episode_id"])] += 1
    return [1.0 / counts[str(row["episode_id"])] for row in rows]


def _rows_by_episode(rows: Iterable[SurvivalRow]) -> dict[str, tuple[SurvivalRow, ...]]:
    result: dict[str, list[SurvivalRow]] = defaultdict(list)
    for row in rows:
        result[row.episode_id].append(row)
    return {key: tuple(values) for key, values in result.items()}


def _known_rows(
    rows_by_episode: Mapping[str, Sequence[SurvivalRow]],
    episode_ids: Iterable[str],
    horizon: int,
) -> tuple[SurvivalRow, ...]:
    return tuple(
        sorted(
            (
                row
                for episode_id in episode_ids
                for row in rows_by_episode.get(episode_id, ())
                if row.targets[horizon] is not None
            ),
            key=_row_key,
        )
    )


def _episode_ids_before(episodes: Sequence[ActualEpisode], cutoff: date) -> tuple[str, ...]:
    return tuple(
        sorted(
            episode.episode_id
            for episode in episodes
            if date.fromisoformat(episode.valid_to) < cutoff
        )
    )


def _episode_ids_within_year(episodes: Sequence[ActualEpisode], year: int) -> tuple[str, ...]:
    start = date(year, 1, 1)
    end = date(year + 1, 1, 1)
    return tuple(
        sorted(
            episode.episode_id
            for episode in episodes
            if start <= date.fromisoformat(episode.valid_from)
            and date.fromisoformat(episode.valid_to) < end
        )
    )


def _targets(rows: Iterable[SurvivalRow], horizon: int) -> list[int]:
    return [int(row.targets[horizon]) for row in rows if row.targets[horizon] is not None]


def _has_both_classes(rows: Sequence[SurvivalRow], horizon: int) -> bool:
    return set(_targets(rows, horizon)) == {0, 1}


def _require_binary(rows: Sequence[SurvivalRow], name: str) -> None:
    if not _has_both_classes(rows, 30):
        raise MlSanityAuditError(f"{name} requires both target classes")


def _row_key(row: SurvivalRow) -> tuple[str, str, str]:
    return row.period_end, row.region_id, row.sample_id


def _quantile(sorted_values: Sequence[float], probability: float) -> float:
    position = (len(sorted_values) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(sorted_values[lower])
    fraction = position - lower
    return float(sorted_values[lower] * (1 - fraction) + sorted_values[upper] * fraction)


def _validate_hashes(values: Mapping[str, str]) -> None:
    if not values or any(
        not str(value).startswith("sha256:") or len(str(value)) != 71 for value in values.values()
    ):
        raise MlSanityAuditError("input hashes must be complete SHA-256 values")


def _bounded(value: float) -> float:
    if not math.isfinite(value):
        raise MlSanityAuditError("non-finite probability")
    return min(1.0, max(0.0, value))


def _clip(value: float) -> float:
    return min(1 - 1e-15, max(1e-15, value))


def _logit(value: float) -> float:
    probability = _clip(_bounded(value))
    return math.log(probability / (1 - probability))


def _hash(value: object) -> str:
    digest = hashlib.sha256(canonical_json(value).encode()).hexdigest()
    return f"sha256:{digest}"


__all__ = [
    "AuditConfig",
    "CANDIDATE_FIELDS",
    "HgbParameters",
    "MlSanityAuditError",
    "audit_config_from_mapping",
    "audit_ml_sanity",
    "audit_probability_metrics",
    "clustered_episode_bootstrap",
    "episode_equal_weights",
    "fit_hazard",
    "fit_hgb",
    "fit_weighted_platt",
    "hgb_grid_from_sequence",
    "hazard_feature_record",
    "mapping_episode_weighted_brier",
    "missing_indicator_count",
    "phase_survival_predictions",
    "predict_continuation",
    "predict_hazard_continuation",
    "select_hazard_c",
    "select_hgb_parameters",
    "skill_verdict",
    "temporal_oof_predictions",
]
