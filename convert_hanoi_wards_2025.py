"""Convert the downloaded Hanoi 2025 ward JSON into standard GeoJSON.

Input:  maps/01.json
Output: maps/hanoi_wards_2025.geojson

The input's ``polygons`` field contains one or more exterior rings per ward.
They are written as a GeoJSON MultiPolygon so every feature has one uniform
geometry type and can be opened directly in QGIS.
"""

from __future__ import annotations

import json
from pathlib import Path


SOURCE = Path("maps/01.json")
TARGET = Path("maps/hanoi_wards_2025.geojson")
EXPECTED_WARD_COUNT = 126


def normalise_ring(raw_ring: list[list[float]], ward_name: str) -> list[list[float]]:
    if len(raw_ring) < 4:
        raise ValueError(f"{ward_name}: a polygon ring needs at least four positions.")

    ring: list[list[float]] = []
    for position in raw_ring:
        if not isinstance(position, list) or len(position) < 2:
            raise ValueError(f"{ward_name}: invalid coordinate position.")
        lon, lat = float(position[0]), float(position[1])
        if not (102.0 <= lon <= 110.0 and 19.0 <= lat <= 24.0):
            raise ValueError(f"{ward_name}: coordinate outside the expected Hanoi region: {position}")
        ring.append([lon, lat])

    if ring[0] != ring[-1]:
        ring.append(ring[0])
    return ring


def main() -> None:
    with SOURCE.open(encoding="utf-8") as source_file:
        source = json.load(source_file)

    wards = source.get("wards")
    if not isinstance(wards, list) or len(wards) != EXPECTED_WARD_COUNT:
        raise ValueError(f"Expected {EXPECTED_WARD_COUNT} wards; found {len(wards) if isinstance(wards, list) else 'none'}.")

    features = []
    seen_names: set[str] = set()
    for ward in wards:
        name = ward.get("name")
        polygons = ward.get("polygons")
        if not isinstance(name, str) or not name:
            raise ValueError("A ward has no name.")
        if name in seen_names:
            raise ValueError(f"Duplicate ward name: {name}")
        seen_names.add(name)
        if not isinstance(polygons, list) or not polygons:
            raise ValueError(f"{name}: no polygons supplied.")

        multipolygon = [[normalise_ring(ring, name)] for ring in polygons]
        center = ward.get("center", [None, None])
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "ward_id": ward.get("id"),
                    "ward": name,
                    "unit_type": ward.get("type"),
                    "area_km2_source": ward.get("area"),
                    "population_source": ward.get("population"),
                    "density_source": ward.get("density"),
                    "center_lon_source": center[0] if len(center) >= 1 else None,
                    "center_lat_source": center[1] if len(center) >= 2 else None,
                    "admin_geography_version": "Hanoi wards/communes effective 2025-07-01",
                },
                "geometry": {"type": "MultiPolygon", "coordinates": multipolygon},
            }
        )

    required_names = {"Từ Liêm", "Xuân Phương"}
    missing = required_names - seen_names
    if missing:
        raise ValueError(f"Required pilot wards missing: {', '.join(sorted(missing))}")

    result = {
        "type": "FeatureCollection",
        "name": "hanoi_wards_2025",
        "features": features,
    }
    with TARGET.open("w", encoding="utf-8", newline="\n") as target_file:
        json.dump(result, target_file, ensure_ascii=False, separators=(",", ":"))
        target_file.write("\n")

    print(f"Created {TARGET} with {len(features)} ward/commune features in WGS84 GeoJSON.")


if __name__ == "__main__":
    main()
