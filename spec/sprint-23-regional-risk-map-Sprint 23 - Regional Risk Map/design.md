# sprint-23-regional-risk-map · undefined — Diseño

## Scope (archivos que puede tocar)

- `app.py`
- `src/mwangaza/ui/**`
- `src/mwangaza/services/**`
- `assets/**`
- `tests/ui/**`
- `tests/maps/**`
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
- `src/mwangaza/maps/**`
- `smoke_tests/**`

## Decisiones de la entrevista

- **data_model:** Sprint 23 consume el catalogo local de regiones IGAD y snapshots de riesgo ya saneados desde cache/local fixtures. El view model del mapa contiene por region: `region_id`, `name`, `iso3`, `ui_geometry`, `risk_level`, `score`, `period_start`, `period_end`, `quality_flag`, `source_mode` y metadata de trazabilidad. Una region sin snapshot valido se representa como `unknown`, nunca como `green`.
- **error_states:** Si faltan geometria, cache o snapshots, el mapa sigue renderizando la region con estado `unknown` y tooltip explicativo. Si el constructor del mapa falla, `render_dashboard(...)` conserva el fallback seguro de Sprint 22 sin traceback, rutas locales, clases internas ni secretos.
- **edge_cases:** El mapa usa las `ui_geometry` GeoJSON del catalogo en WGS84 sin reproyectar ni mezclar CRS. Los scores ausentes, no finitos o con calidad bloqueante se muestran como `unknown`. El layout mantiene el contrato 1366x768 sin scroll horizontal y no depende de red ni assets remotos para renderizar fixtures.
- **auth_secrets:** El dashboard no lee credenciales ni ejecuta Earth Engine. El script de smoke real en `smoke_tests/` lee credenciales exclusivamente desde variables de entorno ya definidas para GEE, no imprime secretos y valida que los payloads/cache generados no contienen claves como `private_key`, `service_account`, `token`, `secret` o `password`.
- **external_contracts:** Se conservan `streamlit run app.py`, `mwangaza.ui.dashboard.render_dashboard(...)`, `build_dashboard_shell_html(...)` y `load_dashboard_shell_data(...)`. Se anade un contrato testeable bajo `mwangaza.maps` o `mwangaza.services` para construir el modelo/HTML del mapa desde regiones y snapshots locales. Streamlit consume cache local materializada; GEE solo puede ejecutarse desde el script de smoke.
- **ui_states:** La vista Overview sustituye el placeholder de mapa por un mapa coropletico regional con leyenda visible para `green`, `yellow`, `orange`, `red` y `unknown`. Cada region expone tooltip con region, score, nivel, periodo y calidad. La seleccion de una region actualiza el estado visual de navegacion/region seleccionada sin afirmar cobertura subnacional completa fuera de pilotos.
- **rollback_compat:** Cambio aditivo dentro del scope de Sprint 23. No cambia los contratos de riesgo, cache, regiones, dashboard ni alertas anteriores; solo consume sus payloads ya saneados y conserva el modo demo/cache/live introducido en Sprint 22.
- **tests:** Tests bajo `tests/ui/**` o `tests/maps/**` cubren colores/leyenda, tooltip, unknown para regiones sin datos, uso de `ui_geometry`, seleccion de region, render con fixtures sin Streamlit ni red y ausencia de secretos en payloads de smoke/cache. El script real GEE queda versionado en `smoke_tests/` y es manual/opt-in.

