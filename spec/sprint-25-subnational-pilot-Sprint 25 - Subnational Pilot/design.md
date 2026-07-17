# sprint-25-subnational-pilot · undefined — Diseño

## Scope (archivos que puede tocar)

- `app.py`
- `src/mwangaza/ui/**`
- `src/mwangaza/services/**`
- `assets/**`
- `tests/ui/**`
- `pyproject.toml`
- `requirements*.txt`
- `Makefile`
- `.env.example`
- `.gitignore`
- `.github/workflows/**`
- `.harness/gates.config.json`
- `docs/**`
- `spec/**`
- `progress/**`
- `src/mwangaza/data/**`
- `src/mwangaza/gee/**`
- `src/mwangaza/contracts/**`
- `tests/data/**`
- `tests/fixtures/**`

## Decisiones de la entrevista

- **data_model:** Sprint 25 usa solo regiones `is_pilot=true` del catálogo local (`pilot_area`) y las vincula a su `parent_id`. El view model subnacional contiene `pilot_id`, `name`, `parent_id`, `parent_label`, `level`, `coverage_type`, `geometry_source`, `score`, `risk_level`, `quality_flag`, `coverage_note`, `rank` y trazabilidad del snapshot padre. Mientras no existan agregados subnacionales propios, el piloto se etiqueta como prototipo y no como cobertura administrativa completa.
- **error_states:** Si falta parent, snapshot, score o cobertura suficiente, el piloto aparece como `unknown` o `No data`, nunca como `green` por defecto. Si no hay pilotos disponibles, el panel muestra empty state seguro. Errores de catálogo o datos se manejan sin traceback, rutas locales ni secretos.
- **edge_cases:** Solo Somalia y norte de Kenia ofrecen drilldown subnacional en 1.0. El resto de países conserva análisis nacional y una explicación visible. El ranking ordena por score numérico descendente, empujando `None` al final. Cobertura insuficiente o datos no concluyentes se muestran como `unknown`.
- **auth_secrets:** El panel subnacional no dispara consultas Earth Engine bajo interacción de usuario. Consume payloads live/cache/demo ya cargados y catálogo local. No renderiza credenciales, tokens, rutas locales ni mensajes crudos de excepción.
- **external_contracts:** Se conservan `streamlit run app.py`, `render_dashboard(...)`, `build_dashboard_shell_html(...)` y `load_dashboard_shell_data(...)`. Se puede ampliar `DashboardShellData` con un view model de pilotos y render HTML/JS determinista bajo `src/mwangaza/ui/**` y `src/mwangaza/services/**`.
- **ui_states:** El panel Region muestra una sección subnacional cuando el país seleccionado tiene pilotos. Incluye selector/ranking de pilotos, parent, nivel, fuente de geometría, cobertura/limitación y score/riesgo. Para países sin piloto, muestra una explicación de que el IGAD restante se ofrece a nivel nacional en 1.0.
- **rollback_compat:** Cambio aditivo sobre Sprint 24. Si se revierte, el drilldown nacional y mapa regional siguen funcionando. No cambia contratos de datos ni catálogo.
- **tests:** Tests bajo `tests/ui/**` cubren que solo regiones piloto ofrecen subnacional, que cada unidad muestra parent/nivel/fuente, que el ranking usa score numérico, que `unknown` no se mezcla con green, que países sin piloto muestran explicación nacional y que no hay llamadas remotas al interactuar.

