# sprint-34-audit-trail · undefined — Tareas

Checklist de implementación. El agente marca [x] al completar; los gates verifican.

- [x] (T1) Los eventos incluyen actor, tipo, entidad, timestamp, run_id y metadata saneada.  ↔ R1
- [x] (T2) Crear, elevar, degradar y resolver una alerta produce eventos separados.  ↔ R2
- [x] (T3) Cambiar configuracion registra version anterior y nueva sin secretos.  ↔ R3
- [x] (T4) No existe metodo publico ni endpoint para borrar eventos de auditoria.  ↔ R4
- [x] (T5) La consulta filtra por region, run y tipo con limite maximo.  ↔ R5
- [x] (T6) Un evento puede enlazarse a snapshot y modelo mediante `snapshot_id` y `model_version`.  ↔ R6
- [x] Tests que cubran los criterios de aceptación
