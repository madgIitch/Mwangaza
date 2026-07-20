# sprint-46-northern-kenya-end-to-end-scenario · undefined — Tareas

Checklist de implementación. El agente marca [x] al completar; los gates verifican.

- [x] (T1) AC1: Existe un escenario demo versionado de Northern Kenya con al menos 3 unidades subnacionales identificadas de forma estable; el fixture y el resumen del escenario enumeran exactamente esas unidades y su `snapshot_id` común o relación explícita.  ↔ R1
- [x] (T2) AC2: Una única unidad queda destacada como mayor severidad en el escenario, y su detalle muestra al menos severidad, score compuesto y los indicadores usados para justificarla; si hay empate potencial, la regla de desempate queda definida y testeada.  ↔ R2
- [x] (T3) AC3: Desde la vista `/region` o su equivalente PWA, seleccionar una unidad en el mapa o tabla accesible actualiza el panel de detalle sin consultas remotas y deja visible el identificador/nombre de la unidad activa.  ↔ R3
- [x] (T4) AC4: El reporte mostrado o referenciado tras la selección corresponde inequívocamente a la unidad activa mediante `unit_id` o nombre estable y no a otra unidad del escenario.  ↔ R4
- [x] (T5) AC5: La notificación simulada generada para la unidad activa usa el idioma seleccionado cuando existe plantilla para `en`, `sw` o `so`; si la plantilla no existe, el comportamiento de fallback queda explícito y se refleja en el resultado verificable.  ↔ R5
- [x] (T6) AC6: Ejecutar el recorrido completo con datos demo no realiza red ni inicializa servicios remotos; corre sin credenciales externas, produce artefactos marcados `demo` o `simulated` y es idempotente respecto a alerta y notificación simulada.  ↔ R6
- [x] Tests que cubran los criterios de aceptación
