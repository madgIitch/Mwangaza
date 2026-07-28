# Probabilistic Risk Engine Roadmap

Mwangaza will evolve the existing experimental deterministic forecast through Sprints 61-65. This is an additive post-1.0 capability; Sprints 36 and 37 remain unchanged.

## Scientific claim

The primary target is:

`P(the same officially observed drought episode remains active at horizon h | active at as_of)`

It is not onset probability, exact duration, humanitarian impact, agricultural loss or
affected population. Targets come from validated operational drought phases; missing
coverage remains unknown and never becomes recovery.

## Minimum product

- One binary target: `same_episode_continues`.
- Dekadal feature rows aligned to validated operational phase coverage.
- Four horizons: 30, 60, 90 and 180 days.
- HGB+Platt may compete only at 30 days.
- `phase_survival` is the approved baseline and the only route at 60/90/180 days.
- Nested temporal evaluation with separate base-fit, calibration and evaluation episodes.
- Core metrics: Brier score, Brier Skill Score, log loss, calibration bins and ECE.
- One read-only endpoint, one compact Region module and report integration.
- Up to three non-causal drivers.
- Strict abstention whenever validated skill or data quality is insufficient.

## Delivery sequence

1. Sprints 61-62C materialize leakage-safe history and antecedent signals.
2. Sprints 62D-62F build independent drought episodes and evaluate continuation.
3. Sprint 63 calibrates the 30-day ML candidate and freezes hybrid routing.
4. Sprint 64 materializes continuation estimates, drivers and the read-only API.
5. Sprint 65 integrates ML, baseline, fallback and abstention into Region and Reports.

## Sprint 61 implementation

`mwangaza.probabilistic.dataset` builds an immutable, deterministic training dataset from already materialized historical periods. It supports monthly and dekadal frequencies, exact contiguous lags, three future horizons, temporal features, lineage, structured null reasons and atomic canonical JSON output with SHA-256.

Future observations may determine a target but cannot enter the feature vector for an earlier `as_of`. Gaps remain gaps; unknown or quality-blocked future levels remain null labels and are never coerced to the negative class.

Dekadal is the primary training cadence. Daily CHIRPS observations are aggregated into rainfall features inside each 10-day period; they do not create duplicate daily training rows. MODIS NDVI and LST retain their actual `observed_at`, and the dataset exposes `*_age_days` so an older composite is never presented as a new observation. Monthly remains a secondary reporting-compatible frequency.

## Sprint 62 implementation

`mwangaza.probabilistic.training` evaluates persistence, seasonal climatology, historical frequency, logistic regression and histogram gradient boosting independently for horizons of 10, 20 and 30 days.

Walk-forward folds use globally shared dekadal dates. Every fold leaves a gap equal to its forecast horizon; preprocessing, median imputation, scaling and region encoding are learned only from the training side. New regions are treated as unknown categories rather than causing failure or borrowing another region's identity.

Selection uses out-of-sample Brier score. An ML model is selected only when it improves persistence, seasonal climatology and historical frequency; otherwise the horizon is retained as `rejected_insufficient_skill`. Runs record dataset and feature hashes, threshold versions, seed, scikit-learn version, folds, parameters, OOF probabilities and a canonical run hash. This sprint does not publish probabilities.

## Real historical backfill

`scripts/backfill_probabilistic_history.py` materializes regional aggregates from Google Earth Engine without downloading source rasters. The default pilot covers Kenya from `2024-01-01` through the last complete dekad. `--dry-run` is offline; a real extraction requires `--confirm-remote`. Local outputs under `data/historical/` are ignored by Git.

CHIRPS Daily is accumulated inside exact calendar dekads. MODIS MOD13Q1 NDVI and MOD11A2 LST use the latest composite whose source timestamp is not later than the dekad `as_of`; output rows preserve `observed_at` and `age_days`. Missing upstream signals remain null with structured reasons. JSONL writes are atomic and each completed chunk acts as a resumable checkpoint. The canonical manifest records collections, coverage, counts and the SHA-256 of the local data file.

The validated Kenya run on 2026-07-24 produced 92 rows through `2026-07-20`. The two July 2026 CHIRPS periods were not yet present upstream and remain explicit `rainfall_no_data`; no zero was invented. This raw signal history is not yet an independent drought-event label catalog.

The subsequent full IGAD run produced 736 valid JSONL rows, 92 for each of the eight countries. There are 720 complete rows and 16 explicit CHIRPS absences corresponding to the two latest dekads in every country. Raw observations must not be passed directly to the classifier: dekadal seasonal climatologies, anomaly transformations and versioned risk labels are required first. In particular, the live composite scorer is not a substitute for this step because its generic raw-value path does not define a historical anomaly label.

### Reproducible treatment and training commands

All long-running scripts print completed/total units, percentage and ETA. Download the independent `2003-2023` seasonal reference first:

```powershell
uv run python scripts/backfill_probabilistic_history.py --scope igad --start 2003-01-01 --end 2023-12-31 --output data/historical/gee-baseline-2003-2023 --chunk-size 24 --confirm-remote
```

Then derive 36 dekadal climatologies per region, orient anomalies so rainfall/NDVI deficits and LST excess increase risk, create versioned `green/yellow/orange/red` labels, and build the three-horizon dataset:

```powershell
uv run python scripts/prepare_probabilistic_dataset.py
```

Inspect the printed target counts before training. If every horizon lacks both classes, the run must stop rather than weakening thresholds silently. Train candidates and persist the reproducible evaluation:

```powershell
uv run python scripts/train_probabilistic_model.py
```

The prepared dataset is written to `data/historical/probabilistic-training.json`; the training run goes to `data/models/probabilistic-training-run.json`. Both are local ignored artifacts. Treatment version `igad-dekadal-2003-2017-v2`, score version `probabilistic-composite-v1`, and threshold version `probabilistic-risk-thresholds-v3-2003-2017-quantiles` are preserved in lineage.

Threshold v2 uses country-level P75/P90/P97.5 of valid `2003-2023` baseline scores for yellow/orange/red. Exact values are frozen before labeling 2024 onward, so current observations cannot tune their own target.

The first v2 run produced three severe observations: Eritrea 2025-06-30, Kenya 2025-12-10 and Sudan 2025-06-10. ML did not beat historical frequency in any horizon, so all horizons remain `rejected_insufficient_skill`. Sparse positives and very small Brier differences prohibit publishing a model from this run.

Threshold v3 freezes climatology and cuts on `2003-2017`, then labels the disjoint `2018-2026` period. It produces 2,464 labeled observations, 7,392 horizon rows and 86 severe targets per horizon. Despite the larger positive class, ML still does not beat historical frequency: the final status remains `rejected_insufficient_skill` for 10, 20 and 30 days. Training progress is reported by walk-forward fold so long runs expose a meaningful ETA.

## ADM1 antecedent feature pipeline

Sprint 62C changes the information available to a future model instead of trying more estimators on the national feature set. `scripts/backfill_adm1_antecedent_signals.py` materializes one source row per complete calendar dekad and each of the 121 version-pinned IGAD ADM1 units. Earth Engine requests batch both regions and windows; every completed batch is written atomically and can be resumed. The raw extraction starts in July 2002 to provide the six-month warm-up required by SPI; the prepared, publishable artifact continues to start on 1 January 2003.

The backfill contains CHIRPS rainfall, MOD13Q1 NDVI, SPEIbase 1/3/6 month values, FLDAS top-layer/root-zone soil moisture and evapotranspiration rate, plus ECMWF IFS cumulative precipitation forecasts at 240 and 360 hours where historically available. Monthly values keep native timestamps. MOD13Q1 is admitted only after its full 16-day composite closes, so a source start timestamp cannot hide future pixels. Forecasts keep creation time and lead and never populate `observed_at`.

Run an offline plan first:

```powershell
uv run python scripts/backfill_adm1_antecedent_signals.py --dry-run
```

Then start or resume the complete extraction:

```powershell
uv run python scripts/backfill_adm1_antecedent_signals.py --confirm-remote
```

The default raw extraction covers `2002-07-01` through the last complete dekad; the first six months are warm-up and are excluded from the prepared artifact. Progress is measured in ADM1/dekad rows and prints an ETA. To validate a small remote slice before the long run, repeat `--region`:

```powershell
uv run python scripts/backfill_adm1_antecedent_signals.py --region adm1-ke-43 --region adm1-so-hi --start 2025-01-01 --end 2025-01-31 --output data/historical/adm1-smoke --confirm-remote --force
```

Prepare leakage-safe features after the backfill:

```powershell
uv run python scripts/prepare_adm1_probabilistic_dataset.py
```

Preparation derives empirical SPI 1/3/6, cumulative rainfall deficits 1/3/6, seasonal NDVI anomaly, consecutive negative-anomaly persistence and 3/6-dekad OLS velocity. SPI and climatologies use only complete windows from the reference period ending `2017-12-31`. First and second dekads therefore use the latest prior complete month; no future part of the current month enters the feature vector. This artifact contains features only: it does not train, publish probabilities or create labels from the Mwangaza score.

## Independent label catalog

Sprint 62D materializes external evidence without deriving targets from the Mwangaza score. Food-security outcomes (`acute_food_insecurity_impact`) and drought evidence (`drought_hazard_event`) are separate semantics. FEWS NET and IPC assessed phases never become drought labels automatically; missing coverage is unknown and never phase 1 or a negative event.

Plan or smoke the public FEWS NET adapter first:

```powershell
uv run python scripts/import_independent_labels.py --source fews --country KE --dry-run
uv run python scripts/import_independent_labels.py --source fews --country KE --page-size 1 --page-limit 1 --output data/historical/independent-labels-smoke
```

Run the resumable IGAD download by omitting `--country` and `--page-limit`:

```powershell
uv run python scripts/import_independent_labels.py --source fews
```

IPC is fail-closed and needs an explicitly configured `IPC_API_KEY` plus the approved area endpoint. Official drought phases/declarations use `--official-input` with a reviewed JSON manifest. EM-DAT uses `--emdat-input`, `--emdat-access-date` and the applicable registered-access license. Downloaded rows, geometries, spatial-match checkpoints and final JSONL artifacts remain under ignored `data/historical/` paths.

FEWS/IPC geometries are intersected with the pinned ADM1 catalog. Simple geometries use planar polygon intersection; complex provider boundaries use a deterministic fixed-budget grid intersection so full-history processing stays bounded. Each mapped label records source and ADM1 fractions, unmatched source fraction, method and rule version. Country-only FEWS units and EM-DAT events without explicit ADM1 identifiers are not propagated to every ADM1.

## Non-negotiable gates

No percentage is published when any approved gate fails, including insufficient history or positive cases, blocked current quality, non-positive skill against climatology, unacceptable calibration, material drift, unsupported horizon, regional under-representation, corrupt artifacts or version/hash mismatch.

The public unavailable state is:

`Probability unavailable - insufficient validated skill for this region and horizon.`

Unavailable never means zero probability.

## Deferred decisions for SDD interviews

- Exact period frequency and minimum history/event counts.
- Skill improvement margin and calibration-quality thresholds.
- Drift metric, reference distribution and threshold.
- Encoding and minimum representation for regions.
- Artifact serialization and signing/verification strategy.
- Explanation method for histogram gradient boosting.
- Probability bands and user-facing confidence mapping.
- Whether an independently validated drought-event catalog becomes available later.
- Multiclass probabilities and isotonic calibration; neither belongs to Sprints 61-65 without a new approved contract.
## Catálogo de hazard real (Sprint 62D.2)

Las fases operativas de NDMA y los eventos de EM-DAT se mantienen separados de las
etiquetas FEWS/IPC: los primeros tienen semántica `drought_hazard_event`; los segundos
siguen siendo `acute_food_insecurity_impact`. Ninguna de estas etiquetas entra todavía
en entrenamiento.

El backfill de NDMA recorre el archivo oficial mensual de County Bulletins de 2016 hasta
el mes solicitado. Los índices, PDFs y checkpoints quedan bajo `data/historical/`, fuera
de Git. Cada descarga se reanuda, muestra ETA y conserva URL y SHA-256. Para leer PDFs se
usa `pypdf` de forma explícita:

```powershell
uv run --with pypdf python scripts/backfill_ndma_drought_phases.py --start 2016-01
```

Solo se valida una observación cuando el PDF contiene el condado y periodo esperados y
una única fila textual `COUNTY <Normal|Alert|Alarm|Emergency|Recovery>`. El resto queda
en `review-queue.jsonl`; no se convierte en negativo. Después se normaliza el manifiesto:

```powershell
uv run python scripts/import_independent_labels.py `
  --source official `
  --official-input data/historical/ndma-drought-phases/official-manifest.json `
  --output data/historical/drought-hazard-labels
```

EM-DAT no se descarga ni autentica automáticamente. Tras descargar el Public Table con
una cuenta registrada y guardarlo como CSV UTF-8, se incorpora junto a NDMA así:

```powershell
uv run python scripts/import_independent_labels.py `
  --source official `
  --official-input data/historical/ndma-drought-phases/official-manifest.json `
  --source emdat `
  --emdat-input C:\ruta\al\emdat-public-table.csv `
  --emdat-access-date 2026-07-27 `
  --output data/historical/drought-hazard-labels
```

Un evento EM-DAT sin ADM1 explícita se conserva como evidencia nacional. Un nombre ADM1
explícito solo se acepta si coincide con el catálogo versionado; ubicaciones libres y
unidades ADM2 no se promueven a ADM1.

La auditoría agrupa únicamente `Alert`, `Alarm` y `Emergency` contiguos. `Normal` y
`Recovery` demuestran cobertura, pero no inflan episodios. EM-DAT y NDMA nunca se mezclan:

```powershell
uv run python scripts/audit_drought_hazard_episodes.py `
  --labels data/historical/drought-hazard-labels
```

El resultado separa episodios ADM1, evidencia nacional, observaciones no validadas,
observaciones sin hazard activo, desacuerdos y países cuya cobertura sigue desconocida.

## Evaluación por episodios reales (Sprint 62E)

La evaluación consume las 102.608 filas ADM1 de antecedentes, las etiquetas
NDMA validadas y los episodios auditados. Solo Alert/Alarm/Emergency son target
activo; Normal/Recovery son inactivos y cualquier hueco de cobertura es unknown.
Los splits walk-forward globales conservan cada episodio completo en un solo fold.

```powershell
uv run python scripts/evaluate_drought_episodes.py
```

El CLI alinea targets y entrena persistencia, climatología estacional, frecuencia
histórica, regresión logística e histogram gradient boosting para 10, 20 y 30
días. Escribe `oof-predictions.jsonl`, `predicted-episodes.jsonl`,
`evaluation.json` y `manifest.json` bajo
`data/historical/drought-episode-evaluation/`, con ETA y hashes de entradas/salidas.

La corrida real del 28 de julio de 2026 alineó 20.364 filas conocidas y evaluó
98 episodios fuera de muestra. Persistencia ganó los tres horizontes. Regresión
logística obtuvo Brier/F1 de 0,118637/0,680 a 10 días, 0,126405/0,659 a 20 y
0,136091/0,645 a 30, frente a persistencia 0,045710/0,740,
0,088478/0,720 y 0,129962/0,646. Ambos ML quedaron rechazados; serving sigue
deshabilitado. Run hash:
`sha256:552e25e16d6000dbd2b5b2da79a83c252d209550bed1b8377cea1a455cbdfc03`.

## Probabilidad de continuidad de sequía (Sprint 62F)

62F responde a la pregunta operativa principal: dada una sequía oficialmente activa en
una fecha `as_of`, ¿qué probabilidad hay de que el mismo episodio siga activo dentro de
30, 60, 90 o 180 días? El risk set solo contiene fechas cubiertas por una fase NDMA
validada. Una fase Normal/Recovery o un mes sin observación separa episodios; los huecos
no se convierten en recuperación ni en negativos.

```powershell
uv run python scripts/evaluate_drought_survival.py `
  --evaluated-at 2026-07-28T00:00:00Z
```

La validación usa episodios 2021-2023 y deja 2024+ sellado. Tras congelar código y el
hash de validación, el holdout solo puede abrirse una vez con
`--unlock-final-holdout --frozen-validation-run-hash <hash>`. Las probabilidades por
muestra se proyectan a una curva no creciente y se comparan con always-active,
supervivencia empírica por tiempo transcurrido y supervivencia por fase.

En validación, `phase_survival` ganó con Brier integrado 0,179043; logistic regression
y HGB obtuvieron 0,220786 y 0,240212. En el holdout de 29 episodios, HGB mejoró el Brier
integrado del mejor baseline (0,265225 frente a 0,296562) y el MAE de recuperación
(94,9 frente a 133,3 días), pero empeoró el horizonte de 180 días (0,305341 frente a
0,206369). El gate completo lo rechaza y serving permanece deshabilitado. No se ajusta
el modelo después de conocer este holdout.

## Calibración y routing híbrido (Sprint 63)

La calibración se ejecuta sin leer predicciones del holdout 2024+. Para cada año de
evaluación 2021-2023, HGB se ajusta antes del año de calibración, Platt usa únicamente
el año inmediatamente anterior y la evaluación usa episodios completos del año
siguiente. Los episodios de frontera y targets censurados se excluyen.

```powershell
uv run python scripts/calibrate_drought_continuation.py `
  --evaluated-at 2026-07-28T00:00:00Z
```

La corrida real generó 2.955 filas pre-holdout y 255 predicciones OOF. A 30 días,
`phase_survival` obtuvo Brier 0,195348 y ECE 0,098291; HGB sin calibrar obtuvo Brier
0,197150 y BSS -0,009222; HGB+Platt obtuvo Brier 0,249860, BSS -0,279051 y ECE
0,197380. El gate rechaza ML por skill no positivo, degradación tras calibrar y ECE por
encima de 0,15. Los cuatro horizontes quedan en `phase_survival`; no se serializa ningún
modelo ML. Run hash:
`sha256:5981338901de379c9943fd2f30b826d0ede687eccff5489657210476e4e74d39`.
