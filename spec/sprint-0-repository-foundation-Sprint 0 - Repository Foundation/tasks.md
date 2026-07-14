# sprint-0-repository-foundation · undefined — Tareas

Checklist de implementación. El agente marca [x] al completar; los gates verifican.

- [x] (T1) En un entorno limpio con Python 3.11, `python -m pip install -e .` instala el paquete sin errores y `python -c "import mwangaza; print(mwangaza.__version__)"` imprime `0.0.1`.  ↔ R1
- [x] (T2) `make lint`, `make typecheck` y `make test` existen, se ejecutan localmente y son los mismos comandos usados por CI; todos terminan con código 0.  ↔ R2
- [x] (T3) La CI ejecuta instalación editable, lint, typecheck y tests en cada push o pull request hacia `main`.  ↔ R3
- [x] (T4) `README.md` documenta comandos exactos para `streamlit run app.py`, levantar la API y ejecutar la actualización de datos, incluyendo comportamiento esperado sin credenciales reales.  ↔ R4
- [x] (T5) El código de dominio y los stubs de módulos viven bajo `src/mwangaza`; no se requiere ningún notebook para importar, ejecutar tests o arrancar entrypoints.  ↔ R5
- [x] (T6) `.env.example` contiene solo nombres de variables y valores placeholder no sensibles; no contiene claves, tokens, emails personales, rutas privadas ni identificadores de cuentas reales.  ↔ R6
- [x] (T7) El repositorio incluye `LICENSE` con licencia MIT y la versión declarada en metadata del paquete es `0.0.1`.  ↔ R7
- [x] Tests que cubran los criterios de aceptación
