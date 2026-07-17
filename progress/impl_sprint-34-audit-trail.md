# Sprint 34 - Audit Trail

## Resultado

- Se agrego `AuditRepository` append-only sobre SQLite.
- Eventos con actor, tipo, entidad, region, timestamp, run, snapshot, modelo y metadata saneada.
- Helpers de ciclo de alerta y cambios de configuracion.
- Consultas por region, run y tipo.

## Validaciones

- `uv run python -m unittest tests.audit.test_audit_trail`
- `uv run python -m compileall -q src tests app.py`
- `uv run python -m unittest discover -s tests`
- `node .harness\gates.mjs sprint-34-audit-trail`
