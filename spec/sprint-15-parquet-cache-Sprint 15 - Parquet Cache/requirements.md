# sprint-15-parquet-cache · undefined — Requisitos

- name: `Sprint 15 - Parquet Cache` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-15T15:56:59.946Z

## Contexto



## Requisitos funcionales

R1. `build_cache_key(...)` produce una clave estable que incluye region, indicador, periodo, fuente, version de algoritmo y tipo de dato.
R2. `AnalyticalCache.get_or_compute(...)` devuelve una entrada valida desde cache sin invocar el productor cuando hay hit no expirado.
R3. Las escrituras usan un archivo temporal en el mismo directorio y se publican con reemplazo atomico.
R4. Una entrada corrupta se trata como miss controlado y permite regenerar el payload.
R5. El TTL es configurable por tipo de dato y una entrada expirada no cuenta como hit.
R6. La cache rechaza payloads o metadata con campos sensibles como private keys, tokens, secrets, passwords o service accounts.
R7. Las entradas serializadas conservan `cache_key`, `algorithm_version`, `created_at`, `expires_at`, payload y metadata de cache.
R8. La suite automatizada no llama Earth Engine ni requiere credenciales y cubre hit, miss, corrupto, TTL, atomicidad y bloqueo de secretos.

