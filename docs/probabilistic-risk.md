# Probabilistic Risk Engine Roadmap

Mwangaza will evolve the existing experimental deterministic forecast through Sprints 61-65. This is an additive post-1.0 capability; Sprints 36 and 37 remain unchanged.

## Scientific claim

The primary target is:

`P(Mwangaza risk level is orange or red at horizon h | information available at as_of)`

It is not the probability of an officially declared drought, humanitarian crisis, agricultural loss or affected population. Historical labels are derived from versioned Mwangaza risk levels, not an independent ground-truth event catalog.

## Minimum product

- One binary target: `risk_level_at_or_above_orange`.
- Primary cadence: dekadal (10-day periods).
- Three validated horizons: 10, 20 and 30 days.
- Two ML candidates: logistic regression and histogram gradient boosting.
- Baselines: persistence, seasonal climatology and historical frequency.
- Walk-forward validation using global date cuts and a horizon gap.
- Sigmoid calibration using out-of-sample predictions.
- Core metrics: Brier score, Brier Skill Score, log loss, recall and precision.
- One read-only endpoint, one compact Region module and report integration.
- Up to three non-causal drivers.
- Strict abstention whenever validated skill or data quality is insufficient.

## Delivery sequence

1. Sprint 61 materializes a leakage-safe, versioned training dataset.
2. Sprint 62 trains candidates and compares them with approved baselines.
3. Sprint 63 calibrates probabilities and makes eligibility decisions.
4. Sprint 64 materializes predictions, drivers and the public API.
5. Sprint 65 integrates eligible results and abstentions into Region and Reports.

Each sprint depends on the previous one. Sprint 61 is implemented and awaiting review; Sprints 62-65 remain `pending` and `spec_approved: false` until their SDD interview resolves the open design decisions.

## Sprint 61 implementation

`mwangaza.probabilistic.dataset` builds an immutable, deterministic training dataset from already materialized historical periods. It supports monthly and dekadal frequencies, exact contiguous lags, three future horizons, temporal features, lineage, structured null reasons and atomic canonical JSON output with SHA-256.

Future observations may determine a target but cannot enter the feature vector for an earlier `as_of`. Gaps remain gaps; unknown or quality-blocked future levels remain null labels and are never coerced to the negative class.

Dekadal is the primary training cadence. Daily CHIRPS observations are aggregated into rainfall features inside each 10-day period; they do not create duplicate daily training rows. MODIS NDVI and LST retain their actual `observed_at`, and the dataset exposes `*_age_days` so an older composite is never presented as a new observation. Monthly remains a secondary reporting-compatible frequency.

## Sprint 62 implementation

`mwangaza.probabilistic.training` evaluates persistence, seasonal climatology, historical frequency, logistic regression and histogram gradient boosting independently for horizons of 10, 20 and 30 days.

Walk-forward folds use globally shared dekadal dates. Every fold leaves a gap equal to its forecast horizon; preprocessing, median imputation, scaling and region encoding are learned only from the training side. New regions are treated as unknown categories rather than causing failure or borrowing another region's identity.

Selection uses out-of-sample Brier score. An ML model is selected only when it improves both persistence and seasonal climatology; otherwise the horizon is retained as `rejected_insufficient_skill`. Runs record dataset and feature hashes, threshold versions, seed, scikit-learn version, folds, parameters, OOF probabilities and a canonical run hash. This sprint does not publish probabilities.

## Non-negotiable gates

No percentage is published when any approved gate fails, including insufficient history or positive cases, blocked current quality, non-positive skill against climatology, unacceptable calibration, material drift, unsupported horizon, regional under-representation, corrupt artifacts or version/hash mismatch.

The public unavailable state is:

`Probability unavailable - insufficient validated skill for this region and horizon.`

Unavailable never means zero probability.

## Deferred decisions for SDD interviews

- Exact period frequency and minimum history/event counts.
- Skill improvement margin and calibration-quality thresholds.
- Drift metric, reference distribution and threshold.
- Encoding and minimum representation for regions.
- Artifact serialization and signing/verification strategy.
- Explanation method for histogram gradient boosting.
- Probability bands and user-facing confidence mapping.
- Whether an independently validated drought-event catalog becomes available later.
- Multiclass probabilities and isotonic calibration; neither belongs to Sprints 61-65 without a new approved contract.
