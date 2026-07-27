from __future__ import annotations

from pathlib import Path

import pytest

from mwangaza.probabilistic.drought_hazards import (
    audit_drought_hazard_episodes,
    extract_ndma_phase,
    is_complete_pdf,
    ndma_official_record,
    ndma_period_postback_index,
    parse_ndma_archive_html,
    parse_ndma_document_link,
)
from mwangaza.probabilistic.independent_labels import import_emdat_csv
from mwangaza.probabilistic.independent_labels import LabelImportError

FIXTURES = Path(__file__).parents[1] / "fixtures" / "probabilistic"


def test_ndma_archive_and_document_contract_are_parsed_from_official_html() -> None:
    archive = (FIXTURES / "ndma-archive.html").read_text(encoding="utf-8")
    rows = parse_ndma_archive_html(archive, expected_year=2026, expected_month=6)
    assert len(rows) == 1
    assert rows[0].county == "Baringo"
    assert rows[0].published_at == "2026-07-20"
    assert ndma_period_postback_index(archive, 2026, 6) == "0:1"
    assert parse_ndma_document_link(
        (FIXTURES / "ndma-detail.html").read_text(encoding="utf-8")
    ).endswith("document=be161a20-6e9f-4149-86b6-7bdfde92d9ad")


def test_ndma_archive_deduplicates_identical_rows_but_rejects_conflicts() -> None:
    archive = (FIXTURES / "ndma-archive.html").read_text(encoding="utf-8")
    row = archive[archive.index('<tr class="dxgvDataRow_Material">') : archive.index("</tr>") + 5]
    duplicated = archive.replace(row, row + row)
    assert len(parse_ndma_archive_html(duplicated)) == 1

    conflict = row.replace("Baringo</td>", "Turkana</td>", 1)
    with pytest.raises(LabelImportError, match="conflicting rows"):
        parse_ndma_archive_html(archive.replace(row, row + conflict))


def test_pdf_integrity_requires_header_and_terminal_eof() -> None:
    assert is_complete_pdf(b"%PDF-1.7\nbody\n%%EOF\n") is True
    assert is_complete_pdf(b"%PDF-1.7\ntruncated") is False
    assert is_complete_pdf(b"<html>temporary error</html>%%EOF") is False


def test_ndma_extraction_accepts_one_exact_county_phase_and_queues_ambiguity() -> None:
    bulletin = parse_ndma_archive_html(
        (FIXTURES / "ndma-archive.html").read_text(encoding="utf-8")
    )[0]
    extraction = extract_ndma_phase(
        (FIXTURES / "ndma-phase.txt").read_text(encoding="utf-8"),
        expected_county="Baringo",
        expected_year=2026,
        expected_month=6,
    )
    assert extraction.validation_status == "validated"
    assert extraction.phase == "alert"
    assert extraction.trend == "deteriorating"
    record = ndma_official_record(
        bulletin,
        extraction,
        adm1_region_id="adm1-ke-01",
        document_url="https://knowledgeweb.ndma.go.ke/example.pdf",
        document_sha256="sha256:document",
    )
    assert record["assessment_status"] == "official_operational_phase"
    assert record["normalized_value"] == "phase_alert"
    assert record["metadata"]["extraction_version"] == "ndma-county-ew-phase-v1"

    ambiguous = extract_ndma_phase(
        (FIXTURES / "ndma-phase-ambiguous.txt").read_text(encoding="utf-8"),
        expected_county="Baringo",
        expected_year=2026,
        expected_month=6,
    )
    assert ambiguous.validation_status == "review_required"
    assert ambiguous.reason == "ambiguous_phase"
    assert ambiguous.phase is None


def test_realistic_emdat_keeps_explicit_adm1_and_national_event_separate() -> None:
    labels = import_emdat_csv(
        FIXTURES / "emdat-realistic.csv",
        access_date="2026-07-27",
        license_policy="registered non-commercial test",
        adm1_name_index={"baringo": "adm1-ke-01", "turkana": "adm1-ke-43"},
        allowed_iso3=frozenset({"KEN", "ETH"}),
    )
    assert {item.source_record_id for item in labels} == {
        "2024-0001-KEN",
        "2025-0002-ETH",
    }
    kenya = [item for item in labels if item.metadata["country_iso3"] == "KEN"]
    assert {item.adm1_region_id for item in kenya} == {"adm1-ke-01", "adm1-ke-43"}
    ethiopia = next(item for item in labels if item.metadata["country_iso3"] == "ETH")
    assert ethiopia.adm1_region_id is None
    assert ethiopia.review_status == "country_only"
    assert ethiopia.valid_from == "2025-01-01"
    assert ethiopia.valid_to == "2025-12-31"
    assert ethiopia.metadata["start_date_precision"] == "year"


def test_episode_audit_groups_months_but_not_sources_or_non_hazard_evidence() -> None:
    labels = [
        _label("a1", "NDMA", "phase_alert", "2024-01-01", "2024-01-31"),
        _label("a2", "NDMA", "phase_alarm", "2024-02-01", "2024-02-29"),
        _label("a3", "NDMA", "phase_normal", "2024-03-01", "2024-03-31"),
        _label("e1", "EM-DAT", "drought_event", "2024-02-01", "2024-04-30"),
        _label("country", "EM-DAT", "drought_event", "2024-01-01", "2024-12-31", adm1=None),
        _label(
            "pending",
            "NDMA",
            "phase_alert",
            "2024-05-01",
            "2024-05-31",
            review_status="review_required",
        ),
    ]
    report = audit_drought_hazard_episodes(labels, adm1_country={"adm1-ke-01": "KEN"})
    assert report["episode_count"] == 2
    assert sorted(item["evidence_count"] for item in report["episodes"]) == [1, 2]
    assert {item["source"] for item in report["episodes"]} == {"NDMA", "EM-DAT"}
    assert report["country_only_count"] == 1
    assert report["unvalidated_count"] == 1
    assert report["non_hazard_observation_count"] == 1
    assert report["disagreement_count"] >= 1


def _label(
    record_id: str,
    source: str,
    value: str,
    valid_from: str,
    valid_to: str,
    *,
    adm1: str | None = "adm1-ke-01",
    review_status: str = "validated",
) -> dict[str, object]:
    return {
        "label_id": f"test:{record_id}",
        "source": source,
        "source_record_id": record_id,
        "label_semantics": "drought_hazard_event",
        "assessment_status": (
            "validated_catalog_event" if source == "EM-DAT" else "official_operational_phase"
        ),
        "original_taxonomy": "EM-DAT" if source == "EM-DAT" else "NDMA phase",
        "normalized_value": value,
        "valid_from": valid_from,
        "valid_to": valid_to,
        "adm1_region_id": adm1,
        "review_status": review_status,
    }
