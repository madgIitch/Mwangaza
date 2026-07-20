from __future__ import annotations

import copy
import unittest

from mwangaza.regions import (
    ADM1_LEVEL,
    PILOT_COVERAGE,
    REGIONAL_COVERAGE,
    REQUIRED_COUNTRIES,
    Region,
    RegionCatalogError,
    get_region,
    list_regions,
    load_region_catalog,
    validate_region_catalog,
)


class RegionCatalogTests(unittest.TestCase):
    def test_catalog_contains_required_igad_countries_only(self) -> None:
        countries = list_regions(level="country")
        self.assertEqual({region.iso3 for region in countries}, set(REQUIRED_COUNTRIES))
        self.assertEqual(len(countries), 8)
        self.assertEqual({region.id for region in countries}, {"ken", "eth", "som", "sdn", "ssd", "uga", "dji", "eri"})

    def test_regions_expose_required_public_fields(self) -> None:
        for region in load_region_catalog():
            public = region.to_public_dict()
            self.assertEqual(
                set(public),
                {
                    "id",
                    "name",
                    "iso3",
                    "level",
                    "parent_id",
                    "is_pilot",
                    "coverage_type",
                    "source",
                    "source_version",
                    "geometry",
                    "ui_geometry",
                    "metadata",
                },
            )
            self.assertIsInstance(region.geometry, dict)
            self.assertIsInstance(region.ui_geometry, dict)
            self.assertNotEqual(region.geometry, region.ui_geometry)

    def test_pilot_areas_are_explicit_and_parented(self) -> None:
        pilots = [region for region in load_region_catalog() if region.is_pilot]
        self.assertGreaterEqual(len(pilots), 2)
        self.assertIn("somalia-pilot", {region.id for region in pilots})
        self.assertIn("northern-kenya-pilot", {region.id for region in pilots})
        for pilot in pilots:
            self.assertEqual(pilot.coverage_type, PILOT_COVERAGE)
            self.assertEqual(pilot.level, "pilot_area")
            self.assertIsNotNone(pilot.parent_id)
            self.assertIn("not complete validated subnational coverage", pilot.metadata["pilot_note"])

    def test_list_regions_can_exclude_pilots(self) -> None:
        regions = list_regions(include_pilots=False)
        self.assertEqual(len(regions), 8)
        self.assertTrue(all(not region.is_pilot for region in regions))
        self.assertTrue(all(region.coverage_type == REGIONAL_COVERAGE for region in regions))

    def test_get_region_returns_stable_ids(self) -> None:
        self.assertEqual(get_region("KEN").id, "ken")
        self.assertEqual(get_region("northern-kenya-pilot").iso3, "KEN")
        with self.assertRaises(RegionCatalogError):
            get_region("missing")

    def test_adm1_catalog_preserves_geoboundaries_identifiers(self) -> None:
        units = list_regions(level=ADM1_LEVEL, include_administrative=True)

        self.assertEqual(len(units), 121)
        hiiraan = get_region("adm1-so-hi")
        self.assertEqual(hiiraan.parent_id, "som")
        self.assertEqual(hiiraan.metadata["boundary_iso"], "SO-HI")
        self.assertTrue(hiiraan.metadata["boundary_id"])
        self.assertIn(hiiraan.geometry["type"], {"Polygon", "MultiPolygon"})

    def test_validate_rejects_duplicate_ids(self) -> None:
        regions = list(load_region_catalog())
        regions[1] = _replace(regions[1], id=regions[0].id)
        with self.assertRaisesRegex(RegionCatalogError, "duplicate region ids"):
            validate_region_catalog(regions)

    def test_validate_rejects_duplicate_country_iso3(self) -> None:
        regions = list(load_region_catalog())
        regions[1] = _replace(regions[1], iso3=regions[0].iso3)
        with self.assertRaisesRegex(RegionCatalogError, "duplicate country ISO3"):
            validate_region_catalog(regions)

    def test_validate_rejects_empty_geometry(self) -> None:
        regions = list(load_region_catalog())
        regions[0] = _replace(regions[0], geometry={})
        with self.assertRaisesRegex(RegionCatalogError, "geometry"):
            validate_region_catalog(regions)

    def test_validate_rejects_open_polygon_ring(self) -> None:
        regions = list(load_region_catalog())
        geometry = copy.deepcopy(regions[0].geometry)
        geometry["coordinates"][0][-1] = [99.0, 99.0]
        regions[0] = _replace(regions[0], geometry=geometry)
        with self.assertRaisesRegex(RegionCatalogError, "closed"):
            validate_region_catalog(regions)

    def test_validate_rejects_missing_parent(self) -> None:
        regions = list(load_region_catalog())
        pilot = next(region for region in regions if region.id == "somalia-pilot")
        regions[regions.index(pilot)] = _replace(pilot, parent_id="missing-parent")
        with self.assertRaisesRegex(RegionCatalogError, "parent_id"):
            validate_region_catalog(regions)


def _replace(region: Region, **changes: object) -> Region:
    values = region.to_public_dict()
    values.update(changes)
    return Region(**values)


if __name__ == "__main__":
    unittest.main()
