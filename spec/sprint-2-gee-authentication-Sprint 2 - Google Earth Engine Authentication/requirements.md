# sprint-2-gee-authentication · undefined — Requisitos

- name: `Sprint 2 - Google Earth Engine Authentication` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-14T13:02:40.619Z

## Contexto



## Requisitos funcionales

R1. El health check GEE devuelve un JSON saneado con `gee.status` en exactamente uno de `ok`, `auth_error`, `permission_error`, `quota_error` o `network_error`, y los tests verifican que los codigos son estables.
R2. En `production`, el adaptador GEE nunca inicia flujos interactivos ni lee credenciales de usuario locales; si faltan credenciales de servicio devuelve `auth_error` saneado.
R3. El secreto de cuenta de servicio puede cargarse desde `MWANGAZA_GEE_PRIVATE_KEY_JSON` como JSON en memoria, sin escribirlo a disco ni exponerlo en repr, logs, HTTP responses o dashboard.
R4. Los reintentos del adaptador usan backoff configurable, respetan el maximo configurado y los tests verifican numero de intentos y pausas mediante mocks/fakes sin dormir realmente.
R5. La suite automatica no importa ni llama Earth Engine real salvo mediante una frontera mockeable; los tests bloquean llamadas remotas accidentales.
R6. Existe una comprobacion manual documentada en `docs/` o `README.md` que indica variables necesarias, comando a ejecutar y resultado esperado para confirmar acceso real a Earth Engine.

## Restricciones

- **error_states:** Mapeo determinista: `auth_error` para credenciales ausentes/placeholder en production, JSON secreto malformado, JSON sin objeto, service account ausente o errores que contengan auth/credential/unauthorized; `permission_error` para forbidden/permission/403 o proyecto sin acceso; `quota_error` para quota/rate limit/429/resource exhausted; `network_error` para timeout, connection, DNS, unavailable/5xx transitorio. Errores desconocidos caen en `network_error` con `error_code="unknown_error"` y mensaje generico saneado.
- **auth_secrets:** El secreto JSON se carga exclusivamente desde `MWANGAZA_GEE_PRIVATE_KEY_JSON` en memoria junto con `MWANGAZA_GEE_SERVICE_ACCOUNT` y `MWANGAZA_GEE_PROJECT`. No se permite ruta ni archivo de secreto en ningun perfil. El adaptador no escribe secretos a disco ni registra valores. Login interactivo queda fuera de Sprint 2 y esta prohibido en production.
- **rollback_compat:** Se preservan invariantes de Sprint 1: nombres `MWANGAZA_GEE_PROJECT`, `MWANGAZA_GEE_SERVICE_ACCOUNT`, `MWANGAZA_GEE_PRIVATE_KEY_JSON`; `/health` nunca filtra secretos; local/test/demo siguen ejecutandose sin credenciales reales; `Settings` y `public_config_status` conservan su contrato; refresh `--dry-run` sigue sin llamadas remotas. No se introducen rutas de secretos ni fallback silencioso de production a demo.

