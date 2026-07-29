# sprint-52-demo-video · Guion y grabación de la demo final — Diseño

## Scope (archivos que puede tocar)

- `submission/video/**`
- `scripts/prepare_demo.py`
- `docs/demo-script.md`
- `docs/**`
- `spec/**`
- `progress/**`
- `spec.json`
- `.harness/interviews/**`

## Enfoque

- **data_model:** no se crean nuevos datos; se presenta el snapshot materializado existente
- **external_contracts:** rutas `/landing`, `/overview?layer=episodes` y detalle ADM1
- **edge_cases:** margen de 15 segundos y regla para omitir esperas/cargas
- **ui_states:** episodio activo, área evaluada sin episodio y horizontes de continuidad

## Decisiones de la entrevista

- **audience:** El vídeo está dirigido al jurado del IGAD Hackathon 2026 y debe poder entenderse sin contexto previo ni explicación adicional.
- **duration:** La duración máxima es 3:00. El guion objetivo durará 2:45 para conservar 15 segundos de margen de grabación y edición.
- **route:** El recorrido principal usa el build final: landing, Overview con `Persistent episodes` y detalle ADM1 de Bay. Debe mostrar la diferencia entre áreas evaluadas sin episodio y áreas activas con continuidad a 30, 60, 90 y 180 días.
- **product_truth:** No se mostrarán Reports, Admin ni notificaciones simuladas porque ya no forman parte de la superficie diferencial final. La narración distinguirá observación satelital, referencia histórica y predicción ML experimental.
- **recording:** El documento incluirá texto literal, acción visible, ruta, duración por bloque, preparación previa, fallback con capturas y una lista de comprobación antes de exportar.
- **security:** La grabación no mostrará consola, credenciales, datos privados, barras de favoritos ni pestañas ajenas al producto.
