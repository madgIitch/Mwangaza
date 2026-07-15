# sprint-21-alert-persistence · undefined — Requisitos

- name: `Sprint 21 - Alert Persistence` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-15T16:15:28.906Z

## Contexto



## Requisitos funcionales

R1. Una alerta se identifica por region, tipo, periodo y version de modelo.
R2. Reprocesar el mismo snapshot no crea duplicados.
R3. Un cambio de severidad genera un evento de transicion.
R4. Una alerta resuelta conserva su historia.
R5. El registro guarda score, nivel, calidad, evidencias y recomendaciones.
R6. Las migraciones son idempotentes y testeadas.

