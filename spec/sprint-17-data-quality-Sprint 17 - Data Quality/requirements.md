# sprint-17-data-quality · undefined — Requisitos

- name: `Sprint 17 - Data Quality` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-15T16:03:27.783Z

## Contexto



## Requisitos funcionales

R1. `evaluate_data_quality(...)` calcula frescura, cobertura espacial, cobertura temporal e historia suficiente desde un snapshot.
R2. El score total queda entre 0 y 100 e incluye desglose de contribuciones por dimension.
R3. Calidad critica produce estado `data_review_required` y `blocks_automatic_alerts=True`.
R4. El reporte conserva datos disponibles y genera warnings sin ocultarlos.
R5. Las reglas son configurables y conservan `rules_version`.
R6. Snapshots completos, degradados y bloqueados quedan cubiertos por tests automatizados.

