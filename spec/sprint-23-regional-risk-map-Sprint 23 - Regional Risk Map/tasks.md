# sprint-23-regional-risk-map - Sprint 23 - Regional Risk Map - Tareas

Checklist de implementacion. El agente marca [x] al completar; los gates verifican.

- [x] (T1) Los colores del mapa representan exactamente los niveles `green`, `yellow`, `orange`, `red` y `unknown`, con una leyenda visible que explica cada nivel. -> R1
- [x] (T2) Cada tooltip de region muestra nombre de region, score, nivel de riesgo, periodo y calidad de datos sin exponer metadata privada ni trazas internas. -> R2
- [x] (T3) Una region sin snapshot valido, con score no finito o con calidad bloqueante aparece como `unknown`, no como `green`. -> R3
- [x] (T4) El mapa usa las geometries `ui_geometry` del catalogo regional como GeoJSON WGS84 y no mezcla geometria analitica con geometria de UI. -> R4
- [x] (T5) La seleccion de una region actualiza el estado visual de region seleccionada/navegacion manteniendo el resto del dashboard renderizable. -> R5
- [x] (T6) El mapa se renderiza de forma determinista con fixtures/cache local en tests automatizados, sin Streamlit instalado, red ni Earth Engine. -> R6
- [x] (T7) El dashboard consulta GEE directamente en modo `live` cuando hay credenciales configuradas, usando una region/periodo acotados y cayendo a cache/demo si GEE no esta disponible. -> R7
- [x] (T8) Existe un script en `smoke_tests/` que usa la misma ruta live GEE con credenciales tomadas solo de variables de entorno, genera payloads saneados de riesgo/indicadores y escribe la cache consumida por el dashboard. -> R8
- [x] (T9) Los tests o validaciones del smoke verifican que los payloads/cache no contienen campos o valores de secretos como `private_key`, `service_account`, `token`, `secret` o `password`. -> R9
- [x] Tests que cubran los criterios de aceptacion
