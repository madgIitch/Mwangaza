# sprint-33-public-api · undefined — Tareas

Checklist de implementación. El agente marca [x] al completar; los gates verifican.

- [x] (T1) Existen `/health`, `/api/v1/regions`, `/api/v1/snapshots/latest`, `/api/v1/alerts`, `/api/v1/forecasts` y `/openapi.json`.  ↔ R1
- [x] (T2) Ningun endpoint `/api/v1/**` inicia calculos Earth Engine ni llama al loader live bajo peticion publica.  ↔ R2
- [x] (T3) Las respuestas publicas incluyen `schema_version` y campos contractuales estables.  ↔ R3
- [x] (T4) Los errores usan `{error:{code,message}}` sin stack traces, rutas locales ni secretos.  ↔ R4
- [x] (T5) Listados aceptan `limit` y `offset`, aplican limite maximo 100 y devuelven `total`.  ↔ R5
- [x] (T6) OpenAPI se genera automaticamente como JSON y contiene ejemplos para los endpoints v1.  ↔ R6
- [x] Tests que cubran los criterios de aceptación
