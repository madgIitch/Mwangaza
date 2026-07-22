# Review pending · Sprint 58 - Alerts Center Completion

## Veredicto

Implementación lista para smoke test humano. Los criterios T1-T14 están cubiertos y los contratos públicos siguen siendo aditivos.

## Checkpoints

- API: IDs estables, timestamps, filtros, paginación, resumen, detalle, historial y exportaciones.
- Seguridad: outbox simulado, destinatarios enmascarados, sin adaptadores de envío ni mutaciones públicas.
- UI: consola table-first, URL reproducible, inspector sticky, deep-link y estados vacíos explícitos.
- Accesibilidad operativa: modo low-bandwidth con filtros, resumen, tabla, evidencia, recomendaciones, lifecycle y exportaciones.
- Calidad: suite Python/frontend, typecheck, lint y build pasan.

## Pendiente humano

- Confirmar jerarquía visual y comportamiento responsive en un navegador real.

## Corrección posterior al smoke · cobertura regional

- El smoke live detectó que la cola se construía sólo desde el riesgo de la región seleccionada (`SOM`), aunque el snapshot contenía los ocho países IGAD.
- La cola fallback ahora agrega el último riesgo nacional de cada país y excluye unidades subnacionales para evitar duplicados.
- Regresión automatizada: ocho riesgos nacionales producen ocho alertas para `dji`, `eri`, `eth`, `ken`, `sdn`, `som`, `ssd` y `uga`.
- Verificación contra el snapshot live local: 8 alertas, una por cada país IGAD.
- Suites enfocadas backend/API: 49 passed. Frontend: typecheck, lint y 48 tests pasan.
- La suite Python completa quedó sin resultado por timeout de 120 segundos; la suite enfocada no presenta fallos.
