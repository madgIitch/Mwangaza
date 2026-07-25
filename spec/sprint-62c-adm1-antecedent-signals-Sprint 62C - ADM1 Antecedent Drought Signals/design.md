# sprint-62c-adm1-antecedent-signals · undefined — Diseño

## Scope (archivos que puede tocar)

- `src/mwangaza/probabilistic/**`
- `src/mwangaza/gee/**`
- `scripts/backfill_adm1_antecedent_signals.py`
- `scripts/prepare_adm1_probabilistic_dataset.py`
- `tests/probabilistic/**`
- `tests/fixtures/probabilistic/**`
- `data/historical/.gitkeep`
- `.gitignore`
- `docs/data-sources/**`
- `docs/probabilistic-risk.md`
- `docs/data-provenance.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS.md`
- `spec/sprint-62c-adm1-antecedent-signals-*/**`
- `progress/**`

## Decisiones de la entrevista

- **data_model:** Una fila representa ADM1 y dekada. Conserva parent country, boundary id/source/version, señales actuales, acumulados antecedentes, SPI 1/3/6, SPEI 1/3/6, suelo, ET, forecast disponible, observed_at/age/lead, quality y lineage. Las señales mensuales se asignan a dekadas sin fingir nueva observación.
- **error_states:** Colección vacía, fecha no soportada, gap, cobertura insuficiente, unidad inválida, cuota/red y geometría sin píxeles tienen reason codes separados. Ausencia queda null, nunca cero. Forecast anterior a 2024-11-12 es `not_available_for_date`.
- **edge_cases:** SPI solo usa historia anterior al as_of y ventanas mensuales completas. SPEIbase termina en 2024/2025 según publicación y no se extrapola. FLDAS mensual conserva su timestamp. ADM1 pequeñas/islas pueden no tener píxeles a resolución gruesa y quedan con cobertura explícita. Cambios de frontera se fijan a la versión local aprobada.
- **auth_secrets:** Se reutiliza la cuenta GEE existente; no se imprimen secretos. SPEIbase y ECMWF requieren atribución CC-BY-4.0; FLDAS requiere cita NASA GES DISC. Los agregados ADM1 no contienen datos personales.
- **external_contracts:** Colecciones: CHIRPS Daily, MOD13Q1, MOD11A2, `CSIC/SPEI/2_11`, `NASA/FLDAS/NOAH01/C/GL/M/V001`, `ECMWF/NRT_FORECAST/IFS/OPER`. Forecast se usa como feature solo cuando creation_time precede as_of y lead corresponde al horizonte.
- **ui_states:** Sin UI ni endpoint. Dos CLI: backfill y preparación, ambos con dry-run, progreso, ETA, resume y manifiesto. Ningún script entrena automáticamente.
- **rollback_compat:** Aditivo. No altera dataset nacional ni probabilidades públicas. Los artefactos ADM1 viven bajo `data/historical/` ignorado. Deshabilitar las nuevas features conserva el pipeline anterior.
- **tests:** Fakes cubren 121 ADM1, batching, SPI anti-lookahead, ventanas, gaps, unidades FLDAS, disponibilidad SPEI/forecast, observed_at, resume, hashes y secretos. Smoke real mínimo Kenya/Somalia.

