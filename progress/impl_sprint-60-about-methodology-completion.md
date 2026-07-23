# Sprint 60 · About and Methodology Completion

## Resultado

- `/about` ofrece catálogo de fuentes verificable, metodología, límites, cobertura y metadata backend.
- Tema Light/Dark persistente, logo a `/overview` y degradación low-bandwidth.
- Rutas públicas `/methodology`, `/privacy`, `/terms` y `/contact`.
- `GET /api/v1/about/status` es metadata-only, sin GEE, pipeline ni escrituras.
- Enlaces públicos no configurados permanecen explícitos y no se inventan destinos.

## Validación

- Frontend: 49 tests, typecheck, lint y build pasan.
- API enfocada: 18 tests pasan.
- Suite Python global no puede recolectarse con el `pytest` del PATH (Python 3.14 no resuelve módulos raíz); Python 3.12 no tiene pytest instalado.
- Gate Node/Corepack del harness bloqueado por `EPERM lstat C:\Users\peorr` / `ERR_VM_DYNAMIC_IMPORT_CALLBACK_MISSING`; los comandos npm equivalentes pasan.
