# sprint-19-composite-drought-score · undefined — Requisitos

- name: `Sprint 19 - Composite Drought Score` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-15T16:09:25.994Z

## Contexto



## Requisitos funcionales

R1. El score final queda entre 0 y 100 cuando hay señales obligatorias suficientes.
R2. NDVI, lluvia y LST contribuyen por separado con pesos configurados que suman 1.
R3. Si falta una señal opcional, los pesos se renormalizan y queda registrado en metadata.
R4. Si faltan señales obligatorias o la calidad bloquea alertas, el score es `None` y el nivel `unknown`.
R5. El resultado incluye contribucion, peso y evidencia de cada indicador usado.
R6. El mismo snapshot y version de modelo producen el mismo `RiskSnapshot`.

