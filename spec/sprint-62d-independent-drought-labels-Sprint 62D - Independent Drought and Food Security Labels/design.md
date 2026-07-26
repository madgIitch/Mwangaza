# sprint-62d-independent-drought-labels · undefined — Diseño

## Scope (archivos que puede tocar)

- `src/mwangaza/probabilistic/**`
- `scripts/import_independent_labels.py`
- `tests/probabilistic/**`
- `tests/fixtures/probabilistic/**`
- `data/historical/.gitkeep`
- `.gitignore`
- `docs/data-sources/**`
- `docs/probabilistic-risk.md`
- `docs/data-provenance.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS.md`
- `spec/sprint-62d-independent-drought-labels-*/**`
- `progress/**`

## Decisiones de la entrevista

- **data_model:** El catálogo conserva observaciones fuente independientes y no fuerza un único target. Cada fila declara `label_semantics` (`drought_hazard_event` o `acute_food_insecurity_impact`), fuente e identidad original, taxonomía/valor original y normalizado, estado de evaluación, fechas de emisión y validez, geometría/identificadores fuente, cruce ADM1, licencia, hash, calidad, revisión y exclusión. FEWS NET e IPC permanecen como observaciones separadas incluso si coinciden espacial y temporalmente.
- **error_states:** Ausencia de fila, país sin cobertura, fuente inaccesible, secreto ausente, geometría inexistente o ambigua, valor 66/88/99, proyección, licencia incompatible y documento no revisado tienen códigos separados. Todos producen `unknown` o exclusión explícita; nunca una etiqueta negativa ni fase 1 implícita.
- **edge_cases:** Solo FEWS NET `scenario=CS` e IPC `period=C` pueden ser assessed por defecto. Variantes con/sin asistencia no se sobrescriben. Solapes parciales conservan fracción respecto de geometría fuente y ADM1; cruces por nombre están prohibidos. Eritrea sin filas es cobertura desconocida. Eventos EM-DAT de nivel país no se copian a todos los ADM1. La inseguridad alimentaria no se atribuye a sequía sin evidencia hazard separada.
- **auth_secrets:** FEWS NET usa su API pública anónima. IPC requiere `IPC_API_KEY`, nunca se imprime ni persiste y su ausencia falla de forma cerrada para ese adapter sin bloquear importaciones locales. EM-DAT se ingiere desde un archivo registrado aportado por el usuario. Se conservan los términos/licencias por registro; no se redistribuyen artefactos fuente restringidos ni se versionan datos descargados.
- **external_contracts:** FEWS NET usa `https://fdw.fews.net/api/ipcphase/` y `feature.geojson`, preservando FNID, scenario, scale, assistance, documentos y fechas. IPC usa `https://api.ipcinfo.org` conforme a su OpenAPI, preservando analysis ID, period, phase, fechas y GeoJSON. NDMA/otras autoridades entran mediante manifiesto local validado. EM-DAT entra mediante tabla registrada local con event ID, tipo, fechas y unidades administrativas explícitas.
- **ui_states:** No hay UI, endpoint ni entrenamiento. Un CLI de importación permite seleccionar fuentes, plan/dry-run, checkpoint/resume, retry acotado, ETA y rutas locales opcionales. Produce JSONL normalizado y manifiesto con cobertura, exclusiones, hashes y versiones de reglas.
- **rollback_compat:** Es aditivo y no altera features ADM1, dataset nacional ni probabilidades públicas. Los artefactos quedan bajo `data/historical/` ignorado. Cada adapter puede deshabilitarse; una fuente ausente no cambia el significado de las restantes. El schema y las reglas de cruce se versionan.
- **tests:** Tests offline con fixtures pequeñas cubren paginación/retry/resume/ETA, assessed frente a projected, valores unknown, asistencia, fechas anti-lookahead, secreto IPC ausente, importadores locales, licencias/hashes, cruce espacial por solape y rechazo de geometrías ambiguas. Ningún test depende de red ni secretos. Un smoke humano FEWS NET descarga una muestra pública; IPC/EM-DAT solo se prueban realmente si el usuario dispone de credenciales/archivo.

