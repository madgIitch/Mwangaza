# sprint-48-data-provenance-documentation · undefined — Requisitos

- name: `Sprint 48 - Data Provenance Documentation` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-20T15:55:37.414Z

## Contexto



## Requisitos funcionales

R1. Existe un recurso canónico accesible desde la UI en una URL estable definida por el spec, enlazado visiblemente desde `/about` con texto explícito sobre metodología o procedencia de datos.
R2. La documentación enumera como mínimo cada fuente aprobada para esta release y, para cada una, muestra `source_name`, `variable_or_indicator`, `unit`, `spatial_or_temporal_resolution`, `update_frequency` y `license_or_terms`; si algún campo no aplica, se muestra un valor explícito como `Not available` o `Pending`, nunca silencio.
R3. La documentación define de forma separada y no ambigua los términos `observation`, `anomaly`, `score`, `forecast` y `exposure`, incluyendo una frase de uso y cómo se relacionan dentro del producto.
R4. Todos los umbrales de prototipo aparecen etiquetados explícitamente como configurables y no oficiales; no se presenta ningún threshold como estándar oficial de IGAD ni como warning público oficial.
R5. La documentación explica, con texto visible, cómo afectan `clouds or QA masking`, `coverage`, `latency` y `aggregation` a la interpretación de cada indicador o de la cadena metodológica.
R6. Incluye un diagrama o esquema visible que conecte, en ese orden lógico, `source`, `transformation`, `cache`, `API`, `UI` y `report`, usando esos conceptos o equivalentes inequívocos.
R7. La pantalla `/about` contiene un enlace navegable hacia esta documentación y los tests verifican tanto la presencia del enlace como la renderización de al menos un encabezado único de la documentación de procedencia.
R8. La documentación deja explícito que `exposure` significa población potencialmente expuesta y no población confirmada afectada, y que la fuente/año/resolución de exposición solo se muestran cuando existan datos disponibles para esta release.

## Restricciones

- **error_states:** Ningún metadato obligatorio puede omitirse en silencio. Si licencia, términos o metadatos no están confirmados, la documentación muestra explícitamente `Pending verification` y una advertencia visible de no redistribución; la fuente sigue listada, pero no puede presentarse como aprobada para uso operativo. Si un campo no aplica, se muestra un valor explícito como `Not available`.
- **auth_secrets:** La feature sigue siendo documental y no introduce manejo nuevo de credenciales. La documentación puede nombrar plataformas y datasets, pero no debe exponer secretos, identificadores sensibles ni valores internos de configuración.
- **rollback_compat:** El cambio sigue siendo aditivo: añade documentación, navegación y catálogo canónico sin romper contratos existentes, siempre que `/about` mantenga sus rutas actuales y el nuevo enlace complemente, no sustituya, la navegación ya existente.

