# sprint-18-alert-thresholds · undefined — Tareas

Checklist de implementación. El agente marca [x] al completar; los gates verifican.

- [x] (T1) Los niveles permitidos son exactamente `green`, `yellow`, `orange`, `red` y `unknown`.  ↔ R1
- [x] (T2) `validate_preset(...)` exige que los rangos cubran el dominio configurado sin solapes ni huecos.  ↔ R2
- [x] (T3) Calidad bloqueada o valor ausente fuerza `unknown` independientemente del valor numerico.  ↔ R3
- [x] (T4) Cada clasificacion conserva `threshold_version`.  ↔ R4
- [x] (T5) Cambiar umbrales produce una version distinta y no muta clasificaciones previas.  ↔ R5
- [x] (T6) El preset por defecto se marca como configuracion de prototipo, no estandar oficial IGAD.  ↔ R6
- [x] Tests que cubran los criterios de aceptación
