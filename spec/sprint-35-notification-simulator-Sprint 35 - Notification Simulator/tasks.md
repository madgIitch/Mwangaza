# sprint-35-notification-simulator · undefined — Tareas

Checklist de implementación. El agente marca [x] al completar; los gates verifican.

- [x] (T1) Por defecto ningun mensaje sale a una red externa ni se invoca adapter real.  ↔ R1
- [x] (T2) Cada envio simulado guarda canal, destinatario enmascarado, contenido, alerta, estado y dedupe key.  ↔ R2
- [x] (T3) Solo severidades configuradas crean notificaciones.  ↔ R3
- [x] (T4) Reprocesar una alerta no duplica mensajes con la misma clave.  ↔ R4
- [x] (T5) La UI muestra una vista previa del mensaje simulado y estado de outbox.  ↔ R5
- [x] (T6) Los adapters reales fallan cerrados sin feature flag explicito y secretos separados.  ↔ R6
- [x] Tests que cubran los criterios de aceptación
