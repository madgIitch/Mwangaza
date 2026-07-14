# sprint-6-ndvi-climatology · undefined — Requisitos

- name: `Sprint 6 - NDVI Climatology` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-14T14:54:25.708Z

## Contexto



## Requisitos funcionales

R1. `compute_ndvi_climatology(...)` devuelve un `Baseline` valido para `indicator="ndvi"` usando solo años dentro de la ventana histórica configurada e incluye en metadata la lista `effective_years`.
R2. El período actual nunca se incluye en el baseline; si un año configurado coincide con el año del período actual se excluye y aparece en metadata `excluded_years`.
R3. Con años efectivos suficientes se calculan `mean`, `median`, `stddev` poblacional y `observations` sobre valores NDVI finitos.
R4. Si los años efectivos válidos son menos que `min_years`, el resultado usa `quality_flag="insufficient_history"` y estadísticos `None` sin llamar a ese caso `no_data`.
R5. Cambiar la ventana histórica, la temporada o la colección NDVI cambia `metadata.baseline_version` de forma determinista.
R6. Los tests cubren temporadas que cruzan cambio de año, meses de distinta duración, ventanas históricas inclusivas y ausencia de llamadas Earth Engine reales.

