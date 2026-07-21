# Revisión Sprint 56 - Region Explorer Completion

Veredicto: `review_pending`.

El contrato API publica perfiles regionales completos y cortes temporales procesados para demo/live: geometría, métricas, unidades piloto, contribuciones, tendencias, comparación estacional y recomendaciones. Region Explorer consume esos datos, ofrece controles funcionales y deep-link filtrado a alertas sin iniciar GEE desde el navegador.

Validación:

- Smoke GEE real para Somalia: 19/19 checks, `mode_live=true`, `not_demo=true`.
- 300 tests Python y 40 tests frontend.
- Typecheck, lint, build y gates del harness.

Smoke humano pendiente: revisar `/region?api=1` en modo live y low-bandwidth.

La primera revisión visual fue rechazada: el mapa reutilizaba los bounding boxes de prototipo y la composición inferior producía paneles altos con espacio muerto. La corrección sustituye esos rectángulos por ADM1 reales de geoBoundaries para los ocho países, separa la capa administrativa de las observaciones API y normaliza el winding de polígonos.

La propuesta C reorganiza ahora la página como un atlas operacional: mapa e inspector territorial forman el workspace principal; mapa, selector y ranking comparten la unidad activa; el ranking queda plegado y con scroll interno; tendencias nacionales declaran su alcance; y low-bandwidth conserva selección y detalle sin SVG. La activación de áreas evaluadas admite ratón y teclado.

El segundo pase visual sustituye barras sin escala por líneas de anomalía con eje cero, fechas y tooltip; agrupa pesos en una barra apilada neutral; comparte badges entre mapa, inspector y ranking; destaca el top tres; agrupa historia por año con deltas compactos; retira la falsa affordance de metodología; y mantiene una sola acción principal porque el contrato aún no incluye prioridad ni horizonte.

La serie live queda ampliada a 24 agregados mensuales nacionales por defecto y configurable entre 12 y 24. Todos los meses y países se resuelven en un único lote GEE; ADM1 permanece limitado al periodo actual. Los payloads de tendencia no aparecen como periodos operativos ni alimentan la comparación estacional. Sin baseline de fuente, el shell publica la media de valores mensuales disponibles con etiqueta explícita.

Smoke GEE real: PASS 19/19 en aproximadamente 16 s, con horizonte mensual válido, baseline en todos los puntos no-gap, suma nacional explicada y contribuciones propias para 121/121 ADM1 concluyentes.

`Why this region is at risk` deja de mostrar pesos fijos: cada segmento representa puntos efectivos del composite y detalla score normalizado, peso, fuente y calidad. El contrato ADM1 incluye el mismo desglose; si falta, la PWA muestra un estado pendiente y nunca hereda la explicación nacional.

La conexión de automatización visual no encontró un navegador disponible en esta sesión. El build y las verificaciones estructurales/responsive pasan, pero la segunda revisión visual humana sigue pendiente y T21 permanece abierto hasta esa aprobación.
