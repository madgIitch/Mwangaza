# sprint-62d-independent-drought-labels · undefined — Requisitos

- name: `Sprint 62D - Independent Drought and Food Security Labels` · priority: - · sdd: true
- aprobado por: peorr · 2026-07-26T23:13:30.046Z

## Contexto



## Requisitos funcionales

R1. El schema separa `drought_hazard_event` de `acute_food_insecurity_impact`; FEWS NET/IPC Phase 3+ nunca se convierte automáticamente en sequía.
R2. FEWS NET importa únicamente `scenario=CS` como assessed por defecto y conserva FNID, escala, fase original, variante de asistencia, fechas de publicación/validez, documento, organización y política de uso; escenarios proyectados y valores 66/88/99 quedan excluidos con motivo.
R3. El adapter FEWS NET pagina, reintenta con backoff acotado, crea checkpoints reanudables y muestra filas/progreso/ETA sin duplicar registros tras reanudar.
R4. IPC conserva analysis ID, tipo de análisis, `period`, fase, fechas, geometría y licencia; solo `period=C` es assessed y la ausencia de `IPC_API_KEY` falla cerrada sin filtrar el secreto.
R5. Declaraciones/fases oficiales se importan mediante manifiesto local validado y distinguen `official_operational_phase` de `official_emergency_declaration`, conservando autoridad, jurisdicción, documento/hash, publicación, validez, taxonomía y revisión.
R6. EM-DAT se importa desde un archivo local registrado, conserva event ID, tipo, fechas, ubicación/unidades administrativas, acceso/hash/licencia y no propaga evidencia nacional a ADM1 no enumerados.
R7. Toda concordancia espacial usa geometrías y una regla versionada de solape; registra fracción de la fuente, fracción del ADM1, método y área no concordada, y rechaza resultados ambiguos en vez de unir por nombre.
R8. Ausencia de análisis, país sin cobertura, geometría faltante, fuente caída o adapter deshabilitado se representa como cobertura desconocida/exclusión, nunca como etiqueta negativa o fase 1.
R9. El artefacto JSONL y su manifiesto son deterministas y registran schema/rule versions, fuentes, cobertura temporal/espacial, incluidos/excluidos por motivo, SHA-256 y fecha de recuperación; los datos descargados permanecen fuera de Git.
R10. Tests offline no usan red ni secretos y cubren semántica, anti-lookahead, paginación/retry/resume, auth, importadores locales, solape espacial, ambigüedad, provenance, licencias y hashes; un smoke FEWS NET público valida una muestra real antes de revisión humana.

