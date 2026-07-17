# Data Export

Sprint 32 adds safe CSV and JSON export for the visible dashboard snapshot.

Contracts:

- `build_visible_export(data, region_id=None, max_rows=500, include_geometry=False)`;
- `export_visible_json(export)`;
- `export_visible_csv(export)`;
- `safe_export_filename(export, extension)`.

CSV and JSON are derived from the same logical rows. JSON includes
`schema_version` and source metadata. CSV leaves null values empty; JSON keeps
them as `null`.

Geometry is omitted by default. If explicitly requested, only simplified UI
geometry from the regional map is included.

The export is limited to the selected snapshot period and a positive `max_rows`
limit. Serializers redact secret-like keys, credentials, tokens and local paths.
