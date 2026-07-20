"""Run the deterministic, offline Northern Kenya demo scenario."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = ROOT / "tests" / "fixtures" / "scenarios" / "kenya" / "snapshot.json"
DEFAULT_STATE = ROOT / ".demo" / "kenya-state.json"
SEVERITY = {"unknown": 0, "normal": 1, "watch": 2, "warning": 3, "critical": 4}


class ScenarioError(ValueError):
    pass


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ScenarioError(f"fixture not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ScenarioError(f"fixture is not valid JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise ScenarioError("fixture must be a JSON object")
    return value


def prepare_scenario(fixture_path: Path, state_path: Path, unit_id: str | None = None, language: str = "en") -> dict[str, Any]:
    fixture = _load(fixture_path)
    snapshot_id, units = fixture.get("snapshot_id"), fixture.get("units")
    if not snapshot_id or not isinstance(units, list) or len(units) < 3:
        raise ScenarioError("fixture requires snapshot_id and at least three units")
    ids = {unit.get("unit_id") for unit in units if isinstance(unit, dict)}
    if len(ids) != len(units) or None in ids:
        raise ScenarioError("units require unique unit_id values")
    for unit in units:
        if not unit.get("report") or not unit.get("indicators") or unit.get("severity") not in SEVERITY:
            raise ScenarioError(f"unit {unit.get('unit_id', 'unknown')} requires indicators, severity and report")
    highlighted = sorted(units, key=lambda u: (-SEVERITY[u["severity"]], -float(u.get("score", 0)), u["unit_id"]))[0]
    selected = next((unit for unit in units if unit["unit_id"] == unit_id), highlighted)
    templates = fixture.get("templates", {})
    effective = language if language in templates else "en"
    warnings = [] if effective == language else [{"code": "language_fallback", "requested": language, "effective": effective}]
    notification_id = f"notification-{snapshot_id}-{selected['unit_id']}-{effective}"
    result = {
        "status": "complete", "mode": "demo", "is_demo": True, "offline": True, "reference_date": "2026-03-31", "snapshot_id": snapshot_id,
        "units": units, "selected_unit": selected["unit_id"], "highlighted_unit": highlighted["unit_id"],
        "detail": {**selected, "snapshot_id": snapshot_id, "provenance": "demo"},
        "report": {**selected["report"], "snapshot_id": snapshot_id, "unit_id": selected["unit_id"]},
        "alert": {"alert_id": f"alert-{snapshot_id}-{selected['unit_id']}", "snapshot_id": snapshot_id, "unit_id": selected["unit_id"], "provenance": "simulated"},
        "notification": {"notification_id": notification_id, "snapshot_id": snapshot_id, "unit_id": selected["unit_id"], "status": "simulated", "content": templates[effective].format(unit=selected["name"])},
        "requested_language": language, "effective_language": effective, "warnings": warnings,
    }
    state = _load(state_path) if state_path.exists() else {"version": 1, "scenarios": {}}
    state.setdefault("scenarios", {})[snapshot_id] = result
    state_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = state_path.with_suffix(state_path.suffix + ".tmp")
    temporary.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(state_path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--unit")
    parser.add_argument("--language", default="en")
    args = parser.parse_args()
    try:
        print(json.dumps(prepare_scenario(args.fixture.resolve(), args.state.resolve(), args.unit, args.language), indent=2, sort_keys=True))
    except ScenarioError as exc:
        print(f"Northern Kenya demo scenario failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
