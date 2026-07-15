# sprint-18-alert-thresholds · undefined — Requisitos

- name: `Sprint 18 - Alert Thresholds` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-15T16:06:30.491Z

## Contexto



## Requisitos funcionales

R1. Los niveles permitidos son exactamente `green`, `yellow`, `orange`, `red` y `unknown`.
R2. `validate_preset(...)` exige que los rangos cubran el dominio configurado sin solapes ni huecos.
R3. Calidad bloqueada o valor ausente fuerza `unknown` independientemente del valor numerico.
R4. Cada clasificacion conserva `threshold_version`.
R5. Cambiar umbrales produce una version distinta y no muta clasificaciones previas.
R6. El preset por defecto se marca como configuracion de prototipo, no estandar oficial IGAD.

