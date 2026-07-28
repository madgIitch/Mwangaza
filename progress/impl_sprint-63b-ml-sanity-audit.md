# Sprint 63B · Implementación

- Target único `same_episode_continues` a 30 días y sentinel estricto pre-2024.
- Pesos de fit y métricas normalizados para que cada episodio aporte uno.
- Imputación con indicadores de ausencia y conteo por fold en el manifiesto.
- Rejilla HGB congelada, selección temporal interna y hazard logístico discreto.
- Platt anual y pooled OOF comparados contra probabilidades raw.
- Bootstrap determinista de 2.000 muestras por episodio y veredicto conservador.
- CLI offline, atómico, con ETA, hashes y run hash reproducible.

La ejecución real produjo 255 predicciones OOF de 29 episodios. El mejor candidato fue
hazard con Brier 0,203102 frente a 0,241388 del baseline, pero quedó `inconclusive` porque
el IC95 del delta termina en +0,002149.
