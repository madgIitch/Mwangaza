# sprint-47-offline-demo-fallback · undefined — Diseño

## Scope (archivos que puede tocar)

- `demo_data/**`
- `.demo/**`
- `scripts/reset_demo.py`
- `scripts/demo_somalia.py`
- `scripts/demo_kenya.py`
- `src/**/config/**`
- `src/**/demo/**`
- `src/**/api/**`
- `src/**/services/**`
- `src/**/alerts/**`
- `src/**/reports/**`
- `src/**/ui/**`
- `frontend/src/**`
- `frontend/public/**`
- `tests/demo/**`
- `tests/**/api/**`
- `tests/**/ui/**`
- `tests/**/reports/**`
- `docs/configuration.md`
- `docs/contracts.md`
- `docs/dashboard-shell.md`
- `docs/reports-interface.md`
- `docs/DECISIONS.md`

## Enfoque

- **data_model:** `is_demo=true` queda como marca canónica aditiva para todos los datos derivados de fixtures demo: overview, region, alerts, reports, forecast diagnostics, exports, configuración y outbox. `is_simulated=true` se conserva solo donde ya exista: `is_demo` describe el origen del dato y `is_simulated` que no hubo entrega o acción real. Todo dato demo debe exponer además `reference_date` o `snapshot_id`.
- **external_contracts:** La activación contractual única del modo es `MWANGAZA_MODE=demo`. `scripts/reset_demo.py` es el reset oficial. Los payloads API en demo añaden `is_demo`, `reference_date` o `snapshot_id`, y `data_mode=demo`. Deben funcionar offline Overview, Regions, Alerts, Reports, About, Admin y Technical, además de `scripts/demo_somalia.py`, `scripts/demo_kenya.py` y previews/exports locales.
- **edge_cases:** El modo demo valida su baseline al arrancar. Si detecta estado corrupto, parcial o mezclado con registros no demo, bloquea el recorrido con mensaje accionable hasta ejecutar `scripts/reset_demo.py`; no hay sobrescritura automática. El reset elimina únicamente el estado demo gestionado y restaura el baseline de forma idempotente. Esto también cubre reinstalaciones/refrescos offline: el baseline debe validarse antes de servir datos demo.
- **ui_states:** El banner demo debe mostrar siempre como mínimo “Demo data”, origen offline, `reference_date`, `snapshot_id` y referencia al comando oficial de reset. Debe permanecer visible en Overview, Regions, Alerts, Reports, About, Admin y Technical, incluidos estados de error y durante la navegación interna.

## Decisiones de la entrevista

- **adv-250d48ce40:** ### [adv-925928aaf1] AC1 habla de "entrypoints públicos aprobados" y de "estado/metadata de modo demo verificable", pero no fija de forma cerrada qué superficies entran exactamente en ese conjunto ni qué metadata mínima debe exponer cada una. Dos implementaciones razonables podrían cubrir conjuntos distintos (por ejemplo incluir o no `/health`, `/openapi.json`, el shim `app.py` o solo la PWA) y dar veredictos diferentes.

**R:**
- **adv-509d045c52:** ### [adv-27516180c8] AC2 y AC3 dejan indeterminado qué debe mostrarse cuando un artefacto demo no tiene ambos campos. AC2 permite `reference_date` o `snapshot_id`, mientras AC3 exige que el banner muestre "la fecha de referencia". Sin decidir si `snapshot_id` sustituye a la fecha en UI o si toda superficie debe exponer además una `reference_date` real, dos implementaciones razonables darían resultados distintos.

**R:**
- **adv-32e9c16fc4:** ### [adv-5d51e41d24] AC5 usa "recorridos demo aprobados" y "mismo comportamiento observable esencial" para Somalia, Northern Kenya y Reports/export/preview offline, pero no define el recorrido canónico ni qué aspectos son esenciales y cuáles pueden degradarse. Ya existen superficies con placeholders/simulaciones y varias interpretaciones razonables del flujo completo producirían PASS/FAIL distintos.

**R:**
- **adv-8315b26f3f:** ## Decisiones registradas
- **data_model:** `is_demo=true` es la marca canónica aditiva para overview, region, alerts, reports, forecast diagnostics, exports, configuración y outbox derivados de fixtures. Se conserva `is_simulated=true` donde ya exista; `is_demo` describe el origen y `is_simulated` que no hubo entrega/acción real. Todo dato demo incluye `reference_date` o `snapshot_id`.
- **error_states:** En `production`, credenciales ausentes o GEE no disponible nunca activan demo. Se permite degradación explícita a caché válida con `data_mode=cache`, warning visible y estado readiness degradado; sin caché válida, el endpoint afectado falla con error estructurado y la UI muestra indisponibilidad, sin inventar datos.
- **edge_cases:** El modo demo valida su baseline al arrancar. Estado corrupto, parcial o mezclado con registros no demo bloquea el recorrido con mensaje accionable hasta ejecutar `scripts/reset_demo.py`; no hay sobrescritura automática. El reset elimina únicamente el estado demo gestionado y restaura el baseline de forma idempotente.
- **external_contracts:** La activación contractual única es `MWANGAZA_MODE=demo`. `scripts/reset_demo.py` es el reset oficial. Los payloads API añaden `is_demo`, `reference_date`/`snapshot_id` y `data_mode=demo`. Deben funcionar offline Overview, Regions, Alerts, Reports, About, Admin y Technical, además de los scripts Somalia/Kenya y previews/exports locales.
- **ui_states:** El banner muestra siempre “Demo data”, origen offline, `reference_date`, `snapshot_id` y referencia al comando de reset. Debe permanecer visible en Overview, Regions, Alerts, Reports, About, Admin y Technical, incluidos estados de error y navegación interna.
- **rollback_compat:** Se preservan endpoints y shape base de `/region` y `/reports`, los `snapshot_id` de Somalia/Kenya y los IDs estables de alertas/outbox. Todos los cambios de payload son aditivos; el modo conectado y el modo cache existente mantienen su comportamiento.
- **tests:** Bloquean la aprobación: arranque demo sin secretos, prueba de ausencia de red e inicialización GEE, banner persistente en todas las rutas, reset idempotente y aislamiento de estado no demo, escenarios Somalia/Kenya offline, reports/export demo, compatibilidad de contratos y production sin credenciales verificando cache explícita o error, nunca demo.

