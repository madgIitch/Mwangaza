# Data provenance and methodology

The canonical metadata catalog is `docs/data-sources/catalog.json` (`mwangaza.provenance.v1`). It covers MODIS NDVI, CHIRPS rainfall, MODIS land-surface temperature, administrative boundaries and potential exposure. `Pending verification` means terms are not yet confirmed and the source must not be presented as operationally approved.

## Product concepts

- **Observation:** a quality-controlled measurement or estimate for a region and period.
- **Anomaly:** an observation compared with a seasonally comparable historical baseline.
- **Score:** a configurable composite of normalized anomalies; prototype thresholds are configurable and not official IGAD warnings.
- **Forecast:** a model-derived future estimate, distinct from a current observation.
- **Exposure:** population potentially exposed to the assessed condition, never confirmed affected population.

## Modes and limitations

`live` reads approved sources, `cache` preserves their original provenance and adds age, and `demo` uses versioned fixtures labelled `is_demo=true`. Simulated alerts or notifications additionally use `is_simulated=true`. Cloud and QA masking affect coverage; product publication affects latency; spatial aggregation can hide local variation. Missing values remain missing and are never interpolated silently.

## Lineage

```text
source → transformation/QA → versioned cache → public API → accessible UI → report/export
```

Each step retains source identifier, period, unit, quality and mode. Reports must link back to the snapshot used.
