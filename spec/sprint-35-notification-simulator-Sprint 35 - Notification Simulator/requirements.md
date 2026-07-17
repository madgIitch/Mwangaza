# sprint-35-notification-simulator · undefined — Requisitos

- name: `Sprint 35 - Notification Simulator` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-17T11:45:32.739Z

## Contexto



## Requisitos funcionales

R1. Por defecto ningun mensaje sale a una red externa ni se invoca adapter real.
R2. Cada envio simulado guarda canal, destinatario enmascarado, contenido, alerta, estado y dedupe key.
R3. Solo severidades configuradas crean notificaciones.
R4. Reprocesar una alerta no duplica mensajes con la misma clave.
R5. La UI muestra una vista previa del mensaje simulado y estado de outbox.
R6. Los adapters reales fallan cerrados sin feature flag explicito y secretos separados.

