# sprint-1-configuration-and-secrets · undefined — Requisitos

- name: `Sprint 1 - Configuration and Secrets` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-14T12:46:49.001Z

## Contexto



## Requisitos funcionales

R1. AC1: En perfil production, crear Settings o arrancar los entrypoints publicos falla con excepcion controlada y mensaje accionable que incluye el nombre de cada variable obligatoria ausente, sin incluir valores secretos.
R2. AC2: En perfil test, Settings se construye sin credenciales reales de servicios externos y los tests no requieren variables privadas en el entorno.
R3. AC3: Ninguna representacion de Settings, logs capturados ni respuestas HTTP expone valores de variables marcadas como privadas; como minimo deben aparecer omitidas o enmascaradas.
R4. AC4: Las fechas de climatologia y la lista de paises habilitados se leen desde configuracion externa documentada y pueden cambiarse sin modificar codigo Python.
R5. AC5: En perfil demo, los entrypoints publicos pueden ejecutarse usando solo rutas de fixtures locales configuradas, sin llamadas remotas ni credenciales externas.
R6. AC6: La documentacion y .env.example separan explicitamente variables publicas/no sensibles de variables privadas/secretas, indicando obligatoriedad por perfil.
R7. AC7: Los nombres de variables existentes de Sprint 0 se mantienen o se documenta una migracion compatible con aviso claro.
R8. AC8: Hay tests automatizados para production incompleto, test sin secretos, demo con fixtures, validacion de fechas/paises y sanitizacion de secretos en repr/log/HTTP.

## Restricciones

- **error_states:** El modulo no falla al importarse. Los errores ocurren al ejecutar `load_settings()` o entrypoints que cargan configuracion. En `production`, configuracion incompleta o invalida levanta `ConfigurationError` con mensaje accionable, nombres de variables, perfil activo y accion sugerida, sin valores secretos. CLI/refresh devuelve codigo distinto de cero cuando no sea un dry-run seguro.
- **auth_secrets:** Variables privadas: `MWANGAZA_GEE_SERVICE_ACCOUNT` y `MWANGAZA_GEE_PRIVATE_KEY_JSON`. En `production` son obligatorias junto con `MWANGAZA_GEE_PROJECT`. Variables publicas/no sensibles quedan enumeradas. En `local`, `test` y `demo` no se requieren credenciales reales.
- **rollback_compat:** Se mantienen como canonicos los nombres existentes de Sprint 0: `MWANGAZA_GEE_PROJECT`, `MWANGAZA_GEE_SERVICE_ACCOUNT` y `MWANGAZA_GEE_PRIVATE_KEY_JSON`. `.env.example` debe actualizarse con nuevas variables publicas, secciones publica/privada y placeholders no sensibles. No hay renombres en Sprint 1.

