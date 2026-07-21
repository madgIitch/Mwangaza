from __future__ import annotations

import argparse
import json
from pathlib import Path

from mwangaza.gee.auth import check_gee_auth
from mwangaza.services.dashboard_shell import _dashboard_data_from_payloads
from mwangaza.services.live_gee_dashboard import (
    dashboard_live_adm1_region_ids,
    load_live_gee_dashboard_payloads,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sprint 56 real-GEE Region Explorer smoke.")
    parser.add_argument("--region-id", default="som")
    args = parser.parse_args()
    auth = check_gee_auth()
    if auth.status != "ok":
        print(json.dumps({"ok": False, "gee": auth.to_public_dict()}, sort_keys=True))
        return 1
    payloads = tuple(load_live_gee_dashboard_payloads(region_id=args.region_id))
    dashboard = _dashboard_data_from_payloads(
        payloads,
        Path(".data/nonexistent-alerts.db"),
        mode="live",
        source_observed="Google Earth Engine live query",
        source_simulated="invalid",
        message_observed="Using live Google Earth Engine data",
        message_simulated="invalid",
    )
    profile = None if dashboard is None else next((item for item in dashboard.region_profiles if item.region_id == args.region_id), None)
    expected_adm1_ids = set(dashboard_live_adm1_region_ids())
    adm1_risks = {
        str(payload.get("region_id")): payload
        for payload in payloads
        if payload.get("payload_type") == "risk_snapshot"
        and isinstance(payload.get("metadata"), dict)
        and payload["metadata"].get("region_level") == "adm1"
    }
    conclusive_adm1_ids = {
        region_id
        for region_id, payload in adm1_risks.items()
        if payload.get("composite_score") is not None and payload.get("quality_flag") == "ok"
    }
    non_conclusive_details = {
        region_id: {
            str(payload.get("indicator")): payload.get("value")
            for payload in payloads
            if payload.get("payload_type") == "indicator_observation"
            and payload.get("region_id") == region_id
        }
        for region_id in sorted(set(adm1_risks) - conclusive_adm1_ids)
    }
    checks = {
        "dashboard": dashboard is not None,
        "mode_live": dashboard is not None and dashboard.data_status.mode == "live",
        "not_demo": not any(payload.get("is_simulated") is True for payload in payloads),
        "map": dashboard is not None and bool(dashboard.risk_map.regions),
        "profile": profile is not None,
        "metrics": profile is not None and bool(profile.metrics),
        "contributions": profile is not None and bool(profile.contributions),
        "trends": profile is not None and bool(profile.trends),
        "historical": profile is not None and profile.historical_comparison is not None,
        "recommendations": profile is not None and bool(profile.recommendations),
        "adm1_contract": profile is not None and bool(profile.administrative_units),
        "adm1_boundary_ids": profile is not None and all(
            unit.boundary_id and unit.boundary_iso for unit in profile.administrative_units
        ),
        "adm1_conclusive": profile is not None and any(
            unit.score is not None and unit.quality_flag == "ok" for unit in profile.administrative_units
        ),
        "adm1_full_scope": set(adm1_risks) == expected_adm1_ids,
        "adm1_all_conclusive": conclusive_adm1_ids == expected_adm1_ids,
    }
    print(json.dumps({
        "ok": all(checks.values()),
        "region_id": args.region_id,
        "adm1_units": 0 if profile is None else len(profile.administrative_units),
        "adm1_units_total": len(adm1_risks),
        "adm1_units_conclusive": len(conclusive_adm1_ids),
        "adm1_units_not_conclusive": sorted(set(adm1_risks) - conclusive_adm1_ids),
        "adm1_not_conclusive_details": non_conclusive_details,
        "checks": checks,
    }, sort_keys=True))
    return 0 if all(checks.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
