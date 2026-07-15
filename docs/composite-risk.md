# Composite Drought Score

Sprint 19 combines snapshot signals into a deterministic `RiskSnapshot`.

The prototype model uses configurable weights for NDVI, rainfall and LST. Missing
optional signals are renormalized and recorded in metadata. Missing required
signals or blocked data quality produce a non-conclusive result with
`composite_score=None` and metadata `risk_level_override="unknown"`.

Each result includes per-indicator contribution metadata: weight, score, source
and quality flag.
