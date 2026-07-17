# Review - sprint-30-exposure-estimation

## Checkpoints

- [x] Contrato usa `potentially_exposed` y rechaza terminologia `affected`.
- [x] Metadata obligatoria: fuente, ano, resolucion, metodo, calidad e `is_demo`.
- [x] UI muestra demo/sintetico y warnings de mezcla de anos.
- [x] Dataset invalido no muestra cifra inventada.
- [x] Gates automatizados pasan.

## Siguiente accion

- Smoke visual del dashboard: confirmar que la tarjeta `potentially_exposed` se entiende como exposicion potencial y no como impacto medido. Cerrar con `node .harness/spec.mjs done sprint-30-exposure-estimation` si pasa.
