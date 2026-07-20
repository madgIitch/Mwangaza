# sprint-42-observability · undefined — Diseño

## Scope (archivos que puede tocar)

- `src/mwangaza/observability/**`
- `tests/observability/**`
- `src/mwangaza/api/**`
- `src/mwangaza/contracts/**`
- `src/mwangaza/db/**`
- `tests/api/**`
- `frontend/**`
- `tests/frontend/**`
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

- **data_model:** La observabilidad usa eventos JSON con `timestamp`, `level`, `component`, `event`, `run_id` y metadatos saneados. Las métricas se mantienen como contadores y duraciones agregadas del proceso; no almacenan payloads operativos completos.
- **error_states:** `/health` confirma que el proceso responde. `/ready` devuelve 200 cuando las dependencias obligatorias están disponibles y 503 con checks saneados cuando la base SQLite o el directorio de cache requerido no pueden usarse. El panel distingue cargando, operativo, degradado y no disponible.
- **edge_cases:** Un `X-Run-ID` válido recibido se conserva; si falta o es inválido se genera uno nuevo. Errores, respuestas y logs comparten el identificador. Los fallos de logging o métricas no deben tumbar la API, y los contadores son seguros frente a concurrencia local.
- **auth_secrets:** La redacción es recursiva para claves sensibles y valores conocidos de credenciales. Logs, métricas, health y readiness no exponen secretos, payloads completos, rutas locales ni detalles internos de excepción.
- **external_contracts:** La API conserva `/health`, añade `/ready` y `/api/v1/observability`, y devuelve `X-Run-ID` en respuestas API. El frontend React añade `/technical`, separado de Overview, con estado de API, readiness y métricas resumidas.
- **ui_states:** `/technical` prioriza estado operativo, checks y métricas en una superficie compacta. No mezcla diagnósticos con la narrativa principal y mantiene una tabla legible en low-bandwidth.
- **rollback_compat:** Los payloads públicos existentes siguen siendo compatibles; sólo se añade la cabecera de correlación. `/health` mantiene sus campos actuales y agrega observabilidad sin eliminar contratos previos.
- **tests:** Tests unitarios cubren formato JSON, redacción, propagación/generación de run_id, readiness 200/503, métricas agregadas, correlación de error Earth Engine y estados frontend de `/technical`.

