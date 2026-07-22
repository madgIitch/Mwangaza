# sprint-59-reports-center-completion · undefined — Requisitos

- name: `Sprint 59 - Reports Center Completion` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-22T18:11:09.327Z

## Contexto



## Requisitos funcionales

R1. R1: `/reports` presenta filtros por texto, region, tipo, periodo y estado; tabs Generated, Scheduled, Templates y All; banda de resumen, cola table-first, detalle, exportaciones recientes, preview e inspector, con loading, empty, filtered-empty, error y disabled explicitos.
R2. R2: `GET /api/v1/reports` devuelve `items`, `summary`, `limit`, `offset` y `total`; aplica filtros y orden determinista. Cada item incluye `id`, `generated_at`, `updated_at`, `expires_at`, `status`, `region_id`, periodo, `template_id`, `language`, `author`, `snapshot_id`, formatos disponibles y error saneado opcional.
R3. R3: Los estados permitidos son `queued`, `generating`, `ready`, `failed` y `expired`; los timestamps son UTC ISO-8601 y la prioridad observable es `generated_at`, luego `updated_at`. Si falta ID o `generated_at`, la fila se etiqueta `Incomplete record`, queda seleccionable para diagnostico y bloquea descargas sin inventar valores.
R4. R4: `GET /api/v1/reports/<id>` devuelve detalle y eventos; un ID inexistente devuelve 404 saneado. `POST /api/v1/reports` genera desde un snapshot materializado con region, periodo, template e idioma validados y nunca inicia GEE desde el navegador.
R5. R5: `GET /api/v1/reports/<id>/download?format=pdf|csv|json` devuelve contenido real no vacio, tipo y filename seguros solo para reportes `ready`; `queued`/`generating` devuelve 409, `failed` 422 y `expired` 410. Un formato fallido no invalida los demas.
R6. R6: El preview HTML reproduce el contenido aprobado del reporte y se etiqueta HTML; solo un artefacto PDF generado se etiqueta PDF. Seleccion, filtros, paginacion y deep-links conservan contexto de forma determinista y low-bandwidth mantiene evidencia y descargas.
R7. R7: Generacion y descarga registran eventos append-only `report_generated` y `report_downloaded` mediante `AuditRepository`, con actor `public-dashboard`, entity_type `report`, report ID, region, timestamp, snapshot ID y metadata saneada. Las lecturas no auditan y los fallos de auditoria degradan explicitamente sin invalidar una descarga ya generada.
R8. R8: Programacion, gestion de plantillas, compartir y distribucion permanecen deshabilitados como `pending_contract`; no existen endpoints publicos para esas mutaciones, no se simula persistencia ni envio y no se exponen secretos o destinatarios.
R9. R9: Demo es determinista y offline; live/cache usan solo snapshots materializados. Payloads anteriores degradan como `Incomplete record`; si falla el historial, la generacion y descarga actual siguen operativas. Se preservan `/reports`, rutas previas y contratos existentes de reportes/exportaciones.
R10. R10: Tests de API, reportes, auditoria y frontend cubren IDs/timestamps, lifecycle, filtros/paginacion, 404/409/410/422, PDF/CSV/JSON no vacios, preview, deep-links, low-bandwidth, pending_contract, demo offline, ausencia de GEE/envios reales y documentacion de implementado, pendiente y futuro.

## Restricciones

- **error_states:** La spec debe cubrir estados separados para carga fallida, endpoint pendiente, permiso denegado, generación fallida, descarga fallida y auditoría no disponible. Los mensajes deben estar saneados. El reintento sólo aparece cuando sea seguro. Un formato fallido no invalida los demás ni permite descargar archivos vacíos. `pending_contract` y funciones no autorizadas permanecen explícitamente deshabilitadas.
- **auth_secrets:** `/reports` es público y de sólo lectura. Generar y descargar PDF/CSV/JSON usa exclusivamente datos ya materializados y no requiere secretos del navegador. Programación, gestión de plantillas, compartir y distribución quedan deshabilitados hasta disponer de autenticación, roles y permisos aprobados. No se simula persistencia ni envío real y no se exponen destinatarios o secretos.
- **rollback_compat:** La experiencia es aditiva y preserva `/reports`, deep-links existentes, contratos de exports y reportes previos, demo determinista y funcionamiento offline. Payloads antiguos pueden mostrarse con degradación explícita, pero nunca se inventan IDs/timestamps. Si el historial no está disponible, generación y descargas actuales siguen operativas. No se añade feature flag; el rollback es revertir el commit del sprint.

