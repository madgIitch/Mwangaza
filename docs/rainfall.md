# Current Rainfall

Sprint 8 computes recent accumulated rainfall as an `IndicatorObservation`
through a mockable adapter boundary.

## Configuration

- `MWANGAZA_RAINFALL_COLLECTION`: Earth Engine rainfall collection ID. Defaults
  to `UCSB-CHG/CHIRPS/DAILY`.

## Contract

Use `mwangaza.data.rainfall.compute_current_rainfall(...)` with an adapter that
exposes:

```python
query_rainfall(geometry, period_start, period_end, config) -> RainfallQueryResult
```

The result is an `IndicatorObservation` with:

- `indicator="rainfall_mm"`
- `unit="mm"`
- `value` as accumulated rainfall for the requested period
- `metadata.expected_days`
- `metadata.available_days`
- `metadata.missing_days`
- `metadata.coverage_fraction`
- `metadata.incomplete_period`
- `metadata.actual_period_start`
- `metadata.actual_period_end`

If no valid days or pixels remain, rainfall is `value=None` with
`quality_flag="no_data"` rather than `0`. If missing days exceed the configured
threshold, the available accumulation is preserved with `quality_flag="degraded"`.

## Rainfall Climatology

Sprint 9 computes historical rainfall baselines for equivalent UTC calendar
windows with `mwangaza.data.rainfall_climatology.compute_rainfall_climatology(...)`.
It reuses the Sprint 8 rainfall adapter per historical year and returns a
`RainfallClimatologyBaseline` with a contractual `Baseline` plus:

- `percentile_20`, `percentile_50`, `percentile_80`
- `included_years`
- `excluded_years` with stable reasons such as `insufficient_coverage` or
  `no_data`
- `baseline_version`

Configuration is explicit through `RainfallClimatologyConfig`:

- `min_years`: minimum included years required for an `ok` baseline.
- `min_coverage_fraction`: minimum effective coverage per historical year.
- `collection_id`: rainfall source identifier, matching Sprint 8 units.

If history is insufficient, statistics are `None` and
`quality_flag="insufficient_history"`; rainfall climatology is never represented
as zero unless the included historical accumulation is actually zero.

## Rainfall Anomaly

Sprint 10 computes rainfall deviation with
`mwangaza.data.rainfall_anomaly.compute_rainfall_anomaly(...)`. It consumes a
current rainfall `IndicatorObservation` and a rainfall climatology baseline, then
returns an `Anomaly` with:

- `value`: absolute anomaly in mm, calculated as current rainfall minus
  baseline mean.
- `metadata.percent_anomaly`: percent deviation when the baseline mean is above
  epsilon.
- `metadata.empirical_percentile`: deterministic percentile over included
  historical values when enough observations exist.
- `metadata.classification`: technical `deficit`, `normal`, `excess`, or
  `not_conclusive`.

The default internal classification thresholds are documented and inclusive:

- `deficit_threshold_percent=-20.0`
- `excess_threshold_percent=20.0`

This module does not create alerts, actions, or final severity. Those decisions
belong to later alert and recommendation sprints.
