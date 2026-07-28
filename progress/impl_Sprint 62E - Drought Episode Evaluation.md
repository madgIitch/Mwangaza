# Implementación Sprint 62E

## 2026-07-28 - estado: review_pending

- Nuevo módulo `episode_evaluation` para targets hazard, folds sin fuga,
  entrenamiento OOF, episodios predichos, matching y métricas.
- Nuevo CLI `scripts/evaluate_drought_episodes.py` con ETA, artefactos atómicos,
  hashes y resumen de skill.
- Umbral de episodio 0,5; continuidad máxima 32 días; matching uno-a-uno.
- Gate ML: mejor Brier y F1 que el baseline champion, falsas alarmas no mayores
  y al menos dos episodios evaluables.

Verificación:

- `uv run pytest tests/probabilistic -q`: 49 passed.
- `uv run python -m compileall -q src tests scripts`: passed.
- `uv run ruff check ...`: passed.
- Corrida real repetida dos veces con run hash idéntico
  `sha256:552e25e16d6000dbd2b5b2da79a83c252d209550bed1b8377cea1a455cbdfc03`.

Resultado real:

- 20.364 filas conocidas; 98 episodios OOF; 24 folds.
- 10d persistence Brier/F1 0,045710/0,740; logistic 0,118637/0,680.
- 20d persistence Brier/F1 0,088478/0,720; logistic 0,126405/0,659.
- 30d persistence Brier/F1 0,129962/0,646; logistic 0,136091/0,645.
- Ningún ML alcanza `episode_skill_eligible`; serving permanece deshabilitado.
