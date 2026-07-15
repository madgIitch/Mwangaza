# sprint-18-alert-thresholds · undefined — Tareas

Checklist de implementación. El agente marca [x] al completar; los gates verifican.

- [ ] (T1) Los niveles permitidos son exactamente `green`, `yellow`, `orange`, `red` y `unknown`.  ↔ R1
- [ ] (T2) `validate_preset(...)` exige que los rangos cubran el dominio configurado sin solapes ni huecos.  ↔ R2
- [ ] (T3) Calidad bloqueada o valor ausente fuerza `unknown` independientemente del valor numerico.  ↔ R3
- [ ] (T4) Cada clasificacion conserva `threshold_version`.  ↔ R4
- [ ] (T5) Cambiar umbrales produce una version distinta y no muta clasificaciones previas.  ↔ R5
- [ ] (T6) El preset por defecto se marca como configuracion de prototipo, no estandar oficial IGAD.  ↔ R6
- [ ] Tests que cubran los criterios de aceptación
