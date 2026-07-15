from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Callable, Sequence
from uuid import uuid4

STATUSES = ("cache_hit", "remote_query", "no_data", "error", "skipped")
MAX_CONSERVATIVE_CONCURRENCY = 8


class PipelineError(ValueError):
    pass


@dataclass(frozen=True)
class PipelineConfig:
    max_concurrency: int = 2
    max_failure_fraction: float = 0.25
    dry_run: bool = False

    def sanitized(self) -> dict[str, Any]:
        return {
            "max_concurrency": self.max_concurrency,
            "max_failure_fraction": self.max_failure_fraction,
            "dry_run": self.dry_run,
        }


@dataclass(frozen=True)
class PipelineTask:
    region_id: str
    processor: Callable[[str], "RegionRunResult"]


@dataclass(frozen=True)
class RegionRunResult:
    region_id: str
    status: str
    message: str = ""
    payload: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PipelineRun:
    run_id: str
    started_at: str
    finished_at: str
    effective_config: dict[str, Any]
    results: tuple[RegionRunResult, ...]
    summary: dict[str, int]
    exit_code: int

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["results"] = [result.to_dict() for result in self.results]
        return payload

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=2)


def run_refresh_pipeline(
    tasks: Sequence[PipelineTask],
    *,
    config: PipelineConfig | None = None,
    resume: bool = False,
    previous_results: Sequence[RegionRunResult] | None = None,
    run_id: str | None = None,
) -> PipelineRun:
    resolved_config = config or PipelineConfig()
    _validate_config(resolved_config)
    previous_by_region = {result.region_id: result for result in previous_results or ()}
    started = _now()
    results: list[RegionRunResult] = []

    for task in sorted(tasks, key=lambda item: item.region_id):
        previous = previous_by_region.get(task.region_id)
        if resume and previous is not None and previous.status not in {"error", "skipped"}:
            results.append(RegionRunResult(task.region_id, "skipped", "already completed", previous.payload))
            continue
        try:
            result = task.processor(task.region_id)
            _validate_result(result)
        except Exception as exc:  # noqa: BLE001 - regional failures are isolated by contract.
            result = RegionRunResult(task.region_id, "error", str(exc), None)
        results.append(result)

    finished = _now()
    summary = _summary(results)
    exit_code = 1 if _failure_fraction(results) > resolved_config.max_failure_fraction else 0
    return PipelineRun(
        run_id=run_id or uuid4().hex,
        started_at=started,
        finished_at=finished,
        effective_config=resolved_config.sanitized(),
        results=tuple(results),
        summary=summary,
        exit_code=exit_code,
    )


def _validate_config(config: PipelineConfig) -> None:
    if not 1 <= config.max_concurrency <= MAX_CONSERVATIVE_CONCURRENCY:
        raise PipelineError("max_concurrency must be between 1 and 8")
    if not 0 <= config.max_failure_fraction <= 1:
        raise PipelineError("max_failure_fraction must be inside [0, 1]")


def _validate_result(result: RegionRunResult) -> None:
    if not result.region_id:
        raise PipelineError("region_id is required")
    if result.status not in STATUSES:
        raise PipelineError(f"unsupported pipeline status: {result.status}")


def _summary(results: Sequence[RegionRunResult]) -> dict[str, int]:
    summary = {status: 0 for status in STATUSES}
    for result in results:
        summary[result.status] += 1
    return summary


def _failure_fraction(results: Sequence[RegionRunResult]) -> float:
    if not results:
        return 0.0
    return sum(1 for result in results if result.status == "error") / len(results)


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "PipelineConfig",
    "PipelineError",
    "PipelineRun",
    "PipelineTask",
    "RegionRunResult",
    "run_refresh_pipeline",
]
