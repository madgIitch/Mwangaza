from __future__ import annotations

import argparse
from typing import Sequence

from mwangaza.pipeline import PipelineConfig, PipelineTask, RegionRunResult, run_refresh_pipeline


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mwangaza")
    sub = parser.add_subparsers(dest="command", required=True)
    refresh = sub.add_parser("refresh-pipeline")
    refresh.add_argument("--region", action="append", dest="regions", default=[])
    refresh.add_argument("--max-concurrency", type=int, default=2)
    refresh.add_argument("--max-failure-fraction", type=float, default=0.25)
    refresh.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if args.command == "refresh-pipeline":
        regions = args.regions or ["ken"]
        tasks = [
            PipelineTask(
                region,
                lambda region_id: RegionRunResult(region_id, "cache_hit", "dry-run"),
            )
            for region in regions
        ]
        run = run_refresh_pipeline(
            tasks,
            config=PipelineConfig(
                max_concurrency=args.max_concurrency,
                max_failure_fraction=args.max_failure_fraction,
                dry_run=args.dry_run,
            ),
        )
        print(run.to_json())
        return run.exit_code
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
