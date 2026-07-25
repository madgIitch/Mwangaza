from __future__ import annotations

import hashlib
import json
import os
import tempfile
from calendar import monthrange
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Callable, Iterable, Protocol

BACKFILL_SCHEMA_VERSION = "mwangaza.probabilistic-history.v1"


class HistoricalBackfillError(RuntimeError):
    """Raised when historical materialization cannot be completed safely."""


@dataclass(frozen=True)
class DekadalWindow:
    period_start: str
    period_end: str
    as_of: str

    @property
    def key(self) -> str:
        return self.period_start


@dataclass(frozen=True)
class HistoricalSignalRow:
    region_id: str
    period_start: str
    period_end: str
    as_of: str
    rainfall_mm: float | None
    rainfall_available_days: int
    rainfall_observed_at: str | None
    ndvi: float | None
    ndvi_observed_at: str | None
    ndvi_age_days: int | None
    lst_c: float | None
    lst_observed_at: str | None
    lst_age_days: int | None
    quality_flag: str
    missing_reasons: tuple[str, ...]
    source_mode: str
    geometry_version: str

    @property
    def key(self) -> str:
        return f"{self.region_id}:{self.period_start}"


class HistoricalSignalAdapter(Protocol):
    def fetch(
        self, region: object, windows: tuple[DekadalWindow, ...]
    ) -> tuple[HistoricalSignalRow, ...]: ...


@dataclass(frozen=True)
class BackfillManifest:
    schema_version: str
    period_start: str
    period_end: str
    regions: tuple[str, ...]
    row_count: int
    missing_signal_count: int
    collections: dict[str, str]
    data_sha256: str


def dekadal_windows(start: date, end: date) -> tuple[DekadalWindow, ...]:
    if end < start:
        raise HistoricalBackfillError("end must not be before start")
    cursor = date(start.year, start.month, 1)
    result: list[DekadalWindow] = []
    while cursor <= end:
        last_day = monthrange(cursor.year, cursor.month)[1]
        for first, last in ((1, 10), (11, 20), (21, last_day)):
            period_start = date(cursor.year, cursor.month, first)
            period_end = date(cursor.year, cursor.month, last)
            if period_start >= start and period_end <= end:
                result.append(
                    DekadalWindow(
                        period_start=period_start.isoformat(),
                        period_end=period_end.isoformat(),
                        as_of=_iso_midnight(period_end),
                    )
                )
        cursor = (
            date(cursor.year + 1, 1, 1)
            if cursor.month == 12
            else date(cursor.year, cursor.month + 1, 1)
        )
    return tuple(result)


def last_complete_dekad(today: date | None = None) -> date:
    current = today or datetime.now(UTC).date()
    if current.day > 20:
        return date(current.year, current.month, 20)
    if current.day > 10:
        return date(current.year, current.month, 10)
    previous = current.replace(day=1) - timedelta(days=1)
    return previous


def materialize_history(
    *,
    regions: tuple[object, ...],
    windows: tuple[DekadalWindow, ...],
    adapter: HistoricalSignalAdapter,
    output_dir: Path,
    chunk_size: int = 12,
    force: bool = False,
    progress: Callable[[int, int], None] | None = None,
) -> BackfillManifest:
    if chunk_size < 1:
        raise HistoricalBackfillError("chunk_size must be positive")
    output_dir.mkdir(parents=True, exist_ok=True)
    rows_path = output_dir / "history.jsonl"
    existing = {} if force else _read_rows(rows_path)
    expected_total = len(regions) * len(windows)
    if progress is not None:
        progress(len(existing), expected_total)

    for region in regions:
        region_id = str(getattr(region, "id"))
        pending = tuple(
            window for window in windows if f"{region_id}:{window.key}" not in existing
        )
        for offset in range(0, len(pending), chunk_size):
            fetched = adapter.fetch(region, pending[offset : offset + chunk_size])
            for row in fetched:
                if row.region_id != region_id:
                    raise HistoricalBackfillError("adapter returned the wrong region")
                existing[row.key] = row
            _write_rows(rows_path, existing.values())
            if progress is not None:
                progress(len(existing), expected_total)

    rows = tuple(sorted(existing.values(), key=lambda item: (item.region_id, item.period_start)))
    expected = {
        f"{getattr(region, 'id')}:{window.key}" for region in regions for window in windows
    }
    if set(existing) != expected:
        missing = sorted(expected - set(existing))
        raise HistoricalBackfillError(f"backfill incomplete: {len(missing)} rows missing")

    data_hash = f"sha256:{hashlib.sha256(rows_path.read_bytes()).hexdigest()}"
    manifest = BackfillManifest(
        schema_version=BACKFILL_SCHEMA_VERSION,
        period_start=windows[0].period_start,
        period_end=windows[-1].period_end,
        regions=tuple(str(getattr(region, "id")) for region in regions),
        row_count=len(rows),
        missing_signal_count=sum(len(row.missing_reasons) for row in rows),
        collections={
            "rainfall": "UCSB-CHG/CHIRPS/DAILY",
            "ndvi": "MODIS/061/MOD13Q1",
            "lst": "MODIS/061/MOD11A2",
        },
        data_sha256=data_hash,
    )
    _atomic_text(output_dir / "manifest.json", _canonical_json(asdict(manifest)) + "\n")
    return manifest


def _read_rows(path: Path) -> dict[str, HistoricalSignalRow]:
    if not path.exists():
        return {}
    result: dict[str, HistoricalSignalRow] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        payload = json.loads(line)
        payload["missing_reasons"] = tuple(payload["missing_reasons"])
        row = HistoricalSignalRow(**payload)
        result[row.key] = row
    return result


def _write_rows(path: Path, rows: Iterable[HistoricalSignalRow]) -> None:
    content = "".join(
        _canonical_json(asdict(row)) + "\n"
        for row in sorted(rows, key=lambda item: (item.region_id, item.period_start))
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


def _iso_midnight(value: date) -> str:
    return datetime(value.year, value.month, value.day, tzinfo=UTC).isoformat().replace(
        "+00:00", "Z"
    )
