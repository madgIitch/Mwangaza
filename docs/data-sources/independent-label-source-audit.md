# Independent label source audit

Reviewed on 2026-07-25 for the future Sprint 62D. This document records
what can actually be accessed and what each source means. It does not approve
or implement the feature.

## Non-negotiable semantic split

Independent means independent from the Mwangaza feature-derived score. It does
not mean that all external sources measure the same phenomenon, or that FEWS
NET and IPC are mutually independent.

The normalized catalog must preserve at least two targets:

1. `drought_hazard_event`: an observed/declared drought episode from an
   official authority or a validated disaster catalog.
2. `acute_food_insecurity_impact`: an assessed current outcome from FEWS NET
   or IPC.

IPC/FEWS Phase 3+ must never be relabelled as drought without separate,
source-backed drought attribution. Conflict, displacement, markets, disease
and assistance can cause or alter acute food insecurity. Conversely, an
EM-DAT drought record does not prove that every ADM1 in the country was
affected.

## FEWS NET

- Official API documentation:
  `https://help.fews.net/fde/v3/fews-net-api`
- Public assessed classifications endpoint:
  `https://fdw.fews.net/api/ipcphase/`
- Public geometry endpoint:
  `https://fdw.fews.net/api/feature.geojson`
- Historical GIS downloads date back to June 2009; country-specific files
  start in October 2020. Regional files can cover earlier country history.
- Anonymous API access was verified on 2026-07-25. A Kenya query for
  `collection_date=2024-06-01&scenario=CS` returned published public rows and
  retained `source_organization`, source document, collection/reporting dates,
  projection interval, scenario, scale, phase, FNID and usage policy.
- FNID geometry resolution was verified for
  `KE2016C312010019` through `feature.geojson`.

### Verified IGAD coverage snapshot

An anonymous `scenario=CS&page_size=1` count was queried on 2026-07-25 for
every enabled country:

| ISO2 | Country | Public CS records |
|---|---|---:|
| DJ | Djibouti | 401 |
| ER | Eritrea | 0 |
| ET | Ethiopia | 40,416 |
| KE | Kenya | 28,358 |
| SO | Somalia | 11,536 |
| SS | South Sudan | 3,993 |
| SD | Sudan | 8,398 |
| UG | Uganda | 18,412 |
|  | **Total** | **111,514** |

These are source records, not usable ADM1/dekad labels. The counts include
Admin-0 rows, multiple source documents, changing boundary versions,
classification scales and alternative humanitarian-assistance variants.
Normalization must deduplicate only through explicit source identity and must
preserve differing classifications rather than selecting a maximum phase.

Eritrea has no public FEWS NET CS rows in this endpoint, so its coverage is
unknown rather than negative. Query latency also varied materially (the
one-row Ethiopia count took roughly 27 seconds), making pagination,
checkpointing, retry and ETA mandatory for the eventual downloader.

Training defaults:

- Accept only `scenario=CS` (Current Situation / assessed).
- Reject `ML1`, `ML2`, `FIPE6` and other projected scenarios as labels.
- Preserve `created`, `collection_status_changed` and reporting/validity dates;
  a classification cannot be visible before publication.
- Preserve `classification_scale`; FEWS NET classifications are IPC-compatible
  but are not necessarily IPC consensus results.
- Preserve `is_allowing_for_assistance`; assisted and counterfactual/no-
  assistance variants are distinct observations and cannot silently overwrite
  each other.
- Map source geometries to the pinned ADM1 catalog by area overlap, recording
  numerator, denominator, method and unmatched area. Never join by name alone.
- Values `66`, `88`, `99`, missing geometry and unpublished collections are
  unknown/excluded, not negative.

## IPC / CH

- OpenAPI contract:
  `https://docs.api.ipcinfo.org/api/public/openapi.json`
- Production API: `https://api.ipcinfo.org`
- Advanced endpoints expose analysis metadata and area GeoJSON by analysis ID
  and period.
- `period=C` is current/assessed; `P` and `A` are projections.
- The contract exposes phase, validity interval, analysis creation date,
  geometry, population and Phase 3+ population/percentage.
- An anonymous Kenya request was verified to return
  `API_KEY_MISSING`; ingestion therefore requires an explicitly configured IPC
  API key and must fail closed when it is absent.
- The OpenAPI document is Apache-2.0, but IPC results are governed by the IPC
  API Terms of Use and licensed CC BY-NC-SA 3.0 IGO. The data license, not the
  documentation/software license, controls stored results.

Training defaults:

- Use only acute food insecurity analyses and assessed/current period `C`.
- Preserve analysis ID, creation/modification dates and exact validity window.
- Never backfill an unpublished month or extend a validity interval.
- Preserve FEWS/IPC disagreement as separate source observations. A merge rule
  must be versioned and cannot silently select the highest phase.

## Official drought classifications and declarations

Kenya's National Drought Management Authority (NDMA) provides an official,
public county bulletin archive:

`https://knowledgeweb.ndma.go.ke/Public/Resources/CountyBulletins.aspx?ID=11`

The archive contains monthly county Drought Early Warning bulletins. A
Marsabit bulletin for December 2025 was verified to identify its county-level
`DROUGHT EW PHASE: ALERT`, phase trend, period end and publication date.
NDMA response guidelines define Normal, Alert, Alarm, Emergency and Recovery
phases.

These are official operational phase classifications, not automatically legal
state-of-emergency declarations. The normalized record must therefore retain:

- issuing authority and jurisdiction;
- document URL/hash and publication date;
- declared phase and the authority's phase taxonomy;
- valid/reference period;
- whether the record is an `official_operational_phase` or a legally explicit
  `official_emergency_declaration`;
- reviewer/verification status.

Other IGAD authorities use heterogeneous portals and documents. Sprint 62D
must support a validated local manifest for official declarations rather than
scraping arbitrary news or treating a search-result absence as a negative.

## EM-DAT

- Documentation: `https://doc.emdat.be/docs/data-accessibility/`
- Public table fields:
  `https://doc.emdat.be/docs/data-structure-and-content/emdat-public-table/`
- The living public table is updated weekly. Non-commercial access is free
  after registration and acceptance of the Terms of Use; commercial use
  requires the applicable paid license.
- The public table has event IDs, disaster type, start/end components,
  source-backed location and optional GADM 4.1 administrative units. Drought is
  an explicit disaster type.
- Human/economic impacts remain country-level even when occurrence is
  geocoded to ADM1/ADM2. Empty impact cells may mean zero or unknown and cannot
  be coerced to zero.
- The anonymous HDX country profiles are annual aggregates. They are useful
  for audit totals but cannot replace event-level public-table data for episode
  labels.

Ingestion must therefore be a local registered-file import by default. It must
record the access date, source artifact hash, license mode and EM-DAT event ID,
and map only explicitly listed GADM/GAUL units or reviewed source locations.
Country-only drought records remain country evidence; they are not copied to
all ADM1 units.

## Minimum normalized label contract

Every source observation needs:

- `source`, `source_version`, `source_record_id`, `source_url`;
- `label_semantics` (`drought_hazard_event` or
  `acute_food_insecurity_impact`);
- `assessment_status` (`assessed`, `projected`, `official_phase`,
  `official_declaration`, `validated_catalog_event`);
- `issued_at`, `valid_from`, `valid_to`, and source retrieval time;
- original taxonomy/value and normalized value;
- source geometry/administrative identifiers;
- ADM1 overlap fractions and mapping method/version;
- document/artifact SHA-256 and license/usage policy;
- quality, review status and structured exclusion reason.

An absent row, source outage, uncovered geography or unlicensed source is
`unknown`. It is never a negative label.
## Extensión de hazard real - 2026-07-27

- NDMA Kenya: archivo oficial público de County Drought Early Warning Bulletins,
  2016-presente. Adapter implementado con selección mensual WebForms, PDF oficial,
  checkpoint, SHA-256 y extracción conservadora. Fuente:
  https://knowledgeweb.ndma.go.ke/Public/Resources/CountyBulletins.aspx?ID=11
- EM-DAT: el Public Table requiere registro; Mwangaza solo acepta el CSV que aporte el
  usuario y no automatiza login ni redistribución. `Admin Units` y `GADM Admin Units` son
  JSON; la evidencia nacional no se replica a ADM1. Documentación:
  https://doc.emdat.be/docs/data-structure-and-content/emdat-public-table/ y
  https://doc.emdat.be/docs/data-accessibility/
- Las demás autoridades se registran en `igad-drought-authorities.json`. Tener una
  autoridad verificada no implica que exista una serie pública utilizable. Todo hueco se
  clasifica `unknown`, nunca `no drought`.

Smoke público del 27 de julio de 2026: junio de 2026 devolvió 23 boletines; el primer PDF
(Baringo) produjo una fase `Normal` validada y, correctamente, cero episodios de sequía
activa. El manifiesto del smoke tuvo SHA-256
`sha256:bca43eace2c8199c385a371a5523e8971b13fd9a8f2f4950e348f58cf8d4c785`.

El PDF oficial de Laikipia de octubre de 2016 se sirve truncado (sin marcador
terminal `%%EOF`) incluso tras descargarlo de nuevo. El backfill valida la
integridad antes de extraer texto, realiza dos descargas de reparación y, si la
fuente sigue sirviendo un documento incompleto, conserva su hash en la cola
`review_required` y continúa con el resto del archivo.

Incidencia verificada durante el backfill: junio de 2020 contiene dos filas idénticas
para el mismo PDF de Taita/Taveta (`8a9e38f1-466c-4635-b8c2-e29b1ed61304`). Se conserva
una sola observación. El adapter solo aplica esta deduplicación cuando todos los campos
normalizados coinciden; un UUID con metadatos distintos sigue siendo un error.

Incidencia verificada el 28 de julio de 2026: el enlace oficial del boletín de
Tharaka-Nithi de agosto de 2022 (`c759391a-f98f-4650-8639-ebd24b4f6ceb`)
devuelve HTTP 404 tras los reintentos. El índice y la URL se conservan como
`document_unavailable_after_retries` en `review_required`; la ausencia del PDF
no se interpreta como una fase negativa y no detiene el resto del backfill.
