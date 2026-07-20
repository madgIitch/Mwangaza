"""Prepare the deterministic, offline Somalia end-to-end demo scenario."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = ROOT / "tests" / "fixtures" / "scenarios" / "somalia" / "snapshot.json"
DEFAULT_STATE = ROOT / ".demo" / "somalia-state.json"
REQUIRED_ARTIFACTS = ("map", "trend", "score", "quality", "action", "report")


class ScenarioError(ValueError):
    """Raised when the local scenario cannot be prepared safely."""


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ScenarioError(f"{label} not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ScenarioError(f"{label} is not valid JSON: {path}: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ScenarioError(f"{label} must contain a JSON object: {path}")
    return payload


def validate_fixture(payload: dict[str, Any]) -> None:
    snapshot_id = payload.get("snapshot_id")
    if not isinstance(snapshot_id, str) or not snapshot_id.strip():
        raise ScenarioError("fixture requires a non-empty snapshot_id")
    if payload.get("mode") not in {"demo", "simulated"}:
        raise ScenarioError("fixture mode must be demo or simulated")
    for field in ("region", "period"):
        if not isinstance(payload.get(field), dict) or not payload[field]:
            raise ScenarioError(f"fixture requires a non-empty {field} object")
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ScenarioError("fixture requires an artifacts object")
    missing = [name for name in REQUIRED_ARTIFACTS if not isinstance(artifacts.get(name), dict)]
    if missing:
        raise ScenarioError(f"fixture is missing required artifacts: {', '.join(missing)}")
    for name, artifact in artifacts.items():
        if artifact.get("snapshot_id") != snapshot_id:
            raise ScenarioError(f"artifact {name} is not linked to snapshot_id {snapshot_id}")
        if artifact.get("provenance") not in {"demo", "simulated"}:
            raise ScenarioError(f"artifact {name} must be labelled demo or simulated")
    alert = payload.get("alert")
    notification = payload.get("notification")
    if not isinstance(alert, dict) or not alert.get("alert_id"):
        raise ScenarioError("fixture requires an alert with alert_id")
    if alert.get("snapshot_id") != snapshot_id or alert.get("provenance") != "simulated":
        raise ScenarioError("alert must be linked to the snapshot and labelled simulated")
    if not isinstance(notification, dict) or not notification.get("notification_id"):
        raise ScenarioError("fixture requires a notification with notification_id")
    if notification.get("snapshot_id") != snapshot_id or notification.get("status") != "simulated":
        raise ScenarioError("notification must be linked to the snapshot and simulated")
    if "recipient" in notification:
        raise ScenarioError("simulated notification must not contain a real recipient")


def prepare_scenario(fixture_path: Path, state_path: Path) -> dict[str, Any]:
    fixture = _load_json(fixture_path, "fixture")
    validate_fixture(fixture)
    state = _load_json(state_path, "state") if state_path.exists() else {"version": 1, "scenarios": {}}
    scenarios = state.setdefault("scenarios", {})
    if not isinstance(scenarios, dict):
        raise ScenarioError("state scenarios must be a JSON object")
    snapshot_id = fixture["snapshot_id"]
    result = {
        "status": "complete", "mode": "demo", "is_demo": True, "offline": True, "reference_date": "2026-03-31",
        "snapshot_id": snapshot_id, "region": fixture["region"], "period": fixture["period"],
        "artifacts": fixture["artifacts"],
        "alerts": {fixture["alert"]["alert_id"]: fixture["alert"]},
        "notifications": {fixture["notification"]["notification_id"]: fixture["notification"]},
    }
    scenarios[snapshot_id] = result
    state_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = state_path.with_suffix(state_path.suffix + ".tmp")
    temporary.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(state_path)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    args = parser.parse_args(argv)
    try:
        result = prepare_scenario(args.fixture.resolve(), args.state.resolve())
    except ScenarioError as exc:
        print(f"Somalia demo scenario failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
