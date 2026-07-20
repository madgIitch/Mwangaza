# sprint-46-northern-kenya-end-to-end-scenario · undefined — Diseño

## Scope (archivos que puede tocar)

- `scripts/demo_kenya.py`
- `.demo/**`
- `docs/region-interface.md`
- `docs/reports-interface.md`
- `docs/notification-simulator.md`
- `docs/i18n.md`
- `docs/README.md`
- `spec/sprint-46-northern-kenya-end-to-end-scenario-*/**`
- `src/**/demo/**`
- `src/**/region*/**`
- `src/**/reports*/**`
- `src/**/notifications/**`
- `frontend/src/routes/region/**`
- `frontend/src/routes/reports/**`
- `frontend/src/components/**`
- `frontend/src/App.tsx`
- `frontend/src/types.ts`
- `frontend/src/styles.css`
- `tests/frontend/app.test.tsx`
- `tests/e2e/test_kenya_scenario.py`
- `tests/fixtures/scenarios/kenya/**`
- `tests/demo/**`
- `tests/ui/**`
- `tests/notifications/**`
- `tests/reports/**`

## Enfoque

- **data_model:** El escenario usa exactamente tres unidades subnacionales estables: Turkana (`KEN-023`), Marsabit (`KEN-010`) e Isiolo (`KEN-011`), todas enlazadas al `snapshot_id` común `northern-kenya-2026-03-demo-v1`. Turkana es la unidad destacada por mayor severidad. Cada unidad expone `unit_id`, nombre, severidad, score e indicadores, y mapa, detalle, reporte, alerta y notificación deben referenciar conjuntamente `snapshot_id` y `unit_id`. El estado demo idempotente se persiste por esos identificadores.
- **external_contracts:** La entrada principal verificable es `python scripts/demo_kenya.py`, con fixture local versionado y estado por defecto en `.demo/kenya-state.json`. El JSON de salida debe incluir como mínimo `status`, `mode`, `offline`, `snapshot_id`, `units`, `selected_unit`, `highlighted_unit`, `detail`, `report`, `alert`, `notification`, `requested_language`, `effective_language` y `warnings`. No debe realizar llamadas de red ni depender de credenciales.
- **edge_cases:** La unidad de mayor severidad se resuelve determinísticamente por severidad, luego por score descendente y finalmente por `unit_id` ascendente. Una unidad con datos parciales sigue siendo seleccionable y muestra `unknown` en campos ausentes. Una unidad sin geometría debe seguir funcionando vía tabla accesible. La ausencia de reporte obligatorio bloquea la finalización del escenario.
- **ui_states:** La vista debe mostrar de forma visible el nombre y `unit_id` activos, badge de severidad, score e indicadores justificativos. El mapa o la tabla accesible permiten cambiar la selección sin recarga remota. El reporte debe reflejar el mismo `unit_id` de la unidad activa. La vista previa de notificación debe exponer idioma solicitado y efectivo, incluyendo fallback.

## Decisiones de la entrevista

- **adv-a648517df4:** ### [adv-2c79eb70d7] AC6 exige ejecutar "el recorrido completo" con datos demo, pero no define el entrypoint canónico ni qué pasos mínimos lo componen para considerar el flujo completo. Dos implementaciones razonables podrían validar cosas distintas (solo script CLI, solo PWA, o script + UI + reporte + notificación) y dar PASS/FAIL diferente.

**R:**
- **adv-6bc508d351:** ### [adv-b159cf1953] AC5 exige usar el idioma seleccionado cuando existe plantilla para `en`/`sw`/`so`, pero no define a nivel de escenario si Northern Kenya debe disponer de plantillas para los tres idiomas o si alguna ausencia es aceptable por diseño. Sin esa decisión de negocio, no se puede decidir PASS/FAIL ante un resultado con fallback explícito en uno o más idiomas.

**R:**
- **data_model:** Usar Turkana (`KEN-023`), Marsabit (`KEN-010`) e Isiolo (`KEN-011`) como unidades estables, todas enlazadas al `snapshot_id` `northern-kenya-2026-03-demo-v1`. Turkana es la unidad de mayor severidad. Cada unidad contiene `unit_id`, nombre, severidad, score e indicadores; mapa, detalle, reporte, alerta y notificación referencian tanto `snapshot_id` como `unit_id`. El estado demo se persiste de forma idempotente por esos identificadores.
- **error_states:** Un fixture ausente, corrupto o sin detalle/reporte obligatorio termina con código distinto de cero, mensaje accionable y sin publicar estado completo. Una unidad sin geometría conserva selección mediante tabla accesible y muestra placeholder. Si falta la plantilla del idioma elegido, se usa inglés y se emite un warning estructurado con el idioma solicitado y el efectivo.
- **edge_cases:** La mayor severidad se decide primero por nivel de severidad, después por score descendente y finalmente por `unit_id` ascendente. Una unidad con datos parciales sigue siendo seleccionable y muestra `unknown` en los campos ausentes; sin geometría usa tabla accesible, pero la ausencia de reporte obligatorio impide completar el escenario.
- **external_contracts:** La entrada principal es `python scripts/demo_kenya.py`, con fixture local versionado y estado por defecto `.demo/kenya-state.json`. El JSON de salida incluye `status`, `mode`, `offline`, `snapshot_id`, unidades, unidad seleccionada/destacada, detalle, reporte, alerta, notificación, idioma solicitado/efectivo y warnings. No realiza red ni requiere credenciales.
- **ui_states:** La vista muestra el nombre y `unit_id` activos, badge de severidad, score e indicadores justificativos. El mapa o tabla accesible permite cambiar la selección. El reporte muestra el mismo `unit_id`, y la vista previa de notificación indica idioma solicitado y efectivo, incluido el fallback.
- **rollback_compat:** El Sprint 46 es estrictamente aditivo. Debe preservar el escenario Somalia y los contratos actuales de `/region`, `/reports` y notificaciones. Los campos específicos del escenario Kenya se añaden como opcionales o dentro del fixture/estado demo, sin convertirlos en requisitos de contratos existentes.
- **tests:** Deben pasar un E2E offline del script, prueba de selección desde mapa y tabla accesible, correspondencia entre unidad activa y reporte, notificación en `en`, `sw` y `so` con fallback a inglés, empate determinista, errores de fixture y reporte, ausencia de red/credenciales e idempotencia sin duplicar alertas ni notificaciones.
