# sprint-56-region-explorer-completion · undefined — Diseño

## Scope (archivos que puede tocar)

- `frontend/**`
- `tests/frontend/**`
- `src/mwangaza/api/**`
- `tests/api/**`
- `src/mwangaza/services/live_gee_dashboard.py`
- `src/mwangaza/services/dashboard_shell.py`
- `src/mwangaza/regions/**`
- `src/mwangaza/data/**`
- `data/regions/**`
- `tests/regions/**`
- `tests/data/**`
- `tests/services/**`
- `smoke_tests/**`
- `docs/region-interface.md`
- `docs/contracts.md`
- `spec/sprint-56-region-explorer-completion-*/**`
- `progress/**`

## Enfoque

- **data_model:** Contrato subnacional completo y equivalente para demo y live GEE, con valores ausentes explícitos.
- **external_contracts:** Deep-link, geometrías y salida completa del pipeline live GEE definidos.
- **edge_cases:** Orden, comparación y selección deterministas.
- **ui_states:** Panel funcional completo en live y demo, low-bandwidth y payload incompleto.

## Ampliación ADM1 aprobada

- Incorporar las fronteras ADM1 versionadas al catálogo geográfico como regiones consultables por GEE, conservando `shapeID` y `shapeISO` de geoBoundaries.
- Añadir `AdministrativeUnit` a `RegionProfile` y serializarlo como `administrative_units` sin romper consumidores v1.
- Consultar ADM1 sólo en la ventana actual. La cobertura por defecto es Somalia completa y Turkana, Marsabit e Isiolo; se amplía mediante configuración.
- Resolver el color del mapa por `boundary_iso`. No se permite propagar el score nacional ni usar coincidencia aproximada de nombre.

## Decisiones de la entrevista

- **data_model:** La API expone unidades subnacionales ya procesadas tanto en demo como en live GEE, con `id`, `name`, `admin_level`, `score`, `level`, `quality`, `period`, `ui_geometry`, métricas, contribuciones del composite, tendencias y comparaciones. Los valores ausentes permanecen `null`; no se completan desde fixtures salvo en modo demo explícito.
- **error_states:** En local/cache, si faltan geometría, ranking, contribuciones, comparación o tendencias, cada módulo muestra un estado pendiente específico y conserva tabla/resumen accesible. En producción live, una respuesta incompleta se identifica como degradada o fallida y nunca se rellena con fixtures. Nunca se dibuja geometría sintética ni se convierte ausencia de datos en riesgo bajo.
- **edge_cases:** El ranking ordena score numérico descendente, después nombre estable; `null`/`unknown` siempre al final. Las comparaciones usan únicamente el snapshot estacional comparable anterior; si no existe, muestran `No comparison yet`. La selección se conserva solo mientras siga disponible.
- **auth_secrets:** No se añade autenticación ni secretos al navegador. `MWANGAZA_MODE=demo` usa exclusivamente payloads locales. En live, el backend ejecuta y materializa consultas GEE acotadas; el navegador consume la API y ninguna interacción inicia Earth Engine directamente. Cuenta y notificaciones permanecen como placeholders explícitos y no interactivos.
- **external_contracts:** `View all alerts` navega a `/alerts?region=<id>&period=<period>&status=active`. La API pública amplía el snapshot existente sin romper campos actuales. Geometrías admitidas: GeoJSON `Polygon` y `MultiPolygon`. El pipeline live GEE debe producir el mismo contrato funcional que demo para las regiones habilitadas, incluyendo unidades, métricas, contribuciones, series y comparaciones.
- **ui_states:** Vista normal live y demo: mapa, controles de país/subregión/periodo/vista, resumen, alerta, métricas, contribuciones, ranking, tendencias, comparación y acciones funcionales. Low-bandwidth: equivalente completo en tabla/texto sin SVG ni animaciones. Demo: banner persistente con `is_demo`, `reference_date` y `snapshot_id`. Live/cache: procedencia y frescura reales, sin mezclar fixtures.
- **rollback_compat:** Se preservan rutas y contratos existentes; los campos API nuevos son aditivos. Los placeholders actuales siguen siendo fallback recuperable cuando el backend no cubra una región.
- **tests:** Bloquean pruebas API y frontend para geometría real, demo sin red/GEE, live GEE con adaptador determinista y smoke real versionado, ranking determinista, unknown al final, contribuciones, comparación disponible/ausente, tendencias, deep-link con filtros, todos los controles, low-bandwidth sin mapa, producción sin fallback demo y degradación accesible por payload incompleto.
