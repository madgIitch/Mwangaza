# sprint-57-overview-completion · undefined — Requisitos

- name: `Sprint 57 - Overview Completion` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-21T15:13:07.295Z

## Contexto



## Requisitos funcionales

R1. `/overview` y `/` renderizan el mismo cockpit independiente, sin hashes ni autoscroll, y conservan navegación por rutas de página.
R2. El mapa usa exclusivamente `ui_geometry` procesada; regiones `no_data`, inválidas o ausentes permanecen grises y sin geometría aparece un fallback tabular explícito.
R3. Home restaura el encuadre IGAD, zoom opera entre 1× y 4× y el selector alterna `Risk` y `Data quality` sobre datos ya cargados, sin consultas GEE.
R4. Cada región evaluada ofrece tooltip y foco accesibles con nombre, score, nivel, indicadores disponibles, calidad, fuente y periodo; seleccionar mapa o selector actualiza el mismo contexto regional.
R5. Las alertas exponen identificador estable; `View details` abre `/alerts/<alert_id>` y el listado global conserva `region`, `period` y `status=active` en la query.
R6. Una alerta existente muestra detalle, evidencia, calidad, periodo y acción; una inexistente produce un estado 404 accesible y saneado.
R7. El PDF ejecutivo se descarga desde un endpoint real usando sólo el snapshot procesado de región/periodo, con MIME, `Content-Disposition` y nombre determinista; un fallo no descarga un archivo vacío.
R8. CSV y JSON se descargan desde un endpoint real para la región/periodo visibles, conservan nulls, omiten geometría por defecto, aplican límite y usan nombres/cabeceras seguras.
R9. Las tarjetas sólo muestran delta cuando existe comparación estacional válida; sin ella muestran `No comparison yet` y nunca comparan ventanas incompatibles.
R10. Las tendencias de cualquier región IGAD seleccionada muestran 12–24 puntos disponibles contra baseline, con fechas, escala, tooltip, gaps explícitos y fallback accesible en low-bandwidth. Si el lote regional GEE falla, la carga reintenta cada país de forma aislada sin reducir la cobertura a la región inicial.
R11. El locale Somali (`so`) cubre todo texto visible de Overview y navegación; EN/SW/SO se presentan como selector segmentado y ES permanece disponible por compatibilidad sin traducir valores técnicos ni fuentes.
R12. Cuenta y notificaciones permanecen etiquetadas como no disponibles y no son interactivas hasta contar con contrato aprobado.
R13. Demo funciona sin red/GEE y conserva `is_demo`, `reference_date` y `snapshot_id`; live/cache no mezclan fixtures y mantienen fuente/frescura visibles.
R14. Low-bandwidth conserva región, riesgos, alertas, métricas, deltas, tendencias, recomendaciones y acciones de descarga en texto/tablas sin SVG ni animaciones.
R15. Tests API/frontend verifican controles, rutas, descargas, idiomas y degradación; ninguna interacción de Overview inicia Earth Engine desde el navegador.
R16. El tema oscuro conserva una jerarquía legible en navegación, estados, alertas, cobertura regional, controles y acciones; evita superficies blancas accidentales y textos de bajo contraste sin alterar los colores semánticos del mapa.

## Restricciones

- **error_states:** Degradación independiente y sin datos inventados.
- **auth_secrets:** Archivos desde snapshots; sin input ni secretos GEE.
- **rollback_compat:** Rutas previas preservadas y Reports Center fuera de alcance.
