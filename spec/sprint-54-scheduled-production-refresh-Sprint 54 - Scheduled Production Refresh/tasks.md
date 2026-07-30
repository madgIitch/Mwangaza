# sprint-54-scheduled-production-refresh · undefined — Tareas

Checklist de implementación. El agente marca [x] al completar; los gates verifican.

- [ ] (T1) Local, CI y Cloud Run Job invocan el mismo CLI de refresco y este nunca se ejecuta dentro de una petición HTTP.  ↔ R1
- [ ] (T2) Dos ejecuciones concurrentes para el mismo período no procesan ni publican dos veces el corte.  ↔ R2
- [ ] (T3) Un fallo de consulta, validación o publicación no reemplaza el último snapshot válido.  ↔ R3
- [ ] (T4) El candidato validado se promociona atómicamente y conserva una copia inmutable direccionable para rollback.  ↔ R4
- [ ] (T5) Cada ejecución registra `run_id`, período, timestamps, resultado y resumen de calidad sin secretos.  ↔ R5
- [ ] (T6) El API y el dashboard exponen última actualización exitosa, fecha efectiva, edad y aviso stale sin confundir consulta con observación.  ↔ R6
- [ ] (T7) La infraestructura define Cloud Run Job y Cloud Scheduler con IAM mínimo, configuración runtime y alerta basada en exit code/log.  ↔ R7
- [ ] (T8) Pruebas automatizadas cubren lock, idempotencia, fallo seguro, publicación atómica, frescura y ejecución del CLI.  ↔ R8
- [ ] Tests que cubran los criterios de aceptación
