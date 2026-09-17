"""Extract the Hanoi administrative polygon from GADM level-1 GeoJSON.

The output is a standalone GeoJSON MultiPolygon in WGS84 (EPSG:4326), suitable
for `osmium extract -p`.
"""

from __future__ import annotations

import json
from pathlib import Path


SOURCE = Path("maps/gadm41_VNM_1.json")
TARGET = Path("maps/hanoi_boundary.geojson")
HANOI_GID = "VNM.27_1"


def main() -> None:
    with SOURCE.open(encoding="utf-8") as source_file:
        collection = json.load(source_file)

    matches = [
        feature
        for feature in collection.get("features", [])
        if feature.get("properties", {}).get("GID_1") == HANOI_GID
    ]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one Hanoi feature ({HANOI_GID}); found {len(matches)}.")

    geometry = matches[0].get("geometry")
    if not isinstance(geometry, dict) or geometry.get("type") not in {"Polygon", "MultiPolygon"}:
        raise ValueError("Hanoi feature does not contain a Polygon or MultiPolygon geometry.")

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    with TARGET.open("w", encoding="utf-8", newline="\n") as target_file:
        json.dump(geometry, target_file, ensure_ascii=False, separators=(",", ":"))
        target_file.write("\n")

    print(f"Created {TARGET} ({geometry['type']}) from {SOURCE}.")
    print("GeoJSON uses longitude, latitude coordinates in WGS84 (EPSG:4326).")


if __name__ == "__main__":
    main()
