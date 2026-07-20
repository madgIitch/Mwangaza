from __future__ import annotations

import subprocess
from pathlib import Path

from mwangaza.security import scan_files


def tracked_files() -> list[Path]:
    result = subprocess.run(["git", "ls-files"], check=True, capture_output=True, text=True)
    return [Path(line) for line in result.stdout.splitlines() if line and Path(line).is_file()]


def main() -> int:
    findings = scan_files(tracked_files())
    for finding in findings:
        print(f"{finding.path}: {finding.rule}")
    if findings:
        print(f"Security scan failed with {len(findings)} finding(s).")
        return 1
    print("Security scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
