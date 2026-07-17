# sprint-33-public-api · undefined — Requisitos

- name: `Sprint 33 - Public API` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-17T11:39:58.215Z

## Contexto



## Requisitos funcionales

R1. Existen `/health`, `/api/v1/regions`, `/api/v1/snapshots/latest`, `/api/v1/alerts`, `/api/v1/forecasts` y `/openapi.json`.
R2. Ningun endpoint `/api/v1/**` inicia calculos Earth Engine ni llama al loader live bajo peticion publica.
R3. Las respuestas publicas incluyen `schema_version` y campos contractuales estables.
R4. Los errores usan `{error:{code,message}}` sin stack traces, rutas locales ni secretos.
R5. Listados aceptan `limit` y `offset`, aplican limite maximo 100 y devuelven `total`.
R6. OpenAPI se genera automaticamente como JSON y contiene ejemplos para los endpoints v1.

