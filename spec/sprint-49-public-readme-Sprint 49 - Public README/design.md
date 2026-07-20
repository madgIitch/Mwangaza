# sprint-49-public-readme · undefined — Diseño

## Scope (archivos que puede tocar)

- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/README.md`
- `docs/configuration.md`
- `docs/security/**`
- `.github/workflows/ci.yml`
- `Makefile`
- `tests/**`
- `spec/**`
- `progress/**`

## Enfoque

- **data_model:** La feature sigue siendo documental y no introduce contratos de datos nuevos. El README debe apoyarse en los modelos y catálogos ya documentados en `docs/`, incluyendo la separación entre modos `live`, `cache` y `demo`, sin redefinir payloads ni estructuras.
- **external_contracts:** La spec ya puede fijar los entrypoints y comandos públicos canónicos que el README puede prometer: `uv sync`, `npm install`, `MWANGAZA_MODE=demo` + `uv run uvicorn mwangaza.api.app:app`, `npm run dev`, `scripts/demo_somalia.py`, `scripts/demo_kenya.py`, `scripts/reset_demo.py`, `uv run python -m unittest discover -s tests`, `npm test`, `npm run typecheck`, `npm run lint` y `npm run build`. El README no debe publicar comandos obsoletos ni nombres que contradigan `docs/ARCHITECTURE.md`.
- **edge_cases:** La spec debe fijar una ruta canónica basada en `uv` y `npm`, documentando equivalentes claros para PowerShell y shells POSIX cuando difiera la sintaxis de variables de entorno. `make` puede aparecer como atajo opcional, pero no como requisito universal. También debe quedar explícito que el README público solo promete recorridos demo soportados actualmente, incluyendo los escenarios versionados de Somalia y Northern Kenya.
- **ui_states:** La feature no cambia la UI. El README solo debe describir estados ya existentes: demo/offline, conectado, limitaciones y roadmap, sin introducir nuevos estados visuales ni pantallas no implementadas.

## Decisiones de la entrevista

- **adv-2be1b20861:** ### [adv-db5b2e50ac] `sin mezclar roadmap con funcionalidad disponible` y `Implemented today` vs `Roadmap` no fijan la regla de separación cuando una capacidad existe solo en modo demo, parcial, experimental o detrás de credenciales; hace falta una decisión de negocio sobre si eso cuenta como "entregado hoy" o como "roadmap/no garantizado".

**R:**
- **adv-97b4514d3d:** ### [adv-820b245dfb] `Technology stack` debe enumerar `las tecnologías realmente usadas en el repositorio y visibles en los entrypoints o workflows actuales`, pero no especifica el umbral para incluir o excluir herramientas de test, build, runtime, CI o dependencias transversales; sin esa frontera no se puede decidir objetivamente si una lista es completa o excesiva.

**R:**
- **adv-f6a9d692ef:** ### [adv-a0bb9a03a6] `Cada comando publicado en el README queda trazado a una evidencia verificable` es ambiguo para comandos compuestos o variantes por plataforma: no define si basta con que CI ejecute un target equivalente (`make test` vs `python -m unittest ...`), si la evidencia manual puede cubrir equivalencias parciales, ni qué nivel de correspondencia textual/funcional se exige.

**R:**
- **adv-f352706ced:** ## Decisiones registradas
- **error_states:** Cubrir todos: dependencias faltantes, credenciales GEE ausentes en conectado y baseline demo inválido con recuperación mediante `scripts/reset_demo.py`. Distinguir errores esperados de demo, cache y production sin sugerir fallback silencioso.
- **edge_cases:** Documentar una ruta canónica con `uv`/`npm` y equivalentes claros para PowerShell y shells POSIX cuando difieran las variables de entorno. `make` queda como atajo opcional, no requisito universal.
- **auth_secrets:** Listar solo nombres de variables y prerequisitos públicos. No incluir valores, claves ni tutorial de creación de credenciales; remitir a `docs/configuration.md` y `docs/security/` para manejo seguro.
- **external_contracts:** Contrato público: `uv sync`, `npm install`, `MWANGAZA_MODE=demo` + `uv run uvicorn mwangaza.api.app:app`, `npm run dev`, ambos scripts de Somalia/Kenya, `scripts/reset_demo.py`, `uv run python -m unittest discover -s tests`, `npm test`, `npm run typecheck`, `npm run lint` y `npm run build`.
- **rollback_compat:** Se permite reestructuración completa porque el README actual está obsoleto, conservando anchors públicos razonables: Requirements, Installation, Architecture, Testing, Configuration, Limitations y Roadmap.
- **tests:** Los comandos de calidad deben estar cubiertos por CI o ejecutarse en el smoke versionado del Sprint 49. Los comandos de arranque y escenarios pueden tener verificación manual reproducible documentada en `progress/review_sprint-49-public-readme.md`.

