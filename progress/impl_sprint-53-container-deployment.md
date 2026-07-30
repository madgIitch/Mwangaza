# Sprint 53 - Implementación

Estado: implementación completa, pendiente de revisión humana.

- Spec aprobada en `1613484`; la grabación externa de Sprint 52 no se marcó como terminada.
- Primer build detectó que el frontend necesitaba `demo_data` durante Vite build; corregido.
- Los puertos Compose se aislaron en `18080/18081` para no colisionar con Vite/API locales.
- El smoke detectó rutas runtime dependientes del árbol fuente; la imagen conserva `/app/src`,
  `data/regions` y los mapas versionados con `PYTHONPATH=/app/src`.
- La imagen API instala el extra `api` con `uv sync --frozen` desde `uv.lock`; el entorno
  conserva la misma ruta `/opt/venv` entre build y runtime.
- Build final y smoke de cinco rutas: PASS.
- Usuarios finales verificados: API `10001:10001`, web `101:101`.
- Tamaños finales inspeccionados: API 155.5 MB, web 28.7 MB.
- No aparecen variables GEE ni material secreto en el historial de imagen inspeccionado.
- Typecheck, lint, build y 60/60 tests frontend: PASS.
- 248/248 tests backend en `.venv-s53`: PASS.
- Gates oficiales: PASS.
- `gcloud` no está instalado, por lo que el despliegue externo no se ejecutó; el script falla
  de forma accionable y la guía documenta demo, production, secretos y rollback.
