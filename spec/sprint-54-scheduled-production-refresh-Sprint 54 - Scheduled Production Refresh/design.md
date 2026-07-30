# sprint-54-scheduled-production-refresh · undefined — Diseño

## Scope (archivos que puede tocar)

- `src/mwangaza/data/**`
- `src/mwangaza/services/**`
- `src/mwangaza/api/**`
- `frontend/src/**`
- `tests/**`
- `infrastructure/scheduler/**`
- `scripts/refresh.sh`
- `scripts/**`
- `.github/workflows/refresh.yml`
- `.github/workflows/**`
- `Dockerfile`
- `docker-compose.yml`
- `infrastructure/**`
- `docs/deployment/**`
- `docs/**`
- `pyproject.toml`
- `requirements*.txt`
- `Makefile`
- `.env.example`
- `.gitignore`
- `.harness/gates.config.json`
- `spec/**`
- `progress/**`
- `spec.json`
- `.harness/interviews/**`

## Enfoque

- **data_model:** snapshot, manifiesto de run, frescura y resumen de calidad versionados
- **external_contracts:** CLI único, Cloud Run Job, Cloud Scheduler y backend de almacenamiento
- **edge_cases:** ejecución repetida, concurrencia, snapshot previo ausente y reloj/edad
- **ui_states:** current, stale, failed con último snapshot válido, y sin snapshot

## Decisiones de la entrevista

- **execution:** El refresco se ejecutará como un comando Python único y probado, invocable localmente,
desde CI y como Cloud Run Job. Cloud Scheduler solo disparará el Job; no se recalculará dentro
de una petición del dashboard.
- **storage:** El artefacto publicado será un snapshot JSON versionado con manifiesto de estado. El
backend local usará filesystem y production podrá usar Google Cloud Storage. La publicación
estable se hará únicamente después de generar y validar un candidato completo.
- **locking:** Un lock con propietario, período y expiración impedirá procesar dos veces el mismo corte.
Filesystem usará creación exclusiva; GCS usará precondición de generación cero. Un lock vencido
se podrá recuperar de forma explícita y auditable.
- **atomicity:** El último snapshot válido nunca se modifica in-place. Se escribe un candidato, se valida
su esquema y calidad, y finalmente se promueve de forma atómica. Un fallo conserva el estable
anterior y deja un manifiesto de ejecución fallida separado.
- **freshness:** El contrato incluirá `run_id`, hora de consulta, fecha efectiva de observación, edad,
estado `current|stale|failed` y resumen de calidad. El dashboard distinguirá última ejecución
exitosa de antigüedad efectiva y mostrará aviso visible cuando el snapshot esté stale.
- **operations:** Los fallos producirán exit code no cero y log JSON estructurado apto para alerta de Cloud
Monitoring. La guía cubrirá creación de Job/Scheduler, IAM mínimo, diagnóstico y rollback al
objeto versionado previo.
- **dependency:** El usuario ha avanzado al siguiente sprint, por lo que Sprint 53 se cierra como revisado.
El Sprint 54 construye sobre sus imágenes, pero no afirma que exista ya una URL pública ni exige
credenciales reales para sus pruebas locales.

