# Data provenance and methodology

The canonical metadata catalog is `docs/data-sources/catalog.json` (`mwangaza.provenance.v1`). It covers MODIS NDVI, CHIRPS rainfall, MODIS land-surface temperature, SPEIbase, FLDAS, ECMWF IFS, administrative boundaries and potential exposure. `Pending verification` means terms are not yet confirmed and the source must not be presented as operationally approved.

The ADM1 antecedent artifact pins 121 geoBoundaries gbOpen units from `wmgeolab/geoBoundaries@9469f09`. Its manifest keeps each complete geometry once; dekadal rows join by stable boundary identity. This avoids repeating large polygons in every row while preserving an auditable spatial snapshot.

The access, license and semantic audit for future independent labels is
`docs/data-sources/independent-label-source-audit.md`. In particular, food
security impact labels and drought-hazard event labels remain separate.

The Sprint 62D local catalog uses schema `mwangaza.independent-label.v1` and
mapping rule `adm1-geometry-overlap-v1`. It retains original source identity,
taxonomy, publication and validity times, license policy, artifact hash and
explicit coverage/exclusion status. FEWS NET uses assessed `scenario=CS`;
IPC uses assessed `period=C` only when an API key is supplied. Official and
EM-DAT evidence enters through reviewed local files. Source absence, disabled
adapters and unmatched geometry remain unknown rather than negative.

Monthly SPEIbase and FLDAS values retain their source timestamp and are only attached after a complete source month. CHIRPS empirical SPI is fitted from complete monthly accumulations ending on or before the configured reference cutoff. The provider SPEI value and Mwangaza SPI are separate features and must not be conflated.

ECMWF IFS precipitation is stored only when `creation_time <= as_of`; `forecast_hours` is preserved and `observed_at` remains null. Dates before 2024-11-12 use `not_available_for_date`. A forecast is never substituted for a missing observation.

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
