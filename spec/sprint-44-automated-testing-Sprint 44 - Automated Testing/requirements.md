# sprint-44-automated-testing · undefined — Requisitos

- name: `Sprint 44 - Automated Testing` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-18T12:15:40.333Z

## Contexto



## Requisitos funcionales

R1. AC1: CI ejecuta y separa lint/typecheck, unit/integration, contract, frontend smoke y coverage; cualquier grupo fallido bloquea el merge.
R2. AC2: Fixtures compartidas fijan reloj y sustituyen Earth Engine y notificaciones sin red, sleeps ni credenciales reales.
R3. AC3: Coverage de módulos críticos se configura en `pyproject.toml`, tiene mínimo inicial 70% y falla por debajo del umbral.
R4. AC4: Tests deterministas cubren no_data, calidad insuficiente, cache corrupta y reintento/backoff.
R5. AC5: Smoke React abre `/overview`, `/region`, `/alerts`, `/reports`, `/about`, `/admin` y `/technical` con fixtures, cubre low-bandwidth y mantiene smoke del shim legado.
R6. AC6: Los contratos API v1 y JSON de dominio tienen un comando/job dedicado cuya regresión devuelve código distinto de cero.

