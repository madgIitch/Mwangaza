import type { GeoJsonGeometry, RegionRisk, Severity } from "../types";
import djiboutiBoundariesRaw from "../../public/maps/DJI-ADM1.geojson?raw";
import eritreaBoundariesRaw from "../../public/maps/ERI-ADM1.geojson?raw";
import ethiopiaBoundariesRaw from "../../public/maps/ETH-ADM1.geojson?raw";
import kenyaBoundariesRaw from "../../public/maps/KEN-ADM1.geojson?raw";
import sudanBoundariesRaw from "../../public/maps/SDN-ADM1.geojson?raw";
import somaliaBoundariesRaw from "../../public/maps/SOM-ADM1.geojson?raw";
import southSudanBoundariesRaw from "../../public/maps/SSD-ADM1.geojson?raw";
import ugandaBoundariesRaw from "../../public/maps/UGA-ADM1.geojson?raw";

interface BoundaryFeature {
  type: "Feature";
  properties: { shapeName: string; shapeISO: string; shapeID: string };
  geometry: GeoJsonGeometry;
}

interface BoundaryCollection {
  type: "FeatureCollection";
  features: BoundaryFeature[];
}

export interface OverviewRiskFeature {
  type: "Feature";
  properties: { region: RegionRisk; boundaryName: string; interactiveAnchor: boolean };
  geometry: GeoJsonGeometry;
}

export interface OverviewRiskFeatureCollection {
  type: "FeatureCollection";
  features: OverviewRiskFeature[];
}

const BOUNDARY_SOURCES: Array<{ id: string; name: string; raw: string }> = [
  { id: "sdn", name: "Sudan", raw: sudanBoundariesRaw },
  { id: "eri", name: "Eritrea", raw: eritreaBoundariesRaw },
  { id: "dji", name: "Djibouti", raw: djiboutiBoundariesRaw },
  { id: "eth", name: "Ethiopia", raw: ethiopiaBoundariesRaw },
  { id: "ssd", name: "South Sudan", raw: southSudanBoundariesRaw },
  { id: "uga", name: "Uganda", raw: ugandaBoundariesRaw },
  { id: "ken", name: "Kenya", raw: kenyaBoundariesRaw },
  { id: "som", name: "Somalia", raw: somaliaBoundariesRaw }
];

function normalizeRings(geometry: GeoJsonGeometry): GeoJsonGeometry {
  const signedArea = (ring: number[][]): number => ring.slice(0, -1).reduce(
    (area, point, index) => area + point[0] * ring[index + 1][1] - ring[index + 1][0] * point[1],
    0
  ) / 2;
  const normalizePolygon = (polygon: number[][][]): number[][][] => polygon.map((ring, index) => {
    const area = signedArea(ring);
    const shouldReverse = index === 0 ? area > 0 : area < 0;
    return shouldReverse ? [...ring].reverse() : ring;
  });
  return geometry.type === "Polygon"
    ? { ...geometry, coordinates: normalizePolygon(geometry.coordinates as number[][][]) }
    : { ...geometry, coordinates: (geometry.coordinates as number[][][][]).map(normalizePolygon) };
}

export function buildOverviewRiskFeatures(regions: RegionRisk[], fallbackPeriod: string): OverviewRiskFeatureCollection {
  const regionById = new Map(regions.map((region) => [region.id, region]));
  return {
    type: "FeatureCollection",
    features: BOUNDARY_SOURCES.map(({ id, name, raw }) => {
      const collection = JSON.parse(raw) as BoundaryCollection;
      const polygons = collection.features.flatMap((feature) => {
        const geometry = normalizeRings(feature.geometry);
        return geometry.type === "Polygon"
          ? [geometry.coordinates as number[][][]]
          : geometry.coordinates as number[][][][];
      });
      const uiGeometry: GeoJsonGeometry = { type: "MultiPolygon", coordinates: polygons };
      const region: RegionRisk = {
        ...(regionById.get(id) ?? {
          id,
          name,
          score: null,
          level: "unknown" as Severity,
          quality: "unknown",
          period: fallbackPeriod
        }),
        uiGeometry
      };
      return {
        type: "Feature",
        properties: { region, boundaryName: name, interactiveAnchor: true },
        geometry: uiGeometry
      };
    })
  };
}
