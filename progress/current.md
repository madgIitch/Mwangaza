# Sesión actual

Feature siguiente: **sprint-64-risk-probability-api-drivers — Sprint 64 - Drought Continuation API and Drivers** — estado: `spec_ready`, pendiente de aprobación.

## Decisión cerrada

- Sprint 63B está `done` en `60a4497`.
- A 30 días se integrarán dos estimaciones simultáneas: `experimental_ml_prediction`
  del hazard congelado y `historical_reference` de `phase_survival`.
- ML conserva `validation_status=inconclusive`, `experimental=true` y
  `operational_use=false`; no se afirma superioridad robusta.
- A 60/90/180 días solo habrá referencia histórica.
- Una indisponibilidad ML no oculta una referencia válida.

## Siguiente acción

- Revisar y aprobar el spec 64.
- Tras aprobación, implementar materialización offline, contrato, servicio y API.
- Sprint 65 ya refleja la comparación dual, pero permanece pendiente.
