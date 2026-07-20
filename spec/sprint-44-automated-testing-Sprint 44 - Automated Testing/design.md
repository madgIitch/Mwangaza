# sprint-44-automated-testing · undefined — Diseño

## Scope (archivos que puede tocar)

- `tests/**`
- `.github/workflows/ci.yml`
- `.harness/**`
- `pyproject.toml`
- `uv.lock`
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

- **data_model:** Las fixtures deterministas viven en `tests/fixtures/` y ofrecen reloj fijo, respuestas Earth Engine falsas y adaptadores de notificación en memoria. No contienen credenciales ni dependen de red.
- **error_states:** CI separa fallos de lint/typecheck, unit/integration, contract, frontend smoke y coverage. Cada job/comando devuelve código distinto de cero y muestra el grupo que falló.
- **edge_cases:** La suite cubre explícitamente `no_data`, calidad insuficiente, cache corrupta y reintento; el reloj y backoff se inyectan para no dormir. Los tests no dependen del orden ni de estado compartido.
- **auth_secrets:** Earth Engine y notificaciones se sustituyen por fakes; CI no necesita credenciales. `.env` local no se carga y los payloads de fixtures no incluyen secretos.
- **external_contracts:** Los contratos API v1 y JSON de dominio se ejecutan en un grupo dedicado que bloquea CI. El smoke canónico abre rutas React `/overview`, `/region`, `/alerts`, `/reports`, `/about`, `/admin` y `/technical`; `app.py` recibe sólo un smoke de compatibilidad/importación.
- **ui_states:** El smoke usa fixtures demo, verifica headings/controles esenciales y cubre low-bandwidth. No inicia Earth Engine ni servicios externos.
- **rollback_compat:** Se mantienen `make lint`, `make typecheck` y `make test`; se añaden targets aditivos `test-contract`, `test-frontend`, `coverage` y `quality-gate`.
- **tests:** Coverage mide módulos críticos configurados y aplica un mínimo inicial verificable del 70%. La configuración queda en `pyproject.toml` y puede elevarse en sprints posteriores.
