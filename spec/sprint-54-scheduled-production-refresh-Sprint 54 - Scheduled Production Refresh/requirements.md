# sprint-54-scheduled-production-refresh · undefined — Requisitos

- name: `Sprint 54 - Scheduled Production Refresh` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-30T00:19:24.684Z

## Contexto



## Requisitos funcionales

R1. Local, CI y Cloud Run Job invocan el mismo CLI de refresco y este nunca se ejecuta dentro de una petición HTTP.
R2. Dos ejecuciones concurrentes para el mismo período no procesan ni publican dos veces el corte.
R3. Un fallo de consulta, validación o publicación no reemplaza el último snapshot válido.
R4. El candidato validado se promociona atómicamente y conserva una copia inmutable direccionable para rollback.
R5. Cada ejecución registra `run_id`, período, timestamps, resultado y resumen de calidad sin secretos.
R6. El API y el dashboard exponen última actualización exitosa, fecha efectiva, edad y aviso stale sin confundir consulta con observación.
R7. La infraestructura define Cloud Run Job y Cloud Scheduler con IAM mínimo, configuración runtime y alerta basada en exit code/log.
R8. Pruebas automatizadas cubren lock, idempotencia, fallo seguro, publicación atómica, frescura y ejecución del CLI.

## Restricciones

- **error_states:** lock ocupado, lock vencido, consulta fallida, candidato inválido y promoción fallida
- **auth_secrets:** credenciales solo runtime; IAM mínimo para Job, Scheduler y bucket
- **rollback_compat:** snapshots inmutables y puntero estable recuperable

