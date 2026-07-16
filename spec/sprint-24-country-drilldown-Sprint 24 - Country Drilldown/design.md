# sprint-24-country-drilldown · undefined — Diseño

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

## Decisiones de la entrevista

- **data_model:** Sprint 24 consume los payloads live/cache/demo ya cargados por el dashboard: `RiskSnapshot`, indicator snapshots y observaciones por `region_id`. El view model del drilldown conserva el mapa regional y añade un perfil de país seleccionado con métricas, score, calidad, fuente, periodo, alertas y recomendaciones filtradas por región.
- **error_states:** Si una región no tiene snapshot, indicadores, alertas o recomendaciones, la vista muestra estados `No data`, empty/error seguros y `unknown` cuando corresponda. Un parámetro de URL o selector inválido cae a la región por defecto sin traceback, rutas locales, clases internas ni secretos.
- **edge_cases:** La selección de región no debe ocultar ni reemplazar el mapa y no debe crear renderizado anidado. Debe existir una sola instancia del shell y del mapa regional en el DOM del componente. Cambiar región debe mantener layout 1366x768 sin scroll horizontal y no duplicar dashboards, iframes ni mapas dentro de paneles.
- **auth_secrets:** El click, selector o URL state no disparan consultas Earth Engine arbitrarias ni aceptan geometría/colección/fechas desde usuario. La UI consume payloads ya acotados por configuración en live/cache/demo y no imprime ni renderiza credenciales, tokens, service accounts, private keys, rutas locales ni mensajes crudos de excepción.
- **external_contracts:** Se conservan `streamlit run app.py`, `mwangaza.ui.dashboard.render_dashboard(...)`, `build_dashboard_shell_html(...)` y `load_dashboard_shell_data(...)`. Sprint 24 puede ampliar los view models de `mwangaza.services.dashboard_shell` y el HTML determinista de `mwangaza.ui.dashboard`, sin romper el mapa regional de Sprint 23 ni los modos live/cache/demo.
- **ui_states:** Overview mantiene el mapa regional visible. Al seleccionar una región con click/teclado, selector manual o URL, el panel/navegación `Region` muestra el análisis funcional del país seleccionado: indicadores, anomalías disponibles, score, explicación, calidad, alertas y recomendaciones. Debe existir camino claro de vuelta a Overview y estados empty/loading/error por región.
- **rollback_compat:** Cambio aditivo dentro del dashboard. No cambia contratos de riesgo, cache, regiones, alertas ni GEE; solo reorganiza/filtra payloads existentes para la experiencia de región. Si se revierte, Sprint 23 debe seguir mostrando mapa regional live/cache/demo.
- **tests:** Tests bajo `tests/ui/**` cubren selección desde mapa, permanencia del mapa renderizado, ausencia de renderizado anidado, panel Region funcional, selector manual, URL state, no-data, alertas/recomendaciones por región y ausencia de consultas remotas al interactuar. Los tests no requieren Streamlit instalado, red ni GEE real.

