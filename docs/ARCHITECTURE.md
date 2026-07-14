# Arquitectura

> El agente lo lee antes de implementar. Mantén aquí el contexto que no cabe en una feature concreta.

## Visión general

Producto/proyecto:

Usuarios principales:

Objetivo no negociable:

## Componentes

- (rellenar) Componente:
  - Responsabilidad:
  - Entradas/salidas:
  - Dueño/riesgo:

## Flujo de datos

1. (rellenar)

## Integraciones externas

- (rellenar) Servicio/API:
  - Contrato:
  - Credenciales/config:
  - Entorno local/CI:

## Restricciones conocidas

- (rellenar) Rendimiento, seguridad, compatibilidad, despliegue, coste, etc.

## Decisiones abiertas

- (rellenar) Preguntas que bloquean diseño futuro.

<!-- Los specs aprobados se anexan debajo con marcadores harness:<id>. -->

<!-- harness:sprint-0-repository-foundation -->
## sprint-0-repository-foundation · Sprint 0 - Repository Foundation



### Scope aprobado

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
  - `src/mwangaza/**`
  - `tests/**`
  - `app.py`
  - `README.md`
  - `LICENSE`

### Contexto técnico

- **data_model:** Sprint 0 queda limitado a estructura de modulos y stubs importables bajo `src/mwangaza`. No define contratos de dominio, modelos Pydantic, dataclasses ni schemas de indicadores, alertas o regiones; esos contratos empiezan en sprints posteriores. Los modulos pueden exponer funciones placeholder simples y documentadas solo para validar importabilidad.
- **external_contracts:** Quedan fijados los entrypoints exactos: dashboard `streamlit run app.py`, API `uvicorn mwangaza.api.app:app --reload` y refresco `python -m mwangaza.data.refresh --dry-run`. La API debe exponer al menos `/health` con estado stub, y el refresco dry-run debe imprimir que no consulta servicios remotos.
- **edge_cases:** Sprint 0 soporta Python 3.11+ y CI Linux. En Windows local se documentan comandos Python equivalentes; `make` es el contrato principal para CI y entornos Unix-like. Los entrypoints Python deben funcionar sin depender de notebooks ni datos locales.
- **ui_states:** `streamlit run app.py` debe mostrar una pantalla placeholder de producto con nombre, tagline, estado tecnico basico y aviso visible de `foundation stub`. No debe mostrar navegacion vacia ni claims de datos reales.

<!-- harness:sprint-1-configuration-and-secrets -->
## sprint-1-configuration-and-secrets · Sprint 1 - Configuration and Secrets



### Scope aprobado

  - `src/mwangaza/config/**`
  - `src/mwangaza/api/**`
  - `src/mwangaza/data/**`
  - `src/mwangaza/ui/**`
  - `tests/**`
  - `.env.example`
  - `README.md`
  - `docs/**`
  - `spec/**`
  - `progress/**`

### Contexto técnico

- **data_model:** Define `Settings` como dataclass inmutable en `src/mwangaza/config.py`, construido por `load_settings(env: Mapping[str, str] | None = None)`, sin Pydantic. Campos, tipos, defaults y perfiles validos quedan especificados: `environment`, `log_level`, rutas, paises habilitados, periodo de climatologia, credenciales GEE opcionales y `max_remote_pixels`.
- **external_contracts:** Todos los entrypoints publicos cargan `Settings`: API `/health`, dashboard y refresh. `/health` expone solo campos saneados: `environment`, `version`, `status`, `config_valid`, `enabled_countries`, `climatology_period` y nombres de variables faltantes, sin valores. Refresh `--dry-run` valida configuracion y no consulta servicios remotos; sin `--dry-run`, Sprint 1 sigue bloqueado con mensaje stub.
- **edge_cases:** Quedan definidos los casos invalidos: entorno desconocido, paises vacios o fuera de ISO3 IGAD permitido, anos no enteros, rango invertido, `max_remote_pixels <= 0`, rutas vacias, log level invalido y `MWANGAZA_GEE_PRIVATE_KEY_JSON` presente pero no JSON object valido. Placeholders como `replace-me` no bloquean en `test` o `demo`, pero cuentan como ausentes en `production`.
- **ui_states:** Dashboard muestra perfil activo, paises habilitados, periodo de climatologia y estado `configuration ok` o `configuration invalid`. Los errores son accionables y saneados, con nombres de variables o campos invalidos, sin secretos ni valores privados. En `production` invalido no continua mostrando datos ni claims operativos.

