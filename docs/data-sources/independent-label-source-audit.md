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

Training defaults:

- Accept only `scenario=CS` (Current Situation / assessed).
- Reject `ML1`, `ML2`, `FIPE6` and other projected scenarios as labels.
- Preserve `created`, `collection_status_changed` and reporting/validity dates;
  a classification cannot be visible before publication.
- Preserve `classification_scale`; FEWS NET classifications are IPC-compatible
  but are not necessarily IPC consensus results.
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
