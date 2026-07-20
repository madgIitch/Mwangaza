# sprint-48-data-provenance-documentation · undefined — Diseño

## Scope (archivos que puede tocar)

- `docs/about-interface.md`
- `docs/contracts.md`
- `docs/thresholds.md`
- `docs/ARCHITECTURE.md`
- `docs/data-provenance.md`
- `frontend/src/App.tsx`
- `frontend/src/styles.css`
- `tests/frontend/app.test.tsx`
- `tests/frontend/smoke.test.tsx`

## Enfoque

- **data_model:** La feature debe definir un inventario canónico versionado y legible por máquina en `docs/data-sources/catalog.json`, reutilizado como fuente de verdad de `docs/data-provenance.md` y de la vista `/about/provenance`. Cada entrada del catálogo incluye como mínimo `source_name`, `variable_or_indicator`, `unit`, `spatial_or_temporal_resolution`, `update_frequency`, `license_or_terms`, `applicable_modes`, `latency` y `limitations`.
- **external_contracts:** El contrato navegable queda fijado en la ruta interna estable `/about/provenance`, enlazada desde `/about` y reutilizable como referencia durable desde reportes. La documentación persistente equivalente vive en `docs/data-provenance.md`, y el catálogo fuente de verdad en `docs/data-sources/catalog.json`.
- **edge_cases:** La documentación debe separar de forma explícita las variantes `live`, `cache` y `demo` cuando cambien procedencia, latencia o cobertura. `demo` y cualquier dato simulated deben quedar claramente diferenciados de los datos operativos. `cache` conserva la procedencia original y añade la antigüedad. Si una misma variable usa distintas fuentes o coberturas según modo o país, el catálogo debe reflejar esa variante sin ambigüedad. `exposure` solo muestra fuente/año/resolución cuando existan datos disponibles para esta release.
- **ui_states:** `/about` debe mostrar un CTA visible con el texto `Data provenance and methodology` dentro de la sección Methodology. Ese enlace navega a la vista dedicada `/about/provenance`, que debe renderizar de forma visible el catálogo, las definiciones, las limitaciones, los umbrales etiquetados como no oficiales/configurables y un diagrama de linaje. Si existe contenido pendiente de verificación, la advertencia debe ser visible en esa misma vista.

## Decisiones de la entrevista

- **adv-6e33a78a00:** ### [adv-edc4d9dca9] El spec no fija de forma inequívoca cuáles son las "fuentes aprobadas para esta release". `docs/about-interface.md` mezcla fuentes implementadas con fuentes esperadas/futuras, así que no se puede decidir PASS/FAIL sobre el listado mínimo exigido sin una decisión de negocio sobre el conjunto exacto de fuentes obligatorias en esta release.

**R:**
- **adv-7e2aa88be1:** ## Decisiones registradas
- **data_model:** Usar una estructura canónica versionada y legible por máquina en `docs/data-sources/catalog.json`, reutilizada como fuente de verdad por la documentación. Cada entrada incluye nombre, indicador, unidad, resolución espacial/temporal, frecuencia, licencia/términos, modos aplicables, latencia y limitaciones.
- **error_states:** Ningún campo queda silencioso. Cuando licencia o metadatos no estén confirmados se muestra `Pending verification` con una advertencia de no redistribución; la fuente permanece documentada pero no puede presentarse como aprobada para uso operativo.
- **edge_cases:** Documentar variantes `live`, `cache` y `demo` cuando cambien procedencia, latencia o cobertura. Demo y simulated deben quedar claramente separados de datos operativos; cache conserva la procedencia original y añade antigüedad.
- **external_contracts:** Crear la ruta interna estable `/about/provenance`, enlazada desde `/about` y reutilizable como referencia desde reportes. La documentación durable equivalente vive en `docs/data-provenance.md`.
- **ui_states:** Usar una vista dedicada `/about/provenance`, con CTA visible `Data provenance and methodology` dentro de la sección Methodology de `/about`. La vista muestra catálogo, definiciones, limitaciones, umbrales y diagrama de linaje.
- **tests:** Verificar como mínimo MODIS NDVI, CHIRPS rainfall, MODIS LST, límites administrativos y exposición poblacional; además comprobar la ruta, el enlace desde About, los campos completos del catálogo, las definiciones, el aviso de umbrales no oficiales y la cadena source→transformation→cache→API→UI→report.

