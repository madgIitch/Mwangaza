# sprint-30-exposure-estimation · undefined — Requisitos

- name: `Sprint 30 - Exposure Estimation` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-17T11:25:47.010Z

## Contexto



## Requisitos funcionales

R1. La metrica publica se denomina `potentially_exposed` y no aparece ningun campo o etiqueta `affected` para la estimacion.
R2. Cada estimacion disponible incluye fuente, ano, resolucion, metodo, calidad y marca `is_demo`.
R3. Los datos demo o sinteticos se etiquetan explicitamente en el contrato y en la UI.
R4. Si se combinan fuentes de anos distintos, la estimacion queda marcada con warning visible y no se presenta como comparable directa.
R5. Sin dataset valido, la cifra queda oculta/no disponible y el sistema no inventa valores.
R6. La UI muestra valores redondeados o rangos coherentes con la precision disponible.

