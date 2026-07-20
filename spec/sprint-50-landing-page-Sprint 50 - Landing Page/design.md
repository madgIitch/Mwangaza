# sprint-50-landing-page · undefined — Diseño

## Scope (archivos que puede tocar)

- `frontend/src/**`
- `frontend/public/**`
- `frontend/index.html`
- `frontend/src/router/**`
- `frontend/src/config/**`
- `frontend/src/components/**`
- `frontend/src/pages/**`
- `tests/frontend/**`
- `docs/about-interface.md`
- `README.md`
- `spec/sprint-50-landing-page-*/**`

## Enfoque

- **data_model:** La configuración pública de la landing se define en `frontend/src/config/landing.ts` con los campos `dashboard`, `github` y `demo`. Cada valor debe ser una URL absoluta HTTPS o una ruta interna que empiece por `/`. El componente de la landing admite configuración inyectable en tests para verificar resolución de CTAs por entorno sin depender de secretos.
- **external_contracts:** La landing vive en la ruta pública `/landing` y es estrictamente aditiva. El CTA principal abre `/overview`. La navegación secundaria enlaza `About`, `GitHub` y `demo` desde la configuración pública. `/` y las rutas operativas existentes conservan su comportamiento actual.
- **edge_cases:** La validación responsive cubre 320 px de ancho mínimo y breakpoints de 375/768/1280. Ningún contenedor puede introducir overflow horizontal; textos largos deben hacer wrapping. Las listas de pilotos y limitaciones crecen verticalmente y cualquier grid colapsa a una sola columna en móvil estrecho.
- **ui_states:** La landing no tiene estado de carga ni dependencias remotas. El contenido principal es estático/versionado y no depende de la disponibilidad de los CTAs opcionales. Los CTAs no disponibles se omiten sin mensaje de error y sin dejar huecos visuales.

## Decisiones de la entrevista

- **adv-73abcc2f5f:** ### [adv-717625353e] `Capabilities` exige exactamente 3 capacidades resumidas, pero la documentación vigente del producto enumera 4 capacidades en `docs/about-interface.md` (vegetation, rainfall, surface temperature, early action) y el criterio no define cuáles 3 deben mostrarse en la landing. Dos implementaciones razonables podrían elegir tríos distintos y no habría base para decidir si pasa o falla.

**R:**
- **adv-604ecc82fb:** ### [adv-e8154223be] Si falta o es inválida la configuración de un CTA, se pide aplicar `el comportamiento de fallback aprobado por spec`, pero el fallback observable no está definido: no se sabe si el CTA debe ocultarse, deshabilitarse, seguir visible con texto alternativo, redirigir a otra ruta o mostrar un mensaje. Cualquiera de esas opciones sería razonable.

**R:**
- **adv-765455f281:** ### [adv-65895ca4c8] `La introducción de la landing no rompe las rutas existentes de la PWA ni sustituye contenido operativo aprobado salvo decisión explícita del spec` no define la ruta pública exacta de la landing ni qué rutas/contenidos operativos están protegidos frente a sustitución. Sin esa decisión de routing, una landing en `/`, `/about` o una ruta nueva podrían ser interpretaciones razonables con veredictos distintos.

**R:**
- **data_model:** Leer `dashboard`, `github` y `demo` desde un módulo público versionado `frontend/src/config/landing.ts`. Cada campo es una URL absoluta HTTPS o una ruta interna que empieza por `/`; el componente acepta una configuración inyectable para tests.
- **error_states:** Omitir cualquier CTA ausente o inválido sin renderizar controles deshabilitados ni destinos inventados. El layout redistribuye los CTAs restantes y conserva siempre al menos el enlace interno al dashboard configurado por defecto.
- **edge_cases:** Verificar desde 320 px de ancho y breakpoints 375/768/1280. Ningún contenedor usa anchos mínimos que desborden; listas de pilotos y limitaciones crecen verticalmente, con wrapping de texto y grid que colapsa a una columna.
- **external_contracts:** La landing vive en `/landing` y es estrictamente aditiva. El CTA principal abre `/overview`; la navegación secundaria enlaza About, GitHub y demo configurables. `/` y las rutas operativas existentes conservan su comportamiento.
- **ui_states:** Los CTAs no disponibles se omiten sin mensaje de error porque son navegación opcional; no quedan huecos. El contenido principal nunca depende de esos enlaces y no tiene estado de carga ni dependencia remota.
- **rollback_compat:** Sí, preservar intactos `/`, `/overview`, `/region`, `/alerts`, `/reports`, `/about`, `/admin`, `/technical`, el banner demo y todos los contratos existentes. Solo se añade `/landing` y sus assets/configuración.
- **tests:** Bloquean: smoke de contenido y exactamente tres capacidades, URLs configuradas y omisión de inválidas, prueba de ruta aditiva, verificación CSS/DOM a 320 px sin overflow, ausencia de llamadas remotas/GEE y test que rechaza claims cuantitativos sin cita visible.
