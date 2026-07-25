# sprint-62c-adm1-antecedent-signals · undefined — Requisitos

- name: `Sprint 62C - ADM1 Antecedent Drought Signals` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-25T13:20:57.623Z

## Contexto



## Requisitos funcionales

R1. Incluye exactamente las 121 unidades ADM1 versionadas y conserva parent country, boundary source/version y geometría.
R2. SPI 1/3/6 usa solo lluvia observada hasta as_of, ventana mensual explícita y climatología pre-corte; no existe centrado con datos futuros.
R3. SPEI usa `CSIC/SPEI/2_11` con bandas 1/3/6 meses, observed_at y licencia CC-BY-4.0 documentada; periodos posteriores a disponibilidad quedan null.
R4. Humedad de suelo y ET usan `NASA/FLDAS/NOAH01/C/GL/M/V001`, unidades/escala verificadas, cadencia mensual y términos NASA documentados.
R5. Déficit acumulado de lluvia y NDVI persistence/slope se calculan con ventanas contiguas y null reason si hay gaps.
R6. Forecast usa `ECMWF/NRT_FORECAST/IFS/OPER`, creación y lead time explícitos, CC-BY-4.0, y nunca aparece antes de 2024-11-12 ni como observación.
R7. Backfill agrupa regiones en consultas acotadas, es reanudable, muestra progreso/ETA y no versiona datos descargados.
R8. Cada feature conserva source collection, source version, observed_at, age/lead, quality y disponibilidad temporal.
R9. Tests offline cubren 121 ADM1, anti-lookahead, SPI, ventanas/gaps, unidades, forecast availability, batching, resume y hashes.
R10. Smoke GEE real valida al menos un ADM1 de Kenya y uno de Somalia sin exponer secretos.

