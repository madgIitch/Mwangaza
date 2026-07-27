"""Import independent drought and food-security labels into a local ADM1 catalog."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from mwangaza.probabilistic.independent_labels import (
    IndependentLabel,
    LabelExclusion,
    LabelImportError,
    SpatialMatch,
    import_emdat_csv,
    import_official_manifest,
    map_geometry_to_adm1,
    normalize_fews_record,
    normalize_ipc_record,
    sha256_json,
    utc_now,
    write_label_artifact,
)
from mwangaza.probabilistic.label_sources import FewsNetDownloader, JsonHttpClient, fetch_ipc_payload
from mwangaza.probabilistic.progress import EtaProgress
from mwangaza.regions import ADM1_LEVEL, list_regions

IGAD_ISO2 = ("DJ", "ER", "ET", "KE", "SO", "SS", "SD", "UG")
ISO2_TO_ISO3 = {
    "DJ": "DJI",
    "ER": "ERI",
    "ET": "ETH",
    "KE": "KEN",
    "SO": "SOM",
    "SS": "SSD",
    "SD": "SDN",
    "UG": "UGA",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        action="append",
        choices=("fews", "ipc", "official", "emdat"),
        default=[],
        help="Source adapter to run; repeat to merge sources. Default: FEWS NET.",
    )
    parser.add_argument("--country", action="append", default=[], help="ISO2 country for FEWS NET.")
    parser.add_argument("--official-input", type=Path, help="Validated local official-label JSON manifest.")
    parser.add_argument("--emdat-input", type=Path, help="Registered local EM-DAT CSV export.")
    parser.add_argument("--ipc-url", help="IPC API endpoint returning assessed-area records.")
    parser.add_argument("--output", type=Path, default=Path("data/historical/independent-labels"))
    parser.add_argument("--page-size", type=int, default=1000)
    parser.add_argument("--page-limit", type=int, help="Maximum FEWS pages per country; useful for smoke tests.")
    parser.add_argument("--retrieved-at", default=None, help="Fixed ISO timestamp for reproducible manifests.")
    parser.add_argument("--emdat-access-date", help="Required YYYY-MM-DD access date for EM-DAT.")
    parser.add_argument("--emdat-license", default="EM-DAT registered non-commercial access")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    sources = tuple(dict.fromkeys(args.source or ["fews"]))
    countries = tuple(dict.fromkeys(code.upper() for code in (args.country or IGAD_ISO2)))
    invalid = sorted(set(countries) - set(IGAD_ISO2))
    if invalid:
        parser.error(f"countries outside the versioned IGAD catalog: {', '.join(invalid)}")
    if "official" in sources and (
        not args.official_input or args.official_input.suffix.lower() != ".json"
    ):
        parser.error("official import requires --official-input with a JSON manifest")
    if "emdat" in sources and (not args.emdat_input or not args.emdat_access_date):
        parser.error("EM-DAT import requires --emdat-input and --emdat-access-date")
    if "ipc" in sources and not args.ipc_url:
        parser.error("IPC import requires --ipc-url")

    print(f"Sources: {', '.join(sources)}")
    if "fews" in sources:
        print(f"FEWS NET countries: {', '.join(countries)}")
    print(f"Output: {args.output}")
    print("Training eligibility: assessed/current observations only")
    if args.dry_run:
        return

    regions = list_regions(level=ADM1_LEVEL, include_administrative=True)
    if len(regions) != 121:
        parser.error(f"versioned ADM1 catalog must contain 121 regions, got {len(regions)}")
    labels: list[IndependentLabel] = []
    exclusions: list[LabelExclusion] = []
    source_statuses = {
        name: ("requested" if name in sources else "disabled_unknown")
        for name in ("fews", "ipc", "official", "emdat")
    }
    client = JsonHttpClient()

    if "fews" in sources:
        downloader = FewsNetDownloader(client, args.output / "checkpoints")
        fews_failures: list[str] = []
        for country in countries:
            rows = None
            last_error: LabelImportError | None = None
            for repair_pass in range(1, 6):
                try:
                    rows = downloader.download_country(
                        country,
                        page_size=args.page_size,
                        page_limit=args.page_limit,
                        progress=EtaProgress(f"FEWS NET {country} download"),
                    )
                    break
                except LabelImportError as exc:
                    last_error = exc
                    if "pagination changed during download" not in str(exc) or args.page_limit is not None:
                        break
                    print(f"FEWS NET {country}: repair pass {repair_pass}/5 required")
            if rows is None:
                exc = last_error or LabelImportError("unknown FEWS NET failure")
                exclusions.append(LabelExclusion("FEWS NET", country, "source_unavailable", str(exc)))
                fews_failures.append(country)
                continue
            if not rows:
                exclusions.append(LabelExclusion("FEWS NET", country, "no_public_coverage", "unknown"))
            country_regions = tuple(region for region in regions if region.iso3 == ISO2_TO_ISO3[country])
            match_cache: dict[str, tuple[object, str]] = {}
            progress = EtaProgress(f"FEWS NET {country} normalization")
            for index, record in enumerate(rows, 1):
                fnid = str(record.get("fnid") or "")
                try:
                    if not fnid:
                        raise LabelImportError("record lacks FNID")
                    if fnid not in match_cache:
                        match_cache[fnid] = _fews_matches(
                            downloader,
                            fnid,
                            country_regions,
                            args.output / "checkpoints" / "fews-matches" / f"{fnid}.json",
                        )
                    matches, geometry_hash = match_cache[fnid]
                    normalized, exclusion = normalize_fews_record(
                        record,
                        matches=matches,  # type: ignore[arg-type]
                        geometry_hash=geometry_hash,
                    )
                    labels.extend(normalized)
                    if exclusion:
                        exclusions.append(exclusion)
                except LabelImportError as exc:
                    exclusions.append(
                        LabelExclusion("FEWS NET", str(record.get("id", "")), "geometry_error", str(exc))
                    )
                progress(index, len(rows))
        source_statuses["fews"] = "partial_unknown" if fews_failures else "ingested"

    if "ipc" in sources:
        payload = fetch_ipc_payload(client, args.ipc_url, api_key=os.environ.get("IPC_API_KEY"))
        records = _records(payload)
        for record in records:
            geometry = record.get("geometry")
            if not isinstance(geometry, dict):
                exclusions.append(LabelExclusion("IPC", str(record.get("id", "")), "missing_geometry", ""))
                continue
            matches = map_geometry_to_adm1(geometry, regions)
            normalized, exclusion = normalize_ipc_record(
                record, matches=matches, artifact_hash=sha256_json(payload)
            )
            labels.extend(normalized)
            if exclusion:
                exclusions.append(exclusion)
        source_statuses["ipc"] = "ingested"

    if "official" in sources and args.official_input:
        labels.extend(import_official_manifest(args.official_input))
        source_statuses["official"] = "ingested"
    if "emdat" in sources and args.emdat_input and args.emdat_access_date:
        labels.extend(
            import_emdat_csv(
                args.emdat_input,
                access_date=args.emdat_access_date,
                license_policy=args.emdat_license,
            )
        )
        source_statuses["emdat"] = "ingested"

    manifest = write_label_artifact(
        labels,
        exclusions,
        args.output,
        retrieved_at=args.retrieved_at or utc_now(),
        source_statuses=source_statuses,
    )
    print(f"Labels: {manifest['label_count']}")
    print(f"Excluded: {manifest['exclusion_count']}")
    print(f"ADM1 covered: {len(manifest['regions'])}/121")
    print(f"SHA-256: {manifest['labels_sha256']}")
    if not manifest["complete"]:
        parser.error("artifact is partial; inspect source_unavailable exclusions and rerun")


def _records(payload: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    value = payload.get("results", payload.get("data", []))
    if not isinstance(value, list):
        raise LabelImportError("IPC response lacks a records list")
    return tuple(item for item in value if isinstance(item, dict))


def _fews_matches(
    downloader: FewsNetDownloader,
    fnid: str,
    regions: tuple[object, ...],
    cache_path: Path,
) -> tuple[object, str]:
    if cache_path.exists():
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        matches = tuple(
            SpatialMatch(
                adm1_region_id=item["adm1_region_id"],
                source_fraction=item["source_fraction"],
                adm1_fraction=item["adm1_fraction"],
                mapping_method=item["mapping_method"],
            )
            for item in payload["matches"]
        )
        return matches, str(payload["geometry_sha256"])
    geometry, geometry_payload = downloader.geometry(fnid)
    geometry_hash = sha256_json(geometry_payload)
    matches = map_geometry_to_adm1(geometry, regions)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = cache_path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(
            {
                "mapping_version": "adm1-geometry-overlap-v1",
                "geometry_sha256": geometry_hash,
                "matches": [item.__dict__ for item in matches],
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, cache_path)
    return matches, geometry_hash


if __name__ == "__main__":
    main()
