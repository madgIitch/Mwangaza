# Spatial Aggregation

Sprint 13 aggregates existing indicator rasters or adapter outputs by region.

Use `mwangaza.data.spatial_aggregation.aggregate_regions(...)` with an adapter
that exposes:

```python
aggregate_region(geometry, region_id, indicator, period_start, period_end, config)
```

The adapter receives the analytical catalog geometry (`geometry`), not the
simplified `ui_geometry`. Results are sorted by `region_id` for stable caches and
tests.

Each aggregate includes:

- `region_id`, `indicator`, `unit`, period and source
- `mean`, `median` and configured percentiles
- `valid_area`, `total_area` and `coverage_fraction` when available
- `quality_flag` and traceability metadata

Low coverage is marked `degraded` while preserving the observed values and
coverage. Missing values are `no_data`; absence is never represented as zero.
Configuration enforces maximum region count, scale and remote pixel limits before
the adapter is called.
