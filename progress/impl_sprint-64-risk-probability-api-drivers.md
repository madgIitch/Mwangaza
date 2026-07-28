# Sprint 64 · Implementación

- Añadido `continuation_serving` con bundle hazard, gates regionales y drivers logit.
- Añadido CLI atómico con ETA, evidencia 63B/63, hashes y snapshot materializado.
- Añadido contrato `DroughtContinuationProbability` con estimaciones tipadas.
- Añadido servicio de lectura/verificación y degradación independiente de ML.
- Añadido endpoint público, filtros, paginación, cache y OpenAPI.
- Añadido fixture demo y documentación durable.

La corrida real es reproducible y no usa filas 2024+ para fit. Dos regiones actualmente
activas reciben comparación dual; las fases Normal se representan como `not_applicable`.
