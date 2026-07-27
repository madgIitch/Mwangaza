# Implementación Sprint 62D.2

## 2026-07-27 - estado: review_pending

- Contratos: hazard fuente y episodios auditados permanecen separados.
- NDMA: índice mensual WebForms oficial, checkpoints, PDFs, hashes, extracción exacta y review queue.
- EM-DAT: CSV registrado local, JSON administrativo realista, evidencia nacional separada y precisión temporal.
- IGAD: ocho estados explícitos; ausencia de serie pública es unknown.
- Auditoría: continuidad versionada, fuentes incompatibles separadas, normales/recuperación fuera de episodios.

Verificación:

- `uv run pytest tests/probabilistic -q`: 42 passed.
- `uv run python -m compileall -q src tests scripts`: passed.
- `uv run ruff check ...`: passed.
- Smoke NDMA junio 2026: 23 indexados, 1 procesado, 1 fase Normal validada, 0 pendientes.
- Smoke auditoría: 0 episodios activos, Kenya observada, 7/8 países unknown.

Pendiente de datos externos: backfill completo a ejecutar por el usuario y CSV EM-DAT registrado no presente en el workspace.

### Reparación de archivo NDMA

El archivo oficial repite dos veces el mismo UUID y los mismos metadatos para
Taita/Taveta en junio de 2020. El parser deduplica únicamente filas idénticas; si un UUID
repite metadatos contradictorios, falla cerrado. Smoke público: 22 boletines únicos.

### Reparación de PDF NDMA truncado

El documento oficial de Laikipia de octubre de 2016 carece de `%%EOF` en
descargas repetidas. El backfill ahora comprueba cabecera y cierre del PDF,
intenta dos descargas de reparación y, si el documento sigue incompleto, lo
registra como `invalid_pdf_after_retries` para revisión y continúa.
