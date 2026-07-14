from __future__ import annotations

import argparse
import json

from mwangaza.regions import load_region_catalog


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the Mwangaza IGAD region catalog.")
    parser.add_argument("--validate", action="store_true", help="Validate the catalog and print a summary.")
    args = parser.parse_args(argv)
    if not args.validate:
        parser.print_help()
        return 2

    regions = load_region_catalog()
    summary = {
        "status": "ok",
        "regions": len(regions),
        "countries": len([region for region in regions if region.level == "country"]),
        "pilots": len([region for region in regions if region.is_pilot]),
    }
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
