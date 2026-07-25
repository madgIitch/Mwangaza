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

Selection uses out-of-sample Brier score. An ML model is selected only when it improves persistence, seasonal climatology and historical frequency; otherwise the horizon is retained as `rejected_insufficient_skill`. Runs record dataset and feature hashes, threshold versions, seed, scikit-learn version, folds, parameters, OOF probabilities and a canonical run hash. This sprint does not publish probabilities.

## Real historical backfill

`scripts/backfill_probabilistic_history.py` materializes regional aggregates from Google Earth Engine without downloading source rasters. The default pilot covers Kenya from `2024-01-01` through the last complete dekad. `--dry-run` is offline; a real extraction requires `--confirm-remote`. Local outputs under `data/historical/` are ignored by Git.

CHIRPS Daily is accumulated inside exact calendar dekads. MODIS MOD13Q1 NDVI and MOD11A2 LST use the latest composite whose source timestamp is not later than the dekad `as_of`; output rows preserve `observed_at` and `age_days`. Missing upstream signals remain null with structured reasons. JSONL writes are atomic and each completed chunk acts as a resumable checkpoint. The canonical manifest records collections, coverage, counts and the SHA-256 of the local data file.

The validated Kenya run on 2026-07-24 produced 92 rows through `2026-07-20`. The two July 2026 CHIRPS periods were not yet present upstream and remain explicit `rainfall_no_data`; no zero was invented. This raw signal history is not yet an independent drought-event label catalog.

The subsequent full IGAD run produced 736 valid JSONL rows, 92 for each of the eight countries. There are 720 complete rows and 16 explicit CHIRPS absences corresponding to the two latest dekads in every country. Raw observations must not be passed directly to the classifier: dekadal seasonal climatologies, anomaly transformations and versioned risk labels are required first. In particular, the live composite scorer is not a substitute for this step because its generic raw-value path does not define a historical anomaly label.

### Reproducible treatment and training commands

All long-running scripts print completed/total units, percentage and ETA. Download the independent `2003-2023` seasonal reference first:

```powershell
uv run python scripts/backfill_probabilistic_history.py --scope igad --start 2003-01-01 --end 2023-12-31 --output data/historical/gee-baseline-2003-2023 --chunk-size 24 --confirm-remote
```

Then derive 36 dekadal climatologies per region, orient anomalies so rainfall/NDVI deficits and LST excess increase risk, create versioned `green/yellow/orange/red` labels, and build the three-horizon dataset:

```powershell
uv run python scripts/prepare_probabilistic_dataset.py
```

Inspect the printed target counts before training. If every horizon lacks both classes, the run must stop rather than weakening thresholds silently. Train candidates and persist the reproducible evaluation:

```powershell
uv run python scripts/train_probabilistic_model.py
```

The prepared dataset is written to `data/historical/probabilistic-training.json`; the training run goes to `data/models/probabilistic-training-run.json`. Both are local ignored artifacts. Treatment version `igad-dekadal-2003-2017-v2`, score version `probabilistic-composite-v1`, and threshold version `probabilistic-risk-thresholds-v3-2003-2017-quantiles` are preserved in lineage.

Threshold v2 uses country-level P75/P90/P97.5 of valid `2003-2023` baseline scores for yellow/orange/red. Exact values are frozen before labeling 2024 onward, so current observations cannot tune their own target.

The first v2 run produced three severe observations: Eritrea 2025-06-30, Kenya 2025-12-10 and Sudan 2025-06-10. ML did not beat historical frequency in any horizon, so all horizons remain `rejected_insufficient_skill`. Sparse positives and very small Brier differences prohibit publishing a model from this run.

Threshold v3 freezes climatology and cuts on `2003-2017`, then labels the disjoint `2018-2026` period. It produces 2,464 labeled observations, 7,392 horizon rows and 86 severe targets per horizon. Despite the larger positive class, ML still does not beat historical frequency: the final status remains `rejected_insufficient_skill` for 10, 20 and 30 days. Training progress is reported by walk-forward fold so long runs expose a meaningful ETA.

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
