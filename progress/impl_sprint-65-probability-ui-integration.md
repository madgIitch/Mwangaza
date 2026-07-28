# Sprint 65 · Implementación

- Añadido contrato TypeScript para la respuesta de continuidad y carga tolerante a fallo.
- Añadido módulo `DroughtContinuation` compacto al inspector ADM1.
- Añadidos cuatro horizontes, comparación dual, drivers, skill, IC95 y abstención.
- Añadida representación equivalente para low-bandwidth.
- Reutilizado el fixture versionado de Sprint 64 y añadidas ADM1 demo seleccionables.
- Añadida sección de continuidad a preview, HTML y PDF de reportes.
- La generación de informes lee solo el snapshot materializado y no consulta GEE.

La composición sigue la jerarquía existente: el mapa continúa siendo el ancla y la
probabilidad es contexto secundario dentro del inspector, no un dashboard adicional.
