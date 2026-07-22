# sprint-58-alerts-center-completion · Sprint 58 - Alerts Center Completion — Tareas

Checklist de implementación completado; los gates verifican el resultado.

- [x] (T1) `/alerts` presenta una consola table-first con filtros compactos, banda de estado, cola principal e inspector sticky; no conserva mosaicos de tarjetas ni placeholders silenciosos. ↔ R1
- [x] (T2) La API asigna un ID público estable a cada alerta y expone `issued_at`, `updated_at`, estado, evidencia y recomendaciones sin que la UI reconstruya identidad o fechas. ↔ R2
- [x] (T3) `GET /api/v1/alerts` aplica `q`, región, severidad, estado, periodo y paginación en backend, devuelve resumen consistente y mantiene orden determinista. ↔ R3
- [x] (T4) Preventive, active, monitoring, resolved y superseded son estados diferenciados; resolved/recent consume historial real cuando existe y degrada explícitamente cuando no. ↔ R4
- [x] (T5) El detalle `/alerts/<id>` muestra evidencia, indicadores, acción, eventos lifecycle y outbox simulado del mismo ID; un ID ausente produce 404 accesible y saneado. ↔ R5
- [x] (T6) El outbox procede del backend, enmascara destinatarios, declara `is_simulated=true` en cada fila y no puede activar adaptadores reales ni filtrar secretos. ↔ R6
- [x] (T7) Las recomendaciones incluyen actor, prioridad, horizonte, evidencia, región objetivo y versión de catálogo cuando estén disponibles; campos ausentes no se inventan. ↔ R7
- [x] (T8) CSV/JSON y PDF respetan exactamente los filtros activos, llevan nombres/cabeceras seguras y no generan archivos vacíos ante error. ↔ R8
- [x] (T9) Los filtros se reflejan en la URL y los deep-links desde Overview/Region conservan región, periodo y estado; recargar reproduce la misma vista. ↔ R9
- [x] (T10) Selección, filtros y paginación conservan contexto de manera determinista; una búsqueda vacía ofrece limpiar filtros sin perder la ruta. ↔ R10
- [x] (T11) `Alert settings` permanece explícitamente no disponible hasta contar con autenticación/permisos; no se simula persistencia administrativa. ↔ R11
- [x] (T12) Demo funciona offline con IDs y tiempos deterministas; live/cache no mezclan fixtures y ninguna interacción del navegador consulta GEE. ↔ R12
- [x] (T13) Low-bandwidth conserva filtros, resumen, cola, detalle, lifecycle, recomendaciones, outbox simulado y exportaciones en texto/tablas. ↔ R13
- [x] (T14) Tests de contratos, repositorio, API y frontend bloquean regresiones de identidad, estados, filtros, masking, export, rutas y degradación. ↔ R14
- [x] Tests que cubren los criterios de aceptación.
