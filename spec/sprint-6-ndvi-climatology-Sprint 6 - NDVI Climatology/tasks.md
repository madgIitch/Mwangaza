# sprint-6-ndvi-climatology - Tareas

Checklist de implementacion. El agente marca [x] al completar; los gates verifican.

- [x] (T1) `compute_ndvi_climatology(...)` devuelve un `Baseline` valido para `indicator="ndvi"` usando solo anos dentro de la ventana historica configurada e incluye en metadata la lista `effective_years`. -> R1
- [x] (T2) El periodo actual nunca se incluye en el baseline; si un ano configurado coincide con el ano del periodo actual se excluye y aparece en metadata `excluded_years`. -> R2
- [x] (T3) Con anos efectivos suficientes se calculan `mean`, `median`, `stddev` poblacional y `observations` sobre valores NDVI finitos. -> R3
- [x] (T4) Si los anos efectivos validos son menos que `min_years`, el resultado usa `quality_flag="insufficient_history"` y estadisticos `None` sin llamar a ese caso `no_data`. -> R4
- [x] (T5) Cambiar la ventana historica, la temporada o la coleccion NDVI cambia `metadata.baseline_version` de forma determinista. -> R5
- [x] (T6) Los tests cubren temporadas que cruzan cambio de ano, meses de distinta duracion, ventanas historicas inclusivas y ausencia de llamadas Earth Engine reales. -> R6
- [x] Tests que cubran los criterios de aceptacion
