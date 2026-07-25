# sprint-62b-real-historical-backfill · undefined — Diseño

## Scope (archivos que puede tocar)

- `src/mwangaza/probabilistic/**`
- `src/mwangaza/gee/**`
- `scripts/backfill_probabilistic_history.py`
- `tests/probabilistic/**`
- `tests/fixtures/probabilistic/**`
- `data/historical/.gitkeep`
- `.gitignore`
- `docs/probabilistic-risk.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS.md`
- `spec/sprint-62b-real-historical-backfill-*/**`
- `progress/**`

## Decisiones de la entrevista

- **data_model:** Una fila representa region y dekada. Incluye periodo, `as_of`, valores CHIRPS/NDVI/LST, `observed_at` y `age_days` por compuesto, cobertura, calidad, modo real, versiones y lineage. El artefacto tiene schema, rango, regiones, resumen y SHA-256. Un adaptador posterior produce `HistoricalRiskPeriod`; el backfill no entrena automaticamente.
- **error_states:** Autenticacion, permisos, cuota, red, respuesta corrupta y coleccion vacia tienen reason codes distintos. Una senal ausente queda null, nunca cero. La fila solo se marca completa cuando se escribe y verifica atomicamente. Los fallos parciales conservan el checkpoint anterior.
- **edge_cases:** Las dekadas son 1-10, 11-20 y 21-fin de mes en UTC. El corte inicial es 2024-01-01 y el final por defecto es la ultima dekada completa. CHIRPS se suma dentro de la ventana. MOD13Q1 de 16 dias y MOD11A2 de 8 dias usan el ultimo compuesto con `observed_at <= as_of`; no existe lookahead. Mes corto, ano bisiesto, compuesto antiguo y region sin pixeles quedan cubiertos.
- **auth_secrets:** El CLI reutiliza `check_gee_auth` y las variables privadas existentes. No imprime proyecto sensible, cuenta, JSON privado ni URLs firmadas. Los artefactos contienen solo agregados regionales no personales. `.env`, credenciales, checkpoints y datos descargados no se versionan.
- **external_contracts:** Fuentes iniciales: `UCSB-CHG/CHIRPS/DAILY`, `MODIS/061/MOD13Q1` y `MODIS/061/MOD11A2`. Piloto por defecto: Kenya nacional. La expansion IGAD requiere flag explicito. Salida local JSONL canonica y manifiesto JSON; no se descargan rasteres originales.
- **ui_states:** No hay UI ni endpoint. El CLI muestra plan, numero estimado de filas, progreso, filas reutilizadas, fallidas y ruta final. `--dry-run` no consulta GEE. La expansion desde Kenya requiere `--scope igad --confirm-remote`.
- **rollback_compat:** Feature aditiva y offline. No altera dashboard, API, cache live ni contratos deterministas. El directorio local puede borrarse y regenerarse; el codigo anterior sigue funcionando. Sprint 63 depende del backfill, pero no se inicia automaticamente.
- **tests:** Tests offline con fake GEE cubren ventanas, leap year, no-lookahead, escalado, edad, ausencias, reanudacion, `--force`, escritura atomica, hash, dry-run y ausencia de secretos/red. El smoke manual Kenya consulta tres dekadas y valida valores finitos y metadata real.

