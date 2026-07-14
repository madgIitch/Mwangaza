# NDVI Climatology

Sprint 6 computes historical NDVI baselines as `Baseline` contract payloads.

## Configuration

- `MWANGAZA_CLIMATOLOGY_START_YEAR`
- `MWANGAZA_CLIMATOLOGY_END_YEAR`
- `MWANGAZA_CLIMATOLOGY_MIN_YEARS`
- `MWANGAZA_NDVI_COLLECTION`

The historical window is inclusive. The current observation year is always
excluded from the baseline and recorded in `metadata.excluded_years`.

## Contract

Use `mwangaza.data.climatology.compute_ndvi_climatology(...)` with an adapter
that exposes:

```python
query_ndvi_year(geometry, year, season_start, season_end, config)
```

The result includes `metadata.effective_years`, `metadata.excluded_years`,
`metadata.baseline_version`, `metadata.season_start`, `metadata.season_end`,
and `metadata.collection_id`.
