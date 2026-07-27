from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from mwangaza.probabilistic.spatial_overlap import (
    OVERLAP_RULE_VERSION,
    GeometryError,
    geometry_complexity,
    geometry_overlap,
    sampled_geometry_overlaps,
)

LABEL_SCHEMA_VERSION = "mwangaza.independent-label.v1"
FEWS_SOURCE_VERSION = "FEWS NET Data Explorer API v3"
IPC_SOURCE_VERSION = "IPC public API"
OFFICIAL_SOURCE_VERSION = "official-label-manifest-v1"
EMDAT_SOURCE_VERSION = "EM-DAT public table"
UNKNOWN_FEWS_VALUES = {66, 88, 99}


class LabelImportError(RuntimeError):
    """Raised when a source cannot be normalized without inventing evidence."""


@dataclass(frozen=True)
class SpatialMatch:
    adm1_region_id: str
    source_fraction: float
    adm1_fraction: float
    mapping_method: str = "planar_polygon_intersection"


@dataclass(frozen=True)
class IndependentLabel:
    label_id: str
    source: str
    source_version: str
    source_record_id: str
    source_url: str
    label_semantics: str
    assessment_status: str
    issued_at: str
    valid_from: str
    valid_to: str
    original_taxonomy: str
    original_value: str
    normalized_value: str
    source_geometry_id: str | None
    adm1_region_id: str | None
    overlap_source_fraction: float | None
    overlap_adm1_fraction: float | None
    mapping_method: str | None
    mapping_version: str | None
    artifact_sha256: str
    license_policy: str
    quality: str
    review_status: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class LabelExclusion:
    source: str
    source_record_id: str
    reason: str
    detail: str


def map_geometry_to_adm1(
    geometry: dict[str, Any],
    regions: Iterable[object],
    *,
    min_source_fraction: float = 0.001,
) -> tuple[SpatialMatch, ...]:
    region_values = tuple(regions)
    target_geometries = tuple(getattr(region, "geometry") for region in region_values)
    try:
        use_sampling = geometry_complexity(geometry) + max(
            (geometry_complexity(target) for target in target_geometries), default=0
        ) > 400
        overlaps = (
            sampled_geometry_overlaps(geometry, target_geometries)
            if use_sampling
            else tuple(geometry_overlap(geometry, target) for target in target_geometries)
        )
    except GeometryError as exc:
        raise LabelImportError(str(exc)) from exc
    method = "deterministic_grid_intersection" if use_sampling else "planar_polygon_intersection"
    matches: list[SpatialMatch] = []
    for region, overlap in zip(region_values, overlaps, strict=True):
        if overlap.source_fraction >= min_source_fraction:
            matches.append(
                SpatialMatch(
                    adm1_region_id=str(getattr(region, "id")),
                    source_fraction=round(overlap.source_fraction, 8),
                    adm1_fraction=round(overlap.target_fraction, 8),
                    mapping_method=method,
                )
            )
    if sum(match.source_fraction for match in matches) > 1.02:
        raise LabelImportError("ambiguous ADM1 mapping: overlapping target boundaries")
    return tuple(sorted(matches, key=lambda item: item.adm1_region_id))


def normalize_fews_record(
    record: dict[str, Any],
    *,
    matches: tuple[SpatialMatch, ...],
    geometry_hash: str,
) -> tuple[tuple[IndependentLabel, ...], LabelExclusion | None]:
    record_id = str(record.get("id", ""))
    if record.get("scenario") != "CS":
        return (), LabelExclusion("FEWS NET", record_id, "projected_scenario", str(record.get("scenario")))
    value = record.get("value")
    if value is None or int(float(value)) in UNKNOWN_FEWS_VALUES:
        return (), LabelExclusion("FEWS NET", record_id, "unknown_phase_value", str(value))
    if record.get("collection_status") != "Published":
        return (), LabelExclusion("FEWS NET", record_id, "unpublished_collection", str(record.get("collection_status")))
    if str(record.get("fnid") or "") == str(record.get("country_code") or ""):
        return (), LabelExclusion("FEWS NET", record_id, "source_unit_too_coarse", "admin0")
    if not matches:
        return (), LabelExclusion("FEWS NET", record_id, "unmatched_geometry", str(record.get("fnid")))
    issued_at = _required_time(record, "collection_status_changed", fallback="created")
    valid_from = _required_date(record, "projection_start", fallback="reporting_date")
    valid_to = _required_date(record, "projection_end", fallback="reporting_date")
    phase = int(float(value))
    unmatched_source_fraction = round(max(0.0, 1 - sum(item.source_fraction for item in matches)), 8)
    labels = tuple(
        IndependentLabel(
            label_id=f"fews:{record_id}:{match.adm1_region_id}",
            source="FEWS NET",
            source_version=FEWS_SOURCE_VERSION,
            source_record_id=record_id,
            source_url="https://fdw.fews.net/api/ipcphase/",
            label_semantics="acute_food_insecurity_impact",
            assessment_status="assessed",
            issued_at=issued_at,
            valid_from=valid_from,
            valid_to=valid_to,
            original_taxonomy=str(record.get("classification_scale") or "unknown"),
            original_value=str(value),
            normalized_value=f"phase_{phase}",
            source_geometry_id=str(record.get("fnid") or ""),
            adm1_region_id=match.adm1_region_id,
            overlap_source_fraction=match.source_fraction,
            overlap_adm1_fraction=match.adm1_fraction,
            mapping_method=match.mapping_method,
            mapping_version=OVERLAP_RULE_VERSION,
            artifact_sha256=sha256_json({"record": record, "geometry_sha256": geometry_hash}),
            license_policy=str(record.get("data_usage_policy") or "unknown"),
            quality="source_assessed",
            review_status="machine_normalized",
            metadata={
                "country_code": record.get("country_code"),
                "fnid": record.get("fnid"),
                "scenario": record.get("scenario"),
                "scenario_name": record.get("scenario_name"),
                "source_organization": record.get("source_organization"),
                "source_document": record.get("source_document"),
                "is_allowing_for_assistance": record.get("is_allowing_for_assistance"),
                "reporting_date": record.get("reporting_date"),
                "created": record.get("created"),
                "modified": record.get("modified"),
                "geometry_sha256": geometry_hash,
                "unmatched_source_fraction": unmatched_source_fraction,
            },
        )
        for match in matches
    )
    return labels, None


def normalize_ipc_record(
    record: dict[str, Any],
    *,
    matches: tuple[SpatialMatch, ...],
    artifact_hash: str,
) -> tuple[tuple[IndependentLabel, ...], LabelExclusion | None]:
    record_id = str(record.get("id") or record.get("analysis_id") or "")
    period = str(record.get("period") or "")
    if period != "C":
        return (), LabelExclusion("IPC", record_id, "projected_period", period)
    if not matches:
        return (), LabelExclusion("IPC", record_id, "unmatched_geometry", "")
    phase = record.get("phase")
    if phase is None:
        return (), LabelExclusion("IPC", record_id, "unknown_phase_value", "null")
    unmatched_source_fraction = round(max(0.0, 1 - sum(item.source_fraction for item in matches)), 8)
    labels = tuple(
        IndependentLabel(
            label_id=f"ipc:{record_id}:{match.adm1_region_id}",
            source="IPC",
            source_version=IPC_SOURCE_VERSION,
            source_record_id=record_id,
            source_url="https://api.ipcinfo.org",
            label_semantics="acute_food_insecurity_impact",
            assessment_status="assessed",
            issued_at=_required_time(record, "created_at", fallback="created"),
            valid_from=_required_date(record, "valid_from", fallback="from"),
            valid_to=_required_date(record, "valid_to", fallback="to"),
            original_taxonomy=str(record.get("analysis_type") or "IPC acute food insecurity"),
            original_value=str(phase),
            normalized_value=f"phase_{int(float(phase))}",
            source_geometry_id=str(record.get("area_id") or record_id),
            adm1_region_id=match.adm1_region_id,
            overlap_source_fraction=match.source_fraction,
            overlap_adm1_fraction=match.adm1_fraction,
            mapping_method=match.mapping_method,
            mapping_version=OVERLAP_RULE_VERSION,
            artifact_sha256=artifact_hash,
            license_policy="CC BY-NC-SA 3.0 IGO",
            quality="source_assessed",
            review_status="machine_normalized",
            metadata={
                "analysis_id": record.get("analysis_id"),
                "period": period,
                "unmatched_source_fraction": unmatched_source_fraction,
            },
        )
        for match in matches
    )
    return labels, None


def import_official_manifest(path: Path) -> tuple[IndependentLabel, ...]:
    payload = _read_json(path)
    records = payload.get("records") if isinstance(payload, dict) else None
    if not isinstance(records, list):
        raise LabelImportError("official manifest must contain a records list")
    artifact_hash = sha256_file(path)
    result: list[IndependentLabel] = []
    for record in records:
        if not isinstance(record, dict):
            raise LabelImportError("official manifest record must be an object")
        status = str(record.get("assessment_status"))
        if status not in {"official_operational_phase", "official_emergency_declaration"}:
            raise LabelImportError("official record has invalid assessment_status")
        if record.get("review_status") != "validated":
            raise LabelImportError("official records must be validated")
        adm1 = record.get("adm1_region_id")
        result.append(
            IndependentLabel(
                label_id=f"official:{record['source_record_id']}:{adm1 or 'country'}",
                source=str(record["authority"]),
                source_version=OFFICIAL_SOURCE_VERSION,
                source_record_id=str(record["source_record_id"]),
                source_url=str(record["document_url"]),
                label_semantics="drought_hazard_event",
                assessment_status=status,
                issued_at=str(record["issued_at"]),
                valid_from=str(record["valid_from"]),
                valid_to=str(record["valid_to"]),
                original_taxonomy=str(record["taxonomy"]),
                original_value=str(record["value"]),
                normalized_value=str(record["normalized_value"]),
                source_geometry_id=str(record.get("jurisdiction") or ""),
                adm1_region_id=str(adm1) if adm1 else None,
                overlap_source_fraction=1.0 if adm1 else None,
                overlap_adm1_fraction=1.0 if adm1 else None,
                mapping_method="validated_manifest" if adm1 else None,
                mapping_version=OFFICIAL_SOURCE_VERSION if adm1 else None,
                artifact_sha256=str(record.get("document_sha256") or artifact_hash),
                license_policy=str(record["license_policy"]),
                quality="human_validated",
                review_status="validated",
                metadata={
                    "jurisdiction": record.get("jurisdiction"),
                    **(
                        dict(record.get("metadata") or {})
                        if isinstance(record.get("metadata"), dict)
                        else {}
                    ),
                },
            )
        )
    return tuple(result)


def import_emdat_csv(
    path: Path,
    *,
    access_date: str,
    license_policy: str,
    adm1_name_index: dict[str, str] | None = None,
    allowed_iso3: frozenset[str] | None = None,
) -> tuple[IndependentLabel, ...]:
    """Import a user-supplied registered public-table export without spatial invention.

    EM-DAT's administrative-unit fields are JSON. Only an explicit ADM1 name that
    matches the versioned Mwangaza catalog becomes ADM1 evidence. A row with no
    resolvable ADM1 remains one country-level event and is never copied to regions.
    """

    artifact_hash = sha256_file(path)
    result: list[IndependentLabel] = []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for record in csv.DictReader(stream):
            disaster_type = _csv_value(record, "Disaster Type", "Disaster_Type")
            if disaster_type.lower() != "drought":
                continue
            iso3 = _csv_value(record, "ISO", "Country ISO", required=False).upper()
            if allowed_iso3 is not None and iso3 not in allowed_iso3:
                continue
            event_id = _csv_value(record, "DisNo.", "DisNo", "Event ID")
            raw_admin = _csv_value(record, "Admin Units", "Admin_Units", required=False)
            raw_gadm = _csv_value(record, "GADM Admin Units", "GADM_Admin_Units", required=False)
            admin_units = _emdat_admin_units(raw_admin, raw_gadm)
            adm1_ids = _resolve_emdat_adm1(admin_units, adm1_name_index or {})
            start, start_precision = _emdat_date(record, "Start", end=False)
            end, end_precision = _emdat_date(record, "End", end=True, fallback_year=start[:4])
            targets: tuple[str | None, ...] = adm1_ids or (None,)
            for adm1 in targets:
                suffix = adm1 or f"country-{iso3.lower() or 'unknown'}"
                result.append(
                    IndependentLabel(
                        label_id=f"emdat:{event_id}:{suffix}",
                        source="EM-DAT",
                        source_version=EMDAT_SOURCE_VERSION,
                        source_record_id=event_id,
                        source_url="https://public.emdat.be/",
                        label_semantics="drought_hazard_event",
                        assessment_status="validated_catalog_event",
                        issued_at=access_date,
                        valid_from=start,
                        valid_to=end,
                        original_taxonomy=disaster_type,
                        original_value="Drought",
                        normalized_value="drought_event",
                        source_geometry_id=adm1 or iso3 or None,
                        adm1_region_id=adm1,
                        overlap_source_fraction=1.0 if adm1 else None,
                        overlap_adm1_fraction=1.0 if adm1 else None,
                        mapping_method="explicit_registered_admin_name" if adm1 else None,
                        mapping_version="emdat-explicit-admin-v2" if adm1 else None,
                        artifact_sha256=artifact_hash,
                        license_policy=license_policy,
                        quality="registered_catalog",
                        review_status="source_unit_explicit" if adm1 else "country_only",
                        metadata={
                            "access_date": access_date,
                            "country": record.get("Country"),
                            "country_iso3": iso3 or None,
                            "event_name": record.get("Event Name"),
                            "location": record.get("Location"),
                            "declaration": record.get("Declaration"),
                            "entry_date": record.get("Entry Date"),
                            "last_update": record.get("Last Update"),
                            "start_date_precision": start_precision,
                            "end_date_precision": end_precision,
                            "admin_units": admin_units,
                            "spatial_status": (
                                "explicit_adm1"
                                if adm1
                                else "unresolved_subnational"
                                if admin_units
                                else "country_only"
                            ),
                        },
                    )
                )
    return tuple(result)


def write_label_artifact(
    labels: Iterable[IndependentLabel],
    exclusions: Iterable[LabelExclusion],
    output_dir: Path,
    *,
    retrieved_at: str,
    source_statuses: dict[str, str] | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    ordered = tuple(sorted(labels, key=lambda item: item.label_id))
    excluded = tuple(sorted(exclusions, key=lambda item: (item.source, item.source_record_id, item.reason)))
    label_path = output_dir / "independent-labels.jsonl"
    exclusion_path = output_dir / "exclusions.jsonl"
    _atomic_text(label_path, "".join(_canonical(asdict(item)) + "\n" for item in ordered))
    _atomic_text(exclusion_path, "".join(_canonical(asdict(item)) + "\n" for item in excluded))
    manifest = {
        "schema_version": LABEL_SCHEMA_VERSION,
        "mapping_version": OVERLAP_RULE_VERSION,
        "retrieved_at": retrieved_at,
        "label_count": len(ordered),
        "exclusion_count": len(excluded),
        "regions": sorted({item.adm1_region_id for item in ordered if item.adm1_region_id}),
        "sources": sorted({item.source for item in ordered} | {item.source for item in excluded}),
        "source_statuses": dict(sorted((source_statuses or {}).items())),
        "complete": not any(
            status in {"partial_unknown", "source_unavailable"}
            for status in (source_statuses or {}).values()
        ),
        "semantics": sorted({item.label_semantics for item in ordered}),
        "valid_from": min((item.valid_from for item in ordered), default=None),
        "valid_to": max((item.valid_to for item in ordered), default=None),
        "exclusions_by_reason": _counts(item.reason for item in excluded),
        "labels_sha256": sha256_file(label_path),
        "exclusions_sha256": sha256_file(exclusion_path),
    }
    _atomic_text(output_dir / "manifest.json", _canonical(manifest) + "\n")
    return manifest


def sha256_json(value: object) -> str:
    return f"sha256:{hashlib.sha256(_canonical(value).encode()).hexdigest()}"


def sha256_file(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _required_time(record: dict[str, Any], key: str, *, fallback: str) -> str:
    value = record.get(key) or record.get(fallback)
    if not value:
        raise LabelImportError(f"record lacks {key}/{fallback}")
    text = str(value)
    return text if "T" in text else f"{text}T00:00:00Z"


def _required_date(record: dict[str, Any], key: str, *, fallback: str) -> str:
    value = record.get(key) or record.get(fallback)
    if not value:
        raise LabelImportError(f"record lacks {key}/{fallback}")
    return str(value)[:10]


def _emdat_date(
    record: dict[str, str],
    prefix: str,
    *,
    end: bool,
    fallback_year: str | None = None,
) -> tuple[str, str]:
    year_text = _csv_value(record, f"{prefix} Year", f"{prefix}_Year", required=False)
    year = int(year_text or fallback_year or "")
    month_text = _csv_value(record, f"{prefix} Month", f"{prefix}_Month", required=False)
    day_text = _csv_value(record, f"{prefix} Day", f"{prefix}_Day", required=False)
    if month_text and day_text:
        return f"{year:04d}-{int(month_text):02d}-{int(day_text):02d}", "day"
    if month_text:
        month = int(month_text)
        if end:
            from calendar import monthrange

            day = monthrange(year, month)[1]
        else:
            day = 1
        return f"{year:04d}-{month:02d}-{day:02d}", "month"
    return f"{year:04d}-{'12-31' if end else '01-01'}", "year"


def _emdat_admin_units(*values: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for value in values:
        if not value.strip():
            continue
        try:
            payload = json.loads(value)
        except json.JSONDecodeError:
            # Legacy test/export support remains explicit and never accepts a
            # free-form location string as an ADM1 assignment.
            for item in value.split(";"):
                if item.strip().startswith("adm1-"):
                    result.append({"mwangaza_adm1_id": item.strip()})
            continue
        if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
            raise LabelImportError("EM-DAT administrative units must be a JSON array of objects")
        result.extend(dict(item) for item in payload)
    return result


def _resolve_emdat_adm1(
    units: list[dict[str, Any]], name_index: dict[str, str]
) -> tuple[str, ...]:
    result: set[str] = set()
    for unit in units:
        explicit = str(unit.get("mwangaza_adm1_id") or "")
        if explicit.startswith("adm1-"):
            result.add(explicit)
            continue
        name = str(unit.get("adm1_name") or unit.get("name_1") or "").strip()
        if not name:
            # ADM2 units do not get promoted to ADM1 without an explicit parent.
            continue
        key = " ".join("".join(character if character.isalnum() else " " for character in name.casefold()).split())
        if key in name_index:
            result.add(name_index[key])
    return tuple(sorted(result))


def _csv_value(record: dict[str, str], *keys: str, required: bool = True) -> str:
    for key in keys:
        if record.get(key):
            return str(record[key]).strip()
    if required:
        raise LabelImportError(f"EM-DAT row lacks one of {keys}")
    return ""


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LabelImportError(f"could not read {path}") from exc


def _counts(values: Iterable[str]) -> dict[str, int]:
    result: dict[str, int] = {}
    for value in values:
        result[value] = result.get(value, 0) + 1
    return dict(sorted(result.items()))


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _atomic_text(path: Path, content: str) -> None:
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
