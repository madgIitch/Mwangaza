from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Callable, Iterable, Protocol

from mwangaza.probabilistic.backfill import DekadalWindow

ADM1_RAW_SCHEMA_VERSION = "mwangaza.adm1-antecedent-raw.v1"
ADM1_PREPARED_SCHEMA_VERSION = "mwangaza.adm1-antecedent-features.v1"


class Adm1DataError(RuntimeError):
    """Raised when an ADM1 artifact would be incomplete or temporally unsafe."""


@dataclass(frozen=True)
class SignalObservation:
    value: float | int | None
    unit: str
    source_collection: str
    source_version: str
    observed_at: str | None
    available_at: str | None
    age_days: int | None
    lead_hours: int | None
    quality: str
    missing_reason: str | None = None


@dataclass(frozen=True)
class Adm1RawRow:
    region_id: str
    parent_region_id: str
    parent_iso3: str
    boundary_id: str
    boundary_iso: str
    boundary_source: str
    boundary_version: str
    period_start: str
    period_end: str
    as_of: str
    signals: dict[str, SignalObservation]

    @property
    def key(self) -> str:
        return f"{self.region_id}:{self.period_start}"


@dataclass(frozen=True)
class Adm1PreparedRow:
    region_id: str
    parent_region_id: str
    parent_iso3: str
    boundary_id: str
    boundary_iso: str
    boundary_source: str
    boundary_version: str
    period_start: str
    period_end: str
    as_of: str
    signals: dict[str, SignalObservation]
    transformation_version: str

    @property
    def key(self) -> str:
        return f"{self.region_id}:{self.period_start}"


@dataclass(frozen=True)
class Adm1RegionManifest:
    region_id: str
    parent_region_id: str
    parent_iso3: str
    boundary_id: str
    boundary_iso: str
    boundary_source: str
    boundary_version: str
    geometry: dict[str, object]


@dataclass(frozen=True)
class Adm1ArtifactManifest:
    schema_version: str
    period_start: str
    period_end: str
    row_count: int
    region_count: int
    regions: tuple[Adm1RegionManifest, ...]
    collections: dict[str, str]
    missing_signal_count: int
    data_sha256: str


class Adm1SignalAdapter(Protocol):
    def fetch(
        self, regions: tuple[object, ...], windows: tuple[DekadalWindow, ...]
    ) -> tuple[Adm1RawRow, ...]: ...


def materialize_adm1_history(
    *,
    regions: tuple[object, ...],
    windows: tuple[DekadalWindow, ...],
    adapter: Adm1SignalAdapter,
    output_dir: Path,
    window_chunk_size: int = 12,
    region_batch_size: int = 32,
    force: bool = False,
    progress: Callable[[int, int], None] | None = None,
) -> Adm1ArtifactManifest:
    if not regions or not windows:
        raise Adm1DataError("regions and windows must not be empty")
    if window_chunk_size < 1 or region_batch_size < 1:
        raise Adm1DataError("batch sizes must be positive")
    _validate_adm1_regions(regions)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows_path = output_dir / "adm1-history.jsonl"
    existing = {} if force else _read_raw_rows(rows_path)
    expected = {
        f"{getattr(region, 'id')}:{window.period_start}"
        for region in regions
        for window in windows
    }
    existing = {key: value for key, value in existing.items() if key in expected}
    total = len(expected)
    if progress:
        progress(len(existing), total)

    for region_offset in range(0, len(regions), region_batch_size):
        region_batch = regions[region_offset : region_offset + region_batch_size]
        for window_offset in range(0, len(windows), window_chunk_size):
            window_batch = windows[window_offset : window_offset + window_chunk_size]
            pending_regions = tuple(
                region
                for region in region_batch
                if any(
                    f"{getattr(region, 'id')}:{window.period_start}" not in existing
                    for window in window_batch
                )
            )
            if not pending_regions:
                continue
            fetched = adapter.fetch(pending_regions, window_batch)
            allowed = {
                f"{getattr(region, 'id')}:{window.period_start}"
                for region in pending_regions
                for window in window_batch
            }
            for row in fetched:
                if row.key not in allowed:
                    raise Adm1DataError(f"adapter returned unexpected row {row.key}")
                _validate_temporal_safety(row)
                existing[row.key] = row
            _write_rows(rows_path, existing.values())
            if progress:
                progress(len(existing), total)

    missing = expected - set(existing)
    if missing:
        raise Adm1DataError(f"ADM1 backfill incomplete: {len(missing)} rows missing")
    rows = tuple(sorted(existing.values(), key=lambda row: (row.region_id, row.period_start)))
    digest = f"sha256:{hashlib.sha256(rows_path.read_bytes()).hexdigest()}"
    manifest = Adm1ArtifactManifest(
        schema_version=ADM1_RAW_SCHEMA_VERSION,
        period_start=windows[0].period_start,
        period_end=windows[-1].period_end,
        row_count=len(rows),
        region_count=len(regions),
        regions=tuple(_region_manifest(region) for region in regions),
        collections={
            "rainfall": "UCSB-CHG/CHIRPS/DAILY",
            "ndvi": "MODIS/061/MOD13Q1",
            "spei": "CSIC/SPEI/2_11",
            "land_surface": "NASA/FLDAS/NOAH01/C/GL/M/V001",
            "forecast": "ECMWF/NRT_FORECAST/IFS/OPER",
        },
        missing_signal_count=sum(
            signal.missing_reason is not None for row in rows for signal in row.signals.values()
        ),
        data_sha256=digest,
    )
    _atomic_text(output_dir / "manifest.json", _canonical_json(asdict(manifest)) + "\n")
    return manifest


def load_adm1_raw_rows(path: Path) -> tuple[Adm1RawRow, ...]:
    return tuple(_read_raw_rows(path).values())


def write_prepared_rows(rows: tuple[Adm1PreparedRow, ...], output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows_path = output_dir / "adm1-features.jsonl"
    _write_rows(rows_path, rows)
    digest = f"sha256:{hashlib.sha256(rows_path.read_bytes()).hexdigest()}"
    manifest: dict[str, object] = {
        "schema_version": ADM1_PREPARED_SCHEMA_VERSION,
        "row_count": len(rows),
        "region_count": len({row.region_id for row in rows}),
        "period_start": min(row.period_start for row in rows),
        "period_end": max(row.period_end for row in rows),
        "missing_signal_count": sum(
            signal.missing_reason is not None for row in rows for signal in row.signals.values()
        ),
        "data_sha256": digest,
        "transformation_versions": sorted({row.transformation_version for row in rows}),
    }
    _atomic_text(output_dir / "manifest.json", _canonical_json(manifest) + "\n")
    return manifest


def _validate_adm1_regions(regions: tuple[object, ...]) -> None:
    ids = {str(getattr(region, "id")) for region in regions}
    if len(ids) != len(regions):
        raise Adm1DataError("ADM1 region ids must be unique")
    for region in regions:
        if getattr(region, "level", None) != "adm1":
            raise Adm1DataError(f"{getattr(region, 'id', '?')} is not ADM1")
        metadata = getattr(region, "metadata", {})
        if not metadata.get("boundary_id") or not metadata.get("boundary_iso"):
            raise Adm1DataError(f"{getattr(region, 'id')} lacks boundary identity")


def _validate_temporal_safety(row: Adm1RawRow) -> None:
    as_of = _parse_time(row.as_of)
    for name, signal in row.signals.items():
        if signal.available_at is not None and _parse_time(signal.available_at) > as_of:
            raise Adm1DataError(f"{row.key}:{name} was unavailable at as_of")
        if signal.lead_hours is not None:
            if signal.available_at is None or signal.observed_at is not None:
                raise Adm1DataError(f"{row.key}:{name} forecast lineage is invalid")


def _region_manifest(region: object) -> Adm1RegionManifest:
    metadata = getattr(region, "metadata")
    return Adm1RegionManifest(
        region_id=str(getattr(region, "id")),
        parent_region_id=str(getattr(region, "parent_id")),
        parent_iso3=str(getattr(region, "iso3")),
        boundary_id=str(metadata["boundary_id"]),
        boundary_iso=str(metadata["boundary_iso"]),
        boundary_source=str(getattr(region, "source")),
        boundary_version=str(getattr(region, "source_version")),
        geometry=getattr(region, "geometry"),
    )


def _read_raw_rows(path: Path) -> dict[str, Adm1RawRow]:
    if not path.exists():
        return {}
    result: dict[str, Adm1RawRow] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        payload = json.loads(line, parse_constant=_reject_constant)
        payload["signals"] = {
            name: SignalObservation(**signal) for name, signal in payload["signals"].items()
        }
        row = Adm1RawRow(**payload)
        result[row.key] = row
    return result


def _write_rows(path: Path, rows: Iterable[Adm1RawRow | Adm1PreparedRow]) -> None:
    content = "".join(
        _canonical_json(asdict(row)) + "\n"
        for row in sorted(rows, key=lambda value: (value.region_id, value.period_start))
    )
    _atomic_text(path, content)


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


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def _parse_time(value: str) -> datetime:
    if len(value) == 10:
        return datetime.combine(date.fromisoformat(value), datetime.min.time(), tzinfo=UTC)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
