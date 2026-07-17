# sprint-32-data-export · undefined — Requisitos

- name: `Sprint 32 - Data Export` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-17T11:36:24.641Z

## Contexto



## Requisitos funcionales

R1. CSV y JSON contienen los mismos valores, unidades y calidades visibles para el snapshot exportado.
R2. El JSON incluye `schema_version` y metadata de fuente no sensible.
R3. No se exportan secretos, rutas internas, credenciales ni errores crudos.
R4. Las geometrías se omiten por defecto y solo aparecen simplificadas con opcion explicita.
R5. La exportacion limita volumen y periodo mediante `max_rows` y snapshot seleccionado.
R6. Valores `None` se conservan como `null` en JSON y campo vacio en CSV, nunca como cero.

