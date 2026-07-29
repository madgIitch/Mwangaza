# Sesion actual

Feature: **sprint-65-probability-ui-integration - Sprint 65** - estado: `review_pending`.

## Resultado

- Continuidad satelital materializada para 121/121 ADM1 y 47/47 Kenya.
- 484/484 resultados a 30, 60, 90 y 180 dias; 11 condiciones activas.
- Regiones inactivas muestran `not_applicable`; activas muestran al menos el baseline.
- Corte de analisis 2026-07-20 con observacion, disponibilidad, edad y calidad por senal.
- NDMA valida externamente y FEWS NET aporta impacto; ninguno limita la cobertura.
- ML experimental a 30 dias: BSS +23.79%, ECE 0.0544, 2/2 folds mejorados.
- 403 pruebas Python, 60 frontend, lint, typecheck, build y harness gates pasan.

## Siguiente accion

- Revision humana en `/region`, especialmente una ADM1 activa como `adm1-ke-27` y una
  inactiva como Turkana (`adm1-ke-43`).
- Cerrar Sprint 65 solo tras aceptacion; no iniciar el siguiente sprint antes de verla.
