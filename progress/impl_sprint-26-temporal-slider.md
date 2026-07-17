# Sprint 26 - Temporal Slider

## Intento 1

Resultado: OK

- El servicio agrupa payloads ya cargados por `period_end`.
- La seleccion por defecto usa el periodo mas reciente.
- El dashboard embebe el indice temporal y cambia mapa, metricas, alertas, recomendaciones y panel regional en cliente.
- Periodos con cobertura incompleta se marcan como `partial`.
- El cambio de periodo no invoca el loader ni recalcula indicadores.
