# sprint-19-composite-drought-score · undefined — Tareas

Checklist de implementación. El agente marca [x] al completar; los gates verifican.

- [ ] (T1) El score final queda entre 0 y 100 cuando hay señales obligatorias suficientes.  ↔ R1
- [ ] (T2) NDVI, lluvia y LST contribuyen por separado con pesos configurados que suman 1.  ↔ R2
- [ ] (T3) Si falta una señal opcional, los pesos se renormalizan y queda registrado en metadata.  ↔ R3
- [ ] (T4) Si faltan señales obligatorias o la calidad bloquea alertas, el score es `None` y el nivel `unknown`.  ↔ R4
- [ ] (T5) El resultado incluye contribucion, peso y evidencia de cada indicador usado.  ↔ R5
- [ ] (T6) El mismo snapshot y version de modelo producen el mismo `RiskSnapshot`.  ↔ R6
- [ ] Tests que cubran los criterios de aceptación
