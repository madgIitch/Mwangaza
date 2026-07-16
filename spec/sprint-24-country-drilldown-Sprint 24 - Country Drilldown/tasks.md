# sprint-24-country-drilldown · undefined — Tareas

Checklist de implementación. El agente marca [x] al completar; los gates verifican.

- [x] (T1) Hacer click o usar teclado sobre una región del mapa abre o actualiza el perfil del país seleccionado sin dejar de renderizar el mapa regional.  ↔ R1
- [x] (T2) La navegación o panel Region muestra el análisis funcional del país seleccionado y mantiene un camino claro de vuelta a Overview.  ↔ R2
- [x] (T3) La interacción de región no produce renderizado anidado; existe una sola instancia del shell y del mapa regional en el DOM del componente.  ↔ R3
- [x] (T4) La vista muestra NDVI, lluvia, LST, anomalías, score, calidad, fecha, fuente y período para el país seleccionado.  ↔ R4
- [x] (T5) Cada tarjeta incluye unidad y comparación histórica cuando exista; datos ausentes muestran `No data`, no cero.  ↔ R5
- [x] (T6) Alertas y recomendaciones se recalculan o filtran para la región seleccionada y muestran severidad, evidencia y versión.  ↔ R6
- [x] (T7) Cambiar de país no dispara consultas Earth Engine arbitrarias desde la UI; consume payloads live/cache/demo ya acotados por configuración.  ↔ R7
- [x] (T8) El estado seleccionado puede compartirse mediante parámetros de URL cuando Streamlit lo permita y conserva fallback si el parámetro no es válido.  ↔ R8
- [x] (T9) La UI tiene estados empty, loading y error por región sin traceback, rutas locales ni secretos.  ↔ R9
- [x] (T10) Tests automatizados cubren selección desde mapa, permanencia del mapa renderizado, ausencia de renderizado anidado, panel Region funcional, selector manual, URL state, no-data, alertas por región y ausencia de consultas remotas en interacción.  ↔ R10
- [x] Tests que cubran los criterios de aceptación
