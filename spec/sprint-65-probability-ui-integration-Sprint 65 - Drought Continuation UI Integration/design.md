# sprint-65-probability-ui-integration · undefined — Diseño

## Scope (archivos que puede tocar)

- `frontend/**`
- `tests/frontend/**`
- `src/mwangaza/services/dashboard_shell.py`
- `src/mwangaza/reports/**`
- `tests/ui/**`
- `tests/reports/**`
- `docs/probabilistic-risk.md`
- `docs/region-interface.md`
- `docs/reports-interface.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS.md`
- `spec/sprint-65-probability-ui-integration-*/**`
- `progress/**`

## Decisiones de la entrevista

- **data_model:** El frontend consume el contrato versionado de Sprint 64 y conserva cada estimación
como entidad separada. `DashboardData` incorpora resultados de continuidad por región y
horizonte; no promedia, reetiqueta ni deriva probabilidades. Los reportes reutilizan el
mismo snapshot materializado y conservan `as_of`, fase, método, validación y calidad.
- **error_states:** `not_applicable` oculta cualquier porcentaje y explica que no hay un episodio
oficial activo. `unavailable` conserva el espacio de la estimación afectada y su reason
code legible; ML unavailable no oculta una referencia histórica disponible. Un fallo de
la petición de continuidad degrada solo este módulo y no bloquea Region Explorer.
- **edge_cases:** La selección nacional o una unidad sin resultado no hereda la probabilidad de otra
geografía. El selector ofrece exactamente 30, 60, 90 y 180 días. A 30 días se muestran
las dos estimaciones en paralelo; a horizontes largos no se reserva ni simula un valor ML.
Los valores ausentes nunca se representan como 0 %.
- **auth_secrets:** Navegador y reportes leen exclusivamente API/snapshots locales materializados. No
entrenan, calibran, escriben artefactos ni llaman GEE. No se muestran paths, secretos ni
hashes internos completos en la interfaz pública.
- **external_contracts:** Se consume `GET /api/v1/drought-continuation-probabilities` de Sprint 64 mediante
una función tipada y tolerante a fallo. La consulta se limita a la región seleccionada y
los cuatro horizontes. IDs, métodos, estados de validación, reason codes y versiones no
se traducen ni reinterpretan.
- **ui_states:** Tesis visual: bloque operativo sobrio dentro del inspector, con una comparación
tipográfica compacta y sin competir con el mapa. Plan de contenido: título y alcance,
selector de horizonte, estimaciones comparadas, evidencia/calidad y disclaimer. Tesis de
interacción: transición breve al cambiar horizonte, revelado accesible de evidencia y
el mismo orden semántico en modo normal y low-bandwidth. A 30 días las etiquetas exactas
son `Experimental ML prediction` y `Historical reference`; ML muestra `Inconclusive
validation` y `Not for operational use`.
- **rollback_compat:** Integración aditiva. Si el endpoint no está disponible, el resto de Region Explorer
y Reports conserva su comportamiento actual. El módulo usa los patrones visuales,
responsive, idiomas y accesibilidad existentes, sin nueva ruta ni dependencia remota.
- **tests:** Tests frontend cubren doble estimación, cuatro horizontes, ML unavailable con
baseline disponible, not_applicable, fallo de red, copy no causal, selección ADM1,
low-bandwidth y demo offline. Tests de reportes cubren inclusión dual a 30 días,
baseline exclusivo a horizontes largos y abstención sin porcentajes inventados.

