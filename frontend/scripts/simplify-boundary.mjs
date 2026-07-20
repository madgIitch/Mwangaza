import { readFile, writeFile } from "node:fs/promises";

const [inputPath, outputPath, toleranceArg = "0.01"] = process.argv.slice(2);
if (!inputPath || !outputPath) {
  throw new Error("Usage: node frontend/scripts/simplify-boundary.mjs <input> <output> [tolerance]");
}

const tolerance = Number(toleranceArg);
const squaredSegmentDistance = (point, start, end) => {
  let x = start[0];
  let y = start[1];
  let dx = end[0] - x;
  let dy = end[1] - y;
  if (dx !== 0 || dy !== 0) {
    const position = ((point[0] - x) * dx + (point[1] - y) * dy) / (dx * dx + dy * dy);
    if (position > 1) {
      [x, y] = end;
    } else if (position > 0) {
      x += dx * position;
      y += dy * position;
    }
  }
  dx = point[0] - x;
  dy = point[1] - y;
  return dx * dx + dy * dy;
};

const simplifyOpenRing = (points) => {
  if (points.length <= 2) return points;
  const keep = new Uint8Array(points.length);
  keep[0] = 1;
  keep[points.length - 1] = 1;
  const stack = [[0, points.length - 1]];
  while (stack.length) {
    const [first, last] = stack.pop();
    let furthest = -1;
    let greatestDistance = tolerance * tolerance;
    for (let index = first + 1; index < last; index += 1) {
      const distance = squaredSegmentDistance(points[index], points[first], points[last]);
      if (distance > greatestDistance) {
        furthest = index;
        greatestDistance = distance;
      }
    }
    if (furthest >= 0) {
      keep[furthest] = 1;
      stack.push([first, furthest], [furthest, last]);
    }
  }
  return points.filter((_, index) => keep[index]);
};

const simplifyRing = (ring) => {
  if (ring.length < 5) return ring;
  const openRing = ring.slice(0, -1);
  let simplified = simplifyOpenRing(openRing);
  if (simplified.length < 3) simplified = openRing.slice(0, 3);
  simplified = simplified.map(([longitude, latitude]) => [
    Number(longitude.toFixed(5)),
    Number(latitude.toFixed(5))
  ]);
  simplified.push([...simplified[0]]);
  return simplified;
};

const simplifyPolygon = (polygon) => polygon.map(simplifyRing);
const simplifyGeometry = (geometry) => {
  if (geometry.type === "Polygon") {
    return { ...geometry, coordinates: simplifyPolygon(geometry.coordinates) };
  }
  if (geometry.type === "MultiPolygon") {
    return { ...geometry, coordinates: geometry.coordinates.map(simplifyPolygon) };
  }
  return geometry;
};

const collection = JSON.parse(await readFile(inputPath, "utf8"));
collection.features = collection.features.map((feature) => ({
  type: "Feature",
  properties: {
    shapeName: feature.properties.shapeName,
    shapeISO: feature.properties.shapeISO,
    shapeID: feature.properties.shapeID
  },
  geometry: simplifyGeometry(feature.geometry)
}));
await writeFile(outputPath, JSON.stringify(collection));
