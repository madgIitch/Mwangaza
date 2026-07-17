# sprint-40-pwa-installability · undefined — Requisitos

- name: `Sprint 40 - React PWA Migration` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-17T14:24:28.419Z

## Contexto



## Requisitos funcionales

R1. AC1: El dashboard principal ya no depende de Streamlit para la experiencia de usuario; la app React/Vite renderiza las pantallas equivalentes usando datos de `/api/v1/**` o fixtures demo.
R2. AC2: El manifest contiene nombre, short_name, iconos, start_url y display standalone, y la app puede instalarse en navegador compatible.
R3. AC3: El service worker cachea unicamente assets seguros y shell, no datos sensibles indefinidamente.
R4. AC4: Sin conexion se muestra el ultimo timestamp disponible y una advertencia; no se afirma que los datos sean live en modo offline.
R5. AC5: La migracion conserva las capacidades visibles ya implementadas: riesgo regional, drilldown, alertas activas, comparacion historica, exposicion potencial, reportes/export, forecast diagnostics, i18n y modo low-bandwidth.
R6. AC6: Los tests automatizados del frontend verifican render principal, low-bandwidth, i18n, offline shell y consumo de contratos API; el build/typecheck/lint JS termina con codigo 0.
R7. AC7: `app.py` deja de ser el frontend canonico y queda como shim documentado o aviso de migracion; la documentacion y comandos de desarrollo apuntan al frontend JS.
R8. AC8: Lighthouse o prueba equivalente no reporta errores criticos de manifest/installability.

## Restricciones

- **error_states:** Estados offline/API/demo/cache/live definidos.
- **auth_secrets:** Sin secretos ni GEE directo en navegador.
- **rollback_compat:** `app.py` queda como shim documentado.

