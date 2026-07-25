# sprint-62c-adm1-antecedent-signals · undefined — Tareas

Checklist de implementación. El agente marca [x] al completar; los gates verifican.

- [ ] (T1) Incluye exactamente las 121 unidades ADM1 versionadas y conserva parent country, boundary source/version y geometría.  ↔ R1
- [ ] (T2) SPI 1/3/6 usa solo lluvia observada hasta as_of, ventana mensual explícita y climatología pre-corte; no existe centrado con datos futuros.  ↔ R2
- [ ] (T3) SPEI usa `CSIC/SPEI/2_11` con bandas 1/3/6 meses, observed_at y licencia CC-BY-4.0 documentada; periodos posteriores a disponibilidad quedan null.  ↔ R3
- [ ] (T4) Humedad de suelo y ET usan `NASA/FLDAS/NOAH01/C/GL/M/V001`, unidades/escala verificadas, cadencia mensual y términos NASA documentados.  ↔ R4
- [ ] (T5) Déficit acumulado de lluvia y NDVI persistence/slope se calculan con ventanas contiguas y null reason si hay gaps.  ↔ R5
- [ ] (T6) Forecast usa `ECMWF/NRT_FORECAST/IFS/OPER`, creación y lead time explícitos, CC-BY-4.0, y nunca aparece antes de 2024-11-12 ni como observación.  ↔ R6
- [ ] (T7) Backfill agrupa regiones en consultas acotadas, es reanudable, muestra progreso/ETA y no versiona datos descargados.  ↔ R7
- [ ] (T8) Cada feature conserva source collection, source version, observed_at, age/lead, quality y disponibilidad temporal.  ↔ R8
- [ ] (T9) Tests offline cubren 121 ADM1, anti-lookahead, SPI, ventanas/gaps, unidades, forecast availability, batching, resume y hashes.  ↔ R9
- [ ] (T10) Smoke GEE real valida al menos un ADM1 de Kenya y uno de Somalia sin exponer secretos.  ↔ R10
- [ ] Tests que cubran los criterios de aceptación
