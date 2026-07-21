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
- Consultar ADM1 sólo en la ventana actual. La cobertura por defecto incluye todas las unidades ADM1 de todos los países IGAD habilitados; `MWANGAZA_GEE_ADM1_COUNTRIES` puede restringir explícitamente el lote.
- Resolver el color del mapa por `boundary_iso`. No se permite propagar el score nacional ni usar coincidencia aproximada de nombre.
- Convertir el bloque principal en un workspace mapa-inspector. `selectedPilotId` sigue siendo el identificador compartido para selector, mapa y ranking, sin llamadas de red.
- Mover el detalle de la unidad activa al inspector lateral y convertir el ranking completo en una superficie plegable bajo el mapa. En móvil el inspector fluye debajo del mapa; low-bandwidth conserva controles y tabla.
- Sustituir sparklines de barras por SVG accesible de anomalía (`value - baseline`) con eje cero, escala y fechas; representar pesos del composite en una barra apilada con paleta neutral, no de severidad.
- Reforzar la lectura transversal del estado con badges coherentes, destacar el top tres del ranking, agrupar el histórico por año y conservar una sola acción principal. La metodología pendiente no se presenta como enlace o CTA.
- Materializar 24 ventanas mensuales nacionales en un único grafo/request GEE con `reduceRegions`, sin extender la serie a ADM1. El shell calcula un baseline de media de serie solo cuando la fuente no lo publica y expone su etiqueta en el contrato aditivo.
- Convertir `contributions` en una explicación del cálculo: `weighted_contribution = signal_score × effective_weight`, participación sobre el score y procedencia/calidad. Extender `administrative_units` de forma aditiva con su propio desglose y no hacer fallback nacional para una unidad seleccionada.
- Separar lectura y actualización live mediante stale-while-revalidate: responder desde el último materializado válido, ejecutar como máximo un refresh GEE en segundo plano y persistirlo de forma atómica. Aislar tendencias y ADM1 como módulos opcionales para conservar el payload nacional, y hacer que la PWA consulte de nuevo hasta promocionar `cache` a `live`.

## Decisiones de la entrevista

- **data_model:** La API expone unidades subnacionales ya procesadas tanto en demo como en live GEE, con `id`, `name`, `admin_level`, `score`, `level`, `quality`, `period`, `ui_geometry`, métricas, contribuciones del composite, tendencias y comparaciones. Los valores ausentes permanecen `null`; no se completan desde fixtures salvo en modo demo explícito.
- **error_states:** En local/cache, si faltan geometría, ranking, contribuciones, comparación o tendencias, cada módulo muestra un estado pendiente específico y conserva tabla/resumen accesible. En producción live, una respuesta incompleta se identifica como degradada o fallida y nunca se rellena con fixtures. Nunca se dibuja geometría sintética ni se convierte ausencia de datos en riesgo bajo.
- **edge_cases:** El ranking ordena score numérico descendente, después nombre estable; `null`/`unknown` siempre al final. Las comparaciones usan únicamente el snapshot estacional comparable anterior; si no existe, muestran `No comparison yet`. La selección se conserva solo mientras siga disponible.
- **auth_secrets:** No se añade autenticación ni secretos al navegador. `MWANGAZA_MODE=demo` usa exclusivamente payloads locales. En live, el backend ejecuta y materializa consultas GEE acotadas; el navegador consume la API y ninguna interacción inicia Earth Engine directamente. Cuenta y notificaciones permanecen como placeholders explícitos y no interactivos.
- **external_contracts:** `View all alerts` navega a `/alerts?region=<id>&period=<period>&status=active`. La API pública amplía el snapshot existente sin romper campos actuales. Geometrías admitidas: GeoJSON `Polygon` y `MultiPolygon`. El pipeline live GEE debe producir el mismo contrato funcional que demo para las regiones habilitadas, incluyendo unidades, métricas, contribuciones, series y comparaciones.
- **ui_states:** Vista normal live y demo: mapa, controles de país/subregión/periodo/vista, resumen, alerta, métricas, contribuciones, ranking, tendencias, comparación y acciones funcionales. Low-bandwidth: equivalente completo en tabla/texto sin SVG ni animaciones. Demo: banner persistente con `is_demo`, `reference_date` y `snapshot_id`. Live/cache: procedencia y frescura reales, sin mezclar fixtures.
- **rollback_compat:** Se preservan rutas y contratos existentes; los campos API nuevos son aditivos. Los placeholders actuales siguen siendo fallback recuperable cuando el backend no cubra una región.
- **tests:** Bloquean pruebas API y frontend para geometría real, demo sin red/GEE, live GEE con adaptador determinista y smoke real versionado, ranking determinista, unknown al final, contribuciones, comparación disponible/ausente, tendencias, deep-link con filtros, todos los controles, low-bandwidth sin mapa, producción sin fallback demo y degradación accesible por payload incompleto.
