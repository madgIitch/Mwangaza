"""Audit real drought-hazard episodes by ADM1, country, and compatible source."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mwangaza.probabilistic.drought_hazards import (
    audit_drought_hazard_episodes,
    canonical_json,
    load_independent_labels,
)
from mwangaza.probabilistic.independent_labels import sha256_file
from mwangaza.regions import ADM1_LEVEL, list_regions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--labels",
        type=Path,
        action="append",
        required=True,
        help="Label JSONL or artifact directory; repeat to merge sources.",
    )
    parser.add_argument(
        "--authority-catalog",
        type=Path,
        default=Path("docs/data-sources/igad-drought-authorities.json"),
    )
    parser.add_argument(
        "--output", type=Path, default=Path("data/historical/drought-hazard-audit")
    )
    parser.add_argument("--max-gap-days", type=int, default=32)
    parser.add_argument("--audited-at", help="Fixed ISO timestamp for reproducible metadata.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.max_gap_days < 0:
        parser.error("--max-gap-days must be non-negative")
    print(f"Label artifacts: {', '.join(str(path) for path in args.labels)}")
    print(f"Episode continuity: <= {args.max_gap_days} days")
    print(f"Output: {args.output}")
    if args.dry_run:
        return

    labels = load_independent_labels(args.labels)
    regions = list_regions(level=ADM1_LEVEL, include_administrative=True)
    adm1_country = {region.id: region.iso3 for region in regions}
    report = audit_drought_hazard_episodes(
        labels, adm1_country=adm1_country, max_gap_days=args.max_gap_days
    )
    authorities = _authority_coverage(args.authority_catalog)
    covered_countries = {
        adm1_country[str(item["adm1_region_id"])]
        for item in labels
        if item.get("label_semantics") == "drought_hazard_event"
        and item.get("adm1_region_id") in adm1_country
        and item.get("review_status") in {"validated", "source_unit_explicit"}
    }
    covered_countries.update(
        str(item.get("metadata", {}).get("country_iso3"))
        for item in labels
        if item.get("label_semantics") == "drought_hazard_event"
        and not item.get("adm1_region_id")
        and isinstance(item.get("metadata"), dict)
        and item.get("metadata", {}).get("country_iso3")
    )
    report["authority_coverage"] = [
        {
            **item,
            "audited_episode_coverage": (
                "present" if item["country_iso3"] in covered_countries else "unknown"
            ),
        }
        for item in authorities
    ]
    report["unknown_country_count"] = sum(
        item["audited_episode_coverage"] == "unknown" for item in report["authority_coverage"]
    )

    args.output.mkdir(parents=True, exist_ok=True)
    episodes_path = args.output / "episodes.jsonl"
    audit_path = args.output / "audit.json"
    _atomic_text(
        episodes_path,
        "".join(canonical_json(item) + "\n" for item in report.pop("episodes")),
    )
    report["episodes_sha256"] = sha256_file(episodes_path)
    report["audited_at"] = args.audited_at or datetime.now(UTC).isoformat().replace("+00:00", "Z")
    report["input_sha256"] = "sha256:" + hashlib.sha256(
        canonical_json(labels).encode()
    ).hexdigest()
    _atomic_text(audit_path, canonical_json(report) + "\n")
    print(f"Hazard labels: {report['hazard_label_count']}")
    print(f"ADM1 episodes: {report['episode_count']}")
    print(f"ADM1 covered: {report['adm1_count']}/121")
    print(f"Country-only evidence: {report['country_only_count']}")
    print(f"Unvalidated evidence: {report['unvalidated_count']}")
    print(f"Countries unknown: {report['unknown_country_count']}/8")
    print(f"SHA-256: {report['episodes_sha256']}")


def _authority_coverage(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    countries = payload.get("countries") if isinstance(payload, dict) else None
    if not isinstance(countries, list) or len(countries) != 8:
        raise SystemExit("authority catalog must contain exactly 8 IGAD countries")
    return [
        {
            "country_iso3": str(item["country_iso3"]),
            "authority": item.get("authority"),
            "catalog_status": item.get("status", "unknown"),
            "source_granularity": item.get("granularity", "unknown"),
        }
        for item in countries
    ]


def _atomic_text(path: Path, value: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


if __name__ == "__main__":
    main()
