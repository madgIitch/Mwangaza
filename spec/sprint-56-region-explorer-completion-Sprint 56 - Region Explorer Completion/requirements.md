# sprint-56-region-explorer-completion · undefined — Requisitos

- name: `Sprint 56 - Region Explorer Completion` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-20T20:51:57.088Z

## Contexto



## Requisitos funcionales

R1. `/region` muestra un mapa subnacional basado únicamente en geometrías API procesadas y una tabla accesible equivalente; si falta geometría muestra `Map geometry pending` y no dibuja formas sintéticas.
R2. El ranking usa unidades del payload, ordena score descendente con desempate estable y coloca `null`/`unknown` al final.
R3. `Why this region is at risk` consume contribuciones explícitas del payload; si faltan muestra un estado pendiente y no presenta pesos estimados como reales.
R4. Las tarjetas muestran comparación únicamente contra un snapshot estacional comparable anterior; sin él muestran `No comparison yet`.
R5. `View all alerts` abre `/alerts` con `region`, `period` y `status=active` codificados en la query.
R6. Low-bandwidth conserva selección, resumen, alertas, métricas, ranking y acciones en tablas/texto, sin renderizar el mapa SVG ni animaciones.
R7. Con `MWANGAZA_MODE=demo`, la API y `/region` funcionan sin red ni Earth Engine, usan solo payloads demo locales y mantienen visibles `is_demo`, `reference_date` y `snapshot_id`.
R8. Con la API en live y credenciales GEE válidas, `/region` ofrece el panel completo: mapa, país/subregión/periodo/vista, resumen, alerta, métricas, contribuciones, ranking, tendencias, comparación histórica y acciones, usando el contrato producido por GEE/cache.
R9. En live/cache no se mezclan fixtures demo. Producción nunca cae silenciosamente a demo; una región o módulo incompleto se marca degradado/fallido con procedencia explícita.
R10. Las interacciones de país, subregión, periodo y vista actualizan datos ya cargados y no disparan consultas Earth Engine desde el navegador.
R11. Existe un smoke versionado contra GEE real que comprueba al menos una región habilitada y verifica que el payload live alimenta todos los módulos del panel sin datos demo.
R12. Cuenta y notificaciones permanecen como placeholders explícitos no interactivos hasta que sus contratos sean aprobados.
R13. El perfil regional publica `administrative_units` aditivo con identificadores geoBoundaries, periodo, score, nivel, calidad, procedencia y métricas GEE por unidad.
R14. El procesamiento ADM1 live se limita al periodo actual, cubre por defecto todas las unidades de todos los países IGAD habilitados y admite restricción explícita por configuración; tendencias e históricos permanecen agregados para controlar coste y latencia.
R15. El mapa enlaza por `boundary_iso` y sólo colorea unidades con score propio y calidad concluyente; ausencias y fallos permanecen grises.
R16. Mapa, selector ADM1 y ranking comparten una selección activa; el inspector lateral muestra score, indicadores, calidad, periodo y acción contextual usando datos ya cargados.
R17. El ranking ADM1 es plegable, conserva semántica de tabla y no determina la altura del workspace principal. Low-bandwidth mantiene selección y detalle equivalentes sin renderizar SVG.
R18. Las tendencias muestran la diferencia contra baseline con eje cero, escala, fechas y tooltip accesible; las contribuciones se presentan como una única barra apilada de pesos sin semántica de severidad; ranking e histórico usan badges, top tres y deltas agrupados por año.
R19. Live GEE materializa 24 agregados mensuales nacionales por defecto, configurables entre 12 y 24, en una consulta batch; el trend usa baseline explícito o la media de la serie etiquetada y conserva gaps reales. La UI abrevia fechas y no inicia consultas GEE.
R20. El composite publica por indicador score normalizado, peso efectivo, contribución ponderada, participación, calidad y fuente. El panel explica la suma en puntos y, con ADM1 activo, usa exclusivamente el desglose de esa unidad o muestra pendiente.
R21. En modo live, la API aplica stale-while-revalidate: sirve inmediatamente el último snapshot materializado utilizable, limita el refresh GEE a un único proceso en segundo plano, persiste atómicamente el último lote válido y no bloquea `/alerts` ni `/forecasts`. La PWA reintenta mientras recibe `cache` y promociona a `live` sin recarga; un fallo opcional de tendencias o ADM1 no invalida el payload nacional.

## Restricciones

- **error_states:** Fallback por módulo sin datos fabricados.
- **auth_secrets:** Sin secretos ni GEE desde el navegador; demo local.
- **rollback_compat:** Rutas y contratos previos preservados.
