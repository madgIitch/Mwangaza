# Low-Bandwidth Mode

Sprint 39 adds a low-bandwidth HTML mode enabled with
`MWANGAZA_LOW_BANDWIDTH=1`.

Lite mode does not render the regional SVG map or detailed geometry. It shows
essential indicators, active alerts, recommended actions, report filename,
export filename and API path as text/tables.

The full dashboard remains the default. Lite HTML includes a session preference
control and uses accessible table markup instead of color-only map semantics.
