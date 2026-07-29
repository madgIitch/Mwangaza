# Guion de vídeo — Mwangaza

Duración objetivo: **2:45**. Límite absoluto: **3:00**.

Idioma de narración: español. El texto entre comillas es literal; las instrucciones entre
corchetes no se narran.

## Recorrido cronometrado

### 0:00–0:18 — Apertura y problema

**Pantalla:** `/landing`, encuadre completo del hero. Deja el cursor quieto.

**Narración:**

> “Mwangaza transforma observaciones satelitales en una pregunta operativa muy concreta:
> dónde hay una condición de sequía activa y qué probabilidad existe de que continúe el
> tiempo suficiente como para justificar una acción temprana.”

### 0:18–0:35 — Cobertura homogénea

**Acción:** desplázate hasta el bloque “Eight countries. 121 ADM1 areas. One method”.

**Narración:**

> “Aplicamos el mismo método a los ocho países de IGAD y a sus ciento veintiuna áreas
> administrativas de primer nivel. Todas se evalúan; no dependemos de que exista un
> boletín oficial para ofrecer cobertura.”

### 0:35–0:55 — Entrada directa a los episodios

**Acción:** pulsa `View persistent episodes`. Espera a que aparezca Overview y no narres
durante ninguna pantalla de carga.

**Narración:**

> “La vista de episodios persistentes elimina ruido para el evaluador. En violeta aparecen
> las áreas con una condición activa; las áreas neutras también fueron analizadas, pero no
> presentan ahora un episodio al que asignar una probabilidad de continuidad.”

### 0:55–1:15 — Priorización regional

**Pantalla:** `/overview?layer=episodes`. Señala brevemente el mapa, la leyenda y la llamada
`Open persistent episodes · Somalia`.

**Narración:**

> “Así podemos pasar de una visión regional a una lista de casos que merece atención. El
> mapa no confunde riesgo general con persistencia: primero determina si existe una
> condición satelital activa y solo entonces calcula su posible continuación.”

### 1:15–1:35 — Drilldown hasta Bay

**Acción:** abre Somalia, selecciona `Bay` y mantén activa la capa `Persistent episodes`.
Si el enlace ya está preparado, cambia directamente a esa pestaña.

**Narración:**

> “Entramos en Somalia y seleccionamos Bay. La unidad aparece destacada porque mantiene
> un episodio observado. El resto del país permanece visible para conservar el contexto y
> distinguir rápidamente episodios activos de áreas evaluadas sin episodio.”

### 1:35–2:08 — Continuidad y horizontes

**Pantalla:** detalle ADM1 de Bay. Señala `10 active days observed`, selecciona sucesivamente
30, 60, 90 y 180 días, dejando aproximadamente dos segundos en cada horizonte.

**Narración:**

> “Aquí está la aportación principal. Mwangaza estima si este mismo episodio seguirá activo
> dentro de treinta, sesenta, noventa o ciento ochenta días. A treinta días, el modelo
> experimental muestra la probabilidad junto a una referencia histórica separada. Al
> cambiar de horizonte podemos ver cómo evoluciona la evidencia sin convertirla en una
> certeza ni predecir una fecha exacta de finalización.”

### 2:08–2:30 — Evidencia, frescura y límites

**Acción:** vuelve a 30 días y despliega `Associations and validation` u `Observation dates
and freshness`, según cuál quede mejor encuadrado.

**Narración:**

> “Cada resultado conserva procedencia, fecha efectiva de observación, antigüedad y calidad
> por señal. La consulta puede ejecutarse hoy aunque la última observación válida sea
> anterior. El aprendizaje automático se etiqueta como experimental y se compara con el
> histórico; NDMA se usa como validación externa y FEWS NET como evidencia de impacto.”

### 2:30–2:45 — Cierre

**Pantalla:** mantén Bay y sus probabilidades visibles. No muevas el cursor durante la última
frase.

**Narración:**

> “Mwangaza no sustituye el criterio local. Hace visible qué condiciones persisten, dónde
> mirar primero y con qué evidencia decidir. Ese es el paso de observar la sequía a actuar
> antes.”

## Preparación antes de grabar

1. Abre únicamente estas tres pestañas y déjalas cargadas:
   - `http://127.0.0.1:5173/landing`
   - `http://127.0.0.1:5173/overview?layer=episodes`
   - el detalle de Somalia, Bay, con `Persistent episodes` activo
2. Comprueba que la cabecera identifica correctamente si los datos son live o materializados.
3. En Bay, verifica que aparecen los cuatro horizontes y la probabilidad a 30 días.
4. Usa una ventana de navegador limpia, zoom al 100 %, sin favoritos ni otras pestañas.
5. Oculta consola, terminal, correos, credenciales y notificaciones del sistema.
6. Graba a 1080p y 30 fps como mínimo; activa `No molestar`.
7. Haz una prueba en seco. Si supera 2:45, acorta pausas, no aceleres la voz.

## Fallback estable

Si una consulta o transición falla, no grabes la espera. Sustituye el tramo por las capturas
versionadas en `assets/pitch/`:

- `01-landing-final.png`
- `02-overview-persistent-episodes.png`
- `03-adm1-continuation-evidence.png`

Mantén la misma narración. Las capturas deben ocupar todo el encuadre útil y no deben
presentarse como una consulta ejecutada durante la grabación.

## Subtítulos y verificación final

- Usa esta narración como base de subtítulos y corrige manualmente `Mwangaza`, `IGAD`,
  `ADM1`, `Bay`, `NDMA` y `FEWS NET`.
- Mantén cada subtítulo en un máximo de dos líneas y evita tapar cifras, leyendas y botones.
- Exporta en MP4 H.264, 1080p, con audio AAC y duración inferior o igual a 3:00.
- Reproduce el archivo completo después de exportarlo y comprueba audio, sincronización,
  legibilidad y ausencia de información privada.
- Si se sube a una plataforma, abre el enlace final en una ventana privada sin autenticar.

## Claims que no deben improvisarse

- No decir que Mwangaza predice el inicio de una sequía.
- No decir que conoce su duración exacta ni el impacto humano futuro.
- No presentar la referencia histórica como ML.
- No presentar el ML experimental como validado para uso operativo.
- No llamar “dato actual” a una señal sin mostrar o explicar su fecha efectiva.
