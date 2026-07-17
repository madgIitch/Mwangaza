# Sprint 30 - Exposure Estimation

## Resultado

- Se agrego el contrato `ExposureEstimate` con `payload_type="exposure_estimate"` y metrica publica `potentially_exposed`.
- Se agrego `mwangaza.data.exposure` para validar, redondear y describir estimaciones de exposicion.
- El dashboard renderiza la tarjeta `potentially_exposed` con fuente, ano, resolucion, metodo, calidad y etiqueta demo/sintetica.
- Los datasets invalidos quedan como `No data` sin inventar valores.
- La documentacion durable queda en `docs/exposure-estimation.md` y `docs/dashboard-shell.md`.

## Validaciones

- `uv run python -m unittest tests.contracts.test_contracts`
- `uv run python -m unittest tests.ui.test_dashboard_shell`
- `uv run python -m unittest discover -s tests`
- `node .harness\gates.mjs sprint-30-exposure-estimation`
