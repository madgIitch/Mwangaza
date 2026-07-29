# Sprint 65 - Implementacion

- Estado satelital homogeneo para 121 ADM1 con meteorologia, vegetacion y humedad del suelo.
- Activacion y recuperacion con dos dekads consecutivos; episodios y targets causales.
- Backtest walk-forward 2022/2023, episodios purgados y bootstrap por episodio.
- NDMA como validacion externa; FEWS NET como evidencia de impacto exclusivamente.
- Materializador reproducible con ETA, hashes, configuracion resuelta y gates de cobertura.
- API de 484 resultados paginada completamente por el frontend.
- UI y Reports distinguen target satelital, abstencion, fecha de analisis, fecha de consulta y frescura por senal.
- La cabecera distingue `LIVE QUERY` de la ventana efectiva de observacion.

Corrida real: 102608 features, 1468 muestras, 1109 filas de entrenamiento, 65 regiones
de entrenamiento, 121/121 ADM1, 47/47 Kenya, 11 activas, 484/484 resultados y
`analysis_as_of=2026-07-20`. Run hash:
`sha256:2e2fb19e4d490d62a2ece1ccef33b7f705b30fc3a2fcc7d482b0b458e349a7b2`.

El ML experimental de 30 dias obtuvo BSS ponderado por episodio +23.79%, ECE 0.0544,
mejoro 2/2 folds y su IC95 del delta Brier fue [-0.0765, -0.0365]. El estado contractual
sigue siendo `inconclusive` y no operacional.

Durante revision se anadio la capa `Persistent episodes` al mapa ADM1. La vista mantiene
la seleccion, cuenta episodios activos/evaluados por pais, usa una leyenda binaria propia
y muestra duracion y probabilidades de 30 dias en el tooltip del territorio activo.
