# Review - sprint-23-regional-risk-map - Sprint 23 - Regional Risk Map

## Veredicto

APPROVED -> `review_pending`.

## Checkpoints - gates

- [x] lint/typecheck equivalente: `uv run python -m compileall -q src tests app.py smoke_tests`
- [x] test equivalente: `uv run python -m unittest discover -s tests` (185 tests)
- [x] diff-scope: `node .harness/gates.mjs sprint-23-regional-risk-map`

## Checkpoints - SDD

- [x] spec/sprint-23-regional-risk-map-Sprint 23 - Regional Risk Map/requirements.md
- [x] spec/sprint-23-regional-risk-map-Sprint 23 - Regional Risk Map/design.md
- [x] spec/sprint-23-regional-risk-map-Sprint 23 - Regional Risk Map/tasks.md

## Pendiente

- [ ] Smoke test humano visual si aplica; despues cerrar con `node .harness/spec.mjs done sprint-23-regional-risk-map`.
- [ ] Smoke real GEE manual si hay credenciales: `python smoke_tests/sprint23_regional_risk_map_real_gee.py --cache-dir .cache/mwangaza --region-id som`.
- [ ] Arranque dashboard con credenciales GEE para validar origen visible `live`.
