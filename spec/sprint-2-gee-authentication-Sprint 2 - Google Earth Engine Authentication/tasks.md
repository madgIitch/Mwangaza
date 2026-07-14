# sprint-2-gee-authentication · undefined — Tareas

Checklist de implementación. El agente marca [x] al completar; los gates verifican.

- [ ] (T1) El health check GEE devuelve un JSON saneado con `gee.status` en exactamente uno de `ok`, `auth_error`, `permission_error`, `quota_error` o `network_error`, y los tests verifican que los codigos son estables.  ↔ R1
- [ ] (T2) En `production`, el adaptador GEE nunca inicia flujos interactivos ni lee credenciales de usuario locales; si faltan credenciales de servicio devuelve `auth_error` saneado.  ↔ R2
- [ ] (T3) El secreto de cuenta de servicio puede cargarse desde `MWANGAZA_GEE_PRIVATE_KEY_JSON` como JSON en memoria, sin escribirlo a disco ni exponerlo en repr, logs, HTTP responses o dashboard.  ↔ R3
- [ ] (T4) Los reintentos del adaptador usan backoff configurable, respetan el maximo configurado y los tests verifican numero de intentos y pausas mediante mocks/fakes sin dormir realmente.  ↔ R4
- [ ] (T5) La suite automatica no importa ni llama Earth Engine real salvo mediante una frontera mockeable; los tests bloquean llamadas remotas accidentales.  ↔ R5
- [ ] (T6) Existe una comprobacion manual documentada en `docs/` o `README.md` que indica variables necesarias, comando a ejecutar y resultado esperado para confirmar acceso real a Earth Engine.  ↔ R6
- [ ] Tests que cubran los criterios de aceptación
