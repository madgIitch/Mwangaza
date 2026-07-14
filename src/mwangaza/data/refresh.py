from __future__ import annotations

import argparse

from mwangaza._foundation import foundation_status
from mwangaza.config import ConfigurationError, load_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mwangaza data refresh entrypoint.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the refresh entrypoint without remote service calls.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    status = foundation_status()
    try:
        settings = load_settings()
    except ConfigurationError as exc:
        print(str(exc))
        return 1

    if not args.dry_run:
        print("Mwangaza foundation stub: use --dry-run in Sprint 0; no remote services queried.")
        return 2

    print(
        f"{status.project} {status.version} {status.status}: "
        f"dry run only for {settings.environment}; no remote services queried."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
