# sprint-58-alerts-center-completion · undefined — Diseño

## Scope (archivos que puede tocar)

- `frontend/**`
- `tests/frontend/**`
- `src/mwangaza/api/**`
- `tests/api/**`
- `src/mwangaza/contracts/**`
- `tests/contracts/**`
- `src/mwangaza/alerts/**`
- `tests/alerts/**`
- `src/mwangaza/actions/**`
- `tests/actions/**`
- `src/mwangaza/notifications/**`
- `tests/notifications/**`
- `src/mwangaza/audit/**`
- `tests/audit/**`
- `src/mwangaza/services/dashboard_shell.py`
- `tests/ui/test_dashboard_shell.py`
- `src/mwangaza/exports/**`
- `tests/exports/**`
- `src/mwangaza/reports/**`
- `tests/reports/**`
- `docs/alerts-interface.md`
- `docs/contracts.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS.md`
- `spec/sprint-58-alerts-center-completion-*/**`
- `progress/**`

## Enfoque

- **data_model:** identidad backend y lifecycle append-only.
- **external_contracts:** listado, detalle y export filtrados.
- **edge_cases:** orden, filtros, selección y paginación deterministas.
- **ui_states:** workspace table-first con inspector operativo.

## Decisiones de la entrevista

- **data_model:** La API debe ser la propietaria de la identidad y del ciclo de vida. Cada alerta expone `id` público estable, `issued_at`, `updated_at`, `resolved_at` opcional, `status`, `previous_status`, evidencia estructurada, recomendaciones tipadas y eventos append-only. Los estados admitidos son `preventive`, `active`, `monitoring`, `resolved` y `superseded`; los datos ausentes permanecen `null` y nunca se deducen en el navegador. La migración SQLite es aditiva y conserva alertas existentes.
- **external_contracts:** `GET /api/v1/alerts` aplica realmente `q`, `region`, `severity`, `status`, `period`, `limit` y `offset`, y devuelve `items`, `summary`, `limit`, `offset` y `total`. `GET /api/v1/alerts/<id>` devuelve alerta, eventos, recomendaciones y outbox simulado. Los mismos filtros alimentan `/api/v1/exports/alerts?format=csv|json` y `/api/v1/reports/alerts` para PDF. Los deep-links de Overview y Region se preservan. No se añaden mutaciones de resolución ni settings hasta disponer de autenticación y permisos aprobados.
- **auth_secrets:** Alerts Center continúa siendo de lectura operativa. `Alert settings` permanece deshabilitado y explica la dependencia de permisos. El outbox es siempre `is_simulated=true`, usa destinatarios enmascarados, no incluye secretos y no ofrece ninguna ruta de envío real. Las lecturas no generan eventos de auditoría ni modifican estado.
- **error_states:** Un ID inexistente devuelve 404 saneado. Filtros inválidos devuelven 400 sin trazas internas. Si el repositorio histórico no está disponible, las alertas observadas del snapshot siguen operativas y las secciones de resolved/lifecycle/outbox muestran degradación explícita. Export y PDF fallan de forma independiente y nunca descargan archivos vacíos. Demo/cache/live conservan procedencia visible.
- **edge_cases:** El orden es determinista por estado operativo, severidad, score, `issued_at` e ID. Cambiar filtros conserva la selección si sigue visible y selecciona la primera fila si desaparece. La paginación se aplica después de todos los filtros. `resolved_at` sólo existe en alertas resueltas; `superseded` enlaza la alerta reemplazante cuando exista. Un filtro sin resultados conserva el contexto y ofrece limpiar filtros.
- **ui_states:** Tesis visual: consola operativa sobria, densa y table-first, con verde oscuro para acciones y ámbar/rojo reservados a estado. Cabecera y filtros forman una franja compacta; la cola es el workspace dominante y un inspector lateral sticky reúne evidencia, acción, lifecycle y comunicaciones. Los totales se integran como una banda de estado, no como un mosaico de tarjetas. Selección de fila, filtros y cambio de inspector usan transiciones breves y respetan `prefers-reduced-motion`. Low-bandwidth mantiene filtros, tabla, detalle, eventos y exportaciones sin paneles decorativos.
- **rollback_compat:** Se preservan `/alerts`, `/alerts/<id>` y los campos actuales del contrato. Los nuevos campos y rutas son aditivos; los IDs fallback sólo se aceptan en fixtures antiguos y nunca sustituyen un ID del backend. Demo sigue siendo determinista y offline. Reports Center completo, autenticación, settings y cualquier envío real permanecen fuera de Sprint 58.
- **tests:** Tests bloqueantes cubren migración y estabilidad de IDs, todos los estados y eventos, filtros combinados/paginación, 404/400, outbox enmascarado y estrictamente simulado, CSV/JSON/PDF filtrados, deep-links, selección, URL persistente, responsive/low-bandwidth y ausencia de consultas GEE o envíos reales desde el navegador.

