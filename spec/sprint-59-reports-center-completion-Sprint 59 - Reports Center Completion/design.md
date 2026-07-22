# sprint-59-reports-center-completion · undefined — Diseño

## Scope (archivos que puede tocar)

- `frontend/**`
- `tests/frontend/**`
- `src/mwangaza/api/**`
- `tests/api/**`
- `src/mwangaza/reports/**`
- `tests/reports/**`
- `src/mwangaza/audit/**`
- `tests/audit/**`
- `src/mwangaza/services/dashboard_shell.py`
- `tests/ui/test_dashboard_shell.py`
- `docs/reports-interface.md`
- `docs/executive-report.md`
- `docs/audit-trail.md`
- `docs/contracts.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS.md`
- `spec/sprint-59-reports-center-completion-*/**`
- `progress/**`

## Enfoque

- **data_model:** La spec debe definir que la API es propietaria de identidad y tiempos. Cada reporte expone `id`, `generated_at`, `updated_at`, `expires_at` opcional, `status` (`queued`, `generating`, `ready`, `failed`, `expired`), `region_id`, `period_start`, `period_end`, `template_id`, `language`, `author`, `snapshot_id`, formatos disponibles y error saneado opcional. IDs y timestamps son estables, UTC ISO-8601, y el navegador no los inventa. Exportaciones recientes y eventos de auditoría tienen IDs propios y referencian al reporte.
- **external_contracts:** La spec aprueba endpoints aditivos bajo `/api/v1/reports` para listar reportes, obtener detalle, generar reportes y descargar PDF/CSV/JSON. La generación usa snapshots materializados y nunca consulta GEE desde el navegador. La auditoría local de generación y descarga sólo se registra si ya existe adapter aprobado. Compartir, programación, mutación de plantillas y distribución permanecen como `pending_contract` sin endpoints públicos.
- **edge_cases:** La spec debe cubrir lista vacía preservando contexto y acción de generación, filtros sin resultados con acción para limpiar filtros, reportes en curso con progreso indeterminado y descarga bloqueada, IDs/timestamps ausentes con degradación explícita sin fallback inventado, duplicados deduplicados por ID backend, expirados conservados en historial pero no descargables, y orden/selección deterministas.
- **ui_states:** La tesis visual queda definida como workspace editorial-operativo table-first, con cabecera y filtros compactos, banda de estado, cola dominante, preview central paginado e inspector lateral sticky. Deben ser visibles los estados loading, empty, filtered-empty, generating, ready, failed, expired, disabled y `pending_contract`. El preview es HTML fiel hasta que exista PDF generado y sólo entonces se etiqueta como PDF. Low-bandwidth conserva filtros, cola, detalle, metadatos y descargas sin decoración pesada.

## Decisiones de la entrevista

- **adv-b698fcb628:** ### [adv-9dd7ebad25] No queda definido qué campos de timestamp son “equivalentes” a `created_at`/`updated_at`, ni cuál tiene prioridad si hay varios; dos implementaciones podrían elegir `generated_at`, `timestamp`, `run_started_at` u otro campo y ambas parecer razonables.

**R:**
- **adv-235e13651e:** ### [adv-e2f7c01630] No queda definido el contrato de auditoría para descargas y compartidos: event types, entity type/id, campos mínimos, actor, timestamp, snapshot/report id, y si exportaciones locales/demo/simuladas deben registrar auditoría o quedar pendientes.

**R:**
- **adv-bb24255702:** ## Decisiones registradas
- **data_model:** La API es propietaria de identidad y tiempos. Cada reporte expone `id`, `generated_at`, `updated_at`, `expires_at` opcional, `status` (`queued`, `generating`, `ready`, `failed`, `expired`), `region_id`, `period_start`, `period_end`, `template_id`, `language`, `author`, `snapshot_id`, formatos disponibles y error saneado opcional. IDs y timestamps son estables, UTC ISO-8601; el navegador no los inventa. Exportaciones recientes y eventos de auditoría usan IDs propios y referencia al reporte.
- **error_states:** Carga fallida, endpoint pendiente, permiso denegado, generación/descarga fallida y auditoría no disponible se muestran por separado con mensajes saneados y reintento sólo cuando sea seguro. Un formato fallido no invalida los demás ni descarga archivos vacíos. `pending_contract` y funciones no autorizadas permanecen explícitamente deshabilitadas.
- **edge_cases:** Sin reportes se conserva el contexto y una acción de generación; filtros sin resultados ofrecen limpiar filtros. Un reporte en curso muestra progreso indeterminado y no permite descargar. IDs o timestamps ausentes degradan la fila explícitamente sin fallback inventado. Duplicados se deduplican por ID backend; expirados se conservan en historial pero no descargan. Orden y selección son deterministas.
- **auth_secrets:** `/reports` es público y de sólo lectura. Generar y descargar PDF/CSV/JSON usa exclusivamente datos ya materializados y no requiere secretos del navegador. Programación, gestión de plantillas, compartir y distribución quedan deshabilitados hasta disponer de autenticación, roles y permisos aprobados; no se simula persistencia ni envío real y no se exponen destinatarios o secretos.
- **external_contracts:** Se aprueban endpoints aditivos para listar reportes, detalle, generación y descarga de PDF/CSV/JSON, todos bajo `/api/v1/reports`. La generación usa snapshots materializados y nunca consulta GEE desde el navegador. Se permite registrar auditoría local de generación y descarga si ya existe adapter aprobado. Compartir, programación, mutación de plantillas y distribución permanecen `pending_contract` sin endpoints públicos.
- **ui_states:** Tesis visual: workspace editorial-operativo table-first, con cabecera y filtros compactos, banda de estado, cola dominante, preview central paginado e inspector lateral sticky. Loading, empty, filtered-empty, generating, ready, failed, expired, disabled y `pending_contract` son visibles. El preview es HTML fiel hasta que exista PDF generado y sólo entonces se etiqueta PDF. Low-bandwidth conserva filtros, cola, detalle, metadatos y descargas sin decoración pesada.
- **rollback_compat:** La experiencia es aditiva y preserva `/reports`, deep-links existentes, contratos de exports y reportes previos, demo determinista y funcionamiento offline. Payloads antiguos pueden mostrarse con degradación explícita, pero nunca se inventan IDs/timestamps. Si el historial no está disponible, generación y descargas actuales siguen operativas. No se añade feature flag; el rollback es revertir el commit del sprint.
- **tests:** Tests bloqueantes cubren contratos y estabilidad de IDs/timestamps, estados de lifecycle, filtros combinados, orden/selección, generación y descarga real de PDF/CSV/JSON, archivos no vacíos y cabeceras seguras, preview HTML/PDF correctamente etiquetado, deep-links, low-bandwidth, errores independientes, funciones `pending_contract`, auditoría permitida, ausencia de GEE y envíos reales desde navegador, demo offline y documentación de implementado/pendiente/futuro.

