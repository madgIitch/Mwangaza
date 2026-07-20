# sprint-47-offline-demo-fallback · undefined — Requisitos

- name: `Sprint 47 - Offline Demo Fallback` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-20T15:36:59.544Z

## Contexto



## Requisitos funcionales

R1. AC1: Con `MWANGAZA_MODE=demo` y sin `MWANGAZA_GEE_*`, los entrypoints públicos aprobados (UI principal, `/api/v1/**` de solo lectura y scripts demo versionados) arrancan usando solo fixtures locales, no realizan red ni inicializan servicios remotos, y devuelven estado/metadata de modo `demo` verificable.
R2. AC2: Todo payload o artefacto derivado de fixtures demo expone de forma consistente `is_demo=true` y una `reference_date` o `snapshot_id` verificable; si existe el campo histórico `is_simulated`, su compatibilidad queda definida explícitamente sin contradicción.
R3. AC3: Todas las páginas aprobadas de la app React/PWA muestran un banner persistente y visible en modo demo con texto inequívoco de origen no live y la fecha de referencia; el banner también permanece tras navegación entre Overview, Regions, Alerts, Reports y About.
R4. AC4: El mecanismo oficial de reset demo restaura de forma idempotente el estado demo versionado: alertas, outbox y configuración vuelven exactamente al baseline aprobado, sin conservar registros previos no demo ni duplicar artefactos al ejecutar el reset dos veces.
R5. AC5: Los recorridos demo aprobados de Somalia y Northern Kenya, junto con la experiencia de Reports y export/preview ya aprobada, siguen funcionando offline con el mismo comportamiento observable esencial que en modo conectado, usando datos demo marcados sin romper contratos públicos existentes.
R6. AC6: En `production`, la ausencia de credenciales o la indisponibilidad del origen live nunca activa `demo` de forma implícita; el sistema falla o degrada solo según el comportamiento explícitamente aprobado, dejando origen y error visibles en logs sanitizados y en UI/API cuando corresponda.
R7. AC7: La suite automatizada cubre al menos: arranque demo sin secretos; ausencia de red/initialización GEE en demo; persistencia del banner en navegación; reset idempotente; escenarios Somalia/Kenya offline; reports/export en demo; y caso negativo de production sin credenciales verificando que no hay fallback silencioso a demo.

## Restricciones

- **error_states:** En `production`, credenciales ausentes o indisponibilidad de GEE nunca activan `demo`. Solo se permite degradación explícita a caché válida con `data_mode=cache`, warning visible y readiness degradado; si no existe caché válida, el endpoint afectado falla con error estructurado y la UI muestra indisponibilidad sin inventar datos.
- **auth_secrets:** Se mantiene que `demo` arranca sin `MWANGAZA_GEE_*`, sin red y sin servicios remotos. En `production`, la ausencia de credenciales deriva únicamente en `cache` explícita o error estructurado, nunca en `demo`.
- **rollback_compat:** Se preservan sin ruptura los endpoints y el shape base de `/region` y `/reports`, los `snapshot_id` de Somalia y Northern Kenya, y los IDs estables de alertas y outbox. Los cambios de payload solo pueden ser aditivos. El modo conectado y el modo `cache` existentes conservan su comportamiento actual.

