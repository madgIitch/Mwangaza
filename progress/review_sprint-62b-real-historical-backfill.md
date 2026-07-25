# Revisión · Sprint 62B - Real Historical Backfill

Estado: `review_pending`.

## Evidencia

- Dry-run completo: 8 regiones × 92 dekadas.
- Smoke real GEE: autenticación correcta y 736 filas materializadas.
- Artefacto: `data/historical/gee-from-2024/history.jsonl` (local, ignorado por Git).
- Hash: `sha256:3a2b5777cf274377dcb63a6f4b88edc35fe74e385ae476c926540ed4a94e3c08`.
- 16 ausencias explícitas: las dos últimas dekadas CHIRPS aún no publicadas para cada país.
- NDVI age: 0–24 días, media 7.77.
- LST age: 0–8 días, media 3.42.

## Veredicto técnico

La adquisición IGAD y el tratamiento están listos. Thresholds v2 se derivan solo del baseline pre-2024.

## Resultado de thresholds v2 y training

- Dataset: 2.208 filas, hash `sha256:491842290c0e4bda10ed283c1e80f875d6a893d41222793a4ce71aa7298afa41`.
- Tres positivos por horizonte.
- ML pierde ligeramente contra frecuencia histórica en 10/20/30 días.
- Estado final: `rejected_insufficient_skill` en los tres horizontes.
- Run hash: `sha256:7576b5200670a15f97a265d3e0d7f425429fd56d48cc3b078b849d7546bf4bd6`.

## Resultado ampliado 2018-2026

- Referencia separada: 2003-2017.
- 2.464 observaciones, 7.392 filas y 86 positivos por horizonte.
- Dataset hash: `sha256:166eafb0c89ce692942194e339d1431faf0e8a430870183c1109c349d06ef751`.
- Historical frequency conserva mejor Brier que logística y boosting.
- Estado: `rejected_insufficient_skill` en 10/20/30 días.
- Run hash: `sha256:0e38de9067ec6d96f5fe6136bb57b6dca4aa5c8d6e732756d1e7d6d2007245cc`.
