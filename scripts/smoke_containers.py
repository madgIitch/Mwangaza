from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


CHECKS: tuple[tuple[str, str], ...] = (
    ("API health", "http://127.0.0.1:18081/health"),
    ("API readiness", "http://127.0.0.1:18081/ready"),
    ("Web health", "http://127.0.0.1:18080/healthz"),
    ("SPA deep route", "http://127.0.0.1:18080/overview?layer=episodes"),
    ("Same-origin API", "http://127.0.0.1:18080/api/v1/snapshots/latest"),
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and smoke-test Mwangaza containers")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--keep", action="store_true", help="Leave Compose services running")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()

    command = ["docker", "compose", "up", "--detach"]
    if not args.skip_build:
        command.append("--build")

    print("[containers 1/3] Starting API and web services")
    try:
        _run(command)
        print("[containers 2/3] Waiting for health, readiness and SPA routes")
        results = _wait_for_checks(args.timeout)
        _validate_payloads(results)
        print("[containers 3/3] PASS: API, proxy and frontend are ready")
    finally:
        if not args.keep:
            print("[containers cleanup] Stopping the isolated Compose stack")
            subprocess.run(
                ["docker", "compose", "down", "--remove-orphans"],
                check=False,
            )


def _run(command: list[str]) -> None:
    try:
        subprocess.run(command, check=True)
    except FileNotFoundError as exc:
        raise SystemExit("Docker CLI is not installed or is not on PATH") from exc
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"Container command failed with exit code {exc.returncode}") from exc


def _wait_for_checks(timeout_seconds: int) -> dict[str, bytes]:
    deadline = time.monotonic() + timeout_seconds
    pending = dict(CHECKS)
    results: dict[str, bytes] = {}
    last_error = "not started"
    while pending and time.monotonic() < deadline:
        for name, url in tuple(pending.items()):
            try:
                request = Request(url, headers={"Accept": "application/json,text/html"})
                with urlopen(request, timeout=5) as response:
                    if response.status != 200:
                        raise RuntimeError(f"HTTP {response.status}")
                    results[name] = response.read()
                del pending[name]
                print(f"  PASS {name}: {url}")
            except (OSError, RuntimeError, URLError) as exc:
                last_error = f"{name}: {exc}"
        if pending:
            time.sleep(2)
    if pending:
        names = ", ".join(pending)
        raise SystemExit(f"Timed out waiting for {names}; last error: {last_error}")
    return results


def _validate_payloads(results: dict[str, bytes]) -> None:
    health = _json(results["API health"])
    proxied = _json(results["Same-origin API"])
    if health.get("is_demo") is not True or health.get("data_mode") != "demo":
        raise SystemExit("API health does not identify the explicit demo profile")
    if proxied.get("is_demo") is not True or proxied.get("data_mode") != "demo":
        raise SystemExit("Same-origin snapshot is not the explicit demo payload")
    spa = results["SPA deep route"].decode("utf-8", errors="ignore")
    if '<div id="root"></div>' not in spa:
        raise SystemExit("SPA deep route did not return the React entrypoint")


def _json(payload: bytes) -> dict[str, Any]:
    try:
        value = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise SystemExit("Expected a JSON health or API response") from exc
    if not isinstance(value, dict):
        raise SystemExit("Expected a JSON object")
    return value


if __name__ == "__main__":
    main()
