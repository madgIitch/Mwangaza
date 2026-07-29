# sprint-53-container-deployment · Despliegue reproducible de frontend y API — Tareas

Checklist de implementación. El agente marca [x] al completar; los gates verifican.

- [ ] (T1) Un único `Dockerfile` multi-stage construye targets reproducibles `api` y `web`; CI construye ambos sin credenciales ni red en runtime.  ↔ R1
- [ ] (T2) `.dockerignore` impide incorporar `.env`, Git, claves GEE, caches privadas, históricos locales, modelos, entornos virtuales y entregables innecesarios.  ↔ R2
- [ ] (T3) Los contenedores finales ejecutan procesos como usuarios no root y exponen únicamente el puerto HTTP requerido.  ↔ R3
- [ ] (T4) La API publica `/health` y `/ready`; el web publica `/healthz` y enruta same-origin `/api`, `/health` y `/ready` hacia la API.  ↔ R4
- [ ] (T5) `docker-compose.yml` inicia ambos servicios en modo demo sin credenciales GEE y permite abrir la SPA y sus rutas profundas.  ↔ R5
- [ ] (T6) La configuración production acepta secretos solo mediante variables de entorno o Google Secret Manager, sin copiarlos a capas, argumentos de build ni logs.  ↔ R6
- [ ] (T7) La documentación incluye construcción local, smoke test, despliegue anónimo en Cloud Run, diagnóstico, actualización y rollback.  ↔ R7
- [ ] (T8) Una comprobación automatizada falla si las imágenes no construyen o si los contenedores demo no alcanzan health/readiness y una ruta frontend.  ↔ R8
- [ ] Tests que cubran los criterios de aceptación
