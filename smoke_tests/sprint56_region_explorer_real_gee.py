from __future__ import annotations

import argparse
import json
from pathlib import Path

from mwangaza.gee.auth import check_gee_auth
from mwangaza.services.dashboard_shell import _dashboard_data_from_payloads
from mwangaza.services.live_gee_dashboard import load_live_gee_dashboard_payloads


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
    }
    print(json.dumps({"ok": all(checks.values()), "region_id": args.region_id, "checks": checks}, sort_keys=True))
    return 0 if all(checks.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
