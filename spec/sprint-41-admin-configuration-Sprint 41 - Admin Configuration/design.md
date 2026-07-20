# sprint-41-admin-configuration · undefined — Diseño

## Scope (archivos que puede tocar)

- `frontend/**`
- `tests/frontend/**`
- `src/mwangaza/admin/**`
- `src/mwangaza/api/**`
- `src/mwangaza/audit/**`
- `src/mwangaza/db/**`
- `src/mwangaza/alerts/**`
- `src/mwangaza/actions/**`
- `config/thresholds/**`
- `config/actions/**`
- `tests/admin/**`
- `tests/api/**`
- `tests/audit/**`
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

- **data_model:** Versiones append-only para umbrales y acciones.
- **external_contracts:** `/api/v1/admin/**` y frontend React canónico.
- **edge_cases:** Concurrencia, invalidación y no recalculo cubiertos.
- **ui_states:** Acceso público, editor, validación, historial y modo lite.

## Decisiones de la entrevista

- **data_model:** La configuración administrable se modela como versiones append-only de umbrales y acciones. Cada versión incluye `version_id`, `created_at`, `created_by`, `status`, `thresholds`, `actions`, `validation_errors` y hash del contenido. Una versión inválida puede guardarse solo como borrador rechazado, pero nunca se activa.
- **error_states:** La UI y la API distinguen carga, configuración inválida, conflicto de versión y fallo de persistencia.
- **edge_cases:** Guardados concurrentes deben producir una versión nueva o un conflicto explícito, sin sobrescribir historia. Los cambios no disparan recalculo de indicadores, alertas ni cache; solo registran configuración pendiente/activa hasta una acción explícita futura.
- **auth_secrets:** El panel de hackathon es público y no usa credenciales. La documentación debe aclarar que se requiere autenticación y autorización institucional antes de producción.
- **external_contracts:** React/Vite expone la superficie admin y FastAPI conserva el backend. Los endpoints admin quedan bajo `/api/v1/admin/**`, no consultan Earth Engine y no envían notificaciones reales. El frontend canónico vive en `frontend/`; `app.py` puede mantener solo aviso/shim.
- **ui_states:** El panel carga directamente el editor de umbrales/acciones, vista de validación, historial de versiones y confirmación de versión activa. Low-bandwidth mantiene editor y historial en tablas/formularios sin visualizaciones pesadas.
- **rollback_compat:** Los defaults existentes de umbrales y acciones siguen funcionando sin panel admin. Si no hay configuración admin, la app pública no cambia comportamiento. La configuración versionada nueva no migra destructivamente archivos históricos.
- **tests:** Se agregan tests API/admin para acceso público completo, ausencia de autenticación, versionado append-only, validación, no recalculo y auditoría. Se agregan tests frontend para carga directa, edición, errores de validación, historial y low-bandwidth.
