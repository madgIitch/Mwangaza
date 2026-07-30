# Sprint 54 - Implementación

Estado: implementación completa, pendiente de revisión humana.

- El CLI `python -m mwangaza.data.refresh` es común a local, CI y Cloud Run Job.
- La API dejó de iniciar consultas GEE y el frontend dejó de sondear esperando un refresco HTTP.
- Store local con lock exclusivo y store GCS con precondición de generación evitan concurrencia.
- La publicación conserva una copia inmutable y promociona atómicamente `live-dashboard-last-good.json`.
- Los errores registran un resultado saneado y preservan `last_success`.
- La frescura se recalcula al leer para detectar jobs detenidos aunque el fichero no cambie.
- El snapshot de producción se monta en `/mnt/mwangaza-refresh`, separado de caché y SQLite.
- Cloud Run Job, Scheduler, cuentas de servicio, IAM mínimo y alerta por logs están automatizados.
- Imagen refresh verificada como UID/GID `10001:10001`; dry-run sin red ni escrituras: PASS.
- Smoke Docker API/web de Sprint 53 sigue pasando tras la integración.
- 257/257 tests backend, 61/61 frontend, build y gates oficiales: PASS.
- Despliegue externo completado posteriormente en `mwangaza-502413`, región `europe-west1`.
- Web pública, API, bucket privado, Secret Manager, Job, Scheduler y política de alerta: operativos.
- Primer run real `mwangaza-refresh-x6fjv`: éxito en 1m40s; segundo run idempotente: éxito.
- Snapshot público en modo cache, frescura current, fecha efectiva 2026-07-30 y edad 0.
