# Sprint 31 - Executive PDF Report

## Resultado

- Se agrego `mwangaza.reports` con contexto ejecutivo, HTML, bytes PDF y nombre de archivo seguro.
- El reporte usa el snapshot ya cargado del dashboard y no consulta Earth Engine.
- El panel Reports del dashboard muestra filename determinista y QR solo si `MWANGAZA_DASHBOARD_URL` esta configurada.
- Se documento el contrato en `docs/executive-report.md`.

## Validaciones

- `uv run python -m unittest tests.reports.test_executive_report`
- `uv run python -m unittest tests.ui.test_dashboard_shell`
- `uv run python -m unittest discover -s tests`
- `node .harness\gates.mjs sprint-31-executive-pdf-report`
