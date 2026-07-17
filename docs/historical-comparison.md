# Historical Comparison

Sprint 29 adds same-window historical comparison to the dashboard.

The comparison uses only indicator payloads already loaded by the dashboard from
live GEE, materialized cache or demo fixtures. A period is comparable only when
its `period_start` and `period_end` match the current period by month and day.

Rules:

- `no_data`, `insufficient_history` and non-numeric values are excluded.
- The user can select up to three historical periods client-side.
- Data versions shown in the UI come from source and non-sensitive metadata such
  as `baseline_version`, `model_version` or collection identifiers.
- The dryness ranking uses comparable rainfall values, sorted from lower to
  higher rainfall.
- Narrative text describes observed indicator differences only; it does not
  infer causes, impacts or affected population.
