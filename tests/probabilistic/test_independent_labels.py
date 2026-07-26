from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from urllib.error import URLError

import pytest

from mwangaza.probabilistic.independent_labels import (
    LabelImportError,
    SpatialMatch,
    import_emdat_csv,
    import_official_manifest,
    map_geometry_to_adm1,
    normalize_fews_record,
    normalize_ipc_record,
    write_label_artifact,
)
from mwangaza.probabilistic.label_sources import FewsNetDownloader, JsonHttpClient, fetch_ipc_payload
from mwangaza.probabilistic.spatial_overlap import geometry_overlap

FIXTURES = Path(__file__).parents[1] / "fixtures" / "probabilistic"


class _Region:
    def __init__(self, region_id: str, geometry: dict[str, object]) -> None:
        self.id = region_id
        self.geometry = geometry


class _Response(BytesIO):
    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def _box(x1: float, y1: float, x2: float, y2: float) -> dict[str, object]:
    return {
        "type": "Polygon",
        "coordinates": [[[x1, y1], [x2, y1], [x2, y2], [x1, y2], [x1, y1]]],
    }


def _fews_record(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "id": 42,
        "scenario": "CS",
        "value": 3.0,
        "collection_status": "Published",
        "collection_status_changed": "2024-06-15T12:00:00Z",
        "projection_start": "2024-06-01",
        "projection_end": "2024-06-30",
        "classification_scale": "IPC 3.1",
        "fnid": "KE-test",
        "data_usage_policy": "Public",
        "country_code": "KE",
        "source_organization": "FEWS NET",
        "source_document": "Food Security Outlook",
        "is_allowing_for_assistance": False,
        "reporting_date": "2024-06-01",
    }
    record.update(overrides)
    return record


def test_spatial_overlap_reports_both_fractions_and_honors_holes() -> None:
    source = _box(0, 0, 2, 2)
    target = _box(1, 0, 3, 2)
    overlap = geometry_overlap(source, target)
    assert overlap.source_fraction == pytest.approx(0.5)
    assert overlap.target_fraction == pytest.approx(0.5)

    with_hole = {
        "type": "Polygon",
        "coordinates": [
            [[0, 0], [4, 0], [4, 4], [0, 4], [0, 0]],
            [[1, 1], [3, 1], [3, 3], [1, 3], [1, 1]],
        ],
    }
    assert geometry_overlap(with_hole, _box(1, 1, 3, 3)).intersection_area == pytest.approx(0)


def test_adm1_mapping_uses_geometry_not_names_and_rejects_ambiguous_boundaries() -> None:
    matches = map_geometry_to_adm1(
        _box(0, 0, 2, 1),
        (_Region("adm1-left", _box(0, 0, 1, 1)), _Region("adm1-right", _box(1, 0, 2, 1))),
    )
    assert [(item.adm1_region_id, item.source_fraction) for item in matches] == [
        ("adm1-left", 0.5),
        ("adm1-right", 0.5),
    ]
    with pytest.raises(LabelImportError, match="ambiguous"):
        map_geometry_to_adm1(
            _box(0, 0, 1, 1),
            (_Region("adm1-a", _box(0, 0, 1, 1)), _Region("adm1-b", _box(0, 0, 1, 1))),
        )


def test_fews_assessed_label_preserves_lineage_and_never_becomes_drought() -> None:
    labels, exclusion = normalize_fews_record(
        _fews_record(),
        matches=(SpatialMatch("adm1-ke-test", 0.75, 0.4),),
        geometry_hash="sha256:geometry",
    )
    assert exclusion is None
    assert len(labels) == 1
    label = labels[0]
    assert label.label_semantics == "acute_food_insecurity_impact"
    assert label.assessment_status == "assessed"
    assert label.normalized_value == "phase_3"
    assert label.issued_at == "2024-06-15T12:00:00Z"
    assert label.metadata["is_allowing_for_assistance"] is False
    assert label.metadata["unmatched_source_fraction"] == 0.25

    assert normalize_fews_record(
        _fews_record(scenario="ML1"), matches=(), geometry_hash="sha256:x"
    )[1].reason == "projected_scenario"
    assert normalize_fews_record(
        _fews_record(value=99), matches=(), geometry_hash="sha256:x"
    )[1].reason == "unknown_phase_value"
    assert normalize_fews_record(
        _fews_record(fnid="KE"), matches=(), geometry_hash="sha256:x"
    )[1].reason == "source_unit_too_coarse"


def test_ipc_requires_secret_and_current_period() -> None:
    client = JsonHttpClient(opener=lambda *_args, **_kwargs: _Response(b"{}"))
    with pytest.raises(LabelImportError, match="IPC_API_KEY"):
        fetch_ipc_payload(client, "https://api.ipcinfo.test/areas", api_key=None)

    record = {
        "id": "area-1",
        "analysis_id": "analysis-1",
        "period": "P",
        "phase": 4,
        "created_at": "2024-01-10T00:00:00Z",
        "valid_from": "2024-02-01",
        "valid_to": "2024-05-31",
    }
    assert normalize_ipc_record(record, matches=(), artifact_hash="sha256:x")[1].reason == "projected_period"


def test_fews_downloader_retries_checkpoints_and_resumes_without_duplicates(tmp_path: Path) -> None:
    calls = 0

    def opener(*_args: object, **_kwargs: object) -> _Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise URLError("temporary")
        payload = {
            "count": 1,
            "next": None,
            "results": [_fews_record()],
        }
        return _Response(json.dumps(payload).encode())

    client = JsonHttpClient(opener=opener, sleep=lambda _: None)
    downloader = FewsNetDownloader(client, tmp_path)
    first = downloader.download_country("KE", page_size=1)
    second = downloader.download_country("KE", page_size=1)
    assert len(first) == len(second) == 1
    assert calls == 2
    assert len((tmp_path / "fews-KE-rows.jsonl").read_text().splitlines()) == 1


def test_local_official_and_emdat_importers_do_not_invent_country_adm1() -> None:
    official = import_official_manifest(FIXTURES / "official-labels.json")
    assert official[0].assessment_status == "official_operational_phase"
    assert official[0].label_semantics == "drought_hazard_event"

    emdat = import_emdat_csv(
        FIXTURES / "emdat.csv",
        access_date="2026-07-27",
        license_policy="registered test access",
    )
    assert {item.adm1_region_id for item in emdat} == {"adm1-ke-24", "adm1-ke-43"}
    assert {item.source_record_id for item in emdat} == {"2008-0001"}


def test_artifact_is_deterministic_and_reports_unknown_exclusions(tmp_path: Path) -> None:
    labels, _ = normalize_fews_record(
        _fews_record(),
        matches=(SpatialMatch("adm1-ke-test", 1, 1),),
        geometry_hash="sha256:geometry",
    )
    _, exclusion = normalize_fews_record(
        _fews_record(id=43, value=88), matches=(), geometry_hash="sha256:geometry"
    )
    first = write_label_artifact(labels, (exclusion,), tmp_path, retrieved_at="2026-07-27T00:00:00Z")
    second = write_label_artifact(reversed(labels), (exclusion,), tmp_path, retrieved_at="2026-07-27T00:00:00Z")
    assert first == second
    assert first["exclusions_by_reason"] == {"unknown_phase_value": 1}
    assert first["semantics"] == ["acute_food_insecurity_impact"]
