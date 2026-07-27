# sprint-62d2-real-drought-hazard-catalog · Sprint 62D.2 - Real Drought Hazard Catalog — Tareas

- [x] (T1) EM-DAT se ingiere únicamente desde un CSV registrado aportado por el usuario; conserva evento, fechas, ubicación, unidades administrativas, hash, acceso y licencia, y la evidencia solo nacional no se replica a ADM1. ↔ R1
- [x] (T2) NDMA usa exclusivamente el archivo oficial de boletines de Kenya; cada fase conserva condado, periodo, publicación, URL, PDF SHA-256, taxonomía original, método/versión de extracción y estado de validación. ↔ R2
- [x] (T3) Solo fases NDMA con condado y periodo concordantes y evidencia textual inequívoca entran como official_operational_phase; documentos ambiguos quedan en cola de revisión, nunca como negativos. ↔ R3
- [x] (T4) El catálogo de autoridades IGAD registra por país autoridad, URL oficial, granularidad, acceso, cobertura temporal, método previsto y estado; ausencia de adapter o datos es unknown. ↔ R4
- [x] (T5) La auditoría agrupa evidencia hazard temporalmente contigua por ADM1 sin mezclar fuentes incompatibles y reporta episodios, ADM1 cubiertas, periodos, duración y evidencia por país/fuente. ↔ R5
- [x] (T6) Eventos de país sin ADM1, registros no validados y cobertura desconocida se reportan aparte y no inflan los episodios subnacionales. ↔ R6
- [x] (T7) Descargas y tratamiento son reanudables, muestran ETA, conservan artefactos fuera de Git y generan manifiestos/hashes deterministas. ↔ R7
- [x] (T8) Tests offline cubren PDFs/texto NDMA representativo, ambigüedad, EM-DAT realista, eventos nacionales, agrupación temporal, desacuerdos, cobertura y hashes; los smokes reales usan solo fuentes públicas o archivos proporcionados. ↔ R8
- [x] Tests que cubran los criterios de aceptación
