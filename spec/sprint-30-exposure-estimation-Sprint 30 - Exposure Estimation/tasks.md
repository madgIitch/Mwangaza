# sprint-30-exposure-estimation · undefined — Tareas

Checklist de implementación. El agente marca [x] al completar; los gates verifican.

- [x] (T1) La metrica publica se denomina `potentially_exposed` y no aparece ningun campo o etiqueta `affected` para la estimacion.  ↔ R1
- [x] (T2) Cada estimacion disponible incluye fuente, ano, resolucion, metodo, calidad y marca `is_demo`.  ↔ R2
- [x] (T3) Los datos demo o sinteticos se etiquetan explicitamente en el contrato y en la UI.  ↔ R3
- [x] (T4) Si se combinan fuentes de anos distintos, la estimacion queda marcada con warning visible y no se presenta como comparable directa.  ↔ R4
- [x] (T5) Sin dataset valido, la cifra queda oculta/no disponible y el sistema no inventa valores.  ↔ R5
- [x] (T6) La UI muestra valores redondeados o rangos coherentes con la precision disponible.  ↔ R6
- [x] Tests que cubran los criterios de aceptación
