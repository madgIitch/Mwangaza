"""Backfill validated Kenya NDMA county drought phases from official monthly PDFs.

Run with the PDF reader available:
  uv run --with pypdf python scripts/backfill_ndma_drought_phases.py --start 2024-01
"""

from __future__ import annotations

import argparse
import http.cookiejar
import io
import json
import os
import time
from dataclasses import asdict
from datetime import UTC, date, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener

from mwangaza.probabilistic.drought_hazards import (
    NDMA_ARCHIVE_URL,
    NdmaBulletin,
    build_adm1_name_index,
    canonical_json,
    download_ndma_document,
    extract_ndma_phase,
    is_complete_pdf,
    match_adm1_name,
    ndma_official_record,
    ndma_period_postback_index,
    parse_ndma_archive_html,
    sha256_bytes,
)
from mwangaza.probabilistic.independent_labels import LabelImportError, sha256_file
from mwangaza.probabilistic.progress import EtaProgress
from mwangaza.regions import ADM1_LEVEL, list_regions

YEAR_TREE_TARGET = "ctl00$ContentPlaceHolder1$ASPxRoundPanel1$yearTree"


class _InputParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.fields: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "input":
            return
        values = dict(attrs)
        if values.get("name"):
            self.fields[str(values["name"])] = str(values.get("value") or "")


class NdmaHttpClient:
    def __init__(self, *, attempts: int = 4, timeout_seconds: float = 120) -> None:
        self.attempts = attempts
        self.timeout_seconds = timeout_seconds
        self.opener = build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def get(self, url: str) -> tuple[bytes, str]:
        return self._request(Request(url, headers={"User-Agent": "Mwangaza-NDMA-import/1"}))

    def post(self, url: str, fields: dict[str, str]) -> tuple[bytes, str]:
        request = Request(
            url,
            data=urlencode(fields).encode(),
            headers={
                "User-Agent": "Mwangaza-NDMA-import/1",
                "Referer": NDMA_ARCHIVE_URL,
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        return self._request(request)

    def _request(self, request: Request) -> tuple[bytes, str]:
        for attempt in range(self.attempts):
            try:
                with self.opener.open(request, timeout=self.timeout_seconds) as response:
                    return response.read(), response.geturl()
            except (HTTPError, URLError, TimeoutError, OSError) as exc:
                if attempt + 1 == self.attempts:
                    raise LabelImportError(
                        f"NDMA request failed after {self.attempts} attempts: {request.full_url}"
                    ) from exc
                time.sleep(min(2**attempt, 8))
        raise AssertionError("unreachable")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2016-01", help="First archive month, YYYY-MM.")
    parser.add_argument("--end", default=date.today().strftime("%Y-%m"), help="Last month, YYYY-MM.")
    parser.add_argument(
        "--output", type=Path, default=Path("data/historical/ndma-drought-phases")
    )
    parser.add_argument("--index-only", action="store_true", help="Index bulletins without PDFs.")
    parser.add_argument("--document-limit", type=int, help="Limit PDF processing for a public smoke.")
    parser.add_argument("--retrieved-at", help="Fixed ISO timestamp for reproducible metadata.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    periods = _periods(args.start, args.end)
    print(f"Source: {NDMA_ARCHIVE_URL}")
    print(f"Period: {args.start} .. {args.end} ({len(periods)} months)")
    print(f"Output: {args.output}")
    print("Validation: exact county + month + unique COUNTY phase")
    if args.dry_run:
        return

    args.output.mkdir(parents=True, exist_ok=True)
    checkpoint_dir = args.output / "checkpoints" / "index"
    document_dir = args.output / "documents"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    document_dir.mkdir(parents=True, exist_ok=True)
    client = NdmaHttpClient()
    page_bytes, _ = client.get(NDMA_ARCHIVE_URL)
    current_page = page_bytes.decode("utf-8", "replace")
    indexed: list[NdmaBulletin] = []
    index_progress = EtaProgress("NDMA archive indexing")
    for number, (year, month) in enumerate(periods, 1):
        checkpoint = checkpoint_dir / f"{year:04d}-{month:02d}.json"
        if checkpoint.exists():
            payload = json.loads(checkpoint.read_text(encoding="utf-8"))
            rows = tuple(NdmaBulletin(**item) for item in payload["bulletins"])
        else:
            try:
                index = ndma_period_postback_index(current_page, year, month)
            except LabelImportError as exc:
                if "does not list" not in str(exc):
                    raise
                rows = ()
            else:
                fields = _form_fields(current_page)
                fields["__EVENTTARGET"] = YEAR_TREE_TARGET
                fields["__EVENTARGUMENT"] = canonical_json(
                    {"commandName": "Click", "index": index}
                )
                response, _ = client.post(NDMA_ARCHIVE_URL, fields)
                current_page = response.decode("utf-8", "replace")
                rows = parse_ndma_archive_html(
                    current_page, expected_year=year, expected_month=month
                )
            _atomic_json(
                checkpoint,
                {
                    "period": f"{year:04d}-{month:02d}",
                    "source_url": NDMA_ARCHIVE_URL,
                    "bulletins": [asdict(item) for item in rows],
                },
            )
        indexed.extend(rows)
        index_progress(number, len(periods))

    duplicates = _duplicates(item.document_id for item in indexed)
    if duplicates:
        raise LabelImportError(f"NDMA index repeats document ids: {', '.join(duplicates[:5])}")
    if args.index_only:
        _write_index_manifest(args.output, indexed, args.retrieved_at)
        print(f"Indexed bulletins: {len(indexed)}")
        return

    try:
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError
    except ImportError as exc:
        raise SystemExit(
            "pypdf is required for conservative PDF extraction. Run with: "
            "uv run --with pypdf python scripts/backfill_ndma_drought_phases.py"
        ) from exc

    kenya_regions = tuple(
        region
        for region in list_regions(level=ADM1_LEVEL, include_administrative=True)
        if region.iso3 == "KEN"
    )
    county_index = build_adm1_name_index(kenya_regions, iso3="KEN")
    selected = indexed[: args.document_limit] if args.document_limit else indexed
    records: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []
    document_progress = EtaProgress("NDMA PDF treatment")
    for number, bulletin in enumerate(selected, 1):
        pdf_path = document_dir / f"{bulletin.document_id}.pdf"
        url_path = document_dir / f"{bulletin.document_id}.url"
        cached = pdf_path.exists() and url_path.exists()
        if cached:
            pdf_data = pdf_path.read_bytes()
            document_url = url_path.read_text(encoding="utf-8").strip()
        else:
            download = download_ndma_document(client.get, bulletin)
            if download.data is None:
                _atomic_text(url_path, download.url + "\n")
                review.append(
                    _document_review(
                        bulletin,
                        document_url=download.url,
                        reason="document_unavailable_after_retries",
                        detail=download.error or "NDMA document is unavailable",
                    )
                )
                document_progress(number, len(selected))
                continue
            pdf_data = download.data
            document_url = download.url

        text: str | None = None
        pdf_error = ""
        for repair_pass in range(1, 4):
            if is_complete_pdf(pdf_data):
                try:
                    text = "\n".join(
                        page.extract_text() or ""
                        for page in PdfReader(io.BytesIO(pdf_data)).pages
                    )
                except (PdfReadError, OSError, ValueError) as exc:
                    pdf_error = f"{type(exc).__name__}: {exc}"
                else:
                    _atomic_bytes(pdf_path, pdf_data)
                    _atomic_text(url_path, document_url + "\n")
                    break
            else:
                pdf_error = "missing PDF header or terminal %%EOF marker"
            if repair_pass < 3:
                print(
                    f"NDMA {bulletin.document_id}: PDF repair pass {repair_pass}/2 "
                    f"({pdf_error})"
                )
                download = download_ndma_document(client.get, bulletin)
                if download.data is None:
                    pdf_error = f"{pdf_error}; repair download failed: {download.error}"
                    break
                pdf_data = download.data
                document_url = download.url

        if text is None:
            _atomic_bytes(pdf_path, pdf_data)
            _atomic_text(url_path, document_url + "\n")
            review.append(
                {
                    "document_id": bulletin.document_id,
                    "county": bulletin.county,
                    "period": bulletin.period,
                    "detail_url": bulletin.detail_url,
                    "document_url": document_url,
                    "document_sha256": sha256_bytes(pdf_data),
                    "reason": "invalid_pdf_after_retries",
                    "detail": pdf_error,
                    "validation_status": "review_required",
                    "extraction_version": "pdf-integrity-v1",
                }
            )
            document_progress(number, len(selected))
            continue
        extraction = extract_ndma_phase(
            text,
            expected_county=bulletin.county,
            expected_year=bulletin.year,
            expected_month=bulletin.month,
        )
        adm1 = match_adm1_name(bulletin.county, county_index)
        if extraction.validation_status == "validated" and adm1:
            records.append(
                ndma_official_record(
                    bulletin,
                    extraction,
                    adm1_region_id=adm1,
                    document_url=document_url,
                    document_sha256=sha256_bytes(pdf_data),
                )
            )
        else:
            review.append(
                {
                    "document_id": bulletin.document_id,
                    "county": bulletin.county,
                    "period": bulletin.period,
                    "detail_url": bulletin.detail_url,
                    "document_url": document_url,
                    "document_sha256": sha256_bytes(pdf_data),
                    "reason": extraction.reason if adm1 else "county_not_in_adm1_catalog",
                    "validation_status": "review_required",
                    "extraction_version": extraction.extraction_version,
                }
            )
        document_progress(number, len(selected))

    ordered_records = sorted(records, key=lambda item: item["source_record_id"])
    ordered_review = sorted(review, key=lambda item: item["document_id"])
    official_path = args.output / "official-manifest.json"
    review_path = args.output / "review-queue.jsonl"
    _atomic_json(
        official_path,
        {
            "schema_version": "mwangaza.official-label-manifest.v1",
            "source": "Kenya National Drought Management Authority (NDMA)",
            "archive_url": NDMA_ARCHIVE_URL,
            "records": ordered_records,
        },
    )
    _atomic_text(review_path, "".join(canonical_json(item) + "\n" for item in ordered_review))
    manifest = {
        "schema_version": "mwangaza.ndma-drought-phase-backfill.v1",
        "retrieved_at": args.retrieved_at or datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "period_start": args.start,
        "period_end": args.end,
        "indexed_bulletin_count": len(indexed),
        "processed_bulletin_count": len(selected),
        "validated_record_count": len(ordered_records),
        "review_required_count": len(ordered_review),
        "complete": len(selected) == len(indexed),
        "official_manifest_sha256": sha256_file(official_path),
        "review_queue_sha256": sha256_file(review_path),
    }
    _atomic_json(args.output / "manifest.json", manifest)
    print(f"Indexed bulletins: {len(indexed)}")
    print(f"Validated phases: {len(ordered_records)}")
    print(f"Review required: {len(ordered_review)}")
    print(f"Complete: {manifest['complete']}")
    print(f"SHA-256: {manifest['official_manifest_sha256']}")


def _form_fields(value: str) -> dict[str, str]:
    parser = _InputParser()
    parser.feed(value)
    return parser.fields


def _document_review(
    bulletin: NdmaBulletin,
    *,
    document_url: str,
    reason: str,
    detail: str,
) -> dict[str, Any]:
    return {
        "document_id": bulletin.document_id,
        "county": bulletin.county,
        "period": bulletin.period,
        "detail_url": bulletin.detail_url,
        "document_url": document_url,
        "document_sha256": None,
        "reason": reason,
        "detail": detail,
        "validation_status": "review_required",
        "extraction_version": "document-availability-v1",
    }


def _periods(start: str, end: str) -> tuple[tuple[int, int], ...]:
    try:
        start_date = date.fromisoformat(start + "-01")
        end_date = date.fromisoformat(end + "-01")
    except ValueError as exc:
        raise SystemExit("--start and --end must use YYYY-MM") from exc
    if end_date < start_date:
        raise SystemExit("--end must not precede --start")
    result = []
    current = start_date
    while current <= end_date:
        result.append((current.year, current.month))
        current = date(current.year + (current.month == 12), current.month % 12 + 1, 1)
    return tuple(result)


def _write_index_manifest(output: Path, rows: list[NdmaBulletin], retrieved_at: str | None) -> None:
    path = output / "bulletin-index.jsonl"
    ordered = sorted(rows, key=lambda item: item.document_id)
    _atomic_text(path, "".join(canonical_json(asdict(item)) + "\n" for item in ordered))
    _atomic_json(
        output / "manifest.json",
        {
            "schema_version": "mwangaza.ndma-drought-phase-backfill.v1",
            "retrieved_at": retrieved_at or datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "indexed_bulletin_count": len(ordered),
            "processed_bulletin_count": 0,
            "complete": False,
            "bulletin_index_sha256": sha256_file(path),
        },
    )


def _duplicates(values: Any) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen and value not in result:
            result.append(value)
        seen.add(value)
    return result


def _atomic_json(path: Path, value: object) -> None:
    _atomic_text(path, canonical_json(value) + "\n")


def _atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def _atomic_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(value)
    os.replace(temporary, path)


if __name__ == "__main__":
    main()
