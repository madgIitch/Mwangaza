# sprint-53-container-deployment · Despliegue reproducible de frontend y API — Requisitos

- name: `Sprint 53 - Container Deployment` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-29T23:41:18.444Z

## Contexto

Construir dos imágenes no root y desplegables en Cloud Run, con modo demo sin secretos, proxy same-origin, healthchecks y documentación operativa.

## Requisitos funcionales

R1. Un único `Dockerfile` multi-stage construye targets reproducibles `api` y `web`; CI construye ambos sin credenciales ni red en runtime.
R2. `.dockerignore` impide incorporar `.env`, Git, claves GEE, caches privadas, históricos locales, modelos, entornos virtuales y entregables innecesarios.
R3. Los contenedores finales ejecutan procesos como usuarios no root y exponen únicamente el puerto HTTP requerido.
R4. La API publica `/health` y `/ready`; el web publica `/healthz` y enruta same-origin `/api`, `/health` y `/ready` hacia la API.
R5. `docker-compose.yml` inicia ambos servicios en modo demo sin credenciales GEE y permite abrir la SPA y sus rutas profundas.
R6. La configuración production acepta secretos solo mediante variables de entorno o Google Secret Manager, sin copiarlos a capas, argumentos de build ni logs.
R7. La documentación incluye construcción local, smoke test, despliegue anónimo en Cloud Run, diagnóstico, actualización y rollback.
R8. Una comprobación automatizada falla si las imágenes no construyen o si los contenedores demo no alcanzan health/readiness y una ruta frontend.

## Restricciones

- **error_states:** probes, fallos de upstream y comandos de diagnóstico documentados
- **auth_secrets:** secretos solo mediante entorno o Secret Manager
- **rollback_compat:** imágenes versionadas y rollback documentado por revisión
