# sprint-15-parquet-cache · undefined — Tareas

Checklist de implementación. El agente marca [x] al completar; los gates verifican.

- [x] (T1) `build_cache_key(...)` produce una clave estable que incluye region, indicador, periodo, fuente, version de algoritmo y tipo de dato.  ↔ R1
- [x] (T2) `AnalyticalCache.get_or_compute(...)` devuelve una entrada valida desde cache sin invocar el productor cuando hay hit no expirado.  ↔ R2
- [x] (T3) Las escrituras usan un archivo temporal en el mismo directorio y se publican con reemplazo atomico.  ↔ R3
- [x] (T4) Una entrada corrupta se trata como miss controlado y permite regenerar el payload.  ↔ R4
- [x] (T5) El TTL es configurable por tipo de dato y una entrada expirada no cuenta como hit.  ↔ R5
- [x] (T6) La cache rechaza payloads o metadata con campos sensibles como private keys, tokens, secrets, passwords o service accounts.  ↔ R6
- [x] (T7) Las entradas serializadas conservan `cache_key`, `algorithm_version`, `created_at`, `expires_at`, payload y metadata de cache.  ↔ R7
- [x] (T8) La suite automatizada no llama Earth Engine ni requiere credenciales y cubre hit, miss, corrupto, TTL, atomicidad y bloqueo de secretos.  ↔ R8
- [x] Tests que cubran los criterios de aceptación
