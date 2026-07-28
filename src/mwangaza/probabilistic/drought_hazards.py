from __future__ import annotations

import hashlib
import html
import json
import re
from calendar import monthrange
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping
from urllib.parse import urljoin

from mwangaza.probabilistic.independent_labels import IndependentLabel, LabelImportError

NDMA_ARCHIVE_URL = (
    "https://knowledgeweb.ndma.go.ke/Public/Resources/CountyBulletins.aspx?ID=11"
)
NDMA_BASE_URL = "https://knowledgeweb.ndma.go.ke/"
NDMA_EXTRACTION_VERSION = "ndma-county-ew-phase-v1"
NDMA_TAXONOMY = "NDMA drought early warning phase"
NDMA_PHASES = ("normal", "alert", "alarm", "emergency", "recovery")
ACTIVE_DROUGHT_PHASES = frozenset({"alert", "alarm", "emergency"})
VALIDATED_REVIEW_STATUSES = frozenset({"validated", "source_unit_explicit"})


@dataclass(frozen=True)
class NdmaBulletin:
    document_id: str
    county: str
    year: int
    month: int
    title: str
    detail_url: str
    published_at: str

    @property
    def period(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"


@dataclass(frozen=True)
class NdmaDocumentDownload:
    data: bytes | None
    url: str
    error: str | None = None


@dataclass(frozen=True)
class NdmaPhaseExtraction:
    validation_status: str
    phase: str | None
    trend: str | None
    evidence: str | None
    reason: str | None
    extraction_version: str = NDMA_EXTRACTION_VERSION


def parse_ndma_archive_html(
    value: str,
    *,
    expected_year: int | None = None,
    expected_month: int | None = None,
) -> tuple[NdmaBulletin, ...]:
    """Parse the rendered official NDMA grid without depending on vendor CSS ids."""

    result: list[NdmaBulletin] = []
    for row in re.findall(r"<tr\b[^>]*>(.*?)</tr>", value, flags=re.IGNORECASE | re.DOTALL):
        link = re.search(
            r'href=["\']([^"\']*ResourceDetails\.aspx\?doc=([0-9a-f-]{36}))[^"\']*["\'][^>]*>(.*?)</a>',
            row,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not link:
            continue
        cells = re.findall(r"<td\b[^>]*>(.*?)</td>", row, flags=re.IGNORECASE | re.DOTALL)
        if len(cells) < 5:
            raise LabelImportError("NDMA bulletin row has an unexpected column layout")
        county = _html_text(cells[1])
        year_text = _html_text(cells[2])
        month_text = _html_text(cells[3])
        if not year_text.isdigit():
            raise LabelImportError(f"NDMA bulletin has invalid year: {year_text}")
        try:
            month = datetime.strptime(month_text, "%B").month
        except ValueError as exc:
            raise LabelImportError(f"NDMA bulletin has invalid month: {month_text}") from exc
        year = int(year_text)
        if expected_year is not None and year != expected_year:
            raise LabelImportError(
                f"NDMA period response mismatch: requested {expected_year}, received {year}"
            )
        if expected_month is not None and month != expected_month:
            raise LabelImportError(
                f"NDMA period response mismatch: requested month {expected_month}, received {month}"
            )
        published = re.search(r"Published:\s*(\d{4}-\d{2}-\d{2})", row, flags=re.IGNORECASE)
        result.append(
            NdmaBulletin(
                document_id=link.group(2).lower(),
                county=county,
                year=year,
                month=month,
                title=_html_text(link.group(3)),
                detail_url=urljoin(NDMA_ARCHIVE_URL, html.unescape(link.group(1))),
                published_at=published.group(1) if published else "",
            )
        )
    unique: dict[str, NdmaBulletin] = {}
    for item in result:
        previous = unique.get(item.document_id)
        if previous is not None and previous != item:
            raise LabelImportError(
                f"NDMA period response contains conflicting rows for {item.document_id}"
            )
        unique[item.document_id] = item
    return tuple(sorted(unique.values(), key=lambda item: (item.county.casefold(), item.document_id)))


def ndma_period_postback_index(value: str, year: int, month: int) -> str:
    marker = "ContentPlaceHolder1_ASPxRoundPanel1_yearTree"
    start = value.find(marker)
    data_start = value.find('"nodeData":', start)
    if start < 0 or data_start < 0:
        raise LabelImportError("NDMA archive no longer exposes the official period tree")
    array_start = value.find("[", data_start)
    array_end = _matching_bracket(value, array_start)
    try:
        periods = json.loads(value[array_start : array_end + 1])
    except json.JSONDecodeError as exc:
        raise LabelImportError("NDMA period tree is not valid JSON") from exc
    for year_index, year_item in enumerate(periods):
        if str(year_item.get("value")) != str(year):
            continue
        for month_index, month_item in enumerate(year_item.get("items", [])):
            if str(month_item.get("value")) == str(month):
                return f"{year_index}:{month_index}"
    raise LabelImportError(f"NDMA archive does not list {year:04d}-{month:02d}")


def parse_ndma_document_link(detail_html: str) -> str:
    match = re.search(
        r'["\']((?:/Library/|https://knowledgeweb\.ndma\.go\.ke/Library/)'
        r'doclink\.aspx\?document=[0-9a-f-]{36})["\']',
        detail_html,
        flags=re.IGNORECASE,
    )
    if not match:
        raise LabelImportError("NDMA detail page does not expose an official document link")
    return urljoin(NDMA_BASE_URL, html.unescape(match.group(1)))


def extract_ndma_phase(
    text: str,
    *,
    expected_county: str,
    expected_year: int,
    expected_month: int,
) -> NdmaPhaseExtraction:
    normalized = _normalized_text(text)
    header = normalized[:4000]
    county_words = _normalized_text(expected_county).split()
    month_name = datetime(expected_year, expected_month, 1).strftime("%B").upper()
    if not county_words or not all(word in header for word in county_words):
        return NdmaPhaseExtraction("review_required", None, None, None, "county_mismatch")
    if str(expected_year) not in header or month_name not in header:
        return NdmaPhaseExtraction("review_required", None, None, None, "period_mismatch")

    pattern = re.compile(
        r"\bCOUNTY\s*[:\-]?\s*(NORMAL|ALERT|ALARM|EMERGENCY|RECOVERY)"
        r"(?:\s+(STABLE|IMPROVING|DETERIORATING))?\b"
    )
    matches = tuple(pattern.finditer(normalized))
    phases = sorted({match.group(1).lower() for match in matches})
    if not phases:
        return NdmaPhaseExtraction("review_required", None, None, None, "phase_not_found")
    if len(phases) != 1:
        return NdmaPhaseExtraction("review_required", None, None, None, "ambiguous_phase")
    trends = sorted({match.group(2).lower() for match in matches if match.group(2)})
    if len(trends) > 1:
        return NdmaPhaseExtraction("review_required", None, None, None, "ambiguous_trend")
    evidence = matches[0].group(0)
    return NdmaPhaseExtraction(
        "validated",
        phases[0],
        trends[0] if trends else None,
        evidence,
        None,
    )


def ndma_official_record(
    bulletin: NdmaBulletin,
    extraction: NdmaPhaseExtraction,
    *,
    adm1_region_id: str,
    document_url: str,
    document_sha256: str,
) -> dict[str, Any]:
    if extraction.validation_status != "validated" or not extraction.phase:
        raise LabelImportError("only validated NDMA phase extractions can become official records")
    last_day = monthrange(bulletin.year, bulletin.month)[1]
    return {
        "authority": "Kenya National Drought Management Authority (NDMA)",
        "source_record_id": f"ndma:{bulletin.document_id}",
        "assessment_status": "official_operational_phase",
        "review_status": "validated",
        "adm1_region_id": adm1_region_id,
        "jurisdiction": bulletin.county,
        "issued_at": f"{bulletin.published_at or bulletin.period + '-01'}T00:00:00Z",
        "valid_from": f"{bulletin.period}-01",
        "valid_to": f"{bulletin.period}-{last_day:02d}",
        "taxonomy": NDMA_TAXONOMY,
        "value": extraction.phase.title(),
        "normalized_value": f"phase_{extraction.phase}",
        "document_url": document_url,
        "document_sha256": document_sha256,
        "license_policy": "Official public bulletin; NDMA source terms apply",
        "metadata": {
            "archive_url": NDMA_ARCHIVE_URL,
            "bulletin_title": bulletin.title,
            "county": bulletin.county,
            "period": bulletin.period,
            "publication_date": bulletin.published_at or None,
            "original_phase": extraction.phase.title(),
            "trend": extraction.trend,
            "evidence": extraction.evidence,
            "extraction_method": "PDF text, exact county phase row",
            "extraction_version": extraction.extraction_version,
            "validation_status": extraction.validation_status,
        },
    }


def build_adm1_name_index(regions: Iterable[object], *, iso3: str | None = None) -> dict[str, str]:
    result: dict[str, str] = {}
    for region in regions:
        if iso3 and str(getattr(region, "iso3", "")).upper() != iso3.upper():
            continue
        name = _name_key(str(getattr(region, "name")))
        if name in result:
            raise LabelImportError(f"duplicate normalized ADM1 name: {name}")
        result[name] = str(getattr(region, "id"))
    return result


def match_adm1_name(value: str, index: Mapping[str, str]) -> str | None:
    aliases = {
        "tharaka nithi": "tharaka",
        "elgeyo marakwet": "elgeyo marakwet",
        "taita taveta": "taita taveta",
    }
    key = _name_key(value)
    return index.get(key) or index.get(aliases.get(key, ""))


def load_independent_labels(paths: Iterable[Path]) -> tuple[dict[str, Any], ...]:
    result: list[dict[str, Any]] = []
    for supplied in paths:
        path = supplied / "independent-labels.jsonl" if supplied.is_dir() else supplied
        if not path.exists():
            raise LabelImportError(f"label artifact does not exist: {path}")
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise LabelImportError(f"invalid JSON at {path}:{line_number}") from exc
            if not isinstance(item, dict):
                raise LabelImportError(f"label at {path}:{line_number} is not an object")
            result.append(item)
    unique = {str(item.get("label_id")): item for item in result}
    if len(unique) != len(result):
        raise LabelImportError("duplicate label ids across supplied artifacts")
    return tuple(sorted(unique.values(), key=lambda item: str(item["label_id"])))


def audit_drought_hazard_episodes(
    labels: Iterable[Mapping[str, Any]],
    *,
    adm1_country: Mapping[str, str],
    max_gap_days: int = 32,
) -> dict[str, Any]:
    hazards = [item for item in labels if item.get("label_semantics") == "drought_hazard_event"]
    country_only: list[Mapping[str, Any]] = []
    unvalidated: list[Mapping[str, Any]] = []
    non_hazard: list[Mapping[str, Any]] = []
    eligible: list[Mapping[str, Any]] = []
    for item in hazards:
        if not item.get("adm1_region_id"):
            country_only.append(item)
        elif str(item.get("review_status")) not in VALIDATED_REVIEW_STATUSES:
            unvalidated.append(item)
        elif _normalized_phase(item.get("normalized_value")) not in ACTIVE_DROUGHT_PHASES and str(
            item.get("normalized_value")
        ) != "drought_event":
            non_hazard.append(item)
        else:
            eligible.append(item)

    groups: dict[tuple[str, ...], list[Mapping[str, Any]]] = {}
    for item in eligible:
        groups.setdefault(_episode_group_key(item), []).append(item)
    episodes: list[dict[str, Any]] = []
    for key, values in sorted(groups.items()):
        ordered = sorted(values, key=lambda item: (str(item["valid_from"]), str(item["valid_to"])))
        series_start = min(_as_date(item["valid_from"]) for item in ordered)
        series_end = max(_as_date(item["valid_to"]) for item in ordered)
        current: list[Mapping[str, Any]] = []
        current_end: date | None = None
        for item in ordered:
            start = _as_date(item["valid_from"])
            if current and current_end and start > current_end + timedelta(days=max_gap_days):
                episodes.append(_episode_payload(current, key, adm1_country, series_start, series_end))
                current = []
            current.append(item)
            current_end = max(current_end or _as_date(item["valid_to"]), _as_date(item["valid_to"]))
        if current:
            episodes.append(_episode_payload(current, key, adm1_country, series_start, series_end))

    disagreements = _overlap_disagreements(hazards)
    by_country_source: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for episode in episodes:
        by_country_source.setdefault((episode["country_iso3"], episode["source"]), []).append(episode)
    summary = []
    for (country, source), values in sorted(by_country_source.items()):
        summary.append(
            {
                "country_iso3": country,
                "source": source,
                "episode_count": len(values),
                "adm1_count": len({item["adm1_region_id"] for item in values}),
                "evidence_count": sum(item["evidence_count"] for item in values),
                "period_start": min(item["valid_from"] for item in values),
                "period_end": max(item["valid_to"] for item in values),
                "duration_days": sum(item["duration_days"] for item in values),
            }
        )
    return {
        "schema_version": "mwangaza.drought-hazard-audit.v1",
        "episode_rule_version": "source-compatible-gap-32d-v1",
        "hazard_label_count": len(hazards),
        "eligible_evidence_count": len(eligible),
        "episode_count": len(episodes),
        "adm1_count": len({item["adm1_region_id"] for item in episodes}),
        "country_only_count": len(country_only),
        "unvalidated_count": len(unvalidated),
        "non_hazard_observation_count": len(non_hazard),
        "disagreement_count": len(disagreements),
        "summary_by_country_source": summary,
        "episodes": sorted(episodes, key=lambda item: item["episode_id"]),
        "country_only": [_evidence_reference(item) for item in country_only],
        "unvalidated": [_evidence_reference(item) for item in unvalidated],
        "non_hazard_observations": [_evidence_reference(item) for item in non_hazard],
        "disagreements": disagreements,
    }


def independent_label_to_dict(label: IndependentLabel) -> dict[str, Any]:
    return asdict(label)


def sha256_bytes(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def is_complete_pdf(value: bytes) -> bool:
    """Reject HTML/error bodies and prematurely truncated PDF downloads."""

    return value.startswith(b"%PDF") and b"%%EOF" in value[-65536:]


def download_ndma_document(
    get: Callable[[str], tuple[bytes, str]], bulletin: NdmaBulletin
) -> NdmaDocumentDownload:
    """Resolve an indexed NDMA document without aborting on a stale source link."""

    try:
        detail_data, _ = get(bulletin.detail_url)
        document_link = parse_ndma_document_link(detail_data.decode("utf-8", "replace"))
    except LabelImportError as exc:
        return NdmaDocumentDownload(None, bulletin.detail_url, str(exc))
    try:
        data, final_url = get(document_link)
    except LabelImportError as exc:
        return NdmaDocumentDownload(None, document_link, str(exc))
    return NdmaDocumentDownload(data, final_url)


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _episode_group_key(item: Mapping[str, Any]) -> tuple[str, ...]:
    base = (
        str(item["adm1_region_id"]),
        str(item["source"]),
        str(item.get("assessment_status") or ""),
        str(item.get("original_taxonomy") or ""),
    )
    if item.get("assessment_status") == "validated_catalog_event":
        return (*base, str(item["source_record_id"]))
    return base


def _episode_payload(
    values: list[Mapping[str, Any]],
    key: tuple[str, ...],
    adm1_country: Mapping[str, str],
    series_start: date,
    series_end: date,
) -> dict[str, Any]:
    start = min(_as_date(item["valid_from"]) for item in values)
    end = max(_as_date(item["valid_to"]) for item in values)
    identity = canonical_json({"key": key, "from": start.isoformat(), "to": end.isoformat()})
    return {
        "episode_id": f"drought:{hashlib.sha256(identity.encode()).hexdigest()[:20]}",
        "adm1_region_id": key[0],
        "country_iso3": adm1_country.get(key[0], "unknown"),
        "source": key[1],
        "assessment_status": key[2],
        "original_taxonomy": key[3],
        "valid_from": start.isoformat(),
        "valid_to": end.isoformat(),
        "duration_days": (end - start).days + 1,
        "evidence_count": len(values),
        "source_record_ids": sorted({str(item["source_record_id"]) for item in values}),
        "phases": sorted({str(item["normalized_value"]) for item in values}),
        "left_censored": start == series_start,
        "right_censored": end == series_end,
        "evidence_sha256": f"sha256:{hashlib.sha256(canonical_json([_evidence_reference(item) for item in values]).encode()).hexdigest()}",
    }


def _overlap_disagreements(values: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_region: dict[str, list[Mapping[str, Any]]] = {}
    for item in values:
        if item.get("adm1_region_id") and str(item.get("review_status")) in VALIDATED_REVIEW_STATUSES:
            by_region.setdefault(str(item["adm1_region_id"]), []).append(item)
    result: list[dict[str, Any]] = []
    for region, items in sorted(by_region.items()):
        ordered = sorted(items, key=lambda item: str(item["valid_from"]))
        for index, left in enumerate(ordered):
            for right in ordered[index + 1 :]:
                if _as_date(right["valid_from"]) > _as_date(left["valid_to"]):
                    break
                if left.get("normalized_value") != right.get("normalized_value"):
                    result.append(
                        {
                            "adm1_region_id": region,
                            "left_label_id": left.get("label_id"),
                            "right_label_id": right.get("label_id"),
                            "left_value": left.get("normalized_value"),
                            "right_value": right.get("normalized_value"),
                        }
                    )
    return result


def _evidence_reference(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "label_id": item.get("label_id"),
        "source": item.get("source"),
        "source_record_id": item.get("source_record_id"),
        "adm1_region_id": item.get("adm1_region_id"),
        "valid_from": item.get("valid_from"),
        "valid_to": item.get("valid_to"),
        "normalized_value": item.get("normalized_value"),
        "review_status": item.get("review_status"),
    }


def _normalized_phase(value: object) -> str:
    return str(value or "").lower().removeprefix("phase_")


def _as_date(value: object) -> date:
    return date.fromisoformat(str(value)[:10])


def _html_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def _normalized_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9]+", " ", value.upper())).strip()


def _name_key(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value.casefold())).strip()


def _matching_bracket(value: str, start: int) -> int:
    if start < 0 or value[start] != "[":
        raise LabelImportError("NDMA period tree JSON array is missing")
    depth = 0
    quoted = False
    escaped = False
    for index in range(start, len(value)):
        character = value[index]
        if quoted:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                quoted = False
            continue
        if character == '"':
            quoted = True
        elif character == "[":
            depth += 1
        elif character == "]":
            depth -= 1
            if depth == 0:
                return index
    raise LabelImportError("NDMA period tree JSON array is truncated")
