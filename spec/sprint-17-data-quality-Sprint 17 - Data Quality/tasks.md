# sprint-17-data-quality · undefined — Tareas

Checklist de implementación. El agente marca [x] al completar; los gates verifican.

- [ ] (T1) `evaluate_data_quality(...)` calcula frescura, cobertura espacial, cobertura temporal e historia suficiente desde un snapshot.  ↔ R1
- [ ] (T2) El score total queda entre 0 y 100 e incluye desglose de contribuciones por dimension.  ↔ R2
- [ ] (T3) Calidad critica produce estado `data_review_required` y `blocks_automatic_alerts=True`.  ↔ R3
- [ ] (T4) El reporte conserva datos disponibles y genera warnings sin ocultarlos.  ↔ R4
- [ ] (T5) Las reglas son configurables y conservan `rules_version`.  ↔ R5
- [ ] (T6) Snapshots completos, degradados y bloqueados quedan cubiertos por tests automatizados.  ↔ R6
- [ ] Tests que cubran los criterios de aceptación
