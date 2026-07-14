# sprint-3-igad-region-catalog · undefined — Diseño

## Scope (archivos que puede tocar)

- `src/mwangaza/regions/**`
- `data/regions/**`
- `tests/regions/**`
- `pyproject.toml`
- `requirements*.txt`
- `Makefile`
- `.env.example`
- `.gitignore`
- `.github/workflows/**`
- `.harness/gates.config.json`
- `docs/**`
- `spec/**`
- `progress/**`

## Decisiones de la entrevista

- **data_model:** El catalogo expone regiones como dataclasses inmutables bajo `mwangaza.regions`: `Region` con `id`, `name`, `iso3`, `level`, `parent_id`, `is_pilot`, `coverage_type`, `source`, `source_version`, `geometry`, `ui_geometry` y `metadata`. `geometry` y `ui_geometry` son GeoJSON dicts validos. Los IDs son estables en minusculas: paises `ken`, `eth`, `som`, `sdn`, `ssd`, `uga`, `dji`, `eri`; pilotos `somalia-pilot` y `northern-kenya-pilot`. `level` usa `country` o `pilot_area`; `coverage_type` usa `regional_country` o `pilot_subnational`.
- **error_states:** Cargar el catalogo falla con `RegionCatalogError` si hay geometria vacia, geometria invalida, ID duplicado, ISO3 duplicado para paises, `parent_id` inexistente, pais IGAD faltante, piloto sin `is_pilot=true`, o si una geometria UI no conserva un GeoJSON valido. Los errores deben listar IDs/campos, nunca datos enormes ni trazas remotas.
- **edge_cases:** Se valida que Eritrea, Yibuti, Somalia y Sudan del Sur existan aunque las geometria sean simplificadas. Sudan usa ISO3 `SDN`; Sudan del Sur usa `SSD`. Las areas piloto no sustituyen cobertura subnacional completa: tienen `coverage_type=pilot_subnational`, `is_pilot=true`, `parent_id` de su pais principal o una lista de paises en metadata si cruza fronteras. La simplificacion UI no reemplaza la geometria analitica y ambas deben mantenerse separadas.
- **auth_secrets:** Sprint 3 no introduce credenciales nuevas ni lee Earth Engine. El catalogo se carga desde archivos versionados locales bajo `data/regions/**` y codigo `src/mwangaza/regions/**`; no toca `.env` salvo documentacion si fuese necesario. No hay secretos ni identificadores privados.
- **external_contracts:** Contrato publico: modulo `mwangaza.regions`, funciones `load_region_catalog()`, `get_region(region_id)`, `list_regions(level: str | None = None, include_pilots: bool = True)`, `validate_region_catalog(catalog)`. CLI opcional `python -m mwangaza.regions --validate`. Los datos viven en `data/regions/igad_regions.json` con version y fuente; no hay dependencia obligatoria de GeoPandas/Shapely en Sprint 3.
- **ui_states:** Sprint 3 no cambia el dashboard salvo que sea necesario mostrar un resumen seguro. Si se muestra algo, debe distinguir visual/textualmente paises regionales de pilotos y no afirmar cobertura subnacional completa fuera de Somalia/norte de Kenia. Los nombres de regiones deben estar listos para UI futura.
- **rollback_compat:** No se rompen contratos de Sprints 0-2: `make lint`, `make typecheck`, `make test`, `/health`, configuracion y GEE auth siguen igual. `MWANGAZA_ENABLED_COUNTRIES` mantiene los ISO3 configurables existentes y el catalogo valida contra esos codigos. No se introducen llamadas remotas ni dependencias pesadas obligatorias.
- **tests:** Tests bajo `tests/regions/**` cubren: ocho paises IGAD presentes; unicidad de IDs; unicidad de ISO3 para `level=country`; existencia y validez estructural de `geometry` y `ui_geometry`; pilotos marcados explicitamente; `parent_id` valido; separacion entre geometria analitica y UI; errores para duplicados/geometria vacia/parent inexistente. Los tests no llaman red ni Earth Engine.

