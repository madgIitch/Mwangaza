# Forecast Model

Sprint 36 adds an experimental deterministic seasonal baseline forecast.

The default model averages the last four valid values and repeats that value for
up to three forecast steps. It is reproducible, does not require GPU, and does
not use network access.

Forecasts include region, indicator, training timestamp, horizon, model version
and an explicit `experimental=true` marker. They also set
`replaces_observation=false`; forecasts never replace current observations.

Backtesting reports MAE and a safe relative error that is omitted when all
actual values are zero.

## Post-1.0 roadmap

Sprints 61-65 add a separate probabilistic risk engine without changing this deterministic contract. The new target predicts whether the versioned Mwangaza risk indicator reaches orange or red; it does not claim a probability of official drought or humanitarian impact. See `docs/probabilistic-risk.md`.
