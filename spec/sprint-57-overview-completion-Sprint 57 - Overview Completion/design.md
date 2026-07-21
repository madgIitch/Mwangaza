# sprint-57-overview-completion · undefined — Diseño

## Scope (archivos que puede tocar)

- `frontend/**`
- `tests/frontend/**`
- `src/mwangaza/api/**`
- `tests/api/**`
- `src/mwangaza/services/dashboard_shell.py`
- `src/mwangaza/reports/**`
- `src/mwangaza/exports/**`
- `tests/reports/**`
- `tests/exports/**`
- `docs/overview-interface.md`
- `docs/contracts.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS.md`
- `spec/sprint-57-overview-completion-*/**`
- `progress/**`

## Enfoque

- **data_model:** Snapshot procesado con IDs y descargas contextuales aditivas.
- **external_contracts:** Rutas de detalle y endpoints de descarga concretos.
- **edge_cases:** Zoom, selección, orden y comparación deterministas.
- **ui_states:** Cockpit completo, accesible y equivalente en low-bandwidth.

## Decisiones de la entrevista

- **data_model:** Overview consume el snapshot y los perfiles regionales ya procesados. El contrato de alertas incorpora un `id` estable y detalle trazable; las descargas reciben región y periodo explícitos. Indicadores, tendencias, deltas, calidad, fuente y geometría permanecen aditivos y conservan `null` cuando no hay evidencia. No se recalculan datos ni se consulta GEE desde el navegador.
- **error_states:** Mapa, alertas, tendencias y descargas fallan de forma independiente. Sin geometría se muestra tabla/estado explícito; sin comparación no se inventa delta; una descarga fallida muestra error recuperable y no genera un archivo vacío; alertas inexistentes devuelven 404 saneado. Cache, live, demo y offline mantienen procedencia visible.
- **edge_cases:** Home restaura el encuadre IGAD; zoom queda acotado entre 1× y 4×; la capa activa sólo cambia la representación de datos ya cargados. La selección regional se conserva si existe en el nuevo periodo y vuelve a la región canónica si desaparece. Alertas se ordenan por severidad, score, periodo e identificador estable. Los deltas sólo comparan ventanas estacionales equivalentes.
- **auth_secrets:** Los endpoints públicos generan archivos exclusivamente desde snapshots procesados y aplican límites, nombres y cabeceras seguras. No aceptan geometría arbitraria, credenciales ni parámetros GEE. Cuenta y notificaciones continúan como estados explícitos no interactivos hasta disponer de contratos aprobados; no se simula autenticación.
- **external_contracts:** `View details` abre `/alerts/<alert_id>` y `View all alerts` abre `/alerts?region=<id>&period=<period>&status=active`. Overview descarga el PDF ejecutivo desde `/api/v1/reports/executive?region=<id>&period=<period>` y CSV/JSON desde `/api/v1/exports/snapshot?region=<id>&period=<period>&format=<csv|json>`, con `Content-Disposition` y nombres deterministas. La vista ofrece capas `Risk` y `Data quality`, ambas derivadas del snapshot.
- **ui_states:** El cockpit se organiza en mapa y alertas prioritarias, contexto de región seleccionada, métricas/tendencias y una única zona de acción. El mapa incluye Home, zoom, selector de capa y tooltip accesible con score, indicadores, calidad, fuente y periodo. El selector de idioma conserva ES por compatibilidad y añade Somali; la superficie segmentada prioriza EN/SW/SO. Low-bandwidth sustituye mapa y gráficos por tablas equivalentes.
- **rollback_compat:** `/` conserva equivalencia con `/overview`; las rutas actuales y campos API se preservan. Los nuevos IDs, endpoints y locale `so` son aditivos. El Sprint 57 sólo conecta acciones del cockpit; la gestión, cola, preview y distribución completas del Reports Center permanecen en Sprint 59.
- **tests:** Bloquean pruebas frontend y API para controles de mapa, tooltip, selección, low-bandwidth, detalle/deep-links de alertas, locale Somali, delta comparable/ausente, PDF/CSV/JSON reales y errores saneados. Se verifica que ninguna interacción invoca GEE, que no se colorea `no_data` como bajo y que demo funciona offline.

