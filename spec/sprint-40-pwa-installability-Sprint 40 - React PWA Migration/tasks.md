# sprint-40-pwa-installability - Sprint 40 - React PWA Migration - Tareas

Checklist de implementacion. El agente marca [x] al completar; los gates verifican.

- [x] (T1) AC1: El dashboard principal ya no depende de Streamlit para la experiencia de usuario; la app React/Vite renderiza las pantallas equivalentes usando datos de `/api/v1/**` o fixtures demo. -> R1
- [x] (T2) AC2: El manifest contiene nombre, short_name, iconos, start_url y display standalone, y la app puede instalarse en navegador compatible. -> R2
- [x] (T3) AC3: El service worker cachea unicamente assets seguros y shell, no datos sensibles indefinidamente. -> R3
- [x] (T4) AC4: Sin conexion se muestra el ultimo timestamp disponible y una advertencia; no se afirma que los datos sean live en modo offline. -> R4
- [x] (T5) AC5: La migracion conserva las capacidades visibles ya implementadas: riesgo regional, drilldown, alertas activas, comparacion historica, exposicion potencial, reportes/export, forecast diagnostics, i18n y modo low-bandwidth. -> R5
- [x] (T6) AC6: Los tests automatizados del frontend verifican render principal, low-bandwidth, i18n, offline shell y consumo de contratos API; el build/typecheck/lint JS termina con codigo 0. -> R6
- [x] (T7) AC7: `app.py` deja de ser el frontend canonico y queda como shim documentado o aviso de migracion; la documentacion y comandos de desarrollo apuntan al frontend JS. -> R7
- [x] (T8) AC8: Lighthouse o prueba equivalente no reporta errores criticos de manifest/installability. -> R8
- [x] Tests que cubran los criterios de aceptacion
