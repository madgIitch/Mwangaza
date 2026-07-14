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
