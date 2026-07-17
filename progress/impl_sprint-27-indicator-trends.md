# Sprint 27 - Indicator Trends

## Intento 1

Resultado: OK

- Live GEE carga un conjunto acotado de cortes recientes para construir series.
- El dashboard deriva tendencias de NDVI, rainfall y LST desde payloads ya cargados.
- Los graficos muestran unidad, fuente, baseline documentado, gaps y detalle de calidad/anomalia por punto.
- La cantidad de puntos live queda limitada por `MWANGAZA_LIVE_TREND_POINTS` con maximo 8.
