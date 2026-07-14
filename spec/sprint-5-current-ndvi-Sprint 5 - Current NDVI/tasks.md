# sprint-5-current-ndvi - Tareas

Checklist de implementacion. El agente marca [x] al completar; los gates verifican.

- [x] (T1) `compute_current_ndvi(...)` devuelve un `IndicatorObservation` valido con `indicator="ndvi"`, `unit="index"`, `source` igual a la coleccion usada y `value` escalado dentro de `[-1.0, 1.0]` cuando hay pixeles validos. -> R1
- [x] (T2) El procesamiento excluye pixeles sin QA valida o sin valor NDVI y los tests verifican que solo los pixeles validos contribuyen al promedio. -> R2
- [x] (T3) Si una region/periodo no tiene pixeles validos, el resultado usa `quality_flag="no_data"`, `value=None` y `valid_pixel_fraction=0.0`, nunca `0` como NDVI. -> R3
- [x] (T4) La coleccion NDVI puede cambiarse mediante `NdviCollectionConfig` y por configuracion externa `MWANGAZA_NDVI_COLLECTION` sin modificar codigo de procesamiento. -> R4
- [x] (T5) El adaptador recibe exactamente la geometria de la region seleccionada y las fechas solicitadas; los tests con fake adapter verifican esos limites de consulta. -> R5
- [x] (T6) El resultado persiste en metadata `valid_pixel_fraction`, `valid_pixel_count`, `total_pixel_count`, `collection_id`, `scale_factor` y periodo real observado. -> R6
- [x] Tests que cubran los criterios de aceptacion
