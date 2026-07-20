# sprint-49-public-readme · undefined — Requisitos

- name: `Sprint 49 - Public README` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-20T16:02:50.637Z

## Contexto



## Requisitos funcionales

R1. El `README.md` abre con una descripción pública del problema, los usuarios objetivo, el propósito de early action y el alcance explícito del piloto actual, sin mezclar roadmap con funcionalidad disponible.
R2. El `README.md` incluye secciones separadas y tituladas para `Requirements`, `Installation`, `Offline demo`, `Connected mode`, `Architecture`, `Technology stack`, `Implemented today`, `Roadmap`, `Limitations`, `Responsible use` y `Testing/verification`.
R3. La sección `Offline demo` documenta comandos reproducibles y sin red para al menos un recorrido demo soportado actualmente, indicando el modo demo y cualquier prerequisito local no secreto.
R4. La sección `Connected mode` documenta únicamente los prerequisitos públicos y variables necesarias para habilitar integraciones reales, sin exponer secretos ni valores sensibles; cualquier detalle sensible se deriva a la documentación de configuración/seguridad existente.
R5. La sección `Architecture` contiene un diagrama textual o Mermaid renderizable en GitHub que describe frontend, API, fuentes de datos/modos (`live`, `cache`, `demo`) y flujos principales.
R6. La sección `Technology stack` enumera las tecnologías realmente usadas en el repositorio y visibles en los entrypoints o workflows actuales.
R7. La sección `Implemented today` enumera solo capacidades ya entregadas en la release actual; la sección `Roadmap` enumera únicamente capacidades futuras o no garantizadas.
R8. La sección `Limitations` explica al menos las restricciones de cobertura/piloto, dependencia de datos demo vs operativos y cualquier limitación relevante de conectividad o credenciales.
R9. La sección `Responsible use` indica que las recomendaciones son prototipo de apoyo a decisión y no órdenes oficiales, médicas ni humanitarias automáticas.
R10. Cada comando publicado en el README queda trazado a una evidencia verificable: o bien aparece ejecutado en CI (`.github/workflows/ci.yml`), o bien se referencia explícitamente una verificación manual reproducible versionada en el repo.
R11. No quedan en el README comandos obsoletos, nombres de componentes que contradigan `docs/ARCHITECTURE.md`, ni promesas de funcionalidades no implementadas.

## Restricciones

- **error_states:** El README debe cubrir explícitamente los fallos operativos mínimos de la superficie pública: dependencias faltantes durante instalación/arranque, credenciales GEE ausentes en modo conectado y baseline demo inválido o corrupto con recuperación mediante `scripts/reset_demo.py`. Debe distinguir entre errores esperados de `demo`, `cache` y `production`, y dejar claro que no existe fallback silencioso a demo.
- **auth_secrets:** La sección pública solo puede listar nombres de variables y prerequisitos públicos. No debe incluir valores, claves, blobs JSON ni tutoriales de creación de credenciales; cualquier detalle sensible se deriva a `docs/configuration.md` y `docs/security/**`.
- **rollback_compat:** Se permite reestructurar completamente el README actual porque está obsoleto, pero deben conservarse anchors públicos razonables para `Requirements`, `Installation`, `Architecture`, `Testing`, `Configuration`, `Limitations` y `Roadmap`. También debe evitarse romper expectativas de onboarding ya trazadas desde CI, `docs/` o revisiones versionadas.

