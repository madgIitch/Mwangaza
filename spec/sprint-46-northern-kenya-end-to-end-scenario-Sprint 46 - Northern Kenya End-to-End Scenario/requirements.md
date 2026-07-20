# sprint-46-northern-kenya-end-to-end-scenario · undefined — Requisitos

- name: `Sprint 46 - Northern Kenya End-to-End Scenario` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-20T15:22:27.537Z

## Contexto



## Requisitos funcionales

R1. AC1: Existe un escenario demo versionado de Northern Kenya con al menos 3 unidades subnacionales identificadas de forma estable; el fixture y el resumen del escenario enumeran exactamente esas unidades y su `snapshot_id` común o relación explícita.
R2. AC2: Una única unidad queda destacada como mayor severidad en el escenario, y su detalle muestra al menos severidad, score compuesto y los indicadores usados para justificarla; si hay empate potencial, la regla de desempate queda definida y testeada.
R3. AC3: Desde la vista `/region` o su equivalente PWA, seleccionar una unidad en el mapa o tabla accesible actualiza el panel de detalle sin consultas remotas y deja visible el identificador/nombre de la unidad activa.
R4. AC4: El reporte mostrado o referenciado tras la selección corresponde inequívocamente a la unidad activa mediante `unit_id` o nombre estable y no a otra unidad del escenario.
R5. AC5: La notificación simulada generada para la unidad activa usa el idioma seleccionado cuando existe plantilla para `en`, `sw` o `so`; si la plantilla no existe, el comportamiento de fallback queda explícito y se refleja en el resultado verificable.
R6. AC6: Ejecutar el recorrido completo con datos demo no realiza red ni inicializa servicios remotos; corre sin credenciales externas, produce artefactos marcados `demo` o `simulated` y es idempotente respecto a alerta y notificación simulada.

## Restricciones

- **error_states:** Si falta un fixture, está corrupto o falta un detalle/reporte obligatorio, el recorrido termina con código distinto de cero, mensaje accionable y sin publicar un estado completo. Si una unidad no tiene geometría, sigue siendo seleccionable mediante tabla accesible y la UI muestra un placeholder de mapa. Si falta la plantilla del idioma solicitado, se aplica fallback a inglés y se emite un warning estructurado con idioma solicitado y efectivo.
- **auth_secrets:** El flujo sigue siendo completamente offline/demo: no realiza red, no inicializa GEE ni requiere credenciales externas. Los artefactos derivados deben quedar marcados como `demo` o `simulated`.
- **rollback_compat:** Sprint 46 es estrictamente aditivo. Debe preservar el escenario Somalia y los contratos actuales de `/region`, `/reports` y notificaciones simuladas. Los campos específicos de Kenya solo pueden añadirse como opcionales o encapsulados en fixture/estado demo, sin convertirlos en requisitos obligatorios de contratos existentes.

