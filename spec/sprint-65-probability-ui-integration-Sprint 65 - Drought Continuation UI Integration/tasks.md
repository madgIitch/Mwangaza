# sprint-65-probability-ui-integration · undefined — Tareas

Checklist de implementación. El agente marca [x] al completar; los gates verifican.

- [ ] (T1) Region Explorer incorpora un único módulo `Drought continuation` dentro del workspace existente y solo muestra probabilidades cuando la unidad seleccionada tiene una fase oficial activa; no crea otra ruta ni un velocímetro dominante.  ↔ R1
- [ ] (T2) El usuario puede elegir 30, 60, 90 y 180 días y ve periodo objetivo, fase actual, método, calidad, skill y hasta tres drivers o evidencias cuando están disponibles.  ↔ R2
- [ ] (T3) A 30 días se muestran juntas, sin fusionarlas, `Experimental ML prediction` y `Historical reference`; la primera indica `Inconclusive validation` y `Not for operational use`.  ↔ R3
- [ ] (T4) A 60, 90 y 180 días solo se muestra `Historical reference` y nunca `AI prediction` ni un hueco numérico reservado para ML.  ↔ R4
- [ ] (T5) El copy dice que se estima si el mismo episodio activo continuará; no promete inicio de sequía, duración exacta, impacto humano ni certeza operativa.  ↔ R5
- [ ] (T6) Si ML no está disponible, su espacio explica el motivo mientras la referencia puede seguir visible; `unavailable` y `not_applicable` nunca muestran 0 %.  ↔ R6
- [ ] (T7) Los drivers ML se presentan como asociaciones, mientras fase y tiempo transcurrido del baseline se presentan como evidencia descriptiva; ambos conservan método y periodo.  ↔ R7
- [ ] (T8) Reports incorpora ambas estimaciones de 30 días con `as_of`, fase, artefacto/skill, intervalo, calidad y disclaimer; en horizontes largos incorpora solo la referencia y `unavailable` se documenta como abstención.  ↔ R8
- [ ] (T9) Navegador y generación de reportes no entrenan, calibran ni consultan GEE; consumen exclusivamente API o snapshots materializados y un fallo del módulo no bloquea las superficies existentes.  ↔ R9
- [ ] (T10) Low-bandwidth conserva la comparación dual a 30 días y la referencia o abstención en horizontes largos, con fase, método, skill, calidad, evidencia y disclaimer en texto o tabla; no traduce IDs, versiones ni reason codes.  ↔ R10
- [ ] (T11) La integración funciona en demo offline con el fixture versionado de Sprint 64 y selecciona probabilidades por ID exacto de región, sin heredar datos nacionales o de otra ADM1.  ↔ R11
- [ ] (T12) Tests frontend y de reportes cubren comparación ML/referencia, ML unavailable con referencia disponible, `not_applicable`, cuatro horizontes, lenguaje no causal, low-bandwidth, demo offline y ausencia de entrenamiento/GEE.  ↔ R12
- [ ] Tests que cubran los criterios de aceptación
