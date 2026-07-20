# sprint-42-observability · undefined — Requisitos

- name: `Sprint 42 - Observability` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-18T11:51:10.298Z

## Contexto



## Requisitos funcionales

R1. AC1: Cada evento JSON contiene timestamp UTC, level, component, event y run_id; las respuestas API incluyen el mismo `X-Run-ID` usado en sus logs.
R2. AC2: La redacción recursiva elimina credenciales, tokens, secretos, rutas locales y payloads sensibles de logs, errores, métricas y checks.
R3. AC3: `/health` conserva liveness; `/ready` devuelve 503 y checks saneados si la base o cache obligatoria no están disponibles.
R4. AC4: `/api/v1/observability` expone duración, cache hit, regiones procesadas, errores y alertas activas como agregados sin datos sensibles.
R5. AC5: `/technical` muestra estado operativo, readiness y métricas separado de Overview, con estados loading/error y low-bandwidth.
R6. AC6: Un error de Earth Engine puede localizarse por run_id compartido entre evento, respuesta y diagnóstico, sin revelar detalles sensibles.

