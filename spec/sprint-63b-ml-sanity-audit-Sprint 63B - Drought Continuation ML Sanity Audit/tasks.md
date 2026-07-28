# sprint-63b-ml-sanity-audit · undefined — Tareas

Checklist de implementación. El agente marca [x] al completar; los gates verifican.

- [ ] (T1) La auditoría usa exclusivamente `same_episode_continues` a 30 días y rechaza cualquier fila o episodio desde 2024; no descarga ni incorpora fuentes nuevas.  ↔ R1
- [ ] (T2) En fit y métricas cada `episode_id` aporta peso total uno, independientemente de su número de filas conocidas; se reportan también métricas sin ponderar solo como diagnóstico.  ↔ R2
- [ ] (T3) Los pipelines auditados añaden indicadores binarios de missingness después de vectorizar y antes del estimador; el manifiesto registra cuántas columnas indicadoras se crean.  ↔ R3
- [ ] (T4) La rejilla HGB contiene como máximo ocho configuraciones congeladas y se selecciona dentro de cada outer fold usando solo folds walk-forward anteriores al periodo de calibración; ninguna fila de evaluación decide hiperparámetros.  ↔ R4
- [ ] (T5) Se comparan HGB raw, Platt con el año inmediatamente anterior y Platt pooled ajustado solo sobre predicciones OOF históricas anteriores a cada outer evaluation; cada estrategia conserva soporte y razones cuando no es evaluable.  ↔ R5
- [ ] (T6) Se evalúa un `discrete_time_logistic_hazard` que modela recuperación en los siguientes 30 días condicionado a episodio activo e incluye elapsed days/fase/tendencia, features causales e indicadores de missingness.  ↔ R6
- [ ] (T7) El bootstrap usa 2000 remuestreos deterministas de `episode_id`, conserva todas las filas del episodio y produce IC95 del delta de Brier ponderado frente a `phase_survival` para cada candidato.  ↔ R7
- [ ] (T8) Un candidato es `robust_skill` solo si mejora Brier ponderado, el límite superior del IC95 del delta es menor que cero, mejora en al menos dos de tres outer folds y ECE es menor o igual a 0,15; mejora puntual sin esas pruebas es `inconclusive`.  ↔ R8
- [ ] (T9) El CLI muestra ETA y escribe config, selección por fold, OOF, métricas, bootstrap, veredicto y manifiesto atómicos con hashes y run hash determinista bajo `data/models/drought-continuation-ml-audit/`.  ↔ R9
- [ ] (T10) Tests cubren pesos por episodio, missing indicators, tuning sin leakage, calibración anual/pooled, hazard logístico, bootstrap clusterizado, IC/veredicto, sentinel 2024 y reproducibilidad; pasan los gates del repo.  ↔ R10
- [ ] Tests que cubran los criterios de aceptación
