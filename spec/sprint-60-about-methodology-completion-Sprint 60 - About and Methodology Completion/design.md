# sprint-60-about-methodology-completion · undefined — Diseño

## Scope (archivos que puede tocar)

- `frontend/**`
- `tests/frontend/**`
- `src/mwangaza/api/**`
- `tests/api/**`
- `docs/**`
- `spec/**`
- `progress/**`

## Enfoque

- **data_model:** Metadata pública y catálogo de fuentes tienen campos, propiedad y degradación definidos.
- **external_contracts:** Endpoint ligero, rutas PWA y navegación están definidos.
- **edge_cases:** Tema, almacenamiento, URLs, metadata inválida y low-bandwidth están cubiertos.
- **ui_states:** Jerarquía editorial, tema, documentos y degradación están definidos.

## Decisiones de la entrevista

- **data_model:** El backend expone metadata pública, versionada y saneada: versión de aplicación, versión metodológica, modo, snapshot, estado documental, fecha de actualización, licencia y repositorio/contacto configurados. El catálogo local de fuentes conserva ID, dataset, proveedor, tipo (plataforma/dataset/geometría/exposición), unidad, resolución, frecuencia, baseline, transformaciones, limitaciones y URL documental aprobada. Ningún campo ausente se inventa.
- **error_states:** La página distingue carga, error recuperable, metadata parcial, enlace no configurado y estado obsoleto. `Refresh status` sólo repite una lectura ligera y muestra el error saneado sin borrar el último estado válido. Enlaces legales o de contacto sin destino aprobado quedan deshabilitados con explicación explícita.
- **edge_cases:** Tema inválido o almacenamiento no disponible vuelve a la preferencia del sistema sin romper render. La preferencia manual prevalece sobre el sistema y persiste entre recargas. URLs externas se validan como HTTPS; fuentes con campos opcionales ausentes muestran `Not available`. Fechas y versiones inválidas se degradan explícitamente. Low-bandwidth omite ilustración y movimiento, pero conserva todo el contenido.
- **auth_secrets:** About, metodología, privacidad, términos, contacto y status son públicos y de sólo lectura. El endpoint no devuelve secretos, rutas privadas, credenciales, configuración administrativa ni variables de entorno. Contacto usa únicamente URL pública configurada; no se añade formulario, email personal ni mutación.
- **external_contracts:** Se aprueba `GET /api/v1/about/status` como lectura ligera de metadata/configuración ya cargada, sin GEE, refresh pipeline, escritura ni recálculo. Se aprueban rutas PWA `/about`, `/methodology`, `/privacy`, `/terms` y `/contact`; el repositorio y la documentación de fuentes usan enlaces HTTPS públicos configurados. El logo navega internamente a `/overview`.
- **ui_states:** `/about` mantiene una composición editorial tranquila con cabecera de estado, explicación, capacidades, catálogo de fuentes con detalle accesible, flujo Observe/Compare/Assess/Act, cobertura, límites y contexto. El tema claro/oscuro se aplica a todo el shell, persiste y respeta foco/contraste. Las páginas legales y metodología son documentos legibles; contacto es una página de enlaces públicos. Low-bandwidth elimina ilustración decorativa y transiciones.
- **about_imagery:** La ilustración conceptual se sustituye por una fotografía documental local de analistas climáticos revisando observaciones satelitales. El recorte horizontal preserva a las personas y el contexto territorial, no incorpora interfaces ni cifras ficticias y mantiene una alternativa textual breve. Low-bandwidth no descarga ni renderiza el elemento visual.
- **dark_theme_audit:** La preferencia oscura cubre también contenedores no semánticos (`div`, `aside`, `dl` y filas seleccionadas), con tokens compartidos para canvas, superficie, elevación, selección y borde. No quedan paneles blancos en las rutas públicas; los estados de riesgo mantienen su color propio.
- **navigation_pruning:** Se retiran del render los estados `Notifications unavailable` y `Account unavailable`, además de los enlaces Privacy/Terms/Contact del footer de About. Las rutas legales/contacto permanecen accesibles directamente para no romper compatibilidad; el footer conserva licencia y repositorio cuando exista un destino configurado.
- **brand_system:** La marca combina sol/haz dorado, relieve territorial y punto de observación sobre verde profundo. Un único SVG versionado alimenta favicon, manifiesto PWA, sidebar y landing; el texto continúa en HTML para conservar nitidez, localización y accesibilidad. La versión de caché del service worker cambia al actualizar la marca.
- **rollback_compat:** El cambio es aditivo, preserva rutas existentes, contrato `DashboardData`, demo offline y preferencias anteriores. El nuevo payload no sustituye contratos operativos. Sin endpoint nuevo, la UI muestra metadata disponible y estado parcial. El rollback es revertir el sprint; datos locales desconocidos de tema se ignoran.
- **tests:** Tests bloqueantes cubren payload saneado y parcial, ausencia de GEE/escrituras en refresh, rutas y navegación, catálogo y enlaces, persistencia de tema y fallback, contraste/semántica accesible, low-bandwidth, páginas legales/contacto, demo offline y documentación de implementado/pendiente/futuro.
