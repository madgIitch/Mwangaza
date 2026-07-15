# Land Surface Temperature

Sprint 11 computes recent land surface temperature as an `IndicatorObservation`
through a mockable adapter boundary.

## Contract

Use `mwangaza.data.lst.compute_current_lst(...)` with an adapter that exposes:

```python
query_lst(geometry, period_start, period_end, config) -> LstQueryResult
```

The result has:

- `indicator="lst_c"`
- `unit="celsius"`
- `value` as regional mean Celsius for the requested period
- `metadata.mean_c`
- `metadata.median_c`
- `metadata.valid_pixel_count`
- `metadata.total_pixel_count`
- `metadata.coverage_fraction`
- `metadata.actual_period_start`
- `metadata.actual_period_end`

`summarize_lst_raw_values(...)` isolates product conversion with:

```text
raw * scale + offset - 273.15
```

Pixels failing the quality mask do not participate in the mean, median, or valid
pixel coverage. If no valid pixels remain, the result is `value=None` with
`quality_flag="no_data"`. If the aggregate is outside the configured physical
temperature range, the result is `quality_flag="invalid"` and `value=None`.

## Temperature Anomaly

Sprint 12 computes seasonal LST baselines and current temperature anomalies with
`mwangaza.data.temperature_anomaly`.

Use `compute_lst_climatology(...)` to build a `Baseline` with:

- `indicator="lst_c"`
- `unit="celsius"`
- historical mean, median, and standard deviation
- `metadata.product_variant` as `day` or `night`
- included and excluded historical years

Use `compute_temperature_anomaly(...)` to compare a current LST observation with
that baseline. The result is an `Anomaly` where positive values mean the surface
is hotter than the baseline. `metadata.z_score` is available only when baseline
standard deviation is above the configured epsilon.

Day and night product variants are not mixed by default. The module does not
generate recommendations, actions, alerts, severity, or final drought scores.
