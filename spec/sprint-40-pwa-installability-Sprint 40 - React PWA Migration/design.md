# sprint-40-pwa-installability · undefined — Diseño

## Scope (archivos que puede tocar)

- `frontend/**`
- `package.json`
- `package-lock.json`
- `pnpm-lock.yaml`
- `vite.config.*`
- `tsconfig*.json`
- `eslint.config.*`
- `tests/frontend/**`
- `pwa/**`
- `assets/icons/**`
- `src/mwangaza/ui/pwa/**`
- `tests/pwa/**`
- `app.py`
- `src/mwangaza/api/**`
- `src/mwangaza/ui/**`
- `tests/api/**`
- `tests/ui/**`
- `pyproject.toml`
- `requirements*.txt`
- `Makefile`
- `.env.example`
- `.gitignore`
- `.github/workflows/**`
- `.harness/gates.config.json`
- `docs/**`
- `spec/**`
- `progress/**`

## Enfoque

- **data_model:** Contratos API y fixtures demo definidos para React.
- **external_contracts:** React/Vite como frontend canonico; FastAPI permanece backend.
- **edge_cases:** Responsive, low-bandwidth, i18n y payload parcial cubiertos.
- **ui_states:** Paridad visible con Streamlit definida.

## Decisiones de la entrevista

- **data_model:** El frontend React consume contratos JSON existentes de `/api/v1/**` y puede usar fixtures demo locales solo cuando la API no este disponible en modo demo/local. No introduce llamadas directas a Earth Engine ni nuevos secretos en navegador.
- **error_states:** La UI debe distinguir API no disponible, datos demo, datos cacheados/offline y datos live. En offline muestra timestamp y advertencia visible; nunca afirma que los datos offline sean live.
- **edge_cases:** Debe soportar mobile, escritorio, low-bandwidth, i18n, API fallida, payload parcial, ausencia de service worker y navegador no instalable sin romper el render principal.
- **auth_secrets:** No se exponen credenciales ni llamadas GEE desde el navegador. El service worker cachea shell/assets seguros y no persiste datos sensibles indefinidamente.
- **external_contracts:** La experiencia principal pasa a `frontend/` con React + Vite + TypeScript. FastAPI/Python se mantiene como backend y `app.py` queda como shim o aviso de migracion.
- **ui_states:** La migracion debe conservar las pantallas visibles ya implementadas: riesgo regional, drilldown, alertas, comparacion historica, exposicion potencial, reportes/export, forecast diagnostics, i18n y modo low-bandwidth.
- **rollback_compat:** `app.py` no se elimina; queda como compatibilidad documentada. La documentacion de desarrollo apunta al frontend JS como experiencia canonica.
- **tests:** Se agregan tests automatizados del frontend para render principal, low-bandwidth, i18n, offline shell y consumo de contratos API. Los comandos JS build/typecheck/lint deben terminar con codigo 0.

