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
