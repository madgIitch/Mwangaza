# Sesión actual

Feature: **sprint-65-probability-ui-integration — Sprint 65 - Drought Continuation UI Integration** — estado: `review_pending`.

## Resultado

- Region Explorer incorpora un módulo compacto ligado por ID exacto a la ADM1 seleccionada.
- A 30 días compara ML experimental y referencia histórica; a 60/90/180 solo muestra la referencia.
- Estados `unavailable` y `not_applicable` abstienen sin mostrar 0%.
- BSS, IC95, calidad y asociaciones no causales permanecen visibles.
- Low-bandwidth conserva la misma semántica mediante tabla.
- Reports HTML/PDF incorpora las estimaciones activas desde el snapshot materializado.
- Demo offline incluye Turkana activo y Baringo inactivo para revisar ambos estados.
- 59 tests frontend, 41 tests UI/reportes, lint, typecheck y build pasan.
- Dashboard y continuidad deben compartir modo: cualquier mezcla demo/real falla cerrada.
- Smoke GEE real Kenya: 47 ADM1 en perfil, 121/121 ADM1 IGAD concluyentes, `not_demo=true`.

## Siguiente acción

- Revisión humana en `/region`: seleccionar Kenya → Turkana.
- Cerrar 65 solo tras aceptación; no comenzar el siguiente sprint antes de esa revisión.
