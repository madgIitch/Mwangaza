# sprint-32-data-export · undefined — Tareas

Checklist de implementación. El agente marca [x] al completar; los gates verifican.

- [x] (T1) CSV y JSON contienen los mismos valores, unidades y calidades visibles para el snapshot exportado.  ↔ R1
- [x] (T2) El JSON incluye `schema_version` y metadata de fuente no sensible.  ↔ R2
- [x] (T3) No se exportan secretos, rutas internas, credenciales ni errores crudos.  ↔ R3
- [x] (T4) Las geometrías se omiten por defecto y solo aparecen simplificadas con opcion explicita.  ↔ R4
- [x] (T5) La exportacion limita volumen y periodo mediante `max_rows` y snapshot seleccionado.  ↔ R5
- [x] (T6) Valores `None` se conservan como `null` en JSON y campo vacio en CSV, nunca como cero.  ↔ R6
- [x] Tests que cubran los criterios de aceptación
