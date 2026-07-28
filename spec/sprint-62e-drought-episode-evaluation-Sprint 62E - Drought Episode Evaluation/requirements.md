# sprint-62e-drought-episode-evaluation · undefined — Requisitos

- name: `Sprint 62E - Drought Episode Evaluation` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-28T03:18:13.167Z

## Contexto



## Requisitos funcionales

R1. Solo observaciones `drought_hazard_event` validadas generan target: Alert/Alarm/Emergency son 1, Normal/Recovery son 0 y cualquier periodo sin cobertura oficial es unknown.
R2. Episodios activos de una región y fuente separados por como máximo 32 días comparten `episode_id`; 33 días abren otro episodio, y se conservan onset, fin, duración y censura.
R3. Los splits walk-forward usan cortes temporales globales, asignan cada episodio completo a un único fold y purgan filas fronterizas; una corrida falla si un `episode_id` aparece en train y test.
R4. Cada candidato produce predicciones OOF trazables para horizontes de 10, 20 y 30 días sin usar features ni etiquetas posteriores a `as_of`; periodos unknown no entrenan ni puntúan.
R5. La evaluación convierte predicciones con umbral 0,5 en episodios predichos usando la misma continuidad y matching uno-a-uno por solapamiento, y reporta event recall, falsas alarmas, precisión/F1, lead time, error de onset, duración y recovery.
R6. Métricas de onset omiten left-censored y métricas de recovery/duración omiten right-censored; el reporte conserva denominadores y razones de métrica no disponible.
R7. Brier OOF por fila se reporta como diagnóstico sobre exactamente las mismas filas conocidas para ML, persistencia, climatología estacional y frecuencia histórica, pero no sustituye las métricas por episodio.
R8. Un modelo ML queda `episode_skill_eligible` solo si mejora estrictamente el Brier y el event F1 del mejor baseline, no aumenta las falsas alarmas y dispone de al menos dos episodios evaluables en test; en otro caso queda rechazado con razón estructurada.
R9. El CLI consume artefactos locales con hashes, muestra progreso/ETA y escribe predicciones, episodios, métricas y manifiesto canónicos; repetir con las mismas entradas/configuración produce el mismo hash salvo el timestamp externo al contenido evaluado.
R10. Tests offline cubren episodios largos, gaps 32/33, censura, regiones simultáneas, unknown, matching, falsos positivos, split leakage, baselines y determinismo; la ejecución real informa cobertura y abstención sin publicar probabilidades.

