# sprint-45-somalia-end-to-end-scenario · undefined — Requisitos

- name: `Sprint 45 - Somalia End-to-End Scenario` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-20T14:36:04.774Z

## Contexto



## Requisitos funcionales

R1. AC1: El comando `python scripts/demo_somalia.py` completa sin red un recorrido desde un `snapshot_id` estable hasta una alerta persistida y devuelve código cero.
R2. AC2: El resultado verificable incluye mapa o degradación accesible, tendencia, score, calidad, acción recomendada y reporte, todos vinculados al snapshot de origen.
R3. AC3: Cada cifra o artefacto procedente de fixtures se etiqueta de forma visible como `demo` o `simulated`, sin aparentar datos operativos en vivo.
R4. AC4: Ejecutar dos veces el mismo snapshot produce el mismo resultado lógico y no duplica alertas ni notificaciones simuladas.
R5. AC5: Fixtures ausentes o inválidas y etapas incompletas terminan con código distinto de cero, mensaje accionable y sin presentar el escenario como completado.
R6. AC6: Un test E2E automatizado ejecuta el flujo con fixtures locales, sin Earth Engine, red, credenciales ni destinatarios reales.

