# Implementación · Sprint 62B - Real Historical Backfill

- Añadidas ventanas dekadales exactas y corte en la última dekada completa.
- Añadido adaptador Earth Engine para CHIRPS Daily, MOD13Q1 y MOD11A2.
- MODIS resuelve el último compuesto no futuro y conserva `observed_at`/`age_days`.
- Añadidas escritura JSONL atómica, manifiesto canónico, SHA-256 y reanudación por fila.
- Añadido CLI con `--dry-run`, Kenya por defecto, IGAD explícito, `--confirm-remote` y `--force`.
- El piloto real materializó 92 filas de Kenya desde 2024-01-01.
- La ampliación IGAD materializó 736 filas: 92 dekadas para cada uno de los ocho países.
- Añadidos scripts con ETA para descargar baseline 2003-2023, derivar climatologías/anomalías/labels y entrenar candidatos.
