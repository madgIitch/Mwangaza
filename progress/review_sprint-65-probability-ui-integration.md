# Sprint 65 - Revision

Estado: `review_pending`.

- [x] Spec correctivo aprobado antes de implementar (`77a8816`).
- [x] Cobertura real 121/121, 47/47 Kenya y 484/484 resultados.
- [x] Inactivas `not_applicable`; las 11 activas conservan probabilidad historica.
- [x] ML a 30 dias separado del baseline y marcado experimental/no operacional.
- [x] Backtest oculta datos futuros por `available_at` y purga episodios fronterizos.
- [x] NDMA es validacion externa y FEWS NET no genera estado ni target.
- [x] Corte 2026-07-20 y frescura individual por senal expuestos en API/UI.
- [x] Frontend pagina los 484 resultados y diferencia consulta live de observacion.
- [x] Low-bandwidth y Reports conservan target, evidencia y abstencion.
- [x] API local: 484 total, 121 ADM1, 47 Kenya; `adm1-ke-27` disponible y `adm1-ke-43` no aplicable.
- [x] 403 pruebas Python y 60 frontend pasan.
- [x] Lint, typecheck, build y gates del harness pasan.
- [x] El mapa alterna riesgo/episodios y conserva pais, periodo y ADM1 seleccionada.
- [x] La capa de episodios muestra recuento, fecha, leyenda y tooltip de continuidad.
- [ ] Revision visual humana en `/region` antes de cerrar el sprint.

La inspeccion visual automatizada no se ejecuto porque no habia un navegador conectado
en esta sesion. El sprint no se cierra hasta la aceptacion humana.
