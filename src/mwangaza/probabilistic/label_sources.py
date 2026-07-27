from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from mwangaza.probabilistic.independent_labels import LabelImportError

FEWS_PHASE_ENDPOINT = "https://fdw.fews.net/api/ipcphase/"
FEWS_GEOMETRY_ENDPOINT = "https://fdw.fews.net/api/feature.geojson"


class JsonHttpClient:
    def __init__(
        self,
        *,
        attempts: int = 4,
        timeout_seconds: float = 60,
        sleep: Callable[[float], None] = time.sleep,
        opener: Callable[..., Any] = urlopen,
    ) -> None:
        if attempts < 1:
            raise ValueError("attempts must be positive")
        self.attempts = attempts
        self.timeout_seconds = timeout_seconds
        self._sleep = sleep
        self._opener = opener

    def get(self, url: str, *, headers: dict[str, str] | None = None) -> dict[str, Any]:
        request = Request(url, headers={"User-Agent": "Mwangaza-label-import/1", **(headers or {})})
        for attempt in range(self.attempts):
            try:
                with self._opener(request, timeout=self.timeout_seconds) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                if not isinstance(payload, dict):
                    raise LabelImportError("JSON endpoint returned a non-object")
                return payload
            except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
                if attempt + 1 == self.attempts:
                    detail = f"{type(exc).__name__}: {exc}"
                    raise LabelImportError(
                        f"request failed after {self.attempts} attempts ({detail}): {url}"
                    ) from exc
                self._sleep(min(2**attempt, 8))
        raise AssertionError("unreachable")


class FewsNetDownloader:
    def __init__(self, client: JsonHttpClient, checkpoint_dir: Path) -> None:
        self.client = client
        self.checkpoint_dir = checkpoint_dir
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def download_country(
        self,
        country_code: str,
        *,
        page_size: int = 1000,
        page_limit: int | None = None,
        progress: Callable[[int, int], None] | None = None,
    ) -> tuple[dict[str, Any], ...]:
        code = country_code.upper()
        rows_path = self.checkpoint_dir / f"fews-{code}-rows.jsonl"
        state_path = self.checkpoint_dir / f"fews-{code}-state.json"
        rows = _read_jsonl(rows_path)
        seen = {str(item.get("id")) for item in rows}
        state = _read_object(state_path)
        recorded_total = int(state.get("total", len(rows)))
        if state.get("complete") and len(rows) >= recorded_total:
            if progress:
                progress(len(rows), recorded_total)
            return tuple(rows)
        # Offset pagination can move while FEWS publishes new rows. A completed
        # checkpoint whose final count grew is repaired by rescanning from page
        # one; stable source ids make that pass append only genuinely missing rows.
        repairing = bool(state.get("complete") and len(rows) < recorded_total)
        next_url = str(
            _fews_url(code, page_size) if repairing else state.get("next") or _fews_url(code, page_size)
        )
        pages = 0
        while next_url and (page_limit is None or pages < page_limit):
            payload = self.client.get(next_url)
            total = int(payload.get("count", 0))
            results = payload.get("results")
            if not isinstance(results, list):
                raise LabelImportError("FEWS NET page lacks results list")
            new_rows = [item for item in results if isinstance(item, dict) and str(item.get("id")) not in seen]
            if new_rows:
                with rows_path.open("a", encoding="utf-8", newline="\n") as stream:
                    for item in new_rows:
                        stream.write(_canonical(item) + "\n")
                        seen.add(str(item.get("id")))
                        rows.append(item)
                    stream.flush()
                    os.fsync(stream.fileno())
            next_value = payload.get("next")
            next_url = str(next_value) if next_value else ""
            pages += 1
            complete = not next_url and len(rows) >= total
            resume_url = "" if complete else next_url or _fews_url(code, page_size)
            _write_object(
                state_path,
                {"country_code": code, "next": resume_url, "total": total, "complete": complete},
            )
            if progress:
                progress(len(rows), total)
        final_state = _read_object(state_path)
        if page_limit is None and not final_state.get("complete"):
            raise LabelImportError(
                f"FEWS NET pagination changed during download for {code}; rerun to repair "
                f"({len(rows)}/{final_state.get('total', '?')} stable ids)"
            )
        return tuple(rows)

    def geometry(self, fnid: str) -> tuple[dict[str, Any], dict[str, Any]]:
        cache_path = self.checkpoint_dir / "fews-geometries" / f"{fnid}.json"
        if cache_path.exists():
            payload = _read_object(cache_path)
        else:
            payload = self.client.get(f"{FEWS_GEOMETRY_ENDPOINT}?{urlencode({'fnid': fnid})}")
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            _write_object(cache_path, payload)
        features = payload.get("features")
        if not isinstance(features, list) or len(features) != 1 or not isinstance(features[0], dict):
            raise LabelImportError(f"FEWS NET geometry {fnid} is missing or ambiguous")
        geometry = features[0].get("geometry")
        if not isinstance(geometry, dict):
            raise LabelImportError(f"FEWS NET geometry {fnid} is invalid")
        return geometry, payload


def fetch_ipc_payload(client: JsonHttpClient, url: str, *, api_key: str | None) -> dict[str, Any]:
    if not api_key:
        raise LabelImportError("IPC_API_KEY is required for IPC ingestion")
    return client.get(url, headers={"X-API-Key": api_key})


def _fews_url(country_code: str, page_size: int) -> str:
    return f"{FEWS_PHASE_ENDPOINT}?{urlencode({'country_code': country_code, 'scenario': 'CS', 'page_size': page_size})}"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    result: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        payload = json.loads(line)
        if isinstance(payload, dict):
            result.append(payload)
    return result


def _read_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise LabelImportError(f"checkpoint {path} is not a JSON object")
    return payload


def _write_object(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(_canonical(value) + "\n", encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
