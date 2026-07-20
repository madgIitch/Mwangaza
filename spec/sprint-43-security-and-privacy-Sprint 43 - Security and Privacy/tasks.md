# sprint-43-security-and-privacy · undefined — Tareas

Checklist de implementación. El agente marca [x] al completar; los gates verifican.

- [x] (T1) AC1: CI ejecuta un scanner determinista que falla ante claves privadas, credenciales GCP o archivos de secretos versionados, sin leer valores locales de `.env`.  ↔ R1
- [x] (T2) AC2: La API limita cuerpos a 64 KiB, exige JSON en endpoints con body y aplica rate limiting configurable con respuestas 413, 415 y 429 saneadas.  ↔ R2
- [x] (T3) AC3: El prototipo no expone uploads; multipart, nombres de archivo y traversal no alcanzan ejecución ni escritura de archivos.  ↔ R3
- [x] (T4) AC4: Código, contratos y documentación no recopilan nombres, teléfonos ni ubicación individual de comunidades; métricas de seguridad son efímeras y agregadas.  ↔ R4
- [x] (T5) AC5: API y despliegue estático aplican CSP, nosniff, anti-framing, referrer policy y permissions policy sin romper la PWA.  ↔ R5
- [x] (T6) AC6: El threat model cubre credenciales GEE, manipulación de datos, disponibilidad, desinformación y el riesgo explícito del admin público de demo.  ↔ R6
- [x] Tests que cubran los criterios de aceptación
