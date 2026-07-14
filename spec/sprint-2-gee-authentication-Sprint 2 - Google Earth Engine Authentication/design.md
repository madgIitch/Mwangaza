# sprint-2-gee-authentication · undefined — Diseño

## Scope (archivos que puede tocar)

- `src/mwangaza/config/**`
- `src/mwangaza/gee/**`
- `src/mwangaza/api/**`
- `src/mwangaza/data/**`
- `src/mwangaza/ui/**`
- `tests/**`
- `.env.example`
- `README.md`
- `pyproject.toml`
- `docs/**`
- `spec/**`
- `progress/**`

## Enfoque

- **data_model:** Contrato publico definido bajo `gee` en `/health` y en `GeeAuthResult.to_public_dict()`: `status` literal `ok|auth_error|permission_error|quota_error|network_error`; `configured` bool; `project_configured` bool; `service_account_configured` bool; `checked_at` ISO8601 UTC string; `attempts` int; `max_attempts` int; `message` string saneado; `missing_required_variables` list[str]; `error_code` string estable opcional. Nunca incluye project id, service account, private key ni payload JSON.
- **external_contracts:** Contrato canonico: modulo `src/mwangaza/gee/auth.py`; dataclass `GeeAuthResult`; funcion `check_gee_auth(settings: Settings | None = None, *, ee_module: object | None = None, max_attempts: int | None = None, base_delay_seconds: float = 0.1, sleep: Callable[[float], None] | None = None) -> GeeAuthResult`. `max_attempts` default 3. Backoff exponencial `base_delay_seconds * 2 ** (attempt - 1)`. `settings.max_remote_pixels` solo se usa como configuracion existente, no para consultar datos. API `/health` incluye `gee` usando el mismo resultado saneado. No se anade endpoint nuevo en Sprint 2.
- **edge_cases:** Casos cerrados: SDK `ee` no instalado devuelve `auth_error`; local/test/demo sin credenciales no autentican remotamente y devuelven `auth_error` con `configured=false` solo si se llama al health GEE; JSON malformado, JSON no objeto, campos minimos ausentes o `private_key` ausente devuelven `auth_error`; timeout devuelve `network_error`; cuota devuelve `quota_error`; permisos o proyecto incorrecto devuelven `permission_error`; credenciales revocadas devuelven `auth_error`.
- **ui_states:** El dashboard muestra un estado GEE saneado y compacto: `gee.status`, `configured`, `attempts` y mensaje generico, sin valores de credenciales. En local/test/demo puede mostrar `auth_error/configured=false` sin bloquear el resto del placeholder. En production con configuracion invalida no muestra claims operativos.

## Decisiones de la entrevista

- **adv-1277a26eea:** El entrypoint observable canonico es `GET /health`, que incluye `gee` anidado. Tambien existe la funcion `check_gee_auth(...)` y el comando manual `python -m mwangaza.gee.auth --check`, pero no se agrega endpoint HTTP separado en Sprint 2.
- **adv-281e7e308f:** El JSON saneado de `gee` puede incluir solo `status`, `configured`, `project_configured`, `service_account_configured`, `checked_at`, `attempts`, `max_attempts`, `message`, `missing_required_variables` y `error_code`. No se permite exponer proyecto real, service account real, private key, client_email ni JSON completo aunque algunos sean no secretos.
- **adv-27416e87cc:** Mapeo estable: HTTP 401/credenciales/auth/credential/unauthorized/credenciales revocadas/JSON invalido -> `auth_error`; HTTP 403/forbidden/permission/proyecto sin acceso -> `permission_error`; HTTP 429/quota/rate/resource exhausted -> `quota_error`; timeout/DNS/connection/unavailable/5xx/desconocido -> `network_error`.
- **adv-58c91bb6ae:** `GET /health` mantiene HTTP 200 para todos los estados GEE; los errores de GEE no hacen fallar el health global porque pueden no estar configurados en local/test/demo. El resultado se expresa solo dentro de `gee.status` y `gee.configured`.
- **adv-121bbe5794:** No se agregan nuevas variables de entorno de retry en Sprint 2. Defaults: `max_attempts=3`, `base_delay_seconds=0.1`, unidad segundos, backoff exponencial `base_delay_seconds * 2 ** (attempt - 1)`. Solo se pueden cambiar por argumentos de `check_gee_auth(...)` en tests o llamadas internas.
- **data_model:** El schema publico se expone bajo `gee` en `/health` y por `GeeAuthResult.to_public_dict()`: `status` literal `ok|auth_error|permission_error|quota_error|network_error`; `configured` bool; `project_configured` bool; `service_account_configured` bool; `checked_at` ISO8601 UTC string; `attempts` int; `max_attempts` int; `message` string saneado; `missing_required_variables` list[str]; `error_code` string estable opcional. Nunca incluir project id, service account, private key ni payload JSON.
- **error_states:** `auth_error`: credenciales ausentes/placeholder en production, JSON secreto malformado, JSON sin objeto, service account ausente o errores que contengan auth/credential/unauthorized. `permission_error`: errores forbidden/permission/403 o proyecto sin acceso. `quota_error`: quota/rate limit/429/resource exhausted. `network_error`: timeout, connection, DNS, unavailable/5xx transitorio. Fallback para errores desconocidos: `network_error` con `error_code="unknown_error"` y mensaje generico saneado.
- **edge_cases:** Edge cases bloqueantes y estado: SDK `ee` no instalado -> `auth_error` en production y `auth_error` saneado en chequeo manual; local/test/demo sin credenciales -> no autenticar remotamente y devolver `auth_error` solo si se llama al health GEE, con `configured=false`; JSON malformado o sin campos minimos -> `auth_error`; `private_key` ausente en JSON -> `auth_error`; timeout -> `network_error`; cuota -> `quota_error`; permisos/proyecto incorrecto -> `permission_error`; credenciales revocadas -> `auth_error`.
- **auth_secrets:** En Sprint 2 el secreto JSON se carga exclusivamente desde `MWANGAZA_GEE_PRIVATE_KEY_JSON` en memoria junto con `MWANGAZA_GEE_SERVICE_ACCOUNT` y `MWANGAZA_GEE_PROJECT`. No se permite ruta/archivo de secreto en ningun perfil. El adaptador no escribe secretos a disco y no registra valores. Login interactivo solo podra habilitarse en features futuras; en production esta prohibido.
- **external_contracts:** Contrato canonico: modulo `src/mwangaza/gee/auth.py`; dataclass `GeeAuthResult`; funcion `check_gee_auth(settings: Settings | None = None, *, ee_module: object | None = None, max_attempts: int | None = None, base_delay_seconds: float = 0.1, sleep: Callable[[float], None] | None = None) -> GeeAuthResult`. Usa `settings.max_remote_pixels` solo como configuracion existente, no para consultar datos. `max_attempts` default 3. Backoff exponencial `base_delay_seconds * 2 ** (attempt - 1)`, sin dormir en tests mediante fake sleep. API `/health` debe incluir `gee` usando el mismo resultado saneado; no se anade endpoint nuevo en Sprint 2.
- **ui_states:** El dashboard debe mostrar un estado GEE saneado y compacto: `gee.status`, `configured`, `attempts` y mensaje generico, sin valores de credenciales. En local/test/demo puede mostrar `auth_error/configured=false` sin bloquear el resto del placeholder. En production con configuracion invalida no debe mostrar claims operativos.
- **rollback_compat:** Permanecen invariantes: nombres `MWANGAZA_GEE_PROJECT`, `MWANGAZA_GEE_SERVICE_ACCOUNT`, `MWANGAZA_GEE_PRIVATE_KEY_JSON`; `/health` nunca filtra secretos; local/test/demo siguen ejecutandose sin credenciales reales; `Settings` y `public_config_status` conservan su contrato; refresh `--dry-run` sigue sin llamadas remotas. No introducir rutas de secretos ni fallback silencioso de production a demo.
- **tests:** Tests unitarios con fakes: credenciales ausentes, JSON secreto en memoria, JSON invalido, SDK ausente, auth error, permission error, quota error, network timeout, exito, reintentos/backoff sin dormir y `/health` saneado. Ningun test debe importar ni llamar Earth Engine real. La comprobacion manual vive en `docs/earth-engine.md` e indica variables, comando `python -m mwangaza.gee.auth --check`, resultado esperado y advertencia de no commitear secretos.

