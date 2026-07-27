# sprint-62d2-real-drought-hazard-catalog · undefined — Requisitos

- name: `Sprint 62D.2 - Real Drought Hazard Catalog` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-27T20:45:22.177Z

## Contexto



## Requisitos funcionales

R1. EM-DAT se ingiere únicamente desde un CSV registrado aportado por el usuario; conserva evento, fechas, ubicación, unidades administrativas, hash, acceso y licencia, y la evidencia solo nacional no se replica a ADM1.
R2. NDMA usa exclusivamente el archivo oficial de boletines de Kenya; cada fase conserva condado, periodo, publicación, URL, PDF SHA-256, taxonomía original, método/versión de extracción y estado de validación.
R3. Solo fases NDMA con condado y periodo concordantes y evidencia textual inequívoca entran como official_operational_phase; documentos ambiguos quedan en cola de revisión, nunca como negativos.
R4. El catálogo de autoridades IGAD registra por país autoridad, URL oficial, granularidad, acceso, cobertura temporal, método previsto y estado; ausencia de adapter o datos es unknown.
R5. La auditoría agrupa evidencia hazard temporalmente contigua por ADM1 sin mezclar fuentes incompatibles y reporta episodios, ADM1 cubiertas, periodos, duración y evidencia por país/fuente.
R6. Eventos de país sin ADM1, registros no validados y cobertura desconocida se reportan aparte y no inflan los episodios subnacionales.
R7. Descargas y tratamiento son reanudables, muestran ETA, conservan artefactos fuera de Git y generan manifiestos/hashes deterministas.
R8. Tests offline cubren PDFs/texto NDMA representativo, ambigüedad, EM-DAT realista, eventos nacionales, agrupación temporal, desacuerdos, cobertura y hashes; los smokes reales usan solo fuentes públicas o archivos proporcionados.

