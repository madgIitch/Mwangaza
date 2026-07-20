# sprint-41-admin-configuration · undefined — Requisitos

- name: `Sprint 41 - Admin Configuration` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-17T20:52:08.575Z

## Contexto



## Requisitos funcionales

R1. AC1: El panel admin React permite leer y modificar toda la configuración sin credenciales; la API no exige cabeceras de autenticación en lectura, guardado ni activación.
R2. AC2: El panel no solicita, almacena ni devuelve credenciales admin; los logs, auditoría y respuestas HTTP no incluyen secretos de administración.
R3. AC3: Guardar cambios de umbrales o acciones crea siempre una nueva versión append-only con `version_id`, `created_at`, `created_by`, estado, hash de contenido y snapshot de configuración; no reescribe versiones previas.
R4. AC4: Una configuración inválida devuelve errores de validación accionables y no pasa a estado activo; la versión activa anterior permanece disponible.
R5. AC5: Guardar o activar configuración no recalcula indicadores, cache, forecasts ni alertas hasta una acción explícita futura; los tests verifican que no se invocan rutas de refresco ni Earth Engine.
R6. AC6: Cada validación, guardado y activación registra auditoría saneada con actor público, acción, versión y resultado.
R7. AC7: El frontend admin muestra acceso público, editor, errores de validación, versión activa, historial y low-bandwidth sin simular seguridad institucional.
R8. AC8: La documentación indica el alcance público de la demo, formato de configuración versionada, rollback manual y que este panel requiere control de acceso antes de producción.

## Restricciones

- **error_states:** Estados de carga, validación, conflicto y persistencia saneados.
- **auth_secrets:** Sin credenciales admin en la demo.
- **rollback_compat:** Defaults existentes se conservan.
