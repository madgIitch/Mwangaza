# sprint-15-parquet-cache · undefined — Diseño

## Scope (archivos que puede tocar)

- `src/mwangaza/cache/**`
- `data/cache/.gitkeep`
- `tests/cache/**`
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

- **data_model:** Sprint 15 introduce una cache analitica local versionada para payloads serializables. La clave se deriva de region, indicador, periodo, fuente, version de algoritmo y tipo de dato. El valor conserva payload, metadata de cache, `created_at`, `expires_at`, `cache_key` y `algorithm_version`. Se usa JSON determinista como formato portable; la interfaz mantiene el concepto de cache analitica aunque no se exige dependencia Parquet externa.
- **error_states:** Claves incompletas, TTL invalido, entradas expiradas, archivos corruptos, payload no serializable y rutas inseguras producen miss controlado o `CacheError`. Un archivo corrupto se ignora para permitir regeneracion.
- **edge_cases:** La escritura se hace a archivo temporal en el mismo directorio y se publica con rename atomico. Un hit valido evita invocar el productor. El TTL se configura por tipo de dato. La cache no guarda secretos ni rutas privadas en metadata publica.
- **auth_secrets:** Sprint 15 no introduce secretos. Se rechazan campos de metadata/payload cuyo nombre sugiera credenciales (`private_key`, `service_account`, `token`, `secret`, `password`).
- **external_contracts:** Contrato publico en `mwangaza.cache`: `CacheKey`, `CacheEntry`, `CacheConfig`, `CacheError`, `AnalyticalCache.get_or_compute(...)`, `read(...)`, `write(...)` y `build_cache_key(...)`.
- **ui_states:** No hay UI nueva. La metadata de cache distingue `hit`, `miss`, `expired` y `corrupt` para futuros resúmenes.
- **rollback_compat:** No cambia contratos de datos ni sprints 0-14. Cache es modulo nuevo bajo `src/mwangaza/cache/**`.
- **tests:** Tests bajo `tests/cache/**` cubren clave estable, hit sin recomputar, escritura atomica, corrupto como miss, TTL por tipo y bloqueo de secretos.

