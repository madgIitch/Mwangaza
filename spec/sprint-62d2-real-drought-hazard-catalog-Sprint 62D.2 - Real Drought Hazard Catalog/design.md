# sprint-62d2-real-drought-hazard-catalog · undefined — Diseño

## Scope (archivos que puede tocar)

- `src/mwangaza/probabilistic/**`
- `scripts/backfill_ndma_drought_phases.py`
- `scripts/import_independent_labels.py`
- `scripts/audit_drought_hazard_episodes.py`
- `tests/probabilistic/**`
- `tests/fixtures/probabilistic/**`
- `docs/data-sources/**`
- `docs/probabilistic-risk.md`
- `docs/data-provenance.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS.md`
- `spec/sprint-62d2-real-drought-hazard-catalog-*/**`
- `progress/**`

## Decisiones de la entrevista

- **data_model:** Mantener observaciones hazard fuente y episodios auditados como artefactos separados. EM-DAT conserva eventos nacionales y subnacionales sin expansión artificial. NDMA conserva condado, periodo, fase original, publicación, documento/hash, método de extracción y validación. La auditoría agrupa por ADM1, fuente/semántica y continuidad temporal versionada.
- **error_states:** Archivo EM-DAT ausente, evento solo nacional, PDF inaccesible, texto sin fase, condado/periodo discordante, fase ambigua, duplicado, autoridad sin adapter y país sin cobertura tienen estados separados. Ninguno se convierte en negativo.
- **edge_cases:** NDMA operational phase no equivale a declaración legal. Un PDF con varias fases o periodo no verificable queda pendiente. Eventos nacionales se auditan pero no forman episodios ADM1. Episodios no mezclan fuentes con taxonomías incompatibles y conservan censura en extremos.
- **auth_secrets:** NDMA es público. EM-DAT requiere archivo registrado aportado por el usuario y su licencia aplicable; no se automatiza autenticación ni redistribución. Datos descargados quedan ignorados fuera de Git.
- **external_contracts:** NDMA usa exclusivamente su archivo oficial de County Bulletins y URLs de documentos oficiales. EM-DAT usa el public table CSV registrado. Otras autoridades se documentan solo con URL oficial y estado verificado, sin scraping de prensa.
- **ui_states:** Sin UI ni entrenamiento. CLIs separados para backfill NDMA, importación y auditoría; dry-run, resume, ETA, hashes y manifiestos.
- **rollback_compat:** Aditivo sobre 62D. No modifica features ni probabilidades. Eliminar los nuevos artefactos devuelve el catálogo FEWS previo sin cambiar su semántica.
- **tests:** Fixtures offline realistas cubren extracción inequívoca/ambigua, fechas, condados, EM-DAT subnacional/nacional, episodios, cobertura, determinismo y secretos. Smoke NDMA real acotado; EM-DAT real solo cuando el usuario aporte el archivo.

