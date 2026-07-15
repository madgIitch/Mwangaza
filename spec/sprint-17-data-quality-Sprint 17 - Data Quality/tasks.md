# sprint-17-data-quality · undefined — Tareas

Checklist de implementación. El agente marca [x] al completar; los gates verifican.

- [x] (T1) `evaluate_data_quality(...)` calcula frescura, cobertura espacial, cobertura temporal e historia suficiente desde un snapshot.  ↔ R1
- [x] (T2) El score total queda entre 0 y 100 e incluye desglose de contribuciones por dimension.  ↔ R2
- [x] (T3) Calidad critica produce estado `data_review_required` y `blocks_automatic_alerts=True`.  ↔ R3
- [x] (T4) El reporte conserva datos disponibles y genera warnings sin ocultarlos.  ↔ R4
- [x] (T5) Las reglas son configurables y conservan `rules_version`.  ↔ R5
- [x] (T6) Snapshots completos, degradados y bloqueados quedan cubiertos por tests automatizados.  ↔ R6
- [x] Tests que cubran los criterios de aceptación
