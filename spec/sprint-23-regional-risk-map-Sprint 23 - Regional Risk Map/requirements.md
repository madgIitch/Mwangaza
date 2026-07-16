# sprint-23-regional-risk-map · undefined — Requisitos

- name: `Sprint 23 - Regional Risk Map` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-16T16:48:40.021Z

## Contexto



## Requisitos funcionales

R1. Los colores del mapa representan exactamente los niveles `green`, `yellow`, `orange`, `red` y `unknown`, con una leyenda visible que explica cada nivel.
R2. Cada tooltip de region muestra nombre de region, score, nivel de riesgo, periodo y calidad de datos sin exponer metadata privada ni trazas internas.
R3. Una region sin snapshot valido, con score no finito o con calidad bloqueante aparece como `unknown`, no como `green`.
R4. El mapa usa las geometries `ui_geometry` del catalogo regional como GeoJSON WGS84 y no mezcla geometria analitica con geometria de UI.
R5. La seleccion de una region actualiza el estado visual de region seleccionada/navegacion manteniendo el resto del dashboard renderizable.
R6. El mapa se renderiza de forma determinista con fixtures/cache local en tests automatizados, sin Streamlit instalado, red ni Earth Engine.
R7. El dashboard consulta GEE directamente en modo `live` cuando hay credenciales configuradas, usando una region/periodo acotados y cayendo a cache/demo si GEE no esta disponible.
R8. Existe un script en `smoke_tests/` que usa la misma ruta live GEE con credenciales tomadas solo de variables de entorno, genera payloads saneados de riesgo/indicadores y escribe la cache consumida por el dashboard.
R9. Los tests o validaciones del smoke verifican que los payloads/cache no contienen campos o valores de secretos como `private_key`, `service_account`, `token`, `secret` o `password`.
