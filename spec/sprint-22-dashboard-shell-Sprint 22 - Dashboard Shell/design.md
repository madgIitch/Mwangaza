# sprint-22-dashboard-shell · undefined — Diseño

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

- **data_model:** Sprint 22 introduce un view model demo/mock bajo `src/mwangaza/services/**` con dataclasses para marca, tagline, ultima actualizacion, estado de datos, modo de origen, navegacion, region seleccionada, metricas, alertas y recomendaciones. El loader por defecto no consulta SQLite, Earth Engine ni servicios remotos.
- **error_states:** Los errores de carga del view model o configuracion se capturan en `render_dashboard(...)` y producen un banner seguro con shell degradado. La salida visible nunca incluye traceback, clase interna de excepcion, secretos, rutas locales ni valores privados.
- **edge_cases:** El layout se disena para 1366x768 sin scroll horizontal, con CSS `overflow-x: hidden`, tracks responsivos, `min-width: 0` y textos que envuelven/truncan. En entorno sin Streamlit, el entrypoint emite una salida CLI compacta y no falla.
- **auth_secrets:** Sprint 22 no lee ni muestra secretos. Cualquier estado de configuracion se muestra de forma saneada y no incluye valores privados.
- **external_contracts:** Se conservan `streamlit run app.py` y `mwangaza.ui.dashboard.render_dashboard(...)`. Se anaden contratos testeables `mwangaza.ui.dashboard.build_dashboard_shell_html(...)` y `mwangaza.services.dashboard_shell.load_dashboard_shell_data(...)`.
- **ui_states:** La UI renderiza una experiencia operacional inspirada en `UI-mockup.png`: sidebar izquierda con navegacion `Overview`, `Region`, `Alerts`, `Reports`, `About`; cabecera con fuente, ultima actualizacion y freshness; paneles de mapa/alertas/metricas. Distingue estados `current`, `stale`, `error`, `loading`, `empty` y origen `live`, `cache`, `demo` con chips visibles.
- **rollback_compat:** Cambio aditivo bajo `src/mwangaza/ui/**`, `src/mwangaza/services/**`, `tests/ui/**`, `app.py`, `docs/**`, `spec/**` y `progress/**`. La imagen `UI-mockup.png` se usa solo como referencia visual y no se incorpora al producto en este sprint.
- **tests:** Tests bajo `tests/ui/**` cubren portada, navegacion, diferenciacion live/cache/demo, fallback seguro ante error y contrato CSS anti-scroll horizontal. Los tests no requieren Streamlit instalado.

