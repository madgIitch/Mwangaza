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

