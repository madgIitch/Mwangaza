# sprint-65-probability-ui-integration · undefined — Tareas

Checklist de implementación. El agente marca [x] al completar; los gates verifican.

- [ ] (T1) El pipeline deriva una condición de sequía satelital homogénea para exactamente las 121 ADM1 del catálogo IGAD mediante una configuración versionada basada en familias meteorológica, vegetación y humedad del suelo; no depende de que exista una etiqueta NDMA.  ↔ R1
- [ ] (T2) El estado satelital y sus episodios se calculan únicamente con señales `available_at <= as_of`, conservan `observed_at`, `available_at`, `age_days`, calidad y versión por señal, y aplican dos dekads consecutivos para activar y dos para cerrar un episodio.  ↔ R2
- [ ] (T3) El backtest es walk-forward: para cada predicción solo ajusta transformaciones, estado, episodios, baseline y modelo con información disponible antes del corte; el target en 30/60/90/180 días se abre únicamente para scoring posterior y los episodios no se dividen entre train y test.  ↔ R3
- [ ] (T4) NDMA se usa solo como validación externa oficial y publica cobertura/concordancia separadas; nunca limita regiones ni genera el target satelital. FEWS NET permanece tipado como evidencia de impacto alimentario y nunca crea estados o episodios de sequía.  ↔ R4
- [ ] (T5) La materialización real evalúa las 121 ADM1 y escribe exactamente 484 resultados ordenados, incluidos los 47 ADM1 de Kenya. Una región inactiva devuelve `not_applicable`; toda región activa ofrece una probabilidad histórica válida en 30, 60, 90 y 180 días.  ↔ R5
- [ ] (T6) A 30 días la predicción ML, cuando supera sus gates temporales, se muestra junto a la referencia histórica sin fusionarse; si ML se abstiene, la referencia permanece. A 60/90/180 días se conserva al menos la referencia histórica y ningún ausente se representa como 0 %.  ↔ R6
- [ ] (T7) La materialización usa el último corte ADM1 disponible sin retrasar todas las señales a la fecha mínima común; cada señal mantiene su fecha efectiva y antigüedad, y la corrida local actual debe alcanzar al menos `analysis_as_of=2026-07-20`.  ↔ R7
- [ ] (T8) El snapshot y la API distinguen `query_generated_at`, `analysis_as_of` y fechas efectivas de señales, exponen hashes/versiones sin paths ni secretos y no realizan GEE, entrenamiento ni escrituras durante una request.  ↔ R8
- [ ] (T9) Region Explorer encuentra continuidad por ID exacto para cualquier ADM1, diferencia consulta live de actualidad observada y muestra antigüedad/calidad por señal; `not_applicable` explica que no hay condición satelital activa y una región activa nunca muestra “sin evaluación materializada”.  ↔ R9
- [ ] (T10) Low-bandwidth y Reports conservan la misma cobertura, target, horizontes, fechas, calidad, evidencia y abstención sin convertir validación oficial o impacto FEWS en el estado satelital.  ↔ R10
- [ ] (T11) La demo offline sigue siendo determinista y marcada `is_demo=true`; dashboard live/cache solo acepta snapshots reales `is_demo=false` y cualquier mezcla falla cerrada.  ↔ R11
- [ ] (T12) Tests de dominio, fuga temporal, contratos, API, servicios, frontend, reportes y seguridad verifican 121/121, 47/47 Kenya, 484 resultados, cuatro horizontes, asincronía de fuentes, estados activo/inactivo, validación NDMA separada, FEWS no causal y ausencia de GEE/entrenamiento bajo request.  ↔ R12
- [ ] Tests que cubran los criterios de aceptación
