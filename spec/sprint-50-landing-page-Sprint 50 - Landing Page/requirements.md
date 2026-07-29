# sprint-50-landing-page · undefined — Requisitos

- name: `Sprint 50 - Landing Page` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-20T16:11:23.949Z

## Contexto



## Requisitos funcionales

R1. La landing pública muestra literalmente `Mwangaza - Bringing Light to Early Action` en el hero o encabezado principal visible sin interacción.
R2. La landing incluye secciones distinguibles y visibles para `Problem`, `Solution`, `Capabilities` (exactamente 3 capacidades resumidas), `Pilots` y `Limitations`.
R3. Los enlaces `dashboard`, `github` y `demo` se resuelven desde una configuración pública aprobada y cada CTA usa exactamente la URL configurada para ese entorno.
R4. La landing renderiza y navega sin inicializar Google Earth Engine ni requerir credenciales `MWANGAZA_GEE_*`; con la app en modo demo/offline sigue cargando correctamente.
R5. En un viewport móvil aprobado por spec no aparece scroll horizontal en `body` ni en el contenedor principal de la landing.
R6. Cualquier claim de impacto cuantitativo mostrado en la landing incluye cita visible o referencia explícita aprobada; si no existe cita, el texto permanece cualitativo y no presenta cifras simuladas como reales.
R7. Si falta o es inválida la configuración de un CTA, la landing aplica el comportamiento de fallback aprobado por spec de forma consistente y sin romper el layout.
R8. La introducción de la landing no rompe las rutas existentes de la PWA ni sustituye contenido operativo aprobado salvo decisión explícita del spec.
R9. La sección de cobertura usa una fotografía documental generada y versionada localmente, sin texto, logos ni dependencias remotas, conservando legibles las dos métricas de cobertura en escritorio y móvil.

## Restricciones

- **error_states:** Si un CTA falta o es inválido, se omite por completo sin renderizar controles deshabilitados, mensajes de error ni destinos inventados. El layout redistribuye los CTAs restantes sin dejar huecos. Debe conservarse siempre al menos el enlace interno al dashboard configurado por defecto.
- **auth_secrets:** La landing es pública, no depende de Earth Engine y no requiere credenciales `MWANGAZA_GEE_*`. La configuración de enlaces usa solo valores públicos no sensibles definidos en código versionado.
- **rollback_compat:** La feature es estrictamente aditiva: deben preservarse intactos `/`, `/overview`, `/region`, `/alerts`, `/reports`, `/about`, `/admin`, `/technical`, el banner demo y los contratos existentes. Solo se añade `/landing` junto con sus assets y configuración pública.
