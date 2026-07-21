# sprint-57-overview-completion · Sprint 57 - Overview Completion — Tareas

Checklist de implementación. El agente marca [x] al completar; los gates verifican.

- [x] (T1) `/overview` y `/` renderizan el mismo cockpit independiente, sin hashes ni autoscroll, y conservan navegación por rutas de página. ↔ R1
- [x] (T2) El mapa usa exclusivamente `ui_geometry` procesada; regiones `no_data`, inválidas o ausentes permanecen grises y sin geometría aparece un fallback tabular explícito. ↔ R2
- [x] (T3) Home restaura el encuadre IGAD, zoom opera entre 1× y 4× y el selector alterna `Risk` y `Data quality` sobre datos ya cargados, sin consultas GEE. ↔ R3
- [x] (T4) Cada región evaluada ofrece tooltip y foco accesibles con nombre, score, nivel, indicadores disponibles, calidad, fuente y periodo; seleccionar mapa o selector actualiza el mismo contexto regional. ↔ R4
- [x] (T5) Las alertas exponen identificador estable; `View details` abre `/alerts/<alert_id>` y el listado global conserva `region`, `period` y `status=active` en la query. ↔ R5
- [x] (T6) Una alerta existente muestra detalle, evidencia, calidad, periodo y acción; una inexistente produce un estado 404 accesible y saneado. ↔ R6
- [x] (T7) El PDF ejecutivo se descarga desde un endpoint real usando sólo el snapshot procesado de región/periodo, con MIME, `Content-Disposition` y nombre determinista; un fallo no descarga un archivo vacío. ↔ R7
- [x] (T8) CSV y JSON se descargan desde un endpoint real para la región/periodo visibles, conservan nulls, omiten geometría por defecto, aplican límite y usan nombres/cabeceras seguras. ↔ R8
- [x] (T9) Las tarjetas sólo muestran delta cuando existe comparación estacional válida; sin ella muestran `No comparison yet` y nunca comparan ventanas incompatibles. ↔ R9
- [x] (T10) Las tendencias de cualquier región IGAD seleccionada muestran 12–24 puntos disponibles contra baseline; si el lote GEE falla, se reintenta país por país sin reducir la cobertura a Somalia. ↔ R10
- [x] (T11) El locale Somali (`so`) cubre todo texto visible de Overview y navegación; EN/SW/SO se presentan como selector segmentado y ES permanece disponible por compatibilidad sin traducir valores técnicos ni fuentes. ↔ R11
- [x] (T12) Cuenta y notificaciones permanecen etiquetadas como no disponibles y no son interactivas hasta contar con contrato aprobado. ↔ R12
- [x] (T13) Demo funciona sin red/GEE y conserva `is_demo`, `reference_date` y `snapshot_id`; live/cache no mezclan fixtures y mantienen fuente/frescura visibles. ↔ R13
- [x] (T14) Low-bandwidth conserva región, riesgos, alertas, métricas, deltas, tendencias, recomendaciones y acciones de descarga en texto/tablas sin SVG ni animaciones. ↔ R14
- [x] (T15) Tests API/frontend verifican controles, rutas, descargas, idiomas y degradación; ninguna interacción de Overview inicia Earth Engine desde el navegador. ↔ R15
- [x] Tests que cubren los criterios de aceptación.
