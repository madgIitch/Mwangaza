# Current NDVI

Sprint 5 computes a current NDVI `IndicatorObservation` through a mockable
adapter boundary.

## Configuration

- `MWANGAZA_NDVI_COLLECTION`: Earth Engine image collection ID. Defaults to
  `MODIS/061/MOD13Q1`.

## Contract

Use `mwangaza.data.ndvi.compute_current_ndvi(...)` with an adapter that exposes:

```python
query_ndvi(geometry, period_start, period_end, config) -> NdviQueryResult
```

The result is an `IndicatorObservation` with:

- `indicator="ndvi"`
- `unit="index"`
- `source` set to the configured collection
- `metadata.valid_pixel_fraction`
- `metadata.valid_pixel_count`
- `metadata.total_pixel_count`
- `metadata.actual_period_start`
- `metadata.actual_period_end`

If no valid pixels remain after QA filtering, NDVI is `value=None` with
`quality_flag="no_data"` rather than `0`.

## NDVI Anomaly

Sprint 7 computes NDVI anomaly from an existing current `IndicatorObservation`
and historical `Baseline`:

- absolute anomaly: `current.value - baseline.mean`
- percent anomaly: `(current.value - baseline.mean) / baseline.mean * 100`
  only when `abs(baseline.mean)` is greater than the configured epsilon
- z-score only when `baseline.stddev` exists and is greater than the configured
  epsilon

Use `mwangaza.data.anomaly.compute_ndvi_anomaly(...)`. The function is pure,
does not call Earth Engine, preserves `current_id` and `baseline_id` in
metadata, and does not encode alert thresholds or action recommendations.
