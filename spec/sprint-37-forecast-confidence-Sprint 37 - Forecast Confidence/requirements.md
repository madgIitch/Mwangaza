# sprint-37-forecast-confidence · undefined — Requisitos

- name: `Sprint 37 - Forecast Confidence` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-17T11:50:42.423Z

## Contexto



## Requisitos funcionales

R1. Cada punto forecast evaluado incluye intervalo inferior y superior.
R2. El modelo solo es elegible si supera baseline ingenuo bajo MAE configurado.
R3. Una alerta preventiva requiere caida prevista y confianza minima.
R4. La UI/diagnostico describe forecast como estimacion, no hecho.
R5. Modelos no elegibles quedan visibles en diagnostics pero no disparan alertas.
R6. La razon de elegibilidad o rechazo se conserva en el resultado.

