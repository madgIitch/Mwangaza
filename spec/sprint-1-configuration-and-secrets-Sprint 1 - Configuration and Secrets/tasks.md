# sprint-1-configuration-and-secrets · undefined — Tareas

Checklist de implementación. El agente marca [x] al completar; los gates verifican.

- [x] (T1) AC1: En perfil production, crear Settings o arrancar los entrypoints publicos falla con excepcion controlada y mensaje accionable que incluye el nombre de cada variable obligatoria ausente, sin incluir valores secretos.  ↔ R1
- [x] (T2) AC2: En perfil test, Settings se construye sin credenciales reales de servicios externos y los tests no requieren variables privadas en el entorno.  ↔ R2
- [x] (T3) AC3: Ninguna representacion de Settings, logs capturados ni respuestas HTTP expone valores de variables marcadas como privadas; como minimo deben aparecer omitidas o enmascaradas.  ↔ R3
- [x] (T4) AC4: Las fechas de climatologia y la lista de paises habilitados se leen desde configuracion externa documentada y pueden cambiarse sin modificar codigo Python.  ↔ R4
- [x] (T5) AC5: En perfil demo, los entrypoints publicos pueden ejecutarse usando solo rutas de fixtures locales configuradas, sin llamadas remotas ni credenciales externas.  ↔ R5
- [x] (T6) AC6: La documentacion y .env.example separan explicitamente variables publicas/no sensibles de variables privadas/secretas, indicando obligatoriedad por perfil.  ↔ R6
- [x] (T7) AC7: Los nombres de variables existentes de Sprint 0 se mantienen o se documenta una migracion compatible con aviso claro.  ↔ R7
- [x] (T8) AC8: Hay tests automatizados para production incompleto, test sin secretos, demo con fixtures, validacion de fechas/paises y sanitizacion de secretos en repr/log/HTTP.  ↔ R8
- [x] Tests que cubran los criterios de aceptación
