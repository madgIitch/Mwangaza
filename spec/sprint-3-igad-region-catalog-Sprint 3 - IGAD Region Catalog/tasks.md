# sprint-3-igad-region-catalog · undefined — Tareas

Checklist de implementación. El agente marca [x] al completar; los gates verifican.

- [ ] (T1) El catalogo incluye exactamente los ocho paises IGAD requeridos para la vista regional: Kenia (`KEN`), Etiopia (`ETH`), Somalia (`SOM`), Sudan (`SDN`), Sudan del Sur (`SSD`), Uganda (`UGA`), Yibuti (`DJI`) y Eritrea (`ERI`).  ↔ R1
- [ ] (T2) Cada region expuesta por `mwangaza.regions` tiene `id`, `name`, `iso3`, `level`, `parent_id`, `is_pilot`, `coverage_type`, `source`, `source_version`, `geometry` y `ui_geometry`; ambos campos de geometria son objetos GeoJSON no vacios.  ↔ R2
- [ ] (T3) `validate_region_catalog` bloquea catalogos con IDs duplicados, ISO3 duplicado entre paises, geometria vacia o estructuralmente invalida, `parent_id` inexistente o pais IGAD obligatorio ausente.  ↔ R3
- [ ] (T4) El catalogo incluye al menos dos areas piloto marcadas explicitamente con `is_pilot=true` y `coverage_type=pilot_subnational`: Somalia y norte de Kenia; las areas piloto no se presentan como cobertura subnacional completa del IGAD.  ↔ R4
- [ ] (T5) La geometria simplificada para UI se almacena por separado como `ui_geometry` y no sustituye la geometria analitica `geometry`; los tests verifican que ambas existen y son objetos distintos.  ↔ R5
- [ ] (T6) Hay tests automatizados para unicidad de IDs, unicidad de ISO3 en paises, presencia de los ocho paises, validez estructural de geometria, parent_id de pilotos y errores de validacion; la suite no llama red ni Earth Engine.  ↔ R6
- [ ] Tests que cubran los criterios de aceptación
