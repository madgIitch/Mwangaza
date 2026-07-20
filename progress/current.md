# Sesion actual

Feature: **sprint-47-offline-demo-fallback - Sprint 47 - Offline Demo Fallback** - estado: `review_pending`.

- agente: codex
- rama: `main`
- intentos: 1

## Siguiente accion

- Smoke humano: arrancar con `MWANGAZA_MODE=demo`, navegar todas las rutas y verificar el banner persistente; ejecutar dos veces `python scripts/reset_demo.py`. Cerrar con `node .harness/spec.mjs done sprint-47-offline-demo-fallback` si pasa.

## Ultimo resultado

| intento | resultado | gate fallido | tts(s) | coste |
|--:|--|--|--:|--:|
| 1 | OK | - | - | - |

Validaciones ejecutadas:

- 229 tests Python y 29 tests frontend pasan.
- Typecheck, lint, build y gates del harness pasan.
- Reset demo y metadatos API validados; production nunca cae silenciosamente a demo.
