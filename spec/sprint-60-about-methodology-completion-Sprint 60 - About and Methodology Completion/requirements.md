# sprint-60-about-methodology-completion · undefined — Requisitos

- name: `Sprint 60 - About and Methodology Completion` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-23T16:52:30.839Z

## Contexto



## Requisitos funcionales

R1. `/about` presenta propósito, capacidades, fuentes, flujo metodológico, contexto IGAD Hackathon 2026, cobertura, límites y estado usando una jerarquía editorial accesible; no presenta el prototipo como alerta oficial ni exposición como personas afectadas.
R2. `GET /api/v1/about/status` devuelve metadata pública y saneada de versión de aplicación/metodología, modo, snapshot, estado documental, actualización, licencia y enlaces configurados; es de sólo lectura y no inicia GEE, pipeline, escritura ni recálculo.
R3. Cada fuente muestra dataset, proveedor, tipo, unidad, resolución, frecuencia, baseline, transformaciones, limitaciones y enlace HTTPS aprobado cuando estén disponibles; los campos ausentes se muestran como no disponibles y plataforma no se confunde con dataset.
R4. El detalle de fuente y los enlaces de metodología son accesibles por teclado y URL; no se abren paneles o destinos ficticios y un enlace no configurado queda explícitamente deshabilitado.
R5. `/methodology` documenta NDVI, lluvia, LST, anomalías, score compuesto, calidad, forecast y exposición con fuentes, periodos, unidades, límites y lenguaje conservador coherente con los contratos existentes.
R6. `/privacy`, `/terms` y `/contact` ofrecen contenido real del prototipo; contacto y repositorio usan sólo enlaces públicos configurados, sin formulario, email personal, autenticación ni mutaciones.
R7. El selector Light/Dark aplica el tema a todo el shell, persiste una preferencia manual en almacenamiento local, usa la preferencia del sistema por defecto y se recupera de almacenamiento ausente o inválido sin impedir el render.
R8. En low-bandwidth se conserva todo el contenido, estado, enlaces y selector de tema en texto, mientras ilustraciones decorativas, fondos pesados y transiciones se omiten; el logo navega a `/overview`.
R9. `Refresh status` sólo relee el endpoint ligero, conserva el último estado válido durante el refresh y muestra estados loading, metadata parcial, obsoleto y error saneado con reintento seguro.
R10. Demo funciona offline y determinista; live/cache no mezclan fixtures. Tests API/frontend cubren saneado, payload parcial, ausencia de GEE/escrituras, rutas, enlaces, tema persistente/fallback, teclado, low-bandwidth y documentación de implementado, pendiente y futuro.
R11. El bloque principal de About usa una fotografía editorial profesional, generada y versionada localmente, con descripción accesible, sin marcas ni claims incrustados; la imagen se omite por completo en low-bandwidth.
R12. El tema oscuro elimina superficies blancas residuales en Overview, Region, Alerts, About, documentos y estado técnico; mapas, tablas, filtros, selecciones y metadatos conservan contraste y jerarquía sin invertir los colores semánticos.
R13. El shell no muestra placeholders de notificaciones o cuenta, y About no promociona enlaces a Privacy, Terms o Contact; sus rutas directas se preservan por compatibilidad.
R14. Mwangaza usa una marca vectorial propia y coherente como favicon/PWA, identidad del shell y wordmark de la landing; permanece legible a tamaño pequeño, funciona en ambos temas y no duplica ornamento dentro del contenido operativo.

## Restricciones

- **error_states:** Carga, error, parcial, obsoleto y enlace no configurado son observables.
- **auth_secrets:** Todas las superficies son públicas, de sólo lectura y saneadas.
- **rollback_compat:** Se preservan rutas, demo y contratos existentes.
