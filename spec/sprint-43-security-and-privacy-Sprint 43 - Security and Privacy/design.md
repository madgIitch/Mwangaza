# sprint-43-security-and-privacy · undefined — Diseño

## Scope (archivos que puede tocar)

- `docs/security/**`
- `src/mwangaza/security/**`
- `tests/security/**`
- `src/mwangaza/api/**`
- `tests/api/**`
- `frontend/public/**`
- `.github/workflows/security.yml`
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

## Decisiones de la entrevista

- **data_model:** No se introduce almacenamiento de identidad ni PII. Los controles mantienen sólo contadores efímeros por cliente para rate limiting y resultados saneados; no persisten IPs, nombres, teléfonos ni ubicaciones individuales.
- **error_states:** La API distingue `payload_too_large` (413), `unsupported_media_type` (415), `rate_limited` (429) e input inválido (400), siempre con mensajes saneados y `X-Run-ID`.
- **edge_cases:** El límite se aplica antes de parsear JSON. Sólo los endpoints con body aceptan `application/json`. No existen uploads; rutas multipart, nombres de archivo y traversal quedan fuera del contrato y son rechazados. El rate limiter es local al proceso y apto para demo, no sustituye un gateway.
- **auth_secrets:** CI ejecuta un scanner local determinista contra patrones de claves privadas, credenciales GCP y archivos sensibles. Los valores de `.env` no se leen ni se incluyen. El panel admin permanece público por decisión de demo; no se reintroducen credenciales.
- **external_contracts:** Todas las respuestas HTTP añaden CSP, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` y `Permissions-Policy`. API limita cuerpos a 64 KiB y peticiones por cliente mediante configuración pública de entorno.
- **ui_states:** No se añade una pantalla nueva. La UI existente continúa funcionando y el despliegue estático declara headers equivalentes. Los errores de API siguen usando estados existentes.
- **rollback_compat:** GETs y payloads válidos existentes conservan su contrato. El rate limit tiene defaults amplios para no romper la demo. No se crean endpoints de upload ni se modifica la decisión de acceso público del admin.
- **tests:** Tests cubren scanner, tamaño, content type, rate limit, headers, traversal/multipart, ausencia de PII y saneamiento. El threat model documenta GEE, manipulación, disponibilidad, desinformación y admin público.

