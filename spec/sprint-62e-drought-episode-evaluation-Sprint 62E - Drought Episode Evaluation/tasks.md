# sprint-62e-drought-episode-evaluation · Sprint 62E - Drought Episode Evaluation — Tareas

Checklist de implementación completado y verificado por gates.

- [x] (T1) Solo observaciones `drought_hazard_event` validadas generan target; unknown no se convierte en negativo. ↔ R1
- [x] (T2) La continuidad de episodios usa gap máximo de 32 días y conserva censura. ↔ R2
- [x] (T3) Los splits globales mantienen cada `episode_id` completo en un único fold. ↔ R3
- [x] (T4) Los cinco candidatos producen predicciones OOF causales a 10, 20 y 30 días. ↔ R4
- [x] (T5) El matching uno-a-uno reporta recall, precisión/F1, falsas alarmas, lead, onset, duración y recovery. ↔ R5
- [x] (T6) Las métricas omiten extremos censurados y conservan denominadores. ↔ R6
- [x] (T7) Todos los candidatos reportan Brier sobre las mismas filas conocidas. ↔ R7
- [x] (T8) El gate exige mejorar Brier y F1 sin aumentar falsas alarmas. ↔ R8
- [x] (T9) El CLI muestra ETA y genera artefactos canónicos enlazados por hash. ↔ R9
- [x] (T10) Tests offline y corrida real cubren los criterios de aceptación. ↔ R10
- [x] Tests que cubren los criterios de aceptación.
