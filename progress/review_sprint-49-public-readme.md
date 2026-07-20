# Revision Sprint 49 - Public README

Veredicto: `review_pending`.

README público reescrito contra el estado real del producto. Los comandos de calidad están cubiertos por CI/tests; demo/reset/scenarios están cubiertos por tests E2E y demo. Pasan 232 tests Python, 30 frontend, typecheck, lint, build y gates.

Smoke reproducible ejecutado durante la revisión:

- `uv run python scripts/reset_demo.py`
- `uv run python scripts/demo_somalia.py`
- `uv run python scripts/demo_kenya.py --unit KEN-010 --language sw`
