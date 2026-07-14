# Region Catalog

Sprint 3 adds a local, versioned IGAD region catalog.

## Scope

The catalog includes the eight IGAD countries used by the regional view:

- Kenya (`KEN`)
- Ethiopia (`ETH`)
- Somalia (`SOM`)
- Sudan (`SDN`)
- South Sudan (`SSD`)
- Uganda (`UGA`)
- Djibouti (`DJI`)
- Eritrea (`ERI`)

It also includes two explicit pilot areas: Somalia and Northern Kenya. Pilot
areas are marked with `is_pilot=true` and `coverage_type=pilot_subnational`.
They are not complete validated subnational coverage for the IGAD region.

## Contract

Use `mwangaza.regions`:

- `load_region_catalog()`
- `get_region(region_id)`
- `list_regions(level=None, include_pilots=True)`
- `validate_region_catalog(catalog)`

Each region includes `geometry` and `ui_geometry` as separate GeoJSON Polygon
objects. Sprint 3 uses coarse prototype polygons so the application can validate
stable IDs, ISO codes and pilot metadata without remote calls or heavy GIS
dependencies. Later data sprints can replace the analytical geometry source
without changing region IDs.

Manual validation:

```bash
python -m mwangaza.regions --validate
```
