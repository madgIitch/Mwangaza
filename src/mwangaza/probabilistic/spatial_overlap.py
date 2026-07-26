from __future__ import annotations

from dataclasses import dataclass
from math import isclose
from typing import Any

Point = tuple[float, float]
Ring = tuple[Point, ...]
Polygon = tuple[Ring, ...]

OVERLAP_RULE_VERSION = "adm1-geometry-overlap-v1"
_EPSILON = 1e-10


class GeometryError(ValueError):
    """Raised when a GeoJSON geometry cannot be mapped safely."""


@dataclass(frozen=True)
class GeometryOverlap:
    intersection_area: float
    source_area: float
    target_area: float

    @property
    def source_fraction(self) -> float:
        return self.intersection_area / self.source_area if self.source_area else 0.0

    @property
    def target_fraction(self) -> float:
        return self.intersection_area / self.target_area if self.target_area else 0.0


def geometry_complexity(geometry: dict[str, Any]) -> int:
    return sum(len(ring) for polygon in _polygons(geometry) for ring in polygon)


def sampled_geometry_overlaps(
    source: dict[str, Any],
    targets: tuple[dict[str, Any], ...],
    *,
    sample_budget: int = 25_000,
) -> tuple[GeometryOverlap, ...]:
    """Approximate complex intersections on a deterministic lon/lat grid."""
    source_polygons = _polygons(source)
    target_polygons = tuple(_polygons(target) for target in targets)
    source_compiled = _compile_polygons(source_polygons)
    target_compiled = tuple(_compile_polygons(polygons) for polygons in target_polygons)
    source_area = sum(_polygon_area(polygon) for polygon in source_polygons)
    target_areas = tuple(sum(_polygon_area(polygon) for polygon in polygons) for polygons in target_polygons)
    bounds = _geometry_bbox(source_polygons)
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    if source_area <= _EPSILON or width <= _EPSILON or height <= _EPSILON:
        raise GeometryError("geometry has zero area")
    ratio = width / height
    columns = max(1, int((sample_budget * ratio) ** 0.5))
    rows = max(1, sample_budget // columns)
    dx = width / columns
    dy = height / rows
    counts = [0] * len(targets)
    for row in range(rows):
        y = bounds[1] + (row + 0.5) * dy
        for column in range(columns):
            point = (bounds[0] + (column + 0.5) * dx, y)
            if not _point_in_compiled_polygons(point, source_compiled):
                continue
            for index, polygons in enumerate(target_compiled):
                if _point_in_compiled_polygons(point, polygons):
                    counts[index] += 1
    cell_area = dx * dy
    return tuple(
        GeometryOverlap(count * cell_area, source_area, target_area)
        for count, target_area in zip(counts, target_areas, strict=True)
    )


def geometry_overlap(source: dict[str, Any], target: dict[str, Any]) -> GeometryOverlap:
    source_polygons = _polygons(source)
    target_polygons = _polygons(target)
    source_area = sum(_polygon_area(polygon) for polygon in source_polygons)
    target_area = sum(_polygon_area(polygon) for polygon in target_polygons)
    if source_area <= _EPSILON or target_area <= _EPSILON:
        raise GeometryError("geometry has zero area")
    intersection = sum(
        _polygon_intersection_area(left, right)
        for left in source_polygons
        for right in target_polygons
        if _bbox_intersects(_bbox(left[0]), _bbox(right[0]))
    )
    return GeometryOverlap(
        intersection_area=max(0.0, intersection),
        source_area=source_area,
        target_area=target_area,
    )


def _polygons(geometry: dict[str, Any]) -> tuple[Polygon, ...]:
    kind = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if kind == "Polygon":
        return (_polygon(coordinates),)
    if kind == "MultiPolygon" and isinstance(coordinates, list):
        return tuple(_polygon(value) for value in coordinates)
    raise GeometryError("only Polygon and MultiPolygon GeoJSON are supported")


def _polygon(value: object) -> Polygon:
    if not isinstance(value, list) or not value:
        raise GeometryError("polygon has no rings")
    rings = tuple(_ring(item) for item in value)
    if _polygon_area(rings) <= _EPSILON:
        raise GeometryError("polygon has zero area")
    return rings


def _ring(value: object) -> Ring:
    if not isinstance(value, list):
        raise GeometryError("ring is not a coordinate list")
    points: list[Point] = []
    for item in value:
        if (
            not isinstance(item, list)
            or len(item) < 2
            or not isinstance(item[0], int | float)
            or not isinstance(item[1], int | float)
        ):
            raise GeometryError("ring contains an invalid coordinate")
        point = (float(item[0]), float(item[1]))
        if not points or point != points[-1]:
            points.append(point)
    if len(points) > 1 and points[0] == points[-1]:
        points.pop()
    if len(points) < 3:
        raise GeometryError("ring needs at least three distinct points")
    return tuple(points)


def _signed_area(ring: Ring) -> float:
    if len(ring) < 3:
        return 0.0
    return sum(
        left[0] * right[1] - right[0] * left[1]
        for left, right in zip(ring, (*ring[1:], ring[0]), strict=True)
    ) / 2


def _polygon_area(polygon: Polygon) -> float:
    return max(0.0, abs(_signed_area(polygon[0])) - sum(abs(_signed_area(r)) for r in polygon[1:]))


def _polygon_intersection_area(left: Polygon, right: Polygon) -> float:
    area = _ring_intersection_area(left[0], right[0])
    area -= sum(_ring_intersection_area(hole, right[0]) for hole in left[1:])
    area -= sum(_ring_intersection_area(left[0], hole) for hole in right[1:])
    area += sum(
        _ring_intersection_area(left_hole, right_hole)
        for left_hole in left[1:]
        for right_hole in right[1:]
    )
    return max(0.0, area)


def _ring_intersection_area(left: Ring, right: Ring) -> float:
    if not _bbox_intersects(_bbox(left), _bbox(right)):
        return 0.0
    return sum(
        abs(_signed_area(tuple(_clip_polygon(list(a), b))))
        for a in _triangulate(left)
        for b in _triangulate(right)
        if _bbox_intersects(_bbox(a), _bbox(b))
    )


def _triangulate(ring: Ring) -> tuple[tuple[Point, Point, Point], ...]:
    points = list(ring if _signed_area(ring) > 0 else tuple(reversed(ring)))
    triangles: list[tuple[Point, Point, Point]] = []
    remaining = list(range(len(points)))
    guard = len(points) * len(points)
    while len(remaining) > 3 and guard:
        guard -= 1
        clipped = False
        for offset, current in enumerate(remaining):
            before = remaining[offset - 1]
            after = remaining[(offset + 1) % len(remaining)]
            triangle = (points[before], points[current], points[after])
            if _cross(triangle[0], triangle[1], triangle[2]) <= _EPSILON:
                continue
            if any(
                _point_in_triangle(points[index], triangle)
                for index in remaining
                if index not in {before, current, after}
            ):
                continue
            triangles.append(triangle)
            remaining.pop(offset)
            clipped = True
            break
        if not clipped:
            raise GeometryError("polygon ring is invalid or self-intersecting")
    if len(remaining) == 3:
        triangles.append(tuple(points[index] for index in remaining))
    if not triangles:
        raise GeometryError("polygon could not be triangulated")
    return tuple(triangles)


def _clip_polygon(subject: list[Point], clip: tuple[Point, Point, Point]) -> list[Point]:
    output = subject
    for edge_start, edge_end in zip(clip, (*clip[1:], clip[0]), strict=True):
        incoming = output
        output = []
        if not incoming:
            break
        previous = incoming[-1]
        for current in incoming:
            current_inside = _cross(edge_start, edge_end, current) >= -_EPSILON
            previous_inside = _cross(edge_start, edge_end, previous) >= -_EPSILON
            if current_inside:
                if not previous_inside:
                    output.append(_line_intersection(previous, current, edge_start, edge_end))
                output.append(current)
            elif previous_inside:
                output.append(_line_intersection(previous, current, edge_start, edge_end))
            previous = current
    return output


def _line_intersection(a: Point, b: Point, c: Point, d: Point) -> Point:
    ab = (b[0] - a[0], b[1] - a[1])
    cd = (d[0] - c[0], d[1] - c[1])
    denominator = ab[0] * cd[1] - ab[1] * cd[0]
    if isclose(denominator, 0.0, abs_tol=_EPSILON):
        return b
    factor = ((c[0] - a[0]) * cd[1] - (c[1] - a[1]) * cd[0]) / denominator
    return a[0] + factor * ab[0], a[1] + factor * ab[1]


def _point_in_triangle(point: Point, triangle: tuple[Point, Point, Point]) -> bool:
    a, b, c = triangle
    return (
        _cross(a, b, point) >= -_EPSILON
        and _cross(b, c, point) >= -_EPSILON
        and _cross(c, a, point) >= -_EPSILON
    )


def _cross(a: Point, b: Point, c: Point) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _bbox(ring: Ring | tuple[Point, Point, Point]) -> tuple[float, float, float, float]:
    xs = [point[0] for point in ring]
    ys = [point[1] for point in ring]
    return min(xs), min(ys), max(xs), max(ys)


def _bbox_intersects(left: tuple[float, ...], right: tuple[float, ...]) -> bool:
    return not (
        left[2] <= right[0] or right[2] <= left[0] or left[3] <= right[1] or right[3] <= left[1]
    )


def _geometry_bbox(polygons: tuple[Polygon, ...]) -> tuple[float, float, float, float]:
    bounds = tuple(_bbox(polygon[0]) for polygon in polygons)
    return (
        min(value[0] for value in bounds),
        min(value[1] for value in bounds),
        max(value[2] for value in bounds),
        max(value[3] for value in bounds),
    )


def _compile_polygons(
    polygons: tuple[Polygon, ...],
) -> tuple[tuple[Polygon, tuple[float, float, float, float]], ...]:
    return tuple((polygon, _bbox(polygon[0])) for polygon in polygons)


def _point_in_compiled_polygons(
    point: Point,
    polygons: tuple[tuple[Polygon, tuple[float, float, float, float]], ...],
) -> bool:
    return any(
        _point_in_ring(point, polygon[0])
        and not any(_point_in_ring(point, hole) for hole in polygon[1:])
        for polygon, bounds in polygons
        if _point_in_bbox(point, bounds)
    )


def _point_in_ring(point: Point, ring: Ring) -> bool:
    inside = False
    previous = ring[-1]
    for current in ring:
        if (current[1] > point[1]) != (previous[1] > point[1]):
            crossing_x = (previous[0] - current[0]) * (point[1] - current[1]) / (
                previous[1] - current[1]
            ) + current[0]
            if point[0] < crossing_x:
                inside = not inside
        previous = current
    return inside


def _point_in_bbox(point: Point, bounds: tuple[float, float, float, float]) -> bool:
    return bounds[0] <= point[0] <= bounds[2] and bounds[1] <= point[1] <= bounds[3]
