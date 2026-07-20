from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

REQUIRED_COUNTRIES: dict[str, str] = {
    "KEN": "Kenya",
    "ETH": "Ethiopia",
    "SOM": "Somalia",
    "SDN": "Sudan",
    "SSD": "South Sudan",
    "UGA": "Uganda",
    "DJI": "Djibouti",
    "ERI": "Eritrea",
}
COUNTRY_LEVEL = "country"
PILOT_LEVEL = "pilot_area"
ADM1_LEVEL = "adm1"
REGIONAL_COVERAGE = "regional_country"
PILOT_COVERAGE = "pilot_subnational"
ADMINISTRATIVE_COVERAGE = "administrative_reference"
ADM1_SOURCE = "geoBoundaries gbOpen"
ADM1_SOURCE_VERSION = "wmgeolab/geoBoundaries@9469f09"


class RegionCatalogError(ValueError):
    pass


@dataclass(frozen=True)
class Region:
    id: str
    name: str
    iso3: str
    level: str
    parent_id: str | None
    is_pilot: bool
    coverage_type: str
    source: str
    source_version: str
    geometry: dict[str, Any]
    ui_geometry: dict[str, Any]
    metadata: dict[str, Any]

    @classmethod
    def from_dict(cls, item: dict[str, Any], *, source: str, source_version: str) -> Region:
        return cls(
            id=_required_str(item, "id"),
            name=_required_str(item, "name"),
            iso3=_required_str(item, "iso3").upper(),
            level=_required_str(item, "level"),
            parent_id=_optional_str(item, "parent_id"),
            is_pilot=_required_bool(item, "is_pilot"),
            coverage_type=_required_str(item, "coverage_type"),
            source=source,
            source_version=source_version,
            geometry=_required_dict(item, "geometry"),
            ui_geometry=_required_dict(item, "ui_geometry"),
            metadata=dict(item.get("metadata") or {}),
        )

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "iso3": self.iso3,
            "level": self.level,
            "parent_id": self.parent_id,
            "is_pilot": self.is_pilot,
            "coverage_type": self.coverage_type,
            "source": self.source,
            "source_version": self.source_version,
            "geometry": self.geometry,
            "ui_geometry": self.ui_geometry,
            "metadata": dict(self.metadata),
        }


def default_catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "regions" / "igad_regions.json"


@lru_cache(maxsize=8)
def load_region_catalog(path: str | Path | None = None) -> tuple[Region, ...]:
    catalog_path = Path(path) if path is not None else default_catalog_path()
    try:
        raw = json.loads(catalog_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise RegionCatalogError(f"could not read region catalog: {catalog_path}") from exc
    except json.JSONDecodeError as exc:
        raise RegionCatalogError(f"invalid region catalog JSON: {catalog_path}") from exc

    source = _required_str(raw, "source")
    source_version = _required_str(raw, "source_version")
    items = raw.get("regions")
    if not isinstance(items, list) or not items:
        raise RegionCatalogError("region catalog must include a non-empty regions list")
    regions = tuple(Region.from_dict(item, source=source, source_version=source_version) for item in items)
    if path is None:
        regions = (*regions, *_load_adm1_regions(regions))
    validate_region_catalog(regions)
    return regions


def get_region(region_id: str, catalog: Iterable[Region] | None = None) -> Region:
    target = region_id.strip().lower()
    for region in catalog or load_region_catalog():
        if region.id == target:
            return region
    raise RegionCatalogError(f"unknown region id: {region_id}")


def list_regions(
    level: str | None = None,
    include_pilots: bool = True,
    include_administrative: bool = False,
    catalog: Iterable[Region] | None = None,
) -> tuple[Region, ...]:
    regions = tuple(catalog or load_region_catalog())
    if level is not None:
        regions = tuple(region for region in regions if region.level == level)
    if not include_pilots:
        regions = tuple(region for region in regions if not region.is_pilot)
    if not include_administrative and level != ADM1_LEVEL:
        regions = tuple(region for region in regions if region.level != ADM1_LEVEL)
    return regions


def validate_region_catalog(catalog: Iterable[Region]) -> None:
    regions = tuple(catalog)
    if not regions:
        raise RegionCatalogError("region catalog is empty")

    ids = [region.id for region in regions]
    duplicates = _duplicates(ids)
    if duplicates:
        raise RegionCatalogError(f"duplicate region ids: {', '.join(duplicates)}")

    by_id = {region.id: region for region in regions}
    countries = [region for region in regions if region.level == COUNTRY_LEVEL]
    country_iso = [region.iso3 for region in countries]
    duplicate_iso = _duplicates(country_iso)
    if duplicate_iso:
        raise RegionCatalogError(f"duplicate country ISO3 values: {', '.join(duplicate_iso)}")

    missing = sorted(set(REQUIRED_COUNTRIES) - set(country_iso))
    if missing:
        raise RegionCatalogError(f"missing required IGAD countries: {', '.join(missing)}")
    extra = sorted(set(country_iso) - set(REQUIRED_COUNTRIES))
    if extra:
        raise RegionCatalogError(f"unsupported country ISO3 values: {', '.join(extra)}")

    for region in regions:
        _validate_region(region, by_id)


def _validate_region(region: Region, by_id: dict[str, Region]) -> None:
    if region.level not in {COUNTRY_LEVEL, PILOT_LEVEL, ADM1_LEVEL}:
        raise RegionCatalogError(f"{region.id}: unsupported level {region.level}")
    if region.coverage_type not in {REGIONAL_COVERAGE, PILOT_COVERAGE, ADMINISTRATIVE_COVERAGE}:
        raise RegionCatalogError(f"{region.id}: unsupported coverage_type {region.coverage_type}")
    if region.level == COUNTRY_LEVEL and region.parent_id is not None:
        raise RegionCatalogError(f"{region.id}: country parent_id must be null")
    if region.level == PILOT_LEVEL:
        if not region.is_pilot or region.coverage_type != PILOT_COVERAGE:
            raise RegionCatalogError(f"{region.id}: pilot areas must be explicitly marked")
        if region.parent_id not in by_id:
            raise RegionCatalogError(f"{region.id}: parent_id does not exist")
    if region.level == ADM1_LEVEL:
        if region.is_pilot or region.coverage_type != ADMINISTRATIVE_COVERAGE:
            raise RegionCatalogError(f"{region.id}: ADM1 regions must be administrative references")
        if region.parent_id not in by_id or by_id[region.parent_id].level != COUNTRY_LEVEL:
            raise RegionCatalogError(f"{region.id}: ADM1 parent_id must reference a country")
    if region.level == COUNTRY_LEVEL and region.coverage_type != REGIONAL_COVERAGE:
        raise RegionCatalogError(f"{region.id}: countries must use regional coverage")
    if region.geometry is region.ui_geometry or region.geometry == region.ui_geometry:
        raise RegionCatalogError(f"{region.id}: geometry and ui_geometry must be separate")
    _validate_geojson(region.id, "geometry", region.geometry)
    _validate_geojson(region.id, "ui_geometry", region.ui_geometry)


def _validate_geojson(region_id: str, field: str, geometry: dict[str, Any]) -> None:
    geo_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if geo_type not in {"Polygon", "MultiPolygon"}:
        raise RegionCatalogError(f"{region_id}: {field} must be a Polygon or MultiPolygon GeoJSON object")
    if not isinstance(coordinates, list) or not coordinates:
        raise RegionCatalogError(f"{region_id}: {field} coordinates are empty")
    polygons = coordinates if geo_type == "MultiPolygon" else [coordinates]
    for polygon in polygons:
        if not isinstance(polygon, list) or not polygon:
            raise RegionCatalogError(f"{region_id}: {field} polygon is invalid")
        _validate_polygon_rings(region_id, field, polygon)


def _validate_polygon_rings(region_id: str, field: str, polygon: list[Any]) -> None:
    outer_ring = polygon[0]
    if not isinstance(outer_ring, list) or len(outer_ring) < 4:
        raise RegionCatalogError(f"{region_id}: {field} polygon ring is invalid")
    if outer_ring[0] != outer_ring[-1]:
        raise RegionCatalogError(f"{region_id}: {field} polygon ring must be closed")
    for point in outer_ring:
        if (
            not isinstance(point, list)
            or len(point) != 2
            or not all(isinstance(value, int | float) for value in point)
        ):
            raise RegionCatalogError(f"{region_id}: {field} contains an invalid coordinate")


def _load_adm1_regions(base_regions: tuple[Region, ...]) -> tuple[Region, ...]:
    asset_dir = Path(__file__).resolve().parents[3] / "frontend" / "public" / "maps"
    country_by_iso = {region.iso3: region for region in base_regions if region.level == COUNTRY_LEVEL}
    regions: list[Region] = []
    for iso3, parent in sorted(country_by_iso.items()):
        asset_path = asset_dir / f"{iso3}-ADM1.geojson"
        try:
            collection = json.loads(asset_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RegionCatalogError(f"could not read ADM1 boundary asset: {asset_path}") from exc
        features = collection.get("features") if isinstance(collection, dict) else None
        if not isinstance(features, list):
            raise RegionCatalogError(f"invalid ADM1 boundary asset: {asset_path}")
        for feature in features:
            properties = feature.get("properties", {}) if isinstance(feature, dict) else {}
            geometry = feature.get("geometry") if isinstance(feature, dict) else None
            if not isinstance(properties, dict) or not isinstance(geometry, dict):
                raise RegionCatalogError(f"invalid ADM1 feature in {asset_path}")
            boundary_iso = _required_str(properties, "shapeISO")
            boundary_id = _required_str(properties, "shapeID")
            name = _required_str(properties, "shapeName")
            analytical_geometry = copy.deepcopy(geometry)
            ui_geometry = copy.deepcopy(geometry)
            ui_geometry["bbox"] = _geometry_bbox(geometry)
            regions.append(
                Region(
                    id=f"adm1-{boundary_iso.lower()}",
                    name=name,
                    iso3=iso3,
                    level=ADM1_LEVEL,
                    parent_id=parent.id,
                    is_pilot=False,
                    coverage_type=ADMINISTRATIVE_COVERAGE,
                    source=ADM1_SOURCE,
                    source_version=ADM1_SOURCE_VERSION,
                    geometry=analytical_geometry,
                    ui_geometry=ui_geometry,
                    metadata={
                        "boundary_id": boundary_id,
                        "boundary_iso": boundary_iso,
                        "boundary_level": "ADM1",
                    },
                )
            )
    return tuple(regions)


def _geometry_bbox(geometry: dict[str, Any]) -> list[float]:
    points: list[tuple[float, float]] = []

    def visit(value: Any) -> None:
        if isinstance(value, list) and len(value) == 2 and all(isinstance(item, int | float) for item in value):
            points.append((float(value[0]), float(value[1])))
            return
        if isinstance(value, list):
            for item in value:
                visit(item)

    visit(geometry.get("coordinates"))
    if not points:
        return []
    return [min(point[0] for point in points), min(point[1] for point in points), max(point[0] for point in points), max(point[1] for point in points)]


def _duplicates(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    dupes: list[str] = []
    for value in values:
        if value in seen and value not in dupes:
            dupes.append(value)
        seen.add(value)
    return dupes


def _required_str(item: dict[str, Any], key: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RegionCatalogError(f"missing or invalid string field: {key}")
    return value.strip()


def _optional_str(item: dict[str, Any], key: str) -> str | None:
    value = item.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise RegionCatalogError(f"invalid optional string field: {key}")
    return value.strip()


def _required_bool(item: dict[str, Any], key: str) -> bool:
    value = item.get(key)
    if not isinstance(value, bool):
        raise RegionCatalogError(f"missing or invalid boolean field: {key}")
    return value


def _required_dict(item: dict[str, Any], key: str) -> dict[str, Any]:
    value = item.get(key)
    if not isinstance(value, dict) or not value:
        raise RegionCatalogError(f"missing or invalid object field: {key}")
    return value
