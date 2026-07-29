# sprint-65-probability-ui-integration - Tareas

- [x] (T1) Derivar una condicion satelital homogenea para exactamente 121 ADM1 con configuracion versionada y sin depender de NDMA. -> R1
- [x] (T2) Calcular estado y episodios solo con senales disponibles, conservando fechas, edad, calidad y dos dekads de histeresis. -> R2
- [x] (T3) Ejecutar backtest walk-forward causal, abrir el futuro solo para scoring y no dividir episodios entre train y test. -> R3
- [x] (T4) Usar NDMA solo como validacion externa y FEWS NET solo como evidencia de impacto. -> R4
- [x] (T5) Materializar 121 ADM1, 47 de Kenya y exactamente 484 resultados; inactivas `not_applicable`, activas con baseline disponible. -> R5
- [x] (T6) Servir ML experimental a 30 dias solo tras sus gates y mantener la referencia separada en los cuatro horizontes. -> R6
- [x] (T7) Alcanzar el ultimo corte disponible sin forzar una fecha minima comun; corrida real `analysis_as_of=2026-07-20`. -> R7
- [x] (T8) Separar query, analisis y observacion por senal; verificar hashes sin ejecutar GEE, training o escrituras en request. -> R8
- [x] (T9) Mostrar continuidad por ID exacto en cualquier ADM1, con fechas/calidad y abstencion correcta. -> R9
- [x] (T10) Conservar semantica y cobertura en low-bandwidth y Reports. -> R10
- [x] (T11) Mantener demo determinista y separacion cerrada entre artefactos demo y reales. -> R11
- [x] (T12) Cubrir dominio, fuga temporal, contratos, API, frontend, reportes y seguridad. -> R12
- [x] Tests que cubren los criterios de aceptacion.
- [x] (T13) Anadir al mapa ADM1 las capas `Current risk` y `Persistent episodes`, con recuento, leyenda, tooltip y seleccion estable. -> R13
- [x] (T14) Anadir `Persistent episodes` a Overview con agregacion por pais y deep-link al detalle regional. -> R14
- [x] (T15) Retirar Admin y Reports de la interfaz publica sin romper Overview, Regions, Active alerts ni las exportaciones CSV/JSON. -> R15
