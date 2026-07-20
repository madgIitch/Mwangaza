"""Restore the versioned Mwangaza demo baseline without touching non-demo state."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "demo_data" / "baseline.json"
DEFAULT_STATE = ROOT / ".demo" / "baseline-state.json"


def reset_demo(state_path: Path = DEFAULT_STATE) -> dict:
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    if baseline.get("is_demo") is not True:
        raise ValueError("demo baseline must declare is_demo=true")
    state_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = state_path.with_suffix(state_path.suffix + ".tmp")
    temporary.write_text(json.dumps(baseline, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(state_path)
    return baseline


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    args = parser.parse_args()
    print(json.dumps(reset_demo(args.state.resolve()), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
