# sprint-44-automated-testing · undefined — Tareas

Checklist de implementación. El agente marca [x] al completar; los gates verifican.

- [x] (T1) AC1: CI ejecuta y separa lint/typecheck, unit/integration, contract, frontend smoke y coverage; cualquier grupo fallido bloquea el merge.  ↔ R1
- [x] (T2) AC2: Fixtures compartidas fijan reloj y sustituyen Earth Engine y notificaciones sin red, sleeps ni credenciales reales.  ↔ R2
- [x] (T3) AC3: Coverage de módulos críticos se configura en `pyproject.toml`, tiene mínimo inicial 70% y falla por debajo del umbral.  ↔ R3
- [x] (T4) AC4: Tests deterministas cubren no_data, calidad insuficiente, cache corrupta y reintento/backoff.  ↔ R4
- [x] (T5) AC5: Smoke React abre `/overview`, `/region`, `/alerts`, `/reports`, `/about`, `/admin` y `/technical` con fixtures, cubre low-bandwidth y mantiene smoke del shim legado.  ↔ R5
- [x] (T6) AC6: Los contratos API v1 y JSON de dominio tienen un comando/job dedicado cuya regresión devuelve código distinto de cero.  ↔ R6
- [x] Tests que cubran los criterios de aceptación
