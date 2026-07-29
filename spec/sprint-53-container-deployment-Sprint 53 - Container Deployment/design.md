# sprint-53-container-deployment · Despliegue reproducible de frontend y API — Diseño

## Scope (archivos que puede tocar)

- `Dockerfile`
- `.dockerignore`
- `docker-compose.yml`
- `infrastructure/**`
- `scripts/**`
- `.github/workflows/**`
- `docs/deployment/**`
- `pyproject.toml`
- `requirements*.txt`
- `Makefile`
- `.env.example`
- `.gitignore`
- `.harness/gates.config.json`
- `docs/**`
- `spec/**`
- `progress/**`
- `spec.json`
- `.harness/interviews/**`

## Enfoque

- **data_model:** no cambia contratos de datos; solo empaquetado y configuración runtime
- **external_contracts:** dos imágenes/servicios, Docker Compose y Cloud Run
- **edge_cases:** arranque demo sin secretos, rutas SPA y API same-origin
- **ui_states:** el frontend conserva rutas profundas y modo visible demo/live

## Decisiones de la entrevista

- **platform:** El destino documentado será Google Cloud Run para obtener una URL HTTPS pública y reproducible para Devpost. Docker Compose será el smoke local equivalente.
- **architecture:** Un Dockerfile multi-stage producirá dos targets separados: API Python/ASGI y web React compilada servida por Nginx. El servicio web hará proxy same-origin de `/api`, `/health` y `/ready` hacia la API para evitar CORS y configuración del navegador.
- **demo:** El perfil inicial desplegable será `MWANGAZA_MODE=demo`, sin credenciales GEE. Production podrá inyectar configuración y secretos solo en runtime, sin fallback silencioso a demo.
- **security:** Ambos contenedores se ejecutarán como usuarios no root. `.dockerignore` excluirá Git, `.env`, claves, caches, históricos locales, modelos y entregables que no sean necesarios en runtime.
- **health:** La API usará `/health` para liveness y `/ready` para readiness. El contenedor web tendrá `/healthz`; el proxy conservará `/health` y `/ready` de la API.
- **dependency:** El usuario realizará por su cuenta la grabación pendiente del Sprint 52 y ha autorizado continuar. Sprint 53 no marcará Sprint 52 como completado ni modificará sus artefactos.
