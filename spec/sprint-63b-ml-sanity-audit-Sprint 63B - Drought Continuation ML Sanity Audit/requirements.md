# sprint-63b-ml-sanity-audit · undefined — Requisitos

- name: `Sprint 63B - Drought Continuation ML Sanity Audit` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-28T15:53:09.976Z

## Contexto



## Requisitos funcionales

R1. La auditoría usa exclusivamente `same_episode_continues` a 30 días y rechaza cualquier fila o episodio desde 2024; no descarga ni incorpora fuentes nuevas.
R2. En fit y métricas cada `episode_id` aporta peso total uno, independientemente de su número de filas conocidas; se reportan también métricas sin ponderar solo como diagnóstico.
R3. Los pipelines auditados añaden indicadores binarios de missingness después de vectorizar y antes del estimador; el manifiesto registra cuántas columnas indicadoras se crean.
R4. La rejilla HGB contiene como máximo ocho configuraciones congeladas y se selecciona dentro de cada outer fold usando solo folds walk-forward anteriores al periodo de calibración; ninguna fila de evaluación decide hiperparámetros.
R5. Se comparan HGB raw, Platt con el año inmediatamente anterior y Platt pooled ajustado solo sobre predicciones OOF históricas anteriores a cada outer evaluation; cada estrategia conserva soporte y razones cuando no es evaluable.
R6. Se evalúa un `discrete_time_logistic_hazard` que modela recuperación en los siguientes 30 días condicionado a episodio activo e incluye elapsed days/fase/tendencia, features causales e indicadores de missingness.
R7. El bootstrap usa 2000 remuestreos deterministas de `episode_id`, conserva todas las filas del episodio y produce IC95 del delta de Brier ponderado frente a `phase_survival` para cada candidato.
R8. Un candidato es `robust_skill` solo si mejora Brier ponderado, el límite superior del IC95 del delta es menor que cero, mejora en al menos dos de tres outer folds y ECE es menor o igual a 0,15; mejora puntual sin esas pruebas es `inconclusive`.
R9. El CLI muestra ETA y escribe config, selección por fold, OOF, métricas, bootstrap, veredicto y manifiesto atómicos con hashes y run hash determinista bajo `data/models/drought-continuation-ml-audit/`.
R10. Tests cubren pesos por episodio, missing indicators, tuning sin leakage, calibración anual/pooled, hazard logístico, bootstrap clusterizado, IC/veredicto, sentinel 2024 y reproducibilidad; pasan los gates del repo.

